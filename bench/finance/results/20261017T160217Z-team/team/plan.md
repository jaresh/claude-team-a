# Plan
Goal: small-business finance system (see .claude/team/spec.md = the user's full spec; read only the sections your task names).
Check: `python3 -m unittest discover -s tests` (use `python3`, no `python`).

## Contract (core is DONE; read fin/util.py, fin/db.py, fin/core.py, fin/commands.py, fin/cli.py, tests/helpers.py)
- Handlers are functions `fin/<module>.py: <cmd_with_underscores>(book, **kw)` returning JSON-able data (dicts/lists with money as strings via `util.fmt`). Mapping in fin/commands.py `C` (e.g. "report balance-sheet" -> reports.report_balance_sheet). Argument names (kw) are the argparse dests in fin/cli.py `build()`: dates/amounts/months arrive as raw strings (validate with util.check_date/check_month/D), `frm`/`to` for --from/--to, list options (`posting`, `line`, `clear`) are lists. Optional ones are None when absent.
- The executor (commands.execute) handles transactions/rollback, permissions and audit: handlers NEVER write audit, never commit, never check roles. Raise `util.UserError` for every user error (the whole command is rolled back).
- Use `book.post(date, desc, [(account, Decimal|None)])` for every transaction (it checks closed periods, balance, accounts), `book.ensure_account(name)`, `book.postings(...)`, `book.balances(...)`, `book.convert/total`, `book.currency`, `book.conn` (sqlite, rows are sqlite3.Row). Money: Decimal only, `util.q` rounds half up, `util.fmt` prints; dates ISO strings; month arithmetic `util.add_months/next_month/month_end`.
- Own tables: a module may define `SCHEMA` (a string of `CREATE TABLE IF NOT EXISTS` statements, run on every open). Only modules bank, billing, recon are scanned. Store amounts as TEXT decimals.
- Do not edit core files (util, db, core, commands, cli, tests/helpers.py). If you truly need a change there, append a line to .claude/team/changes.md saying what and why, and make the smallest edit.
- Tests: `tests/test_<yourtask>.py`, using `tests.helpers.FinCase` (CLI via subprocess; see tests/test_core.py). Cover every command/section of your task incl. user-error cases (exit 2) and numeric examples from the spec. Done check for every task: `python3 -m unittest tests.test_<yourtask>` plus `python3 -m unittest tests.test_core`.
- Append one line to changes.md per edit of a file you don't own.

## bank
Owns fin/bank.py, tests/test_bank.py. Spec sections 5, 6, 7 (rule add/list, import, budget set, report budget, recurring add/run). Handlers: rule_add, rule_list, import_ (module function name must be `import_` ... NOTE commands.py resolves "import" to `import`: since that is a keyword, define `import_` and ALSO add `globals()["import"] = import_` ). budget_set, report_budget, recurring_add, recurring_run. Import and recurring run are all-or-nothing (UserError rolls back). Category accounts via book.ensure_account. Recurring occurrences are computed from the start date (use add_months(start, n) for monthly, +7d, yearly with Feb-29 clamp) and tracked in a table so reruns create nothing. May change: only bank.py + its tests.

## reports
Owns fin/reports.py, tests/test_reports.py. Spec sections 8 and 17: report_income, report_balance_sheet, report_networth, report_trial_balance, report_ledger. Foreign-currency postings convert per account-currency total at the report date via book.convert (missing rate -> UserError). Sign flip for income/liabilities/equity. Accounts listed only if they have postings in range, by the name the postings are on (not ancestors). --currency validated with util.check_currency.

## loans
Owns fin/loans.py, fin/recon.py, tests/test_loans.py, tests/test_recon.py. Spec sections 9 (loan_schedule(book, principal, rate, months, start)) and 16 (reconcile(book, account, date, balance, clear); recon.py defines SCHEMA for cleared marks; cleared balance includes postings to the account only (exact name)). Validate: months>=1, principal>0, rate>=0.

## billing
Owns fin/billing.py, tests/test_billing.py. Spec sections 13, 14, 15: tax_add, tax_list, customer_add, customer_list, vendor_add, vendor_list, invoice_create/show/list/issue/pay, bill_create/show/list/pay, report_aging(book, at, payables), report_tax(book, frm, to). Define SCHEMA. Invoice/bill ids start at 1 each. Issue/pay/bill transactions go through book.post (closed periods). Foreign currency: assume book currency (document in README assumptions via a note in your handoff).

## api (wave 2)
Owns fin/api.py, tests/test_api.py. Spec section 10 (+11 for X-User). `serve(db, port)` using http.server ThreadingHTTPServer; every route calls `commands.execute(db, user, cmd, **kw)` with the same kw the CLI would pass (see cli.py build(): e.g. "txn add" gets date, desc, posting=[ "ACC=AMT" or "ACC" ]). GET needs no user (user=None); POST: header X-User missing/unknown -> 401, permission denied -> 403 (execute raises UserError with message starting "permission denied" for role problems and "unknown user"/"--user is required" for identity: map those; check identity yourself before calling execute for POST by querying the users table via fin.db.Book, to get 401 vs 403 right). UserError -> 400 {"error"}; unknown path -> 404; POST 201 for creates (/transactions, /invoices), 200 for issue/payments. Tests start the server in a thread on a free port (serve must be usable so; split a `make_server(db, port)` out) .
