# Plan
Goal: small-business finance system, Python 3.12+ stdlib only. Full spec: `.claude/team/spec.md`
(the user's request; read the sections for your task). Check: `python3 -m unittest discover -s tests`.
Use `python3` (no `python`). Run CLI as `python3 -m fin ...`.

## Contract (already written by lead; READ fin/core.py, fin/cli.py, fin/admin.py, tests/helpers.py first)
- `fin/core.py`: UserError, money (`parse_amount`, `parse_decimal`, `q`, `fmt`), dates (`parse_date`,
  `parse_month`, `month_last_day`, `months_between`, `add_months(start,k)`, `add_years`), SCHEMA (ALL tables
  exist already - do not change the schema; ask nothing, use the tables as they are), `Ctx` with
  `post_txn`, `txn_dict`, `account`, `add_account`, `ensure_account`, `account_sums`, `rate`, `convert`,
  `to_currency`, `check_open`, `audit`, `currency`, `meta`.
- `fin/cli.py`: each module has `register(add)`; `p = add("group cmd", handler, write=bool)`; handler
  `(ctx, args) -> JSON-able object`. write=True commands need editor/admin and MUST call
  `ctx.audit(action, target)` exactly once on success (see spec section 11 for action/target names).
  Raise UserError for all user errors (bad input, unknown things). Money in JSON via `fmt`. Never float.
  All DB access via `ctx.conn` (sqlite3.Row). Do not commit; handler must not call conn.commit().
- Module names (cli.py MODULES): ledger, automation, reports, loans, reconcile, billing, api. Each task
  owns only its files `fin/<module>.py` and `tests/test_<module>.py`. Never edit core.py/cli.py/admin.py/
  helpers.py: if you need a change, log it in `.claude/team/changes.md` and work around it in your module
  (put private helpers in your module). Nothing outside your files may be touched.
- Tests: unittest, subclass `tests.helpers.FinCase`; cover every behavior and error case of your spec
  sections, with exact JSON expectations. Keep them fast (each CLI call is a subprocess).
- Exit code 2 / nothing on stdout for user errors is handled by cli.py. Validate input BEFORE writing
  so a failing command changes nothing (cli rolls back anyway).

## ledger
Files: fin/ledger.py, tests/test_ledger.py. Spec sections 1, 2, 3, 4 (account add/list, txn add/list,
balance, fx add, convert; audit actions account.add, txn.add, fx.add). `--posting ACCOUNT=AMOUNT` (split
at the LAST '='? no: account names have no '=', split at first '='); a posting with no '=' has no amount.
`balance` includes ancestors of accounts with postings. Done: `python3 -m unittest tests.test_ledger`.

## automation
Files: fin/automation.py, tests/test_automation.py. Spec sections 5, 6, 7 (rule, import, budget set,
`report budget MONTH`, recurring add/run). Register `report budget` via add("report budget", ...) (the
report group is shared with other modules; cli.py handles that). Use ctx.post_txn for transactions
(it checks closed periods); for import/recurring run check ALL rows/occurrences for closed periods first.
Recurring: store postings JSON in recurring.postings; occurrence k = add_months(start,k) etc.; record each
created date in recurring_done. Validate postings at `recurring add` (accounts exist, balance) without posting.
Done: `python3 -m unittest tests.test_automation`.

## reports
Files: fin/reports.py, tests/test_reports.py. Spec sections 8 and 17: `report income`, `report balance-sheet`,
`report networth`, `report trial-balance`, `report ledger ACCOUNT`. (NOT budget, aging, tax: others own those.)
Use ctx.account_sums + ctx.to_currency (convert each account's balance as of the report date). Done:
`python3 -m unittest tests.test_reports`. Tests create data via CLI (account add, txn add, fx add).

## loans
Files: fin/loans.py, fin/reconcile.py, tests/test_loans.py, tests/test_reconcile.py. Spec sections 9 and 16
(`loan schedule`, `reconcile`; audit action `reconcile`, target = account; loan schedule is read-only so
needs no user). Done: `python3 -m unittest tests.test_loans tests.test_reconcile`.

## billing
Files: fin/billing.py, tests/test_billing.py. Spec sections 13, 14, 15 plus aging in both directions and
the `--currency`-less tax report: `tax add/list`, `customer add/list`, `vendor add/list`, `invoice create/
issue/pay/show/list`, `bill create/pay/show/list`, `report aging` (with --payables), `report tax`. Store
lines/payments as JSON text in invoices/bills tables (columns lines, payments); compute totals on output
with Decimal. Use ctx.post_txn (checks closed periods; check BEFORE changing invoice status) and
ctx.ensure_account. Print the invoice/bill for each succeeding command. Done:
`python3 -m unittest tests.test_billing`.

## api   (wave 2, after the others are merged)
Files: fin/api.py, tests/test_api.py. Spec section 10 and the API part of 11. `register(add)` adds
`serve --port N` (read-only wrt audit: no --user). Implement with http.server (ThreadingHTTPServer) by
calling `fin.cli.invoke(db, argv, user)` for each endpoint (map JSON bodies to argv; UserError.status gives
the HTTP status: 400/401/403), so output equals the CLI --json output. POST needs header X-User (missing/
unknown -> 401, viewer -> 403; invoke raises these when user passed is None/unknown for write commands).
GET need no user. 404 for unknown paths (and bad invoice ids -> 400 or 404 your choice, document in a
comment). Tests start the server in a thread or subprocess on a free port. Server DB path: from `--db`
global option — NOTE handlers get only (ctx, args); get the path with `ctx.conn.execute("PRAGMA database_list")`
row[2]. Done: `python3 -m unittest tests.test_api`.
