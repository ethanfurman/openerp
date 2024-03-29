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

from lxml import etree
import openerp.tools as tools
from openerp.tools.safe_eval import safe_eval
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, SERVER_TIMEZONE
import print_fnc
from openerp.osv.orm import browse_null, browse_record
import openerp.pooler as pooler
import datetime
import pytz
import logging
 
UTC = pytz.timezone('UTC')
_logger = logging.getLogger(__name__)

class InheritDict(dict):
    # Might be usefull when we're doing name lookup for call or eval.

    def __init__(self, parent=None):
        self.parent = parent

    def __getitem__(self, name):
        if name in self:
            return super(InheritDict, self).__getitem__(name)
        else:
            if not self.parent:
                raise KeyError
            else:
                return self.parent[name]

def tounicode(val):
    if isinstance(val, str):
        unicode_val = unicode(val, 'utf-8')
    elif isinstance(val, unicode):
        unicode_val = val
    else:
        unicode_val = unicode(val)
    return unicode_val

class document(object):
    def __init__(self, cr, uid, datas, func=False):
        # create a new document
        self.cr = cr
        self.pool = pooler.get_pool(cr.dbname)
        self.func = func or {}
        self.datas = datas
        self.uid = uid
        self.bin_datas = {}

    def node_attrs_get(self, node):
        if len(node.attrib):
            return node.attrib
        return {}

    def get_value(self, browser, field_path, format=None):
        fields = field_path.split('.')

        if not len(fields):
            return ''

        value = browser

        for i, field in enumerate(fields):
            if isinstance(value, list):
                if len(value)==0:
                    return ''
                if len(value) > 1 and i == len(fields)-1:
                    multivalue = []
                    for rec in value:
                        subvalue = getattr(rec, field, '')
                        if subvalue:
                            multivalue.append(str(subvalue))
                    value = ', '.join(multivalue)
                    return value
                else:
                    value = value[0]
            if isinstance(value, browse_null):
                return ''
            else:
                browser = value
                value = value[field]
        try:
            if isinstance(value, browse_null):
                return ''
            elif isinstance(value, browse_record):
                return value
            elif isinstance(browser, list):
                model = browser[0]._table
            else:
                model = browser._table
            column = model._columns[field]
            column_type = column._type
            if column_type == 'selection':
                for db_name, human_name in column.selection:
                    if db_name == value:
                        value = human_name
                        break
            elif column_type == 'boolean':
                if format is None:
                    value = column.choice[bool(value)]
                else:
                    value = (format.split(',')[bool(value)]).strip()
            elif column_type == 'date' and value:
                value = datetime.datetime.strptime(value, DEFAULT_SERVER_DATE_FORMAT)
                value = UTC.localize(value).astimezone(SERVER_TIMEZONE).strftime(format or DEFAULT_SERVER_DATE_FORMAT).decode('latin1')
            elif column_type == 'time' and value:
                value = datetime.datetime.strptime(value, DEFAULT_SERVER_TIME_FORMAT)
                value = UTC.localize(value).astimezone(SERVER_TIMEZONE).strftime(format or DEFAULT_SERVER_TIME_FORMAT).decode('latin1')
            elif column_type == 'datetime' and value:
                value = datetime.datetime.strptime(value, DEFAULT_SERVER_DATETIME_FORMAT)
                value = UTC.localize(value).astimezone(SERVER_TIMEZONE).strftime(format or DEFAULT_SERVER_DATETIME_FORMAT).decode('latin1')
            elif column_type == 'float':
                try:
                    spec = format or '%%%s.%sf' % column.digits
                except Exception:
                    _logger.error('unable to get convert `column.digits` of %r for %r' % (column.digits, field))
                    spec = "%16.3f"
                value = spec % value
        except KeyError:
            if field not in ('name', 'id'):
                _logger.exception('unable to convert field %r with value %r', field_path, value)
        except Exception:
            _logger.exception('unable to convert field %r with value %r', field_path, value)

        return value and value or ''

    def get_value2(self, browser, field_path):
        value = self.get_value(browser, field_path)
        if isinstance(value, browse_record):
            return value.id
        elif isinstance(value, browse_null):
            return False
        else:
            return value

    def eval(self, record, expr):
        #TODO: support remote variables (eg address.title) in expr
        # how to do that: parse the string, find dots, replace those dotted variables by temporary
        # "simple ones", fetch the value of those variables and add them (temporarily) to the _data
        # dictionary passed to eval

        #FIXME: it wont work if the data hasn't been fetched yet... this could
        # happen if the eval node is the first one using this browse_record
        # the next line is a workaround for the problem: it causes the resource to be loaded
        #Pinky: Why not this ? eval(expr, browser) ?
        #       name = browser.name
        #       data_dict = browser._data[self.get_value(browser, 'id')]
        return safe_eval(expr, {}, {'obj': record})

    def parse_node(self, node, parent, browser, datas=None):
            attrs = self.node_attrs_get(node)
            if 'type' in attrs:
                if attrs['type']=='field':
                    field = attrs['name']
                    format = attrs.get('format')
                    value = self.get_value(browser, field, format)
                    #TODO: test this
                    if value == '' and 'default' in attrs:
                        value = attrs['default']
                    el = etree.SubElement(parent, node.tag)
                    el.text = tounicode(value)
                    #TODO: test this
                    for key, value in attrs.iteritems():
                        if key not in ('type', 'name', 'default'):
                            el.set(key, value)

                elif attrs['type']=='attachment':
                    if isinstance(browser, list):
                        model = browser[0]._table_name
                    else:
                        model = browser._table_name

                    value = self.get_value(browser, attrs['name'])

                    ids = self.pool.get('ir.attachment').search(self.cr, self.uid, [('res_model','=',model),('res_id','=',int(value))])
                    datas = self.pool.get('ir.attachment').read(self.cr, self.uid, ids)

                    if len(datas):
                        # if there are several, pick first
                        datas = datas[0]
                        fname = str(datas['datas_fname'])
                        ext = fname.split('.')[-1].lower()
                        if ext in ('jpg','jpeg', 'png'):
                            import base64
                            from StringIO import StringIO
                            dt = base64.decodestring(datas['datas'])
                            fp = StringIO()
                            fp.write(dt)
                            i = str(len(self.bin_datas))
                            self.bin_datas[i] = fp
                            el = etree.SubElement(parent, node.tag)
                            el.text = i

                elif attrs['type']=='data':
                    #TODO: test this
                    txt = self.datas.get('form', {}).get(attrs['name'], '')
                    el = etree.SubElement(parent, node.tag)
                    el.text = txt

                elif attrs['type']=='function':
                    if attrs['name'] in self.func:
                        txt = self.func[attrs['name']](node)
                    else:
                        txt = print_fnc.print_fnc(attrs['name'], node)
                    el = etree.SubElement(parent, node.tag)
                    el.text = txt

                elif attrs['type']=='eval':
                    value = self.eval(browser, attrs['expr'])
                    el = etree.SubElement(parent, node.tag)
                    el.text = str(value)

                elif attrs['type']=='fields':
                    fields = attrs['name'].split(',')
                    vals = {}
                    for b in browser:
                        value = tuple([self.get_value2(b, f) for f in fields])
                        if not value in vals:
                            vals[value]=[]
                        vals[value].append(b)
                    keys = vals.keys()
                    keys.sort()

                    if 'order' in attrs and attrs['order']=='desc':
                        keys.reverse()

                    v_list = [vals[k] for k in keys]
                    for v in v_list:
                        el = etree.SubElement(parent, node.tag)
                        for el_cld in node:
                            self.parse_node(el_cld, el, v)

                elif attrs['type']=='call':
                    if len(attrs['args']):
                        #TODO: test this
                        # fetches the values of the variables which names where passed in the args attribute
                        args = [self.eval(browser, arg) for arg in attrs['args'].split(',')]
                    else:
                        args = []
                    # get the object
                    if 'model' in attrs:
                        obj = self.pool.get(attrs['model'])
                    else:
                        if isinstance(browser, list):
                            obj = browser[0]._table
                        else:
                            obj = browser._table

                    # get the ids
                    if 'ids' in attrs:
                        ids = self.eval(browser, attrs['ids'])
                    else:
                        if isinstance(browser, list):
                            ids = [b.id for b in browser]
                        else:
                            ids = [browser.id]

                    # call the method itself
                    newdatas = getattr(obj, attrs['name'])(self.cr, self.uid, ids, *args)

                    def parse_result_tree(node, parent, datas):
                        if not node.tag == etree.Comment:
                            el = etree.SubElement(parent, node.tag)
                            atr = self.node_attrs_get(node)
                            if 'value' in atr:
                                if not isinstance(datas[atr['value']], (str, unicode)):
                                    txt = str(datas[atr['value']])
                                else:
                                    txt = datas[atr['value']]
                                el.text = txt
                            else:
                                for el_cld in node:
                                    parse_result_tree(el_cld, el, datas)
                    if not isinstance(newdatas, list):
                        newdatas = [newdatas]
                    for newdata in newdatas:
                        parse_result_tree(node, parent, newdata)

                elif attrs['type']=='zoom':
                    value = self.get_value(browser, attrs['name'])
                    if value:
                        if not isinstance(value, list):
                            v_list = [value]
                        else:
                            v_list = value
                        for v in v_list:
                            el = etree.SubElement(parent, node.tag)
                            for el_cld in node:
                                self.parse_node(el_cld, el, v)

                elif attrs['type'] == 'merge':
                    value = self.get_value(browser, attrs['name'])
                    field_name = attrs['field']
                    sep = attrs.get('sep', ', ')
                    if sep == '\\n':
                        sep = '\n'
                    vals = []
                    if value:
                        if not isinstance(value, list):
                            v_list = [value]
                        else:
                            v_list = value
                        for v in v_list:
                            vals.append(v[field_name])
                    sort = attrs.get('sort', None)
                    if sort == 'asc':
                        vals.sort()
                    elif sort == 'desc':
                        vals.sort(reverse=True)
                    el = etree.SubElement(parent, node.tag)
                    el.text = tounicode(sep.join(vals))

            else:
                # if there is no "type" attribute in the node, copy it to the xml data and parse its children
                if not node.tag == etree.Comment:
                    if node.tag == parent.tag:
                        el = parent
                    else:
                        el = etree.SubElement(parent, node.tag)
                    for el_cld in node:
                        self.parse_node(el_cld,el, browser)
    def xml_get(self):
        return etree.tostring(self.doc,encoding="utf-8",xml_declaration=True,pretty_print=True)

    def parse_tree(self, ids, model, context=None):
        if context is None:
            context = {}
        browser = self.pool.get(model).browse(self.cr, self.uid, ids, context)
        self.parse_node(self.dom, self.doc, browser)

    def parse_string(self, xml, ids, model, context=None):
        if context is None:
            context = {}
        # parses the xml template to memory
        self.dom = etree.XML(xml)
        # create the xml data from the xml template
        self.parse_tree(ids, model, context)

    def parse(self, filename, ids, model, context=None):
        if context is None:
            context = {}
        # parses the xml template to memory
        src_file = tools.file_open(filename)
        try:
            self.dom = etree.XML(src_file.read())
            self.doc = etree.Element(self.dom.tag)
            self.parse_tree(ids, model, context)
        finally:
            src_file.close()

    def close(self):
        self.doc = None
        self.dom = None



