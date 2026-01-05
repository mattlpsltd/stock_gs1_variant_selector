
# -*- coding: utf-8 -*-
{
    'name': 'GS1 Variant Selector (Stock)',
    'summary': 'Scan GS1 (AI 01/02) → find product by template Shared GTIN, open variant, create stock lines.',
    'version': '19.0.1.2.0',
    'category': 'Inventory/Barcode',
    'author': 'Matthew Nunn',
    'license': 'LGPL-3',
    'depends': ['stock', 'product', 'stock_barcode'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_gs1_variant_selector/static/src/js/gs1_variant_selector.js',
        ],
        # Include for barcode pages as well (harmless if bundle not defined)
        'stock_barcode.assets_backend': [
            'stock_gs1_variant_selector/static/src/js/gs1_variant_selector.js',
        ],
    },
    'installable': True,
    'application': False,
}
