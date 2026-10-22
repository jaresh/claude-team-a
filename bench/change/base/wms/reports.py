"""Costing reports: valuation and aging."""
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import ZERO, fq, money, parse_date, parse_time, wh_of
from .ledger import load_movements, replay


def cut_for(ctx, at):
    parse_time(at)
    r = ctx.one("SELECT MAX(id) AS m FROM movements WHERE at<?", at)
    return r["m"] or 0


def valuation(ctx, wh=None, at=None):
    if wh:
        ctx.warehouse(wh)
    mvs = load_movements(ctx, cut_for(ctx, at) if at else None)
    e = replay(ctx, mvs)
    units = {r["sku"]: r["unit"] for r in ctx.q("SELECT sku, unit FROM products")}
    rows = []
    for sku, w in sorted(set(e.layers) | set(e.avg), key=lambda k: (k[1], k[0])):
        if wh and w != wh:
            continue
        qty, value = e.stock_value(sku, w)
        if qty > 0:
            rows.append({"sku": sku, "warehouse": w, "qty": fq(qty, units[sku]), "value": money(value)})
    done = {m["ref"] for m in mvs if m["type"] == "transfer-in"}
    transit = []
    for tr in ctx.q("SELECT * FROM transfers ORDER BY id"):
        if tr["id"] in e.tr_out and tr["id"] not in done:
            if wh and wh not in (wh_of(tr["src"]), wh_of(tr["dst"])):
                continue
            transit.append({"transfer": tr["id"], "sku": tr["sku"], "qty": tr["qty"],
                            "value": money(e.tr_out[tr["id"]][1])})
    total = sum((Decimal(r["value"]) for r in rows + transit), ZERO)
    return {"rows": rows, "in_transit": transit, "total": money(total)}


def aging(ctx, wh, on=None):
    ctx.warehouse(wh)
    day = parse_date(on) if on else ctx.today
    e = replay(ctx, load_movements(ctx))
    out = []
    for (sku, w), layers in sorted(e.layers.items()):
        if w != wh:
            continue
        b = {"0-30": ZERO, "31-90": ZERO, "91+": ZERO}
        any_left = False
        for layer in layers:
            if layer.rem <= 0:
                continue
            any_left = True
            age = (day - date.fromisoformat(layer.time[:10])).days
            b["0-30" if age <= 30 else "31-90" if age <= 90 else "91+"] += layer.rem * layer.cost
        if any_left:
            out.append({"sku": sku, **{k: money(v) for k, v in b.items()}})
    return out
