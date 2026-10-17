# Plan
Goal: small-business finance system `fin` (Python stdlib). Full spec: `.claude/team/spec.md` (the user's request,
word for word; sections 1-17). Check: `python3 -m unittest discover -s tests`.

## Contract / conventions (READ fin/core.py, fin/cli.py, fin/books.py, tests/helpers.py first)
- Lead already wrote fin/core.py (UserError, D, q2, fmt, dates, Ctx, ensure_account, get_account, post_txn, txn_dict,
  get_rate, convert_amount, account_sums), fin/cli.py (dispatch, permissions, one SQL transaction per command,
  rollback on error, exit 2), fin/books.py (init, user, audit, period), tests/helpers.py (Book test base class).
  NEVER reimplement these; import them (`from .core import *`). Do not edit them (log a request in changes.md instead
  and work around it; if a real bug blocks you, make a minimal fix and append a line to changes.md).
- Each module `fin/<name>.py` defines `register(reg)`: `p = reg.add("group cmd", perm, handler)` then
  `p.add_argument(...)`. perm: 'read' (no --user needed), 'write' (admin/editor), 'admin'. Handler `h(ctx, args)`
  returns a JSON-able dict/list (printed by cli); raise UserError for any user error (message to stderr, exit 2).
  Handlers of data-changing commands call `ctx.audit(action, target)` exactly once (see spec section 11 for names).
  Repeatable options use `action="append"`. Use `ctx.q(sql, params)` for queries. Money: Decimal; store as TEXT;
  output through `fmt()`. Zero is "0.00". Validate everything (dates via date_str/parse_month, decimals via D).
- A module owns its extra tables: create them with `CREATE TABLE IF NOT EXISTS` via `ctx.conn.execute(...)`
  (one statement per call) at the start of each handler that uses them (both reads and writes).
- Transactions are only posted through `post_txn` (it checks closed periods, balance, accounts). Commands that post
  several transactions must check closed periods for ALL before posting (or just rely on the rollback: the cli
  rolls everything back on UserError, so simply raising is enough).
- Tests: `tests/test_<task>.py`, unittest, subclass `tests.helpers.Book`; use `self.cli(...)`, `self.fail(...)`,
  `self.txn(...)`. Cover every command/section of your task incl. error cases, closed periods, audit entries.
  Run with `python3 -m unittest tests.test_<task>`. Code that reads like core.py: terse, no extra commentary.
- Other modules' commands may not exist yet while you work (parallel). Do not depend on them in your tests; use
  `self.txn` to create data and read results with your own commands. Do not touch files you don't own.
- Use `python3` (no `python`). Stdlib only.

## ledger
Owns fin/ledger.py, tests/test_ledger.py. Spec sections 1 (account add/list), 2 (txn add/list), 3 (balance),
4 (fx add, convert; `convert` is a top-level command, `fx add DATE FROM TO RATE`). Audit: account.add (name given
on the command, not parents), txn.add (id), fx.add (FROM/TO). Account add on an existing account is an error.
Validate rate > 0. May change: only your files. Done: `python3 -m unittest tests.test_ledger`.

## banking
Owns fin/banking.py, tests/test_banking.py. Spec sections 5 (rule add/list, import), 6 (budget set, report budget),
7 (recurring add/run). Track recurring occurrences created (table of recurring id + date) so a rerun creates
nothing new. `import` and `recurring run` are all-or-nothing (rolled back on error). Import dedupe key: (account,
date, description, amount) over rows previously imported, tracked in your own table. Budget accounts must be
existing expense accounts (user error otherwise). Done: `python3 -m unittest tests.test_banking`.

## invoicing
Owns fin/invoicing.py, tests/test_invoicing.py. Spec sections 13 (tax, customer, invoice, report aging),
14 (vendor, bill, aging --payables), 15 (report tax). `report aging` is one command with `--payables` flag
(store_true). Use Decimal quantity; show quantity as given. Invoice number counter per year counts invoices
already issued with that year. Aging uses payments dated <= AT only. Every invoice/bill command prints the
document. Done: `python3 -m unittest tests.test_invoicing`.

## reports
Owns fin/reports.py, tests/test_reports.py. Spec sections 8 (report income, balance-sheet, networth),
9 (loan schedule), 16 (reconcile), 17 (report trial-balance, report ledger). Use core.account_sums for the
aggregation (extend nothing in core; do your own helper in reports.py if needed). reconcile needs a table of
cleared (account, txn id), audit action `reconcile` target the account; it is a 'write' command and a user error
changes nothing. Done: `python3 -m unittest tests.test_reports`.

## api (wave 2, after the others)
Owns fin/api.py, tests/test_api.py. Spec section 10. `register(reg)` adds command `serve --port N` (perm 'read';
the server runs until stopped; bind 127.0.0.1). Implement the endpoints by calling `fin.cli.execute(db, user, argv)`
(translate JSON bodies to argv; GET never passes a user; POST passes X-User header; no header or unknown user -> 401
with {"error"}; AuthError has .status 401/403; other UserError -> 400; unknown paths 404; POST /transactions returns
201 and the txn, POST /invoices 201, other POSTs 200). Use ThreadingHTTPServer but serialize calls with a lock.
Tests start the server in a thread (in-process, port 0 via a helper function `make_server(db, port)` you expose)
and use urllib. Done: `python3 -m unittest tests.test_api`.
