# Plan
Goal: finance system per the full spec in .claude/team/spec.md (user's request, verbatim; read the sections for your task).
Check: `python3 -m unittest discover -s tests` (use `python3`, not `python`; tests call `sys.executable -m fin`).

## Contract / conventions (already written by lead, DO NOT edit fin/common.py, fin/cli.py, fin/core_cmds.py, tests/helpers.py, tests/test_core.py)
- Read fin/cli.py docstring and fin/common.py first. Commands are registered in a module's `register(sub)` with
  `p.set_defaults(func=fn, perm="read"|"write"|"admin")`; `fn(ctx, args)` returns JSON-able data (the exact document in the spec),
  raises `common.UserError` for user errors (never print, never sys.exit). Call `ctx.audit(action, target)` once per successful data change
  (action/target per spec section 11). Do NOT commit; cli commits.
- Money: Decimal only, `common.fmt` for output strings, `common.q2` rounds half up. Dates validated via `common.parse_date/parse_month`.
  Post transactions only through `common.post_transaction(conn, date, desc, [(account, Decimal|None)])` (it checks closed periods & balance).
  Create accounts with `common.ensure_account`. Convert with `common.convert` (+ fmt). All DB tables are already in common.SCHEMA; don't alter it.
  If you truly need a schema/common change, append a line to changes.md and add it in your own module instead.
- Raw balance of account = sum of Decimal(postings.amount) (amounts are stored as text), always sum in Python.
- Registered module names are fixed in cli.MODULES: core_cmds (done), ledger_cmds, import_cmds, report_cmds, invoice_cmds, misc_cmds.
- Tests: write tests/test_<task>.py using `from tests.helpers import FinTest` (see helpers: self.ok/self.bad/self.acct/self.txn).
  Cover every spec item of your task, incl. user errors (exit 2, empty stdout). Never define test helpers named like unittest methods.
- Output "no -0.00": always use common.fmt. Unspecified details: decide, and note assumptions in handoff (lead puts them in README).

## ledger  (owns fin/ledger_cmds.py, tests/test_ledger.py)
Spec sections 2 (txn add/list), 3 (balance), 4 (fx add, convert). txn add audit target = id as string; fx.add target `FROM/TO`.
Balance --at: only accounts with postings; ancestors included; per-currency sums. Done: `python3 -m unittest tests.test_ledger tests.test_core`

## imports  (owns fin/import_cmds.py, tests/test_imports.py)
Spec sections 5 (rule add/list, import), 6 (budget set, `report budget MONTH`), 7 (recurring add/run). `report` is a shared top-level
command with subcommands owned by several modules: to add one, in your register(sub) fetch/create the group via
`common`-free helper: use `fin/reportgroup.py` (lead provides: `get_report_sub(sub)` returns the shared `report` subparsers; call it, then `.add_parser("budget")`).
import: whole file validated first (closed period, bad rows) then inserted atomically; use post_transaction per row. Dedup via table `imported`
(n = occurrence index within identical rows in the same file so repeats within one file are skipped only if the first exists... per spec: identical row already imported OR earlier in the same file => skipped).
Budget must be an expense account. Done: `python3 -m unittest tests.test_imports tests.test_core`

## reports  (owns fin/report_cmds.py, tests/test_reports.py)
Spec sections 8 (report income, balance-sheet, networth), 9 (loan schedule), 16 (reconcile), 17 (trial-balance, ledger). Use get_report_sub.
Convert each account's amount at the report date, then round per account, sum rounded values for totals (assumption; document). Test data via CLI
`txn add`/`fx add` (the ledger module is built in parallel; until it exists in your tree, insert via common.post_transaction in tests — but prefer CLI once present).
Done: `python3 -m unittest tests.test_reports tests.test_core`

## invoicing  (owns fin/invoice_cmds.py, tests/test_invoicing.py)
Spec sections 13 (tax, customer, invoice, report aging), 14 (vendor, bill, aging --payables), 15 (report tax). Use get_report_sub for `aging` and `tax`.
Use tables invoices/invoice_payments (see SCHEMA comment); `paid` and `balance` computed from payments. Audit actions per spec 11.
Done: `python3 -m unittest tests.test_invoicing tests.test_core`

## api  (wave 2; owns fin/server.py, fin/misc_cmds.py (registers `serve --port N`), tests/test_api.py)
Spec sections 10 (and 11 for API). Implementation: for each endpoint build an argv for `cli.run`-style execution (add to server.py a helper that runs
`cli.build_parser()`/`cli.run(argv, out=StringIO)` with --db/--json/--user and a global lock) and map UserError -> 400, unknown/missing X-User -> 401,
role refusal (viewer or non-admin) -> 403, unknown path -> 404. Use ThreadingHTTPServer; test with a server on an ephemeral port in a thread/subprocess.
Done: `python3 -m unittest tests.test_api`
