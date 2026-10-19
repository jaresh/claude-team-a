"""Hidden acceptance tests for the warehouse benchmark. Never shown to the model under test.

Run against an app: APP_DIR=/path/to/repo python3 -m unittest discover -s bench/warehouse/accept
Class names carry the tier: T1 (one feature), T2 (features combined), T3 (robustness: atomicity,
permissions, HTTP, concurrency). Every expected value follows from prompt.md; all pass against
bench/warehouse/reference."""
import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

APP = os.environ.get("APP_DIR") or os.environ.get("FIN_DIR") or os.getcwd()
T0 = "2026-03-01T08:00:00Z"
NOW = "2026-03-05T10:00:00Z"


def at(day, hh=9, mm=0, month=3):
    return f"2026-{month:02d}-{day:02d}T{hh:02d}:{mm:02d}:00Z"


def wms(db, *args, user="alice", now=NOW):
    cmd = [sys.executable, "-m", "wms", "--db", db, "--json"]
    if user:
        cmd += ["--user", user]
    if now:
        cmd += ["--now", now]
    return subprocess.run(cmd + list(args), cwd=APP, capture_output=True, text=True, timeout=60)


_TEMPLATE = None


def template():
    """The standard world, built once and copied for every test."""
    global _TEMPLATE
    if _TEMPLATE:
        return _TEMPLATE
    d = tempfile.mkdtemp(prefix="wms-template-")
    atexit.register(shutil.rmtree, d, True)
    db = os.path.join(d, "wms.db")
    steps = [
        (None, ["init", "--currency", "EUR", "--admin", "alice"]),
        ("alice", ["user", "add", "bob", "--role", "clerk"]),
        ("alice", ["user", "add", "carol", "--role", "manager"]),
        ("alice", ["user", "add", "vic", "--role", "viewer"]),
        ("alice", ["warehouse", "add", "WH1", "--name", "Main"]),
        ("alice", ["warehouse", "add", "WH2", "--name", "North"]),
        ("alice", ["location", "add", "WH1/A-01"]),
        ("alice", ["location", "add", "WH1/A-02"]),
        ("alice", ["location", "add", "WH1/B-01"]),
        ("alice", ["location", "add", "WH1/DOCK", "--type", "receiving"]),
        ("alice", ["location", "add", "WH2/S-01"]),
        ("alice", ["product", "add", "BOLT", "--name", "Bolt M8", "--min", "50", "--max", "200"]),
        ("alice", ["product", "add", "FLOUR", "--name", "Flour", "--unit", "kg", "--costing", "average"]),
        ("alice", ["product", "add", "MILK", "--name", "Milk 1L", "--tracking", "lot"]),
        ("alice", ["product", "add", "PHONE", "--name", "Phone X", "--tracking", "serial"]),
        ("alice", ["customer", "add", "Bistro", "--price-list", "TRADE"]),
        ("alice", ["customer", "add", "Shop"]),
        ("alice", ["price", "set", "STANDARD", "BOLT", "0.25"]),
        ("alice", ["price", "set", "TRADE", "BOLT", "0.20"]),
        ("alice", ["price", "set", "TRADE", "BOLT", "0.18", "--min-qty", "100"]),
        ("alice", ["price", "set", "STANDARD", "FLOUR", "1.50"]),
        ("alice", ["price", "set", "STANDARD", "MILK", "0.90"]),
        ("alice", ["price", "set", "STANDARD", "PHONE", "299.00"]),
    ]
    for user, args in steps:
        r = wms(db, *args, user=user, now=T0)
        if r.returncode != 0:
            raise RuntimeError(f"building the test world failed at {args}: {r.stderr[-500:]}")
    _TEMPLATE = db
    return db


class World(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "wms.db")
        src = template()
        for suffix in ("", "-wal", "-shm", "-journal"):
            if os.path.exists(src + suffix):
                shutil.copyfile(src + suffix, self.db + suffix)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args, user="alice", now=NOW):
        return wms(self.db, *args, user=user, now=now)

    def ok(self, *args, user="alice", now=NOW):
        r = self.run_cmd(*args, user=user, now=now)
        self.assertEqual(r.returncode, 0, f"{args}: exit {r.returncode}: {r.stderr[-600:]}")
        try:
            return json.loads(r.stdout)
        except ValueError:
            self.fail(f"{args}: stdout is not one JSON document: {r.stdout[:300]!r}")

    def err(self, *args, user="alice", now=NOW):
        r = self.run_cmd(*args, user=user, now=now)
        self.assertEqual(r.returncode, 2, f"{args}: expected exit 2, got {r.returncode}: {r.stdout[:200]} {r.stderr[-300:]}")
        self.assertEqual(r.stdout.strip(), "", f"{args}: stdout should be empty on a user error")
        self.assertIn("error", r.stderr.lower(), f"{args}: no error message")
        return r

    # helpers
    def receive(self, sku, qty, loc, cost, *extra, now=NOW, user="alice"):
        return self.ok("receive", sku, str(qty), "--at", loc, "--cost", str(cost), *extra, now=now, user=user)

    def stock_rows(self, *args, now=NOW):
        return {(r["location"], r["sku"], r["lot"]): r for r in self.ok("stock", *args, now=now)}

    def val_rows(self, *args, now=NOW):
        v = self.ok("valuation", *args, now=now)
        return {(r["sku"], r["warehouse"]): (r["qty"], r["value"]) for r in v["rows"]}, v

    def order(self, customer, wh, *lines, now=NOW):
        so = self.ok("so", "create", "--customer", customer, "--warehouse", wh,
                     *sum((["--line", x] for x in lines), []), now=now)
        return so["id"]


# ===================================================================== T1: one feature at a time

class T1Users(World):
    def test_roles_and_last_admin(self):
        self.assertEqual(self.ok("user", "list"), [
            {"name": "alice", "role": "admin", "enabled": True},
            {"name": "bob", "role": "clerk", "enabled": True},
            {"name": "carol", "role": "manager", "enabled": True},
            {"name": "vic", "role": "viewer", "enabled": True}])
        self.err("product", "add", "NUTS", "--name", "Nuts", user="bob")
        self.ok("product", "list", user="vic")
        self.err("receive", "BOLT", "1", "--at", "WH1/A-01", "--cost", "1", user="vic")
        self.err("user", "role", "alice", "manager")
        self.err("user", "disable", "alice")
        self.ok("user", "add", "dave", "--role", "admin")
        self.assertEqual(self.ok("user", "role", "alice", "clerk")["role"], "clerk")
        self.ok("user", "disable", "vic", user="dave")
        self.err("product", "list", user="vic")
        self.err("product", "list", user="nobody")
        self.err("product", "list", user=None)

    def test_user_rules(self):
        self.err("init", "--currency", "EUR", "--admin", "zed", user=None)
        self.err("user", "add", "Bob2", "--role", "clerk")
        self.err("user", "add", "bob", "--role", "clerk")
        self.err("user", "add", "eve", "--role", "boss")
        self.err("user", "role", "ghost", "clerk")


class T1Products(World):
    def test_show_and_defaults(self):
        self.assertEqual(self.ok("product", "show", "BOLT"), {
            "sku": "BOLT", "name": "Bolt M8", "unit": "each", "tracking": "none", "costing": "fifo",
            "min": "50", "max": "200", "version": 1})
        f = self.ok("product", "show", "FLOUR")
        self.assertEqual((f["unit"], f["costing"], f["min"], f["max"]), ("kg", "average", None, None))
        self.assertEqual(self.ok("product", "add", "SALT", "--name", "  Salt  ", "--unit", "kg",
                                 "--min", "1.5")["min"], "1.500")
        self.assertEqual(self.ok("product", "show", "SALT")["name"], "Salt")

    def test_validation(self):
        for sku in ("ab", "1ABC", "A" * 21, "AB_C", "abc"):
            self.err("product", "add", sku, "--name", "X")
        self.err("product", "add", "BOLT", "--name", "Again")
        self.err("product", "add", "SERI", "--name", "X", "--unit", "kg", "--tracking", "serial")
        self.err("product", "add", "MINMAX", "--name", "X", "--min", "10", "--max", "5")
        self.err("product", "add", "BLANK", "--name", "   ")
        self.err("product", "add", "HALF", "--name", "X", "--min", "1.5")
        self.err("product", "add", "FINE", "--name", "X", "--unit", "kg", "--min", "1.2345")
        self.err("product", "add", "ODD", "--name", "X", "--costing", "lifo")

    def test_list_and_search(self):
        self.assertEqual([p["sku"] for p in self.ok("product", "list")], ["BOLT", "FLOUR", "MILK", "PHONE"])
        self.assertEqual([p["sku"] for p in self.ok("product", "list", "--search", "m8")], ["BOLT"])
        self.assertEqual([p["sku"] for p in self.ok("product", "list", "--search", "il")], ["MILK"])

    def test_edit_versions(self):
        p = self.ok("product", "edit", "BOLT", "--version", "1", "--name", "Bolt M8 zinc")
        self.assertEqual((p["name"], p["version"]), ("Bolt M8 zinc", 2))
        self.err("product", "edit", "BOLT", "--version", "1", "--name", "Stale")
        self.err("product", "edit", "BOLT", "--version", "2", "--max", "10")
        p = self.ok("product", "edit", "BOLT", "--version", "2", "--min", "none")
        self.assertEqual((p["min"], p["max"], p["version"]), (None, "200", 3))
        self.assertEqual(self.ok("product", "show", "BOLT")["name"], "Bolt M8 zinc")


