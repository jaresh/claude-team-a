"""Hidden acceptance tests for the finance benchmark (v1). Never shown to the model.

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
        self.ok("init", "--currency", "EUR")

    def tearDown(self):
        self.tmp.cleanup()

    def run_fin(self, *args):
        return subprocess.run([sys.executable, "-m", "fin", "--db", self.db, "--json", *args],
                              cwd=FIN, capture_output=True, text=True, timeout=60)

    def ok(self, *args):
        r = self.run_fin(*args)
        self.assertEqual(r.returncode, 0, f"{args}: exit {r.returncode}: {r.stderr[-500:]}")
        try:
            return json.loads(r.stdout) if r.stdout.strip() else None
        except ValueError:
            return None

    def js(self, *args):
        r = self.run_fin(*args)
        self.assertEqual(r.returncode, 0, f"{args}: exit {r.returncode}: {r.stderr[-500:]}")
        return json.loads(r.stdout)

    def user_error(self, *args):
        r = self.run_fin(*args)
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
        self.user_error("init", "--currency", "EUR")

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


class TestApi(Ledger):
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

    def call(self, method, path, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
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


if __name__ == "__main__":
    unittest.main()
