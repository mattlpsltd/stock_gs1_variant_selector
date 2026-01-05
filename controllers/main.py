
# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class GS1ScanController(http.Controller):

    @http.route('/stock_gs1_variant_selector/scan', type='json', auth='user')
    def scan(self, barcode: str, picking_id: int):
        """Apply a GS1 scan to the active picking (template-first lookup)."""
        try:
            handler = request.env['stock_gs1_variant_selector.scan_handler']
            return handler.handle_scan(barcode, picking_id)
        except Exception:
            _logger.exception('GS1 scan handler failed')
            return {'status': 'error', 'message': 'Internal error while processing scan'}

    @http.route('/stock_gs1_variant_selector/confirm', type='json', auth='user')
    def confirm(self, variant_id: int, picking_id: int, ai: dict):
        """Confirm the selected variant and apply GS1 AIs (37/15/10)."""
        try:
            handler = request.env['stock_gs1_variant_selector.scan_handler']
            return handler.confirm_variant(variant_id, picking_id, ai)
        except Exception:
            _logger.exception('GS1 variant confirmation failed')
            return {'status': 'error', 'message': 'Internal error while confirming variant'}

    @http.route('/stock_gs1_variant_selector/open_receipt', type='json', auth='user')
    def open_receipt(self, barcode: str):
        """From Receipts home, try to open an existing incoming picking by Shared GTIN."""
        try:
            helper = request.env['stock_gs1_variant_selector.gs1_helper']
            ai = helper.parse_gs1(barcode or '')
            gtin = (helper.get_lookup_gtin(ai) or '').strip()
            tmpl = helper.find_template_by_shared_gtin(gtin)

            if not tmpl and gtin:
                variant = request.env['product.product'].search([('barcode', '=', gtin)], limit=1)
                tmpl = variant.product_tmpl_id if variant else False

            if not tmpl:
                return {'status': 'error', 'message': 'No template/variant for GTIN'}

            product_ids = tmpl.product_variant_ids.ids
            Move = request.env['stock.move']
            incoming_types = request.env['stock.picking.type'].search([('code', '=', 'incoming')]).ids
            move = Move.search([
                ('product_id', 'in', product_ids),
                ('picking_id.picking_type_id', 'in', incoming_types),
                ('picking_id.state', 'in', ['waiting', 'confirmed', 'assigned']),
            ], limit=1)
            if move:
                picking = move.picking_id[:1]
                return {'status': 'open_picking', 'picking_id': int(picking.id)}
            return {'status': 'error', 'message': 'No receipts ready for this product'}
        except Exception:
            _logger.exception('open_receipt failed')
            return {'status': 'error', 'message': 'Internal error while locating receipt'}
