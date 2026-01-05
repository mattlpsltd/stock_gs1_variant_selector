from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_shared_barcode = fields.Char(
        string="Shared Barcode (GTIN)", index=True,
        help="Place the generic GTIN here when the barcode identifies a template with multiple variants."
    )