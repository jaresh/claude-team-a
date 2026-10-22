"""The whole reference implementation. Stock and costing are derived by replaying the movement log
in id order, so `--at` reports, voids and transfers all follow from one definition."""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class UserError(Exception):
    status = 400


class NotFound(UserError):
    status = 404


class HttpError(UserError):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status


class ImportErrors(UserError):
    def __init__(self, lines):
        super().__init__("; ".join(lines))
        self.lines = lines


ROLES = ["viewer", "clerk", "manager", "admin"]
D2, D3, D4 = Decimal("0.01"), Decimal("0.001"), Decimal("0.0001")
ZERO = Decimal(0)
TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


def r2(x):
    return Decimal(x).quantize(D2, ROUND_HALF_UP)


def r4(x):
    return Decimal(x).quantize(D4, ROUND_HALF_UP)


def money(x):
    v = r2(x)
    return "0.00" if v == 0 else str(v)


def cost4(x):
    return str(r4(x))


def fq(q, unit):
    q = Decimal(q)
    if unit == "each":
        return str(int(q))
    v = q.quantize(D3)
    return "0.000" if v == 0 else str(v)


def floor_unit(q, unit):
    return q.quantize(Decimal(1) if unit == "each" else D3, ROUND_DOWN)


def parse_qty(text, unit, allow_zero=False, what="quantity"):
    s = str(text).strip()
    if not re.fullmatch(r"\d+" if unit == "each" else r"\d+(\.\d{1,3})?", s):
        raise UserError(f"bad {what}: {text!r}")
    q = Decimal(s)
    if q == 0 and not allow_zero:
        raise UserError(f"{what} must be more than 0")
    return q


def parse_cost(text, what="unit cost"):
    s = str(text).strip()
    if not re.fullmatch(r"\d+(\.\d{1,4})?", s):
        raise UserError(f"bad {what}: {text!r}")
    return Decimal(s)


def parse_amount(text, what="amount"):
    s = str(text).strip()
    if not re.fullmatch(r"\d+(\.\d{1,2})?", s):
        raise UserError(f"bad {what}: {text!r}")
    return Decimal(s)


def parse_percent(text):
    p = parse_amount(text, "percent")
    if not (0 < p <= 100):
        raise UserError("percent must be more than 0 and at most 100")
    return p


def parse_time(s):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", s):
        raise UserError(f"bad time: {s!r}")
    try:
        return datetime.strptime(s, TIME_FMT)
    except ValueError:
        raise UserError(f"bad time: {s!r}")


def parse_date(s):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise UserError(f"bad date: {s!r}")
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise UserError(f"bad date: {s!r}")


def wh_of(loc):
    return loc.split("/")[0] if loc else None


SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE users(name TEXT PRIMARY KEY, role TEXT, enabled INTEGER);
CREATE TABLE products(sku TEXT PRIMARY KEY, name TEXT, unit TEXT, tracking TEXT, costing TEXT,
                      min TEXT, max TEXT, version INTEGER);
CREATE TABLE warehouses(code TEXT PRIMARY KEY, name TEXT);
CREATE TABLE locations(loc TEXT PRIMARY KEY, wh TEXT, type TEXT);
CREATE TABLE lots(sku TEXT, lot TEXT, expires TEXT, PRIMARY KEY(sku, lot));
CREATE TABLE movements(id INTEGER PRIMARY KEY, at TEXT, user TEXT, type TEXT, sku TEXT, qty TEXT,
                       src TEXT, dst TEXT, lot TEXT, serials TEXT, unit_cost TEXT, value TEXT,
                       ref TEXT, line INTEGER, voided INTEGER DEFAULT 0, reason TEXT);
CREATE TABLE reservations(id INTEGER PRIMARY KEY, so TEXT, line INTEGER, sku TEXT, loc TEXT,
                          lot TEXT, serial TEXT, qty TEXT, expires TEXT, picked INTEGER);
CREATE TABLE pos(id TEXT PRIMARY KEY, supplier TEXT, wh TEXT, closed INTEGER);
CREATE TABLE po_lines(po TEXT, line INTEGER, sku TEXT, qty TEXT, unit_cost TEXT, PRIMARY KEY(po, line));
CREATE TABLE customers(name TEXT PRIMARY KEY, price_list TEXT);
CREATE TABLE prices(list TEXT, sku TEXT, min_qty TEXT, unit_price TEXT, PRIMARY KEY(list, sku, min_qty));
CREATE TABLE promos(code TEXT PRIMARY KEY, kind TEXT, sku TEXT, threshold TEXT, percent TEXT,
                    dfrom TEXT, dto TEXT);
CREATE TABLE sos(id TEXT PRIMARY KEY, customer TEXT, wh TEXT, state TEXT, hold INTEGER,
                 subtotal TEXT, order_discount TEXT, total TEXT);
CREATE TABLE so_lines(so TEXT, line INTEGER, sku TEXT, qty TEXT, unit_price TEXT, gross TEXT,
                      discount TEXT, net TEXT, PRIMARY KEY(so, line));
