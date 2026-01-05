
# -*- coding: utf-8 -*-
from odoo import api, models, fields
from datetime import date
import re

FNC1 = ""

class GS1Helper(models.AbstractModel):
    _name = 'stock_gs1_variant_selector.gs1_helper'
    _description = 'GS1 Parsing/Lookup Helper'

    # --- Parsing ------------------------------------------------------------
    @api.model
    def parse_gs1(self, raw: str) -> dict:
        """
        Best-effort GS1 parser supporting common AIs used here:
        (01) GTIN (14 fixed)
        (02) Contained GTIN (14 fixed)
        (15) Best before (YYMMDD fixed)
        (37) Count (<=8 digits, variable)
        (10) Lot (<=20, variable; ends at FNC1 or end)
        Accepts bracketed form and unbracketed with FNC1 separators.
        """
        if not raw:
            return {}
        ai = {}
        s = raw
        # Normalize: if bracketed, split by brackets.
        if '(' in s and ')' in s:
            # bracketed tokens like (01)123...(10)LOT... etc.
            tokens = re.findall(r'\((\d{2})\)([^\(]+)', s)
            for k, v in tokens:
                ai[k] = v.replace(FNC1, '')
            return ai
        # unbracketed: we walk through by known-length patterns and FNC1
        i = 0
        n = len(s)
        def take(nch):
            nonlocal i
            v = s[i:i+nch]
            i += nch
            return v
        def take_to_fnc1(maxlen=20):
            nonlocal i
            j = i
            while j < n and s[j] != FNC1 and (j - i) < maxlen:
                j += 1
            v = s[i:j]
            i = j + (1 if j < n and s[j] == FNC1 else 0)
            return v
        while i < n:
            if i+2 > n:
                break
            k = s[i:i+2]
            i += 2
            if k == '01' or k == '02':
                ai[k] = take(14)
            elif k == '15':
                ai[k] = take(6)
            elif k == '37':
                # up to 8 digits; stop at FNC1 or end
                start = i
                while i < n and s[i].isdigit() and (i-start) < 8:
                    i += 1
                ai[k] = s[start:i]
                if i < n and s[i] == FNC1:
                    i += 1
            elif k == '10':
                ai[k] = take_to_fnc1(20)
            else:
                # Unknown AI; try to skip to next FNC1 or stop
                while i < n and s[i] != FNC1:
                    i += 1
                if i < n and s[i] == FNC1:
                    i += 1
        return ai

    @api.model
    def get_lookup_gtin(self, ai: dict) -> str:
        return ai.get('01') or ai.get('02') or ''

    @api.model
    def parse_expiry(self, ai: dict):
        d = ai.get('15')
        if not d or len(d) != 6:
            return False
        try:
            yy = int(d[0:2]); mm = int(d[2:4]); dd = int(d[4:6])
            year = 2000 + yy
            return date(year, mm, dd)
        except Exception:
            return False

    @api.model
    def parse_lot(self, ai: dict):
        lot = ai.get('10')
        return lot or False

    @api.model
    def get_contained_qty(self, ai: dict):
        q = ai.get('37')
        try:
            return float(q) if q is not None and q != '' else 1.0
        except Exception:
            return 1.0

    # --- Lookups ------------------------------------------------------------
    @api.model
    def find_template_by_shared_gtin(self, gtin: str):
        if not gtin:
            return self.env['product.template']
        return self.env['product.template'].search([
            ('x_shared_barcode', '=', gtin)
        ], limit=1)
