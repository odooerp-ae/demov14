{
    'name': 'Restrict Sales Order for Out of Stock Items',
    'description': 'Restrict Sales Order for Out of Stock Items',
    'version': '13.0.0',
    'website': '',
    'depends': [
        'sale_stock',
    ],
    'data': [
        "views/product_category_views.xml",
    ],
    'application': False,
    'installable': True,
}