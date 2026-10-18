# Plan
**Goal**: small-business finance system per .claude/team/spec.md (the user's full spec; read the sections named in your task).
**Check**: `python3 -m unittest discover -s tests` (use `python3`). Each task adds its own tests/test_<task>.py.

## Contract / conventions (already built by the lead; READ fin/core.py, fin/cli.py, fin/admin.py, tests/helpers.py first)
- Never use float. Use `core.dec/q2/fmt/parse_date/parse_month/add_months/month_end/parse_posting/UserError`. All user errors: `raise UserError(msg)`. JSON amounts via `fmt()`.
- A module `fin/<task>.py` optionally defines `SCHEMA` (SQL string, `CREATE TABLE IF NOT EXISTS`, tables it owns; core tables are in core.CORE_SCHEMA: meta,users,audit,accounts,txns,postings(cleared col),rates) and `register(reg)`; reg.add("txn add", setup(parser), handler(book, ns), write=True). Read-only commands: write=False. Handlers return JSON-able data and call `book.audit(action, target)` themselves (targets per spec section 11). Modules are already listed in core.MODULES. Argparse dest names must avoid cmd, sub, db, json, user, _cmd. Repeatable options: `action="append"`.
- Handlers are thin: put the logic in plain service functions `f(book, ...)` (named below) that the HTTP API (last task) calls directly; service functions that change data audit and run the closed-period check (book.post does it) themselves.
- Posting transactions: always `book.post(date, desc, [(account, Decimal|None), ...])`; auto-created accounts via `book.ensure_account(name)`. Rates: `book.convert(amount, frm, to, at)`. Balances: `book.raw_balances(frm,to)` + `Book.rollup`.
- Tests: subclass `tests.helpers.FinTestCase` (self.init(), self.ok(*args) -> parsed JSON, self.err(*args) asserts exit 2 + empty stdout; user= kwarg). Don't name helper methods like unittest methods (fail, assert*, setUp, run...). Tests must cover every command/behaviour of your spec sections incl. error cases.
- Service function names (exact):
  - ledger.py: `list_accounts(book)`, `add_txn(book, date, desc, postings)` (postings list of (acct, Decimal|None); audits txn.add; returns txn dict), `list_txns(book, account=None, frm=None, to=None)`, `balances(book, at=None)`.
  - reports.py: `income_report(book, frm, to, currency=None)`, `balance_sheet(book, at, currency=None)`.
  - invoices.py: `create_invoice(book, customer, date, lines)` (lines: list of dicts description/quantity/price/tax_code), `issue_invoice(book, id)`, `pay_invoice(book, id, amount, date, account)` (amount str/Decimal), `get_invoice(book, id)`, `list_invoices(book, status=None)`, `aging(book, at)`, `tax_rate(book, code)` (Decimal percent; UserError if unknown). Also registers `report aging` (with `--payables` flag; payables calls `fin.bills.aging(book, at)`, imported lazily).
  - bills.py: `aging(book, at)`; registers `report tax`.
- Tasks run ONE AT A TIME in this order; later tasks may import earlier ones. Do not edit files you don't own except appending a line to .claude/team/changes.md for any such edit (avoid it). Do not edit tests you don't own. Don't commit.
- Write handoff to .claude/team/handoff/<task>.txt: Done / Next step (few lines).

## ledger
Owns fin/ledger.py, tests/test_ledger.py. Spec sections 1 (account add/list), 2 (txn add/list), 3 (balance), 4 (fx add, convert), plus audit entries (account.add, txn.add, fx.add). Parent accounts created by `account add`; `txn add` never creates accounts. Done check: `python3 -m unittest discover -s tests`. May change: only your files. Not touch: core/cli/admin (if you find a bug there, log it in changes.md and tell lead in handoff).

## automation
Owns fin/automation.py, tests/test_automation.py. Sections 5 (rule add/list, import), 6 (budget set, report budget), 7 (recurring add/run) with audits (rule.add, import, budget.set, recurring.add, recurring.run). Import and recurring run are all-or-nothing (closed-month check on every row/occurrence before anything is created; the DB transaction is rolled back on UserError anyway). Import dedupe: key (account, date, description, amount) over previously imported rows, persisted in own table. Recurring occurrences tracked in own table (name, date) so reruns create nothing. `recurring add` with duplicate name: user error. Done check: full test command. Same limits as above.

## reports
Owns fin/reports.py, tests/test_reports.py. Sections 8 (report income, balance-sheet, networth) and 17 (report trial-balance, report ledger). Convert per account/currency with book.convert at the report's date then sum, round to cents; negate income/liabilities/equity; accounts appear only if they have postings in range; zero-sum shows "0.00". Balance-sheet: assets/liabilities/equity dicts by posting account name; retained_earnings = total income − total expenses (positive form: -(income raw) - expenses raw). Ledger report: ACCOUNT must exist (UserError); opening/rows/closing in ACCOUNT's currency; rows are postings to ACCOUNT and descendants. Networth month entries from --from to --to inclusive (from>to: user error). Done check: full test command.

## loans
Owns fin/loans.py, tests/test_loans.py. Section 9 `loan schedule` (read-only, no audit). Use Decimal with enough precision for (1+r)^-N (r = RATE/1200 as exact Decimal). Done check: full test command.

## invoices
Owns fin/invoices.py, tests/test_invoices.py. Sections 13 (tax add/list, customer add/list, invoice create/issue/pay/show/list, report aging for receivables, bills part left as lazy import) with audits tax.add, customer.add, invoice.create, invoice.issue, invoice.pay (target = invoice id). Own tables for tax codes, customers, invoices, invoice lines, payments. Numbering counts per year of invoice date. Aging per spec 13 (payments counted only if dated ≤ at). tax rate shown as given string. Decisions on unspecified details go in a "Assumptions" list in your handoff. Done check: full test command.

## bills
Owns fin/bills.py, tests/test_bills.py. Sections 14 (vendor add/list, bill create/pay/show/list, `aging(book, at)` for payables) and 15 (report tax). Use `invoices.tax_rate`. Own tables for vendors, bills, bill lines, bill payments. Audits vendor.add, bill.create, bill.pay. Bill `status` open/partial/paid. Account of a line must exist and be expense or asset type. Done check: full test command including a test that `report aging --payables` works.

## reconcile
Owns fin/reconcile.py, tests/test_reconcile.py. Section 16, audit `reconcile` (target = account). Uses postings.cleared column. Validate all --clear ids before marking. Done check: full test command.

## api
Owns fin/api.py, tests/test_api.py. Section 10 (+ section 11 for HTTP; 401/403 via core.Unauthorized/Forbidden; 400 for other UserError; 404 unknown path/ids? unknown invoice id → 400 user error is fine, unknown path 404; invalid JSON body → 400). Register `serve --port N` (read-only command; blocks serving with http.server ThreadingHTTPServer on 127.0.0.1 until killed). Per request: open `Book(db_path)`, set book.user from X-User, begin, book.require(write=True) for POST, call the service functions named in the contract (ledger/reports/invoices), commit, or rollback on error. Factor a `make_server(db_path, port)` function so tests can run it in a thread on port 0 and use urllib. GET /accounts, /transactions (optional query account/from/to), /balances, /reports/income, /reports/balance-sheet, /invoices, /invoices/ID, /reports/aging (payables=1), /audit (optional by). Done check: full test command.
