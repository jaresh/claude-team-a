"""Sales orders and reservations, stock reports, reordering."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import NotFound, TIME_FMT, UserError, ZERO, cost4, fq, money, parse_qty, r2, wh_of
from .ledger import add_movement, current_stock, load_movements, reserved_map, stock_map
from .pricing import unit_price
from .purchasing import po_received
from .reports import cut_for


def so_get(ctx, so):
    r = ctx.one("SELECT * FROM sos WHERE id=?", so)
    if not r:
        raise NotFound(f"unknown sales order {so}")
    return r


def line_figures(ctx, so, line):
    res = sum((Decimal(x["qty"]) for x in ctx.q(
        "SELECT qty FROM reservations WHERE so=? AND line=? AND picked=0", so, line)), ZERO)
    picked = sum((Decimal(x["qty"]) for x in ctx.q(
        "SELECT qty FROM reservations WHERE so=? AND line=? AND picked=1", so, line)), ZERO)
    shipped = sum((Decimal(m["qty"]) for m in ctx.q(
        "SELECT qty FROM movements WHERE type='ship' AND ref=? AND line=?", so, line)), ZERO)
    returned = sum((Decimal(x["qty"]) for x in ctx.q(
        "SELECT qty FROM returns WHERE so=? AND line=?", so, line)), ZERO)
    return res, picked, shipped, returned


def so_status(ctx, so):
    r = so_get(ctx, so)
    if r["state"] in ("draft", "cancelled"):
        return r["state"]
    lines = ctx.q("SELECT * FROM so_lines WHERE so=?", so)
    figs = [(Decimal(x["qty"]), *line_figures(ctx, so, x["line"])) for x in lines]
    if all(sh >= q for q, _, _, sh, _ in figs):
        return "shipped"
    if any(sh > 0 for _, _, _, sh, _ in figs):
        return "partially_shipped"
    if all(re_ + pi + sh >= q for q, re_, pi, sh, _ in figs):
        return "confirmed"
    return "backordered"


def so_show(ctx, so):
    r = so_get(ctx, so)
    lines = []
    for x in ctx.q("SELECT * FROM so_lines WHERE so=? ORDER BY line", so):
        unit = ctx.product(x["sku"])["unit"]
        res, picked, shipped, returned = line_figures(ctx, so, x["line"])
        lines.append({"line": x["line"], "sku": x["sku"], "qty": x["qty"], "unit_price": x["unit_price"],
                      "gross": x["gross"], "discount": x["discount"], "net": x["net"],
                      "reserved": fq(res, unit), "picked": fq(picked, unit), "shipped": fq(shipped, unit),
                      "returned": fq(returned, unit)})
    exp = ctx.one("SELECT MIN(expires) AS e FROM reservations WHERE so=? AND picked=0", so)["e"]
    return {"id": so, "customer": r["customer"], "warehouse": r["wh"], "status": so_status(ctx, so),
            "hold": r["hold"], "expires": exp, "lines": lines, "subtotal": r["subtotal"],
            "order_discount": r["order_discount"], "total": r["total"]}


def so_list(ctx, status=None):
    out = [so_show(ctx, r["id"]) for r in ctx.q("SELECT id FROM sos ORDER BY id")]
    return [x for x in out if not status or x["status"] == status]


def so_create(ctx, customer, wh, lines):
    if not ctx.one("SELECT 1 FROM customers WHERE name=?", customer):
        raise NotFound(f"unknown customer {customer}")
    ctx.warehouse(wh)
    if not lines:
        raise UserError("at least one line is needed")
    parsed = []
    for spec in lines:
        if isinstance(spec, dict):
            sku, q = spec.get("sku"), spec.get("qty")
        else:
            parts = spec.split(":")
            if len(parts) != 2:
                raise UserError(f"bad line {spec!r}: use SKU:QTY")
            sku, q = parts
        p = ctx.product(sku)
        parsed.append((sku, fq(parse_qty(q, p["unit"]), p["unit"])))
    so = ctx.next_doc("SO")
    ctx.ex("INSERT INTO sos VALUES(?, ?, ?, 'draft', NULL, NULL, NULL, NULL)", so, customer, wh)
    for n, (sku, q) in enumerate(parsed, 1):
        ctx.ex("INSERT INTO so_lines VALUES(?, ?, ?, ?, NULL, NULL, NULL, NULL)", so, n, sku, q)
    ctx.audit("so.create", so)
    return so_show(ctx, so)


def allocate(ctx, so, expires):
    r = so_get(ctx, so)
    storage = {x["loc"] for x in ctx.q("SELECT loc FROM locations WHERE wh=? AND type='storage'", r["wh"])}
    stock, reserved = current_stock(ctx), reserved_map(ctx)
    lots = {(x["sku"], x["lot"]): x["expires"] for x in ctx.q("SELECT * FROM lots")}
    for x in ctx.q("SELECT * FROM so_lines WHERE so=? ORDER BY line", so):
        p = ctx.product(x["sku"])
        res, picked, shipped, _ = line_figures(ctx, so, x["line"])
        need = Decimal(x["qty"]) - res - picked - shipped
        if need <= 0:
            continue
        cands = []
        for k, v in stock.items():
            sku, loc, lot, serial = k
            if sku != x["sku"] or loc not in storage:
                continue
            free = v - reserved.get(k, ZERO)
            if free <= 0:
                continue
            if lot and lots[(sku, lot)] < ctx.today.isoformat():
                continue
            if p["tracking"] == "lot":
                order = (lots[(sku, lot)], lot, loc)
            elif p["tracking"] == "serial":
                order = (loc, serial)
            else:
                order = (loc,)
            cands.append((order, k, free))
        for _, k, free in sorted(cands):
            if need <= 0:
                break
            take = min(free, need)
            ctx.ex("INSERT INTO reservations(so, line, sku, loc, lot, serial, qty, expires, picked) "
                   "VALUES(?, ?, ?, ?, ?, ?, ?, ?, 0)", so, x["line"], k[0], k[1], k[2], k[3],
                   fq(take, p["unit"]), expires)
            reserved[k] = reserved.get(k, ZERO) + take
            need -= take


def so_confirm(ctx, so, hold=None):
    r = so_get(ctx, so)
    if r["state"] != "draft":
        raise UserError(f"{so} is {so_status(ctx, so)}")
    hold = 48 if hold in (None, "") else hold
    try:
        hold = int(hold)
    except (TypeError, ValueError):
        raise UserError("bad hold")
    if not 1 <= hold <= 720:
        raise UserError("hold is 1 to 720 hours")
    plist = ctx.one("SELECT price_list FROM customers WHERE name=?", r["customer"])["price_list"]
    today = ctx.today.isoformat()
    subtotal = ZERO
    for x in ctx.q("SELECT * FROM so_lines WHERE so=? ORDER BY line", so):
        qty = Decimal(x["qty"])
        price = unit_price(ctx, plist, x["sku"], qty)
        gross = r2(qty * price)
        pct = max([Decimal(p["percent"]) for p in ctx.q(
            "SELECT percent FROM promos WHERE kind='line' AND sku=? AND dfrom<=? AND dto>=?", x["sku"], today, today)],
            default=ZERO)
        disc = r2(gross * pct / 100)
        net = gross - disc
        subtotal += net
        ctx.ex("UPDATE so_lines SET unit_price=?, gross=?, discount=?, net=? WHERE so=? AND line=?",
               cost4(price), money(gross), money(disc), money(net), so, x["line"])
    pct = max([Decimal(p["percent"]) for p in ctx.q(
        "SELECT percent, threshold FROM promos WHERE kind='order' AND dfrom<=? AND dto>=?", today, today)
        if Decimal(p["threshold"]) <= subtotal], default=ZERO)
    od = r2(subtotal * pct / 100)
    ctx.ex("UPDATE sos SET state='active', hold=?, subtotal=?, order_discount=?, total=? WHERE id=?",
           hold, money(subtotal), money(od), money(subtotal - od), so)
    allocate(ctx, so, (ctx.now + timedelta(hours=hold)).strftime(TIME_FMT))
    ctx.audit("so.confirm", so)
    return so_show(ctx, so)


def so_allocate(ctx, so):
    r = so_get(ctx, so)
    if so_status(ctx, so) not in ("confirmed", "backordered", "partially_shipped"):
        raise UserError(f"{so} is {so_status(ctx, so)}")
    exp = (ctx.now + timedelta(hours=r["hold"])).strftime(TIME_FMT)
    allocate(ctx, so, exp)
    ctx.ex("UPDATE reservations SET expires=? WHERE so=? AND picked=0", exp, so)
    ctx.audit("so.allocate", so)
    return so_show(ctx, so)


def so_pick(ctx, so):
    r = so_get(ctx, so)
    res = ctx.q("SELECT * FROM reservations WHERE so=? AND picked=0", so)
    if not res:
        raise UserError(f"{so} has nothing reserved")
    ship = f"{r['wh']}/SHIP"
    groups = defaultdict(lambda: [ZERO, []])
    for x in res:
        g = groups[(x["loc"], x["sku"], x["lot"] or "")]
        g[0] += Decimal(x["qty"])
        if x["serial"]:
            g[1].append(x["serial"])
    picks = []
    for (loc, sku, lot), (q, serials) in sorted(groups.items()):
        add_movement(ctx, "pick", sku, q, loc, ship, lot or None, serials, ref=so)
        picks.append({"sku": sku, "from": loc, "lot": lot or None, "serials": sorted(serials),
                      "qty": fq(q, ctx.product(sku)["unit"])})
    ctx.ex("UPDATE reservations SET loc=?, picked=1, expires=NULL WHERE so=? AND picked=0", ship, so)
    ctx.audit("so.pick", so)
    return {"order": so, "picks": picks}


def so_ship(ctx, so):
    r = so_get(ctx, so)
    picked = ctx.q("SELECT * FROM reservations WHERE so=? AND picked=1", so)
    if not picked:
        raise UserError(f"{so} has nothing picked")
    groups = defaultdict(lambda: [ZERO, [], None])
    for x in picked:
        g = groups[(x["line"], x["lot"] or "")]
        g[0] += Decimal(x["qty"])
        g[2] = x["sku"]
        if x["serial"]:
            g[1].append(x["serial"])
    for (line, lot), (q, serials, sku) in sorted(groups.items()):
        add_movement(ctx, "ship", sku, q, f"{r['wh']}/SHIP", None, lot or None, serials, ref=so, line=line)
    ctx.ex("DELETE FROM reservations WHERE so=? AND picked=1", so)
    ctx.audit("so.ship", so)
    return so_show(ctx, so)


def so_cancel(ctx, so):
    r = so_get(ctx, so)
    if r["state"] == "cancelled":
        raise UserError(f"{so} is cancelled already")
    if any(line_figures(ctx, so, x["line"])[2] > 0 for x in ctx.q("SELECT line FROM so_lines WHERE so=?", so)):
        raise UserError(f"{so} has shipped stock")
    ctx.ex("DELETE FROM reservations WHERE so=?", so)
    ctx.ex("UPDATE sos SET state='cancelled' WHERE id=?", so)
    ctx.audit("so.cancel", so)
    return so_show(ctx, so)


def expire_reservations(ctx):
    orders = [r["so"] for r in ctx.q(
        "SELECT DISTINCT so FROM reservations WHERE picked=0 AND expires<=? ORDER BY so", ctx.now_s)]
    if orders:
        ctx.ex("DELETE FROM reservations WHERE picked=0 AND expires<=?", ctx.now_s)
        for so in orders:
            ctx.audit("reservation.expire", so, user="system")


def stock_report(ctx, wh=None, sku=None, at=None):
    mvs = load_movements(ctx, cut_for(ctx, at) if at else None)
    s = stock_map(mvs)
    reserved = reserved_map(ctx)
    units = {r["sku"]: r["unit"] for r in ctx.q("SELECT sku, unit FROM products")}
    groups = defaultdict(lambda: [ZERO, [], ZERO])
    for k, v in s.items():
        if v <= 0 or (wh and wh_of(k[1]) != wh) or (sku and k[0] != sku):
            continue
        g = groups[(k[1], k[0], k[2] or "")]
        g[0] += v
        g[2] += reserved.get(k, ZERO)
        if k[3]:
            g[1].append(k[3])
    rows = []
    for (loc, sk, lot), (on, serials, res) in sorted(groups.items()):
        row = {"sku": sk, "location": loc, "lot": lot or None, "serials": sorted(serials),
               "on_hand": fq(on, units[sk])}
        if not at:
            row["reserved"] = fq(res, units[sk])
            row["available"] = fq(on - res, units[sk])
        rows.append(row)
    return rows


def figures(ctx, sku, wh):
    storage = {x["loc"] for x in ctx.q("SELECT loc FROM locations WHERE wh=? AND type='storage'", wh)}
    stock, reserved = current_stock(ctx), reserved_map(ctx)
    avail = sum((v - reserved.get(k, ZERO) for k, v in stock.items() if k[0] == sku and k[1] in storage), ZERO)
    incoming = ZERO
    for po in ctx.q("SELECT * FROM pos WHERE wh=? AND closed=0", wh):
        for x in ctx.q("SELECT * FROM po_lines WHERE po=? AND sku=?", po["id"], sku):
            incoming += max(Decimal(x["qty"]) - po_received(ctx, po["id"], x["line"]), ZERO)
    back = ZERO
    for so in ctx.q("SELECT * FROM sos WHERE wh=?", wh):
        if so_status(ctx, so["id"]) not in ("confirmed", "backordered", "partially_shipped"):
            continue
        for x in ctx.q("SELECT * FROM so_lines WHERE so=? AND sku=?", so["id"], sku):
            res, picked, shipped, _ = line_figures(ctx, so["id"], x["line"])
            back += max(Decimal(x["qty"]) - res - picked - shipped, ZERO)
    return avail, incoming, back


def available(ctx, sku, wh):
    p = ctx.product(sku)
    ctx.warehouse(wh)
    a, i, b = figures(ctx, sku, wh)
    u = p["unit"]
    return {"sku": sku, "warehouse": wh, "available": fq(a, u), "incoming": fq(i, u), "backordered": fq(b, u)}


def reorder(ctx, wh):
    ctx.warehouse(wh)
    out = []
    for p in ctx.q("SELECT * FROM products WHERE min IS NOT NULL ORDER BY sku"):
        a, i, b = figures(ctx, p["sku"], wh)
        proj = a + i - b
        mn = Decimal(p["min"])
        if proj < mn:
            target = Decimal(p["max"]) if p["max"] is not None else mn
            u = p["unit"]
            out.append({"sku": p["sku"], "available": fq(a, u), "incoming": fq(i, u), "backordered": fq(b, u),
                        "projected": fq(proj, u), "min": p["min"], "max": p["max"], "suggest": fq(target - proj, u)})
    return out
