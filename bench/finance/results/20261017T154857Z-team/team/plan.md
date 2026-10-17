# Plan
Goal: small-business finance system, full spec in `.claude/team/spec.md` (the user's request; section numbers below refer to it).
Check: `python -m unittest discover -s tests`.

## Contract / conventions (already built; READ fin/core.py and fin/cli.py first)
- `fin/core.py` (lead-owned, do NOT edit; if you need a change, log it in changes.md and work around it): UserError, D, q2, fmt, parse_date/month/cur, add_months, month_end, add_days, days_between, Book (ensure_account, account, post_txn, txn_dict, sums, rate, convert, to_currency, check_open, audit, closed_through), SCHEMA (all tables already exist, incl. invoices/bills/cleared).
- Each feature module `fin/<mod>.py` defines `setup(sub)` registering commands via `cli.group(sub, 'report')` (shared command groups, e.g. `report`, `account`) and `cli.command(sub, name, handler, perm, args)`. Handler `(book, ns) -> JSON-able data` (call `book.audit(action, target)` for data changes; raise UserError for user errors; never print). perm: 'read' | 'write' | 'admin'. See fin/books.py patterns once present, and cli.py docstrings. Modules are listed in cli.MODULES; one module per task.
- Money: only Decimal; output via `fmt`. Validate all input (bad dates, numbers, unknown accounts) -> UserError. Dates ISO strings. Put reusable logic in plain functions `fn(book, ...)` (the HTTP API layer calls handlers through `cli.execute(db, user, argv)`).
- Tests: `tests/test_<mod>.py` using `tests/helpers.py` Base (self.ok/self.bad/self.run_cmd). Cover every command and error case of your sections. Don't edit tests/helpers.py, test_core.py or others' files. Run just yours: `python -m unittest tests.test_<mod>`.
- No git commits. Log edits to files you don't own in changes.md (you should have none).

## books
Owns fin/books.py, tests/test_books.py. Sections 1 (account add/list; `init` is done in cli.py), 2 (txn add/list), 3 (balance), 11 (user add/list, audit list [--by]; audit actions are written by each command), 12 (period close/status). Perms: user add & period close 'admin'; reads 'read'. Closed-period check is already inside Book.post_txn. Closing earlier than closed: no change (but still success + audit? yes audit it). Done: `python -m unittest tests.test_books`.

## ratesimport
Owns fin/ratesimport.py, tests/test_ratesimport.py. Sections 4 (fx add, convert), 5 (rule add/list, import). Import: whole import atomic (UserError rolls back automatically); closed-period rows fail the whole import; use Book.ensure_account for uncategorized accounts and rule accounts must exist (unknown account -> error). Rule account existence checked at `rule add`. Invalid regex -> user error. Done: `python -m unittest tests.test_ratesimport`.

## planning
Owns fin/planning.py, tests/test_planning.py. Sections 6 (budget set, `report budget MONTH`), 7 (recurring add/run), 9 (loan schedule; read-only perm). Budget account must be an existing expense account. Recurring run: occurrences computed from start with day-of-month clamp (use add_months(start, k, start_day) for monthly; yearly add_months(start,12k,start_day)), skip those already in recurring_done, post via book.post_txn (closed period -> error, all rolled back). Audit: recurring.add target name, recurring.run target the until date. Done: `python -m unittest tests.test_planning`.

## reports
Owns fin/reports.py, tests/test_reports.py. Sections 8 (report income, balance-sheet, networth), 17 (trial-balance, ledger). Remember `report` is a shared group (cli.group). Conversion: convert each account's per-currency sums at the report date with Book.to_currency, round once per account (fmt). Totals: sum of rounded account figures. Tests may create data via txn add / fx add commands. Done: `python -m unittest tests.test_reports`.

## invoices
Owns fin/invoices.py, tests/test_invoices.py. Section 13 EXCEPT `report aging` (tax add/list, customer add/list, invoice create/issue/pay/show/list). Also expose plain function `invoice_dict(book, id)` and `create_invoice(book, customer, date, lines)`, `issue_invoice(book, id)`, `pay_invoice(book, id, amount, date, account)` for the API layer. Store payments in invoice_payments (date, amount, txn_id). Invoice numbers: per year counter from existing numbers. Quantity kept as given text. Done: `python -m unittest tests.test_invoices`.

## bills
Owns fin/bills.py, tests/test_bills.py. Section 14 EXCEPT `report aging` (vendor add/list, bill create/pay/show/list). Needs tax codes: they live in table taxes (rate TEXT, percent as given) — read directly with SQL. Payments in bill_payments. Expose `bill_dict(book, id)`. Tests create tax codes with direct SQL insert or `tax add` if available (prefer SQL insert via book/sqlite3 to stay independent). Done: `python -m unittest tests.test_bills`.

## arreports (wave 2)
Owns fin/arreports.py, tests/test_arreports.py. Sections 15 (report tax), 16 (reconcile), 13/14 `report aging [--payables]`. Reads invoices/bills/invoice_payments/bill_payments tables (see fin/invoices.py, fin/bills.py for how they're written). Done: `python -m unittest tests.test_arreports`.

## api (wave 2)
Owns fin/api.py (`serve` command, perm 'read', --port; http.server ThreadingHTTPServer), tests/test_api.py. Section 10 + 11 for HTTP. Implement by calling `cli.execute(db, user, argv)` (map JSON bodies to argv; GET without user) — look at which commands exist. 401/403 from UserError.kind 'auth'/'forbidden'; kind 'input' -> 400; unknown path 404; check X-User on every POST before anything. GET /invoices[/ID] etc map to `invoice list/show`; /audit -> `audit list`. Tests start the server on port 0 in a thread (make `make_server(db, port)` function). Done: `python -m unittest tests.test_api`.
