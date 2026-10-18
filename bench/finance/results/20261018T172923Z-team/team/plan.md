# Plan

## Goal

Small-business finance system `fin/` (stdlib only, Python 3.12+), CLI `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...` plus HTTP API `serve`. The full spec is `.claude/team/spec.md` (the user's request, verbatim). Every section of the spec is authoritative; when this plan and the spec differ, the spec wins.

**Check:** `python -m unittest discover -s tests` (run from the repo root) passes.

Per-task done checks are the task's own unit tests (`python -m unittest discover -s tests -p 'test_<module>.py'`), plus the acceptance tests `tests/test_acceptance.py` once the wave they depend on has merged.

## Assumptions (lead decisions; teammates follow these, README repeats them)

- Without `--json`, output is the same JSON document, indented (2 spaces). With `--json` it is compact, one line. Both print exactly one document to stdout on success.
- Handlers return a JSON-serializable object; the CLI prints it. Errors raise `core.FinError` → exit 2, message on stderr, nothing on stdout; the whole command runs in one SQLite transaction and is rolled back on error.
- Money is `Decimal`, quantized to cents with ROUND_HALF_UP. Posting amounts must have at most 2 decimals (more is a user error). Invoice `quantity`, `price`-derived net and rates are parsed as decimals; net/tax are rounded to cents.
- Convert: each amount is converted and rounded to cents, then summed (statements/reports).
- Dates are ISO strings in the DB (`YYYY-MM-DD`); months `YYYY-MM`.
- Recurring occurrences are stored in `recurring_occurrences` so re-running creates nothing new.
- `serve` runs a single-threaded `http.server.HTTPServer`; each request runs the CLI in-process via `fin.cli.main(argv, out, err)` with a fresh connection. The API maps requests to CLI argv; 401/403 are decided in the server by checking the `users` table.
- Import splits on `,`; no quoting beyond what `csv` module handles (use `csv` module).
- `invoice create --line` and `bill create --line` split on `;`; descriptions with `;` are not supported through the API body (documented).

## Contract

### Package layout (created by `core`, stubs first)

- `fin/__init__.py` — empty.
- `fin/__main__.py` — `from fin.cli import main; import sys; sys.exit(main(sys.argv[1:]))`.
- `fin/core.py` — shared code (owned by `core`). Public API below.
- `fin/cli.py` — argparse wiring and dispatch (owned by `core`).
- Command modules, each a stub `def register(commands, reports): pass` created by `core`, then owned by one task:
  - `fin/txn.py` — `ledger`: `txn add`, `txn list`, `balance`, `fx add`, `convert`.
  - `fin/statements.py` — `statements`: `report income`, `report balance-sheet`, `report networth`, `report trial-balance`, `report ledger`.
  - `fin/imports.py` — `imports`: `rule add`, `rule list`, `import`.
  - `fin/planning.py` — `planning`: `recurring add`, `recurring run`, `budget set`, `report budget`.
  - `fin/loans.py` — `loans`: `loan schedule`.
  - `fin/reconcile.py` — `reconcile`: `reconcile`.
  - `fin/invoices.py` — `invoices`: `tax add`, `tax list`, `customer add`, `customer list`, `invoice create|issue|pay|show|list`, `report aging` (both `--payables` off and on), `report tax`.
  - `fin/bills.py` — `bills`: `vendor add`, `vendor list`, `bill create|pay|show|list`.
  - `fin/server.py` — `api` (wave 2): `serve` and the HTTP handler. `serve` registers through `register(commands, reports)` too.
  - `fin/core.py` `init`, `user add`, `user list`, `account add`, `account list`, `audit list`, `period close`, `period status` are registered by `core` itself in `cli.py`.

### Command registration

`cli.py` builds the parser:
- Global options: `--db PATH` (default `./fin.db`), `--json`, `--user NAME`, before the command.
- `commands = parser.add_subparsers(dest="command", required=True)` — each module adds its command with `commands.add_parser(...)`.
- `reports = commands.add_parser("report").add_subparsers(dest="report", required=True)` — `register` receives this too; modules add `reports.add_parser("income", ...)` etc. Nested groups: `txn`, `rule`, `recurring`, `budget`, `loan`, `fx`, `tax`, `customer`, `invoice`, `vendor`, `bill`, `user`, `account`, `audit`, `period` — each group parser is created by the module that owns it (`commands.add_parser("txn").add_subparsers(dest="sub", required=True)`). `core` owns `user`, `account`, `audit`, `period`.
- Each leaf subparser calls `p.set_defaults(handler=func, write=BOOL, admin=BOOL)`:
  - `write=True` for commands that change data (they need `--user`, the user must exist, and the role must not be `viewer`).
  - `admin=True` only for `user add` and `period close`.
  - `handler(args, ctx) -> object` where `ctx` is `core.Context` with `.conn`, `.user` (name or None), `.role` (or None), `.json` (bool).
- Audit: a write handler calls `core.audit(ctx, action, target)` itself, after its changes succeed. Target is a string.
- `cli.main(argv, out=None, err=None) -> int`: `out`/`err` default to `sys.stdout`/`sys.stderr`; returns 0 or 2. Opens the DB (`--db`), runs the handler inside `with conn:` (commit on success, rollback on FinError or any exception), prints JSON to `out`.
- `init` is special: it requires no `--user` and must not exist yet (`core.open_db(path, create=True)`).
- Non-init commands on a missing DB file → FinError "no book at PATH, run init".

### core.py public API (owned by `core`; other tasks import these, never re-implement them)

```
class FinError(Exception)                       # user error -> exit 2
class Context: conn, user, role, json
def money(text) -> Decimal                      # strict: decimal, <= 2 decimal places, else FinError
def decimal_arg(text) -> Decimal                # strict decimal (quantity, price, rate, percent)
def cents(d) -> Decimal                         # quantize ROUND_HALF_UP to 0.01
def fmt(d) -> str                               # two decimals, "-12.50", zero -> "0.00", never "-0.00"
def parse_date(text) -> datetime.date           # strict YYYY-MM-DD
def parse_month(text) -> (int year, int month)  # strict YYYY-MM
def fmt_date(d) -> str                          # ISO
def add_months(d, n) -> date                    # keeps day, last day of shorter months
def book_currency(conn) -> str
def open_db(path, create=False) -> sqlite3.Connection   # FK on, Row factory; FinError if missing/exists per create
def account_type(name) -> str                   # 'asset'|'liability'|'equity'|'income'|'expense'; FinError otherwise
def ensure_account(conn, name, currency=None) -> None   # creates missing parents too (same currency); no-op if exists
def account_exists(conn, name) -> bool
def parse_posting(text) -> (account, Decimal|None)     # "ACCOUNT=AMOUNT" or "ACCOUNT"
def resolve_postings(conn, postings) -> list[(account, Decimal, currency)]
    # postings: list of (account, Decimal|None). >=2 postings; unknown account -> FinError;
    # at most one None -> balances its currency; per-currency sums must be 0 else FinError.
def post_transaction(conn, date, description, postings) -> int   # validates via resolve_postings, checks closed period, inserts txn+postings, returns id
def check_open(conn, date) -> None              # FinError if date's month <= closed_through
def closed_through(conn) -> str|None            # 'YYYY-MM' or None
def close_period(conn, month) -> None           # never moves backwards
def get_rate(conn, on, frm, to) -> Decimal|None # most recent fx row on/before 'on': direct, else 1/inverse; None if none
def convert(conn, amount, frm, to, on) -> Decimal   # cents; same currency 1:1; FinError if no rate
def user_role(conn, name) -> str|None
def audit(ctx_or_conn, action, target) -> None  # inserts audit row with UTC ISO time, the acting user
def write_json(out, obj, pretty)                # used by cli
```

`post_transaction` inserts into `transactions(id, date, description)` and `postings(id, txn_id, seq, account, amount, currency, cleared)`. Amounts are stored as TEXT strings from `fmt`.

### Schema (created by `core` in `open_db(create=True)` — teammates never change it; if a task needs a column, it says so in its handoff and the lead adds it)

```
meta(key TEXT PRIMARY KEY, value TEXT)           -- 'currency', 'closed_through'
users(name TEXT PRIMARY KEY, role TEXT)
audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, user TEXT, action TEXT, target TEXT)
accounts(name TEXT PRIMARY KEY, type TEXT, currency TEXT)
transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, description TEXT)
postings(id INTEGER PRIMARY KEY AUTOINCREMENT, txn_id INTEGER, seq INTEGER, account TEXT, amount TEXT, currency TEXT, cleared INTEGER DEFAULT 0)
fx_rates(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, frm TEXT, tto TEXT, rate TEXT)
rules(id INTEGER PRIMARY KEY AUTOINCREMENT, pattern TEXT, account TEXT)
imported_rows(account TEXT, date TEXT, description TEXT, amount TEXT)
budgets(account TEXT, month TEXT, amount TEXT, PRIMARY KEY(account, month))
recurring(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, every TEXT, start TEXT, postings TEXT)   -- postings: JSON list of [account, amount_str]
recurring_occurrences(recurring_id INTEGER, date TEXT, txn_id INTEGER, PRIMARY KEY(recurring_id, date))
tax_codes(code TEXT PRIMARY KEY, rate TEXT)
customers(name TEXT PRIMARY KEY, terms INTEGER)
vendors(name TEXT PRIMARY KEY, terms INTEGER)
invoices(id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, customer TEXT, date TEXT, due TEXT, status TEXT, net TEXT, tax TEXT, total TEXT, txn_id INTEGER)
invoice_lines(invoice_id INTEGER, seq INTEGER, description TEXT, quantity TEXT, price TEXT, tax_code TEXT, net TEXT, tax TEXT, PRIMARY KEY(invoice_id, seq))
bills(id INTEGER PRIMARY KEY AUTOINCREMENT, vendor TEXT, ref TEXT, date TEXT, due TEXT, status TEXT, net TEXT, tax TEXT, total TEXT, txn_id INTEGER, UNIQUE(vendor, ref))
bill_lines(bill_id INTEGER, seq INTEGER, description TEXT, account TEXT, tax_code TEXT, net TEXT, tax TEXT, PRIMARY KEY(bill_id, seq))
payments(id INTEGER PRIMARY KEY AUTOINCREMENT, doc_kind TEXT, doc_id INTEGER, date TEXT, amount TEXT, account TEXT, txn_id INTEGER)   -- doc_kind 'invoice'|'bill'
```

Paid amount of an invoice/bill = sum of its `payments` rows (dated on or before the report date where relevant). `status` is stored: `draft|issued|partial|paid` for invoices, `open|partial|paid` for bills. `balance = total − paid`.

Money stored as TEXT (`fmt` output). Sums are done in Python with `Decimal`, never in SQL on TEXT.

### Shared rules every task follows

- Money only via `core.money`/`decimal_arg`/`cents`/`fmt`; dates only via `core.parse_date`/`fmt_date`; never `float`.
- Errors: `raise core.FinError("message")`. Never print to stdout yourself, never `sys.exit`.
- Write commands call `core.audit(ctx, action, target)` with the action/target exactly as spec §11.
- Handlers take `(args, ctx)` and return the spec's JSON object. Use `ctx.conn` only.
- Ids are `INTEGER PRIMARY KEY AUTOINCREMENT` and start at 1.
- Tests use `tempfile` DBs, created via `core.open_db(path, create=True)` and `core.cli.main([...], out=io.StringIO(), err=io.StringIO())`. Test files are named `tests/test_<module>.py`. Test helper functions must not be named `fail`, `assert*`, `setUp`, `run`, `skipTest`.
- Each module's register() adds only its own commands; never edit another task's module or `core.py` (except `core` itself). Need a change in core? Write the request in your handoff; the lead decides.

## Tasks

Wave 0 (in parallel): `core`, `acceptance`.
Wave 1 (in parallel, after wave 0 merged): `ledger`, `statements`, `imports`, `planning`, `loans`, `reconcile`, `invoices`, `bills`.
Wave 2: `api`.

## core

**Files owned:** `fin/__init__.py`, `fin/__main__.py`, `fin/core.py`, `fin/cli.py`, the stubs `fin/txn.py`, `fin/statements.py`, `fin/imports.py`, `fin/planning.py`, `fin/loans.py`, `fin/reconcile.py`, `fin/invoices.py`, `fin/bills.py`, `fin/server.py` (stub with `register` only), and `tests/test_core.py`.

**What to do:** implement everything in the Contract for `core.py` and `cli.py`, the schema, and the core commands: `init --currency CUR --admin NAME`, `user add NAME --role admin|editor|viewer` (admin), `user list`, `account add NAME [--currency CUR]`, `account list`, `audit list [--by NAME]`, `period close MONTH` (admin), `period status`. Global options and dispatch in `cli.py` exactly as the Contract says, including the `write`/`admin` checks. Write each stub module with `def register(commands, reports): pass` and a docstring naming the task that owns it. Tests in `tests/test_core.py` cover the core functions and these commands (including exit code 2 and no stdout on errors, the role checks, audit entries with `init` as seq 1, closed periods rejecting `post_transaction`).

**May change to make checks pass:** anything in the files it owns.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` passes, and `python -c "import fin.cli"` works.

**Must not touch:** any other file, including `tests/test_acceptance.py` and `README.md`.

## acceptance

**Files owned:** `tests/test_acceptance.py` only.

**What to do:** write black-box acceptance tests for every section of `.claude/team/spec.md` (sections 1–17, plus the API in section 10). Tests drive the real CLI as a subprocess: `[sys.executable, "-m", "fin", "--db", path, ...]` with `cwd` set to the repo root (derive it from `__file__`). Use a temp DB per test (`tempfile.TemporaryDirectory`). Parse the JSON from stdout (`--json`) and check exact values from the spec's examples and rules (rounding, month-end recurrence, convert, balance, aging buckets, loan schedule final balance 0.00, reconcile, tax report, closed periods, permissions, exit codes). Also cover the HTTP API: start `python -m fin --db PATH serve --port N` as a subprocess on a free port, wait until it answers, then test the routes listed in §10, the 201/400/401/403/404 codes, and stop the process afterwards. Tests must fail now (no code yet) — run them once and confirm the failures are import/command errors, not test-file errors. Keep each test independent.

Use the spec's own examples as expected values. Where the spec is silent, use the Assumptions in this plan (JSON pretty or compact does not matter because we parse).

**May change to make checks pass:** only `tests/test_acceptance.py`. Teammates never edit it; if a test is wrong against the spec, the lead decides.

**Done check:** `python -m py_compile tests/test_acceptance.py` passes, and the file has at least 60 test methods (`grep -c 'def test_' tests/test_acceptance.py`).

**Must not touch:** anything but `tests/test_acceptance.py`.

## ledger

**Files owned:** `fin/txn.py`, `tests/test_txn.py`.

**What to do:** implement `txn add`, `txn list` (group `txn`), `balance`, `fx add`, `convert` per spec §2, §3, §4, using `core.post_transaction`, `core.resolve_postings`, `core.parse_posting`, `core.convert`, `core.get_rate`, `core.audit` (`txn.add` with the id as target, `fx.add` with `FROM/TO`). `balance` and `txn list` are read commands (no `--user`). `convert` is read-only. Tests in `tests/test_txn.py` must cover the spec examples and error cases (unbalanced, unknown account, closed month, missing rate, same currency).

**May change to make checks pass:** `fin/txn.py` and `tests/test_txn.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_txn.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## statements

**Files owned:** `fin/statements.py`, `tests/test_statements.py`.

**What to do:** implement `report income`, `report balance-sheet`, `report networth`, `report trial-balance`, `report ledger` per spec §8, §17 (and the networth/income rules there), using `core.convert`, `core.fmt`, `core.cents`. Read-only; no `--user`. Tests create data through `core.post_transaction` and `core.fx` rows (or `fx add` via `cli.main`). Cover the spec's rules: `--currency` conversion, retained earnings, `total_assets == total_liabilities + total_equity`, trial-balance totals equal, ledger opening/running balance/closing.

**May change to make checks pass:** `fin/statements.py`, `tests/test_statements.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_statements.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## imports

**Files owned:** `fin/imports.py`, `tests/test_imports.py`.

**What to do:** implement `rule add PATTERN ACCOUNT`, `rule list` (group `rule`), and `import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]` per spec §5. Rules: case-insensitive `re.search` on the description; first match wins. Import with `csv` module; skip the header row if `--skip-header`; dedupe by `imported_rows` (account, date, description, amount) including repeats in the same file; category accounts via `core.ensure_account` in the book currency; the whole import fails if any row is in a closed month (use `core.check_open` / `post_transaction`). Audit: `rule.add` (pattern), `import` (account). Tests cover matching, default categories, dedupe, skip counting, closed-month rollback, bad amounts.

**May change to make checks pass:** `fin/imports.py`, `tests/test_imports.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_imports.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## planning

