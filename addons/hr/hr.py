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

# imports
from openerp import addons
import logging
from openerp.osv import fields, osv
from openerp.osv.osv import except_osv
from openerp import tools, SUPERUSER_ID
from selections import *
_logger = logging.getLogger(__name__)

# tables

class hr_employee_category(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _name = "hr.employee.category"
    _description = "Employee Category"
    _columns = {
        'name': fields.char("Category", size=64, required=True),
        'complete_name': fields.function(
            _name_get_fnc,
            type="char",
            string='Name',
            store={
                'hr.employee.category': (lambda kt, cr, uid, ids, ctx=None: ids, ['name', 'parent_id'], 10),
                },
            ),
        'parent_id': fields.many2one('hr.employee.category', 'Parent Category', select=True),
        'child_ids': fields.one2many('hr.employee.category', 'parent_id', 'Child Categories'),
        'employee_ids': fields.many2many('hr.employee', 'employee_category_rel', 'category_id', 'emp_id', 'Employees'),
        }

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from hr_employee_category where id IN %s', (tuple(ids), ))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error! You cannot create recursive Categories.', ['parent_id'])
        ]


class hr_employee_issue(osv.osv):
    _name = 'hr.employee.issue'
    _description = 'employee issue'
    _inherit = []

    _columns = {
        'name': fields.related(
                'hr.employee.issue.employee_id', 'hr.employee.resource_id', 'resource.resource.name',
                readonly=True, store=True, type='char', size=128,
                ),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'reporter_id': fields.many2one('res.users', 'Reported by'),
        'create_date': fields.datetime('Created', readonly=True),
        'description': fields.text('Description'),
        'description_pad': fields.char('Description PAD', pad_content_field='description'),
        }

    _defaults = {
        'create_date': fields.datetime.now,
        }


