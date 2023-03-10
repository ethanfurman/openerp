# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

class knowledge_config_settings(osv.osv_memory):
    _name = 'knowledge.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'module_document_page': fields.boolean('Create static pages',
            help=dedent("""
                Use an HTML editor to create pages.
                This installs the module document_page.
                """).strip()),
        'module_wiki': fields.boolean('Create wiki pages',
            help=dedent("""
                Use a plain editor and markdown to create cross-linkable
                pages which can include images.
                This installs the module wiki.
                """).strip()),
        'module_document': fields.boolean('Manage documents',
            help=dedent("""
                This is a complete document management system, with: user authentication,
                full document search (but pptx and docx are not supported), and a document dashboard.
                This installs the module document.
                """).strip()),
        'module_document_ftp': fields.boolean('Share repositories (FTP)',
            help=dedent("""
                Access your documents in OpenERP through an FTP interface.
                This installs the module document_ftp.
                """).strip()),
        'module_document_webdav': fields.boolean('Share repositories (WebDAV)',
            help=dedent("""
                Access your documents in OpenERP through WebDAV.
                This installs the module document_webdav.
                """).strip()),
        }