CREATE TABLE transfers(id TEXT PRIMARY KEY, sku TEXT, qty TEXT, src TEXT, dst TEXT, lot TEXT,
                       serials TEXT, status TEXT, value TEXT);
CREATE TABLE returns(id TEXT PRIMARY KEY, so TEXT, line INTEGER, sku TEXT, qty TEXT, condition TEXT,
                     dst TEXT, lot TEXT, serials TEXT, unit_cost TEXT, value TEXT, credit TEXT);
CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, user TEXT, action TEXT, target TEXT);
CREATE TABLE idem(key TEXT PRIMARY KEY, path TEXT, body TEXT, status INTEGER, response TEXT);
"""

NEED = {
    "user add": "admin", "user role": "admin", "user disable": "admin",
    "product add": "manager", "product edit": "manager", "import products": "manager",
    "warehouse add": "manager", "location add": "manager", "customer add": "manager",
    "price set": "manager", "promo add": "manager", "po create": "manager", "po close": "manager",
    "so create": "manager", "so confirm": "manager", "so allocate": "manager", "so cancel": "manager",
    "transfer cancel": "manager", "return create": "manager", "movement void": "manager",
    "receive": "clerk", "move": "clerk", "adjust": "clerk", "scrap": "clerk", "po receive": "clerk",
    "so pick": "clerk", "so ship": "clerk", "transfer create": "clerk", "transfer receive": "clerk",
}


class Ctx:
    def __init__(self, conn, now, user):
        self.conn, self.now, self.user = conn, now, user
        self.now_s = now.strftime(TIME_FMT)
        self.today = now.date()

    def q(self, sql, *args):
        return self.conn.execute(sql, args).fetchall()

    def one(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def ex(self, sql, *args):
        return self.conn.execute(sql, args)

    def meta(self, key, default=None):
        r = self.one("SELECT value FROM meta WHERE key=?", key)
        return r["value"] if r else default

    def set_meta(self, key, value):
        self.ex("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", key, str(value))

    def next_doc(self, kind):
        n = int(self.meta("seq_" + kind, "0")) + 1
        self.set_meta("seq_" + kind, n)
        return f"{kind}-{n:04d}"

    def audit(self, action, target, user=None):
        self.ex("INSERT INTO audit(at, user, action, target) VALUES(?, ?, ?, ?)",
                self.now_s, user or self.user, action, str(target))

    def product(self, sku):
        p = self.one("SELECT * FROM products WHERE sku=?", sku)
        if not p:
            raise NotFound(f"unknown product {sku}")
        return p

    def location(self, loc):
        r = self.one("SELECT * FROM locations WHERE loc=?", loc)
        if not r:
            raise NotFound(f"unknown location {loc}")
        return r

    def warehouse(self, code):
        r = self.one("SELECT * FROM warehouses WHERE code=?", code)
        if not r:
            raise NotFound(f"unknown warehouse {code}")
        return r


# ---------------------------------------------------------------- the movement log, replayed

def load_movements(ctx, upto=None):
    sql = "SELECT * FROM movements" + (" WHERE id<=?" if upto is not None else "") + " ORDER BY id"
    return [dict(r) for r in (ctx.q(sql, upto) if upto is not None else ctx.q(sql))]


def unit_keys(m):
    serials = json.loads(m["serials"] or "[]")
    units = [(s, Decimal(1)) for s in serials] if serials else [(None, Decimal(m["qty"]))]
    for serial, q in units:
        if m["src"]:
            yield (m["sku"], m["src"], m["lot"], serial), -q
        if m["dst"]:
            yield (m["sku"], m["dst"], m["lot"], serial), q


def stock_map(mvs):
    s = defaultdict(Decimal)
    for m in mvs:
        for k, q in unit_keys(m):
            s[k] += q
    return {k: v for k, v in s.items() if v != 0}


class Layer:
    __slots__ = ("time", "mvid", "seq", "cost", "rem", "orig")

    def __init__(self, time, mvid, seq, cost, qty):
        self.time, self.mvid, self.seq, self.cost, self.rem, self.orig = time, mvid, seq, cost, qty, qty

    def key(self):
        return (self.time, self.mvid, self.seq)


class Engine:
    """Costing state per (sku, warehouse), built by applying movements in id order."""

    def __init__(self, ctx, mvs):
        self.costing = {r["sku"]: r["costing"] for r in ctx.q("SELECT sku, costing FROM products")}
        self.tr_src = {r["id"]: r["src"] for r in ctx.q("SELECT id, src FROM transfers")}
        self.layers = defaultdict(list)
        self.avg = {}
        self.seq = 0
        self.slices = {}
        self.tr_out = {}
        self.snap = {}
        self.created = {}
        self.by_id = {m["id"]: m for m in mvs}

    def _avg(self, sku, w):
        return self.avg.setdefault((sku, w), {"Q": ZERO, "V": r2(0), "A": None, "last": None})

    @staticmethod
    def _recompute(st):
        if st["Q"] > 0:
            st["A"] = r4(st["V"] / st["Q"])
            st["last"] = st["A"]
        else:
            st["A"] = None

    def _add_layer(self, sku, w, time, mvid, c, q):
        self.seq += 1
        layer = Layer(time, mvid, self.seq, c, q)
        self.layers[(sku, w)].append(layer)
        return layer

    def _in(self, m, w, q, c, value=None):
        sku = m["sku"]
        value = r2(q * c) if value is None else value
        if self.costing[sku] == "fifo":
            self.created[m["id"]] = self._add_layer(sku, w, m["at"], m["id"], c, q)
        else:
            st = self._avg(sku, w)
            self.snap[m["id"]] = dict(st)
            st["V"] += value
            st["Q"] += q
            self._recompute(st)
        return value

    def _out(self, m, w, q):
        sku = m["sku"]
        if self.costing[sku] == "fifo":
            need, total, sl = q, ZERO, []
            for layer in sorted((x for x in self.layers[(sku, w)] if x.rem > 0), key=Layer.key):
                if need <= 0:
                    break
                take = min(layer.rem, need)
                layer.rem -= take
                need -= take
                total += take * layer.cost
                sl.append((layer, take))
            if need > 0:
                raise UserError("not enough costed stock")
            self.slices[m["id"]] = sl
            return r2(total)
        st = self._avg(sku, w)
        if q == st["Q"]:
            value, st["V"], st["Q"] = st["V"], r2(0), ZERO
        else:
            value = r2(q * st["A"])
            st["V"] -= value
            st["Q"] -= q
        self._recompute(st)
        return value

    def apply(self, m):
        t, sku, q = m["type"], m["sku"], Decimal(m["qty"])
        fifo = self.costing[sku] == "fifo"
        if t in ("move", "pick"):
            return r2(0)
        if t in ("receive", "return"):
            return self._in(m, wh_of(m["dst"]), q, Decimal(m["unit_cost"]))
        if t == "adjust":
            if not m["dst"]:
                return self._out(m, wh_of(m["src"]), q)
            w = wh_of(m["dst"])
            if fifo:
                ever = self.layers[(sku, w)]
                if not ever:
                    raise UserError(f"no cost known for {sku} in {w}")
                newest = max(ever, key=Layer.key)
                return self._in(m, w, q, newest.cost)
            st = self.avg.get((sku, w))
            a = st and (st["A"] if st["Q"] > 0 else st["last"])
            if a is None:
                raise UserError(f"no cost known for {sku} in {w}")
            return self._in(m, w, q, a, r2(q * a))
        if t in ("scrap", "ship", "transfer-out"):
            v = self._out(m, wh_of(m["src"]), q)
            if t == "transfer-out":
                self.tr_out[m["ref"]] = (m["id"], v)
            return v
        if t == "transfer-in":
            out_id, v = self.tr_out[m["ref"]]
            w = wh_of(m["dst"])
            back = w == wh_of(self.tr_src[m["ref"]])
            if fifo:
                for layer, sq in self.slices[out_id]:
                    if back:
                        layer.rem += sq
                    else:
                        self._add_layer(sku, w, layer.time, layer.mvid, layer.cost, sq)
            else:
                st = self._avg(sku, w)
                st["V"] += v
                st["Q"] += q
                self._recompute(st)
            return v
        if t == "void":
            x = self.by_id[int(m["ref"][3:])]
            if x["type"] == "move":
                return r2(0)
            if x["type"] == "receive" or (x["type"] == "adjust" and x["dst"]):
                w = wh_of(x["dst"])
                if fifo:
                    layer = self.created[x["id"]]
                    if layer.rem != layer.orig:
                        raise UserError(f"stock of movement {x['id']} has been issued; it can't be voided")
                    self.layers[(sku, w)].remove(layer)
                else:
                    self.avg[(sku, w)] = dict(self.snap[x["id"]])
                return Decimal(x["value"])
            w = wh_of(x["src"])
            if fifo:
                for layer, sq in self.slices[x["id"]]:
                    layer.rem += sq
            else:
                st = self._avg(sku, w)
                st["V"] += Decimal(x["value"])
                st["Q"] += Decimal(x["qty"])
                self._recompute(st)
            return Decimal(x["value"])
        raise UserError(f"unknown movement type {t}")

    def stock_value(self, sku, w):
        if self.costing[sku] == "fifo":
            ls = self.layers.get((sku, w), [])
            return sum((x.rem for x in ls), ZERO), r2(sum((x.rem * x.cost for x in ls), ZERO))
        st = self.avg.get((sku, w))
        return (st["Q"], st["V"]) if st else (ZERO, r2(0))


def replay(ctx, mvs):
    e = Engine(ctx, mvs)
    for m in mvs:
        e.apply(m)
    return e


def _replay_with_value(ctx, mvs, m):
    e = Engine(ctx, mvs + [m])
    for x in mvs:
        e.apply(x)
    return e, e.apply(m)


def add_movement(ctx, type_, sku, qty, src, dst, lot=None, serials=(), unit_cost=None, ref=None,
                 line=None, reason=None):
    p = ctx.product(sku)
    mvs = load_movements(ctx)
    m = {"id": (mvs[-1]["id"] if mvs else 0) + 1, "at": ctx.now_s, "user": ctx.user, "type": type_,
         "sku": sku, "qty": fq(qty, p["unit"]), "src": src, "dst": dst, "lot": lot,
         "serials": json.dumps(sorted(serials)), "unit_cost": cost4(unit_cost) if unit_cost is not None else None,
         "value": None, "ref": ref, "line": line, "voided": 0, "reason": reason}
    _, value = _replay_with_value(ctx, mvs, m)
    m["value"] = money(value)
    ctx.conn.execute(
        "INSERT INTO movements(id, at, user, type, sku, qty, src, dst, lot, serials, unit_cost, value, ref, "
        "line, voided, reason) VALUES(:id, :at, :user, :type, :sku, :qty, :src, :dst, :lot, :serials, "
        ":unit_cost, :value, :ref, :line, :voided, :reason)", m)
    return m


def mv_json(m):
    return {"id": m["id"], "at": m["at"], "user": m["user"], "type": m["type"], "sku": m["sku"],
            "qty": m["qty"], "from": m["src"], "to": m["dst"], "lot": m["lot"],
            "serials": json.loads(m["serials"] or "[]"), "unit_cost": m["unit_cost"], "value": m["value"],
            "ref": m["ref"]}


def current_stock(ctx):
    return stock_map(load_movements(ctx))


def reserved_map(ctx, picked=None):
    r = defaultdict(Decimal)
    sql = "SELECT * FROM reservations" + ("" if picked is None else f" WHERE picked={int(picked)}")
    for x in ctx.q(sql):
        r[(x["sku"], x["loc"], x["lot"], x["serial"])] += Decimal(x["qty"])
    return r


def free_at(ctx, sku, loc, lot, serial, stock=None, reserved=None):
    stock = current_stock(ctx) if stock is None else stock
    reserved = reserved_map(ctx) if reserved is None else reserved
    k = (sku, loc, lot, serial)
    return stock.get(k, ZERO) - reserved.get(k, ZERO)


# ---------------------------------------------------------------- users

def valid_name(name):
    if not re.fullmatch(r"[a-z0-9._-]{1,32}", name or ""):
        raise UserError(f"bad user name {name!r}")


def init(conn, now, currency, admin):
    if conn.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone():
        raise UserError("the book already exists")
    if not re.fullmatch(r"[A-Z]{3}", currency or ""):
        raise UserError("bad currency")
    valid_name(admin)
    conn.executescript(SCHEMA)
    ctx = Ctx(conn, now, admin)
    ctx.set_meta("currency", currency)
    ctx.ex("INSERT INTO users VALUES(?, 'admin', 1)", admin)
    ctx.audit("init", currency)
    return {"currency": currency, "admin": admin}


def enabled_admins(ctx):
    return [r["name"] for r in ctx.q("SELECT name FROM users WHERE role='admin' AND enabled=1")]


def user_add(ctx, name, role):
    valid_name(name)
    if role not in ROLES:
        raise UserError(f"unknown role {role}")
    if ctx.one("SELECT 1 FROM users WHERE name=?", name):
        raise UserError(f"user {name} exists")
    ctx.ex("INSERT INTO users VALUES(?, ?, 1)", name, role)
    ctx.audit("user.add", name)
    return user_json(ctx, name)


def get_user(ctx, name):
    u = ctx.one("SELECT * FROM users WHERE name=?", name)
    if not u:
        raise NotFound(f"unknown user {name}")
    return u


def user_role(ctx, name, role):
    u = get_user(ctx, name)
    if role not in ROLES:
        raise UserError(f"unknown role {role}")
    if u["role"] == "admin" and role != "admin" and u["enabled"] and enabled_admins(ctx) == [name]:
        raise UserError("can't lower the last admin")
    ctx.ex("UPDATE users SET role=? WHERE name=?", role, name)
    ctx.audit("user.role", name)
    return user_json(ctx, name)


def user_disable(ctx, name):
    u = get_user(ctx, name)
    if u["role"] == "admin" and u["enabled"] and enabled_admins(ctx) == [name]:
        raise UserError("can't disable the last admin")
    ctx.ex("UPDATE users SET enabled=0 WHERE name=?", name)
    ctx.audit("user.disable", name)
    return user_json(ctx, name)


def user_json(ctx, name):
    u = get_user(ctx, name)
    return {"name": u["name"], "role": u["role"], "enabled": bool(u["enabled"])}


def user_list(ctx):
    return [user_json(ctx, r["name"]) for r in ctx.q("SELECT name FROM users ORDER BY name")]


# ---------------------------------------------------------------- products, warehouses, locations

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


# ---------------------------------------------------------------- stock movements

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
    p = ctx.product(sku)
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
    p = ctx.product(sku)
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


# ---------------------------------------------------------------- costing reports

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


# ---------------------------------------------------------------- purchase orders

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


# ---------------------------------------------------------------- customers, prices, promotions

def customer_add(ctx, name, price_list=None):
    name = (name or "").strip()
    if not 1 <= len(name) <= 60:
        raise UserError("a customer name is 1 to 60 characters")
    if price_list is not None and not re.fullmatch(r"[A-Z0-9]{1,10}", price_list):
        raise UserError(f"bad price list {price_list!r}")
    if ctx.one("SELECT 1 FROM customers WHERE name=?", name):
        raise UserError(f"customer {name} exists")
    ctx.ex("INSERT INTO customers VALUES(?, ?)", name, price_list)
    ctx.audit("customer.add", name)
    return {"name": name, "price_list": price_list}


def customer_list(ctx):
    return [{"name": r["name"], "price_list": r["price_list"]} for r in ctx.q("SELECT * FROM customers ORDER BY name")]


def price_set(ctx, lst, sku, price_s, min_qty="0"):
    if not re.fullmatch(r"[A-Z0-9]{1,10}", lst or ""):
        raise UserError(f"bad price list {lst!r}")
    p = ctx.product(sku)
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
        ctx.product(sku)
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


# ---------------------------------------------------------------- sales orders

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


# ---------------------------------------------------------------- transfers

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


# ---------------------------------------------------------------- returns

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


# ---------------------------------------------------------------- running a command

def connect(path):
    conn = sqlite3.connect(path, isolation_level=None, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def authorize(ctx, name, need):
    if not name:
        raise HttpError(401, "--user is needed")
    u = ctx.one("SELECT * FROM users WHERE name=?", name)
    if not u or not u["enabled"]:
        raise HttpError(401, f"unknown or disabled user {name}")
    if ROLES.index(u["role"]) < ROLES.index(need):
        raise HttpError(403, f"{name} may not do this")


def run(db, now, user, need, fn):
    """One all-or-nothing command: expire reservations, check the user, run fn(ctx)."""
    conn = connect(db)
    try:
        if not conn.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone():
            raise UserError("no book here: run init first")
        conn.execute("BEGIN IMMEDIATE")
        ctx = Ctx(conn, now, user)
        try:
            expire_reservations(ctx)
            authorize(ctx, user, need)
            out = fn(ctx)
            conn.execute("COMMIT")
            return out
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UserError(message)


def build_parser():
    ap = Parser(prog="wms")
    ap.add_argument("--db", default="wms.db")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--user")
    ap.add_argument("--now")
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=Parser)

    def group(name):
        p = sub.add_parser(name)
        return p.add_subparsers(dest="sub", required=True, parser_class=Parser)

    p = sub.add_parser("init")
    p.add_argument("--currency", required=True)
    p.add_argument("--admin", required=True)
    g = group("user")
    p = g.add_parser("add"); p.add_argument("name"); p.add_argument("--role", required=True)
    p = g.add_parser("role"); p.add_argument("name"); p.add_argument("role")
    p = g.add_parser("disable"); p.add_argument("name")
    g.add_parser("list")
    g = group("product")
    p = g.add_parser("add"); p.add_argument("sku"); p.add_argument("--name", required=True)
    for o in ("--unit", "--tracking", "--costing", "--min", "--max"):
        p.add_argument(o)
    p = g.add_parser("show"); p.add_argument("sku")
    p = g.add_parser("list"); p.add_argument("--search")
    p = g.add_parser("edit"); p.add_argument("sku"); p.add_argument("--version", required=True)
    for o in ("--name", "--min", "--max"):
        p.add_argument(o, default=UNSET)
    g = group("import")
    p = g.add_parser("products"); p.add_argument("file")
    g = group("warehouse")
    p = g.add_parser("add"); p.add_argument("code"); p.add_argument("--name", required=True)
    g.add_parser("list")
    g = group("location")
    p = g.add_parser("add"); p.add_argument("loc"); p.add_argument("--type", default="storage")
    p = g.add_parser("list"); p.add_argument("wh")
    p = sub.add_parser("receive")
    p.add_argument("sku"); p.add_argument("qty"); p.add_argument("--at", required=True)
    p.add_argument("--cost", required=True); p.add_argument("--lot"); p.add_argument("--expires")
    p.add_argument("--serial")
    p = sub.add_parser("move")
    p.add_argument("sku"); p.add_argument("qty"); p.add_argument("--from", dest="src", required=True)
    p.add_argument("--to", dest="dst", required=True); p.add_argument("--lot"); p.add_argument("--serial")
    p = sub.add_parser("adjust")
    p.add_argument("sku"); p.add_argument("--at", required=True); p.add_argument("--count", required=True)
    p.add_argument("--reason", required=True); p.add_argument("--lot")
    p = sub.add_parser("scrap")
    p.add_argument("sku"); p.add_argument("qty"); p.add_argument("--at", required=True)
    p.add_argument("--reason", required=True); p.add_argument("--lot"); p.add_argument("--serial")
    g = group("movement")
    p = g.add_parser("list")
    for o in ("--sku", "--warehouse", "--type", "--since", "--until"):
        p.add_argument(o)
    p = g.add_parser("void"); p.add_argument("id"); p.add_argument("--reason", required=True)
    p = sub.add_parser("valuation"); p.add_argument("--warehouse"); p.add_argument("--at")
    p = sub.add_parser("aging"); p.add_argument("--warehouse", required=True); p.add_argument("--at")
    g = group("po")
    p = g.add_parser("create"); p.add_argument("--supplier", required=True)
    p.add_argument("--warehouse", required=True); p.add_argument("--line", action="append", default=[])
    p = g.add_parser("receive"); p.add_argument("po"); p.add_argument("--line", required=True)
    p.add_argument("--qty", required=True); p.add_argument("--at", required=True); p.add_argument("--lot")
    p.add_argument("--expires"); p.add_argument("--serial")
    p = g.add_parser("close"); p.add_argument("po")
    p = g.add_parser("show"); p.add_argument("po")
    p = g.add_parser("list"); p.add_argument("--status")
    g = group("customer")
    p = g.add_parser("add"); p.add_argument("name"); p.add_argument("--price-list")
    g.add_parser("list")
    g = group("price")
    p = g.add_parser("set"); p.add_argument("list"); p.add_argument("sku"); p.add_argument("price")
    p.add_argument("--min-qty", default="0")
    p = g.add_parser("list"); p.add_argument("--list")
    g = group("promo")
    p = g.add_parser("add"); p.add_argument("code"); p.add_argument("--sku"); p.add_argument("--order", action="store_true")
    p.add_argument("--threshold"); p.add_argument("--percent", required=True)
    p.add_argument("--from", dest="dfrom", required=True); p.add_argument("--to", dest="dto", required=True)
    g.add_parser("list")
    g = group("so")
    p = g.add_parser("create"); p.add_argument("--customer", required=True)
    p.add_argument("--warehouse", required=True); p.add_argument("--line", action="append", default=[])
    p = g.add_parser("confirm"); p.add_argument("so"); p.add_argument("--hold")
    for name in ("allocate", "pick", "ship", "cancel", "show"):
        p = g.add_parser(name); p.add_argument("so")
    p = g.add_parser("list"); p.add_argument("--status")
    p = sub.add_parser("stock")
    for o in ("--warehouse", "--sku", "--at"):
        p.add_argument(o)
    p = sub.add_parser("available"); p.add_argument("sku"); p.add_argument("--warehouse", required=True)
    g = group("transfer")
    p = g.add_parser("create"); p.add_argument("sku"); p.add_argument("qty")
    p.add_argument("--from", dest="src", required=True); p.add_argument("--to", dest="dst", required=True)
    p.add_argument("--lot"); p.add_argument("--serial")
    for name in ("receive", "cancel", "show"):
        p = g.add_parser(name); p.add_argument("tr")
    p = g.add_parser("list"); p.add_argument("--status")
    g = group("return")
    p = g.add_parser("create"); p.add_argument("so"); p.add_argument("--line", required=True)
    p.add_argument("--qty", required=True); p.add_argument("--condition", required=True)
    p.add_argument("--to"); p.add_argument("--lot"); p.add_argument("--serial")
    p = g.add_parser("list"); p.add_argument("--order")
    p = sub.add_parser("reorder"); p.add_argument("--warehouse", required=True)
    g = group("audit")
    p = g.add_parser("list"); p.add_argument("--action"); p.add_argument("--user", dest="by")
    p = sub.add_parser("serve"); p.add_argument("--port", type=int, default=8080)
    return ap


def dispatch(a):
    """(command name, function of ctx) for parsed arguments."""
    c = a.cmd + (" " + a.sub if getattr(a, "sub", None) else "")
    table = {
        "user add": lambda x: user_add(x, a.name, a.role),
        "user role": lambda x: user_role(x, a.name, a.role),
        "user disable": lambda x: user_disable(x, a.name),
        "user list": user_list,
        "product add": lambda x: product_add(x, a.sku, a.name, a.unit, a.tracking, a.costing, a.min, a.max),
        "product show": lambda x: product_json(x.product(a.sku)),
        "product list": lambda x: product_list(x, a.search),
        "product edit": lambda x: product_edit(x, a.sku, a.version, a.name, a.min, a.max),
        "import products": lambda x: import_products(x, a.file),
        "warehouse add": lambda x: warehouse_add(x, a.code, a.name),
        "warehouse list": warehouse_list,
        "location add": lambda x: location_add(x, a.loc, a.type),
        "location list": lambda x: location_list(x, a.wh),
        "receive": lambda x: receive(x, a.sku, a.qty, a.at, a.cost, a.lot, a.expires, a.serial),
        "move": lambda x: move(x, a.sku, a.qty, a.src, a.dst, a.lot, a.serial),
        "adjust": lambda x: adjust(x, a.sku, a.at, a.count, a.reason, a.lot),
        "scrap": lambda x: scrap(x, a.sku, a.qty, a.at, a.reason, a.lot, a.serial),
        "movement list": lambda x: movement_list(x, a.sku, a.warehouse, a.type, a.since, a.until),
        "movement void": lambda x: movement_void(x, a.id, a.reason),
        "valuation": lambda x: valuation(x, a.warehouse, a.at),
        "aging": lambda x: aging(x, a.warehouse, a.at),
        "po create": lambda x: po_create(x, a.supplier, a.warehouse, a.line),
        "po receive": lambda x: po_receive(x, a.po, a.line, a.qty, a.at, a.lot, a.expires, a.serial),
        "po close": lambda x: po_close(x, a.po),
        "po show": lambda x: po_show(x, a.po),
        "po list": lambda x: po_list(x, a.status),
        "customer add": lambda x: customer_add(x, a.name, a.price_list),
        "customer list": customer_list,
        "price set": lambda x: price_set(x, a.list, a.sku, a.price, a.min_qty),
        "price list": lambda x: price_list(x, a.list),
        "promo add": lambda x: promo_add(x, a.code, a.sku, a.order, a.threshold, a.percent, a.dfrom, a.dto),
        "promo list": promo_list,
        "so create": lambda x: so_create(x, a.customer, a.warehouse, a.line),
        "so confirm": lambda x: so_confirm(x, a.so, a.hold),
        "so allocate": lambda x: so_allocate(x, a.so),
        "so pick": lambda x: so_pick(x, a.so),
        "so ship": lambda x: so_ship(x, a.so),
        "so cancel": lambda x: so_cancel(x, a.so),
        "so show": lambda x: so_show(x, a.so),
        "so list": lambda x: so_list(x, a.status),
        "stock": lambda x: stock_report(x, a.warehouse, a.sku, a.at),
        "available": lambda x: available(x, a.sku, a.warehouse),
        "transfer create": lambda x: transfer_create(x, a.sku, a.qty, a.src, a.dst, a.lot, a.serial),
        "transfer receive": lambda x: transfer_finish(x, a.tr, False),
        "transfer cancel": lambda x: transfer_finish(x, a.tr, True),
        "transfer show": lambda x: tr_json(tr_get(x, a.tr)),
        "transfer list": lambda x: transfer_list(x, a.status),
        "return create": lambda x: return_create(x, a.so, a.line, a.qty, a.condition, a.to, a.lot, a.serial),
        "return list": lambda x: return_list(x, a.order),
        "reorder": lambda x: reorder(x, a.warehouse),
        "audit list": lambda x: audit_list(x, a.action, a.by),
    }
    return c, table[c]


def main(argv):
    try:
        a = build_parser().parse_args(argv)
        now = parse_time(a.now) if a.now else datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        if a.cmd == "serve":
            return serve(a.db, a.port)
        if a.cmd == "init":
            conn = connect(a.db)   # init checks everything before executescript, which commits itself
            try:
                out = init(conn, now, a.currency, a.admin)
            finally:
                conn.close()
        else:
            c, fn = dispatch(a)
            out = run(a.db, now, a.user, NEED.get(c, "viewer"), fn)
        print(json.dumps(out, indent=None if a.json else 2))
        return 0
    except ImportErrors as e:
        for line in e.lines:
            print(f"error: {line}", file=sys.stderr)
        return 2
    except UserError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------- HTTP

LOCK = threading.Lock()


def strings(body, *keys):
    for k in keys:
        if k in body and body[k] is not None and not isinstance(body[k], str):
            raise UserError(f"{k} must be a string")


def serve(db, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.handle_req("GET")

        def do_POST(self):
            self.handle_req("POST")

        def do_PATCH(self):
            self.handle_req("PATCH")

        def reply(self, status, obj, headers=()):
            data = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            for k, v in headers:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def handle_req(self, method):
            url = urlparse(self.path)
            qs = {k: v[-1] for k, v in parse_qs(url.query).items()}
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode() if method != "GET" else ""
            with LOCK:
                status, obj, headers = self.process(method, url.path, qs, raw)
            self.reply(status, obj, headers)

        def process(self, method, path, qs, raw):
            conn = connect(db)
            key = self.headers.get("Idempotency-Key") if method == "POST" else None
            try:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    now = parse_time(self.headers["X-Now"]) if self.headers.get("X-Now") else \
                        datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
                    ctx = Ctx(conn, now, self.headers.get("X-User"))
                    expire_reservations(ctx)
                    route, need, fn = self.route(method, path, qs)
                    authorize(ctx, ctx.user, need)
                    if key:
                        hit = ctx.one("SELECT * FROM idem WHERE key=?", key)
                        if hit:
                            conn.execute("COMMIT")
                            if hit["path"] == path and hit["body"] == raw:
                                return hit["status"], json.loads(hit["response"]), []
                            return 409, {"error": "Idempotency-Key reused with another request"}, []
                    try:
                        body = json.loads(raw) if raw.strip() else {}
                    except ValueError:
                        raise UserError("the body isn't JSON")
                    if not isinstance(body, dict):
                        raise UserError("the body must be a JSON object")
                    status, obj, headers = fn(ctx, body)
                    if key:
                        ctx.ex("INSERT INTO idem VALUES(?, ?, ?, ?, ?)", key, path, raw, status, json.dumps(obj))
                    conn.execute("COMMIT")
                    return status, obj, headers
                except UserError as e:
                    conn.execute("ROLLBACK")
                    status, obj = e.status, {"error": str(e)}
                    if key and status not in (401, 403):
                        conn.execute("BEGIN IMMEDIATE")
                        if not conn.execute("SELECT 1 FROM idem WHERE key=?", (key,)).fetchone():
                            conn.execute("INSERT INTO idem VALUES(?, ?, ?, ?, ?)", (key, path, raw, status, json.dumps(obj)))
                        conn.execute("COMMIT")
                    return status, obj, []
            finally:
                conn.close()

        def route(self, method, path, qs):
            parts = [p for p in path.split("/") if p]
            if method == "GET" and parts == ["products"]:
                return "products", "viewer", lambda ctx, b: (200, products_page(ctx, qs), [])
            if len(parts) == 2 and parts[0] == "products":
                sku = parts[1]
                if method == "GET":
                    def get(ctx, b):
                        p = product_json(ctx.product(sku))
                        return 200, p, [("ETag", f'"{p["version"]}"')]
                    return "product", "viewer", get
                if method == "PATCH":
                    def patch(ctx, b):
                        ctx.product(sku)
                        im = self.headers.get("If-Match")
                        if not im:
                            raise HttpError(428, "If-Match is needed")
                        m = re.fullmatch(r'"(\d+)"', im.strip())
                        if not m:
                            raise HttpError(412, "bad If-Match")
                        strings(b, "name", "min", "max")
                        p = product_edit(ctx, sku, m.group(1), b.get("name", UNSET), b.get("min", UNSET),
                                         b.get("max", UNSET), http=True)
                        return 200, p, [("ETag", f'"{p["version"]}"')]
                    return "product", "manager", patch
            if method == "POST" and parts == ["receipts"]:
                def post(ctx, b):
                    strings(b, "sku", "qty", "at", "cost", "lot", "expires")
                    if b.get("serials") is not None and (not isinstance(b["serials"], list) or
                                                         not all(isinstance(s, str) for s in b["serials"])):
                        raise UserError("serials must be a list of strings")
                    return 201, receive(ctx, b.get("sku"), b.get("qty"), b.get("at"), b.get("cost"), b.get("lot"),
                                        b.get("expires"), b.get("serials")), []
                return "receipts", "clerk", post
            if method == "POST" and parts == ["sales-orders"]:
                def post_so(ctx, b):
                    strings(b, "customer", "warehouse")
                    lines = b.get("lines")
                    if not isinstance(lines, list) or not all(isinstance(x, dict) for x in lines):
                        raise UserError("lines must be a list of objects")
                    for x in lines:
                        strings(x, "sku", "qty")
                    return 201, so_create(ctx, b.get("customer"), b.get("warehouse"), lines), []
                return "so", "manager", post_so
            if method == "POST" and len(parts) == 3 and parts[0] == "sales-orders" and parts[2] == "confirm":
                def confirm(ctx, b):
                    so_get(ctx, parts[1])
                    hold = b.get("hold")
                    if hold is not None and (isinstance(hold, bool) or not isinstance(hold, int)):
                        raise UserError("hold is a whole number of hours")
                    return 200, so_confirm(ctx, parts[1], hold), []
                return "confirm", "manager", confirm
            if method == "GET" and len(parts) == 2 and parts[0] == "sales-orders":
                return "so", "viewer", lambda ctx, b: (200, so_show(ctx, parts[1]), [])
            if method == "GET" and parts == ["stock"]:
                return "stock", "viewer", lambda ctx, b: (200, stock_report(ctx, qs.get("warehouse"), qs.get("sku")), [])
            if method == "GET" and parts == ["valuation"]:
                return "valuation", "viewer", lambda ctx, b: (200, valuation(ctx, qs.get("warehouse")), [])
            raise NotFound(f"no route {method} {path}")

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def products_page(ctx, qs):
    try:
        limit = int(qs.get("limit", "50"))
    except ValueError:
        raise UserError("bad limit")
    if not 1 <= limit <= 100:
        raise UserError("limit is 1 to 100")
    rows = product_list(ctx, qs.get("search"))
    after = qs.get("after")
    if after:
        rows = [r for r in rows if r["sku"] > after]
    page = rows[:limit]
    return {"items": page, "next": page[-1]["sku"] if len(rows) > limit else None}
