
# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    x_shared_barcode = fields.Char(
        string='Shared GTIN',
        related='product_tmpl_id.x_shared_barcode',
        store=True,
        readonly=False,
        index=True,
    )
