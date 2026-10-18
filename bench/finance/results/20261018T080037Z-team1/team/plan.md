# Plan
**Goal**: small-business finance system in `fin/` (stdlib only). Full spec: `.claude/team/spec.md` (the user's request, sections 1-17; follow it exactly). Tests with `python3 -m unittest discover -s tests` (no `python` binary; use `python3`).
**Check**: `python3 -m unittest discover -s tests` passes.

## Conventions (lead already wrote fin/core.py, fin/cli.py, tests/helpers.py: READ them first)
- Each module `fin/<name>.py` defines `register(sub, report_sub)`: `sub` = top-level argparse subparsers, `report_sub` = subparsers of `report` (add `report_sub.add_parser("income")` etc.). Add commands with `sub.add_parser(...)`, nested groups with `.add_subparsers(dest=..., required=True)` (parser_class is inherited). Bind every leaf: `core.bind(parser, "txn add", handler)`; key = full command words ("account list", "report income"). Handler `fn(ctx, args) -> JSON-able data` (the CLI prints it; return exactly the documented JSON document). Handlers raise `core.UserError(msg)` for any user error; never print, never sys.exit. Everything runs in one transaction, rolled back on error.
- Use core helpers: `dec`, `q2`, `fmt` (all amount output), `pdate`, `pmonth`, `add_months`, `month_end`, `ctx.account/ensure_account/add_txn/txn_dict/convert/rate/check_open/audit(action,target)`. Never use float. Never write own rounding/format/parse code. The DB schema is in core.SCHEMA (don't change it; if you truly need a change, add a line to changes.md and ask via handoff).
- Permission checks (needs --user, roles) are done in cli.py via core.READONLY/ADMIN_ONLY. Handlers only call `ctx.audit(action, target)` once on success when they change data (spec section 11 list). If a command changes nothing (e.g. closing an earlier month), don't audit.
- Do not edit core.py, cli.py, helpers.py or other modules' files or tests. Each task adds tests `tests/test_<name>.py` (subclass `tests.helpers.FinTestCase`; use `self.ok(...)`, `self.bad(...)`; other tests in the same file may use earlier modules). Cover every spec section of the task incl. error cases (exit 2 & nothing changed) and audit entries.
- Tasks run one at a time, in order. Earlier modules are available.
- Done check for each task: `python3 -m unittest discover -s tests` (whole suite must pass).

## ledger
Files: fin/ledger.py, tests/test_ledger.py. Spec sections 1 (accounts; `init` is already done in cli.py), 2, 3, 4, 11 (user add/list, audit list), 12 (period close/status; txn add must use the closed-period check, which add_txn already does). `convert` command: `convert AMOUNT FROM TO --at DATE`.

## automation
Files: fin/automation.py, tests/test_automation.py. Sections 5 (rule, import), 6 (budget set, `report budget`), 7 (recurring add/run), 9 (loan schedule). Imports/recurring run: closed-period check for every row first (all-or-nothing; the transaction itself rolls back on UserError anyway). Create txns with ctx.add_txn. Recurring occurrences: compute each from the start with add_months(start,k) (monthly), +7k days, yearly with add_months(start,12k) (Feb 29 -> Feb 28 works).

## billing
Files: fin/billing.py, tests/test_billing.py. Sections 13 (tax, customer, invoice incl. `report aging`), 14 (vendor, bill, `report aging --payables`; `--payables` is a flag on the same `report aging` parser). Store invoice lines as JSON in invoices.lines, payments in invoice_payments/bill_payments (store the posting txn id). Helper functions to build the invoice dict: also expose `invoice_dict(ctx, id)` and `bill_dict(ctx, id)` in billing.py (the API module will call the CLI, not these).

## reports
Files: fin/reports.py, tests/test_reports.py. Sections 8 (report income, balance-sheet, networth), 15 (report tax; tax of issued invoices from invoices table lines by invoice date and status != draft, tax of bills from bills table), 16 (reconcile), 17 (report trial-balance, report ledger). Currency conversion via ctx.convert at the report date. Reports are by posting account name (not ancestors) except `report ledger` (account and descendants).

## api
Files: fin/api.py, tests/test_api.py. Section 10 (+ the 11 header rules for POST). Implement `serve --port N` (http.server ThreadingHTTPServer, JSON). Do it by translating each request into a CLI argv and calling `fin.cli.execute(db_path, user, argv)` (it returns data or raises UserError; map to 201/200/400/401/403). For 401/403 determine the user/role yourself in api.py: missing/unknown X-User -> 401; role viewer -> 403 on any POST; (editor/admin allowed; POST endpoints are only txn/invoice ops). `GET /audit` -> `audit list`. Tests: start the server on a free port in a thread (e.g. ThreadingHTTPServer built by a function `make_server(db, port)` that you expose; `serve` handler calls it and serve_forever()) and use urllib.
