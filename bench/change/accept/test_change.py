"""Hidden acceptance tests for the change benchmark. Never shown to the model under test.

Run against an app: APP_DIR=/path/to/repo python3 -m unittest discover -s bench/change/accept
T1 the reported bug, T2 archiving products, T3 archiving across the other commands and the HTTP
API. test_regress.py adds the warehouse benchmark's tests. All pass against bench/change/reference."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "warehouse", "accept"))
from test_wms import Api, World, at  # noqa: E402


class T1AtCutoff(World):
    def test_valuation_at_includes_movements_at_that_time(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.50", now=at(2, 9, 0))
        self.receive("BOLT", 5, "WH1/A-01", "0.60", now=at(3, 9, 0))
        rows, v = self.val_rows("--at", at(2, 9, 0))
        self.assertEqual(rows[("BOLT", "WH1")], ("10", "5.00"))
        self.assertEqual(v["total"], "5.00")
        rows, _ = self.val_rows("--at", at(3, 9, 0))
        self.assertEqual(rows[("BOLT", "WH1")], ("15", "8.00"))

    def test_stock_at_includes_movements_at_that_time(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.50", now=at(2, 9, 0))
        self.ok("move", "BOLT", "4", "--from", "WH1/A-01", "--to", "WH1/A-02", now=at(4, 12, 0))
        rows = self.stock_rows("--at", at(4, 12, 0))
        self.assertEqual((rows[("WH1/A-01", "BOLT", None)]["on_hand"], rows[("WH1/A-02", "BOLT", None)]["on_hand"]), ("6", "4"))
        rows = self.stock_rows("--at", at(4, 11, 59))
        self.assertEqual(rows[("WH1/A-01", "BOLT", None)]["on_hand"], "10")

    def test_before_the_first_movement_is_empty(self):
        self.receive("BOLT", 10, "WH1/A-01", "0.50", now=at(2, 9, 0))
        rows, v = self.val_rows("--at", at(2, 8, 59))
        self.assertEqual((rows, v["total"]), ({}, "0.00"))


class Archive(World):
    def archive(self, sku, **kw):
        return self.ok("product", "archive", sku, **kw)


class T2Archive(Archive):
    def test_archive_and_unarchive(self):
        p = self.archive("BOLT", user="carol")
        self.assertEqual((p["archived"], p["version"]), (True, 2))
        self.assertTrue(self.ok("product", "show", "BOLT")["archived"])
        p = self.ok("product", "unarchive", "BOLT", user="carol")
        self.assertNotIn("archived", p)
        self.assertEqual(p["version"], 3)
        self.assertNotIn("archived", self.ok("product", "show", "BOLT"))

    def test_list_hides_archived(self):
        self.archive("FLOUR")
        self.assertEqual([p["sku"] for p in self.ok("product", "list")], ["BOLT", "MILK", "PHONE"])
        listed = self.ok("product", "list", "--archived")
        self.assertEqual([p["sku"] for p in listed], ["FLOUR"])
        self.assertEqual(self.ok("product", "list", "--archived", "--search", "bolt"), [])

    def test_permissions_and_state_errors(self):
        self.err("product", "archive", "BOLT", user="bob")
        self.err("product", "archive", "NOPE")
        self.err("product", "unarchive", "BOLT")
        self.archive("BOLT")
        self.err("product", "archive", "BOLT")
        self.err("product", "unarchive", "BOLT", user="vic")

    def test_blocked_by_stock_anywhere(self):
        self.receive("BOLT", 5, "WH1/DOCK", "0.10")
        self.err("product", "archive", "BOLT")
        self.ok("scrap", "BOLT", "5", "--at", "WH1/DOCK", "--reason", "x")
        self.archive("BOLT")

    def test_blocked_by_transfer_in_transit(self):
        self.receive("BOLT", 5, "WH1/A-01", "0.10")
        tr = self.ok("transfer", "create", "BOLT", "5", "--from", "WH1/A-01", "--to", "WH2/S-01")
        self.err("product", "archive", "BOLT")
        self.ok("transfer", "receive", tr["id"])
        self.err("product", "archive", "BOLT")   # now it is stock in WH2
        self.ok("scrap", "BOLT", "5", "--at", "WH2/S-01", "--reason", "x")
        self.archive("BOLT")

    def test_blocked_by_open_orders(self):
        po = self.ok("po", "create", "--supplier", "Acme", "--warehouse", "WH1", "--line", "BOLT:10:1.00")
        self.err("product", "archive", "BOLT")
        self.ok("po", "close", po["id"])
        so = self.order("Shop", "WH1", "FLOUR:2")
        self.err("product", "archive", "FLOUR")
        self.ok("so", "cancel", so)
        self.archive("FLOUR")
        self.archive("BOLT")

    def test_audit(self):
        self.archive("BOLT", user="carol")
        self.ok("product", "unarchive", "BOLT", user="carol")
        got = [(a["action"], a["target"], a["user"]) for a in self.ok("audit", "list")][-2:]
        self.assertEqual(got, [("product.archive", "BOLT", "carol"), ("product.unarchive", "BOLT", "carol")])
        self.assertEqual(len(self.ok("audit", "list", "--action", "product.archive")), 1)


class T3ArchiveRules(Archive):
    def setUp(self):
        super().setUp()
        self.archive("BOLT")

    def test_nothing_new_for_an_archived_product(self):
        self.err("receive", "BOLT", "1", "--at", "WH1/A-01", "--cost", "1")
        self.err("adjust", "BOLT", "--at", "WH1/A-01", "--count", "3", "--reason", "count")
        self.err("po", "create", "--supplier", "Acme", "--warehouse", "WH1", "--line", "BOLT:10:1.00")
        self.err("po", "create", "--supplier", "Acme", "--warehouse", "WH1",
                 "--line", "FLOUR:10:1.00", "--line", "BOLT:10:1.00")
        self.err("so", "create", "--customer", "Shop", "--warehouse", "WH1", "--line", "BOLT:1")
        self.err("price", "set", "STANDARD", "BOLT", "0.30")
        self.err("promo", "add", "P1", "--sku", "BOLT", "--percent", "5", "--from", "2026-03-01", "--to", "2026-03-31")
        self.err("product", "edit", "BOLT", "--version", "2", "--name", "Bolt")
        self.assertEqual(self.ok("po", "list"), [])   # the failed commands changed nothing

    def test_unarchived_product_works_again(self):
        self.ok("product", "unarchive", "BOLT")
        self.receive("BOLT", 3, "WH1/A-01", "0.10")

    def test_reads_still_work_and_history_stays(self):
        self.ok("product", "unarchive", "BOLT")
        self.receive("BOLT", 3, "WH1/A-01", "0.10", now=at(2))
        self.ok("scrap", "BOLT", "3", "--at", "WH1/A-01", "--reason", "x", now=at(3))
        self.archive("BOLT")
        self.assertEqual(len(self.ok("movement", "list", "--sku", "BOLT")), 2)
        rows, _ = self.val_rows("--at", at(2))
        self.assertEqual(rows[("BOLT", "WH1")], ("3", "0.30"))

    def test_reorder_skips_archived(self):
        self.assertEqual(self.ok("reorder", "--warehouse", "WH1"), [])
        self.ok("product", "unarchive", "BOLT")
        self.assertEqual([r["sku"] for r in self.ok("reorder", "--warehouse", "WH1")], ["BOLT"])

    def test_returns_of_an_archived_product_are_refused(self):
        self.ok("product", "unarchive", "BOLT")
        self.receive("BOLT", 10, "WH1/A-01", "0.10", now=at(2))
        so = self.order("Shop", "WH1", "BOLT:4")
        self.ok("so", "confirm", so)
        self.ok("so", "pick", so, user="bob")
        self.ok("so", "ship", so, user="bob")
        self.ok("scrap", "BOLT", "6", "--at", "WH1/A-01", "--reason", "x")
        self.archive("BOLT")
        self.err("return", "create", so, "--line", "1", "--qty", "1", "--condition", "good", user="carol")
        self.assertEqual(self.ok("return", "list"), [])


class T3ArchiveApi(Api):
    def test_archive_endpoints(self):
        s, p, _ = self.http("POST", "/products/BOLT/archive", {}, user="carol")
        self.assertEqual((s, p["archived"]), (200, True))
        s, p, h = self.http("GET", "/products/BOLT")
        self.assertEqual((s, p["archived"], h.get("ETag")), (200, True, '"2"'))
        s, p, _ = self.http("GET", "/products")
        self.assertNotIn("BOLT", [x["sku"] for x in p["items"]])
        s, p, _ = self.http("GET", "/products?archived=1")
        self.assertEqual([x["sku"] for x in p["items"]], ["BOLT"])
        self.assertEqual(self.http("POST", "/products/BOLT/archive", {}, user="bob")[0], 403)
        self.assertEqual(self.http("POST", "/products/BOLT/archive", {})[0], 400)
        self.assertEqual(self.http("POST", "/products/NOPE/archive", {})[0], 404)
        s, p, _ = self.http("POST", "/products/BOLT/unarchive", {})
        self.assertEqual((s, "archived" in p), (200, False))
        self.assertEqual(self.http("POST", "/products/BOLT/unarchive", {})[0], 400)

    def test_archived_products_are_refused_over_http(self):
        self.http("POST", "/products/BOLT/archive", {})
        s, _, _ = self.http("POST", "/receipts", {"sku": "BOLT", "qty": "1", "at": "WH1/A-01", "cost": "1"})
        self.assertEqual(s, 400)
        s, _, _ = self.http("PATCH", "/products/BOLT", {"name": "x"}, headers={"If-Match": '"2"'}, user="carol")
        self.assertEqual(s, 400)
