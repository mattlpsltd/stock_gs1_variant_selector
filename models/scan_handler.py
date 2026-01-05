
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

# Toggle: accept plain GTIN (no AIs) as variant barcode fallback when GS1 parsing fails
SCAN_FALLBACK_ACCEPT_PLAIN_GTIN = True

class GS1ScanHandler(models.Model):
    _name = 'stock_gs1_variant_selector.scan_handler'
    _description = 'GS1 Scan Handler'

    @api.model
    def handle_scan(self, raw_barcode: str, picking_id: int):
        """Main entry for scans from the barcode UI.
        Returns a dict with status and optional instructions for the UI.
        """
        picking = self.env['stock.picking'].browse(picking_id)
        if not picking or not picking.exists():
            return {'status': 'error', 'message': _('Picking not found')}

        helper = self.env['stock_gs1_variant_selector.gs1_helper']
        ai = helper.parse_gs1(raw_barcode or '')
        gtin = helper.get_lookup_gtin(ai)

        # 1) Template by shared GTIN (from 01 or 02)
        tmpl = helper.find_template_by_shared_gtin(gtin)

        # 2) If not found, try variant barcode (works when user put GTIN on variant)
        variant = False
        if not tmpl:
            if gtin:
                variant = self.env['product.product'].search([('barcode', '=', gtin)], limit=1)
                if variant:
                    tmpl = variant.product_tmpl_id
            # Fallback: if GS1 parse failed entirely and allowed, try raw barcode match
            if not tmpl and SCAN_FALLBACK_ACCEPT_PLAIN_GTIN and raw_barcode and raw_barcode.isdigit():
                variant = self.env['product.product'].search([('barcode', '=', raw_barcode)], limit=1)
                if variant:
                    tmpl = variant.product_tmpl_id

        if not tmpl:
            return {'status': 'error', 'message': _('Product not found for scanned code')}

        # Multi-variant? let UI ask the user which variant
        if not variant and len(tmpl.product_variant_ids) > 1:
            return {
                'status': 'select_variant',
                'template_id': tmpl.id,
                'variants': [
                    {'id': p.id, 'name': p.display_name}
                    for p in tmpl.product_variant_ids
                ],
                'ai': ai,
            }

        # Single variant or already decided
        product = variant or tmpl.product_variant_id
        return self._apply_scan_to_picking(product, picking, ai)

    # Called when the user confirms a variant (UI dialog)
    @api.model
    def confirm_variant(self, variant_id: int, picking_id: int, ai: dict):
        picking = self.env['stock.picking'].browse(picking_id)
        product = self.env['product.product'].browse(variant_id)
        if not picking or not product:
            return {'status': 'error', 'message': _('Invalid selection')}
        return self._apply_scan_to_picking(product, picking, ai or {})

    # Internal helpers -------------------------------------------------------
    def _apply_scan_to_picking(self, product, picking, ai: dict):
        helper = self.env['stock_gs1_variant_selector.gs1_helper']
        qty = helper.get_contained_qty(ai)
        expiry = helper.parse_expiry(ai)
        lot_name = helper.parse_lot(ai)

        lot = False
        if product.tracking in ('lot', 'serial') and lot_name:
            lot = self.env['stock.lot'].search([
                ('name', '=', lot_name),
                ('product_id', '=', product.id)
            ], limit=1)
            if not lot:
                lot_vals = {'name': lot_name, 'product_id': product.id}
                if expiry:
                    lot_vals['life_date'] = fields.Date.to_string(expiry)
                lot = self.env['stock.lot'].create(lot_vals)

        move = self._ensure_move(product, picking, qty)
        ml_vals = {
            'picking_id': picking.id,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'qty_done': 0.0,
        }
        if lot:
            ml_vals['lot_id'] = lot.id
        ml = self.env['stock.move.line'].create(ml_vals)

        return {
            'status': 'ok',
            'move_id': move.id,
            'move_line_id': ml.id,
            'message': _('Added line for %s (planned +%s)') % (product.display_name, qty),
        }

    def _ensure_move(self, product, picking, qty):
        Move = self.env['stock.move']
        move = Move.search([
            ('picking_id', '=', picking.id),
            ('product_id', '=', product.id),
            ('state', 'in', ['draft', 'confirmed', 'assigned'])
        ], limit=1)
        if move:
            # In 19.0 the planned quantity field remains product_uom_qty
            move.product_uom_qty = move.product_uom_qty + qty
        else:
            move = Move.create({
                'name': product.display_name,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'product_uom_qty': qty,
            })
        return move
