# Plan
Goal: small-business finance system `fin/` (stdlib Python). Full spec: .claude/team/spec.md (read your sections).
Check: `python -m unittest discover -s tests` (each task: its own test file only, see Done check).

## Contract (already written by lead — READ fin/core.py, fin/__main__.py, tests/helpers.py first)
- Each module file `fin/<task>.py` (a stub exists) defines `setup(sub)` registering argparse commands.
  Standalone commands: `p = sub.add_parser("convert")`. Grouped commands (`txn add`, `report income`, ...):
  ALWAYS `g = group(sub, "report"); p = g.add_parser("income")` (core.group) because several modules share groups.
- Each command: `p.set_defaults(func=handler, perm="read"|"write"|"admin")`. Handler `def handler(book, args)` returns a
  JSON-able result (main prints it; do not print). perm: read = changes nothing; write = admin+editor; admin = admin only
  (`user add`, `period close`). Main authorizes, commits on success, rolls back on UserError. Never call sys.exit.
- Raise `UserError(msg)` for every user error (bad input, unknown account...). Argparse errors already become UserError.
- Use core helpers only: parse_amount/parse_date/parse_month/parse_currency/parse_rate, fmt (money->string), q2,
  add_months, month_end, month_range, Decimal. Money is Decimal only, stored as TEXT in sqlite; sum in Python.
  Postings go through `book.post(date, desc, [(account, Decimal|None)])` (checks closed periods, balance, accounts) and
  return the txn dict. `book.audit(action, target)` once per successful data-changing command (actions in spec §11).
  `book.ensure_account(name, currency=None)` creates account + parents. `book.convert(amount, frm, to, at)`.
  `book.currency`, `book.closed_through`, `book.check_open(date)`, `book.txn(id)`, `book.account(name)`.
- DB schema is fixed in core.SCHEMA (do not change core.py or the schema; if you truly need a change, append a line to
  .claude/team/changes.md and work around it). Table notes: invoice/bill totals are computed from lines, `paid` = sum of
  `payments` rows (kind 'invoice'/'bill'); status stored in invoices/bills.status. Invoice number stored on issue.
- Output of commands is JSON as in the spec. Exit/err behaviour is handled by main.
- Tests: `tests/test_<task>.py` using `tests.helpers.BookCase` (self.ok / self.fail_ / self.acct). Cover every command
  in your sections incl. error cases and the examples of the spec. Run: `python -m unittest tests.test_<task>`.
  Do not edit other files. Never use float. Code style: plain, short, no needless comments.

## ledger  (owns fin/ledger.py, tests/test_ledger.py) — spec §1,2,3,4,11,12
Commands: account add/list; txn add/list; balance; fx add; convert; user add/list; audit list; period close/status.
(`init` is done in __main__; audit entry 1 exists.) Audit actions: account.add (name given on the command, not parents),
txn.add (id), fx.add, user.add, period.close (only when it changes something? — always audit successful close; closing an
earlier month = no change but still success, no audit entry), per §11. perms: reads=read, `user add`/`period close`=admin, rest write.
Account add of nested name creates parents with same currency. `convert` result via book.convert. Tests also: viewer/editor/
admin permissions across a few commands (txn add, user add, period close, account list), closed-period rejection of txn add.
Done: `python -m unittest tests.test_ledger`

## imports  (owns fin/imports.py, tests/test_imports.py) — spec §5,6,7,16
Commands: rule add/list; import; budget set; report budget; recurring add/run; reconcile. (`report budget` via group "report".)
Import: whole import atomic (any bad row / closed-month row => UserError, nothing imported). Dedupe table `imported`
(rows identical within file also skipped). Recurring: store postings as JSON list of [account, amount-or-null] in table
recurring; occurrences computed from start (monthly: add_months(start, k) with start's day), tracked in recurring_done.
Reconcile uses table `cleared`; audit actions import(account), rule.add, budget.set("ACCOUNT MONTH"), recurring.add, recurring.run(until), reconcile(account).
perms: report budget/rule list = read; others write. Tests use `txn add` / `account add` through the CLI (ledger module is being written in parallel;
until it exists in the merged tree, test files may fail on those — write setup via CLI anyway, the lead merges before checking).
Done: `python -m unittest tests.test_imports` (needs ledger; if fin/ledger.py is still a stub, check again later or test your pure logic by direct sqlite use via core.Book.ensure_account / book.post).

## reports  (owns fin/reports.py, tests/test_reports.py) — spec §8,9,17
Commands: report income / balance-sheet / networth / trial-balance / ledger; loan schedule. Use book.convert for --currency and for
trial-balance/ledger conversions at the report date; posting amounts are in each posting's own currency. networth month: as of month end.
loan schedule: perm read. Same note about ledger module dependency for tests (use book.post directly in test setUp if needed).
Done: `python -m unittest tests.test_reports`

## sales  (owns fin/sales.py, tests/test_sales.py) — spec §13 (except `report aging`)
Commands: tax add/list; customer add/list; invoice create/issue/pay/show/list. Audit: tax.add, customer.add, invoice.create/issue/pay.
Invoice JSON `paid` = sum of payments; status draft/issued/partial/paid. Number per year from count of already numbered invoices with that year prefix.
Done: `python -m unittest tests.test_sales`

## purchases  (owns fin/purchases.py, tests/test_purchases.py) — spec §14 (except `report aging --payables`)
Commands: vendor add/list; bill create/pay/show/list. Audit vendor.add, bill.create, bill.pay. Tax codes come from table taxes (added by `tax add`, owned by sales; in tests insert via SQL on book.conn or via CLI once available).
Done: `python -m unittest tests.test_purchases`

## bizreports  (owns fin/bizreports.py, tests/test_bizreports.py) — spec §13 `report aging` (both receivables and `--payables`) and §15 `report tax`
Reads tables invoices/invoice_lines/bills/bill_lines/payments directly (insert rows directly in tests via SQL). Receivable aging: only status
issued/partial/paid invoices (number not null) dated <= DATE, payments dated <= DATE only; bills likewise (all bills).
Done: `python -m unittest tests.test_bizreports`

## api  (WAVE 2; owns fin/api.py, tests/test_api.py) — spec §10 and §11 for HTTP
Command `serve --port N` (perm read; blocks via http.server). Implement each endpoint by calling `fin.__main__.execute(db, argv, user)` (maps
requests to the CLI argv, so documents are identical; UserError.status gives 400/401/403; POST body JSON -> argv, e.g. `--posting acct=amt`
or bare `acct`). Unknown path 404 `{"error":...}`. POST needs X-User; 401 if missing/unknown (use Book.authorize(user,"write") before running; invalid JSON → 400).
Handle requests sequentially (HTTPServer, not threaded). Tests start the server on a free port in a thread (make the server class importable, e.g. `make_server(db, port)`).
Done: `python -m unittest tests.test_api`
