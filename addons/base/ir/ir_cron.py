# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
import sys
import threading
import time
import traceback
import psycopg2
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dbf import DateTime
from antipathy import Path
from scription import Job
from tempfile import mkdtemp
import shlex

import openerp
from openerp import netsvc
from openerp.exceptions import ERPError
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, self_ids
from openerp.tools.misc import stonemark2html
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

def str2tuple(s):
    return eval('tuple(%s)' % (s or ''))

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

_ir_cron_inited = False

class ir_cron(osv.osv):
    """ Model describing cron jobs (also called actions or tasks).
    """

    # TODO: perhaps in the future we could consider a flag on ir.cron jobs
    # that would cause database wake-up even if the database has not been
    # loaded yet or was already unloaded (e.g. 'force_db_wakeup' or something)
    # See also openerp.cron

    _name = "ir.cron"
    _order = 'name'

    def _calc_timeout(self, cr, uid, ids, field_name, arg, context=None):
        "convert time to seconds (e.g. 2m -> 120)"
        res = {}
        if field_name != 'timeout':
            return res
        # get changed records
        for rec in self.read(cr, uid, ids, fields=['id', 'timeout_display'], context=context):
            id = rec['id']
            time = rec['timeout_display']
            if not time:
                res[id] = 0
                continue
            text = time
            if text[0] == '-':
                raise ERPError('Field Error', 'invalid wait time: <%s>' % time)
            wait_time = 0
            digits = []
            for c in text:
                # anything after a time is found is an error
                if c.isdigit():
                    digits.append(c)
                    continue
                if c == ' ':
                    if not digits:
                        continue
                    else:
                        raise ERPError('Field Error', 'invalid wait time: <%s>' % time)
                number = int(''.join(digits))
                c = c.lower()
                if c not in ('hms'):
                    raise ERPError('Field Error', 'invalid wait time: <%s>' % time)
                wait_time += {'h':3600, 'm':60, 's':1}[c] * number
                digits = []
            else:
                if digits:
                    # didn't specify a unit, abort
                    raise ERPError('Field Error', 'missing trailing time unit of h, m, or s in <%s>' % time)
            res[id] = wait_time
        return res

    _columns = {
        'name': fields.char('Name', size=60, required=True),
        'type': fields.selection((
            ('internal', 'OpenERP'),
            ('external', 'O/S'),
            ),
            'Job Type',
            sort_order='definition',
            required=True,
            ),
        'schedule_type': fields.selection((
            ('internal', 'OpenERP'),
            ('crontab', 'Cron'),
            ),
            'Schedule Type',
            sort_order='definition',
            required=True,
            ),
        'timeout_display': fields.char('Time-out', size=20, help='maximum time to run'),
        'timeout': fields.function(
            _calc_timeout,
            type='integer',
            string='Time-out in seconds',
            help='Maximum time, in seconds, to run',
            store={
                'ir.cron': (lambda s, c, u, ids, ctx: ids, ['timeout_display'], 10)
                },
            ),
        'cron_schedule': fields.char('Cron Timing', size=128, help="minute  hour  day-of-month  month  day-of-week"),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'active': fields.boolean('Active'),
        'interval_number': fields.integer('Interval Number',help="Repeat every x."),
        'interval_type': fields.selection([
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('work_days','Work Days'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months')
            ],
            string='Interval Unit',
            ),
        'numbercall': fields.integer('Number of Calls', help='How many times the method is called,\na negative number indicates no limit.'),
        'doall' : fields.boolean('Repeat Missed', help="Specify if missed occurrences should be executed when the server restarts."),
        'nextcall' : fields.datetime('Next Execution Date', required=True, help="Next planned execution date for this job."),
        'model': fields.char('Object', size=64, help="Model name on which the method to be called is located, e.g. 'res.partner'."),
        'function': fields.char('Method', size=64, help="Name of the method to be called when this job is processed."),
        'args': fields.text('Arguments', help="Arguments to be passed to the method, e.g. (uid,)."),
        'priority': fields.integer('Priority', help='The priority of the job, as an integer: 0 means higher priority, 10 means lower priority.'),
        'partial': fields.boolean('Allow partial updates', help='Keep changes from failed jobs? (helps prevent update deadlocks)'),
        'state': fields.selection((
            ('inactive', 'Inactive'),
            ('waiting', 'Waiting'),
            ('running', 'Running'),
            ),
            'state',
            sort_order='definition',
            ),
        'results': fields.text('Results'),
        'description': fields.text('Notes (commonmark)'),
        'description_html': fields.function(
                stonemark2html,
                arg='description',
                type='html',
                string='Notes',
                store={
                    'ir.cron': (self_ids, ['description'], 10),
                    }
                ),
    }

    _defaults = {
        'nextcall' : lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'priority' : 5,
        'user_id' : lambda obj,cr,uid,context: uid,
        'interval_number' : 1,
        'interval_type' : 'months',
        'numbercall' : 1,
        'active' : 1,
        'doall' : 1,
        'partial' : False,
        'state' : 'waiting',
        'type' : 'internal',
        'schedule_type': 'internal',
    }

    def __init__(self, pool, cr):
        "make sure state is set approppriately"
        global _ir_cron_inited
        super(ir_cron, self).__init__(pool, cr)
        if not _ir_cron_inited:
            cr.execute("UPDATE ir_cron SET state='inactive' WHERE active=false")
            cr.execute("UPDATE ir_cron SET state='waiting' WHERE active=true")
            _ir_cron_inited = True

    def _check_args(self, cr, uid, ids, context=None):
        try:
            for this in self.browse(cr, uid, ids, context):
                if this.type != 'external':
                    str2tuple(this.args)
        except Exception:
            return False
        return True

    _constraints = [
        (_check_args, 'Invalid arguments', ['args']),
    ]

    def _handle_callback_exception(self, cr, uid, model_name, method_name, args, job_id, job_name, job_type, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        :param job_exception: exception raised by the job.

        """
        cr.rollback()
        if job_type == 'external':
            _logger.exception('Call of %r failed in Job %s' % (args, job_id))
        else:
            _logger.exception("Call of self.pool.get('%s').%s(cr, uid, *%r) failed in Job %s" % (model_name, method_name, args, job_id))

    def _callback(self, cr, uid, model_name, method_name, args, job_id, job_name, job_type, job_timeout):
        """ Run the method associated to a given job

        It takes care of logging and exception handling.

        :param model_name: model name on which the job method is located.
        :param method_name: name of the method to call when this job is processed.
        :param args: arguments of the method (without the usual self, cr, uid).
        :param job_id: job id.
        """
        # convert job_timeout from minutes to seconds
        job_timeout = job_timeout or 0
        _logger.debug('job_type: %r', job_type)
        _logger.debug('model_name: %r', model_name)
        _logger.debug('args: %r', args)
        _logger.debug('job_timeout: %r seconds', job_timeout)
        _logger.debug('job id: %r   job name: %r', job_id, job_name)
        if job_type == 'external':
            model = self.pool.get('ir.cron')
            method = model.external_job
        else:
            args = str2tuple(args)
            model = self.pool.get(model_name)
            result = None
            if model is None:
                _logger.error('model %r does not exist', model_name)
                raise ERPError('Invalid Model', 'model %r does not exist' % model_name)
            method = getattr(model, method_name)
            if method is None:
                _logger.error('method %r does not exist on model %r', method_name, model_name)
                raise ERPError('Invalid Method', 'model %r has no method %r' % (model_name, method_name))
        try:
            log_depth = (None if _logger.isEnabledFor(logging.DEBUG) else 1)
            netsvc.log(_logger, logging.DEBUG, 'cron.object.execute', (cr.dbname,uid,'*',model_name,method_name)+(args,), depth=log_depth)
            start_dt = fields.datetime.now(self, cr, localtime=True)
            start_time = time.time()
            if job_type == 'internal':
                result = method(cr, uid, *args)
            elif job_type == 'external':
               result = method(cr, uid, args, job_timeout)
            else:
               _logger.error('unknown job type for job %d: %r' % (job_id, job_type))
               raise ERPError('Invalid Type', 'unknown job type: %r' % job_type)
            end_time = time.time()
            end_dt = fields.datetime.now(self, cr, localtime=True)
            if result in (None, True, False):
                result = 'Job Start: %s\nJob End: %s' % (start_dt, end_dt)
            else:
                # better be a string
                result = 'Job Start: %s\nJob End: %s\n\n' % (start_dt, end_dt) + result.strip()
            _logger.debug('%.3fs (%s, %s)' % (end_time - start_time, model_name, method_name))
            return result
        except Exception, e:
            end_time = time.time()
            end_dt = fields.datetime.now(self, cr, localtime=True)
            cls, exc, tb = sys.exc_info()
            self._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, job_name, job_type, e)
            return 'Job Start: %s\nJob End: %s\n\n%s' % (start_dt, end_dt, '\n'.join(traceback.format_exception(cls, exc,tb)))

    def _process_job(self, job_cr, job, cron_cr, force=False):
        """ Run a given job taking care of the repetition.

        :param job_cr: cursor to use to execute the job, safe to commit/rollback
        :param job: job to be run (as a dictionary).
        :param cron_cr: cursor holding lock on the cron job row, to use to update the next exec date,
            must not be committed/rolled back!
        """
        try:
            scheduled = Scheduled(job)
            while scheduled or force:
                result = self._callback(job_cr, scheduled.user_id, scheduled.model, scheduled.function, scheduled.args, scheduled.id, scheduled.name, scheduled.type, scheduled.timeout)
                if force:
                    break
            #
            addsql = ''
            if not scheduled.numbercall:
                addsql = ', active=False'
            if scheduled.schedule_type == 'internal':
                next_call = scheduled.nextcall.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            elif scheduled.schedule_type == 'crontab':
                # get time in server's timezone
                now = fields.datetime.server_time(self, job_cr)
                cron_entry = CronEntry(scheduled.cron_schedule)
                next_call = cron_entry.next_occurance(now)
                # switch back to UTC
                next_call = next_call.astimezone(pytz.UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                cron_cr.execute("UPDATE ir_cron SET active=False WHERE id=%s", (scheduled.id, ))
                raise ERPError('Job %r' % scheduled.id, 'Unknown scheduling type: %r' % (scheduled.schedule_type, ))
            #
            cron_cr.execute(
                    "UPDATE ir_cron SET state='waiting', results=%s, nextcall=%s, numbercall=%s"+addsql+" WHERE id=%s",
                    (result, next_call, scheduled.numbercall, scheduled.id),
                    )
        finally:
            job_cr.commit()
            cron_cr.commit()


    def button_submit(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        db_name = threading.current_thread().dbname
        # set the next scheduled event to the last one
        # but use our own cursor
        db = openerp.sql_db.db_connect(db_name)
        button_cr = db.cursor()
        try:
            for id in ids:
                button_cr.execute(
                        "SELECT id, nextcall, interval_type, interval_number"
                        " FROM ir_cron"
                        " WHERE id=%s",
                        (id, ),
                        )
                [cron_job] = button_cr.dictfetchall()
                nextcall = datetime.strptime(cron_job['nextcall'], DEFAULT_SERVER_DATETIME_FORMAT)
                while nextcall > datetime.now():
                    nextcall -= _intervalTypes[cron_job['interval_type']](cron_job['interval_number'])
                button_cr.execute(
                        "UPDATE ir_cron"
                        " SET nextcall=%s"
                        " WHERE id=%s",
                        (nextcall.strftime(DEFAULT_SERVER_DATETIME_FORMAT), id),
                        )
                button_cr.commit()
        finally:
            button_cr.close()
        return True

    def external_job(self, cr, uid, args, timeout):
        "Runs the external job given in args"
        args = shlex.split(args)
        tmp = Path(mkdtemp(prefix='oe_cron_job-%s-' % Path(args[0]).filename))
        job = None
        try:
            job = Job(args, cwd=tmp)
            _logger.info('running job [%s]  %s', job.pid, ' '.join(args))
            job.communicate(timeout=timeout or None)
            result = []
            if job.returncode:
                result.append('script exited with: %s\n' % job.returncode)
            if job.stdout:
                result.append('======')
                result.append('stdout')
                result.append('======')
                result.append(job.stdout.strip())
            if job.stderr:
                result.append('======')
                result.append('stderr')
                result.append('======')
                result.append(job.stderr.strip())
        finally:
            if job is not None:
                _logger.info('closing job [%s]  %s', job.pid, ' '.join(args))
                job.close()
        try:
            tmp.rmtree()
        except Exception:
            cls, exc, tb = sys.exc_info()
            result.append('======')
            result.append('rmtree')
            result.append('======')
            result.append('\n'.join(traceback.format_exception(cls, exc,tb)))
        return '\n'.join(result)

    @classmethod
    def _acquire_job(cls, db_name, job_id=None):
        # TODO remove 'check' argument from addons/base_action_rule/base_action_rule.py
        """ Try to process one cron job.

        This selects in database all the jobs that should be processed. It then
        tries to lock each of them and, if it succeeds, run the cron job (if it
        doesn't succeed, it means the job was already locked to be taken care
        of by another thread) and return.

        If a job was processed, returns True, otherwise returns False.
        """
        _logger.warning('attempting to gather job%s', job_id and (': %s' % job_id) or 's')
        db = openerp.sql_db.db_connect(db_name)
        threading.current_thread().dbname = db_name
        cr = db.cursor()
        jobs = []
        run_any = False
        try:
            if job_id is not None:
                cr.execute("SELECT * FROM ir_cron WHERE id=%s", (job_id, ))
            else:
                # Careful to compare timestamps with 'UTC' - everything is UTC as of v6.1.
                cr.execute("""SELECT * FROM ir_cron
                              WHERE numbercall != 0
                                  AND active AND nextcall <= (now() at time zone 'UTC')
                              ORDER BY priority""")
            jobs = cr.dictfetchall()
        except psycopg2.ProgrammingError, e:
            if e.pgcode == '42P01':
                # Class 42 — Syntax Error or Access Rule Violation; 42P01: undefined_table
                # The table ir_cron does not exist; this is probably not an OpenERP database.
                _logger.warning('Tried to poll an undefined table on database %s.', db_name)
            else:
                raise
        except Exception:
            _logger.warning('Exception in cron:', exc_info=True)
        finally:
            cr.close()

        _logger.warning('found %d jobs', len(jobs))
        for job in jobs:
            _logger.warning('attempting to process %r', job['name'])
            lock_cr = db.cursor()
            try:
                # Try to grab an exclusive lock on the job row from within the task transaction
                lock_cr.execute("""SELECT *
                                   FROM ir_cron
                                   WHERE id=%s
                                   FOR UPDATE NOWAIT""",
                               (job['id'],), log_exceptions=False)
                # pause so other cron threads bypass this row
                time.sleep(0.1)
                # update and relock row
                lock_cr.execute("UPDATE ir_cron SET state='running', results='' WHERE id=%s", (job['id'], ))
                lock_cr.commit()
                lock_cr.execute("""SELECT *
                                   FROM ir_cron
                                   WHERE id=%s
                                   FOR UPDATE NOWAIT""",
                               (job['id'],), log_exceptions=False)
                # Got the lock on the job row, run its code
                _logger.debug('Starting job `%s`.', job['name'])
                job_cr = db.cursor()
                job_cr.autocommit(job['partial']==True)
                try:
                    openerp.modules.registry.RegistryManager.check_registry_signaling(db_name)
                    registry = openerp.pooler.get_pool(db_name)
                    registry[cls._name]._process_job(job_cr, job, lock_cr, force=bool(job_id))
                    openerp.modules.registry.RegistryManager.signal_caches_change(db_name)
                    run_any = True
                except Exception:
                    _logger.exception('Unexpected exception while processing cron job %r', job)
                finally:
                    job_cr.close()

            except psycopg2.OperationalError, e:
                if e.pgcode == '55P03':
                    # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                    _logger.debug('Another process/thread is already busy executing job `%s`, skipping it.', job['name'])
                    continue
                else:
                    # Unexpected OperationalError
                    raise
            finally:
                # we're exiting due to an exception while acquiring the lock
                lock_cr.close()

        if hasattr(threading.current_thread(), 'dbname'): # cron job could have removed it as side-effect
            del threading.current_thread().dbname

        _logger.warning('returning %r', run_any)
        return run_any

    def _try_lock(self, cr, uid, ids, context=None):
        """Try to grab a dummy exclusive write-lock to the rows with the given ids,
           to make sure a following write() or unlink() will not block due
           to a process currently executing those cron tasks"""
        try:
            cr.execute("""SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE NOWAIT""" % self._table,
                       (tuple(ids),), log_exceptions=False)
        except psycopg2.OperationalError:
            cr.rollback() # early rollback to allow translations to work for the user feedback
            raise osv.except_osv(_("Record cannot be modified right now"),
                                 _("This cron task is currently being executed and may not be modified, "
                                  "please try again in a few minutes"))

    def onchange_cron_schedule(self, cr, uid, ids, schedule, context=None):
        res = {}
        if schedule:
            if len(schedule.split()) > 5:
                res['warning'] = {
                        'title': 'Bad Value',
                        'message': 'cron entry should have five space-separated items',
                        }
            else:
                # get time in server's timezone
                now = fields.datetime.server_time(self, cr)
                cron_entry = CronEntry(schedule)
                next_call = cron_entry.next_occurance(now)
                # switch back to UTC
                next_call = next_call.astimezone(pytz.UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                value = {
                    'cron_schedule': cron_entry,
                    'nextcall': next_call,
                    'numbercall': -1,
                    }
                res['value'] = value
        return res

    def create(self, cr, uid, vals, context=None):
        # TODO: handle schedule_type of crontab
        if 'active' in vals and not vals['active']:
            vals['state'] = 'inactive'
        res = super(ir_cron, self).create(cr, uid, vals, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        # TODO: handle schedule_type of crontab
        self._try_lock(cr, uid, ids, context)
        if 'active' in vals:
            if vals['active']:
                vals['state'] = 'waiting'
            else:
                vals['state'] = 'inactive'
        res = super(ir_cron, self).write(cr, uid, ids, vals, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self._try_lock(cr, uid, ids, context)
        res = super(ir_cron, self).unlink(cr, uid, ids, context=context)
        return res


class Scheduled(object):

    def __init__(self, job):
        self.__dict__.update(job)
        self.nextcall = datetime.strptime(self.nextcall, DEFAULT_SERVER_DATETIME_FORMAT)
        self._once = False
        self._now = datetime.now()

    def __nonzero__(self):
        "calculate next run date/time and return True if before now()"
        # emergency exit for crontab jobs without a crontab setting
        if self.schedule_type == 'crontab' and not self.cron_schedule:
            return False
        # only update after initial passthrough
        if self._once and self.numbercall:
            # put this here so it happens after the initial True result
            if self.numbercall > 0:
                self.numbercall -= 1
            # only update nextcall if numbercall is nonzero
            while self.numbercall:
                self.nextcall += _intervalTypes[self.interval_type](self.interval_number)
                if self.doall or self.nextcall > self._now:
                    break
        self._once = True
        return self.numbercall and self.nextcall <= self._now


class CronEntry(str):
    "minute  hour  day-of-month  month  day-of-week"

    def __new__(cls, line):
        if not line:
            raise ERPError('Cron Error', 'No timing specified.')
        line = '  '.join((line.split() + ['*', '*', '*', '*', '*'])[:5])
        ce = super(CronEntry, CronEntry).__new__(cls, line)
        minute, hour, day_of_month, month, day_of_week = line.split()
        ce.minute = ce._get_range(minute, range(60))
        ce.hour = ce._get_range(hour, range(24))
        ce.day_of_month = ce._get_range(day_of_month, range(1, 32))
        ce.month = ce._get_range(month, range(1, 13))
        ce.day_of_week = ce._get_range(day_of_week, range(7))
        return ce

    def __repr__(self):
        return 'CronEntry(%s)' % super(CronEntry, self).__repr__()

    def _get_range(self, value, valid_range):
        #
        # *
        # */2
        # 0-15
        # 10,12,15
        # 0-15/5
        # 0-15/5,30-45/5
        # */3,*/5
        #
        if value == '*':
            return set(valid_range)
        values = value.split(',')
        final = []
        for val in values:
            if '/' in val:
                val, step = val.split('/')
                step = int(step)
            else:
                step = 1
            if val == '*':
                val = valid_range[::step]
            elif '-' in val:
                start, stop = val.split('-')
                start = int(start)
                stop = int(stop) + 1
                val = range(start, stop, step)
            else:
                val = [int(val)]
            final.extend(val)
        return set(final)

    def is_valid(self, timestamp):
        # crontab has Sunday at 0, Monday at 1, but isoweekday has Sunday at 7, Monday at 1
        weekday = (0, 1, 2, 3, 4, 5, 6, 0)[timestamp.isoweekday()]
        return (
                timestamp.minute in self.minute
            and timestamp.hour in self.hour
            and timestamp.day in self.day_of_month
            and timestamp.month in self.month
            and weekday in self.day_of_week
            )

    def next_occurance(self, timestamp):
        timestamp = DateTime(timestamp).replace(second=0, delta_minute=+1)
        while not self.is_valid(timestamp):
            timestamp = timestamp.replace(delta_minute=+1)
        return timestamp.datetime()
