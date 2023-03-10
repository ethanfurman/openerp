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
    'name': 'Employee Directory',
    'version': '1.1',
    'author': 'OpenERP SA',
    'category': 'Human Resources',
    'sequence': 21,
    'website': 'http://www.openerp.com',
    'summary': 'Jobs, Departments, Employees Details',
    'description': """
Human Resources Management
==========================

This application enables you to manage important aspects of your company's staff and other details such as their skills, contacts, working time...


You can manage:
---------------
* Employees and hierarchies : You can define your employee with User and display hierarchies
* HR Departments
* HR Jobs
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': [
        'images/hr_department.jpeg',
        'images/hr_employee.jpeg',
        'images/hr_job_position.jpeg',
        'static/src/img/default_image.png',
    ],
    'depends': ['base_setup', 'base', 'mail', 'resource', 'board'],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'hr_data.xaml',
        'board_hr_view.xml',
        'hr_view.xaml',
        'hr_department_view.xml',
        'process/hr_process.xml',
        'hr_installer.xml',
        'res_config_view.xml',
    ],
    'demo': ['hr_demo.xml'],
    'test': [
        'test/open2recruit2close_job.yml',
        'test/hr_demo.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'css': [ 'static/src/css/hr.css' ],
}
