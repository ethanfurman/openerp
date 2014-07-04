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
{
    'name' : 'HR Driver extensions to Fleet Management',
    'version' : '0.1',
    'author' : 'Ethan Furman',
    'sequence': 115,
    'category': 'Managing drivers for vehicles',
    'summary' : 'Drive info such as DL, class, medical info, etc.',
    'description' : """
Drive info such as DL, class, medical info, etc.
================================================
With this module, OpenERP helps you keep track of necessary driver
information such as license number, class rating, and medical card,
and expiration dates.
""",
    'depends' : [
        'base',
        'hr',
        'fleet'
        ],
    'update_xml' : [
        'fleet_hr_view.xml',
        ],

    'installable' : True,
}