**Files owned:** `fin/planning.py`, `tests/test_planning.py`.

**What to do:** implement `recurring add NAME --every monthly|weekly|yearly --start DATE --posting ...`, `recurring run --until DATE`, `budget set ACCOUNT MONTH AMOUNT`, `report budget MONTH` per spec §6, §7. Recurring stores postings as JSON `[[account, amount_str], ...]` (blank amount stored as null), checks them with `core.resolve_postings` when added; `recurring run` creates each missing occurrence through `core.post_transaction` with description NAME, records it in `recurring_occurrences`, and raises (closed period) through `core.check_open` for any occurrence dated in a closed month. Monthly/yearly use `core.add_months(start, n)`; weekly adds 7 days. Audit: `recurring.add` (name), `recurring.run` (the `--until` date), `budget.set` (`ACCOUNT MONTH`). `report budget` is read-only. Expense accounts only for budgets (error otherwise). Tests cover month-end rule, leap year yearly, idempotent runs, budget replace, actual/remaining.

**May change to make checks pass:** `fin/planning.py`, `tests/test_planning.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_planning.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## loans

**Files owned:** `fin/loans.py`, `tests/test_loans.py`.

**What to do:** implement `loan schedule PRINCIPAL RATE MONTHS --start DATE` per spec §9, read-only. Use `core.decimal_arg`, `core.money`-style rounding via `core.cents`, `core.add_months`. Use `Decimal` with enough precision (context prec 40) for the annuity formula, then round the payment to cents. The last row pays the remaining balance plus its interest. RATE 0 gives PRINCIPAL/MONTHS rounded. Tests: spec-like example (final balance `0.00`, row count = MONTHS, total_interest = sum of interest), zero rate, one month.

**May change to make checks pass:** `fin/loans.py`, `tests/test_loans.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_loans.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## reconcile

