
# -*- coding: utf-8 -*-
from odoo import api

def post_init_hook(env):
    """Normalize legacy 13-digit shared GTINs to GTIN-14 by prefixing '0'."""
    templates = env['product.template'].search([])
    for tmpl in templates:
        code = (tmpl.x_shared_barcode or '').strip()
        if code and code.isdigit() and len(code) == 13:
            tmpl.write({'x_shared_barcode': '0' + code})
