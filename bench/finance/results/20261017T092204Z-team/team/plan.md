# Plan
Goal: small-business finance system per the user's spec (python stdlib, package `fin/`). The full spec is in
/home/jaca/claude-team-a/bench/work/finance-team/.claude/team/spec.md (sections 1-17). Core is DONE by lead:
read fin/core.py, fin/cli.py, tests/helpers.py first (short). Check (global): `python -m unittest discover -s tests`.

## Contract
- A module `fin/<module>.py` exports `COMMANDS` (list of `fin.cli.Command(path, configure, run, mode)`) and optionally `SCHEMA`
  (CREATE TABLE IF NOT EXISTS ... sql; run on every open). Table names must be prefixed with the module's own domain (below) to avoid clashes.
  `run(book, args)` returns a JSON-able result (strings for amounts via core.fmt), calls `book.audit(action, target)` for writes,
  raises UserError for user errors. mode: "read" | "write" (admin+editor) | "admin" | "init". The cli handles auth, transaction, rollback, exit codes.
  Use `book.post_txn(...)` for every posted transaction (it checks closed periods, balance, accounts). Never use float.
  Use `book.conn` queries; money stored as TEXT Decimal strings. Sorted outputs: Python sort by name.
- Shared tables in core: meta(currency, closed_through), users, accounts, txns, postings, audit, fx. Other tables belong to their module.
- Python functions other modules may call (keep these exact names/signatures):
  * cmd_reports.balances(book, date_from=None, date_to=None, account=None) -> {account_name: {currency: Decimal}} raw (own postings only, no ancestors)
- Tests: each task writes `tests/test_<task>.py` using tests/helpers.FinCase (subprocess CLI; `self.init()`, `self.ok(...)`, `self.fails(...)`),
  covering every spec section it owns incl. error cases (exit 2 + nothing changed). Do NOT edit core.py, cli.py, helpers.py (tell lead in handoff if a bug is there; tiny fixes allowed if logged in changes.md).
- Decide unspecified things sensibly; list assumptions in your handoff (lead puts them in README).
- Done check for all: `python -m unittest tests.test_<task> -q` plus `python -m unittest discover -s tests -q` not broken by you (other teammates' tests may still be in progress: ignore their failures).

## books  (owns fin/cmd_books.py, tests/test_books.py) — spec sections 1, 2, 3, 11, 12
Commands: init (mode init: creates meta currency, first user admin, audit entry `init` with user=admin name), user add/list, audit list [--by],
account add/list, txn add/list, balance [--at], period close/status. Note period close = admin mode; user add = admin mode.
`txn add` audit target is the id. Balance per spec incl. ancestors. Note cli.py's MODULES order: cmd_books first.

## data  (owns fin/cmd_data.py, tests/test_data.py) — sections 4, 5, 6, 7
fx add, convert, rule add/list, import (CSV, atomic, closed-period check for every row, dedupe incl. within file, "imported" table keyed by account/date/desc/amount),
budget set, report budget, recurring add/run (monthly/weekly/yearly, idempotent: track created occurrences). Audit as spec.

## reports  (owns fin/cmd_reports.py, tests/test_reports.py) — sections 8, 9, 16, 17
Define `balances(...)` per contract. report income, balance-sheet, networth, trial-balance, ledger; loan schedule (read mode); reconcile (write mode, own table `recon_cleared`).
Currency conversion via book.convert at the report date; convert per account total (state in assumptions). Tests may set up data via txn add/fx add CLI
(owned by other teammates; if not yet merged, insert via Book.post_txn directly in tests using `fin.core.Book`).

## invoices  (owns fin/cmd_invoices.py, tests/test_invoices.py) — sections 13, 14, 15
tax add/list, customer add/list, vendor add/list, invoice create/issue/pay/show/list, bill create/pay/show/list, report aging (with --payables), report tax.
Own tables prefixed inv_/bill_/tax_/party_. Invoice numbering per year. Amount output via core.fmt; quantity as given. Check closed periods (post_txn does).

## api  (owns fin/cmd_api.py, tests/test_api.py) — section 10 (+ auth parts of 11 for HTTP)
`serve --port N` (read mode, runs http.server forever; also export `make_server(db, port)` returning HTTPServer for tests, port 0 allowed).
Implement every endpoint by translating the request to CLI argv and calling `fin.cli.execute(db, user, argv)` per request (new connection each time),
mapping UserError -> e.status (400 default, 401/403 for AuthError) with {"error": msg}; unknown path 404; POST needs header X-User (missing -> 401, unknown -> 401 via execute's AuthError; role denial 403).
Beware: execute for POST with unknown user: AuthError 401 already. Check GET needs no user. POST /transactions -> 201; POST /invoices -> 201; issue and payments -> 200.
Tests: start make_server in a thread, use urllib; the underlying commands are written in parallel by others, so tests of endpoints
may need to wait for merge: write them anyway and run when `python -m fin` commands exist (init/txn add by cmd_books); if not available, note it in handoff.
