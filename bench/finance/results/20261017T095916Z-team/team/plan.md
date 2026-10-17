# Plan: small-business finance system (spec = the user's task text; section numbers refer to it)
The full spec text is in .claude/team/spec.md — read the sections named in your task.

Goal: Python 3.12 stdlib-only package `fin/`. Core, `ledger.py` (accounts, txn, balance) and `admin.py`
(init, user, audit, period) are DONE by the lead: read fin/core.py, fin/cli.py, fin/ledger.py first (short).
Check (all): `python3 -m unittest discover -s tests`. Use `python3` (no `python` here); tests run the CLI
with sys.executable via tests/helpers.py `FinCase` (read it; do not edit helpers.py or test_core.py).

## Contract / Conventions
- A command module is `fin/<name>.py` with `register(reg)`. `reg("report budget", setup(parser), handler, write=bool, admin_only=bool)`.
  `handler(book, args)` returns a JSON-able result (printed as one JSON doc) and, if it changes data, calls
  `book.audit(action, target)` (spec section 11 names) and returns the result. Raise `UserError` for user errors
  (never print/exit yourself; the CLI rolls back everything). Commands that change data: write=True.
  Module names are already listed in cli.MODULES: ledger admin rates bankimport recurring budgets loans reports invoices bills aging taxreport reconcile server.
- ALWAYS use core helpers: `parse_amount/parse_decimal/cents/fmt` (money; never float; fmt gives "0.00" for zero),
  `parse_date/parse_month/parse_currency`, `add_months(start,k)`, `add_days`, `month_last_day`, `months_between`,
  `book.post_txn(date, desc, [(account, Decimal|None)])` (checks closed periods, balance, returns txn dict),
  `book.posting_rows(prefix, date_from, date_to)`, `book.convert(amount, frm, to, at)`, `book.ensure_account(name)`,
  `book.add_account`, `book.account(name)`, `book.check_open(date)`, `book.currency`. Don't write your own versions.
  Imports in your module: `from .core import ...`; `from .ledger import parse_posting_args, balances, list_txns`.
- Do not edit files you don't own except appending one line per edit to `.claude/team/changes.md`. If core lacks
  something, say so in your handoff instead of changing core.py.
- Rounding half up to cents via cents(); percentages: Decimal(rate)/100.
- Tables are in core.SCHEMA (read it). Shapes shared between tasks:
  * invoices.lines / bills.lines = JSON list of the dicts shown in the spec's invoice/bill JSON (all values strings,
    quantity as given, tax_code null or code). Statuses: invoices draft|issued|partial|paid ; bills open|partial|paid.
    invoices.number NULL while draft. invoices.due/bills.due stored dates.
  * payments(kind 'invoice'|'bill', doc_id, date, amount money string, account, txn_id): one row per payment.
    invoice `paid` = sum of its payments; balance = total - paid.
  * taxes.rate is the string as given by the user (e.g. "20").
- Each task writes `tests/test_<task>.py` (unittest, subclass FinCase) covering its spec sections incl. error
  cases (exit 2, nothing changed), audit entries and permissions where relevant. Keep tests quick.
- Do each task's done check; run only `python3 -m unittest tests.test_<task>` plus tests.test_core.

## rates
Owns fin/rates.py (fx add, convert), fin/budgets.py (budget set, report budget), fin/loans.py (loan schedule); tests/test_rates.py. Spec sections 4, 6, 9. `loan schedule` is read-only. Done: `python3 -m unittest tests.test_rates tests.test_core`.

## bankimport
Owns fin/bankimport.py (rule add/list, import), fin/recurring.py (recurring add/run); tests/test_bankimport.py. Spec sections 5, 7 (+ closed periods 12 for import/run: check all rows first, fail all-or-nothing; the CLI rolls back anyway). Import dedupe via the `imports` table; recurring state via recurring_done. Bad regex in rule add = user error. Done: `python3 -m unittest tests.test_bankimport tests.test_core`.

## reports
Owns fin/reports.py (report income, balance-sheet, networth, trial-balance, ledger); tests/test_reports.py. Spec sections 8, 17. Multi-currency conversion uses book.convert at the report date. Done: `python3 -m unittest tests.test_reports tests.test_core`.

## invoices
Owns fin/invoices.py (tax add/list, customer add/list, invoice create/issue/pay/show/list); tests/test_invoices.py. Spec section 13 except aging. Export `invoice_dict(book, row)` for others. Done: `python3 -m unittest tests.test_invoices tests.test_core`.

## bills
Owns fin/bills.py (vendor add/list, bill create/pay/show/list); tests/test_bills.py. Spec section 14 except aging. Tax rates read from the `taxes` table (tests add codes via `tax add`, which the invoices teammate builds; if not yet present in your run, insert into taxes via sqlite3 in your test setUp). Done: `python3 -m unittest tests.test_bills tests.test_core`.

## aging
Owns fin/aging.py (report aging, with --payables), fin/taxreport.py (report tax), fin/reconcile.py (reconcile); tests/test_aging.py. Spec sections 13 (aging), 14 (payables aging), 15, 16. Read invoices/bills/payments tables directly (see shapes); tests may create data through the CLI once other modules exist, else by inserting rows with sqlite3 (+ txns via CLI `txn add`). Tax report `paid`/`collected` sum line taxes; collected counts invoices with status != draft. Done: `python3 -m unittest tests.test_aging tests.test_core`.

## server
Owns fin/server.py (command `serve --port N`; read-only flag, long running; handler must call `book.rollback()` then `book.close()` before serving, then serve with ThreadingHTTPServer on 127.0.0.1 until killed); tests/test_server.py. Spec section 10. Implement each endpoint by calling `fin.cli.execute(db_path, argv, user)` (argv = command words without global options, e.g. ["txn","list"], ["report","income","--from",..]) in the request thread and returning its JSON result: no business logic here. POST /transactions → argv txn add with --posting ACCOUNT=AMOUNT (or just ACCOUNT); invoices lines → --line "desc;qty;price;tax". Status mapping: core.Unauthorized→401, core.Forbidden→403, other UserError→400 `{"error":..}`, unknown path→404 (also invalid JSON body→400). Every POST needs header X-User (missing → 401 even if otherwise fine); pass it as user. GET needs none. Write tests by starting the server in a subprocess on a free port. Done: `python3 -m unittest tests.test_server tests.test_core`.
