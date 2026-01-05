
/** @odoo-module **/
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { Component, onMounted } from '@odoo/owl';

/**
 * Minimal hook that watches for barcode scans when a stock.picking form is open.
 * If the code looks like GS1 with (01)/(02), call our server endpoint to resolve
 * by template shared GTIN; if multiple variants, show a small selector.
 */

class GS1VariantSelector extends Component {
    setup() {
        this.action = useService('action');
        this.rpc = useService('rpc');
        this.barcode = useService('barcode');
        this.orm = useService('orm');
        onMounted(() => {
            // Subscribe to scans
            this.barcode.bus.addEventListener('barcode_scanned', this._onScan);
        });
    }

    _isLikelyGS1(code) {
        // Heuristic: contains bracketed AIs or starts with 01/02 and long length
        return /\(0[12]\)/.test(code) || /^(01|02)/.test(code);
    }

    _activePickingId() {
        // Try reading context: if a stock.picking is open, context holds active_id
        const ctx = this.env.services.user?.context || {};
        return ctx.active_model === 'stock.picking' ? ctx.active_id : null;
    }

    _showVariantDialog(pickingId, ai, variants) {
        const self = this;
        class Selector extends Component {
            setup() { this.state = { variant_id: variants[0]?.id }; }
            confirm() {
                self.rpc('/stock_gs1_variant_selector/confirm', {
                    variant_id: this.state.variant_id,
                    picking_id: pickingId,
                    ai: ai,
                }).then(() => this.props.close());
            }
        }
        Selector.template = 'stock_gs1_variant_selector.VariantSelector';
        Dialog.add(this.env, Selector, {
            title: 'Select variant',
            size: 'md',
        }, { close: () => {} }, { variants });
    }

    _onScan = (ev) => {
        const code = ev.detail.barcode || '';
        const pickingId = this._activePickingId();
        if (!pickingId) return; // only handle when a picking form is open
        if (!this._isLikelyGS1(code)) return; // let default handlers process non-GS1

        ev.stopPropagation();
        this.rpc('/stock_gs1_variant_selector/scan', {
            barcode: code,
            picking_id: pickingId,
        }).then((res) => {
            if (!res) return;
            if (res.status === 'select_variant') {
                this._showVariantDialog(pickingId, res.ai, res.variants);
            } else if (res.status === 'ok') {
                // no-op; server already created move/move line
            } else if (res.status === 'error') {
                // fall back to default if not ours
                this.barcode.bus.dispatchEvent(new CustomEvent('barcode_scanned', { detail: { barcode: code } }));
            }
        }).catch(() => {
            // On error, re-dispatch to default handlers
            this.barcode.bus.dispatchEvent(new CustomEvent('barcode_scanned', { detail: { barcode: code } }));
        });
    }
}

// Register as a startup service-like hook in webclient
registry.category('main_components').add('stock_gs1_variant_selector_hook', GS1VariantSelector);

// Minimal template for the dialog (rendered via Dialog.add)
import { qweb } from '@web/core/qweb';
qweb.addTemplate(`
<t t-name="stock_gs1_variant_selector.VariantSelector">
  <div class="o_form">
    <label class="mb-2">Choose a variant:</label>
    <select t-model="state.variant_id" class="form-select">
      <t t-foreach="props.variants" t-as="v" t-key="v.id">
        <option t-att-value="v.id"><t t-esc="v.name"/></option>
      </t>
    </select>
    <div class="mt-3">
      <button class="btn btn-primary" t-on-click="confirm">Add</button>
    </div>
  </div>
</t>
`);