class hr_job(osv.osv):
    _name = "hr.job"
    _description = "Job Description"
    _inherit = ['mail.thread']

    def _no_of_employee(self, cr, uid, ids, name, args, context=None):
        res = {}
        for job in self.browse(cr, uid, ids, context=context):
            nb_employees = len(job.employee_ids or [])
            res[job.id] = {
                'no_of_employee': nb_employees,
                'expected_employees': nb_employees + job.no_of_recruitment,
            }
        return res

    def _get_job_position(self, cr, uid, ids, context=None):
        res = []
        for employee in self.pool.get('hr.employee').browse(cr, uid, ids, context=context):
            if employee.job_id:
                res.append(employee.job_id.id)
        return res

    _columns = {
        'name': fields.char('Job Name', size=128, required=True, select=True),
        'expected_employees': fields.function(_no_of_employee, string='Total Forecasted Employees',
            type='float', digits=(16,2),
            help='Expected number of employees for this job position after new recruitment.',
            store = {
                'hr.job': (lambda self,cr,uid,ids,c=None: ids, ['no_of_recruitment'], 10),
                'hr.employee': (_get_job_position, ['job_id'], 10),
            },
            multi='no_of_employee'),
        'no_of_employee': fields.function(_no_of_employee, string="Current Number of Employees",
            type='float', digits=(16,2),
            help='Number of employees currently occupying this job position.',
            store = {
                'hr.employee': (_get_job_position, ['job_id'], 10),
            },
            multi='no_of_employee'),
        'no_of_recruitment': fields.float('Expected in Recruitment', help='Number of new employees you expect to recruit.'),
        'employee_ids': fields.one2many('hr.employee', 'job_id', 'Employees', groups='base.group_user'),
        'description': fields.text('Job Description'),
        'requirements': fields.text('Requirements'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'company_id': fields.many2one('res.company', 'Company'),
        'state': fields.selection(JobState, 'Status', readonly=True, required=True,
            help="By default 'In position', set it to 'In Recruitment' if recruitment process is going on for this job position."),
        }
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.job', context=c),
        'state': 'open',
        }

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the job position must be unique per company!'),
        ]


    def on_change_expected_employee(self, cr, uid, ids, no_of_recruitment, no_of_employee, context=None):
        if context is None:
            context = {}
        return {'value': {'expected_employees': no_of_recruitment + no_of_employee}}

    def job_recruitement(self, cr, uid, ids, *args):
        for job in self.browse(cr, uid, ids):
            no_of_recruitment = job.no_of_recruitment == 0 and 1 or job.no_of_recruitment
            self.write(cr, SUPERUSER_ID, [job.id], {'state': 'recruit', 'no_of_recruitment': no_of_recruitment})
        return True

    def job_open(self, cr, uid, ids, *args):
        self.write(cr, SUPERUSER_ID, ids, {'state': 'open', 'no_of_recruitment': 0})
        return True

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _inherits = {'resource.resource': "resource_id"}
    _order='name_related'

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _calc_emp_typ_abbr(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for rec in self.browse(cr, uid, ids, context=context):
            result[rec.id] = EmploymentType[rec.employment_type].list_view_abbr
        return result

    _columns = {
        #we need a related field in order to be able to sort the employee by name
        'name_related': fields.related('resource_id', 'name', type='char', string='Name', readonly=True, store=True),
        'country_id': fields.many2one('res.country', 'Nationality'),
        'birthday': fields.date("Date of Birth"),
        'ssnid': fields.char('SSN No', size=32, help='Social Security Number'),
        'sinid': fields.char('SIN No', size=32, help="Social Insurance Number"),
        'identification_id': fields.char('Identification No', size=32),
        'otherid': fields.char('Other Id', size=64),
        'gender': fields.selection(Gender, 'Gender'),
        'marital': fields.selection(Marital, 'Marital Status'),
        'department_id':fields.many2one('hr.department', 'Department'),
        'partner_id': fields.many2one('res.partner', 'Partner Record'),
        'issue_ids': fields.one2many('hr.employee.issue', 'employee_id', 'Relations Issues'),
        #'address_home_id': fields.many2one('res.partner', 'Home Address'),
        'home_phone': fields.char('Phone', size=32),
        'home_mobile': fields.char('Mobile', size=32),
        'home_email': fields.char('Email', size=240),
        'home_street': fields.char('Street', size=128),
        'home_street2': fields.char('Street2', size=128),
        'home_zip': fields.char('Zip', change_default=True, size=24),
        'home_city': fields.char('City', size=128),
        'home_state_id': fields.many2one("res.country.state", 'State'),
        'home_country_id': fields.many2one('res.country', 'Country'),
        'emergency_contact': fields.char('Emergency Contact', size=240),
        'emergency_number': fields.char('Emergency Number', size=32),
        #'bank_account_id':fields.many2one('res.partner.bank', 'Bank Account Number', domain="[('partner_id','=',partner_id)]", help="Employee bank salary account"),
        'work_phone': fields.char('Work Phone', size=32, readonly=False),
        'mobile_phone': fields.char('Work Mobile', size=32, readonly=False),
        'work_email': fields.char('Work Email', size=240),
        'work_location': fields.char('Office Location', size=32),
        'notes': fields.text('Notes'),
        'parent_id': fields.many2one('hr.employee', 'Manager'),
        'category_ids': fields.many2many('hr.employee.category', 'employee_category_rel', 'emp_id', 'category_id', 'Tags'),
        'child_ids': fields.one2many('hr.employee', 'parent_id', 'Subordinates'),
        'resource_id': fields.many2one('resource.resource', 'Resource', ondelete='cascade', required=True),
        'coach_id': fields.many2one('hr.employee', 'Coach'),
        'job_id': fields.many2one('hr.job', 'Job'),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Photo",
            help="This field holds the image used as photo for the employee, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized photo", type="binary", multi="_get_image",
            store = {
                'hr.employee': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized photo of the employee. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized photo", type="binary", multi="_get_image",
            store = {
                'hr.employee': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the employee. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'image_crc': fields.char('Image CRC', size=128),
        'passport_id':fields.char('Passport No', size=64),
        'blueshield_id': fields.char('Blue Cross No', size=64),
        'color': fields.integer('Color Index'),
        'city': fields.related('partner_id', 'city', type='char', string='City'),
        'login': fields.related('user_id', 'login', type='char', string='Login', readonly=1),
        'last_login': fields.related('user_id', 'date', type='datetime', string='Latest Connection', readonly=1),
        'current': fields.related(
            'resource_id', 'active',
            type='boolean',
            string='Current Employee',
            ),
        'employment_type': fields.selection(EmploymentType, "Employment Status"),
        'employment_type_abbr': fields.function(
            _calc_emp_typ_abbr,
            type='char',
            string='Employment Status Abbr',
            size=1,
            store={
                'hr.employee': (lambda t, c, u, ids, ctx: ids, ['employment_type'], 10),
                },
            ),
        'employment_agency_id': fields.many2one('res.partner', 'Employment Agency'),
        'tests_checks_ids': fields.one2many('hr.test', 'employee_id', 'Tests & Checks'),
        }

    fields.apply_groups(
            _columns,
            {
                'base.group_hr_user': [
                    'identification_id',
                    ],
                'base.group_hr_manager': [
                    'current', 'country_id', 'birthday', 'ssnid', 'sinid', 'otherid',
                    'gender', 'marital', 'home_.*', 'emergency_.*','notes', 'child_ids',
                    'passport_id', 'color', 'city', 'employment_type.*', 'current',
                    'employment_agency', 'blueshield_id', 'partner_id', 'category_ids',
                    'resource_id',  'login','last_login',
                    ]})

    def create(self, cr, uid, data, context=None):
        # work around view not using default image
        if 'image' not in data and not data.get('image_medium'):
            data.pop('image_medium', None)
            data['image'] = self._get_default_image(cr, uid, context=context)
        partner_id = data.get('partner_id')
        if partner_id and not isinstance(partner_id, (int, long)):
            data.pop('partner_id')
        return super(hr_employee, self).create(cr, uid, data, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        partner_id = values.get('partner_id')
        if partner_id:
            if len(ids) > 1:
                except_osv('Error', 'Only one partner per employee.')
            employee_id = ids[0]
            self.pool.get('res.partner').write(cr, uid, partner_id, {'employee_id':employee_id, 'employee':True}, context=context)
        elif partner_id is not None:
            # partner_id is False or some other falsey value
            # clear already linked parter_ids
            res_partner = self.pool.get('res.partner')
            partner_ids = []
            for employee in self.browse(cr, uid, ids, context=context):
                if employee.partner_id:
                    partner_ids.append(employee.partner_id.id)
            if partner_ids:
                res_partner.write(cr, uid, partner_ids, {'employee_id':False, 'employee':False}, context=context)
        return super(hr_employee, self).write(cr, uid, ids, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        resource_ids = []
        for employee in self.browse(cr, uid, ids, context=context):
            resource_ids.append(employee.resource_id.id)
        return self.pool.get('resource.resource').unlink(cr, uid, resource_ids, context=context)

    def onchange_issues(self, cr, uid, ids, issues, context=None):
        res = {}
        res['value'] = {'issue_ids': issues}
        hr_issue = self.pool.get('hr.employee.issue')
        for op, _, issue in issues:
            if op == 0:
                # adding a new record
                if 'description' not in issue and 'description_pad' in issue:
                    issue['description'] = hr_issue.pad_get_content(cr, uid, issue['description_pad'], context=context)
                issue['create_date'] = fields.datetime.now(self, cr)
        return res

    def onchange_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id = self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'home_country_id':country_id}}
        return {}

    def onchange_partner_id(self, cr, uid, ids, partner, name, context=None):
        res = {}
        if partner:
            user_id = False
            partner = self.pool.get('res.partner').browse(cr, uid, partner, context=context)
            related_users = partner.user_ids
            if related_users:
                user_id = related_users[0].id
            email = partner.email
            if not email and related_users and related_users[0].email:
                email = related_users[0].email
            res = {
                'work_phone': partner.phone,
                'mobile_phone': partner.mobile,
                'work_email': email,
                'user_id': user_id,
                }
            if not name:
                res['name'] = partner.name
        return {'value': res}

    def onchange_company(self, cr, uid, ids, company, context=None):
        partner_id = False
        if company:
            company_id = self.pool.get('res.company').browse(cr, uid, company, context=context)
            address = self.pool.get('res.partner').address_get(cr, uid, [company_id.partner_id.id], ['default'])
            partner_id = address and address['default'] or False
        return {'value': {'partner_id' : partner_id}}

    def onchange_department_id(self, cr, uid, ids, department_id, context=None):
        value = {'parent_id': False}
        if department_id:
            department = self.pool.get('hr.department').browse(cr, uid, department_id)
            value['parent_id'] = department.manager_id.id
        return {'value': value}

    def _get_default_image(self, cr, uid, context=None):
        image_path = addons.get_module_resource('hr', 'static/src/img', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    _defaults = {
        'active': 1,
        'image': _get_default_image,
        'color': 0,
        'employment_type': EmploymentType.temporary,
        }

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT parent_id FROM hr_employee WHERE id IN %s AND parent_id!=id',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error! You cannot create recursive hierarchy of Employee(s).', ['parent_id']),
        ]


class hr_department(osv.osv):
    _description = "Department"
    _inherit = 'hr.department'
    _columns = {
        'manager_id': fields.many2one('hr.employee', 'Manager'),
        'member_ids': fields.one2many('hr.employee', 'department_id', 'Members', readonly=True),
        }

    def copy(self, cr, uid, ids, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['member_ids'] = []
        return super(hr_department, self).copy(cr, uid, ids, default, context=context)


class hr_test_type(osv.Model):
    _name = 'hr.test.type'
    _description = 'test and check types run on employees'
    _columns = {
        'name': fields.char('Name', size=32),
        'description': fields.text('Description'),
        'result_type': fields.selection(ResultType, 'Result Type'),
        }


class hr_test(osv.Model):
    _name = 'hr.test'
    _description = 'checks and tests for (potential) employees'
    _columns = {
        'name': fields.related('test_type', 'name', string='Name', type='char', store=True),
        'test_type': fields.many2one('hr.test.type', string='Type', ondelete='restrict', required=True),
        'result_type': fields.related('test_type', 'result_type', string='Result Type', type='selection', selection=ResultType),
        'result_description': fields.related('test_type', 'description', string='Description', type='text'),
        'test_date': fields.date('Date'),
        'result_pass_fail': fields.selection(ResultPassFail, 'Pass/Fail'),
        'result_grade': fields.selection(ResultGrade, string='Grade'),
        'result_percent': fields.integer("%"),
        'result': fields.char('Result', size=4),
        'employee_id': fields.many2one('hr.employee', 'Employee', ondelete='cascade'),
        'notes': fields.text('Notes'),
        'create_date': fields.datetime('Created on'),
        }

    def onchange_test(self, cr, uid, ids, test_type, context=None):
        records = self.pool.get('hr.test.type').read(cr, uid, [('id','=',test_type)], fields=['result_type','description'])
        result_type = records[0]['result_type']
        description = records[0]['description']
        return {
                'value': {
                    'result_type': result_type,
                    'result_description': description,
                    }}

    def onchange_result(self, cr, uid, ids, result_type, result, context=None):
        if result_type == 'pass_fail':
            result = result and ResultPassFail(result).user
        elif result_type == 'grade':
            result = result and ResultGrade(result).user
        elif result_type == 'percent':
            result = result and str(result)
        return {
                'value': {
                    'result': result,
                    }}

    def create(self, cr, uid, values, context=None):
        result_type = values['result_type']
        if result_type == 'pass_fail':
            values['result_grade'] = False
            values['result_percent'] = False
            result = values.get('result_pass_fail', False)
            result = result and ResultPassFail(result).user
        elif result_type == 'grade':
            values['result_percent'] = False
            values['result_pass_fail'] = False
            result = values.get('result_grade', False)
            result = result and ResultGrade(result).user
        elif result_type == 'percent':
            values['result_pass_fail'] = False
            values['result_grade'] = False
            result = values.get('result_percent', False)
            result = result and str(result)
        values['result'] = result
        return super(hr_test, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        result_type = values.get('result_type')
        if result_type is None:
            result_type = self.read(cr, uid, ids[0], fields=['result_type'], context=context)['result_type']
        if result_type == 'pass_fail':
            values['result_grade'] = False
            values['result_percent'] = False
            result = values.get('result_pass_fail', False)
            result = result and ResultPassFail(result).user
        elif result_type == 'grade':
            values['result_percent'] = False
            values['result_pass_fail'] = False
            result = values.get('result_grade', False)
            result = result and ResultGrade(result).user
        elif result_type == 'percent':
            values['result_pass_fail'] = False
            values['result_grade'] = False
            result = values.get('result_percent', False)
            result = result and str(result)
        values['result'] = result
        return super(hr_test, self).write(cr, uid, ids, values, context=context)


class res_partner(osv.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _calc_changing_res_partner(hr_employee, cr, uid, employee_ids, context=None):
        # return the ids of any res.partner records that already point to the changed employee records, or
        # that are pointed to by the changed employee records
        self = hr_employee.pool.get('res.partner')
        # first get records already point to the changed employee records
        ids = self.search(cr, SUPERUSER_ID, [('id','in',employee_ids)], context=context)
        # then add the ids pointed to by changed employee records
        ids.extend([
            r['partner_id'][0]
            for r in hr_employee.read(
                    cr, SUPERUSER_ID, employee_ids, fields=['partner_id'], context=context,
                    )
            if r['partner_id']
            ])

        return ids

    def _set_employee_id(self, cr, uid, ids, name, args, context=None):
        res = {}.fromkeys(ids, False)
        hr_employee = self.pool.get( 'hr.employee')
        for rec in hr_employee.read(
                cr, SUPERUSER_ID,
                [('partner_id','in',ids)],
                fields=['id','partner_id'],
                context=context,
                ):
            res[rec['partner_id'][0]] = rec['id']
        return res


    _columns = {
        'employee_id': fields.function(
            _set_employee_id,
            type='many2one',
            relation='hr.employee',
            string='Employee Record',
            store={
                'hr.employee': (_calc_changing_res_partner, ['partner_id'], 10),
                }),
        'agency_referred_ids': fields.one2many(
            'hr.employee',
            'employment_agency_id',
            'Referred Employees',
            readonly=False,
            ),
        }

