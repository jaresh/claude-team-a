# Plan
Goal: small-business finance system (`python -m fin`), full spec in .claude/team/spec.md (user's words; sections 1-17).
Check: `python3 -m unittest discover -s tests` (each task adds tests/test_<task>.py; never edit others' tests).

## Contract (already written by lead; READ fin/core.py and fin/cli.py first)
- fin/core.py is shared: UserError, D(), q2(), fmt(), parse_date/check_date/check_month, add_months(date,n), month_last_day,
  check_currency, Ctx (ctx.conn, ctx.user, ctx.audit(action,target)), ensure_account, get_account, post_transaction
  (does closed-period + balance check, returns id), txn_dict, get_rate/convert, sum_postings, book_currency, meta_get/meta_set,
  schema tables (users, audit, accounts, transactions, postings(amount TEXT), fx_rates, meta incl. 'currency','closed_through').
  NEVER reimplement these. Need a change in core? Make the smallest addition (append only) and log it in changes.md.
- Each module fin/<mod>.py defines optional `SCHEMA` (CREATE TABLE IF NOT EXISTS ... sql for its own tables) and
  `COMMANDS = [(("account","add"), setup(parser), handler(ctx, args), level)]`; level 'read' | 'write' (admin+editor) | 'admin'.
  Handler returns the JSON-able document; raises UserError for user errors (everything rolls back); calls ctx.audit(action,target)
  for every data change (targets per spec section 11). Parsers use `dest` names you choose; repeated options `action="append"`.
  Module names are fixed in core.MODULES: books, bookkeeping, docs, reports, api.
- Output JSON amounts via fmt(); money Decimal only. Tests call `fin.cli.execute(db, user, argv)` (returns document, raises UserError)
  or subprocess `python -m fin`; use tempfile dbs. Write tests/helpers only in your own test file.
- Ordering of tasks: one module per task, files not shared.

## books  (owns fin/books.py, tests/test_books.py)
Spec sections 1, 2, 3, 4, 11, 12 commands: init, account add/list, txn add/list, balance, fx add, convert, user add/list,
audit list, period close/status. `init` creates meta currency + first admin user + audit entry 1 (user=admin name, action init).
init on existing db is a user error (check meta currency exists). Permissions: user add and period close = 'admin'; reads 'read'.
Account add parents get the same currency. txn add uses core.post_transaction. Done: `python3 -m unittest tests.test_books`.
May change: fin/core.py (append-only additions, logged).

## bookkeeping  (owns fin/bookkeeping.py, tests/test_bookkeeping.py)
Sections 5, 6, 7, 9: rule add/list, import, budget set, report budget, recurring add/run, loan schedule.
Use core.post_transaction (so closed periods fail; for import/recurring run, pre-check all rows first or rely on the rollback,
which cli does). Import: skip duplicates (same account, date, description, amount) incl. within file; keep a table for them.
Recurring: store created occurrences so run is idempotent; the occurrence n = add_months(start, n) (monthly), +7n days, years.
Yearly Feb 29 -> Feb 28 non-leap. Loan: spec 9 exactly. Tests need init via books: if fin/books.py does not exist yet, tests
set up the db with fin.cli.execute(['init',...]) anyway - books is built in parallel; run your tests at the end once it exists
(wait/retry a few times if fin/books.py missing; do not write your own init).
Done: `python3 -m unittest tests.test_bookkeeping`.

## docs  (owns fin/docs.py, tests/test_docs.py)
Sections 13, 14, 15: tax add/list, customer/vendor add/list, invoice create/issue/pay/show/list, bill create/pay/show/list,
report aging (with --at, --payables), report tax. Store tables of your own (SCHEMA); lines as JSON text. Invoice number counter per
year of issue. All posting through core.post_transaction (closed-period errors for issue/pay/bill create/pay). Audit actions per spec 11.
Amounts via fmt; quantity as given. Also expose python functions `invoice_dict(conn,id)`/`bill_dict(conn,id)`.
Same init note as bookkeeping. Done: `python3 -m unittest tests.test_docs`.

## statements  (owns fin/reports.py, tests/test_reports.py)
Sections 8, 16, 17: report income, balance-sheet, networth, trial-balance, ledger, reconcile. Currency conversion per posting amount
at the report date with core.convert, then round once per account (sum converted amounts, round half up at the end). Table for cleared marks in SCHEMA.
Same init note. Done: `python3 -m unittest tests.test_reports`.

## api (wave 2; owns fin/api.py, tests/test_api.py)
Section 10: `serve(db, port)` (http.server, ThreadingHTTPServer, runs until stopped) and COMMANDS = [(("serve",), setup adding --port int, None, 'read')].
Implement by mapping each request to argv for fin.cli.execute(db, user, argv) (X-User header for POST; AuthError->401, ForbiddenError->403,
other UserError->400 {"error"}; unknown path 404). GET /invoices etc map to `invoice list`/`invoice show ID`; POST bodies mapped to the CLI args
(amount-less posting -> bare ACCOUNT). Test with a server thread on port 0.
Done: `python3 -m unittest tests.test_api`.
