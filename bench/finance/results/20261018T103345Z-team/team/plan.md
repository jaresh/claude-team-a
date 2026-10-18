# Plan
Goal: small-business finance CLI+API per .claude/team/spec.md (the user's full request; read the sections for your task).
Check: `python3 -m unittest discover -s tests` (use `python3`, not `python`).

## Contract / Conventions (already built by lead, working, tested: fin/core.py, fin/cli.py, fin/ledger.py)
- Read fin/core.py and fin/cli.py and fin/ledger.py first. NEVER reimplement: money fmt/rounding (core.fmt, round_cents),
  parsing (parse_date/parse_month/parse_amount/parse_decimal/parse_currency/parse_posting), add_months/month_end/next_month,
  errors (raise core.UserError), accounts (core.ensure_account/get_account/in_tree), posting transactions
  (core.add_transaction, which checks closed periods and balance), sums (core.account_sums), rates (core.convert/get_rate),
  balances with ancestors (ledger.balances).
- Each module has `register(root, report)`: `root` = top-level subparsers, `report` = subparsers of `report` (add `report X` commands there
  with core.command(report, "income", handler, ...)). Command groups: core.group(root, "name") then core.command(g, "add", handler, write=True).
  Handler `def cmd_x(ctx, args)` returns the JSON-able document (exactly what the spec says; CLI prints it). ctx.conn (sqlite3, Row),
  ctx.user, ctx.currency (book currency), ctx.audit(action, target) for each data-changing command (spec section 11 names).
  write=True for data-changing commands (cli enforces --user/roles); admin=True for admin-only. Raise UserError for user errors; cli rolls back everything.
- Own tables: module-level `SCHEMA = "CREATE TABLE IF NOT EXISTS ..."` string (cli runs it on open). Store amounts as TEXT Decimal strings.
- Output amounts with core.fmt. Option dest for `--from` is read via `getattr(args, "from")`.
- Tests: tests/test_<yourmodule>.py using tests/helpers.py BookCase (see tests/test_ledger.py); cover every command of your sections incl. error cases (exit 2).
  Unit tests only for your files. Never edit others' files (log any needed shared-file change in .claude/team/changes.md and tell lead instead of making it).
- Done check for all: `python3 -m unittest tests.test_<yourmodule> && python3 -m unittest discover -s tests`. Don't commit. Document assumptions in your handoff.

## banking
Files: fin/banking.py, tests/test_banking.py. Spec sections 5 (rule add/list, import), 6 (budget set, report budget), 7 (recurring add/run).
Audit actions: rule.add, import (account), budget.set ("ACCOUNT MONTH"), recurring.add (name), recurring.run (until date). Table for rules, budgets, recurring (+ created occurrences).
Import all-or-nothing (closed period => UserError). Budget account must be an expense account. report budget goes under `report`.
Done: as above with module banking.

## invoicing
Files: fin/invoicing.py, tests/test_invoicing.py. Spec sections 13 (tax, customer, invoices, report aging), 14 (vendor, bills, aging --payables), 15 (report tax).
Audit per spec section 11 (tax.add, customer.add, vendor.add, invoice.create/issue/pay, bill.create/pay). Put the invoice/bill JSON building in
functions (e.g. invoice_doc(conn, id), bill_doc(conn, id), create_invoice(conn,...), issue_invoice, pay_invoice, ...) usable by others. Payments must be stored with their date (aging counts only payments on or before DATE).
`report aging` is one command with optional --payables. Done: module invoicing.

## statements
Files: fin/statements.py, tests/test_statements.py. Spec sections 8 (report income, balance-sheet, networth), 17 (report trial-balance, report ledger).
Convert each account's per-currency balance with core.convert at the report date (--to/--at; networth: each month's last day), then fmt. Sign rules per spec. Done: module statements.

## loans
Files: fin/loans.py, tests/test_loans.py. Spec sections 9 (loan schedule; read-only, no --user needed) and 16 (reconcile ACCOUNT ...; audit `reconcile` target the account; table of cleared marks). Done: module loans.

## api (wave 2, after the above pass)
Files: fin/api.py, tests/test_api.py, plus add a `serve --port N` command: you may edit fin/cli.py only to add `api` to _modules() list (log in changes.md); fin/api.py has register(root, report) defining `serve`.
Spec section 10 + 11 for API. Implement by calling fin.cli.execute(db, user, argv) (argv excludes globals) for each request, one call per request, mapping UserError -> 400 (401/403 for missing/unknown user/role: check users table and role BEFORE running, for POST only; admin-only commands are user add/period close, not exposed except as below).
POST /transactions -> `txn add`; POST /invoices -> `invoice create`; /invoices/ID/issue -> `invoice issue`; /invoices/ID/payments -> `invoice pay`; GETs map to the --json commands. Viewer POST -> 403. Unknown path 404. ThreadingHTTPServer ok; tests start it on a free port in a thread/subprocess.
