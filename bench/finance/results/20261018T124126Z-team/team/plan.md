# Plan

## Goal
Small-business finance system `fin/` (Python 3.12+ stdlib only), CLI `python -m fin` + HTTP API,
per the full spec in `.claude/team/spec.md` (read the sections your task names).
**Check:** `python -m unittest discover -s tests` passes.

## Contract
- Lead-owned, already written: `fin/core.py` (shared helpers, full DB schema), `fin/cli.py`
  (global options, dispatch, output, errors), `fin/__main__.py`, `tests/helpers.py`, and the
  acceptance tests `tests/test_accept_*.py`. Do not edit these. If core lacks something, write
  it in your own module and say so in your handoff.
- Each command module `fin/<task>.py` defines `register(sub, report)`: `sub` is the top-level
  argparse subparsers, `report` the subparsers of the `report` command (add `report X`
  commands there). Each leaf parser calls
  `p.set_defaults(func=handler, perm=LEVEL)`, LEVEL one of `"read"` (changes nothing),
  `"write"` (editor+admin), `"admin"` (admin only), `"none"` (only `init`).
  cli.py checks `perm`, runs write handlers inside one DB transaction (rolled back on any
  error, so a failing command changes nothing), and prints the returned document (JSON with
  `--json`). Handlers have the signature `handler(ctx, args) -> doc` (dict/list of plain JSON
  values) and raise `core.UserError` for every user error. Handlers never print.
- Logic lives in plain domain functions `fn(ctx, ...) -> doc`; handlers only unpack `args`.
  Domain functions that change data call `ctx.audit(action, target)` exactly once (section 11
  of the spec gives action and target), and never check permissions or open transactions
  (callers do). The HTTP API (task `api`) calls these domain functions, so these names and
  signatures are fixed:
  - books: `list_accounts(ctx)`, `list_txns(ctx, account=None, from_=None, to=None)`,
    `add_txn(ctx, date, description, postings)` (postings: list of `(account, amount-str or None)`),
    `balances(ctx, at=None)`, `list_audit(ctx, by=None)`.
  - statements: `income(ctx, from_, to, currency=None)`, `balance_sheet(ctx, at, currency=None)`.
  - invoicing: `list_invoices(ctx, status=None)`, `show_invoice(ctx, id)`,
    `create_invoice(ctx, customer, date, lines)` (lines: list of dicts with keys description,
    quantity, price, tax_code (optional/None/"" = no tax)), `issue_invoice(ctx, id)`,
    `pay_invoice(ctx, id, amount, date, account)`, `aging(ctx, at, payables=False)`.
  All ids are ints; amounts passed in as strings.
- Tables: all defined in `core.SCHEMA` (read it). Amounts are stored as TEXT decimal strings
  (`core.fmt`), summed in Python as `Decimal`. Never use float.

## Conventions
- Use from `fin.core`: `UserError`, `dec`/`money`/`r2`/`fmt` (parse, round half up, format),
  `parse_date`, `parse_month`, `add_months`, `add_days`, `month_end`, `to_date`,
  `account_type`, `parse_currency`, `get_account`, `ensure_account`, `under`/`is_under`/
  `ancestors`, `check_open`, `parse_posting`, `post_txn` (ALL transactions go through it: it
  validates, balances, checks the closed period), `txn_doc`, `rate`, `convert`.
  `ctx.q/q1/x` run SQL; `ctx.currency` is the book currency; `ctx.meta/set_meta`.
- Repeated options (`--posting`, `--line`, `--clear`) use `action="append"`.
  Option `--from` uses `dest="from_"`.
- Error messages: lower-case, say what is wrong and the offending value.
- Tests: your own unit tests go in `tests/test_<task>.py`, using `tests/helpers.py`
  (`FinCase`: `self.fin(*argv, user=...)` returns the parsed JSON, `self.fin_err(*argv, user=...)`
  asserts exit 2, empty stdout, unchanged DB). Run one file with
  `python -m unittest tests.test_<task> tests.test_accept_<task>`.

## books  (done by the lead)
`fin/books.py` is written and passes `tests.test_accept_books`; use its commands to set up
test data. Do not edit it.

## banking
Files: `fin/banking.py`, `tests/test_banking.py`. Spec sections 5, 6, 7, 16: `rule add/list`,
`import`, `budget set`, `report budget`, `recurring add/run`, `reconcile`. Use tables
`rules`, `imported`, `budgets`, `recurring`, `recurring_done`, `cleared`. May change: anything in its own files.
Done: `python -m unittest tests.test_banking tests.test_accept_banking`.

## statements
Files: `fin/statements.py`, `tests/test_statements.py`. Spec sections 8, 9, 17:
`report income/balance-sheet/networth/trial-balance/ledger`, `loan schedule`. Conversion:
convert each account's per-currency raw balance with `core.convert` at the report date, sum
the converted (rounded) values; totals are sums of the shown values. May change: anything in its own files.
 Done: `python -m unittest tests.test_statements tests.test_accept_statements`.

## invoicing
Files: `fin/invoicing.py`, `tests/test_invoicing.py`. Spec sections 13, 14, 15: `tax add/list`,
`customer add/list`, `invoice create/issue/pay/show/list`, `vendor add/list`,
`bill create/pay/show/list`, `report aging [--payables]`, `report tax`. May change: anything in its own files.
Done: `python -m unittest tests.test_invoicing tests.test_accept_invoicing`.

## api  (wave 2)
Files: `fin/api.py`, `tests/test_api.py`. Spec section 10: `serve --port N` (perm read) with
`http.server.HTTPServer`, calling the domain functions above. For each request: POST needs
`X-User` → `ctx.user`, then `ctx.require("write")` (AuthError has `.status` 401/403), then
`ctx.run(fn, ...)`. UserError → 400 `{"error": msg}`; unknown path → 404 `{"error": ...}`;
bad JSON body → 400. Expose a function `make_server(db_path, port) -> HTTPServer` for tests
(port 0 = any free port). Done: `python -m unittest tests.test_api tests.test_accept_api`.
May change: anything in its own files. Unknown invoice id → 400 (it is a UserError).
