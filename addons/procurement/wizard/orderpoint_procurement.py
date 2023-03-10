# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

#
# Order Point Method:
#    - Order if the virtual stock of today is bellow the min of the defined order point
#

import threading
from openerp import pooler
from openerp.osv import fields,osv

class procurement_compute(osv.osv_memory):
    _name = 'procurement.orderpoint.compute'
    _description = 'Automatic Order Point'

    _columns = {
           'automatic': fields.boolean('Automatic Orderpoint', help='If the stock of a product is under 0, it will act like an orderpoint'),
    }

    _defaults = {
            'automatic': False,
    }

    def _procure_calculation_orderpoint(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        proc_obj = self.pool.get('procurement.order')
        #As this function is in a new thread, I need to open a new cursor, because the old one may be closed
        new_cr = pooler.get_db(cr.dbname).cursor()
        for proc in self.browse(new_cr, uid, ids, context=context):
            proc_obj._procure_orderpoint_confirm(new_cr, uid, automatic=proc.automatic, use_new_cursor=new_cr.dbname, context=context)
        #close the new cursor
        new_cr.close()
        return {}

    def procure_calculation(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint, args=(cr, uid, ids, context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}

procurement_compute()