class T1Locations(World):
    def test_warehouses_and_locations(self):
        self.assertEqual(self.ok("warehouse", "list"), [{"code": "WH1", "name": "Main"}, {"code": "WH2", "name": "North"}])
        self.assertEqual(self.ok("location", "list", "WH1"), [
            {"location": "WH1/A-01", "type": "storage"}, {"location": "WH1/A-02", "type": "storage"},
            {"location": "WH1/B-01", "type": "storage"}, {"location": "WH1/DOCK", "type": "receiving"},
            {"location": "WH1/RECV", "type": "receiving"}, {"location": "WH1/SHIP", "type": "shipping"}])
        self.err("warehouse", "add", "w1", "--name", "Lower")
        self.err("warehouse", "add", "WH1", "--name", "Again")
        self.err("location", "add", "WH1/A-01")
        self.err("location", "add", "WH9/A-01")
        self.err("location", "add", "WH1/X-01", "--type", "shipping")


class T1Receive(World):
    def test_receive_movement(self):
        m = self.receive("BOLT", 100, "WH1/A-01", "0.12", now=at(2), user="bob")
        self.assertEqual(m, {"id": 1, "at": at(2), "user": "bob", "type": "receive", "sku": "BOLT", "qty": "100",
                             "from": None, "to": "WH1/A-01", "lot": None, "serials": [], "unit_cost": "0.1200",
                             "value": "12.00", "ref": None})
        row = self.stock_rows()[("WH1/A-01", "BOLT", None)]
        self.assertEqual((row["on_hand"], row["reserved"], row["available"], row["serials"]), ("100", "0", "100", []))

    def test_receive_rules(self):
        self.err("receive", "BOLT", "1", "--at", "WH1/SHIP", "--cost", "1")
        self.err("receive", "BOLT", "1.5", "--at", "WH1/A-01", "--cost", "1")
        self.err("receive", "BOLT", "0", "--at", "WH1/A-01", "--cost", "1")
        self.err("receive", "BOLT", "1", "--at", "WH1/A-01", "--cost", "-1")
        self.err("receive", "BOLT", "1", "--at", "WH1/A-01", "--cost", "0.12345")
        self.err("receive", "BOLT", "1", "--at", "WH1/A-01", "--cost", "1", "--lot", "L1", "--expires", "2026-06-01")
        self.err("receive", "MILK", "5", "--at", "WH1/A-01", "--cost", "1")
        self.err("receive", "MILK", "5", "--at", "WH1/A-01", "--cost", "1", "--lot", "L1")
        self.receive("MILK", 5, "WH1/A-01", "0.50", "--lot", "L1", "--expires", "2026-06-01")
        self.err("receive", "MILK", "5", "--at", "WH1/A-02", "--cost", "1", "--lot", "L1", "--expires", "2026-07-01")
        self.err("receive", "PHONE", "2", "--at", "WH1/A-01", "--cost", "100", "--serial", "P1")
        self.err("receive", "PHONE", "2", "--at", "WH1/A-01", "--cost", "100", "--serial", "P1,P1")
        self.assertEqual(self.receive("PHONE", 2, "WH1/A-01", "100", "--serial", "P2,P1")["serials"], ["P1", "P2"])
        self.err("receive", "PHONE", "1", "--at", "WH1/A-02", "--cost", "100", "--serial", "P2")
        self.assertEqual(self.receive("FLOUR", "2.5", "WH1/A-01", "1")["qty"], "2.500")
        self.err("receive", "FLOUR", "1.2345", "--at", "WH1/A-01", "--cost", "1")


