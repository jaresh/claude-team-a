# Plan
Goal: small-business finance system `fin/` (stdlib Python). Full spec: .claude/team/spec.md (section numbers below refer to it).
Check: `python -m unittest discover -s tests` (all must pass; never break others' tests).

## Contract / conventions (already written by lead; READ fin/core.py and fin/cli.py first)
- fin/core.py: UserError, dec/money/q/fmt (money as Decimal, fmt gives "0.00" for zero), parse_date/parse_month/month_end/add_months/add_days/days_between, ensure_account/get_account, check_open, post_txn(conn,date,desc,[(acct,Decimal|None)]) -> txn dict (validates, checks closed period; use it for EVERY posted transaction), get_txn, convert(conn,Decimal,frm,to,at), book_currency. Never use float; never write your own rounding/formatting. Do not edit core.py/cli.py (if you need a change, append to changes.md and tell lead in handoff; small additive helpers inside your own module instead).
- Commands: each feature module `fin/<module>.py` has `register(reg)` (see cli.py docstring) and optional `SCHEMA` string (CREATE TABLE IF NOT EXISTS ...; statements separated by `;`). Handlers return JSON-able objects; raise UserError for user errors; call `ctx.audit(action, target)` once per successful data-changing command with the action/target from spec §11. Pick perm="read"/"write" correctly (admin perms already handled for user add / period close). Handlers must not catch/commit; cli wraps all in one transaction (rolled back on UserError -> nothing changes).
- Modules and owners (one teammate each, sequential): ledger (§1-4: account, txn, balance, fx, convert), automation (§5-7: rule, import, budget, recurring), reports (§8, §17, and `loan schedule` §9 in fin/loans.py -> add "loans" is NOT in MODULES; instead put loan command registration inside fin/reports.py via `from .loans import register_loans`), sales (§13 incl. `tax`, `customer`, `invoice`, `report aging` with --payables flag), purchases (§14, §15), misc (§16 reconcile), api (§10, fin/api.py, command `serve` registered in fin/misc.py? NO: api owns fin/api.py with register(reg) and must be added to MODULES in cli.py by lead — lead has already added "api").
- Aging: sales registers `report aging --at DATE [--payables]`; for payables it calls `fin.purchases.aging_payables(conn, at) -> dict` (purchases implements it; if missing at that time, sales test only receivables).
- Tax codes (table in sales SCHEMA, `tax_codes(code,rate)`; rate text as given) are read by purchases via `fin.sales.get_tax_rate(conn, code) -> Decimal|None`-style helper: sales must provide `get_tax(conn, code)` returning Decimal percent or raising UserError if unknown.
- The HTTP API calls `fin.cli.execute(["--db",db,"--json","--user",u]+argv) -> (code,obj,err)`; code 2 => 400 (or 401/403 by checks done in api before), so it needs no per-command code.
- Tests: tests/test_<module>.py using tests/helpers.py FinTest (cli(...)->(code,obj,err), run_ok, run_err). Cover every behaviour of your sections incl. error cases (exit code 2 + nothing changed), audit entries, closed periods, permissions (viewer cannot write). Do not edit tests of others. Don't name helpers like unittest methods (fail, assert*, run, setUp).
- Style: concise, match fin/core.py. Amounts stored as TEXT decimals via fmt(). Zero is "0.00".

## ledger
Owns fin/ledger.py, tests/test_ledger.py. §1 account add/list, §2 txn add/list, §3 balance, §4 fx add, convert. (`init`, users, audit, period already exist in cli.py.) Posting arg `--posting ACCOUNT=AMOUNT` repeated (action=append); use core.parse_posting. Balance in each currency per account incl. ancestors, sorted keys. May change: only your files. Done check: `python -m unittest discover -s tests`.

## automation
Owns fin/automation.py, tests/test_automation.py. §5 rule/import, §6 budget set + `report budget MONTH`, §7 recurring add/run. Needs SCHEMA for rules, imported rows (dedupe per account incl. within file), budgets, recurring + occurrence tracking. Import/run must be all-or-nothing (closed periods, bad rows -> UserError, nothing changes). Done check: the unittest command.

## reports
Owns fin/reports.py, fin/loans.py, tests/test_reports.py, tests/test_loans.py. §8 report income/balance-sheet/networth, §17 trial-balance/ledger, §9 `loan schedule` (register from reports.register). Done check: the unittest command.

## sales
Owns fin/sales.py, tests/test_sales.py. §13 (tax, customer, invoice, report aging). Done check: the unittest command.

## purchases
Owns fin/purchases.py, tests/test_purchases.py. §14 vendor, bill, `aging_payables`, §15 `report tax`. Done check: the unittest command.

## misc
Owns fin/misc.py, tests/test_misc.py. §16 reconcile (cleared flag already in postings.cleared). Done check: the unittest command.

## api
Owns fin/api.py, tests/test_api.py. §10 + §11 over HTTP using execute() (start server on port 0 / ephemeral in a thread for tests; `serve --port N` command; GET and POST routes from spec, X-User auth: missing/unknown -> 401, role forbidden -> 403 (viewer cannot POST; admin/editor can), user errors -> 400 {"error"}, unknown path 404). Map each endpoint to the equivalent CLI argv (e.g. POST /invoices -> `invoice create`, payments -> `invoice pay`). Also GET /audit -> `audit list`. Done check: the unittest command.
