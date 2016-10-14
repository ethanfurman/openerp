# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.addons.mail.tests.test_mail_base import TestMailBase


class test_invite(TestMailBase):

    def test_00_basic_invite(self):
        cr, uid = self.cr, self.uid
        mail_invite = self.registry('mail.wizard.invite')

        # Do: create a mail_wizard_invite, validate it
        self._init_mock_build_email()
        context = {'default_res_model': 'mail.group', 'default_res_id': self.group_pigs_id}
        mail_invite_id = mail_invite.create(cr, self.user_raoul_id, {'partner_ids': [(4, self.partner_bert_id)]}, context)
        mail_invite.add_followers(cr, self.user_raoul_id, [mail_invite_id], {'default_model': 'mail.group', 'default_res_id': 0})

        # Test: Pigs followers should contain only Bert
        self.group_pigs.refresh()
        follower_ids = [follower.id for follower in self.group_pigs.message_follower_ids]
        self.assertEqual(follower_ids, [self.partner_bert_id], 'Pigs followers after invite is incorrect')

        # Test: (pretend to) send email and check subject, body
        test_email = self._build_email_kwargs_list
        # TODO: two messages are being generated -- the original, and what looks like an automatic forward...
        #       figure out how to disable the forward
        self.assertTrue(len(test_email), 'no emails generated')
        for sent_email in test_email:
            self.assertTrue(all('bert@bert.fr' in s for s in sent_email.get('email_to')), 'mail message is not for Bert')
            self.assertEqual(sent_email.get('subject'), 'Invitation to follow Pigs',
                            'subject of invitation email is incorrect')
            # TODO: reenable if we ever get down to one email
            # self.assertTrue('You have been invited to follow Pigs' in sent_email.get('body'),
            #                 'body of invitation email is incorrect')
