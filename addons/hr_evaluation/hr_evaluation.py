# -*- encoding: utf-8 -*-
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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from textwrap import dedent

class hr_evaluation_plan(osv.osv):
    _name = "hr_evaluation.plan"
    _description = "Appraisal Plan"
    _columns = {
        'name': fields.char("Appraisal Plan", size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'phase_ids': fields.one2many('hr_evaluation.plan.phase', 'plan_id', 'Appraisal Phases'),
        'month_first': fields.integer('First Appraisal in (months)', help="This number of months will be used to schedule the first evaluation date of the employee when selecting an evaluation plan. "),
        'month_next': fields.integer('Periodicity of Appraisal (months)', help="The number of month that depicts the delay between each evaluation of this plan (after the first one)."),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active': True,
        'month_first': 6,
        'month_next': 12,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

hr_evaluation_plan()

class hr_evaluation_plan_phase(osv.osv):
    _name = "hr_evaluation.plan.phase"
    _description = "Appraisal Plan Phase"
    _order = "sequence"
    _columns = {
        'name': fields.char("Phase", size=64, required=True),
        'sequence': fields.integer("Sequence"),
        'company_id': fields.related('plan_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'plan_id': fields.many2one('hr_evaluation.plan','Appraisal Plan', ondelete='cascade'),
        'action': fields.selection([
            ('top-down','Top-Down Appraisal Requests'),
            ('bottom-up','Bottom-Up Appraisal Requests'),
            ('self','Self Appraisal Requests'),
            ('final','Final Interview')], 'Action', required=True),
        'survey_id': fields.many2one('survey','Appraisal Form',required=True),
        'send_answer_manager': fields.boolean('All Answers',
            help="Send all answers to the manager"),
        'send_answer_employee': fields.boolean('All Answers',
            help="Send all answers to the employee"),
        'send_anonymous_manager': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the manager"),
        'send_anonymous_employee': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the employee"),
        'wait': fields.boolean('Wait Previous Phases',
            help="Check this box if you want to wait that all preceding phases " +
              "are finished before launching this phase."),
        'mail_feature': fields.boolean('Send mail for this phase', help="Check this box if you want to send mail to employees"+
                                       " coming under this phase"),
        'mail_body': fields.text('Email'),
        'email_subject':fields.text('char')
    }
    _defaults = {
        'sequence': 1,
        'email_subject': _('''Regarding '''),
        'mail_body': lambda *a:_(dedent('''\
                Date: %(date)s

                Dear %(employee_name)s,

                I am doing an evaluation regarding %(eval_name)s.

                Kindly submit your response.


                Thanks,
                --
                %(user_signature)s

                        ''')),
    }

hr_evaluation_plan_phase()

class hr_employee(osv.osv):
    _name = "hr.employee"
    _inherit="hr.employee"
    _columns = {
        'evaluation_plan_id': fields.many2one('hr_evaluation.plan', 'Appraisal Plan'),
        'evaluation_date': fields.date('Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity)."),
    }
    def run_employee_evaluation(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        now = parser.parse(datetime.now().strftime('%Y-%m-%d'))
        obj_evaluation = self.pool.get('hr_evaluation.evaluation')
        emp_ids =self.search(cr, uid, [ ('evaluation_plan_id','<>',False), ('evaluation_date','=', False)], context=context)
        for emp in self.browse(cr, uid, emp_ids, context=context):
            first_date = (now+ relativedelta(months=emp.evaluation_plan_id.month_first)).strftime('%Y-%m-%d')
            self.write(cr, uid, [emp.id], {'evaluation_date': first_date}, context=context)

        emp_ids =self.search(cr, uid, [
            ('evaluation_plan_id','<>',False), ('evaluation_date','<=', time.strftime("%Y-%m-%d")),
            ], context=context)
        for emp in self.browse(cr, uid, emp_ids, context=context):
            next_date = (now + relativedelta(months=emp.evaluation_plan_id.month_next)).strftime('%Y-%m-%d')
            self.write(cr, uid, [emp.id], {'evaluation_date': next_date}, context=context)
            plan_id = obj_evaluation.create(cr, uid, {'employee_id': emp.id, 'plan_id': emp.evaluation_plan_id.id}, context=context)
            obj_evaluation.button_plan_in_progress(cr, uid, [plan_id], context=context)
        return True

class hr_evaluation(osv.osv):
    _name = "hr_evaluation.evaluation"
    _inherit = "mail.thread"
    _description = "Employee Appraisal"
    _rec_name = 'employee_id'
    _columns = {
        'date': fields.date("Appraisal Deadline", required=True, select=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'note_summary': fields.text('Appraisal Summary'),
        'note_action': fields.text('Action Plan',
            help="If the evaluation does not meet the expectations, you can propose"+
              "an action plan"),
        'rating': fields.selection([
            ('0','Significantly bellow expectations'),
            ('1','Did not meet expectations'),
            ('2','Meet expectations'),
            ('3','Exceeds expectations'),
            ('4','Significantly exceeds expectations'),
        ], "Appreciation", help="This is the appreciation on which the evaluation is summarized."),
        'survey_request_ids': fields.one2many('hr.evaluation.interview','evaluation_id','Appraisal Forms'),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', required=True),
        'state': fields.selection([
            ('draft','New'),
            ('cancel','Cancelled'),
            ('wait','Plan In Progress'),
            ('progress','Waiting Appreciation'),
            ('done','Done'),
        ], 'Status', required=True, readonly=True),
        'date_close': fields.date('Ending Date', select=True),
    }
    _defaults = {
        'date': lambda *a: (parser.parse(datetime.now().strftime('%Y-%m-%d')) + relativedelta(months =+ 1)).strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.plan_id.name
            res.append((record['id'], name))
        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        vals = {}
        vals['plan_id'] = False
        if employee_id:
            employee_obj = self.pool.get('hr.employee')
            for employee in employee_obj.browse(cr, uid, [employee_id], context=context):
                if employee and employee.evaluation_plan_id and employee.evaluation_plan_id.id:
                    vals.update({'plan_id': employee.evaluation_plan_id.id})
        return {'value': vals}

    def button_plan_in_progress(self, cr, uid, ids, context=None):
        mail_message = self.pool.get('mail.message')
        hr_eval_inter_obj = self.pool.get('hr.evaluation.interview')
        if context is None:
            context = {}
        for evaluation in self.browse(cr, uid, ids, context=context):
            wait = False
            for phase in evaluation.plan_id.phase_ids:
                children = []
                if phase.action == "bottom-up":
                    children = evaluation.employee_id.child_ids
                elif phase.action in ("top-down", "final"):
                    if evaluation.employee_id.parent_id:
                        children = [evaluation.employee_id.parent_id]
                elif phase.action == "self":
                    children = [evaluation.employee_id]
                for child in children:

                    int_id = hr_eval_inter_obj.create(cr, uid, {
                        'evaluation_id': evaluation.id,
                        'survey_id': phase.survey_id.id,
                        'date_deadline': (parser.parse(datetime.now().strftime('%Y-%m-%d')) + relativedelta(months =+ 1)).strftime('%Y-%m-%d'),
                        'user_id': child.user_id.id,
                        'user_to_review_id': evaluation.employee_id.id
                    }, context=context)
                    if phase.wait:
                        wait = True
                    if not wait:
                        hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [int_id], context=context)

                    if (not wait) and phase.mail_feature:
                        body = phase.mail_body % {'employee_name': child.name, 'user_signature': child.user_id.signature,
                            'eval_name': phase.survey_id.title, 'date': time.strftime('%Y-%m-%d'), 'time': time }
                        sub = phase.email_subject
                        if child.work_email:
                            vals = {'state': 'outgoing',
                                    'subject': sub,
                                    'body_html': '<pre>%s</pre>' % body,
                                    'email_to': child.work_email,
                                    'email_from': evaluation.employee_id.work_email}
                            self.pool.get('mail.mail').create(cr, uid, vals, context=context)

        self.write(cr, uid, ids, {'state':'wait'}, context=context)
        return True

    def button_final_validation(self, cr, uid, ids, context=None):
        request_obj = self.pool.get('hr.evaluation.interview')
        self.write(cr, uid, ids, {'state':'progress'}, context=context)
        for evaluation in self.browse(cr, uid, ids, context=context):
            if evaluation.employee_id and evaluation.employee_id.parent_id and evaluation.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [evaluation.id], user_ids=[evaluation.employee_id.parent_id.user_id.id], context=context)
            if len(evaluation.survey_request_ids) != len(request_obj.search(cr, uid, [('evaluation_id', '=', evaluation.id),('state', 'in', ['done','cancel'])], context=context)):
                raise osv.except_osv(_('Warning!'),_("You cannot change state, because some appraisal(s) are in waiting answer or draft state."))
        return True

    def button_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'state':'done', 'date_close': time.strftime('%Y-%m-%d')}, context=context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        interview_obj=self.pool.get('hr.evaluation.interview')
        evaluation = self.browse(cr, uid, ids[0], context)
        interview_obj.survey_req_cancel(cr, uid, [r.id for r in evaluation.survey_request_ids])
        self.write(cr, uid, ids,{'state':'cancel'}, context=context)
        return True

    def button_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'state': 'draft'}, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        default = default.copy()
        default['survey_request_ids'] = []
        return super(hr_evaluation, self).copy(cr, uid, id, default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('employee_id'):
            employee_id = self.pool.get('hr.employee').browse(cr, uid, vals.get('employee_id'), context=context)
            if employee_id.parent_id and employee_id.parent_id.user_id:
                vals['message_follower_ids'] = [(4, employee_id.parent_id.user_id.partner_id.id)]
        if 'date' in vals:
            new_vals = {'date_deadline': vals.get('date')}
            obj_hr_eval_iterview = self.pool.get('hr.evaluation.interview')
            for evalutation in self.browse(cr, uid, ids, context=context):
                for survey_req in evalutation.survey_request_ids:
                    obj_hr_eval_iterview.write(cr, uid, [survey_req.id], new_vals, context=context)
        return super(hr_evaluation, self).write(cr, uid, ids, vals, context=context)

hr_evaluation()

class survey_request(osv.osv):
    _inherit = "survey.request"
    _columns = {
        'is_evaluation': fields.boolean('Is Appraisal?'),
    }

survey_request()

class hr_evaluation_interview(osv.osv):
    _name = 'hr.evaluation.interview'
    _inherits = {'survey.request': 'request_id'}
    _inherit =  'mail.thread'
    _rec_name = 'request_id'
    _description = 'Appraisal Interview'
    _columns = {
        'request_id': fields.many2one('survey.request','Request_id', ondelete='cascade', required=True),
        'user_to_review_id': fields.many2one('hr.employee', 'Employee to Interview'),
        'evaluation_id': fields.many2one('hr_evaluation.evaluation', 'Appraisal Form'),
    }
    _defaults = {
        'is_evaluation': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.request_id.survey_id.title
            res.append((record['id'], name))
        return res

    def survey_req_waiting_answer(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'state': 'waiting_answer'}, context=context)
        return True

    def survey_req_done(self, cr, uid, ids, context=None):
        hr_eval_obj = self.pool.get('hr_evaluation.evaluation')
        for id in self.browse(cr, uid, ids, context=context):
            flag = False
            wating_id = 0
            if not id.evaluation_id.id:
                raise osv.except_osv(_('Warning!'),_("You cannot start evaluation without Appraisal."))
            records = hr_eval_obj.browse(cr, uid, [id.evaluation_id.id], context=context)[0].survey_request_ids
            for child in records:
                if child.state == "draft":
                    wating_id = child.id
                    continue
                if child.state != "done":
                    flag = True
            if not flag and wating_id:
                self.survey_req_waiting_answer(cr, uid, [wating_id], context=context)
        self.write(cr, uid, ids, { 'state': 'done'}, context=context)
        return True

    def survey_req_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'state': 'draft'}, context=context)
        return True

    def survey_req_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'state': 'cancel'}, context=context)
        return True

    def action_print_survey(self, cr, uid, ids, context=None):
        """
        If response is available then print this response otherwise print survey form(print template of the survey).

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value for print survey form.
        """
        if context is None:
            context = {}
        record = self.browse(cr, uid, ids, context=context)
        record = record and record[0]
        context.update({'survey_id': record.survey_id.id, 'response_id': [record.response.id], 'response_no':0,})
        value = self.pool.get("survey").action_print_survey(cr, uid, ids, context=context)
        return value

hr_evaluation_interview()

