# Plan

## Goal
Small-business finance system, Python stdlib only. Full spec: `.claude/team/spec.md` (the user's request,
word for word; read your sections). Run python as `python3`.

**Check:** `python3 -m unittest discover -s tests`

## Contract (already written by the lead — READ fin/cli.py, fin/db.py, fin/money.py, fin/errors.py, tests/helpers.py first)
- Each feature module `fin/<module>.py` defines `register(R)` (and optionally `SCHEMA`, a string of
  `CREATE TABLE IF NOT EXISTS ...` run on every connect). In `register`: `p = R.add("account add", access="write")`
  (access "read" | "write" | "admin"), add argparse args to `p`, then `p.set_defaults(func=handler)`.
  Two-level commands only ("report income", "loan schedule"); registering several under one group is fine.
- `handler(book, args) -> JSON-able result or None`. `book` is `fin.db.Book`. The CLI already begins/commits/rolls back
  the transaction and checks users/roles. Raise `fin.errors.UserError` for every user error (never print or sys.exit).
  Call `book.audit(action, target)` once for each successful data-changing command (exact action/target in spec §11).
- Use the Book helpers: `ensure_account`, `require_account`, `post_txn` (checks balance + closed period; returns the txn
  document), `txn_doc`, `sums(frm,to)`, `rate`, `convert`, `check_open`, `currency`. Use `fin.money` (`parse_amount`,
  `parse_decimal`, `round_cents`, `fmt`, `check_date`, `check_month`, `parse_date`, `add_months`, `add_years`, `month_end`...).
  NEVER write your own money formatting, date validation, rounding or posting-insert code. Never use float.
  If a shared file lacks something, do not edit it: implement a private helper in your own module and note it in your handoff.
- Output amounts only via `fmt()`. Validate every date/month/amount/currency argument (user error on bad input).
  Command results are exactly the JSON documents in the spec (same key order as the examples).
- Data written by commands that modify must roll back on UserError automatically (cli does it) — just raise before/after writing.
- Tests: `unittest`, file `tests/test_<module>.py`, subclass `tests.helpers.FinTestCase` (`self.ok(*argv)`, `self.bad(*argv)`,
  `self.mkacct(...)`, `self.book()`). Every spec section of your task needs tests incl. error cases (exit 2, empty stdout, nothing changed).
  Don't use test-helper names like `fail`, `run`, `setUp` overrides without calling super. Other modules may not exist yet while you
  work: for fixtures, create accounts via `self.mkacct(...)` and transactions via `self.book().post_txn(...)` (autocommit connection)
  rather than through other teammates' commands.
- Own only your files. Do not edit fin/cli.py, db.py, money.py, errors.py, tests/helpers.py or other tasks' files. Log nothing else in changes.md unless you edit a shared file (you shouldn't).

## basics
Files: `fin/basics.py`, `tests/test_basics.py`. Spec §1 (except init, already done), §2, §3, §4, §11 (user add/list, audit list), §12 (period close/status).
Commands: account add/list, txn add/list, balance, fx add, convert, user add/list, audit list, period close/status.
`period close` and `user add` are access="admin"; reads "read". `audit list`, `account list`, `txn list`, balance, convert, user list, period status are "read".
`txn add` posting arg `ACCOUNT=AMOUNT` or `ACCOUNT` (split on the last `=`... account names contain no `=`, so first `=`).
Currency args upper-cased, 3 letters. `fx add` RATE must be positive. Done: `python3 -m unittest tests.test_basics`.

## importing
Files: `fin/importing.py`, `tests/test_importing.py`. Spec §5, §6, §7 (rule add/list, import, budget set, report budget, recurring add/run).
Use own tables via SCHEMA (rules, imported rows for dedupe, budgets, recurring + created occurrences).
Import: all-or-nothing (closed month in any row, bad row -> user error, nothing imported). Imported rows post via `book.post_txn`,
the category account via `book.ensure_account`. Rule ACCOUNT must be an existing or creatable account name (validate; create it on use via ensure_account).
Validate regex on `rule add`. `budget set` requires an existing expense account. `recurring run` must be idempotent and check closed periods for all occurrences first.
Done: `python3 -m unittest tests.test_importing`.

## statements
Files: `fin/statements.py`, `tests/test_statements.py`. Spec §8 (report income, balance-sheet, networth) and §17 (report trial-balance, report ledger).
All "read". Convert each account's balance per currency with `book.convert(amount, cur, target, at)` (rounded) and sum the converted
values per reported name; totals are sums of the per-account rounded values. Test conversion with `book.x("INSERT INTO rates ...")` fixtures.
networth: assets/liabilities shown positive (liabilities negated), networth = assets − liabilities.
`report ledger` amounts are in ACCOUNT's currency (descendants share it in practice; sum per account's own currency only, skip nothing).
Done: `python3 -m unittest tests.test_statements`.

## invoicing
Files: `fin/invoicing.py`, `tests/test_invoicing.py`. Spec §13, §14, §15 (tax, customer, vendor, invoice, bill, report aging, report tax).
Own tables via SCHEMA. Invoice/bill documents exactly as spec; `paid` = sum of payments; status draft/issued/partial/paid (bills: open/partial/paid).
Invoice number sequence per year counts issued invoices of that year. Payments and issuing post via `book.post_txn` (closed-period check is inside it).
Store payments with their date (needed for aging "payments on or before DATE"). Use `Decimal` for quantity; show quantity as given.
`report aging` registered here too (`--payables` flag, `--at` required). `report tax` ignores draft invoices. Done: `python3 -m unittest tests.test_invoicing`.

## loanrec
Files: `fin/loanrec.py`, `tests/test_loanrec.py`. Spec §9 (loan schedule, "read") and §16 (reconcile, access "write", audit `reconcile`).
Cleared marks live in the `cleared` column of the `postings` table (per posting; reconcile marks the postings to ACCOUNT of the given transactions).
Loan math with Decimal only (use `(1+r)**-MONTHS` on Decimals with sufficient precision, e.g. localcontext prec=50). Done: `python3 -m unittest tests.test_loanrec`.

## api (wave 2)
Files: `fin/api.py`, `tests/test_api.py`. Spec §10 (+ §11 for the API). Register `serve` (access "read", `--port N`, no user needed).
Implement by calling `fin.cli.execute(argv, db=PATH, user=X_USER_or_None)` for every route (e.g. GET /accounts -> ["account","list"]);
build argv from the request (txn add with `--posting ACC=AMT` / `--posting ACC`, invoice create `--line "desc;qty;price;tax"`, etc).
Errors: AuthError kind unauthenticated -> 401, forbidden -> 403, other UserError -> 400 `{"error": msg}`, unknown path -> 404. POST needs X-User
(missing -> 401 even before parsing the body); GETs need none. Body must be valid JSON object else 400. Use `ThreadingHTTPServer`
bound to 127.0.0.1; tests start it on port 0 in a thread. Same JSON documents as CLI. POST success: 201 for creations (/transactions, /invoices), 200 otherwise.
Needs invoices' commands (invoice create/issue/pay/show/list, report aging, audit list). Done: `python3 -m unittest tests.test_api`.
