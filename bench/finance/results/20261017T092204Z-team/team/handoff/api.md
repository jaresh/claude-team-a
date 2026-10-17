# Handoff: api

## Done
- `fin/cmd_api.py` (new): `COMMANDS = [serve --port N, mode read]`, `make_server(db, port)` returning a
  `ThreadingHTTPServer` (bound to 127.0.0.1, `server.db` = db path). Each request is turned into CLI argv and run
  through `fin.cli.execute(db, user, argv)`; `UserError` -> `e.status` with `{"error": msg}`; other exceptions -> 500.
- Endpoints (spec s10): GET /accounts, /transactions, /balances?at, /reports/income?from&to,
  /reports/balance-sheet?at, /reports/aging?at (&payables=1), /invoices, /invoices/ID, /audit;
  POST /transactions (201), POST /invoices (201), POST /invoices/ID/issue (200), POST /invoices/ID/payments (200).
  Anything else: 404.
- `tests/test_api.py` (new): 13 tests, 5 without a book (routing, 401, serve registration/usage) and 8 end-to-end
  through the HTTP layer (txn, balance, user error, 401/403, reports, audit, invoice flow, unknown customer).
- Check results:
  - `python3 -m unittest tests.test_api -q`: Ran 13, OK (run against the cmd_books / cmd_data / cmd_invoices modules
    now present in the tree).
  - `python3 -m unittest discover -s tests -q`: Ran 105, FAILED (failures=4, errors=3). All 7 are in
    `tests/test_reports.py` (reports teammate's area, not touched by me); none are in test_api.
  - Live check: `serve --port 8765` started, printed its address to stderr, stopped cleanly on SIGINT with no
    traceback, and a write right after worked (no leftover lock).
- No shared files edited; `changes.md` not touched. Nothing committed.
- Note: the interpreter in this environment is `python3` (3.14); there is no `python` on PATH.

## In progress
- Nothing. Endpoints for bills (spec s14) are not exposed over HTTP because s10 does not list them.

## Next step
- Lead: merge, then run `python3 -m unittest tests.test_api -q`. If it fails, the failing test name tells you which
  command is missing or changed; the route-to-argv map is in `_route` in `fin/cmd_api.py`.
- Lead: for the README, list these assumptions:
  1. `serve` binds 127.0.0.1 only; there is no host option.
  2. `serve` prints `serving on http://127.0.0.1:N` to stderr, nothing to stdout. It stops on Ctrl-C (exit 0).
  3. Auth order for POST: missing X-User -> 401 is checked before the body is read. Unknown user -> 401 and role
     denial -> 403 come from `execute`, and are reported after the argv is built, so a bad body with an unknown
     user gives 400.
  4. Optional query filters are passed through when the command supports them: /transactions (account, from, to),
     /balances (at), /reports/income (from, to, currency), /reports/balance-sheet (at, currency), /reports/aging
     (at, payables), /invoices (status), /audit (by). A missing required query parameter gives 400.
  5. Invoice line fields are joined as `DESCRIPTION;QUANTITY;PRICE;TAXCODE` for `invoice create`, so a `;` inside
     a field is a 400 error. A missing tax_code becomes an empty field.
  6. Any unexpected exception gives 500 `{"error": "internal error: ..."}`.
  7. The request body must be a JSON object; an empty body on POST counts as `{}`.
  8. Unknown method/path combinations, including a wrong method on a known path, give 404.

## Do not redo
- Serving inside `execute` holds the BEGIN IMMEDIATE write lock; `_serve_run` commits first and reopens a
  transaction before returning so `execute` can COMMIT. Verified by the live run above: a write after serve works.
  Do not remove that dance.
- The two first-run failures (`customer add` unknown, `report income` 400) were only because cmd_invoices and
  cmd_reports did not exist yet. Re-running after merge fixed `test_invoice_flow`; `test_reports_and_audit` passes
  now too. Those are not API bugs.
- The 401 check for POST happens before the body is read on purpose (spec s11: missing user -> 401).
- The ResourceWarning from urllib's HTTPError was fixed with `with e:` in the test helper; not an API issue.
