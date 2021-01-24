{
    'name': 'Restrict Sales Order for Out of Stock Items',
    'description': 'Restrict Sales Order for Out of Stock Items',
    'version': '14.0.0',
    "author": "Oakland",
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
