
/** @odoo-module **/

import { registry } from '@web/core/registry';

function startGs1Interceptor(env) {
  const services = env.services || {};
  const barcode = services.barcode;
  const rpc     = services.rpc;
  const user    = services.user;
  const action  = services.action;

  console.log('[GS1] service starting', { hasBarcode: !!barcode, hasRpc: !!rpc, ctx: user?.context });

  if (!barcode || !rpc || !user) {
    console.warn('[GS1] required services missing', { barcode: !!barcode, rpc: !!rpc, user: !!user });
    return {};
  }

  const isLikelyGS1 = (code) => /(\(0[12]\)|^(01|02))/.test(code);
  const activePickingId = () => (user.context?.active_model === 'stock.picking' ? user.context.active_id : null);

  async function handleScan(code) {
    const pickingId = activePickingId();
    if (pickingId) {
      console.debug('[GS1] inside picking → /scan', { pickingId, code });
      try {
        const res = await rpc('/stock_gs1_variant_selector/scan', { barcode: code, picking_id: pickingId });
        console.debug('[GS1] /scan response', res);
        return res && res.status === 'ok';
      } catch (e) {
        console.error('[GS1] /scan failed', e);
        return false;
      }
    } else {
      console.debug('[GS1] receipts home → /open_receipt', { code });
      try {
        const res = await rpc('/stock_gs1_variant_selector/open_receipt', { barcode: code });
        console.debug('[GS1] /open_receipt response', res);
        if (res && res.status === 'open_picking' && res.picking_id) {
          await action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'stock.picking',
            res_id: res.picking_id,
            views: [[false, 'form']],
            target: 'current',
          });
          return true;
        }
        return false;
      } catch (e) {
        console.error('[GS1] /open_receipt failed', e);
        return false;
      }
    }
  }

  // 1) Barcode service bus listener
  barcode.bus.addEventListener('barcode_scanned', async (ev) => {
    const code = ev.detail?.barcode || '';
    if (!isLikelyGS1(code)) return;
    console.debug('[GS1] bus event barcode_scanned', { code });

    ev.stopPropagation();
    const ok = await handleScan(code);
    if (!ok) {
      console.debug('[GS1] handing back to default handlers');
      barcode.bus.dispatchEvent(new CustomEvent('barcode_scanned', { detail: { barcode: code } }));
    }
  });

  // 2) Document-level capture (safety net for camera modal timing)
  document.addEventListener('barcode_scanned', async (ev) => {
    const code = ev.detail?.barcode || '';
    if (!isLikelyGS1(code)) return;
    console.debug('[GS1] document capture barcode_scanned', { code });

    ev.stopPropagation();
    const ok = await handleScan(code);
    if (!ok) {
      console.debug('[GS1] handing back (document-level)');
      barcode.bus.dispatchEvent(new CustomEvent('barcode_scanned', { detail: { barcode: code } }));
    }
  }, { capture: true });

  console.log('[GS1] service started');
  return {};
}

registry.category('services').add('gs1_interceptor', { start: startGs1Interceptor });

console.log('[GS1] file loaded');
