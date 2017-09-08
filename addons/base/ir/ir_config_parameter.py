# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://www.openerp.com>).
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
"""
Store database-specific configuration parameters
"""

import uuid
import datetime
import pytz
from pytz.exceptions import UnknownTimeZoneError
import sys
from tempfile import TemporaryFile

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import misc, config
from openerp.exceptions import ERPError

"""
A dictionary holding some configuration parameters to be initialized when the database is created.
"""
_default_parameters = {
    "database.uuid": lambda: str(uuid.uuid1()),
    "database.create_date": lambda: datetime.datetime.now().strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT),
    "database.time_zone": lambda: 'UTC',
    "web.base.url": lambda: "http://localhost:%s" % config.get('xmlrpc_port'),
}

class ir_config_parameter(osv.osv):
    """Per-database storage of configuration key-value pairs."""

    _name = 'ir.config_parameter'

    _columns = {
        'key': fields.char('Key', size=256, required=True, select=1),
        'value': fields.text('Value', required=True),
    }

    _sql_constraints = [
        ('key_uniq', 'unique (key)', 'Key must be unique.')
    ]

    def init(self, cr, force=False):
        """
        Initializes the parameters listed in _default_parameters.
        It overrides existing parameters if force is ``True``.
        """
        for key, func in _default_parameters.iteritems():
            # force=True skips search and always performs the 'if' body (because ids=False)
            ids = not force and self.search(cr, SUPERUSER_ID, [('key','=',key)])
            if not ids:
                self.set_param(cr, SUPERUSER_ID, key, func())

    def get_param(self, cr, uid, key, default=False, context=None):
        """Retrieve the value for a given key.

        :param string key: The key of the parameter value to retrieve.
        :param string default: default value if parameter is missing.
        :return: The value of the parameter, or ``default`` if it does not exist.
        :rtype: string
        """
        ids = self.search(cr, uid, [('key','=',key)], context=context)
        if not ids:
            return default
        param = self.browse(cr, uid, ids[0], context=context)
        value = param.value
        return value

    def set_param(self, cr, uid, key, value, context=None):
        """Sets the value of a parameter.

        :param string key: The key of the parameter value to set.
        :param string value: The value to set.
        :return: the previous value of the parameter or False if it did
                 not exist.
        :rtype: string
        """
        self.check_param(key, value, context=context)
        ids = self.search(cr, uid, [('key','=',key)], context=context)
        if ids:
            param = self.browse(cr, uid, ids[0], context=context)
            old = param.value
            self.write(cr, uid, ids, {'value': value}, context=context)
            return old
        else:
            self.create(cr, uid, {'key': key, 'value': value}, context=context)
            return False

    def check_param(self, key, value, context=None):
        if key == 'database.time_zone':
            # make sure new time zone exists
            try:
                pytz.timezone(value)
            except UnknownTimeZoneError:
                raise ERPError('Unknown Time Zone', 'Time zone %r is not supported.' % (value, ))
        elif key == 'ir_attachment.location':
            # check if location is writable by openerp daemon
            if ':' not in value:
                raise ERPError('Bad Value', 'protocol missing (should be "proto:/some/path")')
            proto, path = value.split(':', 1)
            if proto == 'file':
                try:
                    with TemporaryFile(dir=path):
                        pass
                except (IOError, OSError):
                    exc = sys.exc_info()[1]
                    errno, text = exc.args
                    raise ERPError('Bad Path', text)

    def create(self, cr, uid, vals, context=None):
        self.check_param(vals['key'], vals['value'])
        return super(ir_config_parameter, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for entry in self.read(cr, uid, ids, context=context):
            self.check_param(entry['key'], vals['value'])
        return super(ir_config_parameter, self).write(cr, uid, ids, vals, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
