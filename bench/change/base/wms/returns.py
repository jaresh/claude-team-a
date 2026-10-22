"""Returns against shipped sales orders."""
import json
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import NotFound, UserError, ZERO, cost4, fq, money, parse_qty, r2, r4
from .ledger import add_movement
from .orders import line_figures, so_get
from .stock import check_tracking, split_serials


def rt_json(r):
    return {"id": r["id"], "order": r["so"], "line": r["line"], "sku": r["sku"], "qty": r["qty"],
            "condition": r["condition"], "to": r["dst"], "lot": r["lot"], "serials": json.loads(r["serials"] or "[]"),
            "unit_cost": r["unit_cost"], "value": r["value"], "credit": r["credit"]}


def return_create(ctx, so, line, qty_s, condition, to=None, lot=None, serials=None):
    r = so_get(ctx, so)
    x = ctx.one("SELECT * FROM so_lines WHERE so=? AND line=?", so, int(line))
    if not x:
        raise NotFound(f"{so} has no line {line}")
    p = ctx.product(x["sku"])
    qty = parse_qty(qty_s, p["unit"])
    if condition not in ("good", "damaged"):
        raise UserError("condition is good or damaged")
    ships = ctx.q("SELECT * FROM movements WHERE type='ship' AND ref=? AND line=?", so, x["line"])
    shipped = sum((Decimal(m["qty"]) for m in ships), ZERO)
    returned = line_figures(ctx, so, x["line"])[3]
    if qty > shipped - returned:
        raise UserError(f"at most {fq(shipped - returned, p['unit'])} can be returned")
    serials = check_tracking(ctx, p, qty, lot, split_serials(serials))
    if p["tracking"] == "lot" and lot not in {m["lot"] for m in ships}:
        raise UserError(f"lot {lot} wasn't shipped on that line")
    if p["tracking"] == "serial":
        sent = {s for m in ships for s in json.loads(m["serials"])}
        back = {s for y in ctx.q("SELECT serials FROM returns WHERE so=? AND line=?", so, x["line"])
                for s in json.loads(y["serials"])}
        for s in serials:
            if s not in sent or s in back:
                raise UserError(f"serial {s} wasn't shipped on that line, or is back already")
    uc = r4(sum((Decimal(m["value"]) for m in ships), ZERO) / shipped)
    rt = ctx.next_doc("RT")
    value = r2(0)
    if condition == "good":
        if not to:
            raise UserError("a good return needs --to")
        loc = ctx.location(to)
        if loc["wh"] != r["wh"] or loc["type"] != "storage":
            raise UserError(f"returns go to a storage location of {r['wh']}")
        m = add_movement(ctx, "return", x["sku"], qty, None, to, lot, serials, uc, ref=rt)
        value = Decimal(m["value"])
    else:
        to = None
    credit = r2(qty * Decimal(x["net"]) / Decimal(x["qty"]))
    ctx.ex("INSERT INTO returns VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rt, so, x["line"], x["sku"],
           fq(qty, p["unit"]), condition, to, lot, json.dumps(sorted(serials)), cost4(uc), money(value), money(credit))
    ctx.audit("return.create", rt)
    return rt_json(ctx.one("SELECT * FROM returns WHERE id=?", rt))


def return_list(ctx, so=None):
    return [rt_json(r) for r in ctx.q("SELECT * FROM returns ORDER BY id") if not so or r["so"] == so]


def audit_list(ctx, action=None, user=None):
    return [{"seq": r["seq"], "at": r["at"], "user": r["user"], "action": r["action"], "target": r["target"]}
            for r in ctx.q("SELECT * FROM audit ORDER BY seq")
            if (not action or r["action"] == action) and (not user or r["user"] == user)]
