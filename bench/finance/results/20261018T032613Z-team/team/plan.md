# Plan
Goal: small-business finance system, spec in .claude/team/spec.md (the user's request, numbered sections 1-17). Lead already wrote fin/core.py, fin/cli.py, fin/admin.py (sections 1 accounts, 11 users/audit, 12 periods), tests/helpers.py.
Check: `python3 -m unittest discover -s tests` (use python3).

## Contract / Conventions (READ fin/core.py, fin/cli.py, fin/admin.py, tests/helpers.py first; they are short)
- Each module fin/<m>.py has `SCHEMA` (CREATE TABLE IF NOT EXISTS sql, only its own tables) and `register(reg)`; already stubbed. Add commands with `p = reg.add(("txn","add"), handler, mode, action, target_fn)` then `p.add_argument(...)`. Use `action=None` for reads. Handler: `def h(book, args)` returns a JSON-able result (strings for money via core.fmt; Decimal for math, never float). The CLI appends the audit entry (action, str(target(args,result))) itself and commits/rolls back; handlers never commit and never audit. Raise core.UserError for every user error. Repeatable options: `action="append"`.
- Use core helpers: D, q2, fmt, date_str, month_str, month_end, next_month, add_months, currency_code, parse_posting, book.post_txn (validates and checks closed period; use it for EVERY transaction), book.ensure_account, book.account, book.convert/rate, book.check_open, book.currency. Never write own versions. Do not edit core.py/cli.py/admin.py/helpers.py/other modules (if you need a change, say so in your handoff).
- Tables in base schema: accounts(name,type,currency), transactions(id,date,description), postings(id,txn_id,account,amount TEXT,currency,cleared INT). rates table (id,date,from_cur,to_cur,rate TEXT) is created by admin.py; `fx add` inserts into it (ledger task).
- Tables owned by invoicing: taxes(code PK, rate TEXT), customers(name PK, terms INT), invoices(id INTEGER PK AUTOINCREMENT, number TEXT, customer, date, due, status, lines TEXT json (list of the output line dicts), net, tax, total TEXT), invoice_payments(id INTEGER PK AUTOINCREMENT, invoice_id, date, amount TEXT, account, txn_id).
- Tables owned by bills: vendors(name PK, terms INT), bills(id INTEGER PK AUTOINCREMENT, vendor, ref, date, due, status, lines TEXT json (output line dicts), net, tax, total TEXT, UNIQUE(vendor,ref)), bill_payments(id INTEGER PK AUTOINCREMENT, bill_id, date, amount TEXT, account, txn_id).
- Output JSON shapes/keys exactly as in spec.md. Money strings via fmt. Dates validated with date_str.
- Tests: each task writes tests/test_<task>.py with unittest, subclassing tests.helpers.FinCase (never name helpers fail/assert*/setUp/run/skipTest), covering every spec section it owns incl. errors (UserError), permissions where relevant, and edge cases in the spec. Done check: `python3 -m unittest tests.test_<task> tests.test_core` passes.
- Each task owns only the files listed; log nothing else needed. Other modules may not exist yet when you test: create test data via self.post / run_cmd of your own and admin commands.

## ledger
Files: fin/ledger.py, tests/test_ledger.py. Spec sections 2 (txn add/list; audit txn.add target id), 3 (balance), 4 (fx add -> audit fx.add target FROM/TO, mode write; convert, read-only; validate currencies, rate>0, dates). Balance: only accounts with postings, plus ancestors; per-currency sums. Also `GET`-friendly: nothing else. May change: only these files.

## imports
Files: fin/imports.py, tests/test_imports.py. Sections 5 (rule add/list, import, audit rule.add pattern / import account; validate regex compiles; import atomic: any bad row or closed period -> UserError, nothing imported; amounts with ',' not needed; dedupe via own table `imported(account,date,description,amount)`), 6 (budget set, expense accounts only, report budget MONTH registered as ("report","budget")), 7 (recurring add/run; own tables; occurrences computed from start by index n so day clamping doesn't drift; run is atomic and audit recurring.run target = until date), 16 (reconcile ACCOUNT, audit target = account; mode write; own table not needed, use postings.cleared; clear is per ACCOUNT: store clearing in postings.cleared only for that account's postings in that txn; difference etc as spec). Descriptions for imports: row description as-is. A skipped duplicate counts in skipped. Dates in the CSV validated.

## reports
Files: fin/reports.py, tests/test_reports.py. Sections 8 (report income, balance-sheet, networth), 17 (trial-balance, ledger). Register under ("report", ...). Conversion: convert each posting's currency amount at the report's date with book.convert, sum, then fmt (round once per account at the end). networth: months FROM..TO inclusive, as of month_end; assets and liabilities positive numbers (liabilities negated), networth = assets − liabilities. Balance sheet: per account by the name postings are on; equity section excludes retained earnings (which is computed). ledger: ACCOUNT must exist; amounts in account's currency; includes descendants' postings. Treat each report as read-only mode "read". May change: only these files.

## loans
Files: fin/loans.py, tests/test_loans.py. Section 9 (`loan schedule` read-only; PRINCIPAL/RATE decimals, MONTHS positive int; validate). Use Decimal with enough precision (getcontext prec 50 inside a localcontext); r = RATE/1200; (1+r)^-n via Decimal power. total_interest = sum of interest. Row dates: add_months(start, n).

## invoicing
Files: fin/invoicing.py, tests/test_invoicing.py. Section 13 except aging: tax add/list (audit tax.add code; rate shown as given; re-adding existing code is a user error; rate validation: non-negative decimal), customer add/list (customer.add), invoice create (invoice.create target id)/issue (invoice.issue)/pay (invoice.pay)/show/list. Closed-period checks happen through book.post_txn. Export module-level helpers `invoice_dict(conn, id)` for the API task. paid = sum of payments; status draft/issued/partial/paid. Payment account must exist and be an asset. Quantity may be decimal; "shown as given" = the string as typed.

## bills
Files: fin/bills.py, tests/test_bills.py. Section 14 except aging: vendor add/list (vendor.add), bill create (bill.create target id; unique ref per vendor; account must be existing expense or asset), bill pay (bill.pay), bill show/list. Tax codes come from table taxes (owned by invoicing; use `SELECT rate FROM taxes WHERE code=?` — in tests create it with direct SQL insert or `tax add` if available; invoicing is built in parallel, so in tests use direct SQL INSERT INTO taxes after executing `CREATE TABLE IF NOT EXISTS taxes(code TEXT PRIMARY KEY, rate TEXT)`). Empty tax code = no tax; tax_code null in output. Export `bill_dict(conn, id)`. Same payment rules as invoices.

## aging (wave 2)
Files: fin/aging.py, tests/test_aging.py: section 13 aging, 14 payables aging (`report aging --at DATE [--payables]`), section 15 `report tax`. 

## api (wave 2)
Files: fin/api.py, tests/test_api.py: section 10 `serve --port N` (mode read) over http.server (ThreadingHTTPServer), implemented by calling fin.cli.execute(db, user, argv) in-process; map errors via UserError.status (400/401/403); unknown path 404; POST needs X-User header (missing/unknown -> 401). Tests start the server on an ephemeral port in a thread.
