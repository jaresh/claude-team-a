# Plan
Goal: small-business finance system, stdlib Python. FULL SPEC: .claude/team/spec.md (the user's request; sections numbered 1-17). 
Check: `python -m unittest discover -s tests` (each task also runs its own tests/test_<task>.py).

## Contract / conventions (READ fin/core.py and fin/__main__.py first; do NOT edit them — if you need a core change, log it in changes.md and work around it)
- Each module fin/<mod>.py exposes `COMMANDS = [(path_tuple, setup(parser) or None, handler(ctx, args), perm)]` and optional `SCHEMA` (CREATE TABLE IF NOT EXISTS ... string, own tables only). path e.g. ("txn","add"), ("report","income"), ("convert",). perm: 'read'|'write'|'admin'|'init'.
- handler(ctx, args) returns a JSON-able object (exactly the spec's --json document), raises core.UserError for user errors. Use ctx.conn (sqlite, already in a transaction: never commit), ctx.currency, ctx.audit(action, target) for write commands (spec section 11 names), core.post_txn/ensure_account/convert/fmt/q2/D/parse_date/parse_month/add_months/month_end/check_open/txn_json. Never use float. Always validate with parse_date etc. Use argparse dest names equal to the long option / positional names (e.g. --date-col -> date_col; positional ACCOUNT -> `account`). Repeated options use action="append" (dest names: posting, line, clear). Optional args default None.
- Dates compare as ISO strings. Amounts stored as TEXT decimal strings; sum in Python with Decimal. Output money via core.fmt.
- Modules (core.MODULES): books, imports, reports, recon, invoicing; fin/api.py is the HTTP layer (not a COMMANDS module; it calls core.execute(db, user, handler, perm, args_namespace) using core.all_commands() lookups by path; build an argparse.Namespace/SimpleNamespace with the dest names).
- Tests: unittest, use a temp dir db and call `fin.__main__.main([...])` or subprocess `python -m fin`; test helper names must not collide with unittest methods. Only your own tests/test_<task>.py file. Tests must pass in under a minute.
- Log every edit to a shared file (none expected) in .claude/team/changes.md.

## books  (wave 1) — owns fin/books.py, tests/test_books.py
Spec sections 1,2,3,4,11,12 (init, user add/list, audit list, account add/list, txn add/list, balance, fx add, convert, period close/status). init: perm 'init', creates meta currency, first admin user, sets `ctx.audit_user = NAME`, audit entry "init" target currency; error if already initialised (note core.execute for perm init skips the initialised check). audit list perm read. Include tests for permissions (viewer/editor/admin, missing user), audit, closed periods, atomicity (error leaves nothing), and exit code 2 w/ nothing on stdout. May change: only these files. Done check: `python -m unittest tests.test_books`.

## imports  (wave 2) — owns fin/imports.py, tests/test_imports.py
Spec sections 5,6,7: rule add/list, import, budget set, report budget, recurring add/run. Needs a table for rules, imported-row dedupe (store account,date,description,amount), budgets, recurring (+ created occurrences). recurring run: occurrence k of monthly = core.add_months(start,k,day=start day). Import/run all-or-nothing incl. closed periods (raising UserError rolls back). Audit: rule.add, import, budget.set ("ACCOUNT MONTH"), recurring.add, recurring.run (until date). Budget accounts must be existing expense accounts. Done: `python -m unittest tests.test_imports tests.test_books`.

## reports (wave 2) — owns fin/reports.py, tests/test_reports.py
Spec sections 8,9,17: report income, balance-sheet, networth, trial-balance, ledger; loan schedule (perm read). Convert each posting's amount to the target currency at the report date using core.convert per account balance (sum per account+currency, then convert, round). Done: `python -m unittest tests.test_reports tests.test_books`.
Note: retained earnings and totals use converted per-account amounts (sum of rounded values); document in a comment.

## recon (wave 2) — owns fin/recon.py, tests/test_recon.py
Spec section 16: reconcile command (perm write, audit "reconcile" target account). Own table for cleared marks. Done: `python -m unittest tests.test_recon tests.test_books`.

## invoicing (wave 3) — owns fin/invoicing.py, tests/test_invoicing.py
Spec sections 13,14,15: tax, customer, vendor, invoice create/issue/pay/show/list, bill create/pay/show/list, report aging (--payables flag, dest `payables`), report tax. Audit names per section 11 (invoice.create, invoice.issue, invoice.pay, bill.create, bill.pay target = id, tax.add, customer.add, vendor.add). Provide public helper functions for the API in invoicing.py: `invoice_json(conn, id)`. Invoice/bill posts via core.post_txn (which checks closed periods). Invoice status 'paid' when balance zero. Aging uses payments dated <= --at; store payments in own table with date. Bill status values open/partial/paid. Done: `python -m unittest tests.test_invoicing tests.test_books`.

## httpapi (wave 4) — owns fin/api.py, fin/serve.py?, tests/test_api.py, README.md
Spec section 10 (and 11 for the API). Add `serve --port N` as command: create fin/serve.py exposing COMMANDS with ("serve",...) perm 'read' — then ADD "serve" to core.MODULES (the only allowed core edit; log it). The server uses http.server (ThreadingHTTPServer), binds 127.0.0.1, handler runs via core.execute; UserError -> 400 (AuthError -> its .status) with {"error":...}; unknown paths 404; POST needs X-User header (missing/unknown -> 401; role -> 403, checked via execute perms). GET returns same documents as CLI --json (reuse handlers via args namespaces). Tests start the server on an ephemeral port in a thread. Also write README.md: usage of every command briefly, how to run tests, and an "Assumptions" section (list: output of non-JSON mode is pretty JSON; sqlite transaction per command; init on new db only; account list sorted by name; reports convert per-account balances; amounts stored as 2-dec; fx rate must be positive; accounts for invoicing created in book currency; user names case-sensitive; etc. — read the code for the real ones). Done: `python -m unittest discover -s tests`.

## Notes from wave 1
- Use `python3` (no `python` binary here); tests via subprocess should use sys.executable.
- argparse dests: `--from` -> `from_`, `--to` -> `to` (follow fin/books.py setup_txn_list); positionals FROM/TO in fx/convert use dests src/dst with metavar.
- Look at fin/books.py and tests/test_books.py for style; run `python3 -m unittest discover -s tests` as part of done check.
