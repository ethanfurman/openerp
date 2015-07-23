import logging
import threading
import time
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta
import traceback

import openerp
from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, SUPERUSER_ID
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class ir_cron(osv.Model):
    _name = 'ir.cron'
    _inherit = 'ir.cron'
     
    _columns = {
        'notify_ids': fields.many2many(
            'res.users',
            'cron_notify_rel',
            'job_id',
            'user_id',
            string='Notify if errors',
            ),
        }

    def _handle_callback_exception(self, cr, uid, model_name, method_name, args, job_id, job_name, job_exception):
        """
        After super logs the exception and rollsback, send an email to anyone in notify_ids.
        """
        super(ir_cron, self)._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, job_name, job_exception)
        cr.execute("SELECT user_id FROM cron_notify_rel WHERE job_id=%s", (job_id, ))
        notify_ids = [r[0] for r in cr.fetchall()]
        if notify_ids:
            subject = 'Failed Job: ' + job_name
            message = '\n'.join(['<pre>%s</pre>' % line for line in traceback.format_exc(job_exception).split('\n')])
            res_users = self.pool.get('res.users')
            res_users.message_notify(cr, SUPERUSER_ID, notify_ids, subject, message)

    def onchange_user_ids(self, cr, uid, ids, value, context=None):
        """
        The basic purpose of this method is to check that destination users
        effectively have email addresses. Otherwise a warning is thrown.
        :param value: value format: [[6, 0, [3, 4]]]
        """
        res = {'value': {}}
        if not value or not value[0] or not value[0][0] == 6:
            return
        res.update(self.pool.get('res.users').check_email(cr, uid, value[0][2], context=context))
        return res
