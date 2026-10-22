"""Running a command: users and authorisation, the argument parser, dispatch."""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from .catalog import UNSET, import_products, location_add, location_list, product_add, product_edit, product_json, product_list, warehouse_add, warehouse_list
from .core import ImportErrors, NEED, UserError, parse_time
from .http import serve
from .orders import available, reorder, so_allocate, so_cancel, so_confirm, so_create, so_list, so_pick, so_ship, so_show, stock_report
from .pricing import customer_add, customer_list, price_list, price_set, promo_add, promo_list
from .purchasing import po_close, po_create, po_list, po_receive, po_show
from .reports import aging, valuation
from .returns import audit_list, return_create, return_list
from .session import connect, run
from .stock import adjust, move, movement_list, movement_void, receive, scrap
from .transfers import tr_get, tr_json, transfer_create, transfer_finish, transfer_list
from .users import init, user_add, user_disable, user_list, user_role


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
