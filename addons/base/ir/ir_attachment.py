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

import hashlib
import itertools
import logging
import os
import sys

from openerp import tools
from openerp.exceptions import ERPError
from openerp.osv import fields,osv

_logger = logging.getLogger(__name__)

class ir_attachment(osv.osv):
    """Attachments are used to link binary files or url to any openerp document.

    External attachment storage
    ---------------------------

    The 'data' function field (_data_get,data_set) is implemented using
    _file_read, _file_write and _file_delete which can be overridden to
    implement other storage engines, shuch methods should check for other
    location pseudo uri (example: hdfs://hadoppserver)

    The default implementation is the file:dirname location that stores files
    on the local filesystem using name based on their sha1 hash
    """
    def _name_get_resname(self, cr, uid, ids, object, method, context):
        data = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            model_object = attachment.res_model
            res_id = attachment.res_id
            if model_object and res_id:
                model_pool = self.pool.get(model_object)
                res = model_pool.name_get(cr,uid,[res_id],context)
                res_name = res and res[0][1] or False
                if res_name:
                    field = self._columns.get('res_name',False)
                    if field and len(res_name) > field.size:
                        res_name = res_name[:field.size-3] + '...'
                data[attachment.id] = res_name
            else:
                data[attachment.id] = False
        return data

    # 'data' field implementation
    def _full_path(self, cr, uid, attachment, location, filename):
        # location = 'file://filestore'
        assert location.startswith('file://'), "Unhandled filestore location %s" % location
        path_file = os.path.join(location[7:], cr.dbname, attachment.res_model, filename)
        if path_file[0] not in "/\\":
            path_file = os.path.join(tools.config['root_path'], path_file)
        return path_file

    def _file_read(self, cr, uid, attachment, location, fname, bin_size=False):
        full_path = self._full_path(cr, uid, attachment, location, fname)
        r = ''
        try:
            if bin_size:
                r = os.path.getsize(full_path)
            else:
                r = open(full_path,'rb').read().encode('base64')
        except IOError:
            type, exc, traceback = sys.exc_info()
            _logger.error("%s:%s during _read_file reading %s", type, exc, full_path)
        return r

    def _file_write(self, cr, uid, attachment, location, value):
        datas_value = value.decode('base64')
        size = len(datas_value)
        file_hash = hashlib.sha512(datas_value).hexdigest()
        # check if file already exists
        matches = self.browse(cr, 1, [('datas_hash','=',file_hash)])
        for m in matches:
            if m.file_size == size and m.datas == datas_value:
                return m.datas_hash, m.store_fname
        fname = '_'.join(attachment.datas_fname.split())
        full_path = self._full_path(cr, uid, attachment, location, fname)
        try:
            dirname = os.path.dirname(full_path)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(full_path,'wb') as datas:
                datas.write(datas_value)
        except IOError:
            _logger.error("_file_write writing %s",full_path)
        return file_hash, fname

    def _file_delete(self, cr, uid, attachment, location, fname):
        count = self.search(cr, 1, [('store_fname','=',fname)], count=True)
        if count <= 1:
            full_path = self._full_path(cr, uid, attachment, location, fname)
            try:
                os.unlink(full_path)
            except OSError:
                _logger.error("_file_delete could not unlink %s",full_path)
            except IOError:
                # Harmless and needed for race conditions
                _logger.error("_file_delete could not unlink %s",full_path)

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        location = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ir_attachment.location')
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if location and attach.store_fname:
                result[attach.id] = self._file_read(cr, uid, attach, location, attach.store_fname, bin_size)
            else:
                result[attach.id] = attach.db_datas
        return result

    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        # We dont handle setting data to null
        if not value:
            return True
        if context is None:
            context = {}
        location = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ir_attachment.location')
        file_size = len(value.decode('base64'))
        attach = self.browse(cr, uid, id, context=context)
        if not attach.res_model:
            raise ERPError('Programming Error', 'res_model has not been set')
        if attach.store_fname:
            self._file_delete(cr, uid, attach, location, attach.store_fname)
        if location and not context.get('migrate_to_db'):
            fhash, fname = self._file_write(cr, uid, attach, location, value)
            super(ir_attachment, self).write(
                    cr, uid, [id],
                    {'store_fname': fname, 'datas_hash': fhash, 'file_size': file_size, 'db_datas': False},
                    context=context,
                    )
        else:
            super(ir_attachment, self).write(
                    cr, uid, [id],
                    {'db_datas': value, 'file_size': file_size, 'store_fname':False, 'datas_hash':False},
                    context=context,
                    )
        return True

    _name = 'ir.attachment'
    _columns = {
        'name': fields.char('Attachment Name',size=256, required=True),
        'datas_fname': fields.char('File Name',size=256,help='original file name'),
        'datas_hash': fields.char('File hash (sha512)', size=128),
        'description': fields.text('Description'),
        'res_name': fields.function(_name_get_resname, type='char', size=128, string='Resource Name', store=True),
        'res_model': fields.char('Resource Model',size=64, readonly=True, help="The database object this attachment will be attached to"),
        'res_id': fields.integer('Resource ID', readonly=True, help="The record id this is attached to"),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Owner', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Modified by', readonly=True),
        'write_date':  fields.datetime('Date Modified', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', change_default=True),
        'type': fields.selection( [ ('url','URL'), ('binary','Binary'), ],
                'Type', help="Binary File or URL", required=True, change_default=True),
        'url': fields.char('Url', size=1024),
        # al: We keep shitty field names for backward compatibility with document
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),
        'store_fname': fields.char('Stored Filename', size=1024, help='file name on disk'),
        'db_datas': fields.binary('Database Data', help='file data stored in database'),
        'file_size': fields.integer('File Size'),
    }

    _defaults = {
        'type': 'binary',
        'file_size': 0,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'ir.attachment', context=c),
    }

    def _auto_init(self, cr, context=None):
        res = super(ir_attachment, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('ir_attachment_res_idx',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_attachment_res_idx ON ir_attachment (res_model, res_id)')
            cr.commit()
        return res

    def check(self, cr, uid, ids, mode, context=None, values=None):
        """Restricts the access to an ir.attachment, according to referred model
        In the 'document' module, it is overriden to relax this hard rule, since
        more complex ones apply there.
        """
        if not ids:
            return
        res_ids = {}
        if ids:
            if isinstance(ids, (int, long)):
                ids = [ids]
            cr.execute('SELECT DISTINCT res_model, res_id FROM ir_attachment WHERE id = ANY (%s)', (ids,))
            for rmod, rid in cr.fetchall():
                if not (rmod and rid):
                    continue
                res_ids.setdefault(rmod,set()).add(rid)
        if values:
            if 'res_model' in values and 'res_id' in values:
                res_ids.setdefault(values['res_model'],set()).add(values['res_id'])

        ima = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            # ignore attachments that are not attached to a resource anymore when checking access rights
            # (resource was deleted but attachment was not)
            mids = self.pool.get(model).exists(cr, uid, mids)
            ima.check(cr, uid, model, mode)
            self.pool.get(model).check_access_rule(cr, uid, mids, mode, context=context)

    def _search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        ids = super(ir_attachment, self)._search(cr, uid, args, offset=offset,
                                                 limit=limit, order=order,
                                                 context=context, count=False,
                                                 access_rights_uid=access_rights_uid)
        if not ids:
            if count:
                return 0
            return []

        # Work with a set, as list.remove() is prohibitive for large lists of documents
        # (takes 20+ seconds on a db with 100k docs during search_count()!)
        orig_ids = ids
        ids = set(ids)

        # For attachments, the permissions of the document they are attached to
        # apply, so we must remove attachments for which the user cannot access
        # the linked document.
        # Use pure SQL rather than read() as it is about 50% faster for large dbs (100k+ docs),
        # and the permissions are checked in super() and below anyway.
        cr.execute("""SELECT id, res_model, res_id FROM ir_attachment WHERE id = ANY(%s)""", (list(ids),))
        targets = cr.dictfetchall()
        model_attachments = {}
        for target_dict in targets:
            if not (target_dict['res_id'] and target_dict['res_model']):
                continue
            # model_attachments = { 'model': { 'res_id': [id1,id2] } }
            model_attachments.setdefault(target_dict['res_model'],{}).setdefault(target_dict['res_id'],set()).add(target_dict['id'])

        # To avoid multiple queries for each attachment found, checks are
        # performed in batch as much as possible.
        ima = self.pool.get('ir.model.access')
        for model, targets in model_attachments.iteritems():
            if not ima.check(cr, uid, model, 'read', False):
                # remove all corresponding attachment ids
                for attach_id in itertools.chain(*targets.values()):
                    ids.remove(attach_id)
                continue # skip ir.rule processing, these ones are out already

            # filter ids according to what access rules permit
            target_ids = targets.keys()
            allowed_ids = self.pool.get(model).search(cr, uid, [('id', 'in', target_ids)], context=context)
            disallowed_ids = set(target_ids).difference(allowed_ids)
            for res_id in disallowed_ids:
                for attach_id in targets[res_id]:
                    ids.remove(attach_id)

        # sort result according to the original sort ordering
        result = [id for id in orig_ids if id in ids]
        return len(result) if count else list(result)

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        self.check(cr, uid, ids, 'read', context=context)
        return super(ir_attachment, self).read(cr, uid, ids, fields_to_read, context, load)

    def write(self, cr, uid, ids, vals, context=None):
        self.check(cr, uid, ids, 'write', context=context, values=vals)
        if 'file_size' in vals:
            del vals['file_size']
        return super(ir_attachment, self).write(cr, uid, ids, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        self.check(cr, uid, [id], 'write', context=context)
        return super(ir_attachment, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None):
        self.check(cr, uid, ids, 'unlink', context=context)
        location = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ir_attachment.location')
        if location:
            for attach in self.browse(cr, uid, ids, context=context):
                if attach.store_fname:
                    self._file_delete(cr, uid, attach, location, attach.store_fname)
        return super(ir_attachment, self).unlink(cr, uid, ids, context)

    def create(self, cr, uid, values, context=None):
        self.check(cr, uid, [], mode='create', context=context, values=values)
        if 'file_size' in values:
            del values['file_size']
        return super(ir_attachment, self).create(cr, uid, values, context)

    def action_get(self, cr, uid, context=None):
        return self.pool.get('ir.actions.act_window').for_xml_id(
            cr, uid, 'base', 'action_attachment', context=context)

