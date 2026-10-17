"""Hidden acceptance tests for the finance benchmark (v2). Never shown to the model.

    FIN_DIR=/path/to/built/repo python3 -m unittest discover -s bench/finance/accept

Each test runs `python -m fin` from FIN_DIR against a fresh database, through the command line
and HTTP interface that prompt.md specifies, and nothing else.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

FIN = os.environ.get("FIN_DIR", ".")


class Book(unittest.TestCase):
    """A fresh EUR book per test, with helpers for the command line."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "fin.db")
        self.ok("init", "--currency", "EUR", "--admin", "alice", user=None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_fin(self, *args, user="alice"):
        who = ["--user", user] if user else []
        return subprocess.run([sys.executable, "-m", "fin", "--db", self.db, "--json", *who, *args],
                              cwd=FIN, capture_output=True, text=True, timeout=60)

    def ok(self, *args, user="alice"):
        r = self.run_fin(*args, user=user)
        self.assertEqual(r.returncode, 0, f"{args}: exit {r.returncode}: {r.stderr[-500:]}")
        try:
            return json.loads(r.stdout) if r.stdout.strip() else None
        except ValueError:
            return None

    def js(self, *args, user="alice"):
        r = self.run_fin(*args, user=user)
        self.assertEqual(r.returncode, 0, f"{args}: exit {r.returncode}: {r.stderr[-500:]}")
        return json.loads(r.stdout)

    def user_error(self, *args, user="alice"):
        r = self.run_fin(*args, user=user)
        self.assertEqual(r.returncode, 2, f"{args}: expected exit 2, got {r.returncode}")
        self.assertEqual(r.stdout.strip(), "", f"{args}: stdout should be empty on a user error")
        self.assertNotEqual(r.stderr.strip(), "", f"{args}: no message on stderr")

    def accounts(self, *names, currency=None):
        for n in names:
            self.ok("account", "add", n, *(["--currency", currency] if currency else []))

    def txn(self, date, desc, *postings):
        return self.js("txn", "add", "--date", date, "--desc", desc,
                       *[a for p in postings for a in ("--posting", p)])

    def csv(self, text):
        path = os.path.join(self.tmp.name, f"s{time.monotonic_ns()}.csv")
        with open(path, "w") as f:
            f.write(text)
        return path


def postings(t):
    return {p["account"]: (p["amount"], p["currency"]) for p in t["postings"]}


class TestAccounts(Book):
    def test_init_twice_is_a_user_error(self):
        self.user_error("init", "--currency", "EUR", "--admin", "alice", user=None)

    def test_parents_are_created_and_listed_sorted(self):
        self.accounts("Assets:Bank:Checking", "Expenses:Food")
        self.assertEqual(self.js("account", "list"), [
            {"name": "Assets", "type": "asset", "currency": "EUR"},
            {"name": "Assets:Bank", "type": "asset", "currency": "EUR"},
            {"name": "Assets:Bank:Checking", "type": "asset", "currency": "EUR"},
            {"name": "Expenses", "type": "expense", "currency": "EUR"},
            {"name": "Expenses:Food", "type": "expense", "currency": "EUR"},
        ])

    def test_bad_root_and_duplicate_are_user_errors(self):
        self.user_error("account", "add", "Foo:Bar")
        self.accounts("Assets:Bank")
        self.user_error("account", "add", "Assets:Bank")

    def test_account_currency(self):
        self.accounts("Assets:Bank", "Liabilities:Card")
        self.accounts("Assets:Wallet", currency="USD")
        got = {a["name"]: (a["type"], a["currency"]) for a in self.js("account", "list")}
        self.assertEqual(got["Assets"], ("asset", "EUR"))
        self.assertEqual(got["Assets:Wallet"], ("asset", "USD"))
        self.assertEqual(got["Liabilities:Card"], ("liability", "EUR"))


class TestTransactions(Book):
    def test_add_with_balancing_posting(self):
        self.accounts("Assets:Bank", "Expenses:Rent")
        self.assertEqual(self.txn("2026-01-05", "Rent", "Expenses:Rent=900", "Assets:Bank"), {
            "id": 1, "date": "2026-01-05", "description": "Rent", "postings": [
                {"account": "Expenses:Rent", "amount": "900.00", "currency": "EUR"},
                {"account": "Assets:Bank", "amount": "-900.00", "currency": "EUR"}]})

    def test_invalid_transactions_are_rejected_and_not_stored(self):
        self.accounts("Assets:Bank", "Expenses:Rent")
        add = ("txn", "add", "--date", "2026-01-05", "--desc", "x")
        self.user_error(*add, "--posting", "Expenses:Rent=900", "--posting", "Assets:Bank=-800")
        self.user_error(*add, "--posting", "Expenses:Nope=900", "--posting", "Assets:Bank")
        self.user_error(*add, "--posting", "Expenses:Rent", "--posting", "Assets:Bank")
        self.user_error(*add, "--posting", "Expenses:Rent=900")
        self.assertEqual(self.js("txn", "list"), [])

    def test_each_currency_must_balance(self):
        self.accounts("Assets:Bank", "Equity:Exchange")
        self.accounts("Assets:Dollars", "Equity:ExchangeUSD", currency="USD")
        self.user_error("txn", "add", "--date", "2026-01-02", "--desc", "fx",
                        "--posting", "Assets:Bank=-100", "--posting", "Assets:Dollars=110")
        t = self.txn("2026-01-02", "fx", "Assets:Bank=-100", "Equity:Exchange=100",
                     "Assets:Dollars=110", "Equity:ExchangeUSD=-110")
        self.assertEqual(postings(t)["Assets:Dollars"], ("110.00", "USD"))

    def test_list_order_and_filters(self):
        self.accounts("Assets:Bank", "Expenses:Food", "Expenses:Rent", "Income:Salary")
        self.txn("2026-01-10", "Food", "Expenses:Food=40", "Assets:Bank")
        self.txn("2026-01-05", "Rent", "Expenses:Rent=900", "Assets:Bank")
        self.txn("2026-02-01", "Salary", "Assets:Bank=3000", "Income:Salary")
        ids = lambda *a: [t["id"] for t in self.js("txn", "list", *a)]
        self.assertEqual(ids(), [2, 1, 3])
        self.assertEqual(ids("--account", "Expenses"), [2, 1])
        self.assertEqual(ids("--account", "Expenses:Food"), [1])
        self.assertEqual(ids("--from", "2026-01-06", "--to", "2026-01-31"), [1])
        self.assertEqual(ids("--from", "2026-01-05", "--to", "2026-02-01"), [2, 1, 3])


class TestBalances(Book):
    def test_rollup_and_as_of_date(self):
        self.accounts("Assets:Bank:Checking", "Assets:Bank:Savings", "Income:Salary")
        self.txn("2026-01-31", "Salary", "Assets:Bank:Checking=3000", "Income:Salary")
        self.txn("2026-02-01", "Save", "Assets:Bank:Savings=1000", "Assets:Bank:Checking")
        self.assertEqual(self.js("balance", "--at", "2026-01-31"), {
            "Assets": {"EUR": "3000.00"}, "Assets:Bank": {"EUR": "3000.00"},
            "Assets:Bank:Checking": {"EUR": "3000.00"},
            "Income": {"EUR": "-3000.00"}, "Income:Salary": {"EUR": "-3000.00"}})
        b = self.js("balance")
        self.assertEqual(b["Assets:Bank:Checking"], {"EUR": "2000.00"})
        self.assertEqual(b["Assets:Bank:Savings"], {"EUR": "1000.00"})
        self.assertEqual(b["Assets:Bank"], {"EUR": "3000.00"})


class TestFx(Book):
    def test_direct_inverse_latest_and_rounding(self):
        self.ok("fx", "add", "2026-01-01", "USD", "EUR", "0.9")
        self.ok("fx", "add", "2026-02-01", "USD", "EUR", "0.8")
        self.ok("fx", "add", "2026-03-01", "USD", "EUR", "0.125")
        conv = lambda *a: self.js("convert", *a)
        self.assertEqual(conv("100", "USD", "EUR", "--at", "2026-01-15"), {"amount": "90.00", "currency": "EUR"})
        self.assertEqual(conv("100", "USD", "EUR", "--at", "2026-02-15")["amount"], "80.00")
        self.assertEqual(conv("90", "EUR", "USD", "--at", "2026-01-15"), {"amount": "100.00", "currency": "USD"})
        self.assertEqual(conv("1", "EUR", "USD", "--at", "2026-02-15")["amount"], "1.25")
        self.assertEqual(conv("1", "USD", "EUR", "--at", "2026-03-01")["amount"], "0.13")
        self.assertEqual(conv("10", "EUR", "EUR", "--at", "2026-01-15")["amount"], "10.00")
        self.user_error("convert", "1", "USD", "EUR", "--at", "2025-12-31")
        self.user_error("convert", "1", "GBP", "EUR", "--at", "2026-01-15")


class TestImport(Book):
    STATEMENT = ("date,description,amount\n"
                 "2026-01-02,TESCO STORE 12,-25.40\n"
                 "2026-01-03,Salary ACME,3000.00\n"
                 "2026-01-04,Unknown shop,-5.00\n"
                 "2026-01-02,TESCO STORE 12,-25.40\n")

    def test_rules_categories_and_duplicates(self):
        self.accounts("Assets:Bank", "Expenses:Food")
        self.ok("rule", "add", "tesco|lidl", "Expenses:Food")
        self.assertEqual(self.js("rule", "list"), [{"pattern": "tesco|lidl", "account": "Expenses:Food"}])
        path = self.csv(self.STATEMENT)
        self.assertEqual(self.js("import", path, "--account", "Assets:Bank", "--skip-header"),
                         {"imported": 3, "skipped": 1})
        got = {t["description"]: postings(t) for t in self.js("txn", "list")}
        self.assertEqual(got["TESCO STORE 12"], {"Assets:Bank": ("-25.40", "EUR"), "Expenses:Food": ("25.40", "EUR")})
        self.assertEqual(got["Salary ACME"], {"Assets:Bank": ("3000.00", "EUR"), "Income:Uncategorized": ("-3000.00", "EUR")})
        self.assertEqual(got["Unknown shop"], {"Assets:Bank": ("-5.00", "EUR"), "Expenses:Uncategorized": ("5.00", "EUR")})
        self.assertEqual(self.js("import", path, "--account", "Assets:Bank", "--skip-header"),
                         {"imported": 0, "skipped": 4})
        self.assertEqual(len(self.js("txn", "list")), 3)

    def test_column_options(self):
        self.accounts("Assets:Bank")
        path = self.csv("-12.50,2026-03-04,Coffee bar\n")
        self.assertEqual(self.js("import", path, "--account", "Assets:Bank", "--amount-col", "0",
                                 "--date-col", "1", "--desc-col", "2"), {"imported": 1, "skipped": 0})
        (t,) = self.js("txn", "list")
        self.assertEqual((t["date"], t["description"]), ("2026-03-04", "Coffee bar"))
        self.assertEqual(postings(t)["Expenses:Uncategorized"], ("12.50", "EUR"))


class TestBudgets(Book):
    def test_budget_vs_actual(self):
        self.accounts("Assets:Bank", "Expenses:Food:Restaurants", "Expenses:Rent")
        self.ok("budget", "set", "Expenses:Food", "2026-01", "300")
        self.ok("budget", "set", "Expenses:Rent", "2026-01", "900")
        self.ok("budget", "set", "Expenses:Food", "2026-01", "350")
        self.txn("2026-01-03", "Shop", "Expenses:Food=100", "Assets:Bank")
        self.txn("2026-01-20", "Dinner", "Expenses:Food:Restaurants=50.50", "Assets:Bank")
        self.txn("2026-01-05", "Rent", "Expenses:Rent=900", "Assets:Bank")
        self.txn("2026-02-02", "Shop", "Expenses:Food=20", "Assets:Bank")
        self.assertEqual(self.js("report", "budget", "2026-01"), [
            {"account": "Expenses:Food", "budget": "350.00", "actual": "150.50", "remaining": "199.50"},
            {"account": "Expenses:Rent", "budget": "900.00", "actual": "900.00", "remaining": "0.00"}])


class TestRecurring(Book):
    def setUp(self):
        super().setUp()
        self.accounts("Assets:Bank", "Expenses:Rent", "Expenses:Gym", "Expenses:Insurance")

    def dates(self, desc):
        return [t["date"] for t in self.js("txn", "list") if t["description"] == desc]

    def test_monthly_month_ends_and_idempotent(self):
        self.ok("recurring", "add", "Rent", "--every", "monthly", "--start", "2026-01-31",
                "--posting", "Expenses:Rent=900", "--posting", "Assets:Bank")
        self.assertEqual(self.js("recurring", "run", "--until", "2026-04-30"), {"created": 4})
        self.assertEqual(self.dates("Rent"), ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"])
        self.assertEqual(self.js("recurring", "run", "--until", "2026-04-30"), {"created": 0})
        self.assertEqual(self.js("recurring", "run", "--until", "2026-05-31"), {"created": 1})

    def test_weekly_and_yearly(self):
        self.ok("recurring", "add", "Gym", "--every", "weekly", "--start", "2026-01-01",
                "--posting", "Expenses:Gym=10", "--posting", "Assets:Bank")
        self.ok("recurring", "add", "Insurance", "--every", "yearly", "--start", "2024-02-29",
                "--posting", "Expenses:Insurance=120", "--posting", "Assets:Bank")
        self.ok("recurring", "run", "--until", "2027-03-01")
        gym = self.dates("Gym")
        self.assertEqual(gym[:5], ["2026-01-01", "2026-01-08", "2026-01-15", "2026-01-22", "2026-01-29"])
        self.assertEqual(self.dates("Insurance"), ["2024-02-29", "2025-02-28", "2026-02-28", "2027-02-28"])

    def test_unbalanced_recurring_is_a_user_error(self):
        self.user_error("recurring", "add", "Bad", "--every", "monthly", "--start", "2026-01-01",
                        "--posting", "Expenses:Rent=900", "--posting", "Assets:Bank=-1")


class Ledger(Book):
    """A small two-month book shared by the report tests."""

    def setUp(self):
        super().setUp()
        self.accounts("Assets:Bank", "Assets:Cash", "Liabilities:Card", "Equity:Opening",
                      "Income:Salary", "Expenses:Rent", "Expenses:Food")
        self.txn("2026-01-01", "Opening", "Assets:Bank=1000", "Equity:Opening")
        self.txn("2026-01-05", "Salary", "Assets:Bank=3000", "Income:Salary")
        self.txn("2026-01-06", "Rent", "Expenses:Rent=900", "Assets:Bank")
        self.txn("2026-01-10", "Groceries", "Expenses:Food=120.50", "Liabilities:Card")
        self.txn("2026-02-03", "Card payment", "Liabilities:Card=120.50", "Assets:Bank")
        self.txn("2026-02-05", "Salary", "Assets:Bank=3000", "Income:Salary")
        self.txn("2026-02-08", "ATM", "Assets:Cash=200", "Assets:Bank")
        self.txn("2026-02-09", "Market", "Expenses:Food=45", "Assets:Cash")


class TestReports(Ledger):
    def test_income_statement(self):
        self.assertEqual(self.js("report", "income", "--from", "2026-01-01", "--to", "2026-01-31"), {
            "income": {"Income:Salary": "3000.00"},
            "expenses": {"Expenses:Rent": "900.00", "Expenses:Food": "120.50"},
            "total_income": "3000.00", "total_expenses": "1020.50", "net": "1979.50"})
        feb = self.js("report", "income", "--from", "2026-02-01", "--to", "2026-02-28")
        self.assertEqual((feb["expenses"], feb["net"]), ({"Expenses:Food": "45.00"}, "2955.00"))

    def test_balance_sheet(self):
        self.assertEqual(self.js("report", "balance-sheet", "--at", "2026-01-31"), {
            "assets": {"Assets:Bank": "3100.00"}, "liabilities": {"Liabilities:Card": "120.50"},
            "equity": {"Equity:Opening": "1000.00"}, "retained_earnings": "1979.50",
            "total_assets": "3100.00", "total_liabilities": "120.50", "total_equity": "2979.50"})
        feb = self.js("report", "balance-sheet", "--at", "2026-02-28")
        self.assertEqual(feb["assets"], {"Assets:Bank": "5779.50", "Assets:Cash": "155.00"})
        self.assertEqual(feb["liabilities"], {"Liabilities:Card": "0.00"})
        self.assertEqual((feb["retained_earnings"], feb["total_assets"], feb["total_liabilities"],
                          feb["total_equity"]), ("4934.50", "5934.50", "0.00", "5934.50"))

    def test_networth(self):
        self.assertEqual(self.js("report", "networth", "--from", "2026-01", "--to", "2026-02"), [
            {"month": "2026-01", "assets": "3100.00", "liabilities": "120.50", "networth": "2979.50"},
            {"month": "2026-02", "assets": "5934.50", "liabilities": "0.00", "networth": "5934.50"}])


class TestReportCurrency(Book):
    def test_conversion_in_reports(self):
        self.accounts("Assets:Dollars", "Equity:OpeningUSD", currency="USD")
        self.txn("2026-01-01", "Opening USD", "Assets:Dollars=500", "Equity:OpeningUSD")
        self.ok("fx", "add", "2026-01-01", "USD", "EUR", "0.9")
        bs = self.js("report", "balance-sheet", "--at", "2026-01-31")
        self.assertEqual((bs["assets"], bs["equity"], bs["total_assets"], bs["total_equity"]),
                         ({"Assets:Dollars": "450.00"}, {"Equity:OpeningUSD": "450.00"}, "450.00", "450.00"))
        usd = self.js("report", "balance-sheet", "--at", "2026-01-31", "--currency", "USD")
        self.assertEqual(usd["total_assets"], "500.00")
        self.user_error("report", "balance-sheet", "--at", "2026-01-31", "--currency", "GBP")


class TestLoans(Book):
    def test_annuity_schedule(self):
        s = self.js("loan", "schedule", "10000", "6", "12", "--start", "2026-01-15")
        self.assertEqual((s["payment"], s["total_interest"], len(s["rows"])), ("860.66", "327.96", 12))
        self.assertEqual(s["rows"][0], {"n": 1, "date": "2026-02-15", "payment": "860.66",
                                        "interest": "50.00", "principal": "810.66", "balance": "9189.34"})
        self.assertEqual(s["rows"][-1], {"n": 12, "date": "2027-01-15", "payment": "860.70",
                                         "interest": "4.28", "principal": "856.42", "balance": "0.00"})

    def test_fractional_rate_and_month_ends(self):
        s = self.js("loan", "schedule", "5000", "7.5", "6", "--start", "2026-01-31")
        self.assertEqual((s["payment"], s["total_interest"]), ("851.66", "109.94"))
        self.assertEqual([r["date"] for r in s["rows"][:3]], ["2026-02-28", "2026-03-31", "2026-04-30"])
        self.assertEqual((s["rows"][-1]["payment"], s["rows"][-1]["balance"]), ("851.64", "0.00"))

    def test_zero_rate(self):
        s = self.js("loan", "schedule", "1200", "0", "12", "--start", "2026-01-01")
        self.assertEqual((s["payment"], s["total_interest"]), ("100.00", "0.00"))
        self.assertTrue(all(r["interest"] == "0.00" for r in s["rows"]))
        self.assertEqual(s["rows"][-1]["balance"], "0.00")


class Server(Ledger):
    """The Ledger book served over HTTP on a free port."""

    def setUp(self):
        super().setUp()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.server = subprocess.Popen(
            [sys.executable, "-m", "fin", "--db", self.db, "serve", "--port", str(self.port)],
            cwd=FIN, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                self.get("/accounts")
                break
            except OSError:
                time.sleep(0.1)

    def tearDown(self):
        self.server.terminate()
        self.server.wait(timeout=10)
        super().tearDown()

    def call(self, method, path, body=None, user="alice"):
        headers = {"Content-Type": "application/json", **({"X-User": user} if user else {})}
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw) if raw else None
            except ValueError:
                return e.code, None

    def get(self, path):
        return self.call("GET", path)


class TestApi(Server):
    def test_reads_match_the_command_line(self):
        self.assertEqual(self.get("/accounts"), (200, self.js("account", "list")))
        self.assertEqual(self.get("/transactions"), (200, self.js("txn", "list")))
        self.assertEqual(self.get("/balances?at=2026-01-31"), (200, self.js("balance", "--at", "2026-01-31")))
        self.assertEqual(self.get("/reports/income?from=2026-01-01&to=2026-01-31"),
                         (200, self.js("report", "income", "--from", "2026-01-01", "--to", "2026-01-31")))
        self.assertEqual(self.get("/reports/balance-sheet?at=2026-02-28"),
                         (200, self.js("report", "balance-sheet", "--at", "2026-02-28")))

    def test_post_transactions_and_errors(self):
        status, t = self.call("POST", "/transactions", {"date": "2026-03-01", "description": "Lunch",
                              "postings": [{"account": "Expenses:Food", "amount": "12.30"},
                                           {"account": "Assets:Cash"}]})
        self.assertEqual(status, 201)
        self.assertEqual((t["id"], postings(t)["Assets:Cash"]), (9, ("-12.30", "EUR")))
        status, e = self.call("POST", "/transactions", {"date": "2026-03-01", "description": "Bad",
                              "postings": [{"account": "Expenses:Food", "amount": "1"},
                                           {"account": "Assets:Cash", "amount": "-2"}]})
        self.assertEqual(status, 400)
        self.assertIn("error", e)
        self.assertEqual(self.get("/no-such-path")[0], 404)
        self.assertEqual(len(self.js("txn", "list")), 9)


def audit_view(entries):
    return [(e["user"], e["action"], e["target"]) for e in entries]


class TestUsers(Book):
    def setUp(self):
        super().setUp()
        self.ok("user", "add", "bob", "--role", "editor")
        self.ok("user", "add", "vic", "--role", "viewer")

    def test_roles(self):
        self.assertEqual(self.js("user", "list"), [
            {"name": "alice", "role": "admin"}, {"name": "bob", "role": "editor"},
            {"name": "vic", "role": "viewer"}])
        self.user_error("account", "add", "Assets:Bank", user="vic")
        self.js("account", "list", user="vic")
        self.js("account", "list", user=None)
        self.ok("account", "add", "Assets:Bank", user="bob")
        self.user_error("user", "add", "eve", "--role", "viewer", user="bob")
        self.user_error("period", "close", "2026-01", user="bob")
        self.user_error("account", "add", "Expenses:Food", user=None)
        self.user_error("account", "add", "Expenses:Food", user="zed")
        self.user_error("user", "add", "bob", "--role", "viewer")
        self.assertEqual([a["name"] for a in self.js("account", "list")], ["Assets", "Assets:Bank"])

    def test_audit_log(self):
        self.ok("account", "add", "Assets:Bank")
        self.ok("account", "add", "Expenses:Food", user="bob")
        self.txn_as("bob")
        self.user_error("txn", "add", "--date", "2026-01-02", "--desc", "bad",
                        "--posting", "Expenses:Food=5", "--posting", "Assets:Bank=-4", user="bob")
        self.ok("fx", "add", "2026-01-01", "USD", "EUR", "0.9")
        log = self.js("audit", "list", user="vic")
        self.assertEqual(audit_view(log), [
            ("alice", "init", "EUR"), ("alice", "user.add", "bob"), ("alice", "user.add", "vic"),
            ("alice", "account.add", "Assets:Bank"), ("bob", "account.add", "Expenses:Food"),
            ("bob", "txn.add", "1"), ("alice", "fx.add", "USD/EUR")])
        self.assertEqual([e["seq"] for e in log], list(range(1, 8)))
        self.assertTrue(all(set(e) == {"seq", "at", "user", "action", "target"} for e in log))
        self.assertEqual(audit_view(self.js("audit", "list", "--by", "bob")),
                         [("bob", "account.add", "Expenses:Food"), ("bob", "txn.add", "1")])

    def txn_as(self, user):
        return self.js("txn", "add", "--date", "2026-01-02", "--desc", "Lunch",
                       "--posting", "Expenses:Food=12", "--posting", "Assets:Bank", user=user)


class TestPeriods(Book):
    def setUp(self):
        super().setUp()
        self.ok("user", "add", "bob", "--role", "editor")
        self.accounts("Assets:Bank", "Expenses:Rent")
        self.txn("2026-01-15", "Rent", "Expenses:Rent=900", "Assets:Bank")

    def test_close_blocks_postings(self):
        self.assertEqual(self.js("period", "status"), {"closed_through": None})
        self.user_error("period", "close", "2026-01", user="bob")
        self.ok("period", "close", "2026-01")
        self.assertEqual(self.js("period", "status"), {"closed_through": "2026-01"})
        self.user_error("txn", "add", "--date", "2026-01-31", "--desc", "Late",
                        "--posting", "Expenses:Rent=1", "--posting", "Assets:Bank")
        self.txn("2026-02-01", "Rent", "Expenses:Rent=900", "Assets:Bank")
        self.ok("period", "close", "2025-12")
        self.assertEqual(self.js("period", "status"), {"closed_through": "2026-01"})

    def test_import_and_recurring_fail_whole(self):
        self.ok("period", "close", "2026-01")
        path = self.csv("2026-01-20,Shop,-10.00\n2026-02-02,Shop,-12.00\n")
        self.user_error("import", path, "--account", "Assets:Bank")
        self.ok("recurring", "add", "Rent", "--every", "monthly", "--start", "2026-01-05",
                "--posting", "Expenses:Rent=900", "--posting", "Assets:Bank")
        self.user_error("recurring", "run", "--until", "2026-03-31")
        self.assertEqual(len(self.js("txn", "list")), 1)


class Sales(Book):
    """Tax codes, two customers and a bank account."""

    def setUp(self):
        super().setUp()
        self.ok("tax", "add", "VAT20", "20")
        self.ok("tax", "add", "VAT5", "5")
        self.ok("customer", "add", "Acme")
        self.ok("customer", "add", "Beta", "--terms", "14")
        self.accounts("Assets:Bank")

    def invoice(self, customer, date, *lines, issue=True):
        inv = self.js("invoice", "create", "--customer", customer, "--date", date,
                      *[a for line in lines for a in ("--line", line)])
        return self.js("invoice", "issue", str(inv["id"])) if issue else inv

    def by_desc(self, desc):
        (t,) = [t for t in self.js("txn", "list") if t["description"] == desc]
        return t


class TestInvoices(Sales):
    def test_tax_codes_and_customers(self):
        self.assertEqual(self.js("tax", "list"), [{"code": "VAT20", "rate": "20"}, {"code": "VAT5", "rate": "5"}])
        self.assertEqual(self.js("customer", "list"), [{"name": "Acme", "terms": 30}, {"name": "Beta", "terms": 14}])

    def test_draft_amounts(self):
        inv = self.invoice("Acme", "2026-01-10", "Consulting;10;95;VAT20", "Travel;1;33.33;",
                           "Books;3;12.99;VAT5", issue=False)
        self.assertEqual(inv, {
            "id": 1, "number": None, "customer": "Acme", "date": "2026-01-10", "due": "2026-02-09",
            "status": "draft", "lines": [
                {"description": "Consulting", "quantity": "10", "price": "95.00", "tax_code": "VAT20", "net": "950.00", "tax": "190.00"},
                {"description": "Travel", "quantity": "1", "price": "33.33", "tax_code": None, "net": "33.33", "tax": "0.00"},
                {"description": "Books", "quantity": "3", "price": "12.99", "tax_code": "VAT5", "net": "38.97", "tax": "1.95"}],
            "net": "1022.30", "tax": "191.95", "total": "1214.25", "paid": "0.00", "balance": "1214.25"})
        self.assertEqual(self.js("txn", "list"), [])
        self.user_error("invoice", "create", "--customer", "Nobody", "--date", "2026-01-10", "--line", "X;1;1;")
        self.user_error("invoice", "create", "--customer", "Acme", "--date", "2026-01-10", "--line", "X;1;1;GST9")

    def test_issue_numbers_and_posting(self):
        a = self.invoice("Acme", "2026-01-10", "Consulting;10;95;VAT20", issue=False)
        b = self.invoice("Beta", "2026-02-01", "Design;2;200;", issue=False)
        c = self.invoice("Acme", "2027-01-05", "Support;1;100;VAT20", issue=False)
        issue = lambda inv: self.js("invoice", "issue", str(inv["id"]))
        self.assertEqual((issue(b)["number"], issue(a)["number"], issue(c)["number"]),
                         ("INV-2026-0001", "INV-2026-0002", "INV-2027-0001"))
        self.assertEqual(self.js("invoice", "show", str(a["id"]))["status"], "issued")
        self.user_error("invoice", "issue", str(a["id"]))
        t = self.by_desc("Invoice INV-2026-0002")
        self.assertEqual((t["date"], postings(t)), ("2026-01-10", {
            "Assets:Receivable": ("1140.00", "EUR"), "Income:Sales": ("-950.00", "EUR"),
            "Liabilities:SalesTax": ("-190.00", "EUR")}))
        self.assertEqual(postings(self.by_desc("Invoice INV-2026-0001")), {
            "Assets:Receivable": ("400.00", "EUR"), "Income:Sales": ("-400.00", "EUR")})

    def test_payments_and_status(self):
        a = self.invoice("Acme", "2026-01-10", "Consulting;10;95;VAT20")
        draft = self.invoice("Beta", "2026-01-11", "Design;1;50;", issue=False)
        pay = lambda inv, amt, *e: ("invoice", "pay", str(inv["id"]), amt, "--date", "2026-01-20",
                                    "--account", "Assets:Bank", *e)
        p = self.js(*pay(a, "500"))
        self.assertEqual((p["status"], p["paid"], p["balance"]), ("partial", "500.00", "640.00"))
        self.user_error(*pay(a, "700"))
        p = self.js(*pay(a, "640"))
        self.assertEqual((p["status"], p["paid"], p["balance"]), ("paid", "1140.00", "0.00"))
        self.user_error(*pay(a, "1"))
        self.user_error(*pay(draft, "10"))
        self.assertEqual(postings(self.js("txn", "list", "--account", "Assets:Bank")[0]),
                         {"Assets:Bank": ("500.00", "EUR"), "Assets:Receivable": ("-500.00", "EUR")})
        self.assertEqual([i["id"] for i in self.js("invoice", "list", "--status", "paid")], [a["id"]])
        self.assertEqual(self.js("balance")["Assets:Receivable"], {"EUR": "0.00"})

    def test_aging(self):
        i1 = self.invoice("Acme", "2026-01-01", "A;1;100;")
        i2 = self.invoice("Acme", "2026-02-15", "B;1;200;")
        self.invoice("Beta", "2026-03-01", "C;1;300;")
        self.invoice("Acme", "2026-03-20", "D;1;400;")
        self.invoice("Beta", "2026-04-10", "E;1;50;")
        self.invoice("Acme", "2026-01-01", "F;1;999;", issue=False)
        self.ok("invoice", "pay", str(i1["id"]), "30", "--date", "2026-02-10", "--account", "Assets:Bank")
        self.ok("invoice", "pay", str(i2["id"]), "200", "--date", "2026-04-05", "--account", "Assets:Bank")
        self.assertEqual(self.js("report", "aging", "--at", "2026-04-01"), {
            "current": "400.00", "1-30": "500.00", "31-60": "70.00", "61-90": "0.00", "90+": "0.00",
            "total": "970.00"})
        self.assertEqual(self.js("report", "aging", "--at", "2026-06-01"), {
            "current": "0.00", "1-30": "0.00", "31-60": "450.00", "61-90": "300.00", "90+": "70.00",
            "total": "820.00"})


class Purchases(Book):
    def setUp(self):
        super().setUp()
        self.ok("tax", "add", "VAT20", "20")
        self.ok("tax", "add", "VAT5", "5")
        self.ok("vendor", "add", "Office Ltd")
        self.ok("vendor", "add", "Cloud Co", "--terms", "10")
        self.accounts("Assets:Bank", "Assets:Equipment", "Expenses:Office", "Expenses:Hosting", "Income:Other")

    def bill(self, vendor, ref, date, *lines):
        return self.js("bill", "create", "--vendor", vendor, "--ref", ref, "--date", date,
                       *[a for line in lines for a in ("--line", line)])


class TestBills(Purchases):
    def test_bill_amounts_and_posting(self):
        b = self.bill("Office Ltd", "A-17", "2026-01-08", "Paper;40;Expenses:Office;VAT20",
                      "Laptop;1200;Assets:Equipment;VAT20", "Delivery;9.99;Expenses:Office;")
        self.assertEqual(b, {
            "id": 1, "vendor": "Office Ltd", "ref": "A-17", "date": "2026-01-08", "due": "2026-02-07",
            "status": "open", "lines": [
                {"description": "Paper", "account": "Expenses:Office", "tax_code": "VAT20", "net": "40.00", "tax": "8.00"},
                {"description": "Laptop", "account": "Assets:Equipment", "tax_code": "VAT20", "net": "1200.00", "tax": "240.00"},
                {"description": "Delivery", "account": "Expenses:Office", "tax_code": None, "net": "9.99", "tax": "0.00"}],
            "net": "1249.99", "tax": "248.00", "total": "1497.99", "paid": "0.00", "balance": "1497.99"})
        bal = self.js("balance")
        self.assertEqual((bal["Expenses:Office"], bal["Assets:Equipment"], bal["Assets:TaxReceivable"],
                          bal["Liabilities:Payable"]),
                         ({"EUR": "49.99"}, {"EUR": "1200.00"}, {"EUR": "248.00"}, {"EUR": "-1497.99"}))
        self.assertEqual(self.by_desc("Bill A-17")["date"], "2026-01-08")
        self.user_error("bill", "create", "--vendor", "Office Ltd", "--ref", "A-17", "--date", "2026-01-09",
                        "--line", "X;1;Expenses:Office;")
        self.bill("Cloud Co", "A-17", "2026-01-09", "Hosting;5;Expenses:Hosting;")
        self.user_error("bill", "create", "--vendor", "Cloud Co", "--ref", "Z", "--date", "2026-01-09",
                        "--line", "X;1;Income:Other;")
        self.user_error("bill", "create", "--vendor", "Cloud Co", "--ref", "Y", "--date", "2026-01-09",
                        "--line", "X;1;Expenses:Nope;")

    def by_desc(self, desc):
        (t,) = [t for t in self.js("txn", "list") if t["description"] == desc]
        return t

    def test_payments_and_payables_aging(self):
        a = self.bill("Office Ltd", "A-17", "2026-01-08", "Paper;40;Expenses:Office;VAT20",
                      "Laptop;1200;Assets:Equipment;VAT20", "Delivery;9.99;Expenses:Office;")
        h = self.bill("Cloud Co", "B-1", "2026-03-01", "Hosting;100;Expenses:Hosting;")
        pay = lambda b, amt, date: ("bill", "pay", str(b["id"]), amt, "--date", date, "--account", "Assets:Bank")
        p = self.js(*pay(a, "497.99", "2026-02-01"))
        self.assertEqual((p["status"], p["balance"]), ("partial", "1000.00"))
        self.user_error(*pay(a, "1000.01", "2026-02-02"))
        self.assertEqual(postings(self.by_desc("Payment A-17")),
                         {"Liabilities:Payable": ("497.99", "EUR"), "Assets:Bank": ("-497.99", "EUR")})
        self.assertEqual(self.js(*pay(h, "100", "2026-03-25"))["status"], "paid")
        self.assertEqual(self.js("report", "aging", "--at", "2026-03-20", "--payables"), {
            "current": "0.00", "1-30": "100.00", "31-60": "1000.00", "61-90": "0.00", "90+": "0.00",
            "total": "1100.00"})
        self.assertEqual(self.js("report", "aging", "--at", "2026-03-20")["total"], "0.00")


class TestTaxReport(Book):
    def test_collected_and_paid_by_code(self):
        self.ok("tax", "add", "VAT20", "20")
        self.ok("tax", "add", "VAT5", "5")
        self.ok("customer", "add", "Acme")
        self.ok("vendor", "add", "Office Ltd")
        self.accounts("Assets:Bank", "Expenses:Office")
        for date, line, issue in [("2026-01-10", "Consulting;10;95;VAT20", True), ("2026-01-20", "Books;3;12.99;VAT5", True),
                                  ("2026-02-02", "Consulting;1;100;VAT20", True), ("2026-01-25", "X;1;1000;VAT20", False)]:
            inv = self.js("invoice", "create", "--customer", "Acme", "--date", date, "--line", line)
            if issue:
                self.ok("invoice", "issue", str(inv["id"]))
        self.ok("bill", "create", "--vendor", "Office Ltd", "--ref", "1", "--date", "2026-01-08",
                "--line", "Paper;40;Expenses:Office;VAT20")
        self.ok("bill", "create", "--vendor", "Office Ltd", "--ref", "2", "--date", "2026-01-15",
                "--line", "Pens;10;Expenses:Office;VAT5")
        self.assertEqual(self.js("report", "tax", "--from", "2026-01-01", "--to", "2026-01-31"), {
            "collected": "191.95", "paid": "8.50", "net": "183.45",
            "by_code": {"VAT20": {"collected": "190.00", "paid": "8.00"}, "VAT5": {"collected": "1.95", "paid": "0.50"}}})
        self.assertEqual(self.js("report", "tax", "--from", "2026-02-01", "--to", "2026-02-28"), {
            "collected": "20.00", "paid": "0.00", "net": "20.00",
            "by_code": {"VAT20": {"collected": "20.00", "paid": "0.00"}}})


class TestReconcile(Book):
    def test_clearing_across_statements(self):
        self.accounts("Assets:Bank", "Income:Salary", "Expenses:Rent", "Expenses:Food", "Liabilities:Card")
        self.txn("2026-01-02", "Salary", "Assets:Bank=3000", "Income:Salary")
        self.txn("2026-01-05", "Rent", "Expenses:Rent=900", "Assets:Bank")
        self.txn("2026-01-20", "Food", "Expenses:Food=45.50", "Assets:Bank")
        self.txn("2026-02-03", "Food", "Expenses:Food=30", "Assets:Bank")
        self.txn("2026-01-21", "Card food", "Expenses:Food=10", "Liabilities:Card")
        rec = ("reconcile", "Assets:Bank", "--date")
        self.user_error(*rec, "2026-01-31", "--balance", "0", "--clear", "3", "--clear", "99")
        self.assertEqual(self.js(*rec, "2026-01-31", "--balance", "2100", "--clear", "1", "--clear", "2"), {
            "account": "Assets:Bank", "date": "2026-01-31", "statement_balance": "2100.00",
            "cleared_balance": "2100.00", "difference": "0.00", "uncleared": [3]})
        self.user_error(*rec, "2026-01-31", "--balance", "0", "--clear", "4")
        self.user_error(*rec, "2026-01-31", "--balance", "0", "--clear", "5")
        r = self.js(*rec, "2026-02-28", "--balance", "2024.50", "--clear", "3")
        self.assertEqual((r["cleared_balance"], r["difference"], r["uncleared"]), ("2054.50", "-30.00", [4]))


class TestLedgerReports(Ledger):
    def test_trial_balance(self):
        self.assertEqual(self.js("report", "trial-balance", "--at", "2026-01-31"), {"rows": [
            {"account": "Assets:Bank", "debit": "3100.00", "credit": "0.00"},
            {"account": "Equity:Opening", "debit": "0.00", "credit": "1000.00"},
            {"account": "Expenses:Food", "debit": "120.50", "credit": "0.00"},
            {"account": "Expenses:Rent", "debit": "900.00", "credit": "0.00"},
            {"account": "Income:Salary", "debit": "0.00", "credit": "3000.00"},
            {"account": "Liabilities:Card", "debit": "0.00", "credit": "120.50"}],
            "total_debit": "4120.50", "total_credit": "4120.50"})
        feb = self.js("report", "trial-balance", "--at", "2026-02-28")
        rows = {r["account"]: (r["debit"], r["credit"]) for r in feb["rows"]}
        self.assertEqual((rows["Liabilities:Card"], rows["Assets:Cash"], rows["Income:Salary"]),
                         (("0.00", "0.00"), ("155.00", "0.00"), ("0.00", "6000.00")))
        self.assertEqual((feb["total_debit"], feb["total_credit"]), ("7000.00", "7000.00"))

    def test_account_ledger(self):
        self.assertEqual(self.js("report", "ledger", "Assets:Bank", "--from", "2026-01-05", "--to", "2026-02-05"), {
            "account": "Assets:Bank", "opening": "1000.00", "rows": [
                {"date": "2026-01-05", "id": 2, "description": "Salary", "amount": "3000.00", "balance": "4000.00"},
                {"date": "2026-01-06", "id": 3, "description": "Rent", "amount": "-900.00", "balance": "3100.00"},
                {"date": "2026-02-03", "id": 5, "description": "Card payment", "amount": "-120.50", "balance": "2979.50"},
                {"date": "2026-02-05", "id": 6, "description": "Salary", "amount": "3000.00", "balance": "5979.50"}],
            "closing": "5979.50"})
        parent = self.js("report", "ledger", "Assets", "--from", "2026-02-06", "--to", "2026-02-28")
        self.assertEqual((parent["opening"], parent["closing"], sorted(r["amount"] for r in parent["rows"])),
                         ("5979.50", "5934.50", ["-200.00", "-45.00", "200.00"]))


class TestApiV2(Server):
    """The API's users, invoices and reports."""

    def setUp(self):
        super().setUp()
        self.ok("user", "add", "vic", "--role", "viewer")
        self.ok("tax", "add", "VAT20", "20")
        self.ok("customer", "add", "Acme")

    def test_users_on_writes(self):
        body = {"date": "2026-03-01", "description": "Lunch",
                "postings": [{"account": "Expenses:Food", "amount": "5"}, {"account": "Assets:Cash"}]}
        self.assertEqual(self.call("POST", "/transactions", body, user=None)[0], 401)
        self.assertEqual(self.call("POST", "/transactions", body, user="zed")[0], 401)
        status, e = self.call("POST", "/transactions", body, user="vic")
        self.assertEqual((status, "error" in (e or {})), (403, True))
        self.assertEqual(self.call("POST", "/transactions", body)[0], 201)
        self.assertEqual(len(self.js("txn", "list")), 9)
        self.assertEqual(audit_view(self.js("audit", "list"))[-1], ("alice", "txn.add", "9"))

    def test_invoice_flow_and_reports(self):
        status, inv = self.call("POST", "/invoices", {"customer": "Acme", "date": "2026-03-01", "lines": [
            {"description": "Consulting", "quantity": "2", "price": "100", "tax_code": "VAT20"}]})
        self.assertEqual((status, inv["status"], inv["total"]), (201, "draft", "240.00"))
        i = str(inv["id"])
        status, inv = self.call("POST", f"/invoices/{i}/issue")
        self.assertEqual((status, inv["number"]), (200, "INV-2026-0001"))
        status, inv = self.call("POST", f"/invoices/{i}/payments",
                                {"amount": "40", "date": "2026-03-05", "account": "Assets:Bank"})
        self.assertEqual((status, inv["status"], inv["balance"]), (200, "partial", "200.00"))
        self.assertEqual(self.call("POST", f"/invoices/{i}/payments",
                                   {"amount": "999", "date": "2026-03-05", "account": "Assets:Bank"})[0], 400)
        self.assertEqual(self.get(f"/invoices/{i}"), (200, self.js("invoice", "show", i)))
        self.assertEqual(self.get("/invoices"), (200, self.js("invoice", "list")))
        self.assertEqual(self.get("/reports/aging?at=2026-05-01"), (200, self.js("report", "aging", "--at", "2026-05-01")))
        self.assertEqual(self.get("/reports/aging?at=2026-05-01&payables=1"),
                         (200, self.js("report", "aging", "--at", "2026-05-01", "--payables")))
        self.assertEqual(self.get("/audit"), (200, self.js("audit", "list")))


if __name__ == "__main__":
    unittest.main()
