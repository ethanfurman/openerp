import logging
from osv import osv, fields

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
    _columns = {
        'driver_id': fields.many2one(
            'res.partner',
            'Driver',
            domain=[('employee_id','!=',False)],
            help="Driver of the vehicle",
            ),
        }