**Files owned:** `fin/reconcile.py`, `tests/test_reconcile.py`.

**What to do:** implement `reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID ...]` per spec §16. Validate each `--clear` id: a transaction with a posting to ACCOUNT dated on or before DATE, else FinError and nothing is marked (the whole command rolls back). Mark those postings `cleared=1`. Output per spec. Cleared is kept across runs. Audit: `reconcile` (the account). `--clear` may repeat (argparse `action="append"`). Tests: clearing, persistence across runs, difference, uncleared list ascending, invalid clear rolls back.

**May change to make checks pass:** `fin/reconcile.py`, `tests/test_reconcile.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_reconcile.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## invoices

**Files owned:** `fin/invoices.py`, `tests/test_invoices.py`.

**What to do:** implement `tax add CODE RATE`, `tax list`, `customer add NAME [--terms DAYS]`, `customer list`, `invoice create --customer NAME --date DATE --line "DESC;QTY;PRICE;TAXCODE" [--line ...]`, `invoice issue ID`, `invoice pay ID AMOUNT --date DATE --account ACCOUNT`, `invoice show ID`, `invoice list [--status STATUS]`, `report aging --at DATE [--payables]`, `report tax --from DATE --to DATE` per spec §13, §15 and the aging rules in §13. Numbering `INV-YYYY-NNNN` per year. `issue` posts via `core.post_transaction` (Assets:Receivable, Income:Sales, Liabilities:SalesTax if tax ≠ 0; accounts created via `core.ensure_account`). `pay` writes a `payments` row (doc_kind `invoice`) and posts. `report aging --payables` reads the `bills` and `payments` (doc_kind `bill`) tables directly; do not import `fin/bills.py`. `report tax` reads `invoices` (issued) and `bills`. Audit: `tax.add`, `customer.add`, `invoice.create`, `invoice.issue`, `invoice.pay` (targets per §11). Tests: rounding of line net/tax, due date from terms, numbering, status transitions, overpayment error, aging buckets, tax report by_code.

**May change to make checks pass:** `fin/invoices.py`, `tests/test_invoices.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_invoices.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## bills

