# Plan
**Goal**: small-business finance system, `python -m fin`, full spec in `.claude/team/spec.md` (read the sections named in your task; sections 0 = intro/conventions at top apply to all).
**Check**: `python3 -m unittest discover -s tests` (use `python3`; stdlib only; money is Decimal, never float).

## Contract (already written by lead, READ these first: fin/core.py, fin/cli.py docstring, fin/base_cmds.py, fin/taxes.py, tests/helpers.py)
- Each command module defines `register(top, report)` (see cli.py). Handlers are THIN: `lambda ctx, args: plain_function(ctx, ...)`. Business logic lives in plain functions `f(ctx, ...)` so the HTTP API can call them. Handlers return JSON-able data (amounts as strings via `core.fmt`). Writers call `ctx.audit(action, target)` themselves (spec s11 names). Raise `core.UserError` for every user error. Never print, never commit, never call sys.exit in modules. Never use float.
- Reuse core: `parse_dec, q2, fmt, parse_date, date_str, parse_month, last_day_of_month, add_months, add_years, create_account, ensure_account, get_account, post_transaction (checks closed period, balance, unknown account), account_sums, convert, to_currency, get_rate, is_under, ensure(conn, "CREATE TABLE IF NOT EXISTS ..."), ctx.currency`. Do not reimplement these. Private tables: create lazily with `core.ensure(ctx.conn, SQL)` at the start of every function touching them (also read ones).
- Money in transactions: `post_transaction(conn, date, desc, [(account, Decimal|None), ...])` returns the txn dict incl. "id".
- Cross-module signatures (exact):
  - invoices.py: `create_invoice(ctx, customer, date, lines)` (lines: list of dicts with keys description, quantity, price, tax_code(optional/None/"")), `issue_invoice(ctx, id)`, `pay_invoice(ctx, id, amount, date, account)` (amount may be str or Decimal), `show_invoice(ctx, id)`, `list_invoices(ctx, status=None)`; each returns the invoice dict (list → list). Also `invoices_open(conn, at)` -> list of (due_date_str, balance Decimal) for aging (issued invoices dated <= at, payments dated <= at, balance > 0). Tables owned: customers, invoices, invoice_lines, invoice_payments.
  - bills.py: `create_bill(ctx, vendor, ref, date, lines)` (lines: dicts description, amount, account, tax_code), `pay_bill(ctx, id, amount, date, account)`, `show_bill`, `list_bills(ctx, status=None)`, `bills_open(conn, at)` same shape as invoices_open; `bill_tax_by_code(conn, frm, to)` -> {code: Decimal tax} for bills dated in period (tax-coded lines only); invoices.py also exports `invoice_tax_by_code(conn, frm, to)` (issued invoices dated in period). Tables owned: vendors, bills, bill_lines, bill_payments. Use `taxes.get_tax_rate`.
  - aging.py: `aging(ctx, at, payables=False)` -> aging dict; `tax_report(ctx, frm, to)`.
  - reports.py: `income_statement(ctx, frm, to, currency=None)`, `balance_sheet(ctx, at, currency=None)`.
  - api.py: registers `serve`.
- Ids: invoices and bills each have own id sequence from 1 (AUTOINCREMENT). 
- Error/exit behaviour, output format, rounding: spec top section. A failed command changes nothing (cli rolls back), but validate before writing anyway.
- Assumptions to report in your handoff (lead puts them in README): anything you decided.
- Tests: each task writes `tests/test_<module>.py` using `tests/helpers.py` FinTest (look at tests/test_base.py for style), covering every spec section of the task incl. error cases and audit entries. Don't edit tests/helpers.py, core.py, cli.py, base_cmds.py or other tasks' files; if you find a bug there, note it in your handoff and append a line to .claude/team/changes.md. Run only your own test file plus the full suite as the done check.
- Never name a test helper like a unittest method.

## automation
Files: fin/importing.py, fin/budgets.py, fin/recurring.py, tests/test_automation.py. Spec s5, s6, s7 (and s12 closed periods for import/recurring run: whole command fails, nothing imported/created). Recurring state in private tables; dedupe by (recurring id, occurrence date). Import dedupe: look at existing imported rows table (account,date,desc,amount) — not at txns. Category accounts created with create_account in book currency; rule account must exist at `rule add` (user error otherwise) — assumption. Done: `python3 -m unittest tests.test_automation && python3 -m unittest discover -s tests`

## invoices
Files: fin/invoices.py, tests/test_invoices.py. Spec s13 (except `report aging`, `tax add/list` which exist in taxes.py). Customers + invoices + payments; `invoice` and `customer` commands. Done: `python3 -m unittest tests.test_invoices && python3 -m unittest discover -s tests`

## bills
Files: fin/bills.py, tests/test_bills.py. Spec s14 (except `report aging`). `vendor`, `bill` commands. Done: `python3 -m unittest tests.test_bills && python3 -m unittest discover -s tests`

## ledgerreports
Files: fin/reports.py, tests/test_reports.py. Spec s8 and s17 (`report income`, `balance-sheet`, `networth`, `trial-balance`, `ledger`). Conversion: convert each account's per-currency total at the report date, then round the account's value (sum of account values for totals; totals computed from rounded account values so rows add up). Done: `python3 -m unittest tests.test_reports && python3 -m unittest discover -s tests`

## loansrecon
Files: fin/loans.py, fin/reconcile.py, tests/test_loans.py, tests/test_reconcile.py. Spec s9 and s16. Done: `python3 -m unittest tests.test_loans tests.test_reconcile && python3 -m unittest discover -s tests`

## agingtax  (wave 2)
Files: fin/aging.py, tests/test_aging.py. Spec s13 `report aging`, s14 aging, s15 `report tax`, using invoices.py/bills.py functions from the contract (already merged). Done: `python3 -m unittest tests.test_aging && python3 -m unittest discover -s tests`

## httpapi  (wave 2)
Files: fin/api.py, tests/test_api.py. Spec s10 and s11 for API. `serve --port N` using http.server (ThreadingHTTPServer ok), a fresh sqlite connection + transaction per request, call the plain functions (base_cmds, invoices, reports, aging). Permissions via `ctx.authorize(write)` — all POSTs are writes; map `UserError.status` (400/401/403) to responses; 404 for unknown paths (and unknown invoice id -> 400 is fine). Test by starting the server in a thread on port 0 (factor a `make_server(db, port)` function) with urllib. GET /transactions, /accounts, /balances?at=, /reports/income?from&to[&currency], /reports/balance-sheet?at, /invoices, /invoices/ID, /reports/aging?at[&payables=1], /audit. Done: `python3 -m unittest tests.test_api && python3 -m unittest discover -s tests`
