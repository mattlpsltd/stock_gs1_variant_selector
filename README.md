
# GS1 Variant Selector (Stock) for Odoo 19

A minimal Odoo 19 Enterprise add-on that lets you scan **GS1 barcodes** with **AI (01) or (02)** and match products by a **shared GTIN** stored on the **product template** (`x_shared_barcode`). If multiple variants exist, the module can prompt for a **variant selection**; it then pre-creates a **move**/**move line** on the active **Receipt/Delivery** and carries **lot (10)** and **best-before (15)** values.

> Tested against Odoo **19.0+e** (Dec 2025 builds). Adjust asset hooks if Odoo changes the barcode app bundles.

---

## Features
- **Template-level GTIN** (`x_shared_barcode` on `product.template`).
- Accepts **AI (01)** or **AI (02)**; prefers (01), falls back to (02).
- Uses **(37)** as contained quantity when scanning cartons (02).
- Maps **(15)** → best-before (YYMMDD) and **(10)** → lot (variable length, FNC1-aware).
- Creates/extends the **planned quantity** on a matching move; adds a **move line** with `qty_done = 0` for operator confirmation.
- Optional **variant selector** (simple dialog) if multiple variants exist.

> References:
> - Odoo 19 GS1 documentation (nomenclature, FNC1, AI patterns): https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/barcode/operations/gs1_nomenclature.html
> - OCA Stock Barcodes GS1 (behaviour reference for (02)+(37)): https://odoo-community.org/shop/stock-barcodes-gs1-4984

---

## Installation
1. Copy this directory to your Odoo **addons path**.
2. Update Apps list and install **GS1 Variant Selector (Stock)**.
3. In **Inventory → Settings → Barcode**:
   - Enable **Barcode Scanner**.
   - Set **Barcode Nomenclature = Default GS1 Nomenclature**.
4. On product **template**, set **Shared Barcode (GTIN)** to the 14-digit GTIN (no AI prefix).
5. Hard-reload assets if needed (`?debug=assets`).

---

## Usage
- Create/ensure an inbound **Receipt** exists for your product.
- Scan a **GS1** barcode with either of:
  - Unit: `(01)05010663817070(15)260509`
  - Carton: `(02)05010663817070(15)260509(37)0290`
- If several variants exist under the template, a small **variant picker** appears; select one to create a line.

If your scanner outputs **plain GTIN** without AIs, Odoo treats it as a plain barcode (not GS1). You can enable the optional fallback (see `SCAN_FALLBACK_ACCEPT_PLAIN_GTIN` in `scan_handler.py`).

---

## Notes
- This module **does not** replace Odoo’s built-in barcode flows; it enhances product lookup and move-line creation when scanning GS1 strings.
- Depending on your Odoo Enterprise build, the barcode app’s asset bundle names may differ. If the variant dialog doesn’t trigger, the server-side still handles scans via the `/stock_gs1_variant_selector/scan` endpoint. You can integrate scan routing in your environment or adapt the small JS hook included.

## License
LGPL-3. See `LICENSE`.
