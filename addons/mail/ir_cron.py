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
        super(ir_cron, self)._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, job_name, job_type, job_exception)
        cr.execute("SELECT user_id FROM cron_notify_rel WHERE job_id=%s", (job_id, ))
        notify_ids = [r[0] for r in cr.fetchall()]
        if notify_ids:
            subject = 'Failed Job: ' + job_name
            message = '\n'.join(['<pre>%s</pre>' % line for line in traceback.format_exc(job_exception).split('\n')])
            res_users = self.pool.get('res.users')
            res_users.message_notify(cr, SUPERUSER_ID, notify_ids, subject=subject, message=message, model=self._name, res_id=job_id)

    def _check_paused_jobs(self, cr, uid, arg=None, context=None):
        """Send reminder for paused jobs."""
        try:
            # get web url
            cr.execute("SELECT value FROM ir_config_parameter WHERE key='web.base.url'")
            web_url = cr.dictfetchall()[0]['value']
            # check for inactive jobs that require a reminder
            cr.execute("""SELECT id FROM ir_cron
                          WHERE numbercall != 0
                              AND mail_paused
                          ORDER BY priority""")
            reminder_job_ids = [d['id'] for d in cr.dictfetchall()]
            reminder_jobs = self.read(
                    cr, uid,
                    reminder_job_ids,
                    fields=['id','mail_notify_ids','mail_inactive_start','name'],
                    context=context,
                    )
        except Exception:
            _logger.error('Exception in cron:', exc_info=True)
            raise
        # send in-system emails
        mail_message = self.pool.get('mail.message')
        res_users = self.pool.get('res.users')
        if mail_message is None or res_users is None:
            return False
        result = []
        for inactive_job in reminder_jobs:
            result.append('%s - %s' % (inactive_job['id'], inactive_job['name']))
            # transform user-based notify_ids to partner ids
            notify_ids = [
                    r['partner_id'][0]
                    for r in res_users.read(
                            cr, uid,
                            inactive_job['mail_notify_ids'],
                            context=context,
                            )]
            try:
                # Try to grab an exclusive lock on the job row from within the task transaction
                cr.execute("""SELECT id, name
                                   FROM ir_cron
                                   WHERE id=%s
                                   FOR UPDATE NOWAIT""",
                               (inactive_job['id'],),
                               log_exceptions=False,
                               )
                # send email
                values = {
                    'type': 'email',
                    'email_from': 'Cron Scheduler',
                    'author_id': 1,
                    'model': 'ir.cron',
                    'res_id': inactive_job['id'],
                    'partner_ids': [(6, 0, notify_ids)],
                    'subject': 'Inactive job',
                    'body': 'Job %s (%s/#model=ir.cron&id=%s) has been paused since %s'
                            % (
                                inactive_job['name'],
                                web_url,
                                inactive_job['id'],
                                fields.datetime.context_timestamp(
                                    cr, uid,
                                    timestamp=inactive_job['mail_inactive_start'],
                                    context=context,
                                    ),
                                ),
                    }
                mail_message.create(cr, 1, values, context=context)
            except Exception:
                _logger.error('Exception in cron:', exc_info=True)
                raise
        return '\n'.join(result)

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