**Files owned:** `fin/bills.py`, `tests/test_bills.py`.

**What to do:** implement `vendor add NAME [--terms DAYS]`, `vendor list`, `bill create --vendor NAME --ref TEXT --date DATE --line "DESC;AMOUNT;ACCOUNT;TAXCODE" [--line ...]`, `bill pay ID AMOUNT --date DATE --account ACCOUNT`, `bill show ID`, `bill list [--status STATUS]` per spec §14. The bill posts at once: each line ACCOUNT +net (`core.ensure_account` for missing accounts), `Assets:TaxReceivable` +tax if not zero, `Liabilities:Payable` −total. Duplicate `(vendor, ref)` is a user error. `pay` writes a `payments` row (doc_kind `bill`) and posts `Liabilities:Payable` +AMOUNT, ACCOUNT −AMOUNT. Line ACCOUNT must exist and be an expense or asset account. Audit: `vendor.add`, `bill.create`, `bill.pay` (target id). Tests: rounding, unique ref, account type check, status transitions, closed period, overpayment.

**May change to make checks pass:** `fin/bills.py`, `tests/test_bills.py`.

**Done check:** `python -m unittest discover -s tests -p 'test_core.py'` and `python -m unittest discover -s tests -p 'test_bills.py'` both pass.

**Must not touch:** other modules, `core.py`, `cli.py`, the schema.

