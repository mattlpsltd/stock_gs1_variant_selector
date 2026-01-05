
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class VariantSelectorDialog extends Component {
  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.state = useState({ loading: true, search: "", items: [], selectedId: null });

    onWillStart(async () => {
      const ids = this.props.product_ids ?? [];
      if (!ids.length) {
        this.state.loading = false;
        return;
      }
      const fields = ["display_name", "default_code", "barcode"];
      this.state.items = await this.orm.searchRead("product.product", [["id", "in", ids]], fields);
      this.state.loading = false;
    });
  }

  get filteredItems() {
    const s = (this.state.search ?? "").toLowerCase();
    if (!s) return this.state.items;
    return this.state.items.filter(
      (it) =>
        (it.display_name ?? "").toLowerCase().includes(s) ||
        (it.default_code ?? "").toLowerCase().includes(s) ||
        (it.barcode ?? "").toLowerCase().includes(s)
    );
  }

  select(id) {
    this.state.selectedId = id;
  }

  async confirm() {
    const product = this.state.items.find((i) => i.id === this.state.selectedId) || this.filteredItems[0];
    if (!product) {
      this.notification.add(_t("Please select a variant."), { type: "warning" });
      return;
    }
    try {
      const args = [
        this.props.picking_id,
        product.id,
        this.props.qty ?? 1,
        this.props.best_before ?? false,
        this.props.expiry ?? false,
        this.props.sscc ?? false,
        this.props.lot_batch ?? false,
      ];
      await this.orm.call("stock.picking", "add_variant_from_selector", args);
      this.notification.add(_t("Variant added to picking."), { type: "success" });
      this.props.close();
    } catch (err) {
      console.error(err);
      this.notification.add(_t("Failed to add variant."), { type: "danger" });
    }
  }

  cancel() {
    this.props.close();
  }
}

VariantSelectorDialog.template = "stock_gs1_variant_selector.VariantSelectorDialog";

registry.category("actions").add("open_variant_selector", (env, action) => {
  const params = action.params ?? {};
  const dialogProps = { title: _t("Select Variant"), size: "md" };
  return env.services.dialog.add(VariantSelectorDialog, params, dialogProps);
});

export default VariantSelectorDialog;
