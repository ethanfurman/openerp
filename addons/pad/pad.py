# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import random
import re
import string
import urllib2
import logging
from openerp.tools.translate import _
from openerp.tools import html2plaintext
from py_etherpad import EtherpadLiteClient

_logger = logging.getLogger(__name__)

class pad_common(osv.osv_memory):
    _name = 'pad.common'

    def pad_generate_url(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id;

        pad = {
            "server" : company.pad_server,
            "key" : company.pad_key,
        }

        # make sure pad server in the form of http://hostname
        if not pad["server"]:
            return pad
        if not pad["server"].startswith('http'):
            pad["server"] = 'http://' + pad["server"]
        pad["server"] = pad["server"].rstrip('/')
        # generate a salt
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.randint(0, len(s) - 1)] for i in range(10)])
        #path
        path = '%s-%s-%s' % (cr.dbname.replace('_','-'), self._name, salt)
        # contruct the url
        url = '%s/p/%s' % (pad["server"], path)
        myPad = EtherpadLiteClient( pad["key"], pad["server"]+'/api')
        myPad.createPad(path)
        myPad.setText(path, '')

        #if create with content
        if "field_name" in context and "model" in context and "object_id" in context:
            #get attr on the field model
            model = self.pool.get(context["model"])
            field = model._all_columns[context['field_name']]
            real_field = field.column.pad_content_field

            #get content of the real field
            for record in model.browse(cr, uid, [context["object_id"]]):
                if record[real_field]:
                    myPad.setText(path, html2plaintext(record[real_field]))
                    #Etherpad for html not functional
                    #myPad.setHTML(path, record[real_field])

        return {
            "server": pad["server"],
            "path": path,
            "url": url,
        }

    def pad_get_content(self, cr, uid, url, context=None):
        content = False
        if url:
            try:
                page = urllib2.urlopen('%s/export/html'%url).read()
                mo = re.search('<body>([\s\S]*?)</body>',page)
                if mo:
                    content = mo.group(1)
                invite = re.search('You can invite others to share this pad', content)
                advert = re.search('Welcome to Etherpad', content)
                if invite or advert:
                    content = '<br/>'
                else:
                    mo = re.search('([\s\S]*?)<div style="display:none.*?</div>([\s\S]*?)', content)
                    if mo:
                        content = ''.join(mo.groups())
            except:
                _logger.warning("Nothing found at url: %r.", url)
        if content:
            for thing, trans in (
                    ('<br>', '\n'),
                    ('<br/>', '\n'),
                    ('&quot;', '"'),
                    ('&gt;', '>'),
                    ('&lt;', '<'),
                    ('&nbsp', ' '),
                    ):
                content = content.replace(thing, trans)
            for thing in re.findall('&#x..;', content):
                try:
                    ch = chr(int(thing[3:5], 16))
                    content = content.replace(thing, ch)
                except ValueError:
                    _logger.warn('unable to convert %r', thing)
                    continue
        return content.strip()

    # TODO
    # reverse engineer protocol to be setHtml without using the api key

    def write(self, cr, uid, ids, vals, context=None):
        self._set_pad_value(cr, uid, vals, context)
        return super(pad_common, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        self._set_pad_value(cr, uid, vals, context)
        return super(pad_common, self).create(cr, uid, vals, context=context)

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        res = super(pad_common, self).read(cr, uid, ids, fields, context, load)
        pad_fields = [n for n, f in self._all_columns.items() if hasattr(f.column, 'pad_content_field')]
        target_fields = set(pad_fields) & set(fields or self._all_columns.keys())
        if not target_fields:
            return res
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id;
        server = company.pad_server
        if not server.startswith('http'):
            server = 'http://' + server
        for rec in res:
            for tf in target_fields:
                path = rec[tf]
                if not path:
                    continue
                head, sep, tail = path.partition('/p/')
                path = server + sep + tail
                rec[tf] = path
        return res

    # Set the pad content in vals
    def _set_pad_value(self, cr, uid, vals, context=None):
        # the 'http' is removed by the javascript widget to force a rewrite;
        # add it back, and update pad_content_field
        for k,v in vals.items():
            field = self._all_columns[k].column
            if hasattr(field,'pad_content_field'):
                if not v.startswith('http'):
                    v = 'http' + v
                    vals[k] = v
                vals[field.pad_content_field] = self.pad_get_content(cr, uid, v, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        for k, v in self._all_columns.iteritems():
            field = v.column
            if hasattr(field,'pad_content_field'):
                pad = self.pad_generate_url(cr, uid, context)
                default[k] = pad.get('url')
        return super(pad_common, self).copy(cr, uid, id, default, context)
