# Plan
Goal: small-business finance system in `fin/` (stdlib Python 3.12). Full spec: `.claude/team/spec.md` (the user's request, word for word; read the sections of your task).
Check: `python -m unittest discover -s tests` (each task's done check: its own test file, e.g. `python -m unittest tests.test_<task>`).

## Contract (already written by lead; READ `fin/core.py`, `fin/cli.py`, `tests/helpers.py` first, do not edit them)
- A command module `fin/<module>.py` defines `register(sub)` and handlers `def h(ctx, args)` returning a JSON-able doc (dict/list; amounts via `core.fmt`). Register with `cli.command(sub, "txn", "add", handler, write=True)` (group None = top-level command like `balance`, `convert`, `import`). `write=True` for commands that change data (the CLI then enforces --user/role); `admin=True` for admin only. Reads: write=False. Add arguments to the returned parser (`p.add_argument(...)`; `action="append"` for repeated options; dest names are yours).
- Handlers run inside a DB transaction; raise `core.UserError` for user errors (rolled back automatically). Call `core.audit(ctx, action, target)` in every write handler (action/target per spec section 11). Posting transactions: always `core.post_txn` (checks closed period, balance, accounts).
- The module list is fixed in cli.MODULES: books (books.py), ledger (ledger.py), bank (bank.py), reports (reports.py), invoices (invoices.py). The api is `fin/api.py` (wave 2) and drives commands through `cli.execute(db, user, argv)`.
- Schema is in core.SCHEMA (all tables exist already). Money: Decimal only; use core.fmt/q2/parse_amount/parse_date/parse_month/add_months/convert/rate/balances_by_account/total_in. Never write your own versions. If you truly need a change in core/cli/helpers, append a line to changes.md and make the minimal additive change.
- Tests: use `tests.helpers.FinTest` (`self.ok(...)`, `self.bad(...)`, `self.accounts(...)`; book is EUR, user `admin` already exist). Tests must cover every section of your task, including user-error cases (exit 2, nothing printed to stdout, nothing changed). Beware: never name test helpers like unittest methods.
- Only touch your own files. Do not touch other teammates' files or `.claude/skills`.
- Reports, ledger etc. by spec say accounts are "by the name the postings are on".
- Each handler for list-type commands `--json` output equals the spec's documents exactly (key names, order irrelevant).

## books
Files: fin/books.py, tests/test_books.py. Spec sections 1 (init, account add/list), 11 (user add/list, audit list; roles/permission tests via the cli), 12 (period close/status; test closed-period errors only for `txn add` — other modules test theirs). `init` is registered with `write=True, noauth=True, uninit=True`: creates meta currency, admin user, audit entry 1 (user = admin name, `core.audit(..., user=name)`); error if already initialised (meta currency present). `period close`: set meta closed_through = max(existing, month); admin only. Note: tests for init must use a fresh uninitialised db (not FinTest.setUp's), so write your own setUp. Role tests: editor can't `user add`/`period close`, viewer can't write, missing/unknown user errors, reads work without --user (account list, audit list, user list, period status are reads). May change: nothing outside your files.
Done: `python -m unittest tests.test_books`

## ledger
Files: fin/ledger.py, tests/test_ledger.py. Sections 2 (account-free: txn add/list), 3 (balance), 4 (fx add, convert — convert is top-level `convert AMOUNT FROM TO --at DATE`), 16 (reconcile), 17 (report trial-balance, report ledger). Group `report` is shared with other modules: use `cli.command(sub, "report", "trial-balance", ...)`. txn add: `--posting` repeated; audit `txn.add` target id. Needs accounts: tests create them with `self.accounts(...)` ("account add"; books module is built in parallel — if `account add` is not yet available when you test, wait is not possible: instead create accounts in tests via `core.ensure_account(core.Ctx(conn), name)` on a `core.connect(self.db)` connection, and add the setUp helper in your own test file). Likewise users via SQL insert. May change: fin/ledger.py, its test.
Done: `python -m unittest tests.test_ledger`

## bank
Files: fin/bank.py, tests/test_bank.py. Sections 5 (rule add/list, import), 6 (budget set, report budget), 7 (recurring add/run). Same note about creating accounts in tests as for ledger (use core.ensure_account directly). Import: whole import fails atomically on any bad row or closed-month row; duplicates tracked by the `imports` table (also dedupe repeats within one file; record imports only for rows created). Recurring: store postings as JSON in `recurring.postings`; track created occurrences in the recurring_done table (columns rec_id, n) where n = occurrence index from 0; occurrence k date: monthly add_months(start,k), weekly start+7k days, yearly add_months(start,12k). Closed period check on any occurrence fails the whole run (post_txn does it). Budget: expense accounts only, must exist.
Done: `python -m unittest tests.test_bank`

## reports
Files: fin/reports.py, tests/test_reports.py. Section 8 (report income, balance-sheet, networth; `--currency`, conversion at the report's date via core.convert per currency per account) and section 9 (loan schedule; loan is a group `loan`, no data written, write=False). Use exact Decimal arithmetic for the annuity (set a local decimal context precision of 50). Same note about creating accounts and transactions in tests: use core.ensure_account and core.post_txn directly. May change: fin/reports.py, its test.
Done: `python -m unittest tests.test_reports`

## invoices
Files: fin/invoices.py, tests/test_invoices.py. Sections 13 (tax add/list, customer add/list, invoice create/issue/pay/show/list, report aging), 14 (vendor, bill, aging --payables), 15 (report tax). Invoice/bill JSON documents exactly per spec; `paid` = sum of payments rows. Tables invoices/bills/payments exist. Invoice numbers per year sequential among issued. Aging buckets by days past due (DATE − due), only payments dated <= DATE. `--payables` is a flag on `report aging` (one command). Bill status values: open/partial/paid. Closed-period checks come via core.post_txn (make sure nothing is changed on error: handlers are transactional). Audit names per spec section 11 (`invoice.create`, ..., `bill.pay`, `tax.add`, `customer.add`, `vendor.add`). Tests: create accounts/users with core helpers directly where needed. Expose pure functions `invoice_doc(conn, id)`, `bill_doc(conn, id)`, `aging(conn, at, payables)` for reuse.
Done: `python -m unittest tests.test_invoices`

## api (wave 2)
Files: fin/api.py, tests/test_api.py. Section 10; `serve --port N` registered in fin/api.py (add "api" to cli.MODULES, that is the one allowed edit to cli.py; note `serve` is write=False, uninit=True). Handler per request maps to `cli.execute(db, user_from_X-User, argv)` for the same documents; GET endpoints need no user. Map: UserError.status -> HTTP status (400/401/403), 201 for POST /transactions and /invoices, 200 for the other POSTs; unknown path 404; invalid JSON body -> 400. Use ThreadingHTTPServer; serve until stopped. Tests start the server on port 0 in a thread against a temp db (initialize via `fin.books` commands through cli.main with init).
Done: `python -m unittest tests.test_api`
