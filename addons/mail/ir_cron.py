import logging
import traceback

from openerp.osv import fields, osv
from openerp.tools import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ir_cron(osv.Model):
    _name = 'ir.cron'
    _inherit = 'ir.cron'

    _columns = {
        'mail_notify_ids': fields.many2many(
            'res.users', 'cron_notify_rel', 'job_id', 'user_id',
            string='Notify',
            domain=[('groups_id','=',fields.ref('base.group_system'))],
            oldname='notify_ids',
            ),
        'mail_paused': fields.boolean('send in-system email if job inactive'),
        'mail_inactive_start': fields.datetime('last time email reminder was sent'),
        }

    def _handle_callback_exception(self, cr, uid, model_name, method_name, args, job_id, job_name, job_type, job_exception):
        """
        After super logs the exception and rollsback, send an email to anyone in notify_ids.
        """
        super(ir_cron, self)._handle_callback_exception(cr, SUPERUSER_ID, model_name, method_name, args, job_id, job_name, job_type, job_exception)
        exc_lines = traceback.format_exc(job_exception).split('\n')
        exc_lines[1:-2] = ['...']
        body = '\n'.join(exc_lines)
        self._mail_cron_results(cr, SUPERUSER_ID, job_id, 'Failed job: %s' % (job_name, ), body)

    def _callback(self, cr, uid, model_name, method_name, args, job_id, job_name, job_type, job_timeout):
        "mail job report if error detected in results"
        result = super(ir_cron, self)._callback(
                cr, uid,
                model_name, method_name,
                args, job_id, job_name, job_type, job_timeout,
                )
        lines = result.split('\n')
        if len(lines) > 2:
            # look for error output
            if (
                       '======\nstderr\n======' in result
                    or '======\nrmtree\n======' in result
                    or 'TIMEOUT' in result
                ):
                self._mail_cron_results(
                        cr, SUPERUSER_ID,
                        job_id,
                        "Errors in job: %s" % (job_name, ),
                        ' '.join(args) + '\n'.join(lines[4:]),
                        )
        return result

    def _check_paused_jobs(self, cr, uid, arg=None, context=None):
        """Send reminder for paused jobs."""
        try:
            # check for inactive jobs that require a reminder
            cr.execute("""SELECT id FROM ir_cron
                          WHERE numbercall != 0
                              AND mail_paused
                          ORDER BY priority""")
            reminder_job_ids = [d['id'] for d in cr.dictfetchall()]
            reminder_jobs = self.read(
                    cr, SUPERUSER_ID,
                    reminder_job_ids,
                    fields=['id','mail_inactive_start','name'],
                    context=context,
                    )
            result = ['Paused jobs:', '===========']
            for inactive_job in reminder_jobs:
                result.append('%4d:  %s' % (inactive_job['id'], inactive_job['name']))
                pause_date = fields.datetime.context_timestamp(
                        cr, SUPERUSER_ID,
                        timestamp=inactive_job['mail_inactive_start'],
                        context=context,
                        )
                body = 'This job has been paused since %s' % pause_date
                # Try to grab an exclusive lock on the job row from within the task transaction
                cr.execute("""SELECT id, name
                                   FROM ir_cron
                                   WHERE id=%s
                                   FOR UPDATE NOWAIT""",
                               (inactive_job['id'],),
                               log_exceptions=False,
                               )
                self._mail_cron_results(
                        cr, SUPERUSER_ID,
                        inactive_job['id'],
                        'Inactive job: %s' % (inactive_job['name'], ),
                        body,
                        context=context,
                        )
        except Exception:
            _logger.error('Exception in cron:', exc_info=True)
            raise

        if len(result) == 2:
            result = []
        return '\n'.join(result)


    def _mail_cron_results(self, cr, uid, job_id, subject, body, context=None):
        # get needed tables and job
        mail_message = self.pool.get('mail.message')
        res_users = self.pool.get('res.users')
        job = self.read(cr, uid, job_id, fields=['id','mail_notify_ids'], context=context)
        # send in-system emails
        if mail_message is None or res_users is None:
            return False
        # transform user-based notify_ids to partner ids
        notify_ids = [
                r['partner_id'][0]
                for r in res_users.read(
                        cr, uid,
                        job['mail_notify_ids'],
                        context=context,
                        )]
        if not notify_ids:
            # nobody listed?  log an error
            _logger.error('no recipients listed for job %s:\n\tsubject: %s\n\t%s', job_id, subject, body)
            return False
        else:
            # send email
            body = '<pre>' + body + '</pre>'
            values = {
                'type': 'email',
                'email_from': 'Cron Scheduler',
                'author_id': 1,
                'model': 'ir.cron',
                'res_id': job_id,
                'partner_ids': [(6, 0, notify_ids)],
                'subject': subject,
                'body': body,
                }
            return mail_message.create(cr, 1, values, context=context)

    def button_pause(self, cr, uid, ids, context=None):
        return self.write(
            cr, uid, ids,
            {
                'mail_paused': True,
                'mail_inactive_start': fields.datetime.now(self, cr),
                'active':False,
                }
            )

    def button_resume(self, cr, uid, ids, context=None):
        return self.write(
            cr, uid, ids,
            {
                'mail_paused': False,
                'mail_inactive_start': False,
                'active': True,
                }
            )
