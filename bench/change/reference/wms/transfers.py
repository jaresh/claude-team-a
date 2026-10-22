"""Transfers between warehouses."""
import json
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import NotFound, UserError, fq, parse_qty
from .ledger import add_movement
from .stock import check_tracking, split_serials, take_check


def tr_get(ctx, tr):
    r = ctx.one("SELECT * FROM transfers WHERE id=?", tr)
    if not r:
        raise NotFound(f"unknown transfer {tr}")
    return r


def tr_json(r):
    return {"id": r["id"], "sku": r["sku"], "qty": r["qty"], "from": r["src"], "to": r["dst"], "lot": r["lot"],
            "serials": json.loads(r["serials"] or "[]"), "status": r["status"], "value": r["value"]}


def transfer_create(ctx, sku, qty_s, src, dst, lot=None, serials=None):
    p = ctx.product(sku)
    qty = parse_qty(qty_s, p["unit"])
    a, b = ctx.location(src), ctx.location(dst)
    if a["type"] != "storage":
        raise UserError("transfers leave from a storage location")
    if b["type"] not in ("storage", "receiving"):
        raise UserError("transfers arrive in a storage or receiving location")
    if a["wh"] == b["wh"]:
        raise UserError("a transfer goes to a different warehouse")
    serials = check_tracking(ctx, p, qty, lot, split_serials(serials))
    take_check(ctx, p, qty, src, lot, serials)
    tr = ctx.next_doc("TR")
    ctx.ex("INSERT INTO transfers VALUES(?, ?, ?, ?, ?, ?, ?, 'in_transit', NULL)", tr, sku, fq(qty, p["unit"]),
           src, dst, lot, json.dumps(sorted(serials)))
    m = add_movement(ctx, "transfer-out", sku, qty, src, None, lot, serials, ref=tr)
    ctx.ex("UPDATE transfers SET value=? WHERE id=?", m["value"], tr)
    ctx.audit("transfer.create", tr)
    return tr_json(tr_get(ctx, tr))


def transfer_finish(ctx, tr, cancel):
    r = tr_get(ctx, tr)
    if r["status"] != "in_transit":
        raise UserError(f"{tr} is {r['status']}")
    dest = r["src"] if cancel else r["dst"]
    add_movement(ctx, "transfer-in", r["sku"], Decimal(r["qty"]), None, dest, r["lot"],
                 json.loads(r["serials"] or "[]"), ref=tr)
    ctx.ex("UPDATE transfers SET status=? WHERE id=?", "cancelled" if cancel else "received", tr)
    ctx.audit("transfer.cancel" if cancel else "transfer.receive", tr)
    return tr_json(tr_get(ctx, tr))


def transfer_list(ctx, status=None):
    return [tr_json(r) for r in ctx.q("SELECT * FROM transfers ORDER BY id") if not status or r["status"] == status]
