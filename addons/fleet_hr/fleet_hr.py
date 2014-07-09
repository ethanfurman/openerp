import logging
from osv import osv, fields
from fnx import Date

_logger = logging.getLogger(__name__)


class hr_employee(osv.Model):
    "fleet driver information fields"
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    _columns = {
        'driver_employee_num': fields.char('Employee #', size=12),
        'driver_license_state': fields.many2one('res.country.state', 'State of License'),
        'driver_license_num': fields.char('License #', size=24),
        'driver_license_class': fields.selection([('A','A'),('B','B'),('C','C'),('M','M')], 'License Class'),
        'driver_license_exp': fields.date('License Expiration'),
        'driver_medical_exp': fields.date('Medical Expiration'),
        }


class res_partner(osv.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not context.get('show_driver') and self.user_has_groups(cr, uid, 'fleet.group_fleet_manager', context=context):
            return super(res_partner, self).name_get(cr, uid, ids, context=context)
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            employee = record.employee_id
            if employee:
                name = '%s (%s)\nLicense: %s %s %s\nLicense Exp: %s\nMedical Exp: %s' % (
                        name,
                        employee.driver_employee_num or '',
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

    def _get_license_expiries(self, cr, uid, ids, field_names, unknown_none, context=None):
        res = {}
        for vehicle in self.browse(cr, uid, ids, context=context):
            dl_soon = dl_over = False
            md_soon = md_over = False
            if vehicle.driver_id and vehicle.driver_id.employee_id:
                employee = vehicle.driver_id.employee_id
                today = Date.today()
                if not employee.driver_license_exp or today > Date(employee.driver_license_exp):
                    dl_over = True
                elif today.replace(delta_day=30) > Date(employee.driver_license_exp):
                    dl_soon = True
                if not employee.driver_medical_exp or today > Date(employee.driver_medical_exp):
                    md_over = True
                elif today.replace(delta_day=30) > Date(employee.driver_medical_exp):
                    md_soon = True
            res[vehicle.id] = {
                    'driver_license_renewal_due_soon': dl_soon,
                    'driver_license_renewal_overdue': dl_over,
                    'driver_medical_renewal_due_soon': md_soon,
                    'driver_medical_renewal_overdue': md_over,
                    }
        return res

    _columns = {
        'driver_id': fields.many2one(
            'res.partner',
            'Driver',
            domain=[('employee_id','!=',False)],
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
            )
        }
