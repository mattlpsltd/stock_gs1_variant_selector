
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { renderToFragment } from "@web/core/utils/render";

const services = registry.category("services");
let _cleanupFns = [];

// ---- GS1-128 parser essentials ----
const FNC1 = "";
const AI_RULES = {
  "01": { len: 14, var: false }, // GTIN-14
  "02": { len: 14, var: false }, // GTIN-14 of contained trade items
  "10": { len: 20, var: true  }, // Lot/Batch up to 20 chars
  "17": { len: 6,  var: false }, // Expiry YYMMDD
  "37": { len: 8,  var: true  }, // Count up to 8 digits
};
const isDigits = (t) => /^[0-9]+$/.test(t);

function gs1CheckDigit14(body){
  const s = String(body); let sum = 0;
  for (let i = s.length - 1, pos = 0; i >= 0; i--, pos++) {
    const n = s.charCodeAt(i) - 48;
    sum += (pos % 2 === 0) ? n * 3 : n;
  }
  const mod = sum % 10; return mod === 0 ? 0 : 10 - mod;
}

function parseGs1ElementString(raw){
  if (!raw) return null;
  let s = String(raw).trim();
  s = s.replace(/\(|\)/g, ""); // drop brackets if present
  const out = {}; let i = 0;
  while (i < s.length) {
    let ai = s.slice(i, i+2);
    if (!AI_RULES[ai] && i+3 <= s.length) ai = s.slice(i, i+3);
    if (!AI_RULES[ai] && i+4 <= s.length) ai = s.slice(i, i+4);
    const rule = AI_RULES[ai];
    if (!rule) break;
    i += ai.length;
    if (rule.var) {
      const maxLen = rule.len; let j = i;
      while (j < s.length && (j - i) < maxLen && s[j] !== FNC1) j++;
      out[ai] = s.slice(i, j);
      if (j < s.length && s[j] === FNC1) j++;
      i = j;
    } else {
      const value = s.slice(i, i + rule.len);
      if (value.length < rule.len) break;
      out[ai] = value; i += rule.len;
      if (s[i] === FNC1) i++;
    }
  }
  return out;
}

function normalizeNumericToGTIN14(raw){
  const s = String(raw).trim();
  if (!isDigits(s) || ![12,13,14].includes(s.length)) return null;
  const body = s.slice(0, -1); const cd = s.slice(-1);
  return String(gs1CheckDigit14(body)) === cd ? s.padStart(14, "0") : null;
}

