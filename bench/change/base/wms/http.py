"""The HTTP API."""
import json
import re
import threading
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from .catalog import UNSET, product_edit, product_json, product_list
from .core import Ctx, HttpError, NotFound, UserError, parse_time
from .orders import expire_reservations, so_confirm, so_create, so_get, so_show, stock_report
from .reports import valuation
from .session import authorize, connect
from .stock import receive


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
