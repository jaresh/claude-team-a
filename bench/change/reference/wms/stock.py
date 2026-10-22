"""Stock movements: receive, move, adjust, scrap, void."""
import json
import re
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import NotFound, UserError, ZERO, parse_cost, parse_date, parse_qty, parse_time, wh_of
from .ledger import add_movement, current_stock, free_at, load_movements, mv_json, reserved_map, unit_keys


def check_tracking(ctx, p, qty, lot, serials, need_lot=True):
    serials = list(serials or [])
    if p["tracking"] == "lot":
        if need_lot and not lot:
            raise UserError(f"{p['sku']} is lot-tracked: --lot is needed")
        if serials:
            raise UserError(f"{p['sku']} has no serials")
    elif p["tracking"] == "serial":
        if lot:
            raise UserError(f"{p['sku']} has no lots")
        if len(serials) != qty or len(set(serials)) != len(serials):
            raise UserError(f"{p['sku']} needs exactly {qty} distinct serials")
        for s in serials:
            if not re.fullmatch(r"[A-Z0-9-]{1,30}", s):
                raise UserError(f"bad serial {s!r}")
    else:
        if lot or serials:
            raise UserError(f"{p['sku']} has no lots or serials")
    return serials


def split_serials(text):
    return [s for s in (text or "").split(",") if s] if isinstance(text, str) else list(text or [])


def do_receive(ctx, sku, qty_s, at, cost_s, lot=None, expires=None, serials=None, ref=None, line=None,
               cost=None):
    p = ctx.live_product(sku)
    qty = parse_qty(qty_s, p["unit"])
    loc = ctx.location(at)
    if loc["type"] not in ("receiving", "storage"):
        raise UserError(f"can't receive into {at}")
    c = cost if cost is not None else parse_cost(cost_s)
    serials = check_tracking(ctx, p, qty, lot, serials)
    if p["tracking"] == "lot":
        if not re.fullmatch(r"[A-Z0-9-]{1,30}", lot):
            raise UserError(f"bad lot {lot!r}")
        if not expires:
            raise UserError("--expires is needed for a lot")
        exp = parse_date(expires).isoformat()
        known = ctx.one("SELECT expires FROM lots WHERE sku=? AND lot=?", sku, lot)
        if known and known["expires"] != exp:
            raise UserError(f"lot {lot} expires {known['expires']}")
        if not known:
            ctx.ex("INSERT INTO lots VALUES(?, ?, ?)", sku, lot, exp)
    elif expires:
        raise UserError("--expires is only for lots")
    if p["tracking"] == "serial":
        stock = current_stock(ctx)
        for s in serials:
            if any(k[0] == sku and k[3] == s and v > 0 for k, v in stock.items()):
                raise UserError(f"serial {s} is in stock already")
    return add_movement(ctx, "receive", sku, qty, None, at, lot if p["tracking"] == "lot" else None, serials, c,
                        ref, line)


def receive(ctx, sku, qty, at, cost, lot=None, expires=None, serials=None):
    m = do_receive(ctx, sku, qty, at, cost, lot, expires, split_serials(serials))
    ctx.audit("receive", m["id"])
    return mv_json(m)


def take_check(ctx, p, qty, loc, lot, serials):
    """Unreserved stock for qty at loc (and lot/serials)."""
    stock, reserved = current_stock(ctx), reserved_map(ctx)
    if p["tracking"] == "serial":
        for s in serials:
            if free_at(ctx, p["sku"], loc, None, s, stock, reserved) < 1:
                raise UserError(f"serial {s} isn't free at {loc}")
    elif free_at(ctx, p["sku"], loc, lot, None, stock, reserved) < qty:
        raise UserError(f"not enough unreserved {p['sku']} at {loc}")


def move(ctx, sku, qty_s, src, dst, lot=None, serials=None):
    p = ctx.product(sku)
    qty = parse_qty(qty_s, p["unit"])
    a, b = ctx.location(src), ctx.location(dst)
    if a["wh"] != b["wh"] or src == dst:
        raise UserError("move within one warehouse, between two locations")
    if b["type"] == "shipping":
        raise UserError("stock gets to SHIP only by so pick")
    serials = check_tracking(ctx, p, qty, lot, split_serials(serials))
    take_check(ctx, p, qty, src, lot, serials)
    m = add_movement(ctx, "move", sku, qty, src, dst, lot, serials)
    ctx.audit("move", m["id"])
    return mv_json(m)


