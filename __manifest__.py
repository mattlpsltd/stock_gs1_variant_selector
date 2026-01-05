# -*- coding: utf-8 -*-
{
    'name': 'GS1 Variant Selector (Stock)',
    'version': '19.0.1.4.0',
    'license': 'AGPL-3',
    'summary': 'GS1 scan with variant selection in Barcode; shared GTIN on template via x_shared_barcode; demand-only lines',
    'description': """
        Enables scanning of GS1 barcodes that use a shared GTIN identifying a product template with multiple variants.
        When scanned in the Barcode app, it opens a clean variant selector if needed.
        Automatically handles lot/batch (AI 10), expiry/best-before (AI 15/17), quantity (AI 37), and SSCC (AI 00).
        Creates demand-only moves and pre-fills lots with dates.
    """,
    'author': 'Matthew Nunn',
    'category': 'Inventory/Barcode',
    'depends': ['stock', 'barcodes', 'product'],
    'data': [
        'views/product_template_barcode_editable.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_gs1_variant_selector/static/src/js/gs1_barcode_handler.js',
            'stock_gs1_variant_selector/static/src/js/variant_selector_dialog.js',
            'stock_gs1_variant_selector/static/src/xml/variant_selector_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
}