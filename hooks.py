
# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

# Pad 13-digit numeric GTINs to canonical GTIN-14 by prefixing '0'

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    templates = env['product.template'].search([])
    for tmpl in templates:
        code = (tmpl.x_shared_barcode or '').strip()
        if code and code.isdigit() and len(code) == 13:
            tmpl.write({'x_shared_barcode': '0' + code})
