#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from scription import *
import openerp
import openerp.osv
from openerp.osv.osv import except_osv as ERPError
from openerp.tools import config
from openerp.tests import common
from openerp.addons.fnx import Date, Time, DateTime
import time
import unittest2

@Script(
        conf=Spec('configuration file to use', OPTION, remove=True),
        tests=Spec('tests to run', OPTION),
        )
def main(conf, *tests):
    config.parse_config(['--conf', conf])
    # inject the configure values back in to openerp.common
    common.ADDONS_PATH = config['addons_path']
    common.PORT = config['xmlrpc_port']
    common.DB = config['db_name']
    common.HOST = '127.0.0.1'
    common.ADMIN_USER = 'admin'
    common.ADMIN_USER_ID = openerp.SUPERUSER_ID
    common.ADMIN_PASSWORD = config['admin_passwd']


@Command()
@Alias('test_base_calendar.py')
def test_base_calendar():
    unittest2.main()


class TestBaseCalendar(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        print('\n--== setting up ==--')
        super(TestBaseCalendar, self).setUp()
        cr, uid, registry = self.cr, self.uid, self.registry
        context = {}
        res_partner = registry('res.partner')
        res_users = registry('res.users')
        res_groups = registry('res.groups')
        ir_model_data = registry('ir.model.data')
        mail_message = registry('mail.message')
        calendar_event = registry('calendar.event')
        calendar_attendee = registry('calendar.attendee')
        lunch_time = DateTime.combine(Date.today(), Time(21)).strftime("%Y-%m-%d %H:%M:%S") # noonish PST
        vals = res_users._add_missing_default_values(cr ,uid, {'login':'calendar_user', 'name':'Calendar User I'})
        test_uid = res_users.create(cr, uid, vals)
        test_pid = res_users.browse(cr, uid, test_uid, context).partner_id.id
        # inject locals into self
        for k, v in locals().items():
            setattr(self, k, v)

    def tearDown(self):
        print('--== tearing down ==--\n')
        super(TestBaseCalendar, self).tearDown()

    def _create(self, model, cr, uid, values, context=None):
        values = model._add_missing_default_values(cr, uid, values)
        return model.create(cr, uid, values, context)

    def test_simple_create(self):
        """creating user should end up in partner_ids (Attendees)"""
        cr, uid, context = self.cr, self.uid, self.context
        vals = dict(
                name='Lunch Break',
                description='Time for some yummy hot food',
                date=self.lunch_time,
                )
        vals.update(self.calendar_event.onchange_dates(cr, uid, None, vals['date'], context=context)['value'])
        event_id = self._create(self.calendar_event, cr, self.test_uid, vals, context=context)
        event = self.calendar_event.browse(cr, uid, event_id, context)
        self.assertEqual(event.date, self.lunch_time)
        self.assertEqual(len(event.partner_ids), 1)
        self.assertEqual(event.partner_ids[0].id, self.test_pid)


Main()
