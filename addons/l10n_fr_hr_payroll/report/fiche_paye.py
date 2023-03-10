#!/usr/bin/env python
#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp.report import report_sxw

class fiche_paye_parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(fiche_paye_parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_payslip_lines': self.get_payslip_lines,
            'get_total_by_rule_category': self.get_total_by_rule_category,
            'get_employer_line': self.get_employer_line,
        })

    def get_payslip_lines(self, objs):
        payslip_line = self.pool.get('hr.payslip.line')
        res = []
        ids = []
        for item in objs:
            if item.appears_on_payslip == True and not item.salary_rule_id.parent_rule_id :
                ids.append(item.id)
        if ids:
            res = payslip_line.browse(self.cr, self.uid, ids)
        return res


    def get_total_by_rule_category(self, obj, code):
        payslip_line = self.pool.get('hr.payslip.line')
        rule_cate_obj = self.pool.get('hr.salary.rule.category')

        cate_ids = rule_cate_obj.search(self.cr, self.uid, [('code', '=', code)])

        category_total = 0
        if cate_ids:
            line_ids = payslip_line.search(self.cr, self.uid, [('slip_id', '=', obj.id),('category_id.id', '=', cate_ids[0] )])
            for line in payslip_line.browse(self.cr, self.uid, line_ids):
                 category_total += line.total

        return category_total


    def get_employer_line(self, obj, parent_line):

        payslip_line = self.pool.get('hr.payslip.line')

        line_ids = payslip_line.search(self.cr, self.uid, [('slip_id', '=', obj.id), ('salary_rule_id.parent_rule_id.id', '=', parent_line.salary_rule_id.id )])
        res = line_ids and payslip_line.browse(self.cr, self.uid, line_ids[0]) or False

        return res


report_sxw.report_sxw('report.fiche.paye', 'hr.payslip', 'l10n_fr_hr_payroll/report/fiche_paye.rml', parser=fiche_paye_parser)

