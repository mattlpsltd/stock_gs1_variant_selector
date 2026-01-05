from odoo import models, api

class StockBarcodeGs1Service(models.AbstractModel):
    _name = 'stock.gs1.service'
    _description = 'GS1 helper for barcode scanning'

    @api.model
    def interpret(self, scan: str):
        decoder = self.env['stock.gs1.decode']
        parsed = decoder.decode(scan)
        gtin = parsed.get('02') or parsed.get('01')
        lot = parsed.get('10')
        expiry = parsed.get('17')
        best_before = parsed.get('15')
        count = parsed.get('37')
        sscc = parsed.get('00')

        product = False
        template = False
        candidates = self.env['product.product']
        if gtin:
            template = self.env['product.template'].search([('x_shared_barcode', '=', gtin)], limit=1)
            if template:
                candidates = template.product_variant_ids
            else:
                product = self.env['product.product'].search([('barcode', '=', gtin)], limit=1)

        return {
            'parsed': parsed,
            'template_id': template.id if template else False,
            'product_id': product.id if product else False,
            'candidate_ids': candidates.ids,
            'lot': lot,
            'best_before': best_before,
            'expiry': expiry,
            'sscc': sscc,
            'count': int(count) if count and str(count).isdigit() else False,
        }