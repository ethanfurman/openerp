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
from unittest2 import main as Test, skip

@Script(
        conf=Spec('configuration file to use', OPTION, remove=True, default='/etc/openerp/server.conf'),
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
    Test()


class TestBaseCalendar(common.TransactionCase):
    # - only event owner should be able to make changes
    # - shared events should also share attendees
    # - shared events should share everything
    # - deleting an owned event should delete all matching
    #   shared events
    # - deleting shared event should mark that attendee as
    #   declining
    # - don't send external email to attendees that are OE
    #   users 
    def setUp(self):
        """*****setUp*****"""
        print('\n--== setting up ==--', verbose=2)
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
        vals = res_users._add_missing_default_values(cr ,uid, {'login':'calendar_user1', 'name':'Calendar User I'})
        test_uid1 = res_users.create(cr, uid, vals)
        test_pid1 = res_users.browse(cr, uid, test_uid1, context).partner_id.id
        vals.update(login='calendar_user2', name='Calendar User II')
        test_uid2 = res_users.create(cr, uid, vals)
        test_pid2 = res_users.browse(cr, uid, test_uid2, context).partner_id.id
        # inject locals into self
        for k, v in locals().items():
            setattr(self, k, v)

    def tearDown(self):
        print('--== tearing down ==--\n', verbose=2)
        super(TestBaseCalendar, self).tearDown()

    def _create(self, model, cr, uid, values, context=None):
        values = model._add_missing_default_values(cr, uid, values)
        return model.create(cr, uid, values, context)

    def test_simple_create(self, partner_ids=None):
        """creating user should end up in partner_ids (Attendees)"""
        cr, uid, context = self.cr, self.uid, self.context
        vals = dict(
                name='Lunch Break',
                description='Time for some yummy hot food',
                date=self.lunch_time,
                )
        vals['partner_ids'] = [(6, False, partner_ids or [])]
        vals.update(self.calendar_event.onchange_dates(cr, uid, None, vals['date'], context=context)['value'])
        event_id = self._create(self.calendar_event, cr, self.test_uid1, vals, context=context)
        event = self.calendar_event.browse(cr, uid, event_id, context)
        self.assertEqual(event.user_id.id, self.test_uid1)
        self.assertEqual(event.date, self.lunch_time)
        self.assertEqual(len(event.partner_ids), 1+len(partner_ids or []))
        self.assertIn(self.test_pid1, [p.id for p in event.partner_ids])
        return event

    def test_single_invite_create(self):
        cr, uid, context = self.cr, self.uid, self.context
        event = self.test_simple_create(partner_ids=[self.test_pid2])
        partner_ids = [p.id for p in event.partner_ids]
        self.assertIn(self.test_pid1, partner_ids)
        self.assertIn(self.test_pid2, partner_ids)
        return event

    @skip(True)
    def test_unallowed_changes(self):
        pass

    @skip(True)
    def test_shared_events_share_attendees(self):
        pass

    @skip(True)
    def test_shared_events_have_same_data(self):
        pass

    @skip(True)
    def test_shared_events_do_not_share_alarms(self):
        pass

    @skip(True)
    def test_delete_master_event_deletes_all_events(self):
        pass

    @skip(True)
    def test_delete_shared_event_declines_invite(self):
        pass



Main()
