# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'Issue Tracker',
    'version': '1.0',
    'category': 'Project Management',
    'sequence': 9,
    'summary': 'Support, Bug Tracker, Helpdesk',
    'description': """
Track Issues/Bugs Management for Projects
=========================================
This application allows you to manage the issues you might face in a project like bugs in a system, client complaints or material breakdowns.

It allows the manager to quickly check the issues, assign them and decide on their status quickly as they evolve.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/issue_analysis.jpeg','images/project_issue.jpeg'],
    'depends': [
        'base_status',
        'crm',
        'project',
    ],
    'data': [
        'project_issue_view.xml',
        'project_issue_menu.xml',
        'report/project_issue_report_view.xml',
        'security/project_issue_security.xml',
        'security/ir.model.access.csv',
        'board_project_issue_view.xml',
        'res_config_view.xml',
        'project_issue_data.xml'
     ],
    'demo': ['project_issue_demo.xml'],
    'test': [
        'test/subscribe_issue.yml',
        'test/issue_process.yml',
        'test/cancel_issue.yml',
        'test/issue_demo.yml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

