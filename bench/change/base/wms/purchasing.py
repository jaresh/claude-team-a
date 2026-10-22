"""Purchase orders."""
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import NotFound, UserError, ZERO, cost4, floor_unit, fq, money, parse_cost, parse_qty
from .ledger import mv_json
from .stock import do_receive, split_serials


def po_get(ctx, po):
    r = ctx.one("SELECT * FROM pos WHERE id=?", po)
    if not r:
        raise NotFound(f"unknown purchase order {po}")
    return r


def po_received(ctx, po, line):
    return sum((Decimal(m["qty"]) for m in ctx.q(
        "SELECT qty FROM movements WHERE type='receive' AND ref=? AND line=? AND voided=0", po, line)), ZERO)


def po_status(ctx, po):
    r = po_get(ctx, po)
    if r["closed"]:
        return "closed"
    lines = ctx.q("SELECT * FROM po_lines WHERE po=?", po)
    got = [po_received(ctx, po, x["line"]) for x in lines]
    if all(g >= Decimal(x["qty"]) for g, x in zip(got, lines)):
        return "received"
    return "partial" if any(g > 0 for g in got) else "open"


def po_show(ctx, po):
    r = po_get(ctx, po)
    lines = []
    for x in ctx.q("SELECT * FROM po_lines WHERE po=? ORDER BY line", po):
        unit = ctx.product(x["sku"])["unit"]
        got = po_received(ctx, po, x["line"])
        open_ = ZERO if r["closed"] else max(Decimal(x["qty"]) - got, ZERO)
        lines.append({"line": x["line"], "sku": x["sku"], "ordered": x["qty"], "received": fq(got, unit),
                      "open": fq(open_, unit), "unit_cost": x["unit_cost"]})
    value = sum((Decimal(m["value"]) for m in ctx.q(
        "SELECT value FROM movements WHERE type='receive' AND ref=? AND voided=0", po)), ZERO)
    return {"id": po, "supplier": r["supplier"], "warehouse": r["wh"], "status": po_status(ctx, po),
            "lines": lines, "value_received": money(value)}


def po_create(ctx, supplier, wh, lines):
    if not (supplier or "").strip():
        raise UserError("a supplier is needed")
    ctx.warehouse(wh)
    if not lines:
        raise UserError("at least one line is needed")
    parsed = []
    for spec in lines:
        parts = spec.split(":")
        if len(parts) != 3:
            raise UserError(f"bad line {spec!r}: use SKU:QTY:UNITCOST")
        p = ctx.product(parts[0])
        parsed.append((p["sku"], fq(parse_qty(parts[1], p["unit"]), p["unit"]), cost4(parse_cost(parts[2]))))
    po = ctx.next_doc("PO")
    ctx.ex("INSERT INTO pos VALUES(?, ?, ?, 0)", po, supplier.strip(), wh)
    for n, (sku, q, c) in enumerate(parsed, 1):
        ctx.ex("INSERT INTO po_lines VALUES(?, ?, ?, ?, ?)", po, n, sku, q, c)
    ctx.audit("po.create", po)
    return po_show(ctx, po)


def po_receive(ctx, po, line, qty_s, at, lot=None, expires=None, serials=None):
    r = po_get(ctx, po)
    if po_status(ctx, po) in ("received", "closed"):
        raise UserError(f"{po} is {po_status(ctx, po)}")
    x = ctx.one("SELECT * FROM po_lines WHERE po=? AND line=?", po, int(line))
    if not x:
        raise NotFound(f"{po} has no line {line}")
    loc = ctx.location(at)
    if loc["wh"] != r["wh"]:
        raise UserError(f"{po} is for warehouse {r['wh']}")
    p = ctx.product(x["sku"])
    qty = parse_qty(qty_s, p["unit"])
    limit = floor_unit(Decimal(x["qty"]) * Decimal("1.05"), p["unit"])
    if po_received(ctx, po, x["line"]) + qty > limit:
        raise UserError(f"over-receipt: line {line} takes at most {fq(limit, p['unit'])}")
    m = do_receive(ctx, x["sku"], qty_s, at, None, lot, expires, split_serials(serials), po, x["line"],
                   Decimal(x["unit_cost"]))
    ctx.audit("po.receive", po)
    return mv_json(m)


def po_close(ctx, po):
    if po_status(ctx, po) not in ("open", "partial"):
        raise UserError(f"{po} is {po_status(ctx, po)}")
    ctx.ex("UPDATE pos SET closed=1 WHERE id=?", po)
    ctx.audit("po.close", po)
    return po_show(ctx, po)


def po_list(ctx, status=None):
    out = [po_show(ctx, r["id"]) for r in ctx.q("SELECT id FROM pos ORDER BY id")]
    return [x for x in out if not status or x["status"] == status]
