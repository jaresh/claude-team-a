# Plan

## Goal
Small-business finance CLI + HTTP API, package `fin/`, stdlib only. Full user spec, word for word:
`.claude/team/spec.md` (read the sections your task names).

**Check:** `python3 -m unittest discover -s tests` (all pass).

## Contract

Already written and tested by the lead (do NOT edit): `fin/core.py`, `fin/cli.py`, `fin/books.py`,
`fin/__main__.py`, `tests/helpers.py`, `tests/test_*_accept.py`, `tests/test_books.py`.
Read `fin/core.py` and `fin/cli.py` (docstrings) and `fin/books.py` (an example module) first.

- Each feature module defines `register(reg)`; `cli.MODULES` already lists `fin.books, fin.bank,
  fin.reports, fin.invoicing, fin.api` (missing modules are skipped).
  `p = reg.command("report income", handler, writes=False|True, admin=False, db=True)` returns
  the argparse parser; add arguments on it. `db=False` for commands that need no database
  (handler gets ctx=None). Groups like `report` are shared between modules automatically.
- Handler: `handler(ctx, args) -> doc` (JSON-able dict/list; money as strings via `core.fmt`).
  `ctx.conn` (sqlite3, Row factory, autocommit mode; write commands are already wrapped in a
  transaction by cli.run, never BEGIN/COMMIT yourself), `ctx.user`, `ctx.currency` (book currency),
  `ctx.audit(action, target)`: write commands must call it exactly once on success.
  Raise `core.UserError` for every user error (exit 2 / HTTP 400; rollback is automatic);
  `core.NotFoundError` for an unknown invoice/bill id (HTTP 404).
- Your tables: create them in your module with `core.ensure_schema(ctx.conn, "CREATE TABLE IF NOT
  EXISTS ...")` at the start of each handler that uses them (cheap, idempotent). Prefix table names
  with your module (`bank_rules`, `inv_invoices`, ...). Store money as TEXT via `core.fmt`.
- Use core helpers, never your own versions: `parse_amount`, `parse_decimal`, `money`, `fmt`,
  `dsum`, `parse_date`, `parse_month`, `month_end`, `add_months(date, n)` (the monthly rule of
  section 7: occurrence k = add_months(start, k)), `add_days`, `days_between`,
  `require_account`, `get_account`, `ensure_account` (auto-create in book currency),
  `account_type`, `is_under`, `ancestors`, `post_transaction(conn, date, desc, [(account,
  Decimal|None), ...]) -> id` (validates, checks closed period, keeps posting order),
  `parse_posting`, `txn_doc`, `postings_between(conn, frm, to)`, `account_sums`, `rate`,
  `convert(conn, amount, frm, to, at)` (rounded to cents), `check_open(conn, date)`.
  Listing transactions: `fin.books.list_transactions(conn, account, frm, to)`.
- Currency conversion in reports (sections 8, 17): for each account, take its raw balance per
  currency, convert each to the target currency at the report date with `core.convert` (rounds to
  cents), sum; totals are sums of the shown rounded per-account values; `retained_earnings`
  is -(sum of converted income + expense account balances).
- Ledger (17) with descendants in another currency: convert each posting with `core.convert` at
  the posting's date to ACCOUNT's currency.
- `networth` also accepts `--currency`.
- Import: posting order is [ACCOUNT, category]. CSV via `csv` module; every row must parse (bad
  date/amount/missing column → UserError, nothing imported). Dedup key (account, date,
  description, amount) stored in a table at import time; repeats within one file are skipped.
  Rule's ACCOUNT must exist; invalid regex is a user error.
- Recurring: names unique; postings stored as text; track created dates per recurring.
  Weekly k-th = add_days(start, 7k); yearly k-th = add_months(start, 12k).
- `reconcile` is a write command (audit `reconcile`, target the account). Unknown account → error.
- Invoices/bills: `--line` split on `;`; invoice needs exactly 4 fields, bill exactly 4. Quantity,
  price, amount must be decimals; tax per line uses core.money. `invoice pay`/`bill pay` ACCOUNT must
  exist and be an asset account; AMOUNT must be > 0. Bill status `open` → `partial` → `paid`;
  invoice `draft` → `issued` → `partial` → `paid`. `report aging` buckets: days<=0 current,
  1-30, 31-60, 61-90, >90 → `90+`. Statuses for `--status` filter are any string (no match → []).
- `loan schedule` is `db=False` (works without a database). MONTHS must be a positive integer.
- API (`fin/api.py`): `make_server(db_path, port, host="127.0.0.1") -> http.server.HTTPServer`
  (port 0 = any free port) and command `serve --port N` (db=False; uses args.db). Each request is
  served by translating it to argv and calling `fin.cli.execute(db_path, user, argv)`, so the
  documents are identical to `--json`. Errors: `e.status` of the UserError (400/401/403/404)
  with `{"error": str(e)}`. Body not valid JSON → 400.

## Conventions
- Style: like `fin/books.py`: `cmd_<group>_<sub>(ctx, args)` handlers, `<thing>_doc(...)`
  builders, plain functions, short docstrings. No floats anywhere.
- Your unit tests: `tests/test_<task>.py`, using `tests.helpers.FinCase` (`self.ok`, `self.err`,
  `self.cli`, `self.accounts`, `self.txn`). Don't name helpers `fail`, `run`, `setUp`, `assert*`.
- Don't edit files of other tasks; log any shared-file edit in `.claude/team/changes.md`.

## bank
Owns `fin/bank.py`, `tests/test_bank.py`. Spec sections 5, 6, 7, 16: `rule add/list`, `import`,
`budget set`, `report budget`, `recurring add/run`, `reconcile`.
Done: `python3 -m unittest tests.test_bank_accept tests.test_bank tests.test_books`.
May change anything in its own files. Must not touch other files.

## statements
Owns `fin/reports.py`, `tests/test_statements.py`. Spec sections 3, 8, 9, 17: `balance`,
`report income`, `report balance-sheet`, `report networth`, `report trial-balance`,
`report ledger`, `loan schedule`.
Done: `python3 -m unittest tests.test_reports_accept tests.test_statements tests.test_books`.
May change anything in its own files. Must not touch other files.

## invoicing
Owns `fin/invoicing.py`, `tests/test_invoicing.py`. Spec sections 13, 14, 15: `tax add/list`,
`customer add/list`, `vendor add/list`, `invoice create/issue/pay/show/list`,
`bill create/pay/show/list`, `report aging [--payables]`, `report tax`.
Done: `python3 -m unittest tests.test_invoicing_accept tests.test_invoicing tests.test_books`.
May change anything in its own files. Must not touch other files.

## api
Owns `fin/api.py`, `tests/test_api.py`. Spec section 10 (and 11 for the API). Every route listed
in section 10, mapped to the equivalent command argv (e.g. GET /balances?at=D → `balance --at D`
(omit when absent); POST /invoices lines → `--line "desc;qty;price;tax_code"`; GET
/reports/aging?at=D&payables=1 → `report aging --at D --payables`; GET /audit → `audit list`).
Other modules are being written in parallel: the routes for invoices/balances/reports will only
work once they land, so test_api_accept.ApiTest.test_invoices and some reports may fail now.
Done: `python3 -m unittest tests.test_api_accept.ApiTest.test_errors tests.test_api` passes
(write `tests/test_api.py` against routes that use only fin/books commands, plus routing tests).
May change anything in its own files. Must not touch other files.
