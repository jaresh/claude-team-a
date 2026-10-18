# Plan

Full request: `.claude/team/spec.md` (read the section of your task there, word for word; it is
the authority for behaviour). This plan adds the shared contract, conventions and file ownership.

## Goal

Stdlib-only Python 3.12+ finance CLI + HTTP API in package `fin/`, tests in `tests/`, `README.md`.
Run as `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...` from the repo root.

## Check

`python -m unittest discover -s tests` (the whole suite) passes.

Each task's done check is its own test file: `python -m unittest discover -s tests -p 'test_<task>.py'`.

## Conventions (shared code; teammates import it and never write their own copy)

- Money: `fin/money.py`. Amounts are `Decimal`, never float.
  - `parse(text) -> Decimal`: strict decimal string, else `UserError`.
  - `parse_amount(text) -> Decimal`: like `parse` but at most 2 decimals, else `UserError`.
  - `cents(d) -> Decimal`: quantize to 0.01, ROUND_HALF_UP.
  - `fmt(d) -> str`: `cents(d)` as a 2-decimal string; never `-0.00` (zero is `0.00`).
  - `db_text(d) -> str`: the value stored in SQLite TEXT columns: `format(d, 'f')` of the exact value (amounts are stored as `fmt(d)`).
  - Sums are done in Python over Decimal values, never with SQL `SUM` on TEXT.
- Dates: `fin/dates.py`. Dates are `datetime.date`; stored and shown as `YYYY-MM-DD`.
  - `parse_date(text) -> date` strict, else `UserError`. `iso(d) -> str`.
  - `parse_month(text) -> str` returns `YYYY-MM` strictly validated, else `UserError`. `month_range(month) -> (first_date, last_date)`.
  - `add_months(d, n) -> date` from the start date `d` plus `n` months, clamped to month end (use it with `n*k` from the start, never chained).
  - `add_days(d, n) -> date`. `last_day(year, month) -> date`.
- Errors: `fin/errors.py`:
  - `class UserError(Exception)`: user error, CLI exit 2.
  - `class Unauthorized(UserError)` (`status = 401`): missing or unknown `--user` / `X-User`.
  - `class Forbidden(UserError)` (`status = 403`): role may not run the action.
  - Other `UserError`s map to HTTP 400.
- Accounts: `fin/accounts.py` (owned by core):
  - `TYPES = {"Assets": "asset", "Liabilities": "liability", "Equity": "equity", "Income": "income", "Expenses": "expense"}`.
  - `account_type(name) -> str` (UserError on an unknown first segment), `parent_names(name) -> list[str]` (ancestors, shortest first), `get_account(conn, name) -> dict` (`{"name","type","currency"}`, UserError `unknown account: NAME`), `ensure_account(conn, name, currency) -> dict` (creates it and missing ancestors with that currency; returns the account; used for accounts the spec says to create if missing).
  - `is_descendant_or_self(account, prefix) -> bool`. Name matching for prefix filters is `account == p or account.startswith(p + ":")`.
- Periods: `fin/periods.py` (owned by core): `closed_through(conn) -> str | None`; `check_open(conn, date)`: UserError `period closed: MONTH` if the date's month is `<= closed_through`.
- Audit: `fin/audit.py` (owned by core): `record(conn, user, action, target)` appends one row, `at` = UTC now as `%Y-%m-%dT%H:%M:%SZ`.
  - Rule: a command appends an audit entry only when it actually changed a row (a no-op like closing an earlier month, `recurring run` creating nothing, or `reconcile` with no `--clear` appends nothing).
- Database: `fin/db.py` (owned by core): `connect(path) -> sqlite3.Connection`, `init_schema(conn)`, and `SCHEMA` (the exact DDL below). Other tasks never change the schema. If you need a column, say so in your handoff and the lead decides.
- Book metadata: the `meta` table: keys `currency` (book currency) and `closed_through` (may be absent).
- Output: a command returns a JSON-able object (dict, list). Strings for all amounts. The CLI prints it (indent 2, or compact with `--json`), with a trailing newline. A handler that returns `None` prints nothing (used by `serve`).
- Command modules: each `fin/<module>.py` has `register(root, groups)` where `root` is the top-level argparse subparsers and `groups` maps group names (`account`, `txn`, `fx`, `rule`, `budget`, `recurring`, `report`, `loan`, `user`, `audit`, `period`, `tax`, `customer`, `vendor`, `invoice`, `bill`) to their subparsers. Top-level commands (`init`, `convert`, `balance`, `import`, `reconcile`, `serve`) use `root.add_parser`. Each command calls `p.set_defaults(func=handler)` with `handler(ctx, args) -> object`.
- Context (`fin/cli.py`, owned by core): `ctx.conn`, `ctx.user` (name or None), `ctx.role` (or None), `ctx.json` (bool), `ctx.authorize(action)` (raises Unauthorized or Forbidden; actions are the audit action names, e.g. `txn.add`), `ctx.audit(action, target)`, `ctx.book_currency() -> str`.
  - `authorize` is also available as module function `fin.cli.check_access(conn, user, action)` for the API.
  - Roles: `user.add` and `period.close` need admin; other changing actions need admin or editor; viewer may only read. Read-only handlers do not call `authorize`.
