
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class GS1ScanController(http.Controller):
    @http.route('/stock_gs1_variant_selector/scan', type='json', auth='user')
    def scan(self, barcode: str, picking_id: int):
        handler = request.env['stock_gs1_variant_selector.scan_handler']
        return handler.handle_scan(barcode, picking_id)

    @http.route('/stock_gs1_variant_selector/confirm', type='json', auth='user')
    def confirm(self, variant_id: int, picking_id: int, ai: dict):
        handler = request.env['stock_gs1_variant_selector.scan_handler']
        return handler.confirm_variant(variant_id, picking_id, ai)
