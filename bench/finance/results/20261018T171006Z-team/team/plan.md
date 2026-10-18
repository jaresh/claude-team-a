# Plan

## Goal
A small-business finance system, package `fin/` (Python 3.12+, stdlib only), run as
`python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`. Full spec (word for word, the
source of truth): `.claude/team/spec.md`. Section numbers below refer to it.

## Check
`python -m unittest discover -s tests` (all green). Lead's acceptance tests: `tests/test_acc_*.py`
(read-only for teammates). Each task adds its own unit tests in `tests/test_<task>.py`.

## Contract

Already written by the lead (do not edit; if you need a change, say so in your handoff):
- `fin/core.py`: `UserError`, `AuthError`, `NotFound`; money `parse_decimal`, `parse_amount`
  (rounds half up to cents), `money`, `fmt` (Decimal or int cents -> `"12.50"`, never `-0.00`),
  `to_cents`, `from_cents`; dates `parse_date`, `parse_month`, `to_date`, `add_months(d, n, day=None)`
  (clamps to month end; pass `day=start.day` / compute from the start each time, never chain),
  `add_days`, `month_end`, `next_month`, `utc_now`; `get_meta`/`set_meta`, `book_currency`,
  `parse_currency`; `require_role`, `audit`; accounts `account_type`, `ancestors`, `get_account`
  (UserError if unknown), `account_exists`, `ensure_account(conn, name, currency=None)` (creates
  missing parents), `is_under(account, prefix)`; periods `closed_through`, `check_open(conn, date)`;
  transactions `parse_posting("A=1.00")`, `post_transaction(conn, date, desc, [(account, Decimal|None)])`
  -> id (validates everything incl. closed period), `get_transaction(conn, id)` -> transaction doc,
  `posting_sums(conn, frm=None, to=None)` -> `{(account, currency): Decimal}`; fx `get_rate`,
  `convert(conn, amount, frm, to, at)` (rounded; UserError if no rate); `register_schema(ddl)`.
- Core tables: `meta`, `users`, `audit`, `accounts(name,type,currency)`, `transactions(id,date,description)`,
  `postings(id,txn_id,seq,account,amount INTEGER cents,currency)`, `fx(id,date,frm,too,rate TEXT)`.
  Feature tables: each module calls `core.register_schema("CREATE TABLE IF NOT EXISTS ...;")` at
  import time for its own tables, prefixed with nothing special but owned only by that module.
- `fin/cli.py`: `@command("txn add", arg("--date", required=True), ..., write=None|"editor"|"admin")`
  registers `func(ctx, ns)`; it runs inside one DB transaction (rolled back on any exception),
  the role check is done before the call, and the return value is the JSON document printed.
  `ctx.conn`, `ctx.user`, `ctx.audit(action, target)`. Raise `UserError` for every user error
  (exit 2, nothing printed to stdout, nothing changed). `init` is done by the lead in cli.py.
  `cli.execute(db, user, name, ns)` and `cli.namespace(name, **values)` are used by the API.
  `raw=True` commands get `func(db_path, ns)` (only `serve`).
- Feature modules (imported by cli.MODULES): `fin/ledger.py`, `fin/banking.py`,
  `fin/statements.py`, `fin/invoicing.py`, `fin/api.py`.

Command names and argument dests (the API builds namespaces with these exact dests). Positional
args use the lowercase dest as name with a metavar; `--from` always uses `dest="frm"`.
Write role: `editor` for every data-changing command except `user add`, `period close` (`admin`).

