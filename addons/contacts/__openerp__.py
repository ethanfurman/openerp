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
    'name': 'Address Book',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module gives you a quick view of your address book, accessible from your home page.
You can track your suppliers, customers and other contacts.
""",
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'summary': 'Contacts, People and Companies',
    'depends': [
        'mail',
    ],
    'data': [
        'contacts_view.xml',
    ],
    'images': ['images/contacts.jpeg'],
    'installable': True,
    'application': True,
    'auto_install': False,
}

