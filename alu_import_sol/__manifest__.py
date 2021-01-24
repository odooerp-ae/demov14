# -*- coding: utf-8 -*-
{
    'name': 'Aluminum Import SOL/BOM',
    'version': '14.0.0.0',
    'summary': 'import sale order lines from excel or csv',
    'category': 'Sales',
    'description': """
    """,
    'author': 'Oakland',
    'depends': ['base', 'sale_management'],
    'data': [
                'security/ir.model.access.csv',
                'views/import_order_lines_view.xml',
                'views/setting_views.xml',
            ],
    'demo': [],
    'test': [],
    'installable':True,
    'auto_install':False,
    'application':True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
