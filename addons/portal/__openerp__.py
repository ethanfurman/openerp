# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP S.A (<http://www.openerp.com>).
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

{
    'name' : 'Portal',
    'version': '1.0',
    'depends': [
        'base',
        'auth_signup',
    ],
    'author': 'OpenERP SA',
    'category': 'Portal',
    'description': """
Customize access to your OpenERP database to external users by creating portals.
================================================================================
A portal defines a specific user menu and access rights for its members.  This
menu can ben seen by portal members, anonymous users and any other user that
have the access to technical features (e.g. the administrator).
Also, each portal member is linked to a specific partner.

The module also associates user groups to the portal users (adding a group in
the portal automatically adds it to the portal users, etc).
    """,
    'website': 'http://www.openerp.com',
    'data': [
        'portal_data.xml',
        'portal_view.xml',
        'wizard/portal_wizard_view.xml',
        'security/ir.model.access.csv',
        'security/portal_security.xml',
    ],
    'demo': ['portal_demo.xml'],
    'css': ['static/src/css/portal.css'],
    'auto_install': True,
    'installable': True,
}

