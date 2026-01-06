
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime

class GS1VariantSelector(http.Controller):

    @http.route('/stock_gs1_variant_selector/resolve', type='json', auth='user')
    def resolve(self, gtin14=None, lot=None, expiry=None, qty=None, picking_id=None, chosen_variant_id=None, **kw):
        if not gtin14 or not picking_id:
            return {"error": "missing_params"}

        env = request.env
        Picking = env['stock.picking'].sudo()
        ProductT = env['product.template'].sudo()
        Product = env['product.product'].sudo()
        Move = env['stock.move'].sudo()
        MoveLine = env['stock.move.line'].sudo()
        LotModel = env['stock.production.lot'].sudo()

        try:
            picking = Picking.browse(int(picking_id))
        except Exception:
            picking = Picking.browse(False)
        if not picking.exists():
            return {"error": "picking_not_found"}

        # Find template by GTIN-14 (fallback 13 if needed)
        gtin13 = gtin14.lstrip('0') if gtin14 and gtin14.startswith('0') else gtin14
        tmpl = ProductT.search(['|', ('x_shared_barcode', '=', gtin14), ('x_shared_barcode', '=', gtin13)], limit=1)
        if not tmpl:
            return {"error": "template_not_found", "gtin14": gtin14}

        # Determine product (variant)
        product = None
        if chosen_variant_id:
            product = Product.browse(int(chosen_variant_id))
            if not product.exists():
                return {"error": "chosen_variant_not_found"}
            if product.product_tmpl_id.id != tmpl.id:
                return {"error": "variant_not_in_template"}
        else:
            variants = tmpl.product_variant_ids
            if len(variants) > 1:
                return {
                    "needs_variant_choice": True,
                    "template_id": tmpl.id,
                    "variant_ids": variants.ids,
                }
            product = variants[:1]
            if not product:
                return {"error": "no_variant"}

        # Quantity (default 1)
        qty_value = 1.0
        if qty:
            try:
                qn = float(qty)
                if qn > 0:
                    qty_value = qn
            except Exception:
                pass

        # Create demand move
        move_vals = {
            'name': product.display_name,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty_value,
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
        }
        move = Move.create(move_vals)

        # Tracked products → create/find lot and a move line (qty_done=0)
        lot_id = None
        if product.tracking != 'none' and lot:
            lot_rec = LotModel.search([('name', '=', lot), ('product_id', '=', product.id)], limit=1)
            if not lot_rec:
                lot_vals = {'name': lot, 'product_id': product.id}
                if expiry:
                    try:
                        lot_vals['life_date'] = datetime.strptime(expiry, '%y%m%d').date()
                    except Exception:
                        pass
                lot_rec = LotModel.create(lot_vals)
            lot_id = lot_rec.id

        MoveLine.create({
            'move_id': move.id,
            'product_id': product.id,
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_uom_id': product.uom_id.id,
            'qty_done': 0.0,
            'lot_id': lot_id,
        })

        return {
            'status': 'ok',
            'product_id': product.id,
            'template_id': tmpl.id,
            'move_id': move.id,
            'lot_id': lot_id,
        }
