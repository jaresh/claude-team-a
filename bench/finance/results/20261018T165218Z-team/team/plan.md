# Plan: small-business finance system

## Goal
A stdlib-only Python package `fin/` (CLI `python -m fin ...` + HTTP API) implementing the full
spec in `.claude/team/spec.md` (read the sections your task names; it is the authority).

**Check:** `python3 -m unittest discover -s tests` (all green).

## Contract

- Already written by the lead (do not edit; report problems in your handoff):
  - `fin/core.py`: errors (`FinError`, `NotFound`, `AuthError`), money (`parse_amount`, `q`,
    `fmt`, `dsum`), dates (`parse_date`, `parse_month`, `month_end`, `next_month`, `add_months`,
    `add_days`, `occurrence`, `days_between`), storage (`SCHEMA` with ALL tables, `connect`,
    `atomic`, `get_meta`/`set_meta`, `book_currency`, `parse_currency`, `init_book`), users/audit
    (`ROLES`, `require_role`, `audit`), periods (`closed_through`, `check_open`), accounts
    (`account_type`, `ancestors`, `is_under`, `get_account`, `create_account`, `ensure_account`),
    transactions (`parse_posting`, `build_postings`, `post_txn`, `get_txn`, `account_sums`),
    fx (`add_rate`, `get_rate`, `convert`). Read its docstrings; use these, never re-implement.
  - `fin/cli.py`: `@command(name, perm=..., args=[arg(...)], db=True)` registry. Handler
    signature `fn(conn, user, a) -> JSON-able result`. perm `"editor"`/`"admin"`: the framework
    checks the user and wraps the handler in one transaction (any FinError rolls everything
    back); `None` = read-only. `db=False`: no database, conn is None. Multi-word names share
    groups (`"report income"`, `"report budget"` from different modules is fine).
  - `tests/helpers.py`: `FinCase` with `self.book()`, `self.fin(...)`, `self.fin_err(...)`,
    `self.accounts(...)`, `self.txn(...)`.
  - Acceptance tests `tests/test_accept_*.py` (lead-owned, do not edit).
- Every mutating handler calls `core.audit(conn, user, ACTION, TARGET)` exactly once (actions in
  spec section 11). Helpers that post transactions (`core.post_txn`) do not audit.
- Service functions (used by the API in wave 2; CLI handlers are thin wrappers over them).
  Mutating ones do the audit but NOT the role check (callers do it):
  - `fin.books`: `list_accounts(conn)`, `add_txn(conn, user, date, description, postings)`
    (postings: list of `(account, amount_str_or_None)`), `list_txns(conn, account=None, frm=None,
    to=None)`, `balances(conn, at=None)`, `audit_list(conn, by=None)`.
  - `fin.statements`: `income(conn, frm, to, currency=None)`, `balance_sheet(conn, at, currency=None)`.
  - `fin.invoicing`: `create_invoice(conn, user, customer, date, lines)` (lines: list of dicts
    with `description`, `quantity`, `price`, optional `tax_code` (None/"" = no tax)),
    `issue_invoice(conn, user, id)`, `pay_invoice(conn, user, id, amount, date, account)`,
    `get_invoice(conn, id)` (raises `core.NotFound` for an unknown id), `list_invoices(conn,
    status=None)`, `aging(conn, at, payables=False)`.
  All return exactly the JSON documents the spec shows.

## Conventions
- Money: parse with `core.parse_amount`, round with `core.q`, output with `core.fmt`. Never float.
- Validate dates with `core.parse_date` / `core.parse_month`; ids with `int()` → FinError on bad.
- User errors: `raise core.FinError("message")` (or `core.NotFound` for unknown ids). Never print,
  never `sys.exit`. The framework prints `error: ...` and exits 2.
- Options are argparse args via `arg(...)`; repeated options use `action="append"`.
- Each module has its own unit tests `tests/test_<module>.py` using `FinCase`.
- Assumptions you make: list them at the end of your handoff (the lead puts them in README).

## books (done by the lead)
`fin/books.py` is written and passes `tests.test_accept_books`: init, account, txn, balance, fx,
convert, user, audit, period commands and the `fin.books` service functions. Read-only for
teammates; use these commands in your tests.

## banking
Files: `fin/banking.py`, `tests/test_banking.py`.
Spec sections 5, 6, 7, 16: `rule add/list`, `import FILE --account [--date-col --desc-col
--amount-col --skip-header]`, `budget set ACCOUNT MONTH AMOUNT` (expense accounts only),
`report budget MONTH`, `recurring add NAME --every --start --posting...` (validate with
`core.build_postings`; store postings as JSON in table `recurring`), `recurring run --until`
(uses `core.occurrence`; the `created` column counts occurrences already made),
`reconcile ACCOUNT --date --balance [--clear ID ...]` (table `cleared`). Tables for these are in
core.SCHEMA (`rules`, `import_rows`, `budgets`, `recurring`, `cleared`). Rules: account must
exist; invalid regex is a user error. Import: whole file atomic; bad row → user error.
May change: only its files. Must not touch: core.py, cli.py, helpers, acceptance tests, other
modules. Done: `python3 -m unittest tests.test_accept_banking tests.test_banking`.

## statements
Files: `fin/statements.py`, `tests/test_statements.py`.
Spec sections 8, 9, 17: `report income --from --to [--currency]`, `report balance-sheet --at
[--currency]`, `report networth --from MONTH --to MONTH [--currency]`, `report trial-balance
--at` (book currency), `report ledger ACCOUNT --from --to`, `loan schedule PRINCIPAL RATE MONTHS
--start` (db=False). Conversion: convert each account's sum (from `core.account_sums`) from the
account's currency into the target currency with `core.convert` at the report date, then total
the converted values. Plus the `fin.statements` service functions.
May change / must not touch: as banking. Done: `python3 -m unittest tests.test_accept_statements tests.test_statements`.

## invoicing
Files: `fin/invoicing.py`, `tests/test_invoicing.py`.
Spec sections 13, 14, 15: `tax add/list`, `customer add/list`, `vendor add/list`, `invoice
create/issue/pay/show/list`, `bill create/pay/show/list`, `report aging --at [--payables]`,
`report tax --from --to`. Tables `taxes`, `customers`, `vendors`, `invoices`, `invoice_lines`,
`bills`, `bill_lines`, `payments` are in core.SCHEMA. Invoice numbering counter: meta key
`invseq:YYYY`. Postings via `core.post_txn` (checks closed periods), accounts via
`core.ensure_account`. Payment amount must be > 0. Invoice payment account: asset; bill payment
account: asset or liability. Plus the `fin.invoicing` service functions.
May change / must not touch: as banking. Done: `python3 -m unittest tests.test_accept_invoicing tests.test_invoicing`.

## api (wave 2)
Files: `fin/api.py`, `tests/test_api.py`.
Spec section 10. `make_server(db_path, host="127.0.0.1", port=0)` returns an
`http.server.HTTPServer` whose handler opens `core.connect(db_path)` per request; command
`serve --port N` (perm None) calls it and `serve_forever()`. Routes as in the spec; POST: read
`X-User`, `core.require_role(conn, user, "editor")` inside `core.atomic(conn)` with the service
call. Errors: `FinError` → its `.status` (400, 401, 403, 404) with `{"error": msg}`; unknown
path → 404; bad JSON body → 400. Query params `at`, `from`, `to`, `payables`. Service functions
only (fin.books / fin.statements / fin.invoicing); `GET /audit` → `books.audit_list(conn)`.
May change: only its files. Done: `python3 -m unittest tests.test_accept_api tests.test_api`.
