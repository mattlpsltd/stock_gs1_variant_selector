
# -*- coding: utf-8 -*-
from odoo import models
import re


class Gs1Decode(models.AbstractModel):
    """
    Decode GS1 Application Identifiers (AIs) from a scanned string.

    Supports both:
      - Parenthesized AIs:     (01)01234567890123(10)BATCH123(17)251231
      - Concatenated with FNC1: ]C10101234567890123\x1d10BATCH123\x1d17 251231

    Notes:
    - Removes AIM symbology identifier at the start (e.g., ]C1, ]d2, ]Q3).
    - Fixed-length AIs read exactly the specified length.
    - Variable-length AIs read up to FNC1, '(' (start of next AI), or max length.
    - For variable AIs we ALWAYS store the captured value even if there is no FNC1.
    """
    _name = 'stock.gs1.decode'
    _description = 'Decode GS1 AIs from scanned string'

    # Fixed-length AIs (length in characters). None means variable-length.
    _FIXED = {
        '00': 18,  # SSCC
        '01': 14,  # GTIN
        '02': 14,  # GTIN of contents
        '15': 6,   # Best before (YYMMDD)
        '17': 6,   # Expiry (YYMMDD)
        '37': None # Count (variable up to FNC1)
    }

    # Explicit set of variable-length AIs we care about with larger max length.
    _VAR = {'10'}  # Batch/Lot — variable, up to 20 characters by spec

    # Regex to strip AIM Symbology Identifier at the start, e.g. ]C1, ]d2, ]Q3
    AIM_PREFIX = re.compile(r'^\][A-Za-z]\d')

    FNC1 = '\x1d'  # Group Separator used as FNC1 in GS1-128 encodings

    # --- helpers ----------------------------------------------------------------

    def _normalize(self, s: str) -> str:
        """Trim, remove spaces, drop leading AIM identifier."""
        if not s:
            return ''
        s = s.strip().replace(' ', '')
        # remove AIM symbology identifier if present at the very beginning
        s = self.AIM_PREFIX.sub('', s)
        return s

    # --- public API -------------------------------------------------------------

    def decode(self, raw: str):
        """
        Return a dict of parsed AIs -> values.
        Example:
            decode(']C10101234567890123(10)BATCH123(17)251231')
            -> {'01': '01234567890123', '10': 'BATCH123', '17': '251231'}
        """
        s = self._normalize(raw)
        i, n = 0, len(s)
        out = {}

        def take(k: int):
            nonlocal i
            i += k

        while i < n:
            # --- Read AI code (either "(xx...)" or concatenated "xx") -----------
            if s[i] == '(':
                j = s.find(')', i + 1)
                if j == -1:
                    # malformed "(..."; stop parsing
                    break
                ai = s[i + 1:j]
                take(j - i + 1)  # consume "(AI)"
            else:
                ai = s[i:i + 2]
                take(2)

            if not ai.isdigit():
                # Skip any unexpected fragment and continue scanning
                # (robustness against noise in the stream)
                continue

            # --- Fixed-length AI ------------------------------------------------
            if ai in self._FIXED and self._FIXED[ai] is not None:
                length = self._FIXED[ai]
                if i + length > n:
                    # incomplete value; stop parsing
                    break
                value = s[i:i + length]
                take(length)
                if value:
                    out[ai] = value
                continue

            # --- Variable-length AI (e.g., 10 lot/batch) or unknown variable ----
            if ai in self._VAR or self._FIXED.get(ai) is None:
                start = i
                # Lot/batch (AI 10) can be up to 20 chars; unknown vars up to 8 as a safety cap
                max_len = 20 if ai in self._VAR else 8

                # Read until FNC1, next '(' (start of a new "(AI)"), or max_len reached
                while i < n and (s[i] != self.FNC1) and (s[i] != '(') and (i - start) < max_len:
                    i += 1

                value = s[start:i]

                # If we stopped on FNC1, consume it
                if i < n and s[i] == self.FNC1:
                    i += 1

                # IMPORTANT: Always keep the captured value even without FNC1
                if value:
                    out[ai] = value
                continue

            # --- Unhandled AI with unexpected configuration ---------------------
            # Skip forward until a delimiter (FNC1) or '(' which denotes next AI
            while i < n and s[i] not in (self.FNC1, '('):
                i += 1
            if i < n and s[i] == self.FNC1:
                i += 1

        return out
