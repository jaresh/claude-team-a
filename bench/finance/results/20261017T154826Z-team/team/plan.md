# Plan
Goal: small-business finance system in `fin/` (stdlib only). Full spec: .claude/team/spec.md (user's request, verbatim; read the sections for your task).
Check: `python3 -m unittest discover -s tests` (each task: its own tests/test_<task>.py).

## Contract / Conventions (shared code is DONE: fin/core.py, fin/cli.py, read them first, do NOT edit)
- Each command module `fin/cmd_<x>.py` defines `register(sub, report)`: `sub` = top-level subparsers, `report` = subparsers of the `report` command (shared; add `report.add_parser("income")` etc.). Optional `SCHEMA` string of `CREATE TABLE IF NOT EXISTS` (run on every connect; core tables in core.SCHEMA).
- Each leaf parser calls `set_defaults(func=fn, perm=P, audit=A)`: `fn(ctx, args)` returns a JSON-able result (ctx.conn, ctx.user); P in 'read'|'write'|'admin'|'none' (cli enforces --user/role; 'none' only for init); A = `lambda args, result: (action, target)` for data-changing commands, omit for reads. Raise `core.UserError` for user errors (cli rolls back everything and exits 2). Never print; never call sys.exit. Use `type=str` for all arguments and validate with core helpers (dec, parse_date, parse_month, parse_currency, parse_posting, fmt, q) so bad input is UserError.
- Money: Decimal only, `core.fmt` for output, `core.q` rounding. Transactions are created ONLY via `core.post_txn` (handles period closing, balancing, blank posting). Nested subcommands (e.g. `account add`) use `add_subparsers(dest=..., required=True)` on the parent parser.
- `init` is special: perm 'none', creates meta currency (key 'currency'), admin user, and sets `ctx.user = admin name` so cli writes audit entry 1.
- Reports needing currency conversion: `core.convert(conn, amount, from, to, date)` then `q`. Report positive-sign flip for income/liability/equity.
- Tests: use unittest with subprocess or `fin.cli.main([...])` with a temp db; cover every spec section of your task incl. error cases (exit 2, nothing changed). Teammates edit only files they own. Append a line to .claude/team/changes.md for any edit outside owned files (avoid).

## books
Owns fin/cmd_books.py, tests/test_books.py. Spec §1, §2, §3, §4, §11 (user add/list, audit list), §12 (period close/status). Commands: init, account, txn, balance, fx, convert, user, audit, period.
Done: `python3 -m unittest tests.test_books`

## bank
Owns fin/cmd_bank.py, tests/test_bank.py. Spec §5 (rule, import), §6 `budget set` ONLY (not report budget), §7 (recurring), §9 (loan schedule; add as `loan` command, perm 'read'). Import: whole import fails atomically on closed month/any error (core.post_txn raises; cli rolls back). Needs tables for imported-row dedupe and recurring (own SCHEMA). Recurring posting amounts are stored and run through post_txn at run time. For tests, create books via `fin.cli.main`; books module is being written in parallel, so if fin/cmd_books.py isn't there yet, wait/retry briefly, or set up a book directly with core.SCHEMA inserts.
Done: `python3 -m unittest tests.test_bank`

## reports
Owns fin/cmd_reports.py, tests/test_reports.py. Spec §6 `report budget`, §8, §17 (report income, balance-sheet, networth, budget, trial-balance, ledger). Budget table is created by bank module as `budgets`; define it yourself in your SCHEMA too with identical DDL: `CREATE TABLE IF NOT EXISTS budgets(account TEXT, month TEXT, amount TEXT, PRIMARY KEY(account,month))` (bank uses the same, using INSERT OR REPLACE). All reads (perm 'read'), no audit.
Done: `python3 -m unittest tests.test_reports`

## invoices
Owns fin/cmd_invoices.py, tests/test_invoices.py. Spec §13, §14, §15, §16 (tax, customer, vendor, invoice, bill, report aging, report tax, reconcile), plus audit actions in §11 for them. Own tables in SCHEMA. Use core.post_txn for postings (period check included); create accounts with core.ensure_account. Invoice number counter per year counts issued invoices.
Done: `python3 -m unittest tests.test_invoices`

## api (wave 2)
Owns fin/server.py (with `register(sub, report)` adding `serve --port N`, perm 'none' is NOT allowed: use perm 'read', func runs http.server until stopped), tests/test_api.py. Spec §10. Reuse the real command handlers: build `argparse` args via fin.cli.build_parser/run or call handlers directly; POST auth per §11 using cli.check_role and audit with the same actions as the CLI; one sqlite connection per request, run via cli.run so atomic/audited. Errors: UserError→400, 401 missing/unknown X-User, 403 role. Tests start the server on a free port in a thread/subprocess.
Done: `python3 -m unittest tests.test_api`
