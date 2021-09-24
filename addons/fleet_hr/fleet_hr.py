import logging
from osv import osv, fields
from dbf import Date
from openerp import SUPERUSER_ID
from openerp.tools import self_ids

_logger = logging.getLogger(__name__)

class RenewalState(fields.SelectionEnum):
    soon = 'Renewal Due Soon'
    overdue = 'Renewal Overdue'

def _get_license_expiries(model, cr, uid, ids, field_names, unknown_none, context=None):
    res = {}
    today = Date.today()
    for record in model.browse(cr, SUPERUSER_ID, ids, context=context):
        res[record.id] = {}
        dl_soon = dl_over = False
        md_soon = md_over = False
        renewal_state = ''
        employee = None
        # if this is a vehicle record, grab the employee record from it
        if model._name == 'hr.employee':
            employee = record
        elif model._name == 'fleet.vehicle':
            if record.driver_id and record.driver_id.employee_id:
                employee = record.driver_id.employee_id
        if employee is not None:
            if employee.driver_license_exp:
                if today > Date(employee.driver_license_exp):
                    dl_over = True
                elif today.replace(delta_day=30) > Date(employee.driver_license_exp):
                    dl_soon = True
            if employee.driver_medical_exp:
                if today > Date(employee.driver_medical_exp):
                    md_over = True
                elif today.replace(delta_day=30) > Date(employee.driver_medical_exp):
                    md_soon = True
            if dl_soon or md_soon:
                renewal_state = RenewalState.soon
            if dl_over or md_over:
                renewal_state = RenewalState.overdue
        for possible, status in (
                ('driver_license_renewal_due_soon', dl_soon),
                ('driver_license_renewal_overdue', dl_over),
                ('driver_medical_renewal_due_soon', md_soon),
                ('driver_medical_renewal_overdue', md_over),
                ('driver_renewal_state', renewal_state),
            ):
            if possible in field_names:
                res[record.id][possible] = status
    return res

class hr_employee(osv.Model):
    "fleet driver information fields"
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    _columns = {
        'driver_license_state': fields.many2one('res.country.state', 'State of License'),
        'driver_license_num': fields.char('License #', size=24),
        'driver_license_class': fields.selection([('A','A'),('B','B'),('C','C'),('M','M')], 'License Class'),
        'driver_license_exp': fields.date('License Expiration'),
        'driver_medical_exp': fields.date('Medical Expiration'),
        'driver_license_renewal_due_soon': fields.function(
            _get_license_expiries,
            type='boolean',
            string='License expires soon',
            multi='driver',
            ),
        'driver_license_renewal_overdue': fields.function(
            _get_license_expiries,
            type='boolean',
            string='License has expired',
            multi='driver',
            ),
        'driver_medical_renewal_due_soon': fields.function(
            _get_license_expiries,
            type='boolean',
            string='Medical clearance expires soon',
            multi='driver',
            ),
        'driver_medical_renewal_overdue': fields.function(
            _get_license_expiries,
            type='boolean',
            string="Medical clearance expired",
            multi='driver',
            ),
        'driver_renewal_state': fields.function(
            _get_license_expiries,
            type='selection',
            selection=RenewalState,
            string='Renewal Status',
            multi='driver',
            ),
        }

    fields.apply_groups(
            _columns,
            {
                'base.group_hr_manager,fleet.group_fleet_manager':
                    ['driver_license_.*', 'driver_medical_.*', 'driver_renewal_state']
                    })


class res_partner(osv.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not context.get('show_driver') or not self.user_has_groups(cr, uid, 'fleet.group_fleet_manager', context=context):
            return super(res_partner, self).name_get(cr, uid, ids, context=context)
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            is_employee = record.employee
            employee = record.employee_id
            if is_employee and employee:
                name = '%s (%s)\nLicense: %s %s %s\nLicense Exp: %s\nMedical Exp: %s' % (
                        name,
                        employee.identification_id or '',
                        employee.driver_license_state and employee.driver_license_state.code or '',
                        employee.driver_license_num or '',
                        employee.driver_license_class or '',
                        employee.driver_license_exp or '',
                        employee.driver_medical_exp or '',
                        )
            res.append((record.id, name))
        return res


class fleet_vehicle(osv.Model):
    _name = 'fleet.vehicle'
    _inherit = 'fleet.vehicle'

    def _get_driver(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids)
        for vehic in self.browse(cr, uid, ids, context=context):
            driver = vehic.driver_id or vehic.hr_driver_id
            res[vehic.id] = driver.name
        return res

    _columns = {
        'driver': fields.function(
            _get_driver,
            string='Driver',
            type='char',
            size=128,
            store={
                    'fleet.vehicle': (self_ids, ['driver_id', 'hr_driver_id'], 10),
                    },
            ),
        'driver_id': fields.many2one(
            'res.partner',
            'Outside Driver',
            domain=[('employee_id','!=',False)],
            help="Driver of the vehicle",
            ),
        'hr_driver_id': fields.many2one(
            'hr.employee',
            'Employee Driver',
            help="Driver of the vehicle",
            ),
        'driver_license_renewal_due_soon': fields.function(
            _get_license_expiries,
            type='boolean',
            string='License expires soon',
            multi='driver',
            ),
        'driver_license_renewal_overdue': fields.function(
            _get_license_expiries,
            type='boolean',
            string='License has expired',
            multi='driver',
            ),
        'driver_medical_renewal_due_soon': fields.function(
            _get_license_expiries,
            type='boolean',
            string='Medical clearance expires soon',
            multi='driver',
            ),
        'driver_medical_renewal_overdue': fields.function(
            _get_license_expiries,
            type='boolean',
            string="Medical clearance expired",
            multi='driver',
            ),
        'driver_renewal_state': fields.function(
            _get_license_expiries,
            type='selection',
            selection=RenewalState,
            string='Renewal Status',
            multi='driver',
            ),
        }
