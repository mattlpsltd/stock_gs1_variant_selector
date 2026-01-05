GS1 Variant Selector (Stock) — Final Package
===========================================

What this module does
---------------------
• Adds a Shared GTIN field (x_shared_barcode) on product templates.
• When scanning GS1 codes inside pickings (Receipts/Deliveries), matches the template by Shared GTIN, opens a variant selector if needed, and adds a demand-only move line.
• Carries lot/batch and best-before/expiry dates from GS1 AIs onto the lot and pre-creates a move line (qty_done=0) for tracked products.
• Frontend handler ensures the Barcode UI uses this template-first GS1 flow.

Install / Upgrade
-----------------
1) Copy the folder to your addons path
2) Update the module list
3) Install/Upgrade "GS1 Variant Selector (Stock)"

Notes
-----
• Tested and confirmed working on Odoo 19.0 Enterprise (builds from late 2025).
• After installation, hard reload the Barcode app with ?debug=assets if needed.
• Set the shared GTIN on the product template form to enable variant selection on scan.

Generated: 2025-12-22