| Module | Command | Args (dest) | Writes / audit action, target |
|---|---|---|---|
| ledger | `user add` | `name`, `--role` (choices) | admin / `user.add`, name |
| ledger | `user list` | | |
| ledger | `account add` | `name`, `--currency` | `account.add`, name |
| ledger | `account list` | | |
| ledger | `txn add` | `--date`, `--desc`, `--posting` (append, list of `ACCOUNT[=AMOUNT]`) | `txn.add`, id |
| ledger | `txn list` | `--account`, `--from`(frm), `--to` | |
| ledger | `balance` | `--at` | |
| ledger | `fx add` | `date`, `frm`, `to`, `rate` | `fx.add`, `FROM/TO` |
| ledger | `convert` | `amount`, `frm`, `to`, `--at` (required) | |
| ledger | `audit list` | `--by` | |
| ledger | `period close` | `month` | admin / `period.close`, month |
| ledger | `period status` | | |
| banking | `rule add` / `rule list` | `pattern`, `account` | `rule.add`, pattern |
| banking | `import` | `file`, `--account`, `--date-col`(int,0), `--desc-col`(1), `--amount-col`(2), `--skip-header` | `import`, account |
| banking | `budget set` | `account`, `month`, `amount` | `budget.set`, `ACCOUNT MONTH` |
| banking | `report budget` | `month` | |
| banking | `recurring add` | `name`, `--every`, `--start`, `--posting` (append) | `recurring.add`, name |
| banking | `recurring run` | `--until` | `recurring.run`, the date |
| banking | `reconcile` | `account`, `--date`, `--balance`, `--clear` (append, int) | `reconcile`, account |
| statements | `report income` | `--from`(frm), `--to`, `--currency` | |
| statements | `report balance-sheet` | `--at`, `--currency` | |
| statements | `report networth` | `--from`(frm), `--to` (months) | |
| statements | `report trial-balance` | `--at` | |
| statements | `report ledger` | `account`, `--from`(frm), `--to` | |
| statements | `loan schedule` | `principal`, `rate`, `months`(int), `--start` | |
| invoicing | `tax add` / `tax list` | `code`, `rate` | `tax.add`, code |
| invoicing | `customer add` / `customer list` | `name`, `--terms`(int, 30) | `customer.add`, name |
| invoicing | `vendor add` / `vendor list` | `name`, `--terms`(int, 30) | `vendor.add`, name |
| invoicing | `invoice create` | `--customer`, `--date`, `--line` (append, `DESC;QTY;PRICE;TAXCODE`) | `invoice.create`, id |
| invoicing | `invoice issue` | `id`(int) | `invoice.issue`, id |
| invoicing | `invoice pay` | `id`(int), `amount`, `--date`, `--account` | `invoice.pay`, id |
| invoicing | `invoice show` / `invoice list` | `id`(int) / `--status` | |
| invoicing | `bill create` | `--vendor`, `--ref`, `--date`, `--line` (append, `DESC;AMOUNT;ACCOUNT;TAXCODE`) | `bill.create`, id |
| invoicing | `bill pay` | `id`(int), `amount`, `--date`, `--account` | `bill.pay`, id |
| invoicing | `bill show` / `bill list` | `id`(int) / `--status` | |
| invoicing | `report aging` | `--at`, `--payables` (store_true) | |
| invoicing | `report tax` | `--from`(frm), `--to` | |
| api | `serve` | `--port`(int), raw=True | |

Documents: exactly the shapes in spec.md. All amounts via `core.fmt`. Ids are ints in JSON,
audit targets strings.

## Conventions
- Import shared helpers from `fin.core` and `fin.cli` (`from fin.cli import command, arg`); never
  re-implement money/date/account/posting/fx logic. Every posting goes through
  `core.post_transaction` (it checks closed periods). Amount inputs: `core.parse_amount`.
  Dates: `core.parse_date`, months `core.parse_month`.
- Validate fully before writing. Data-changing handler calls `ctx.audit(...)` exactly once, on success.
- Unknown invoice/bill id: raise `core.NotFound`.
- Tests: subclass `tests.helpers.FinCase` (fresh book, EUR, admin `alice`; `self.fin(...)` returns
  JSON, `self.fin_err(...)` asserts exit 2). Don't name helpers after unittest methods.
