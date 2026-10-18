# Plan
Goal: small-business finance system, Python 3.12 stdlib only; full spec in `.claude/team/spec.md` (the user's request, verbatim; read the sections of your task, and section "Stack and conventions").
Check: `python3 -m unittest discover -s tests` (use `python3`, there is no `python`).

## Contract / conventions (ALREADY WRITTEN by lead; read fin/core.py, fin/cli.py, fin/cmd_admin.py, tests/helpers.py first)
- Each command module `fin/<module>.py` defines `register(sub, report_sub)`: `sub` is the top-level subparsers, `report_sub` the subparsers of `report`. Each leaf parser calls `p.set_defaults(func=fn, perm='read'|'write'|'admin')`. `fn(ctx, args)` returns the JSON-able result (strings for money via `fmt`), raises `UserError` on user error, and calls `ctx.audit(action, target)` itself on success for data-changing commands (see spec section 11 for actions). Everything runs in one DB transaction, rolled back on error; permission checks are done by cli.py. Do not edit cli.py/core.py/cmd_admin.py: if you need a change, append a line to .claude/team/changes.md and work around it.
- Use core helpers: `D` (parse decimal), `q`, `fmt`, `parse_date/check_date/parse_month`, `add_months`, `ctx.post(...)`, `ctx.ensure_account`, `ctx.convert`, `ctx.balances`, `ctx.require_open`, `ctx.txn`. Money stored as Decimal text. Never float.
- Tables are all in core.SCHEMA. Billing contract: `invoices`/`bills` rows: party = customer/vendor name, ref = bill ref (NULL for invoices), lines = JSON list of the line dicts exactly as printed in the document JSON, net/tax/total/paid = decimal text, status as in spec (invoice: draft/issued/partial/paid; bill: open/partial/paid), number = invoice number or NULL. `doc_payments(kind 'invoice'|'bill', doc_id, date, amount, txn_id)` gets one row per payment. Reports needing these read these tables directly.
- Tests: each task writes `tests/test_<task>.py` using `tests.helpers.FinCase` (subprocess CLI; `self.init()`, `self.ok(...)`, `self.bad(...)`), covering its spec sections incl. error cases (exit 2, empty stdout, nothing changed) and permissions/audit entry. Don't shadow unittest method names. Each module must be importable alone and not import other command modules.
- Dispatch: `report` subcommands are registered through `report_sub.add_parser(name)`.

## books
Files: fin/cmd_books.py, tests/test_books.py. Spec sections 1, 2, 3, 4 (account add/list, txn add/list, balance, fx add, convert). Account names: validate via ctx.ensure_account; `account add` of an existing one is a user error; audit `account.add`, `txn.add`, `fx.add`. Posting arg `ACCOUNT=AMOUNT` or `ACCOUNT` (split on last '='). txn amounts like "-12.50"; remember argparse may treat "-5" args oddly: accept `--posting=X` forms too. fx rates must be positive. Done: `python3 -m unittest tests.test_books tests.test_core_admin`. Don't touch other files.

## imports
Files: fin/cmd_import.py, tests/test_imports.py. Sections 5, 6, 7 (rule add/list, import, budget set, report budget, recurring add/run). Import is all-or-nothing; closed-period check for every row first; dedupe within the file and against `imported` table. recurring: store postings JSON (account, amount str|null); occurrence n date = start + n months/weeks/years anchored on start (use core.add_months; yearly = add_months(start, 12n)); track created in recurring_done. Create parse helper locally for `ACCOUNT=AMOUNT`. Done: `python3 -m unittest tests.test_imports`. Tests may set up accounts via `account add` CLI. Don't touch other files.

## reports
Files: fin/cmd_reports.py, tests/test_reports.py. Sections 8, 17 (report income, balance-sheet, networth, trial-balance, ledger). Use ctx.balances (raw sums on each account) and ctx.convert per currency amount at the report's date. Round after converting each account's per-currency amount, then sum. Section 3 `balance` is NOT yours. Done: `python3 -m unittest tests.test_reports`. Tests set up data via CLI `txn add`/`fx add`. Don't touch other files.

## loans
Files: fin/cmd_loan.py, tests/test_loans.py. Section 9 (`loan schedule`, read-only perm). Use Decimal with enough precision (getcontext prec 50 locally). Done: `python3 -m unittest tests.test_loans`. Don't touch other files.

## invoicing
Files: fin/cmd_invoicing.py, tests/test_invoicing.py. Section 13 entirely (tax add/list, customer add/list, invoice create/issue/pay/show/list, `report aging --at DATE [--payables]` for invoices AND bills (bills read from `bills`/`doc_payments` tables per contract; due, total, status as in the contract)). Period checks on issue/pay. Another teammate (bills) writes fin/cmd_bills.py (vendor/bill) using the tax table; tax rates stored as given text in `taxes`. Done: `python3 -m unittest tests.test_invoicing`. Don't touch other files; in tests for aging of bills, insert bill rows via sqlite3 directly into the db file.
 (Add `parent` flags carefully: `--payables` is a store_true flag.)

## bills
Files: fin/cmd_bills.py, tests/test_bills.py. Section 14 except aging (vendor add/list, bill create/pay/show/list). Tax codes are rows in `taxes` (add them in tests with the CLI `tax add CODE RATE`, which another teammate writes in cmd_invoicing.py; if it isn't present yet, insert into the DB with sqlite3 directly in test setUp). Bill ref unique per vendor. Period checks. Done: `python3 -m unittest tests.test_bills`. Don't touch other files.

## taxrecon
Files: fin/cmd_taxrecon.py, tests/test_taxrecon.py. Sections 15 (`report tax`) and 16 (`reconcile`). report tax reads invoices (status != draft, by invoice date) and bills tables per contract; tests insert rows via sqlite3 directly. Done: `python3 -m unittest tests.test_taxrecon`. Don't touch other files.

## api (wave 2)
Files: fin/api.py, tests/test_api.py. Section 10 plus 11's API rules. `register(sub, report_sub)` adds `serve --port N` (set_defaults(func=serve, perm='read', serve=True)). Handler maps each route to the CLI handlers by building argparse namespaces via `fin.cli.build().parse_args([...])` and calling `fin.cli.run(ctx, args)` with a new connection per request (reuse the real command code so output matches; no duplicate logic); X-User for POST, 401/403/400 mapping (UserError message -> 400, role problems -> 401/403: check user/role yourself before calling, using the rule: viewer cannot POST at all; editor/admin ok). Tests start the server in a thread or subprocess on a free port. Done: `python3 -m unittest tests.test_api`.