- CLI runner: `fin.cli.main(argv, out=None, err=None) -> int`. It prints the result to `out` and error messages to `err`, returns 0 or 2, never raises `SystemExit`. Non-init commands on a missing DB file are a user error. Each handler runs inside `with conn:` (rollback on any exception). Unexpected exceptions propagate.
- Command module list (fixed, in `fin/cli.py`; core creates a stub with `def register(root, groups): pass` for each module that isn't written yet): `fin.books`, `fin.users`, `fin.accounts`, `fin.audit`, `fin.periods`, `fin.txns`, `fin.balances`, `fin.fx`, `fin.loans`, `fin.parties`, `fin.tax`, `fin.invoices`, `fin.aging`, `fin.bills`, `fin.imports`, `fin.recurring`, `fin.budgets`, `fin.reports`, `fin.reconcile`, `fin.api`. Non-command helper modules: `fin.documents`.
- Money helpers for JSON docs: report fields use `fmt`, dates `iso`.
- Tests: `tests/support.py` (owned by core):
  - `new_db(currency="EUR", admin="admin") -> str`: fresh temp DB path, already initialised.
  - `run(db, *argv) -> (code, out, err)`: runs `main(["--db", db, "--json", *argv])`; pass `--user NAME` as part of argv, before the command.
  - `ok(db, *argv) -> object`: asserts code 0 and empty err, returns `json.loads(out)`.
  - `expect_error(db, *argv) -> str`: asserts code 2 and empty out, returns err.
  - Test files are `tests/test_<task>.py`, `import support`, and are run with `discover -s tests`. Helper names must not be framework method names.

## Contract: schema (exact DDL, `fin/db.py` `SCHEMA`)

```sql
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE users (name TEXT PRIMARY KEY, role TEXT NOT NULL);
CREATE TABLE audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, user TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL);
CREATE TABLE accounts (name TEXT PRIMARY KEY, type TEXT NOT NULL, currency TEXT NOT NULL);
CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE postings (id INTEGER PRIMARY KEY AUTOINCREMENT, txn_id INTEGER NOT NULL REFERENCES transactions(id), seq INTEGER NOT NULL, account TEXT NOT NULL REFERENCES accounts(name), amount TEXT NOT NULL, currency TEXT NOT NULL, cleared INTEGER NOT NULL DEFAULT 0);
CREATE INDEX postings_account ON postings(account);
CREATE TABLE fx_rates (date TEXT NOT NULL, from_cur TEXT NOT NULL, to_cur TEXT NOT NULL, rate TEXT NOT NULL, PRIMARY KEY (date, from_cur, to_cur));
CREATE TABLE rules (seq INTEGER PRIMARY KEY AUTOINCREMENT, pattern TEXT NOT NULL, account TEXT NOT NULL);
CREATE TABLE imported_rows (account TEXT NOT NULL, date TEXT NOT NULL, description TEXT NOT NULL, amount TEXT NOT NULL, txn_id INTEGER NOT NULL);
CREATE TABLE budgets (account TEXT NOT NULL, month TEXT NOT NULL, amount TEXT NOT NULL, PRIMARY KEY (account, month));
CREATE TABLE recurring (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, every TEXT NOT NULL, start TEXT NOT NULL, postings TEXT NOT NULL);
CREATE TABLE recurring_runs (recurring_id INTEGER NOT NULL, occurrence TEXT NOT NULL, txn_id INTEGER NOT NULL, PRIMARY KEY (recurring_id, occurrence));
CREATE TABLE tax_codes (code TEXT PRIMARY KEY, rate TEXT NOT NULL);
CREATE TABLE customers (name TEXT PRIMARY KEY, terms INTEGER NOT NULL);
CREATE TABLE vendors (name TEXT PRIMARY KEY, terms INTEGER NOT NULL);
CREATE TABLE invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT UNIQUE, customer TEXT NOT NULL, date TEXT NOT NULL, due TEXT NOT NULL, status TEXT NOT NULL, txn_id INTEGER);
CREATE TABLE invoice_lines (doc_id INTEGER NOT NULL, seq INTEGER NOT NULL, description TEXT NOT NULL, quantity TEXT NOT NULL, price TEXT NOT NULL, tax_code TEXT, net TEXT NOT NULL, tax TEXT NOT NULL, PRIMARY KEY (doc_id, seq));
CREATE TABLE bills (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor TEXT NOT NULL, ref TEXT NOT NULL, date TEXT NOT NULL, due TEXT NOT NULL, status TEXT NOT NULL, txn_id INTEGER, UNIQUE (vendor, ref));
CREATE TABLE bill_lines (doc_id INTEGER NOT NULL, seq INTEGER NOT NULL, description TEXT NOT NULL, account TEXT NOT NULL, tax_code TEXT, net TEXT NOT NULL, tax TEXT NOT NULL, PRIMARY KEY (doc_id, seq));
CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, doc_id INTEGER NOT NULL, date TEXT NOT NULL, amount TEXT NOT NULL, account TEXT NOT NULL, txn_id INTEGER NOT NULL);
```

`kind` in `payments` is `'invoice'` or `'bill'`. Invoice and bill `status` values are `draft`, `issued`, `partial`, `paid` (bills are created `open`, see the spec). `recurring.every` is `monthly`, `weekly` or `yearly`. `recurring.postings` is JSON: a list of `[account, amount_or_null]`, amounts as `fmt` strings. `txn_id` is the transaction created by issue/create.

## Contract: ledger, fx, documents (cross-task code)

- `fin/txns.py` (ledger):
  - `parse_posting_arg(text) -> (account, Decimal | None)` for `ACCOUNT=AMOUNT` or `ACCOUNT`.
  - `check_postings(conn, postings) -> list[(account, currency, Decimal)]`: `postings` is a list of `(account, Decimal | None)`. Validates (2+ postings, at most one `None`, accounts exist, per currency sums to zero after filling the `None`, the posting's currency is its account's currency), no write. UserError on problems.
  - `create_transaction(conn, date, description, postings) -> dict`: `check_postings` + `check_open` + insert; returns the transaction document (spec shape). No audit (the caller audits). Amounts stored as `fmt` strings.
  - `txn_doc(conn, txn_id) -> dict`: the transaction shape from the spec.
- `fin/balances.py` (ledger):
  - `raw_sums(conn, at=None, from_date=None, to_date=None) -> dict[str, dict[str, Decimal]]`: per posting account (exact name), per currency, the sum of postings with `date <= at` (if given), `date >= from_date`, `date <= to_date` (if given). Zero sums are kept.
  - `rollup(sums) -> dict[str, dict[str, Decimal]]`: adds each account's sums to every ancestor (e.g. `Assets:Bank` also goes to `Assets`); keys include ancestors.
  - `fin.balances.balance` command.
- `fin/fx.py` (fx):
  - `convert_amount(conn, amount: Decimal, frm, to, at) -> Decimal`: unrounded result. Same currency: amount. Otherwise the most recent direct `frm→to` rate on or before `at`; if none, `1 / (most recent to→frm rate on or before at)`. None: UserError `no exchange rate`.
- `fin/documents.py` (invoices, shared with bills):
  - `tax_rate(conn, code) -> Decimal` (UserError for an unknown code; defined in fin/tax.py, re-exported here).
  - `line_tax(net: Decimal, rate) -> Decimal`: `cents(net * rate / 100)`.
  - `document_totals(lines) -> (net, tax, total)` where each line is a dict with `net`, `tax` as Decimal.
  - `payments_total(conn, kind, doc_id) -> Decimal`; `apply_payment(conn, kind, doc_id, amount, date, account, doc_label, pay_description)`: validates the amount, the open period, the document status and balance, and the asset account; posts the transaction (invoice: account +amount, `Assets:Receivable` −amount; bill: `Liabilities:Payable` +amount, account −amount) via `create_transaction`; inserts a payments row; returns the new `paid`, `status`. The caller audits.
  - `status_for(total, paid, issued_status='issued')`: `paid` if balance zero, `partial` if `0 < paid`, else the issued status.
- `fin/parties.py` (parties): `customer_terms(conn, name) -> int`, `vendor_terms(conn, name) -> int` (UserError for unknown).
- `fin/tax.py` (parties): `tax_rate(conn, code) -> Decimal`.

## Waves

- Wave 1: `core`.
- Wave 2: `ledger`, `fx`, `loans`, `parties`.
- Wave 3: `invoices`.
- Wave 4: `bills`, `imports`, `recurring`, `budgets`.
- Wave 5: `reports`, `reconcile`.
- Wave 6: `api`.
- Wave 7: `readme`.

## Shared decisions (apply to every task)

- Human (non-`--json`) output is the same document, indented 2. A list or dict command prints once.
- Account names: non-empty colon-separated segments; the first segment sets the type.
- Book currency codes: 3 ASCII letters, stored uppercase.
- Accounts are never created by transactions or imports, except where the spec says "created if missing" (`Expenses:Uncategorized`, `Income:Uncategorized`, `Income:Sales`, `Liabilities:SalesTax`, `Assets:TaxReceivable`, `Liabilities:Payable`, `Assets:Receivable`). Those are created in the book currency via `ensure_account`.
- Audit rule: see Conventions.
- Every task writes its own unit tests in `tests/test_<task>.py` using `support`.

## core

Files you own: `fin/__init__.py`, `fin/__main__.py`, `fin/cli.py`, `fin/errors.py`, `fin/money.py`, `fin/dates.py`, `fin/db.py`, `fin/books.py`, `fin/users.py`, `fin/audit.py`, `fin/accounts.py`, `fin/periods.py`, stub files for every other module in the module list (`fin/txns.py`, `fin/balances.py`, `fin/fx.py`, `fin/loans.py`, `fin/parties.py`, `fin/tax.py`, `fin/invoices.py`, `fin/aging.py`, `fin/bills.py`, `fin/imports.py`, `fin/recurring.py`, `fin/budgets.py`, `fin/reports.py`, `fin/reconcile.py`, `fin/api.py`, `fin/documents.py`), `tests/__init__.py` is not needed, `tests/support.py`, `tests/test_core.py`.

Build: everything in the Conventions and Contract sections that is not owned by another task, plus:
- `fin/cli.py`: parser (global `--db` default `./fin.db`, `--json`, `--user`), the `groups` dict, the `Context`, `check_access`, `main`, and the list of command modules imported in order.
- `fin/books.py`: `init --currency CUR --admin NAME`.
- `fin/users.py`: `user add NAME --role admin|editor|viewer`, `user list`.
- `fin/audit.py`: `audit list [--by NAME]`.
- `fin/accounts.py`: `account add NAME [--currency CUR]`, `account list`.
- `fin/periods.py`: `period close MONTH`, `period status`.

Test: `tests/test_core.py` covers the commands above and the CLI conventions (exit codes, `--json`, roles, audit entries, unknown users, missing DB, `money` and `dates` helpers, `add_months` clamping). `tests/support.py` as in Conventions.

Done check: `python -m unittest discover -s tests -p 'test_core.py'`.
Must not touch: anything in `fin/` owned by other tasks other than the stubs listed.

Note for stubs: a stub module contains a one-line docstring and `def register(root, groups): pass`. Other tasks replace the whole file.

## ledger

Files you own: `fin/txns.py`, `fin/balances.py`, `tests/test_ledger.py`.

Build: the ledger contract in Contract above (`parse_posting_arg`, `check_postings`, `create_transaction`, `txn_doc`, `raw_sums`, `rollup`), and the commands `txn add`, `txn list [--account PREFIX] [--from DATE] [--to DATE]` (spec section 2), `balance [--at DATE]` (spec section 3). `txn add` audits `txn.add` with the id as target. `txn add` checks `check_open` through `create_transaction`.

Done check: `python -m unittest discover -s tests -p 'test_ledger.py'`.
Must not touch: `fin/money.py`, `fin/dates.py`, `fin/db.py`, `fin/cli.py`, `fin/accounts.py`, `fin/periods.py`, other modules. If you need a helper from core that doesn't exist, write it inside your own file and say so in the handoff.

## fx

Files you own: `fin/fx.py`, `tests/test_fx.py`.

Build: `fx add DATE FROM TO RATE` (spec section 4): RATE strict decimal, positive; stores `format(rate, 'f')`; a repeated date/pair replaces. Audits `fx.add` with `FROM/TO`. `convert AMOUNT FROM TO --at DATE` prints `{"amount": fmt, "currency": TO}`. Currency codes validated; `convert_amount` as in Contract. The convert command is top-level (`root.add_parser`).

Done check: `python -m unittest discover -s tests -p 'test_fx.py'`.
Must not touch: other tasks' files.

## loans

Files you own: `fin/loans.py`, `tests/test_loans.py`.

Build: `loan schedule PRINCIPAL RATE MONTHS --start DATE` (spec section 9), a pure function `schedule(principal, rate, months, start) -> dict` plus the command. Validate: principal > 0, MONTHS ≥ 1, RATE ≥ 0. Rates and principal strict decimals. Use `money.cents` and the Decimal exponent-based payment formula with a context precision high enough (use `decimal.localcontext` with prec 50). Row dates via `dates.add_months(start, n)`.

Done check: `python -m unittest discover -s tests -p 'test_loans.py'`.
Must not touch: other tasks' files. It is a read-only command: no `authorize`, no audit.

## parties

Files you own: `fin/parties.py`, `fin/tax.py`, `tests/test_parties.py`.

Build: `customer add NAME [--terms DAYS]` (default 30), `customer list`, `vendor add NAME [--terms DAYS]`, `vendor list` (spec section 14, 13). `tax add CODE RATE`, `tax list` (spec section 13, rates shown as given, so store the string as given after validating it is a decimal). `customer_terms`, `vendor_terms`, `tax_rate` helpers as in Contract. Duplicate names are user errors. `--terms` must be a non-negative integer. Audits `customer.add`, `vendor.add`, `tax.add`.

Done check: `python -m unittest discover -s tests -p 'test_parties.py'`.
Must not touch: other tasks' files.

## invoices

Files you own: `fin/documents.py`, `fin/invoices.py`, `fin/aging.py`, `tests/test_invoices.py`.

Build: the documents contract in Contract (`line_tax`, `document_totals`, `payments_total`, `apply_payment`, `status_for`), `invoice create`, `invoice issue ID`, `invoice pay ID AMOUNT --date DATE --account ACCOUNT`, `invoice show ID`, `invoice list [--status STATUS]` (spec section 13), `report aging --at DATE [--payables]` (spec section 13 and 14; `--payables` reads `bills` and `payments` with kind `'bill'` via SQL, since the schema is fixed). Numbering: count of issued invoices with the same year's `INV-YYYY-` prefix plus one, zero-padded to 4 digits. Invoice doc shape as in spec section 13; invoice totals from lines. Audits: `invoice.create` (id), `invoice.issue` (id), `invoice.pay` (id). Pay validation: draft, paid, or amount above balance is a user error; the account must be an asset account that exists.

Done check: `python -m unittest discover -s tests -p 'test_invoices.py'`.
Must not touch: other tasks' files, `fin/tax.py` and `fin/parties.py` (use their helpers).

## bills

Files you own: `fin/bills.py`, `tests/test_bills.py`.

Build: `vendor` is owned by `parties`; use `vendor_terms`. Commands `bill create --vendor NAME --ref TEXT --date DATE --line "DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE" [--line ...]`, `bill pay ID AMOUNT --date DATE --account ACCOUNT`, `bill show ID`, `bill list [--status STATUS]` (spec section 14). Use `documents` helpers (owned by invoices, in fin/documents.py). The bill is posted at once; status `open` at creation, then `partial`/`paid` via `apply_payment`. Duplicate `(vendor, ref)` is a user error. Audits: `bill.create` (id), `bill.pay` (id). The report aging `--payables` is owned by invoices in `fin/aging.py`, so do not change it.

Done check: `python -m unittest discover -s tests -p 'test_bills.py'`.
Must not touch: other tasks' files.

## imports

Files you own: `fin/imports.py`, `tests/test_imports.py`.

Build: `rule add PATTERN ACCOUNT`, `rule list` (spec section 5; validate the regex with `re.compile`, the account must exist; audit `rule.add`), and the top-level `import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]` command. Decisions for you to follow: rule accounts and the import ACCOUNT must exist and be in the book currency (else a user error); `Expenses:Uncategorized` / `Income:Uncategorized` are created with `ensure_account`; rows are validated before anything is written; a whole import fails (nothing written) on any bad row or closed-period row. Create transactions through `txns.create_transaction`, and record each row in `imported_rows`. Audit `import` (the ACCOUNT) only if at least one row was imported.

Done check: `python -m unittest discover -s tests -p 'test_imports.py'`.
Must not touch: other tasks' files.

## recurring

Files you own: `fin/recurring.py`, `tests/test_recurring.py`.

Build: `recurring add NAME --every monthly|weekly|yearly --start DATE --posting ACCOUNT=AMOUNT [...]` (validate with `txns.check_postings`, store JSON in `recurring.postings`), `recurring run --until DATE` (spec section 7). Occurrences: monthly `add_months(start, n)`, weekly `add_days(start, 7n)`, yearly `add_months(start, 12n)`, for n = 0, 1, 2, … while the date is `<= until`. Skip occurrences already in `recurring_runs`. Created via `create_transaction` with description NAME. `check_open` applies (a closed occurrence fails the whole run). Recurring names need not be unique: say so in your handoff. Audit `recurring.add` (name) and `recurring.run` (the until date) only if something changed.

Done check: `python -m unittest discover -s tests -p 'test_recurring.py'`.
Must not touch: other tasks' files.

## budgets

Files you own: `fin/budgets.py`, `tests/test_budgets.py`.

Build: `budget set ACCOUNT MONTH AMOUNT` (the account must exist and be an expense account; replaces an existing budget; audit `budget.set` with `ACCOUNT MONTH`), and `report budget MONTH` (spec section 6). For `report budget` use `balances.raw_sums` with the month's range and `balances.rollup`; `actual` is the account's own currency sum (raw, expenses positive); `remaining = budget − actual`. Register the `report budget` subcommand in `groups["report"]`.

Done check: `python -m unittest discover -s tests -p 'test_budgets.py'`.
Must not touch: other tasks' files.

## reports

Files you own: `fin/reports.py`, `tests/test_reports.py`.

Build: `report income --from DATE --to DATE [--currency CUR]`, `report balance-sheet --at DATE [--currency CUR]`, `report networth --from MONTH --to MONTH`, `report trial-balance --at DATE`, `report ledger ACCOUNT --from DATE --to DATE`, `report tax --from DATE --to DATE` (spec sections 8, 15, 17). Currency: an account's per-currency sums are converted with `fx.convert_amount` at the report's date, each rounded with `money.cents` per account, then totalled. Networth converts to the book currency at each month's last day. Trial balance: rounding differences between debit and credit totals are absorbed in the row with the largest absolute balance (state it in the handoff). Accounts appear by exact posting name. Tax report reads the `invoices`/`invoice_lines` and `bills`/`bill_lines` tables directly; issued means status not `draft`.

Done check: `python -m unittest discover -s tests -p 'test_reports.py'`.
Must not touch: other tasks' files. Do not add `report aging` or `report budget` (they are owned by other tasks); register your subcommands in `groups["report"]`.

## reconcile

Files you own: `fin/reconcile.py`, `tests/test_reconcile.py`.

Build: `reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID] [...]` (spec section 16). Validate the IDs first (each must have a posting to exactly ACCOUNT dated on or before DATE), then mark those postings `cleared = 1`. Audit `reconcile` (ACCOUNT) only if a posting changed.

Done check: `python -m unittest discover -s tests -p 'test_reconcile.py'`.
Must not touch: other tasks' files.

## api

Files you own: `fin/api.py`, `tests/test_api.py`.

Build: `serve --port N` (top-level command, uses the global `--db`). It runs a `http.server.ThreadingHTTPServer` on the port until stopped and returns `None`. Each request runs `fin.cli.main` in-process with `--json` and captures stdout and stderr (as in `support.run`). Routes (spec section 10): `GET /accounts`, `GET /transactions`, `GET /balances?at=`, `GET /reports/income?from=&to=`, `GET /reports/balance-sheet?at=`, `GET /invoices`, `GET /invoices/ID`, `GET /reports/aging?at=&payables=1`, `GET /audit`, `POST /transactions`, `POST /invoices`, `POST /invoices/ID/issue`, `POST /invoices/ID/payments`. Map each `POST` to its command with `--user`. Check access first with `fin.cli.check_access(conn, user, action)`: missing or unknown `X-User` → 401, forbidden → 403 (`{"error": "..."}`). Other user errors → 400. Unknown paths → 404. Invalid JSON → 400. Success: 201 for `POST /transactions` and `POST /invoices`, 200 otherwise. Responses are JSON. Decide and list the `POST /transactions` argument mapping in the handoff.

Done check: `python -m unittest discover -s tests -p 'test_api.py'`. Start the server on port 0 in a thread in tests.
Must not touch: other tasks' files.

## readme

Files you own: `README.md`.

Build: README.md with usage (every command group with one example), the HTTP API, roles, and the assumptions list. Gather assumptions from every handoff in `.claude/team/handoff/`. No tests: done check is `test -s README.md`.
Must not touch: anything other than README.md.
