from odoo import models, api, fields
from datetime import date

class StockPickingAdd(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def add_variant_from_selector(self, picking_id, product_id, qty=None,
                                  best_before=None, expiry=None, sscc=None, lot_batch=None):
        picking = self.browse(picking_id)
        picking.ensure_one()
        product = self.env['product.product'].browse(product_id)
        qty = float(qty or 1.0)

        # Demand-only: set requested quantity on the move, let operators validate qty_done later
        move = self.env['stock.move'].create({
            'name': product.display_name,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
        })
        move._action_confirm()
        move._action_assign()

        lot = False
        if product.tracking != 'none':
            lot_name = lot_batch or sscc or ''
            if lot_name:
                lot = self.env['stock.production.lot'].search(
                    [('name', '=', lot_name), ('product_id', '=', product.id)], limit=1
                )
                if not lot:
                    lot = self.env['stock.production.lot'].create({'name': lot_name, 'product_id': product.id})

            def _to_date(yymmdd):
                y, m, d = int(yymmdd[0:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
                century = 2000 if y <= 49 else 1900
                return date(century + y, m, d)

            try:
                if best_before and len(best_before) == 6 and best_before.isdigit():
                    lot.use_date = fields.Date.to_string(_to_date(best_before))
                if expiry and len(expiry) == 6 and expiry.isdigit() and hasattr(lot, 'life_date'):
                    lot.life_date = fields.Date.to_string(_to_date(expiry))
            except Exception:
                pass

        # Do not set qty_done here. If a lot is present, pre-create a move line with qty_done=0 for later validation
        if lot:
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'qty_done': 0.0,
                'lot_id': lot.id,
            })

        return True