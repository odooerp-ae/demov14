
{
    'name': 'Sales With Measurement Requests',
    'summary': 'Measurement Requests',
    'version': '14.0.1.0.0',
    'category': 'Sales',
    'depends': [
        'sale_mrp',
        'account_accountant',
        'hr',
        'base_automation',
        'sale_quotation_number',
    ],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'wizard/sale_order_reject.xml',
        'views/measurement_views.xml',
        'views/payment_views.xml',
        'views/sale_views.xml',
        'views/so_reject_reasons.xml',
        'views/setting_views.xml',
        'views/partner_views.xml',
        'views/picking_views.xml',
        'reports/measurement_report.xml',
    ],
    'installable': True,

}