def adjust(ctx, sku, at, count_s, reason, lot=None):
    p = ctx.live_product(sku)
    if p["tracking"] == "serial":
        raise UserError("serial-tracked products can't be adjusted")
    if not (reason or "").strip():
        raise UserError("a reason is needed")
    ctx.location(at)
    count = parse_qty(count_s, p["unit"], True, "count")
    check_tracking(ctx, p, 1, lot, [])
    k = (sku, at, lot, None)
    on = current_stock(ctx).get(k, ZERO)
    if count < reserved_map(ctx).get(k, ZERO):
        raise UserError("the count is below what is reserved there")
    diff = count - on
    if diff == 0:
        raise UserError("the count equals the stock")
    if diff > 0:
        if p["tracking"] == "lot" and not ctx.one("SELECT 1 FROM lots WHERE sku=? AND lot=?", sku, lot):
            raise UserError(f"lot {lot} has never been received")
        m = add_movement(ctx, "adjust", sku, diff, None, at, lot, reason=reason)
    else:
        m = add_movement(ctx, "adjust", sku, -diff, at, None, lot, reason=reason)
    ctx.audit("adjust", m["id"])
    return mv_json(m)


def scrap(ctx, sku, qty_s, at, reason, lot=None, serials=None):
    p = ctx.product(sku)
    if not (reason or "").strip():
        raise UserError("a reason is needed")
    qty = parse_qty(qty_s, p["unit"])
    ctx.location(at)
    serials = check_tracking(ctx, p, qty, lot, split_serials(serials))
    take_check(ctx, p, qty, at, lot, serials)
    m = add_movement(ctx, "scrap", sku, qty, at, None, lot, serials, reason=reason)
    ctx.audit("scrap", m["id"])
    return mv_json(m)


def movement_list(ctx, sku=None, wh=None, type_=None, since=None, until=None):
    if since:
        parse_time(since)
    if until:
        parse_time(until)
    out = []
    for m in load_movements(ctx):
        if sku and m["sku"] != sku or type_ and m["type"] != type_:
            continue
        if wh and wh not in (wh_of(m["src"]), wh_of(m["dst"])):
            continue
        if since and m["at"] < since or until and m["at"] > until:
            continue
        out.append(mv_json(m))
    return out


def movement_void(ctx, mid, reason):
    if not (reason or "").strip():
        raise UserError("a reason is needed")
    try:
        x = ctx.one("SELECT * FROM movements WHERE id=?", int(mid))
    except ValueError:
        x = None
    if not x:
        raise NotFound(f"unknown movement {mid}")
    x = dict(x)
    if x["type"] not in ("receive", "move", "adjust", "scrap"):
        raise UserError(f"a {x['type']} movement can't be voided")
    if x["voided"]:
        raise UserError(f"movement {mid} is voided already")
    p = ctx.product(x["sku"])
    stock, reserved = current_stock(ctx), reserved_map(ctx)
    if x["dst"]:
        for k, q in unit_keys(x):
            if k[1] == x["dst"] and stock.get(k, ZERO) - q < reserved.get(k, ZERO):
                raise UserError("voiding it would take reserved or missing stock")
    if p["costing"] == "average" and (x["type"] == "receive" or x["type"] == "adjust" and x["dst"]):
        w = wh_of(x["dst"])
        for m in load_movements(ctx):
            if m["id"] > x["id"] and m["sku"] == x["sku"] and (wh_of(m["src"]) == w) != (wh_of(m["dst"]) == w):
                raise UserError("later movements of this product in that warehouse prevent the void")
    m = add_movement(ctx, "void", x["sku"], Decimal(x["qty"]), x["dst"], x["src"], x["lot"],
                     json.loads(x["serials"] or "[]"), ref=f"MV-{x['id']}", reason=reason)
    ctx.ex("UPDATE movements SET voided=1 WHERE id=?", x["id"])
    ctx.audit("movement.void", x["id"])
    return mv_json(m)
