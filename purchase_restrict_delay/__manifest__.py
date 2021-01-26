# -*- coding: utf-8 -*-
{
    'name': 'Purchase Restrict Delay',
    'version': '14.0.0.0',
    'summary': '',
    'category': 'Purchases',
    'description': """
    Send notification mail for confirm  RFQ after limited period,
    Also Send notification mail if po is not fully delivered after limited period,
    """,
    'author': 'Oakland',
    'depends': ['purchase'],
    'data': [
                'data/mail_templates.xml',
                'data/ir_cron_data.xml',
                'views/setting_views.xml',
            ],
    'demo': [],
    'test': [],
    'installable':True,
    'auto_install':False,
    'application':True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
