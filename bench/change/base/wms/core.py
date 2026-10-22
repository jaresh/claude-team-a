"""Errors, parsing and formatting helpers, the schema and the command context."""
import re
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal


# Stock and costing are derived by replaying the movement log in id order (see ledger.py), so
# `--at` reports, voids and transfers all follow from one definition.


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
