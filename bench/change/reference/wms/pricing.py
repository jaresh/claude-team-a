"""Customers, price lists and promotions."""
import re
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import NotFound, UserError, cost4, fq, money, parse_amount, parse_cost, parse_date, parse_percent, parse_qty


def customer_json(r):
    d = {"name": r["name"], "price_list": r["price_list"]}
    if r["credit_limit"] is not None:
        d["credit_limit"] = r["credit_limit"]
    return d


def customer_add(ctx, name, price_list=None, credit_limit=None):
    name = (name or "").strip()
    if not 1 <= len(name) <= 60:
        raise UserError("a customer name is 1 to 60 characters")
    if price_list is not None and not re.fullmatch(r"[A-Z0-9]{1,10}", price_list):
        raise UserError(f"bad price list {price_list!r}")
    if ctx.one("SELECT 1 FROM customers WHERE name=?", name):
        raise UserError(f"customer {name} exists")
    limit = money(check_limit(credit_limit)) if credit_limit is not None else None
    ctx.ex("INSERT INTO customers VALUES(?, ?, ?)", name, price_list, limit)
    ctx.audit("customer.add", name)
    return customer_json(ctx.one("SELECT * FROM customers WHERE name=?", name))


def check_limit(text):
    limit = parse_amount(text, "credit limit")
    if limit <= 0:
        raise UserError("a credit limit is more than 0")
    return limit


def customer_limit(ctx, name, amount):
    if not ctx.one("SELECT 1 FROM customers WHERE name=?", name):
        raise NotFound(f"unknown customer {name}")
    limit = None if amount == "none" else money(check_limit(amount))
    ctx.ex("UPDATE customers SET credit_limit=? WHERE name=?", limit, name)
    ctx.audit("customer.limit", name)
    return customer_json(ctx.one("SELECT * FROM customers WHERE name=?", name))


def customer_list(ctx):
    return [customer_json(r) for r in ctx.q("SELECT * FROM customers ORDER BY name")]


def price_set(ctx, lst, sku, price_s, min_qty="0"):
    if not re.fullmatch(r"[A-Z0-9]{1,10}", lst or ""):
        raise UserError(f"bad price list {lst!r}")
    p = ctx.live_product(sku)
    price = parse_cost(price_s, "unit price")
    mq = fq(parse_qty(min_qty, p["unit"], True, "min-qty"), p["unit"])
    ctx.ex("INSERT OR REPLACE INTO prices VALUES(?, ?, ?, ?)", lst, sku, mq, cost4(price))
    ctx.audit("price.set", f"{lst}/{sku}")
    return {"list": lst, "sku": sku, "min_qty": mq, "unit_price": cost4(price)}


def price_list(ctx, lst=None):
    rows = ctx.q("SELECT * FROM prices")
    rows = sorted(rows, key=lambda r: (r["list"], r["sku"], Decimal(r["min_qty"])))
    return [{"list": r["list"], "sku": r["sku"], "min_qty": r["min_qty"], "unit_price": r["unit_price"]}
            for r in rows if not lst or r["list"] == lst]


def promo_add(ctx, code, sku=None, order=False, threshold=None, percent=None, dfrom=None, dto=None):
    if not re.fullmatch(r"[A-Z0-9-]{1,20}", code or ""):
        raise UserError(f"bad promotion code {code!r}")
    if ctx.one("SELECT 1 FROM promos WHERE code=?", code):
        raise UserError(f"promotion {code} exists")
    pct = parse_percent(percent)
    a, b = parse_date(dfrom), parse_date(dto)
    if a > b:
        raise UserError("--from is after --to")
    if order:
        if sku:
            raise UserError("an order promotion has no SKU")
        th = money(parse_amount(threshold, "threshold"))
        ctx.ex("INSERT INTO promos VALUES(?, 'order', NULL, ?, ?, ?, ?)", code, th, money(pct), a.isoformat(), b.isoformat())
    else:
        if threshold is not None:
            raise UserError("a line promotion has no threshold")
        ctx.live_product(sku)
        ctx.ex("INSERT INTO promos VALUES(?, 'line', ?, NULL, ?, ?, ?)", code, sku, money(pct), a.isoformat(), b.isoformat())
    ctx.audit("promo.add", code)
    return promo_json(ctx.one("SELECT * FROM promos WHERE code=?", code))


def promo_json(r):
    return {"code": r["code"], "kind": r["kind"], "sku": r["sku"], "threshold": r["threshold"],
            "percent": r["percent"], "from": r["dfrom"], "to": r["dto"]}


def promo_list(ctx):
    return [promo_json(r) for r in ctx.q("SELECT * FROM promos ORDER BY code")]


def unit_price(ctx, plist, sku, qty):
    for lst in ([plist] if plist else []) + ["STANDARD"]:
        best = None
        for r in ctx.q("SELECT * FROM prices WHERE list=? AND sku=?", lst, sku):
            if Decimal(r["min_qty"]) <= qty and (best is None or Decimal(r["min_qty"]) > Decimal(best["min_qty"])):
                best = r
        if best:
            return Decimal(best["unit_price"])
    raise UserError(f"no price for {sku}")
