# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from openerp.osv import fields, osv

class account_cdr_report(osv.osv_memory):
    _name = 'account.cdr.report'
    _description = 'Account CDR Report'

    def _get_defaults(self, cr, uid, context=None):
        fiscalyear_id = self.pool.get('account.fiscalyear').find(cr, uid)
        return fiscalyear_id

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
    }

    _defaults = {
        'fiscalyear_id': _get_defaults
    }

    def print_cdr_report(self, cr, uid, ids, context=None):
        active_ids = context.get('active_ids', [])
        data = {}
        data['form'] = {}
        data['ids'] = active_ids
        data['form']['fiscalyear_id'] = self.browse(cr, uid, ids)[0].fiscalyear_id.id
        return { 'type': 'ir.actions.report.xml', 'report_name': 'l10n.fr.compute_resultant', 'datas': data}

account_cdr_report()

