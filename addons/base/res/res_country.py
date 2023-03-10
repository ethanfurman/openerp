# -*- coding: utf-8 -*-
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

from openerp.osv import fields, osv
from textwrap import dedent

def location_name_search(self, cr, user, name='', args=None, operator='ilike',
                         context=None, limit=100):
    if not args:
        args = []

    ids = []
    if len(name) == 2:
        ids = self.search(cr, user, [('code', 'ilike', name)] + args,
                          limit=limit, context=context)

    search_domain = [('name', operator, name)]
    if ids: search_domain.append(('id', 'not in', ids))
    ids.extend(self.search(cr, user, search_domain + args,
                           limit=limit, context=context))

    locations = self.name_get(cr, user, ids, context)
    return sorted(locations, key=lambda (id, name): ids.index(id))

class Country(osv.osv):
    _name = 'res.country'
    _description = 'Country'
    _columns = {
        'name': fields.char('Country Name', size=64,
            help='The full name of the country.', required=True, translate=True),
        'code': fields.char('Country Code', size=2,
            help='The ISO country code in two chars.\nYou can use this field for quick search.'),
        'address_format': fields.text('Address Format', help=dedent("""\
                You can state here the usual format to use for the addresses belonging to this country.\n
                You can use the python-style string patern with all the field of the address:

                - %(street)s ->  the name of the street
                - %(state_name)s ->  the name of the state
                - %(state_code)s ->  the code of the state
                - %(country_name)s ->  the name of the country
                - %(country_code)s ->  the code of the country
                """),
                ),
        'currency_id': fields.many2one('res.currency', 'Currency'),
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the country must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the country must be unique !')
    ]
    _defaults = {
        'address_format': "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s",
    }
    _order='name'

    name_search = location_name_search

    def create(self, cursor, user, vals, context=None):
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        return super(Country, self).create(cursor, user, vals,
                context=context)

    def write(self, cursor, user, ids, vals, context=None):
        if 'code' in vals:
            vals['code'] = vals['code'].upper()
        return super(Country, self).write(cursor, user, ids, vals,
                context=context)


class CountryState(osv.osv):
    _description="Country state"
    _name = 'res.country.state'
    _columns = {
        'country_id': fields.many2one('res.country', 'Country',
            required=True),
        'name': fields.char('State Name', size=64, required=True,
                            help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton'),
        'code': fields.char('State Code', size=3,
            help='The state code in max. three chars.', required=True),
    }
    _order = 'code'

    name_search = location_name_search