- Decisions (don't re-decide): conversions in reports convert each account's per-currency sum at
  the report date, then totals are sums of the converted, rounded values. Invoice `price` is
  displayed with `fmt`; `quantity` and tax `rate` are shown as given (stored as text). A posting
  with an amount that has more than 2 decimals is rounded half up. Invoice/bill `paid` sums all
  payments; aging recomputes as of the date.

## ledger (done by lead)
`fin/ledger.py` is written and passes `tests/test_acc_ledger.py`; use its commands in your tests.

## banking
Owns `fin/banking.py`, `tests/test_banking.py`. Sections 5, 6, 7, 16. Own tables (rules,
import dedupe keys per account, budgets with `PRIMARY KEY(account, month)`, recurring
definitions with postings stored as JSON text and the occurrence dates already created,
reconcile cleared marks `(account, txn_id)`). Rule account must exist (UserError otherwise);
invalid regex is a UserError. Import: read CSV with `csv`, validate every row first (bad date or
amount -> UserError naming the row), dedupe against earlier imports to the same account and
within the file, then post each row with `post_transaction` (closed month -> whole import fails;
the cli rollback guarantees nothing is kept). Budget: account must exist and be type expense.
Recurring add validates the postings exactly like `txn add` (e.g. call `post_transaction` inside
a SAVEPOINT and roll it back, or replicate checks via the same function); unique NAME. Recurring
run: for each definition, occurrences k=0,1,... start + k periods (monthly
`add_months(start, k)`, yearly `add_months(start, 12*k)`, weekly `add_days(start, 7*k)`) up to
`--until`, skip those already created; post in date order. Reconcile per spec section 16; each
`--clear` id must have a posting to ACCOUNT (exact account) dated <= DATE. May change: only its
own files. Done check: `python -m unittest tests.test_acc_banking tests.test_banking`. Must not
touch core.py, cli.py, other modules or `tests/test_acc_*`.

## statements
Owns `fin/statements.py`, `tests/test_statements.py`. Sections 8, 9, 17. Use
`core.posting_sums` + `core.convert` for all reports (target currency = `--currency` or the
book's; conversion date = `--to`/`--at`; month end for networth). Income/liability/equity shown
negated. Only accounts with postings in range, by their own name (no ancestor roll-up), sorted
dicts by name. Ledger report: account must exist; in ACCOUNT's currency over ACCOUNT and its
descendants (postings in other currencies, if any, are converted at the posting date... just
assume same currency and sum raw); rows by date then txn id then posting seq. Loan: Decimal
math (`(1 + r) ** -MONTHS` with Decimal works for int exponents), validate PRINCIPAL > 0,
RATE >= 0, MONTHS >= 1. May change: only its own files. Done check:
`python -m unittest tests.test_acc_statements tests.test_statements`. Must not touch core.py, cli.py, other modules or
`tests/test_acc_*`.

## invoicing
Owns `fin/invoicing.py`, `tests/test_invoicing.py`. Sections 13, 14, 15 and `report aging`.
Own tables (tax codes, customers, vendors, invoices, invoice lines, invoice payments, bills,
bill lines, bill payments). Lines parsed by splitting on `;` (exactly 4 fields). Validate
quantity/price/amount with `parse_decimal`; net = `money(qty*price)`, tax =
`money(net*rate/100)`. Issue: number by counting invoices already issued with that year.
Accounts `Assets:Receivable`, `Income:Sales`, `Liabilities:SalesTax`, `Assets:TaxReceivable`,
`Liabilities:Payable` via `ensure_account`. Pay: account must be an existing asset account;
amount > 0 and <= balance; invoice must be issued/partial. Bill status `open`, `partial`,
`paid`. Bill line ACCOUNT must exist and be expense or asset type. Aging: days past due =
(DATE - due).days: <=0 current, 1-30, 31-60, 61-90, >90 "90+". `report tax`: by issued
(issued/partial/paid) invoices and all bills dated in the period; `by_code` keys sorted; lines
without tax code aren't in by_code. Unknown id -> `core.NotFound`. May change: only its own
files. Done check: `python -m unittest tests.test_acc_invoicing tests.test_invoicing`. Must not touch core.py, cli.py, other modules or
`tests/test_acc_*`.

## api (wave 2)
Owns `fin/api.py`, `tests/test_api.py`. Section 10. `make_server(db_path, port)` returns a
`http.server.ThreadingHTTPServer` (port 0 = any); `serve` command (raw) prints
`serving on http://127.0.0.1:PORT` to stderr and calls `serve_forever` until KeyboardInterrupt.
Every route maps to `cli.execute(db_path, user, NAME, cli.namespace(NAME, ...))`; POST bodies
are converted to the CLI's arg forms (postings -> `"ACCOUNT=AMOUNT"` or `"ACCOUNT"`; invoice
lines -> `"DESC;QTY;PRICE;TAX"` with empty tax when missing). POST without `X-User` -> 401 before
anything else; exceptions: `AuthError`/`NotFound`/`UserError` -> their `.status` with
`{"error": msg}`; invalid JSON body -> 400; unknown path/method -> 404 `{"error": ...}`.
Responses `Content-Type: application/json`. Silence request logging. May change: only its own
files. Done check: `python3 -m unittest discover -s tests` (python3 is the interpreter here).
Must not touch other modules or `tests/test_acc_*`.