class T1Movements(World):
    def test_move_and_list(self):
        self.receive("BOLT", 100, "WH1/A-01", "0.12", now=at(2))
        m = self.ok("move", "BOLT", "30", "--from", "WH1/A-01", "--to", "WH1/A-02", now=at(3))
        self.assertEqual((m["type"], m["from"], m["to"], m["value"], m["unit_cost"]), ("move", "WH1/A-01", "WH1/A-02", "0.00", None))
        rows = self.stock_rows()
        self.assertEqual((rows[("WH1/A-01", "BOLT", None)]["on_hand"], rows[("WH1/A-02", "BOLT", None)]["on_hand"]), ("70", "30"))
        self.err("move", "BOLT", "1", "--from", "WH1/A-01", "--to", "WH1/SHIP")
        self.err("move", "BOLT", "1", "--from", "WH1/A-01", "--to", "WH2/S-01")
        self.err("move", "BOLT", "80", "--from", "WH1/A-01", "--to", "WH1/B-01")
        self.assertEqual([x["id"] for x in self.ok("movement", "list", "--type", "move")], [2])
        self.assertEqual(self.ok("movement", "list", "--warehouse", "WH2"), [])
        self.assertEqual([x["id"] for x in self.ok("movement", "list", "--since", at(3), "--until", at(3))], [2])
        self.assertEqual([x["id"] for x in self.ok("movement", "list", "--until", at(2))], [1])

    def test_adjust(self):
        self.receive("BOLT", 100, "WH1/A-01", "0.12")
        m = self.ok("adjust", "BOLT", "--at", "WH1/A-01", "--count", "97", "--reason", "count")
        self.assertEqual((m["type"], m["from"], m["to"], m["qty"], m["value"]), ("adjust", "WH1/A-01", None, "3", "0.36"))
        self.err("adjust", "BOLT", "--at", "WH1/A-01", "--count", "97", "--reason", "count")
        m = self.ok("adjust", "BOLT", "--at", "WH1/A-01", "--count", "99", "--reason", "found")
        self.assertEqual((m["from"], m["to"], m["qty"], m["value"]), (None, "WH1/A-01", "2", "0.24"))
        self.receive("PHONE", 1, "WH1/A-01", "100", "--serial", "P1")
        self.err("adjust", "PHONE", "--at", "WH1/A-01", "--count", "0", "--reason", "gone")
        self.err("adjust", "MILK", "--at", "WH1/A-01", "--count", "3", "--reason", "found", "--lot", "NEVER")

    def test_scrap(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.12")
        m = self.ok("scrap", "BOLT", "4", "--at", "WH1/A-01", "--reason", "damaged")
        self.assertEqual((m["type"], m["to"], m["value"]), ("scrap", None, "0.48"))
        self.err("scrap", "BOLT", "7", "--at", "WH1/A-01", "--reason", "damaged")


class T1Costing(World):
    def test_fifo_layers(self):
        self.receive("BOLT", 100, "WH1/A-01", "0.10", now=at(2))
        self.receive("BOLT", 50, "WH1/A-01", "0.13", now=at(3))
        self.assertEqual(self.ok("scrap", "BOLT", "120", "--at", "WH1/A-01", "--reason", "x")["value"], "12.60")
        self.assertEqual(self.val_rows()[0], {("BOLT", "WH1"): ("30", "3.90")})

    def test_average_cost(self):
        self.receive("FLOUR", 10, "WH1/A-01", "1.00", now=at(2))
        self.assertEqual(self.receive("FLOUR", "5.5", "WH1/A-01", "1.30", now=at(3))["value"], "7.15")
        self.assertEqual(self.ok("scrap", "FLOUR", "3.25", "--at", "WH1/A-01", "--reason", "x")["value"], "3.60")
        self.assertEqual(self.val_rows()[0], {("FLOUR", "WH1"): ("12.250", "13.55")})
        self.assertEqual(self.ok("scrap", "FLOUR", "12.25", "--at", "WH1/A-01", "--reason", "x")["value"], "13.55")
        self.assertEqual(self.val_rows()[0], {})
        m = self.ok("adjust", "FLOUR", "--at", "WH1/A-01", "--count", "2", "--reason", "found")
        self.assertEqual(m["value"], "2.21")
        self.assertEqual(self.val_rows()[0], {("FLOUR", "WH1"): ("2.000", "2.21")})

    def test_valuation_at_and_total(self):
        self.receive("BOLT", 100, "WH1/A-01", "0.10", now=at(2))
        self.receive("FLOUR", 10, "WH1/A-01", "1.00", now=at(3))
        self.ok("scrap", "BOLT", "40", "--at", "WH1/A-01", "--reason", "x", now=at(4))
        v = self.ok("valuation", "--at", at(2, 23, 59))
        self.assertEqual(v, {"rows": [{"sku": "BOLT", "warehouse": "WH1", "qty": "100", "value": "10.00"}],
                             "in_transit": [], "total": "10.00"})
        v = self.ok("valuation")
        self.assertEqual([(r["sku"], r["qty"], r["value"]) for r in v["rows"]], [("BOLT", "60", "6.00"), ("FLOUR", "10.000", "10.00")])
        self.assertEqual(v["total"], "16.00")

    def test_aging(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00", now="2025-11-01T10:00:00Z")
        self.receive("BOLT", 10, "WH1/A-01", "2.00", now="2026-01-15T10:00:00Z")
        self.receive("BOLT", 10, "WH1/A-01", "3.00", now="2026-03-01T10:00:00Z")
        self.receive("FLOUR", 1, "WH1/A-01", "1.00", now="2026-03-01T10:00:00Z")
        self.assertEqual(self.ok("aging", "--warehouse", "WH1", "--at", "2026-03-10"),
                         [{"sku": "BOLT", "0-30": "30.00", "31-90": "20.00", "91+": "10.00"}])


class T1PurchaseOrders(World):
    def test_po_flow(self):
        po = self.ok("po", "create", "--supplier", "Acme", "--warehouse", "WH1",
                     "--line", "BOLT:100:0.12", "--line", "FLOUR:20:1.10")
        self.assertEqual(po, {"id": "PO-0001", "supplier": "Acme", "warehouse": "WH1", "status": "open", "lines": [
            {"line": 1, "sku": "BOLT", "ordered": "100", "received": "0", "open": "100", "unit_cost": "0.1200"},
            {"line": 2, "sku": "FLOUR", "ordered": "20.000", "received": "0.000", "open": "20.000", "unit_cost": "1.1000"}],
            "value_received": "0.00"})
        m = self.ok("po", "receive", "PO-0001", "--line", "1", "--qty", "40", "--at", "WH1/RECV", user="bob")
        self.assertEqual((m["type"], m["ref"], m["unit_cost"], m["value"]), ("receive", "PO-0001", "0.1200", "4.80"))
        self.assertEqual(self.ok("po", "show", "PO-0001")["status"], "partial")
        self.err("po", "receive", "PO-0001", "--line", "1", "--qty", "66", "--at", "WH1/RECV")
        self.ok("po", "receive", "PO-0001", "--line", "1", "--qty", "65", "--at", "WH1/RECV")
        self.ok("po", "receive", "PO-0001", "--line", "2", "--qty", "20", "--at", "WH1/DOCK")
        po = self.ok("po", "show", "PO-0001")
        self.assertEqual((po["status"], po["value_received"], po["lines"][0]["received"], po["lines"][0]["open"]),
                         ("received", "34.60", "105", "0"))
        self.err("po", "receive", "PO-0001", "--line", "2", "--qty", "1", "--at", "WH1/RECV")
        self.assertEqual([p["id"] for p in self.ok("po", "list", "--status", "received")], ["PO-0001"])

    def test_close_and_void(self):
        self.ok("po", "create", "--supplier", "Acme", "--warehouse", "WH1", "--line", "BOLT:10:1.00")
        self.err("po", "receive", "PO-0001", "--line", "1", "--qty", "4", "--at", "WH2/S-01")
        m = self.ok("po", "receive", "PO-0001", "--line", "1", "--qty", "4", "--at", "WH1/RECV")
        self.ok("movement", "void", str(m["id"]), "--reason", "wrong item")
        po = self.ok("po", "show", "PO-0001")
        self.assertEqual((po["status"], po["lines"][0]["received"], po["value_received"]), ("open", "0", "0.00"))
        self.ok("po", "receive", "PO-0001", "--line", "1", "--qty", "4", "--at", "WH1/RECV")
        po = self.ok("po", "close", "PO-0001")
        self.assertEqual((po["status"], po["lines"][0]["open"], po["value_received"]), ("closed", "0", "4.00"))
        self.err("po", "receive", "PO-0001", "--line", "1", "--qty", "1", "--at", "WH1/RECV")
        self.err("po", "close", "PO-0001")


class T1Prices(World):
    def test_lists_and_customers(self):
        self.assertEqual(self.ok("customer", "list"), [{"name": "Bistro", "price_list": "TRADE"}, {"name": "Shop", "price_list": None}])
        self.ok("price", "set", "TRADE", "BOLT", "0.19")
        self.assertEqual(self.ok("price", "list", "--list", "TRADE"), [
            {"list": "TRADE", "sku": "BOLT", "min_qty": "0", "unit_price": "0.1900"},
            {"list": "TRADE", "sku": "BOLT", "min_qty": "100", "unit_price": "0.1800"}])
        self.err("price", "set", "trade", "BOLT", "1")
        self.err("price", "set", "TRADE", "BOLT", "0.12345")

    def test_pricing_by_list_and_breaks(self):
        self.receive("BOLT", 200, "WH1/A-01", "0.10")
        self.receive("FLOUR", 20, "WH1/A-01", "1.00")
        so = self.order("Bistro", "WH1", "BOLT:120", "FLOUR:2.5")
        draft = self.ok("so", "show", so)
        self.assertEqual((draft["status"], draft["lines"][0]["unit_price"], draft["total"]), ("draft", None, None))
        o = self.ok("so", "confirm", so)
        self.assertEqual([(x["unit_price"], x["gross"], x["discount"], x["net"]) for x in o["lines"]],
                         [("0.1800", "21.60", "0.00", "21.60"), ("1.5000", "3.75", "0.00", "3.75")])
        self.assertEqual((o["subtotal"], o["order_discount"], o["total"]), ("25.35", "0.00", "25.35"))
        o = self.ok("so", "confirm", self.order("Bistro", "WH1", "BOLT:99"))
        self.assertEqual(o["lines"][0]["unit_price"], "0.2000")
        o = self.ok("so", "confirm", self.order("Shop", "WH1", "BOLT:10"))
        self.assertEqual((o["lines"][0]["unit_price"], o["total"]), ("0.2500", "2.50"))
        self.ok("price", "set", "STANDARD", "FLOUR", "1.40", "--min-qty", "10.5")
        self.assertEqual(self.ok("so", "confirm", self.order("Shop", "WH1", "FLOUR:10.5"))["lines"][0]["unit_price"], "1.4000")
        self.assertEqual(self.ok("so", "confirm", self.order("Shop", "WH1", "FLOUR:1.499"))["lines"][0]["unit_price"], "1.5000")

    def test_promotions(self):
        self.receive("BOLT", 300, "WH1/A-01", "0.10")
        self.ok("promo", "add", "SPRING", "--sku", "BOLT", "--percent", "10", "--from", "2026-03-01", "--to", "2026-03-31")
        self.ok("promo", "add", "BIG", "--sku", "BOLT", "--percent", "12.5", "--from", "2026-03-05", "--to", "2026-03-05")
        self.ok("promo", "add", "OLD", "--sku", "BOLT", "--percent", "50", "--from", "2026-01-01", "--to", "2026-02-28")
        self.ok("promo", "add", "ORD5", "--order", "--threshold", "20.00", "--percent", "5", "--from", "2026-03-01", "--to", "2026-03-31")
        self.err("promo", "add", "ORD5", "--order", "--threshold", "1", "--percent", "5", "--from", "2026-03-01", "--to", "2026-03-31")
        self.err("promo", "add", "BAD", "--sku", "BOLT", "--percent", "0", "--from", "2026-03-01", "--to", "2026-03-31")
        self.err("promo", "add", "BAD", "--sku", "BOLT", "--percent", "5", "--from", "2026-03-31", "--to", "2026-03-01")
        self.assertEqual(self.ok("promo", "list")[2], {"code": "ORD5", "kind": "order", "sku": None, "threshold": "20.00",
                                                       "percent": "5.00", "from": "2026-03-01", "to": "2026-03-31"})
        so = self.order("Shop", "WH1", "BOLT:100")
        o = self.ok("so", "confirm", so)
        self.assertEqual((o["lines"][0]["gross"], o["lines"][0]["discount"], o["lines"][0]["net"]), ("25.00", "3.13", "21.87"))
        self.assertEqual((o["subtotal"], o["order_discount"], o["total"]), ("21.87", "1.09", "20.78"))
        o = self.ok("so", "confirm", self.order("Shop", "WH1", "BOLT:10"), now=at(6))
        self.assertEqual((o["lines"][0]["discount"], o["order_discount"], o["total"]), ("0.25", "0.00", "2.25"))
        self.ok("promo", "add", "HUGE", "--sku", "BOLT", "--percent", "90", "--from", "2026-03-01", "--to", "2026-03-31")
        self.assertEqual(self.ok("so", "allocate", so)["total"], "20.78")

    def test_no_price(self):
        self.ok("product", "add", "NUTS", "--name", "Nuts")
        self.receive("NUTS", 5, "WH1/A-01", "1")
        so = self.order("Shop", "WH1", "NUTS:1")
        self.err("so", "confirm", so)
        self.assertEqual(self.ok("so", "show", so)["status"], "draft")


class T1Reservations(World):
    def test_reserve_by_location(self):
        for loc in ("WH1/A-02", "WH1/A-01", "WH1/B-01", "WH1/RECV"):
            self.receive("BOLT", 30 if loc != "WH1/RECV" else 10, loc, "0.10", now=at(2))
        o = self.ok("so", "confirm", self.order("Shop", "WH1", "BOLT:50"))
        self.assertEqual((o["status"], o["hold"], o["expires"], o["lines"][0]["reserved"]), ("confirmed", 48, "2026-03-07T10:00:00Z", "50"))
        rows = self.stock_rows()
        self.assertEqual([(rows[(loc, "BOLT", None)]["reserved"], rows[(loc, "BOLT", None)]["available"])
                          for loc in ("WH1/A-01", "WH1/A-02", "WH1/B-01", "WH1/RECV")],
                         [("30", "0"), ("20", "10"), ("0", "30"), ("0", "10")])

    def test_backorder_and_allocate(self):
        self.receive("BOLT", 20, "WH1/A-01", "0.10")
        so = self.order("Shop", "WH1", "BOLT:50")
        o = self.ok("so", "confirm", so)
        self.assertEqual((o["status"], o["lines"][0]["reserved"]), ("backordered", "20"))
        self.assertEqual(self.ok("available", "BOLT", "--warehouse", "WH1"),
                         {"sku": "BOLT", "warehouse": "WH1", "available": "0", "incoming": "0", "backordered": "30"})
        self.receive("BOLT", 40, "WH1/A-02", "0.10")
        o = self.ok("so", "allocate", so, now=at(6))
        self.assertEqual((o["status"], o["lines"][0]["reserved"], o["expires"]), ("confirmed", "50", "2026-03-08T09:00:00Z"))
        self.assertEqual(self.ok("available", "BOLT", "--warehouse", "WH1", now=at(6))["available"], "10")

    def test_lots_first_expiry_first(self):
        self.receive("MILK", 10, "WH1/A-01", "0.50", "--lot", "L2", "--expires", "2026-04-10")
        self.receive("MILK", 10, "WH1/A-02", "0.50", "--lot", "L1", "--expires", "2026-03-20")
        self.receive("MILK", 10, "WH1/B-01", "0.50", "--lot", "L0", "--expires", "2026-03-04")
        so = self.order("Shop", "WH1", "MILK:15")
        self.ok("so", "confirm", so)
        self.assertEqual(self.ok("so", "pick", so, user="bob")["picks"], [
            {"sku": "MILK", "from": "WH1/A-01", "lot": "L2", "serials": [], "qty": "5"},
            {"sku": "MILK", "from": "WH1/A-02", "lot": "L1", "serials": [], "qty": "10"}])

    def test_serials_by_location_then_serial(self):
        self.receive("PHONE", 2, "WH1/A-02", "100", "--serial", "P3,P1")
        self.receive("PHONE", 1, "WH1/A-01", "100", "--serial", "P2")
        so = self.order("Shop", "WH1", "PHONE:2")
        self.ok("so", "confirm", so)
        self.assertEqual(self.ok("so", "pick", so)["picks"], [
            {"sku": "PHONE", "from": "WH1/A-01", "lot": None, "serials": ["P2"], "qty": "1"},
            {"sku": "PHONE", "from": "WH1/A-02", "lot": None, "serials": ["P1"], "qty": "1"}])
        self.assertEqual(self.stock_rows()[("WH1/SHIP", "PHONE", None)]["serials"], ["P1", "P2"])


class T1Transfers(World):
    def test_transfer_flow(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00")
        t = self.ok("transfer", "create", "BOLT", "4", "--from", "WH1/A-01", "--to", "WH2/S-01", user="bob")
        self.assertEqual(t, {"id": "TR-0001", "sku": "BOLT", "qty": "4", "from": "WH1/A-01", "to": "WH2/S-01",
                             "lot": None, "serials": [], "status": "in_transit", "value": "4.00"})
        v = self.ok("valuation")
        self.assertEqual(v, {"rows": [{"sku": "BOLT", "warehouse": "WH1", "qty": "6", "value": "6.00"}],
                             "in_transit": [{"transfer": "TR-0001", "sku": "BOLT", "qty": "4", "value": "4.00"}], "total": "10.00"})
        self.assertEqual(self.ok("transfer", "receive", "TR-0001", user="bob")["status"], "received")
        self.assertEqual(self.val_rows()[0], {("BOLT", "WH1"): ("6", "6.00"), ("BOLT", "WH2"): ("4", "4.00")})
        self.assertEqual(self.stock_rows("--warehouse", "WH2")[("WH2/S-01", "BOLT", None)]["on_hand"], "4")
        self.receive("BOLT", 5, "WH1/RECV", "1.00")
        self.err("transfer", "create", "BOLT", "1", "--from", "WH1/RECV", "--to", "WH2/S-01")
        self.err("transfer", "create", "BOLT", "1", "--from", "WH1/A-01", "--to", "WH1/A-02")
        self.err("transfer", "receive", "TR-0001")
        self.assertEqual([t["id"] for t in self.ok("transfer", "list", "--status", "received")], ["TR-0001"])


class T1Returns(World):
    def test_good_and_damaged(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00", now=at(2))
        self.receive("BOLT", 10, "WH1/A-01", "2.00", now=at(3))
        so = self.order("Shop", "WH1", "BOLT:15")
        self.ok("so", "confirm", so)
        self.ok("so", "pick", so)
        o = self.ok("so", "ship", so)
        self.assertEqual((o["status"], o["lines"][0]["shipped"]), ("shipped", "15"))
        self.assertEqual(self.ok("movement", "list", "--type", "ship")[0]["value"], "20.00")
        r = self.ok("return", "create", so, "--line", "1", "--qty", "3", "--condition", "good", "--to", "WH1/A-02")
        self.assertEqual(r, {"id": "RT-0001", "order": so, "line": 1, "sku": "BOLT", "qty": "3", "condition": "good",
                             "to": "WH1/A-02", "lot": None, "serials": [], "unit_cost": "1.3333", "value": "4.00", "credit": "0.75"})
        r = self.ok("return", "create", so, "--line", "1", "--qty", "2", "--condition", "damaged")
        self.assertEqual((r["to"], r["value"], r["credit"]), (None, "0.00", "0.50"))
        self.err("return", "create", so, "--line", "1", "--qty", "11", "--condition", "damaged")
        self.err("return", "create", so, "--line", "1", "--qty", "1", "--condition", "good")
        self.assertEqual(self.ok("so", "show", so)["lines"][0]["returned"], "5")
        self.assertEqual(self.stock_rows()[("WH1/A-02", "BOLT", None)]["on_hand"], "3")
        self.assertEqual([r["id"] for r in self.ok("return", "list", "--order", so)], ["RT-0001", "RT-0002"])


class T1Reorder(World):
    def test_reorder(self):
        self.receive("BOLT", 30, "WH1/A-01", "0.10")
        self.ok("po", "create", "--supplier", "Acme", "--warehouse", "WH1", "--line", "BOLT:40:0.10")
        self.ok("so", "confirm", self.order("Shop", "WH1", "BOLT:50"))
        self.assertEqual(self.ok("reorder", "--warehouse", "WH1"), [{
            "sku": "BOLT", "available": "0", "incoming": "40", "backordered": "20", "projected": "20",
            "min": "50", "max": "200", "suggest": "180"}])
        self.assertEqual(self.ok("reorder", "--warehouse", "WH2"), [{
            "sku": "BOLT", "available": "0", "incoming": "0", "backordered": "0", "projected": "0",
            "min": "50", "max": "200", "suggest": "200"}])


class T1Import(World):
    def write(self, text):
        path = os.path.join(self.tmp.name, "p.csv")
        with open(path, "w") as f:
            f.write(text)
        return path

    def test_import(self):
        good = self.write("sku,name,unit,tracking,costing,min,max\nNUTS,Nuts M8,,,,10,\nSUGAR,Sugar,kg,lot,average,,\n")
        self.assertEqual(self.ok("import", "products", good), {"imported": 2})
        self.assertEqual(self.ok("product", "show", "SUGAR"), {"sku": "SUGAR", "name": "Sugar", "unit": "kg", "tracking": "lot",
                                                               "costing": "average", "min": None, "max": None, "version": 1})
        self.assertEqual(self.ok("product", "show", "NUTS")["min"], "10")
        bad = self.write("sku,name,unit,tracking,costing,min,max\nOATS,Oats,kg,,,,\nx,Bad,,,,,\nOATS,Again,,,,,\nBOLT,Dup,,,,,\n")
        r = self.err("import", "products", bad)
        for n in (3, 4, 5):
            self.assertIn(f"row {n}", r.stderr)
        self.assertNotIn("row 2", r.stderr)
        self.err("product", "show", "OATS")
        self.err("import", "products", self.write("sku,name\nRICE,Rice\n"))
        self.err("import", "products", bad, user="bob")


class T1Audit(World):
    def test_audit(self):
        self.assertEqual(self.ok("audit", "list")[0], {"seq": 1, "at": T0, "user": "alice", "action": "init", "target": "EUR"})
        self.assertEqual([a["target"] for a in self.ok("audit", "list", "--action", "user.add")], ["bob", "carol", "vic"])
        m = self.receive("BOLT", 5, "WH1/A-01", "1", user="bob")
        last = self.ok("audit", "list")[-1]
        self.assertEqual((last["user"], last["action"], last["target"], last["at"]), ("bob", "receive", str(m["id"]), NOW))
        n = len(self.ok("audit", "list"))
        self.err("scrap", "BOLT", "50", "--at", "WH1/A-01", "--reason", "x")
        self.assertEqual(len(self.ok("audit", "list")), n)
        self.assertEqual([a["action"] for a in self.ok("audit", "list", "--user", "bob")], ["receive"])


# ===================================================================== T2: features combined

class T2Costing(World):
    def test_transferred_layers_keep_their_age(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00", now="2026-01-01T10:00:00Z")
        self.receive("BOLT", 10, "WH2/S-01", "2.00", now="2026-02-01T10:00:00Z")
        self.assertEqual(self.ok("transfer", "create", "BOLT", "5", "--from", "WH1/A-01", "--to", "WH2/S-01", now=at(2))["value"], "5.00")
        self.ok("transfer", "receive", "TR-0001", now=at(3))
        self.assertEqual(self.ok("scrap", "BOLT", "6", "--at", "WH2/S-01", "--reason", "x", now=at(4))["value"], "7.00")
        self.assertEqual(self.ok("aging", "--warehouse", "WH2", "--at", "2026-03-10"),
                         [{"sku": "BOLT", "0-30": "0.00", "31-90": "18.00", "91+": "0.00"}])

    def test_cancelled_transfer_goes_back_into_its_layers(self):
        self.receive("BOLT", 5, "WH1/A-01", "1.00", now=at(2))
        self.receive("BOLT", 5, "WH1/A-01", "3.00", now=at(3))
        self.assertEqual(self.ok("transfer", "create", "BOLT", "6", "--from", "WH1/A-01", "--to", "WH2/S-01")["value"], "8.00")
        self.assertEqual(self.ok("transfer", "cancel", "TR-0001", user="carol")["status"], "cancelled")
        self.assertEqual(self.ok("scrap", "BOLT", "2", "--at", "WH1/A-01", "--reason", "x")["value"], "2.00")
        self.assertEqual(self.val_rows()[0], {("BOLT", "WH1"): ("8", "18.00")})
        self.err("transfer", "receive", "TR-0001")

    def test_average_across_warehouses(self):
        self.receive("FLOUR", 10, "WH1/A-01", "1.00")
        self.receive("FLOUR", 10, "WH1/A-01", "2.00")
        self.assertEqual(self.ok("transfer", "create", "FLOUR", "4", "--from", "WH1/A-01", "--to", "WH2/S-01")["value"], "6.00")
        self.ok("transfer", "receive", "TR-0001")
        self.receive("FLOUR", 4, "WH2/S-01", "3.00")
        self.assertEqual(self.ok("scrap", "FLOUR", "1", "--at", "WH2/S-01", "--reason", "x")["value"], "2.25")
        self.assertEqual(self.val_rows()[0], {("FLOUR", "WH1"): ("16.000", "24.00"), ("FLOUR", "WH2"): ("7.000", "15.75")})

    def test_kg_rounding_half_up(self):
        self.receive("FLOUR", "0.333", "WH1/A-01", "1.0001")
        self.receive("FLOUR", "0.667", "WH1/A-01", "2.9999")
        self.assertEqual(self.val_rows()[0], {("FLOUR", "WH1"): ("1.000", "2.33")})
        so = self.order("Shop", "WH1", "FLOUR:0.5")
        self.assertEqual(self.ok("so", "confirm", so)["lines"][0]["gross"], "0.75")
        self.ok("so", "pick", so)
        self.ok("so", "ship", so)
        ship = self.ok("movement", "list", "--type", "ship")[0]
        self.assertEqual((ship["qty"], ship["value"]), ("0.500", "1.17"))
        self.assertEqual(self.val_rows()[0], {("FLOUR", "WH1"): ("0.500", "1.16")})

    def test_increasing_adjust_costs(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00", now=at(2))
        self.receive("BOLT", 10, "WH1/A-01", "2.00", now=at(3))
        self.ok("scrap", "BOLT", "20", "--at", "WH1/A-01", "--reason", "x")
        self.assertEqual(self.ok("adjust", "BOLT", "--at", "WH1/A-01", "--count", "5", "--reason", "found")["value"], "10.00")
        self.ok("product", "add", "NEWB", "--name", "New")
        self.err("adjust", "NEWB", "--at", "WH1/A-01", "--count", "5", "--reason", "found")

    def test_average_returns(self):
        self.receive("FLOUR", 10, "WH1/A-01", "1.00", now=at(2))
        so = self.order("Shop", "WH1", "FLOUR:4")
        self.ok("so", "confirm", so)
        self.ok("so", "pick", so)
        self.ok("so", "ship", so)
        self.receive("FLOUR", 6, "WH1/A-01", "2.00")
        r = self.ok("return", "create", so, "--line", "1", "--qty", "2", "--condition", "good", "--to", "WH1/A-02")
        self.assertEqual((r["unit_cost"], r["value"], r["credit"]), ("1.0000", "2.00", "3.00"))
        self.assertEqual(self.val_rows()[0], {("FLOUR", "WH1"): ("14.000", "20.00")})


class T2Voids(World):
    def test_void_of_scrap_restores_layers(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00", now=at(2))
        self.receive("BOLT", 10, "WH1/A-01", "2.00", now=at(3))
        s = self.ok("scrap", "BOLT", "12", "--at", "WH1/A-01", "--reason", "x")
        self.assertEqual(s["value"], "14.00")
        v = self.ok("movement", "void", str(s["id"]), "--reason", "found them", user="carol")
        self.assertEqual((v["type"], v["from"], v["to"], v["qty"], v["value"], v["ref"]), ("void", None, "WH1/A-01", "12", "14.00", f"MV-{s['id']}"))
        self.assertEqual(self.ok("scrap", "BOLT", "1", "--at", "WH1/A-01", "--reason", "x")["value"], "1.00")
        self.err("movement", "void", str(s["id"]), "--reason", "again")
        self.err("movement", "void", str(v["id"]), "--reason", "void of void")
        self.err("movement", "void", str(s["id"]), "--reason", "clerk", user="bob")
        self.assertEqual(self.ok("audit", "list", "--action", "movement.void")[0]["target"], str(s["id"]))

    def test_void_receipt_rules(self):
        r1 = self.receive("BOLT", 10, "WH1/A-01", "1.00")
        s = self.ok("scrap", "BOLT", "1", "--at", "WH1/A-01", "--reason", "x")
        self.err("movement", "void", str(r1["id"]), "--reason", "x")
        self.ok("movement", "void", str(s["id"]), "--reason", "x")
        self.ok("movement", "void", str(r1["id"]), "--reason", "x")
        self.assertEqual(self.val_rows()[0], {})
        a = self.receive("FLOUR", 5, "WH1/A-01", "1.00")
        b = self.receive("FLOUR", 5, "WH1/A-01", "3.00")
        self.err("movement", "void", str(a["id"]), "--reason", "x")
        self.ok("movement", "void", str(b["id"]), "--reason", "x")
        self.assertEqual(self.val_rows()[0], {("FLOUR", "WH1"): ("5.000", "5.00")})
        self.assertEqual(self.ok("adjust", "FLOUR", "--at", "WH1/A-01", "--count", "6", "--reason", "x")["value"], "1.00")

    def test_void_respects_reservations(self):
        r = self.receive("BOLT", 10, "WH1/A-01", "1.00")
        self.ok("so", "confirm", self.order("Shop", "WH1", "BOLT:4"))
        self.err("movement", "void", str(r["id"]), "--reason", "x")
        m = self.ok("move", "BOLT", "6", "--from", "WH1/A-01", "--to", "WH1/A-02")
        self.ok("movement", "void", str(m["id"]), "--reason", "x")
        self.assertEqual(self.stock_rows()[("WH1/A-01", "BOLT", None)]["on_hand"], "10")


class T2Orders(World):
    def test_reservations_expire(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.10", now=at(2))
        so = self.order("Shop", "WH1", "BOLT:10", now=at(2, 10))
        o = self.ok("so", "confirm", so, "--hold", "2", now=at(2, 10))
        self.assertEqual(o["expires"], "2026-03-02T12:00:00Z")
        o = self.ok("so", "show", so, now="2026-03-02T11:59:59Z")
        self.assertEqual((o["status"], o["lines"][0]["reserved"]), ("confirmed", "10"))
        self.err("product", "add", "bad sku", "--name", "x", now=at(2, 12))
        o = self.ok("so", "show", so, now=at(2, 12))
        self.assertEqual((o["status"], o["lines"][0]["reserved"], o["expires"]), ("backordered", "0", None))
        self.assertEqual(self.ok("audit", "list", "--action", "reservation.expire", now=at(2, 13)),
                         [{"seq": self.ok("audit", "list", now=at(2, 13))[-1]["seq"], "at": at(2, 12), "user": "system",
                           "action": "reservation.expire", "target": so}])
        self.assertEqual(self.ok("available", "BOLT", "--warehouse", "WH1", now=at(2, 13))["available"], "10")

    def test_partial_shipping_and_status(self):
        self.receive("BOLT", 20, "WH1/A-01", "0.12")
        so = self.order("Shop", "WH1", "BOLT:30")
        self.assertEqual(self.ok("so", "confirm", so)["status"], "backordered")
        self.ok("so", "pick", so)
        self.assertEqual(self.ok("so", "show", so)["status"], "backordered")
        o = self.ok("so", "ship", so, user="bob")
        self.assertEqual((o["status"], o["lines"][0]["shipped"]), ("partially_shipped", "20"))
        self.receive("BOLT", 10, "WH1/A-02", "0.12")
        o = self.ok("so", "allocate", so)
        self.assertEqual((o["status"], o["lines"][0]["reserved"]), ("partially_shipped", "10"))
        self.ok("so", "pick", so)
        o = self.ok("so", "ship", so)
        self.assertEqual((o["status"], o["lines"][0]["shipped"], o["lines"][0]["reserved"], o["lines"][0]["picked"]),
                         ("shipped", "30", "0", "0"))
        self.assertEqual([m["value"] for m in self.ok("movement", "list", "--type", "ship")], ["2.40", "1.20"])
        self.err("so", "allocate", so)
        self.err("so", "cancel", so)

    def test_cancel_releases_and_ship_stock_stays(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.10")
        so = self.order("Shop", "WH1", "BOLT:6")
        self.ok("so", "confirm", so)
        self.ok("so", "pick", so)
        self.assertEqual(self.ok("so", "cancel", so)["status"], "cancelled")
        rows = self.stock_rows()
        self.assertEqual((rows[("WH1/SHIP", "BOLT", None)]["on_hand"], rows[("WH1/SHIP", "BOLT", None)]["reserved"]), ("6", "0"))
        self.ok("move", "BOLT", "6", "--from", "WH1/SHIP", "--to", "WH1/A-01")
        self.err("so", "cancel", so)
        self.err("so", "pick", so)

    def test_reserved_stock_is_untouchable(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.10")
        self.ok("so", "confirm", self.order("Shop", "WH1", "BOLT:8"))
        self.err("move", "BOLT", "3", "--from", "WH1/A-01", "--to", "WH1/A-02")
        self.ok("move", "BOLT", "2", "--from", "WH1/A-01", "--to", "WH1/A-02")
        self.err("adjust", "BOLT", "--at", "WH1/A-01", "--count", "7", "--reason", "x")
        self.err("scrap", "BOLT", "1", "--at", "WH1/A-01", "--reason", "x")
        self.err("transfer", "create", "BOLT", "1", "--from", "WH1/A-01", "--to", "WH2/S-01")
        self.ok("adjust", "BOLT", "--at", "WH1/A-01", "--count", "9", "--reason", "found one")

    def test_competing_orders(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.10")
        so1 = self.order("Shop", "WH1", "BOLT:8")
        so2 = self.order("Bistro", "WH1", "BOLT:5")
        self.ok("so", "confirm", so1)
        o = self.ok("so", "confirm", so2)
        self.assertEqual((o["status"], o["lines"][0]["reserved"]), ("backordered", "2"))
        self.assertEqual(self.ok("available", "BOLT", "--warehouse", "WH1")["backordered"], "3")
        self.ok("so", "cancel", so1)
        self.assertEqual(self.ok("available", "BOLT", "--warehouse", "WH1")["available"], "8")
        self.assertEqual(self.ok("so", "allocate", so2)["status"], "confirmed")
        self.assertEqual(self.ok("available", "BOLT", "--warehouse", "WH1"),
                         {"sku": "BOLT", "warehouse": "WH1", "available": "5", "incoming": "0", "backordered": "0"})
        self.assertEqual([o["id"] for o in self.ok("so", "list", "--status", "cancelled")], [so1])

    def test_two_lines_same_sku(self):
        self.receive("BOLT", 5, "WH1/A-01", "1.00", now=at(2))
        self.receive("BOLT", 5, "WH1/A-02", "2.00", now=at(3))
        so = self.order("Shop", "WH1", "BOLT:3", "BOLT:4")
        o = self.ok("so", "confirm", so)
        self.assertEqual([x["reserved"] for x in o["lines"]], ["3", "4"])
        picks = self.ok("so", "pick", so)["picks"]
        self.assertEqual([(p["from"], p["qty"]) for p in picks], [("WH1/A-01", "5"), ("WH1/A-02", "2")])
        self.ok("so", "ship", so)
        ships = self.ok("movement", "list", "--type", "ship")
        self.assertEqual([(m["qty"], m["value"]) for m in ships], [("3", "3.00"), ("4", "6.00")])


class T2Tracking(World):
    def test_lot_flow(self):
        self.receive("MILK", 6, "WH1/A-02", "0.60", "--lot", "L2", "--expires", "2026-04-30", now=at(2))
        self.receive("MILK", 6, "WH1/A-01", "0.50", "--lot", "L1", "--expires", "2026-03-20", now=at(3))
        so = self.order("Shop", "WH1", "MILK:8")
        self.ok("so", "confirm", so)
        self.assertEqual([(p["from"], p["lot"], p["qty"]) for p in self.ok("so", "pick", so)["picks"]],
                         [("WH1/A-01", "L1", "6"), ("WH1/A-02", "L2", "2")])
        self.ok("so", "ship", so)
        ships = self.ok("movement", "list", "--type", "ship")
        self.assertEqual([(m["lot"], m["qty"], m["value"]) for m in ships], [("L1", "6", "3.60"), ("L2", "2", "1.00")])
        self.err("return", "create", so, "--line", "1", "--qty", "1", "--condition", "good", "--to", "WH1/A-01", "--lot", "L9")
        r = self.ok("return", "create", so, "--line", "1", "--qty", "2", "--condition", "good", "--to", "WH1/A-01", "--lot", "L2")
        self.assertEqual((r["unit_cost"], r["value"]), ("0.5750", "1.15"))
        self.assertEqual(self.val_rows()[0], {("MILK", "WH1"): ("6", "3.15")})
        rows = self.stock_rows()
        self.assertEqual((rows[("WH1/A-01", "MILK", "L2")]["on_hand"], rows[("WH1/A-02", "MILK", "L2")]["on_hand"]), ("2", "4"))

    def test_serial_flow(self):
        self.receive("PHONE", 3, "WH1/A-01", "100", "--serial", "P1,P2,P3")
        so = self.order("Shop", "WH1", "PHONE:2")
        self.assertEqual(self.ok("so", "confirm", so)["lines"][0]["gross"], "598.00")
        self.ok("so", "pick", so)
        self.ok("so", "ship", so)
        ship = self.ok("movement", "list", "--type", "ship")[0]
        self.assertEqual((ship["serials"], ship["value"]), (["P1", "P2"], "200.00"))
        self.err("return", "create", so, "--line", "1", "--qty", "1", "--condition", "good", "--to", "WH1/A-02", "--serial", "P3")
        self.assertEqual(self.ok("return", "create", so, "--line", "1", "--qty", "1", "--condition", "good", "--to",
                                 "WH1/A-02", "--serial", "P1")["value"], "100.00")
        self.err("return", "create", so, "--line", "1", "--qty", "1", "--condition", "damaged", "--serial", "P1")
        self.err("receive", "PHONE", "1", "--at", "WH1/A-01", "--cost", "100", "--serial", "P1")
        self.assertEqual(self.stock_rows()[("WH1/A-02", "PHONE", None)]["serials"], ["P1"])

    def test_lots_and_serials_through_po_and_transfer(self):
        self.ok("po", "create", "--supplier", "Dairy", "--warehouse", "WH1", "--line", "MILK:10:0.50", "--line", "PHONE:2:100")
        self.ok("po", "receive", "PO-0001", "--line", "1", "--qty", "10", "--at", "WH1/A-01", "--lot", "L1", "--expires", "2026-03-20")
        self.ok("po", "receive", "PO-0001", "--line", "2", "--qty", "2", "--at", "WH1/A-01", "--serial", "P1,P2")
        self.err("po", "receive", "PO-0001", "--line", "2", "--qty", "1", "--at", "WH1/A-01", "--serial", "P3")
        self.ok("transfer", "create", "MILK", "4", "--from", "WH1/A-01", "--to", "WH2/S-01", "--lot", "L1")
        self.ok("transfer", "create", "PHONE", "1", "--from", "WH1/A-01", "--to", "WH2/S-01", "--serial", "P2")
        self.ok("transfer", "receive", "TR-0001")
        self.ok("transfer", "receive", "TR-0002")
        so = self.order("Shop", "WH2", "MILK:2", "PHONE:1")
        self.assertEqual(self.ok("so", "confirm", so)["status"], "confirmed")
        rows = self.stock_rows("--warehouse", "WH2")
        self.assertEqual((rows[("WH2/S-01", "MILK", "L1")]["reserved"], rows[("WH2/S-01", "PHONE", None)]["serials"]), ("2", ["P2"]))
        self.err("receive", "MILK", "1", "--at", "WH2/S-01", "--cost", "1", "--lot", "L1", "--expires", "2026-03-21")


class T2Reports(World):
    def test_stock_at(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.10", now=at(2))
        self.ok("move", "BOLT", "4", "--from", "WH1/A-01", "--to", "WH1/A-02", now=at(3))
        self.ok("scrap", "BOLT", "1", "--at", "WH1/A-02", "--reason", "x", now=at(4))
        self.assertEqual(self.ok("stock", "--at", at(2, 12)), [{"sku": "BOLT", "location": "WH1/A-01", "lot": None, "serials": [], "on_hand": "10"}])
        self.assertEqual([(r["location"], r["on_hand"]) for r in self.ok("stock", "--at", at(3, 12))], [("WH1/A-01", "6"), ("WH1/A-02", "4")])
        self.assertEqual([(r["location"], r["on_hand"]) for r in self.ok("stock")], [("WH1/A-01", "6"), ("WH1/A-02", "3")])

    def test_valuation_with_transit_at(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00", now=at(2))
        self.ok("transfer", "create", "BOLT", "4", "--from", "WH1/A-01", "--to", "WH2/S-01", now=at(3))
        self.ok("transfer", "receive", "TR-0001", now=at(4))
        v = self.ok("valuation", "--at", at(3, 12))
        self.assertEqual((v["in_transit"], v["total"]), ([{"transfer": "TR-0001", "sku": "BOLT", "qty": "4", "value": "4.00"}], "10.00"))
        v = self.ok("valuation", "--warehouse", "WH2", "--at", at(3, 12))
        self.assertEqual((v["rows"], v["total"]), ([], "4.00"))
        v = self.ok("valuation", "--warehouse", "WH2")
        self.assertEqual((v["rows"], v["in_transit"], v["total"]), ([{"sku": "BOLT", "warehouse": "WH2", "qty": "4", "value": "4.00"}], [], "4.00"))

    def test_reorder_negative_projection(self):
        self.ok("product", "edit", "FLOUR", "--version", "1", "--min", "5")
        self.ok("so", "confirm", self.order("Shop", "WH1", "FLOUR:8"))
        self.assertEqual(self.ok("reorder", "--warehouse", "WH1")[1], {
            "sku": "FLOUR", "available": "0.000", "incoming": "0.000", "backordered": "8.000", "projected": "-8.000",
            "min": "5.000", "max": None, "suggest": "13.000"})


# ===================================================================== T3: robustness

class T3Atomicity(World):
    def snapshot(self):
        return [self.ok(*c) for c in (("audit", "list"), ("movement", "list"), ("stock",), ("so", "list"), ("po", "list"),
                                      ("transfer", "list"))]

    def test_failed_commands_change_nothing(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00")
        self.ok("po", "create", "--supplier", "Acme", "--warehouse", "WH1", "--line", "BOLT:10:1.00")
        so = self.order("Shop", "WH1", "BOLT:4", "PHONE:1")
        before = self.snapshot()
        self.err("so", "confirm", so, "--hold", "721")
        self.err("so", "pick", so)
        self.err("po", "receive", "PO-0001", "--line", "1", "--qty", "11", "--at", "WH1/RECV")
        self.err("scrap", "BOLT", "11", "--at", "WH1/A-01", "--reason", "x")
        self.err("transfer", "create", "BOLT", "11", "--from", "WH1/A-01", "--to", "WH2/S-01")
        self.err("movement", "void", "99", "--reason", "x")
        self.err("receive", "PHONE", "2", "--at", "WH1/A-01", "--cost", "1", "--serial", "Q1,Q2,Q3")
        self.assertEqual(self.snapshot(), before)

    def test_confirm_without_any_price_reserves_nothing(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00")
        self.ok("product", "add", "NUTS", "--name", "Nuts")
        so = self.order("Shop", "WH1", "BOLT:4", "NUTS:1")
        self.err("so", "confirm", so)
        self.assertEqual(self.stock_rows()[("WH1/A-01", "BOLT", None)]["reserved"], "0")
        self.assertEqual(self.ok("so", "show", so)["lines"][0]["unit_price"], None)


class T3Permissions(World):
    def test_viewer_and_clerk(self):
        self.receive("BOLT", 10, "WH1/A-01", "1.00")
        for args in (("product", "list"), ("stock",), ("valuation",), ("audit", "list"), ("movement", "list"),
                     ("available", "BOLT", "--warehouse", "WH1"), ("reorder", "--warehouse", "WH1")):
            self.ok(*args, user="vic")
        self.err("so", "create", "--customer", "Shop", "--warehouse", "WH1", "--line", "BOLT:1", user="vic")
        self.err("move", "BOLT", "1", "--from", "WH1/A-01", "--to", "WH1/A-02", user="vic")
        self.ok("move", "BOLT", "1", "--from", "WH1/A-01", "--to", "WH1/A-02", user="bob")
        self.ok("transfer", "create", "BOLT", "1", "--from", "WH1/A-01", "--to", "WH2/S-01", user="bob")
        self.err("transfer", "cancel", "TR-0001", user="bob")
        self.err("so", "create", "--customer", "Shop", "--warehouse", "WH1", "--line", "BOLT:1", user="bob")
        self.err("price", "set", "STANDARD", "BOLT", "1", user="bob")
        self.err("user", "add", "zed", "--role", "viewer", user="carol")
        so = self.order("Shop", "WH1", "BOLT:2")
        self.err("so", "confirm", so, user="bob")
        self.ok("so", "confirm", so, user="carol")
        self.ok("so", "pick", so, user="bob")
        self.ok("so", "ship", so, user="bob")
        self.err("return", "create", so, "--line", "1", "--qty", "1", "--condition", "damaged", user="bob")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Api(World):
    def setUp(self):
        super().setUp()
        self.port = free_port()
        self.proc = subprocess.Popen([sys.executable, "-m", "wms", "--db", self.db, "serve", "--port", str(self.port)],
                                     cwd=APP, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            self.proc.kill()
            self.fail("the server didn't start")

    def tearDown(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        super().tearDown()

    def http(self, method, path, body=None, user="alice", now=NOW, headers=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if user:
            req.add_header("X-User", user)
        if now:
            req.add_header("X-Now", now)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read() or b"null"), dict(r.headers)
        except urllib.error.HTTPError as e:
            text = e.read()
            e.close()
            try:
                payload = json.loads(text or b"null")
            except ValueError:
                payload = text.decode(errors="replace")
            return e.code, payload, dict(e.headers)


class T3Http(Api):
    def test_products_paging_and_auth(self):
        st, b, _ = self.http("GET", "/products?limit=2")
        self.assertEqual((st, [p["sku"] for p in b["items"]], b["next"]), (200, ["BOLT", "FLOUR"], "FLOUR"))
        st, b, _ = self.http("GET", "/products?limit=2&after=FLOUR")
        self.assertEqual(([p["sku"] for p in b["items"]], b["next"]), (["MILK", "PHONE"], None))
        self.assertEqual([p["sku"] for p in self.http("GET", "/products?search=ph")[1]["items"]], ["PHONE"])
        self.assertEqual(self.http("GET", "/products", user=None)[0], 401)
        self.assertEqual(self.http("GET", "/products", user="ghost")[0], 401)
        st, b, _ = self.http("POST", "/receipts", {"sku": "BOLT", "qty": "1", "at": "WH1/A-01", "cost": "1"}, user="vic")
        self.assertEqual(st, 403)
        self.assertIn("error", b)
        self.assertEqual(self.http("GET", "/products/NOPE")[0], 404)
        self.assertEqual(self.http("GET", "/nowhere")[0], 404)

    def test_etags(self):
        st, b, h = self.http("GET", "/products/BOLT")
        self.assertEqual((st, b["version"], h.get("ETag")), (200, 1, '"1"'))
        self.assertEqual(self.http("PATCH", "/products/BOLT", {"name": "Bolt"})[0], 428)
        self.assertEqual(self.http("PATCH", "/products/BOLT", {"name": "Bolt"}, headers={"If-Match": '"2"'})[0], 412)
        self.assertEqual(self.http("PATCH", "/products/BOLT", {"min": 5}, headers={"If-Match": '"1"'})[0], 400)
        st, b, h = self.http("PATCH", "/products/BOLT", {"name": "Bolt", "max": None}, headers={"If-Match": '"1"'})
        self.assertEqual((st, b["name"], b["max"], b["version"], h.get("ETag")), (200, "Bolt", None, 2, '"2"'))
        self.assertEqual(self.ok("product", "show", "BOLT")["version"], 2)

    def test_receipts_and_orders(self):
        st, m, _ = self.http("POST", "/receipts", {"sku": "BOLT", "qty": "10", "at": "WH1/A-01", "cost": "0.12"}, user="bob")
        self.assertEqual((st, m["type"], m["value"], m["user"], m["at"]), (201, "receive", "1.20", "bob", NOW))
        self.assertEqual(self.http("POST", "/receipts", {"sku": "BOLT", "qty": 10, "at": "WH1/A-01", "cost": "0.12"})[0], 400)
        st, o, _ = self.http("POST", "/sales-orders", {"customer": "Shop", "warehouse": "WH1", "lines": [{"sku": "BOLT", "qty": "4"}]}, user="carol")
        self.assertEqual((st, o["id"], o["status"]), (201, "SO-0001", "draft"))
        st, o, _ = self.http("POST", "/sales-orders/SO-0001/confirm", {"hold": 24}, user="carol")
        self.assertEqual((st, o["status"], o["lines"][0]["reserved"], o["expires"]), (200, "confirmed", "4", "2026-03-06T10:00:00Z"))
        self.assertEqual(self.http("GET", "/sales-orders/SO-0001", user="vic")[1]["total"], "1.00")
        rows = self.http("GET", "/stock?warehouse=WH1")[1]
        self.assertEqual([(r["location"], r["on_hand"], r["reserved"]) for r in rows], [("WH1/A-01", "10", "4")])
        self.assertEqual(self.http("GET", "/valuation?warehouse=WH1")[1]["total"], "1.20")
        self.assertEqual(self.ok("so", "show", "SO-0001")["status"], "confirmed")
        self.assertEqual(self.http("GET", "/sales-orders/SO-0001", now="2026-03-06T10:00:00Z")[1]["status"], "backordered")

    def test_failed_request_changes_nothing(self):
        st, _, _ = self.http("POST", "/sales-orders", {"customer": "Shop", "warehouse": "WH1",
                                                       "lines": [{"sku": "BOLT", "qty": "1"}, {"sku": "NOPE", "qty": "1"}]})
        self.assertIn(st, (400, 404))
        self.assertEqual(self.http("GET", "/sales-orders/SO-0001")[0], 404)
        self.assertEqual(self.ok("so", "list"), [])
        self.ok("user", "disable", "vic")
        self.assertEqual(self.http("GET", "/products", user="vic")[0], 401)

    def test_idempotency(self):
        body = {"sku": "BOLT", "qty": "5", "at": "WH1/A-01", "cost": "1"}
        a = self.http("POST", "/receipts", body, headers={"Idempotency-Key": "k1"})
        b = self.http("POST", "/receipts", body, headers={"Idempotency-Key": "k1"})
        self.assertEqual((a[0], a[1]), (b[0], b[1]))
        self.assertEqual(len(self.ok("movement", "list")), 1)
        self.assertEqual(self.http("POST", "/receipts", dict(body, qty="6"), headers={"Idempotency-Key": "k1"})[0], 409)
        self.assertEqual(self.http("POST", "/sales-orders", {"customer": "Shop", "warehouse": "WH1", "lines": []},
                                   headers={"Idempotency-Key": "k1"})[0], 409)
        bad = dict(body, qty="0")
        self.assertEqual(self.http("POST", "/receipts", bad, headers={"Idempotency-Key": "k2"})[0], 400)
        self.assertEqual(self.http("POST", "/receipts", bad, headers={"Idempotency-Key": "k2"})[0], 400)
        self.assertEqual(len(self.ok("movement", "list")), 1)


class T3Concurrency(Api):
    def test_parallel_confirms_never_oversell(self):
        self.receive("BOLT", 7, "WH1/A-01", "1.00")
        orders = [self.order("Shop", "WH1", "BOLT:1") for _ in range(16)]
        results = {}

        def confirm(so):
            results[so] = self.http("POST", f"/sales-orders/{so}/confirm", {}, user="carol")

        threads = [threading.Thread(target=confirm, args=(so,)) for so in orders]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertTrue(all(r[0] == 200 for r in results.values()), {k: v[0] for k, v in results.items()})
        statuses = sorted(r[1]["status"] for r in results.values())
        self.assertEqual(statuses.count("confirmed"), 7)
        self.assertEqual(statuses.count("backordered"), 9)
        row = self.stock_rows()[("WH1/A-01", "BOLT", None)]
        self.assertEqual((row["on_hand"], row["reserved"], row["available"]), ("7", "7", "0"))

    def test_parallel_requests_with_one_key(self):
        body = {"sku": "BOLT", "qty": "3", "at": "WH1/A-01", "cost": "1"}
        results = []

        def post():
            results.append(self.http("POST", "/receipts", body, headers={"Idempotency-Key": "same"}))

        threads = [threading.Thread(target=post) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual({r[0] for r in results}, {201})
        self.assertEqual(len({r[1]["id"] for r in results}), 1)
        self.assertEqual(self.stock_rows()[("WH1/A-01", "BOLT", None)]["on_hand"], "3")


if __name__ == "__main__":
    unittest.main()
