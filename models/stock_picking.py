from odoo import models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        decoded = self.env['stock.gs1.decode'].decode(barcode)

        gtin = decoded.get('02') or decoded.get('01')
        if not gtin:
            return super().on_barcode_scanned(barcode)

        qty = float(decoded.get('37') or 1.0)
        best_before_15 = decoded.get('15')
        expiry_17 = decoded.get('17')
        sscc_00 = decoded.get('00')
        lot_batch_10 = decoded.get('10')

        Product = self.env['product.product']
        Template = self.env['product.template']

        # 1) Shared template barcode (preferred)
        templates = Template.search([('x_shared_barcode', '=', gtin)])

        # 2) Fallback template barcode
        if not templates:
            templates = Template.search([('barcode', '=', gtin)])

        candidates = templates.mapped('product_variant_ids')

        # 3) Variant-level fallback
        if not candidates:
            candidates = Product.search([('barcode', '=', gtin)])

        if len(candidates) <= 1:
            chosen = candidates and candidates[0] or False
            if chosen:
                return self.add_variant_from_selector(
                    self.id, chosen.id, qty,
                    best_before=best_before_15,
                    expiry=expiry_17,
                    sscc=sscc_00,
                    lot_batch=lot_batch_10,
                )
            return super().on_barcode_scanned(barcode)

        return {
            'type': 'ir.actions.client',
            'tag': 'open_variant_selector',
            'params': {
                'picking_id': self.id,
                'product_ids': candidates.ids,
                'qty': qty,
                'best_before': best_before_15,
                'expiry': expiry_17,
                'sscc': sscc_00,
                'lot_batch': lot_batch_10,
            },
        }
