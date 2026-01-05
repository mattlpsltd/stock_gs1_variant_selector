
# -*- coding: utf-8 -*-
{
    'name': 'GS1 Variant Selector (Stock)',
    'summary': 'Scan GS1 (AI 01/02) to find product templates by shared GTIN, pick variant, and create receipt/delivery lines.',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Barcode',
    'author': 'Matthew Nunn + M365 Copilot',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'product',
        'stock_barcode',  # Enterprise barcode app
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_gs1_variant_selector/static/src/js/gs1_variant_selector.js',
        ],
    },
    'installable': True,
    'application': False,
}
