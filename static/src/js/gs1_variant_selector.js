
/** @odoo-module **/

import { registry } from "@web/core/registry";

const services = registry.category("services");
let _cleanupFns = [];

/** Microtask-based debounce: avoids setTimeout entirely */
function debounceMicro(fn) {
    let scheduled = false;
    let lastArgs = null;
    return (...args) => {
        lastArgs = args;
        if (scheduled) return;
        scheduled = true;
        Promise.resolve().then(() => {
            scheduled = false;
            fn(...lastArgs);
        });
    };
}

/** Limit logic to backend picking/barcode contexts */
function isPickingBarcodeContext(env) {
    try {
        const ctrl = env.services.action.currentController;
        const action = ctrl?.action;
        const xmlId = action?.xml_id || "";
        return (
            xmlId.includes("stock_barcode") ||
            xmlId.includes("stock.picking") ||
            action?.tag === "picking_barcode"
        );
    } catch {
        return false;
    }
}

// --- Helpers: GTIN check digit (GS1 Mod-10) and normalization to GTIN-14 ---
function gtinCheckDigit(gtinWithoutCheck) {
    const s = String(gtinWithoutCheck);
    let sum = 0;
    for (let i = s.length - 1, pos = 0; i >= 0; i--, pos++) {
        const n = s.charCodeAt(i) - 48;
        sum += (pos % 2 === 0) ? n * 3 : n;
    }
    const mod = sum % 10;
    return mod === 0 ? 0 : 10 - mod;
}
function isAllDigits(str) { return /^[0-9]+$/.test(str); }
function normalizeNumericToGTIN14(raw) {
    const s = String(raw).trim();
    if (!isAllDigits(s)) return null;
    if (![12,13,14].includes(s.length)) return null;
    const body = s.slice(0, -1);
    const cd = s.slice(-1);
    const expected = gtinCheckDigit(body);
    if (String(expected) !== cd) return null;
    return s.padStart(14, "0");
}
/** Normalize GS1 input to {gtin14, lot, expiry} */
function normalizeGs1(raw) {
    const str = String(raw).trim();
    // AI(01), AI(10), AI(17) with or without FNC1 separators
    const ai01 = str.match(/\(01\)\s*([0-9]{14})/) || str.match(/(?:^|)01([0-9]{14})/);
    const ai10 = str.match(/\(10\)\s*([^\(\)]+?)(?:|$)/) || str.match(/(?:^|)10([^]+)(?:|$)/);
    const ai17 = str.match(/\(17\)\s*([0-9]{6})/) || str.match(/(?:^|)17([0-9]{6})/);
    if (ai01) {
        return { gtin14: ai01[1], lot: ai10 ? ai10[1] : null, expiry: ai17 ? ai17[1] : null };
    }
    const gtin14 = normalizeNumericToGTIN14(str);
    if (gtin14) return { gtin14, lot: null, expiry: null };
    return null;
}

function currentPickingId(env) {
    try {
        const ctrl = env.services.action.currentController;
        const context = ctrl?.env?.config || ctrl?.props?.context || {};
        return context?.active_id || context?.default_picking_id || null;
    } catch { return null; }
}

async function handleGs1Scan(env, rpc, user, rawScan) {
    const parsed = normalizeGs1(rawScan);
    if (!parsed?.gtin14) return;
    const result = await rpc("/stock_gs1_variant_selector/resolve", {
        json: {
            gtin14: parsed.gtin14,
            lot: parsed.lot || null,
            expiry: parsed.expiry || null,
            picking_id: currentPickingId(env),
        },
    });
    if (result?.needs_variant_choice) {
        // TODO: open a variant selector and then call backend to create move
        env.services.notification.add(
            "Multiple variants share this GTIN. Please select the correct variant.",
            { type: "warning" }
        );
    } else if (result?.status === 'ok') {
        env.services.notification.add("GS1 scan applied to receipt.", { type: "success" });
    } else {
        env.services.notification.add("GS1 scan could not be applied.", { type: "danger" });
    }
}

function attachInputHandler(container, env, rpc, user) {
    const input =
        container.querySelector("input.o_barcode_input, input[name='barcode']") ||
        document.querySelector("input.o_barcode_input, input[name='barcode']");
    if (!input) return;

    const onKeydownCapture = async (ev) => {
        if (ev.key !== "Enter") return;
        const raw = input.value || "";
        const parsed = normalizeGs1(raw);
        if (!parsed?.gtin14) return;
        ev.stopImmediatePropagation?.();
        ev.stopPropagation();
        ev.preventDefault();
        input.value = "";
        try { await handleGs1Scan(env, rpc, user, raw); } catch (e) { console.warn("[GS1] error", e); }
    };
    input.addEventListener("keydown", onKeydownCapture, true);

    const onInput = async (ev) => {
        const raw = ev.target?.value || "";
        const parsed = normalizeGs1(raw);
        if (!parsed?.gtin14) return;
        ev.stopImmediatePropagation?.();
        ev.stopPropagation();
        ev.preventDefault();
        ev.target.value = "";
        try { await handleGs1Scan(env, rpc, user, raw); } catch (e) { console.warn("[GS1] error", e); }
    };
    input.addEventListener("input", onInput);
    input.addEventListener("change", onInput);

    _cleanupFns.push(() => {
        input.removeEventListener("keydown", onKeydownCapture, true);
        input.removeEventListener("input", onInput);
        input.removeEventListener("change", onInput);
    });
}

function bootstrapGS1(env, rpc, user) {
    console.log("[GS1] file loaded");

    const mo = new MutationObserver(() => {
        if (!isPickingBarcodeContext(env)) return;
        const container =
            document.querySelector(".o_barcode_view, .o_stock_barcode_main") ||
            document.querySelector(".o_barcode_main_container");
        if (!container) return;
        mo.disconnect();

        const onRawScan = debounceMicro(async (raw) => {
            try { await handleGs1Scan(env, rpc, user, raw); } catch (e) { console.warn("[GS1] error", e); }
        });

        // Custom event hook if needed
        const onCustomScan = (ev) => { const raw = ev?.detail?.raw; if (raw) onRawScan(raw); };
        container.addEventListener("gs1:raw_scan", onCustomScan);
        _cleanupFns.push(() => container.removeEventListener("gs1:raw_scan", onCustomScan));

        attachInputHandler(container, env, rpc, user);
        _cleanupFns.push(() => { try { mo.disconnect(); } catch {} });
    });

    mo.observe(document.body, { childList: true, subtree: true });
    _cleanupFns.push(() => { try { mo.disconnect(); } catch {} });
}

function teardownGS1() { for (const fn of _cleanupFns) { try { fn(); } catch {} } _cleanupFns = []; }

services.add("gs1_interceptor", {
    dependencies: ["rpc", "user", "notification", "action"],
    start(env, { rpc, user }) {
        if (env.services.__gs1InterceptorInstalled) return {};
        env.services.__gs1InterceptorInstalled = true;
        bootstrapGS1(env, rpc, user);
        return { dispose() { teardownGS1(); env.services.__gs1InterceptorInstalled = false; } };
    },
});
