import logging
from osv import osv, fields
from dbf import Date
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

class RenewalState(fields.SelectionEnum):
    SOON = 'Renewal Due Soon'
    OVERDUE = 'Renewal Overdue'

def _get_license_expiries(model, cr, uid, ids, field_names, unknown_none, context=None):
    res = {}
    today = Date.today()
    for record in model.browse(cr, SUPERUSER_ID, ids, context=context):
        res[record.id] = {}
        dl_soon = dl_over = False
        md_soon = md_over = False
        renewal_state = ''
        # check for restricted fields
        if all(f in field_names for f in (
                'driver_license_renewal_due_soon',
                'driver_license_renewal_overdue',
                'driver_medical_renewal_due_soon',
                'driver_medical_renewal_overdue',
                )
                or uid == record.id
            ):
            if record.driver_license_exp:
                if today > Date(record.driver_license_exp):
                    dl_over = True
                elif today.replace(delta_day=30) > Date(record.driver_license_exp):
                    dl_soon = True
            if record.driver_medical_exp:
                if today > Date(record.driver_medical_exp):
                    md_over = True
                elif today.replace(delta_day=30) > Date(record.driver_medical_exp):
                    md_soon = True
            if dl_soon or md_soon:
                renewal_state = RenewalState.SOON
            if dl_over or md_over:
                renewal_state = RenewalState.OVERDUE
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
            {'base.group_hr_manager': ['driver_license_.*', 'driver_medical_.*']},
            )


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
            ),
        'driver_renewal_state': fields.function(
            _get_license_expiries,
            type='selection',
            selection=RenewalState,
            string='Renewal Status',
            multi='driver',
            ),
        }
