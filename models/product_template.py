
# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_shared_barcode = fields.Char(
        string="Shared GTIN",
        index=True,
        help="Template-level GTIN shared by all variants (canonical GTIN-14 recommended)."
    )