function normalizeGs1(raw){
  const parsed = parseGs1ElementString(raw);
  if (parsed) {
    const gtin14 = parsed["01"] || parsed["02"]; // accept AI(01) or AI(02)
    const lot = parsed["10"] || null; const expiry = parsed["17"] || null; const qty = parsed["37"] || null;
    if (gtin14 && isDigits(gtin14) && gtin14.length === 14) {
      return { gtin14, lot, expiry, qty };
    }
  }
  const gtin14 = normalizeNumericToGTIN14(String(raw).replace(//g, ""));
  return gtin14 ? { gtin14, lot: null, expiry: null, qty: null } : null;
}

function currentPickingId(env){
  try {
    const ctrl = env.services.action.currentController;
    const ctx = ctrl?.env?.config || ctrl?.props?.context || {};
    return ctx?.active_id || ctx?.default_picking_id || null;
  } catch { return null; }
}

async function openVariantSelector(env, payload){
  const { rpc, notification } = env.services;
  const { gtin14, lot, expiry, qty, variant_ids } = payload;

  // Fetch info for display
  const variants = await rpc('/web/dataset/call_kw/product.product/read', {
    model: 'product.product', method: 'read', args: [variant_ids, ['display_name','uom_id']], kwargs: {}
  }).then(rows => rows.map(r => ({ id: r.id, display_name: r.display_name, uom_name: r.uom_id?.[1] || '', attribute_string: '' })));

  const onSelect = async (v) => {
    try {
      const res = await rpc('/stock_gs1_variant_selector/resolve', {
        json: {
          gtin14, lot, expiry, qty: qty ? (Number(qty)||1) : 1,
          picking_id: currentPickingId(env),
          chosen_variant_id: v.id,
        },
      });
      if (res?.status === 'ok') notification?.add('Variant selected and move created.', { type: 'success' });
      dlg.close();
    } catch (e) {
      notification?.add('Could not create move for selected variant.', { type: 'danger' });
    }
  };

  const content = renderToFragment('stock_gs1_variant_selector.VariantSelector', {
    title: 'Select Variant', subtitle: 'Multiple variants share this template.',
    gtin14, lot, expiry, qty, variants, onSelect,
  });

  const dlg = new Dialog(env, { title: 'Variant Selector', size: 'lg', body: content, buttons: [{ text: 'Close', classes: 'btn-secondary', close: true }] });
  dlg.open();
}

async function handleGs1Scan(env, raw){
  const parsed = normalizeGs1(raw);
  if (!parsed?.gtin14) return;
  const { rpc, user, notification } = env.services || {};
  if (!rpc || !user) { console.warn('[GS1] rpc/user not ready; skipping'); return; }

  const res = await rpc('/stock_gs1_variant_selector/resolve', {
    json: { gtin14: parsed.gtin14, lot: parsed.lot, expiry: parsed.expiry, qty: parsed.qty ? (Number(parsed.qty)||1) : 1, picking_id: currentPickingId(env) },
  });

  if (res?.needs_variant_choice) {
    await openVariantSelector(env, { ...parsed, ...res });
  } else if (res?.status === 'ok') {
    notification?.add('GS1-128 scan applied to receipt.', { type: 'success' });
  } else {
    notification?.add('GS1-128 scan could not be applied.', { type: 'danger' });
  }
}

function attachGlobalCapture(env){
  const onKeydownCapture = async (ev) => {
    if (ev.key !== 'Enter') return;
    const active = document.activeElement;
    const raw = (active && ('value' in active)) ? active.value : '';
    const parsed = normalizeGs1(raw);
    if (!parsed?.gtin14) return;
    ev.stopImmediatePropagation?.(); ev.stopPropagation(); ev.preventDefault();
    if (active && ('value' in active)) active.value = '';
    try { await handleGs1Scan(env, raw); } catch (e) { console.warn('[GS1] error at global capture', e); }
  };
  document.addEventListener('keydown', onKeydownCapture, true);
  _cleanupFns.push(() => document.removeEventListener('keydown', onKeydownCapture, true));
}

function attachInputHandler(container, env){
  const input = container.querySelector('input.o_barcode_input, input[name='barcode']') || document.querySelector('input.o_barcode_input, input[name='barcode']');
  if (!input) return;
  const onInput = async (ev) => {
    const raw = ev.target?.value || '';
    const parsed = normalizeGs1(raw);
    if (!parsed?.gtin14) return;
    ev.stopImmediatePropagation?.(); ev.stopPropagation(); ev.preventDefault(); ev.target.value = '';
    try { await handleGs1Scan(env, raw); } catch (e) { console.warn('[GS1] error', e); }
  };
  input.addEventListener('input', onInput);
  input.addEventListener('change', onInput);
  _cleanupFns.push(() => { input.removeEventListener('input', onInput); input.removeEventListener('change', onInput); });
}

function isPickingBarcodeContext(env){
  try {
    const ctrl = env.services.action.currentController; const act = ctrl?.action; const xmlId = act?.xml_id || '';
    return xmlId.includes('stock_barcode') || xmlId.includes('stock.picking') || act?.tag === 'picking_barcode';
  } catch { return false; }
}

function bootstrapGS1(env){
  console.log('[GS1] file loaded');
  const mo = new MutationObserver(() => {
    if (!isPickingBarcodeContext(env)) return;
    const container = document.querySelector('.o_barcode_view, .o_stock_barcode_main') || document.querySelector('.o_barcode_main_container');
    if (!container) return; mo.disconnect();
    attachInputHandler(container, env);
    _cleanupFns.push(() => { try { mo.disconnect(); } catch {} });
  });
  mo.observe(document.body, { childList: true, subtree: true });
  _cleanupFns.push(() => { try { mo.disconnect(); } catch {} });
  attachGlobalCapture(env);
}

function teardownGS1(){ for (const fn of _cleanupFns) { try { fn(); } catch {} } _cleanupFns = []; }

services.add('gs1_interceptor', {
  dependencies: [],
  start(env){
    if (env.services.__gs1InterceptorInstalled) return {};
    env.services.__gs1InterceptorInstalled = true;
    bootstrapGS1(env);
    return { dispose(){ teardownGS1(); env.services.__gs1InterceptorInstalled = false; } };
  },
});
