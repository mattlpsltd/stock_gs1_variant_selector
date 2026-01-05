/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const gs1Handler = {
  async onBarcodeScanned(barcode) {
    const orm = this.orm ?? useService("orm");
    const notification = this.notification ?? useService("notification");

    // Normalize barcode: trim and remove spaces
    barcode = barcode.trim().replace(/\s/g, '');

    // NEW: Handle plain 14-digit GTINs (most common supplier labels)
    if (/^\d{14}$/.test(barcode)) {
      const pickingId = (this.props?.picking?.id) || (this.picking?.id) || false;
      if (!pickingId) return false;

      // Direct search for template with shared barcode
      const templates = await orm.searchRead(
        "product.template",
        [["x_shared_barcode", "=", barcode]],
        ["product_variant_ids"]
      );

      if (templates.length > 0) {
        const template = templates[0];
        const candidate_ids = template.product_variant_ids || [];

        if (candidate_ids.length === 1) {
          // Auto-add single variant
          await orm.call("stock.picking", "add_variant_from_selector", [], {
            picking_id: pickingId,
            product_id: candidate_ids[0],
            qty: 1,
          });
          notification.add(_t("Product added."), { type: "success" });
          return true;
        } else if (candidate_ids.length > 1) {
          // Open selector
          const action = {
            type: "ir.actions.client",
            tag: "open_variant_selector",
            params: {
              picking_id: pickingId,
              product_ids: candidate_ids,
              qty: 1,
            },
          };
          await this.env.services.action.doAction(action);
          return true;
        }
      }
      // If no shared template found, fall through to GS1 or default
    }

    // Existing GS1 logic (keep as-is)
    try {
      const res = await orm.call("stock.gs1.service", "interpret", [], { scan: barcode });
      const pickingId = (this.props?.picking?.id) || (this.picking?.id) || false;
      if (!pickingId) return false;

      if (res && res.template_id && !res.product_id && res.candidate_ids?.length > 0) {
        const action = {
          type: "ir.actions.client",
          tag: "open_variant_selector",
          params: {
            picking_id: pickingId,
            product_ids: res.candidate_ids,
            qty: res.count || 1,
            best_before: res.best_before || false,
            expiry: res.expiry || false,
            sscc: res.sscc || false,
            lot_batch: res.lot || false,
          },
        };
        await this.env.services.action.doAction(action);
        return true;
      }

      if (res && res.product_id) {
        await orm.call("stock.picking", "add_variant_from_selector", [], {
          picking_id: pickingId,
          product_id: res.product_id,
          qty: res.count || 1,
          best_before: res.best_before || false,
          expiry: res.expiry || false,
          sscc: res.sscc || false,
          lot_batch: res.lot || false,
        });
        notification.add(_t("Variant added to picking."), { type: "success" });
        return true;
      }

      return false; // fall back
    } catch (err) {
      console.error(err);
      return false;
    }
  },
};

registry.category("barcode_handlers").add("gs1_shared_gtin_handler", gs1Handler, { sequence: 5 });  // Even higher priority
export default gs1Handler;