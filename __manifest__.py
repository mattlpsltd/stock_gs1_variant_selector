
# -*- coding: utf-8 -*-
{
    "name": "GS1 Variant Selector (Stock)",
    "version": "19.0.1.0.2",
    "category": "Inventory/Barcode",
    "summary": "Template-first GS1 scanning with variant selection for stock pickings",
    "license": "LGPL-3",
    "author": "mattlpsltd",
    "website": "https://github.com/mattlpsltd/stock_gs1_variant_selector",
    "depends": [
        "web",
        "product",
        "stock",
        "barcodes",
        "stock_barcode",
    ],
    "data": [
        "views/product_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "stock_gs1_variant_selector/static/src/js/gs1_variant_selector.js",
            "stock_gs1_variant_selector/static/src/xml/gs1_variant_selector.xml",
        ],
        "stock_barcode.assets_backend": [
            "stock_gs1_variant_selector/static/src/js/gs1_variant_selector.js",
            "stock_gs1_variant_selector/static/src/xml/gs1_variant_selector.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "application": False,
    "installable": True,
}
