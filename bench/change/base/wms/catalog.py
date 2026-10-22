"""Products, warehouses and locations."""
import csv
import re
from .core import HttpError, ImportErrors, UserError, fq, parse_qty


def check_product(sku, name, unit, tracking, costing, mn, mx):
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{2,19}", sku or ""):
        raise UserError(f"bad SKU {sku!r}")
    name = (name or "").strip()
    if not 1 <= len(name) <= 100:
        raise UserError("the name must be 1 to 100 characters")
    unit, tracking, costing = unit or "each", tracking or "none", costing or "fifo"
    if unit not in ("each", "kg"):
        raise UserError(f"bad unit {unit!r}")
    if tracking not in ("none", "lot", "serial"):
        raise UserError(f"bad tracking {tracking!r}")
    if costing not in ("fifo", "average"):
        raise UserError(f"bad costing {costing!r}")
    if tracking == "serial" and unit != "each":
        raise UserError("serial tracking needs unit each")
    mnq = parse_qty(mn, unit, True, "min") if mn not in (None, "") else None
    mxq = parse_qty(mx, unit, True, "max") if mx not in (None, "") else None
    if mnq is not None and mxq is not None and mxq < mnq:
        raise UserError("max is below min")
    return {"sku": sku, "name": name, "unit": unit, "tracking": tracking, "costing": costing,
            "min": fq(mnq, unit) if mnq is not None else None, "max": fq(mxq, unit) if mxq is not None else None}


def insert_product(ctx, d):
    ctx.ex("INSERT INTO products VALUES(?, ?, ?, ?, ?, ?, ?, 1)", d["sku"], d["name"], d["unit"],
           d["tracking"], d["costing"], d["min"], d["max"])


def product_add(ctx, sku, name, unit=None, tracking=None, costing=None, mn=None, mx=None):
    d = check_product(sku, name, unit, tracking, costing, mn, mx)
    if ctx.one("SELECT 1 FROM products WHERE sku=?", sku):
        raise UserError(f"product {sku} exists")
    insert_product(ctx, d)
    ctx.audit("product.add", sku)
    return product_json(ctx.product(sku))


def product_json(p):
    return {"sku": p["sku"], "name": p["name"], "unit": p["unit"], "tracking": p["tracking"],
            "costing": p["costing"], "min": p["min"], "max": p["max"], "version": p["version"]}


def product_list(ctx, search=None):
    rows = [product_json(p) for p in ctx.q("SELECT * FROM products ORDER BY sku")]
    if search:
        s = search.lower()
        rows = [r for r in rows if s in r["sku"].lower() or s in r["name"].lower()]
    return rows


UNSET = object()


def product_edit(ctx, sku, version, name=UNSET, mn=UNSET, mx=UNSET, http=False):
    p = ctx.product(sku)
    if int(version) != p["version"]:
        if http:
            raise HttpError(412, "version mismatch")
        raise UserError(f"{sku} has changed since version {version}")
    new_name = p["name"] if name is UNSET else name
    nmn = p["min"] if mn is UNSET else (None if mn in (None, "none") else mn)
    nmx = p["max"] if mx is UNSET else (None if mx in (None, "none") else mx)
    d = check_product(sku, new_name, p["unit"], p["tracking"], p["costing"], nmn, nmx)
    ctx.ex("UPDATE products SET name=?, min=?, max=?, version=version+1 WHERE sku=?", d["name"], d["min"],
           d["max"], sku)
    ctx.audit("product.edit", sku)
    return product_json(ctx.product(sku))


def import_products(ctx, path):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
    except OSError as e:
        raise UserError(f"can't read {path}: {e}")
    if not rows or rows[0] != ["sku", "name", "unit", "tracking", "costing", "min", "max"]:
        raise UserError("the header must be sku,name,unit,tracking,costing,min,max")
    errors, seen, good = [], set(), []
    for n, row in enumerate(rows[1:], start=2):
        try:
            if len(row) != 7:
                raise UserError("expected 7 cells")
            d = check_product(*row)
            if d["sku"] in seen:
                raise UserError(f"{d['sku']} appears twice")
            if ctx.one("SELECT 1 FROM products WHERE sku=?", d["sku"]):
                raise UserError(f"product {d['sku']} exists")
            seen.add(d["sku"])
            good.append(d)
        except UserError as e:
            errors.append(f"row {n}: {e}")
    if errors:
        raise ImportErrors(errors)
    for d in good:
        insert_product(ctx, d)
    ctx.audit("import", "products")
    return {"imported": len(good)}


def warehouse_add(ctx, code, name):
    if not re.fullmatch(r"[A-Z0-9]{2,6}", code or ""):
        raise UserError(f"bad warehouse code {code!r}")
    if not (name or "").strip():
        raise UserError("a name is needed")
    if ctx.one("SELECT 1 FROM warehouses WHERE code=?", code):
        raise UserError(f"warehouse {code} exists")
    ctx.ex("INSERT INTO warehouses VALUES(?, ?)", code, name.strip())
    ctx.ex("INSERT INTO locations VALUES(?, ?, 'receiving')", f"{code}/RECV", code)
    ctx.ex("INSERT INTO locations VALUES(?, ?, 'shipping')", f"{code}/SHIP", code)
    ctx.audit("warehouse.add", code)
    return {"code": code, "name": name.strip()}


def location_add(ctx, loc, type_="storage"):
    if not loc or loc.count("/") != 1:
        raise UserError(f"bad location {loc!r}")
    wh, name = loc.split("/")
    ctx.warehouse(wh)
    if not re.fullmatch(r"[A-Z0-9-]{1,20}", name):
        raise UserError(f"bad location {loc!r}")
    if type_ not in ("storage", "receiving"):
        raise UserError(f"bad location type {type_!r}")
    if ctx.one("SELECT 1 FROM locations WHERE loc=?", loc):
        raise UserError(f"location {loc} exists")
    ctx.ex("INSERT INTO locations VALUES(?, ?, ?)", loc, wh, type_)
    ctx.audit("location.add", loc)
    return {"location": loc, "type": type_}


def warehouse_list(ctx):
    return [{"code": r["code"], "name": r["name"]} for r in ctx.q("SELECT * FROM warehouses ORDER BY code")]


def location_list(ctx, wh):
    ctx.warehouse(wh)
    return [{"location": r["loc"], "type": r["type"]} for r in ctx.q("SELECT * FROM locations WHERE wh=? ORDER BY loc", wh)]
