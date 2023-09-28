# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields,osv

class ir_exports(osv.osv):
    _name = "ir.exports"
    _order = 'name'
    _columns = {
        'name': fields.char('Export Name', size=128),
        'resource': fields.char('Resource', size=128, select=True),
        'export_fields': fields.one2many('ir.exports.line', 'export_id',
                                         'Export ID'),
    }
ir_exports()


class ir_exports_line(osv.osv):
    _name = 'ir.exports.line'
    _order = 'id'
    _columns = {
        'name': fields.char('Field Name', size=64),
        'export_id': fields.many2one('ir.exports', 'Export', select=True, ondelete='cascade'),
    }
ir_exports_line()


class ir_exports_export(osv.osv_memory):
    _name = "ir.exports.export"
    _rec_name = 'id'
    _columns = {
        'export_id': fields.many2one('ir.exports', 'Saved Export', required=True),
        'model': fields.related('export_id', 'resource', string='Model', type='char', size=128),
        'export_fields': fields.related(
                'export_id', 'export_fields',
                string='Fields',
                type='one2many',
                obj='ir.exports.line', fields_id='export_id'
                ),
        'selection_id': fields.many2one('ir.filters', 'Saved Filter', required=True),
        'domain': fields.text('Domain'),
        'user_id': fields.related('selection_id', 'user_id', string='Private to', type='many2one', obj='res.users'),
        'is_default': fields.related('selection_id', 'is_default', string='Default Filter', type='boolean'),
        }

    _defaults = {
        }

    def create_csv(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.report.xml', 'report_name': 'base.csv_export', 'datas': {}, 'nodestroy': True}

    def onchange_export(self, cr, uid, ids, export_id, context=None):
        res = {}
        value = res['value'] = {}
        domain = res['domain'] = {}
        export = self.pool.get('ir.exports').read(cr, uid, export_id, context=context)
        value['model'] = model = export['resource']
        value['export_fields'] = export['export_fields']
        domain['selection_id'] = domain = [('model_id','=',model),('user_id','in',[False, uid])]
        filters = self.pool.get('ir.filters').read(cr, uid, domain, context=context)
        for f in filters:
            if f['is_default']:
                value['selection_id'] = f['id']
                break
        return res

    def onchange_selection(self, cr, uid, ids, selection_id, context=None):
        res = {'domain': {}}
        value = res['value'] = {}
        filter = self.pool.get('ir.filters').read(cr, uid, selection_id, context=context)
        value['domain'] = filter['domain']
        value['is_default'] = filter['is_default']
        value['user_id'] = filter['user_id']
        return res


from openerp import pooler
from openerp.report.interface import report_int
from openerp.report.render import render


class external_csv(render):
    #
    def __init__(self, csv):
        render.__init__(self)
        self.csv = csv
        self.output_type='csv'
    #
    def _render(self):
        return self.csv.encode('utf-8')


class report_spec_sheet(report_int):

    def create(self, cr, uid, ids, datas, context=None):
        if context is None:
            context = {}
        #
        pool = pooler.get_pool(cr.dbname)
        iee = pool.get('ir.exports.export')
        #
        export_rec = iee.read(cr, uid, ids[0], context=context)
        export_rec = iee.browse(cr, uid, ids[0], context=context)
        export_model = pool.get(export_rec.model)
        export_fields = [f.name for f in export_rec.export_fields]
        export_domain = eval(export_rec.domain)
        self._filename = export_rec.export_id.name.replace(' ','_')
        #
        data_records = export_model.read(cr, uid, export_domain, fields=export_fields, context=context)
        data = [','.join(export_fields)]
        for rec in data_records:
            line = []
            for f in export_fields:
                v = rec[f]
                if not v:
                    line.append('')
                else:
                    if isinstance(v, basestring):
                        line.append('"' + v.replace('"','""') + '"')
                    else:
                        line.append(repr(v))
            data.append(','.join(line))
        #
        self.obj = external_csv('\n'.join(data))
        self.obj.render()
        return (self.obj.csv, 'csv')
report_spec_sheet('report.base.csv_export')