## api

**Files owned:** `fin/server.py`, `tests/test_server.py`, `README.md`.

**What to do:** implement `serve --port N` (group-less command, registered through `register`) and the routes of spec §10 as a single-threaded `http.server.HTTPServer`. Each request runs `fin.cli.main([...], out, err)` in-process with `--db` and, for POST, `--user` from `X-User`. Map GET routes to commands: `/accounts` → `account list`, `/transactions` → `txn list` (with `--account/--from/--to` from the query string if present), `/balances?at` → `balance --at`, `/reports/income?from&to` → `report income`, `/reports/balance-sheet?at` → `report balance-sheet --at`, `/invoices` → `invoice list`, `/invoices/ID` → `invoice show ID`, `/reports/aging?at[&payables=1]` → `report aging --at D [--payables]`, `/audit` → `audit list`. POST routes: `/transactions` (body → `txn add`), `/invoices` (→ `invoice create`, `lines` → `--line "d;q;p;t"`), `/invoices/ID/issue`, `/invoices/ID/payments` (→ `invoice pay`). Status codes: success 200 (201 for POST create), FinError → 400 `{"error": msg}`, missing/unknown user on POST → 401, viewer → 403 (decide by reading `users` with `core.user_role`/`core.open_db`), unknown path → 404; both error bodies are `{"error": "..."}`. Parse the stdout JSON and write it. Write the README: how to use the system (init, commands, API, tests), and the Assumptions section: include `.claude/team/plan.md` assumptions and every "Assumption" line in `.claude/team/handoff/*.txt` (read them with `grep -h`). Tests: `tests/test_server.py` starts the server on a free port in a thread with its own DB and checks routes and codes. Keep tests quick.

**May change to make checks pass:** `fin/server.py`, `tests/test_server.py`, `README.md`.

**Done check:** `python -m unittest discover -s tests -p 'test_server.py'` passes, and `python -m unittest discover -s tests` is run once with its result recorded in your handoff (failures are fine to report, not to fix elsewhere).

**Must not touch:** other modules, `core.py`, `cli.py`, `tests/test_acceptance.py`.
