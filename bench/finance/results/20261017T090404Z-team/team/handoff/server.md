# Handoff: server

## Done
- `fin/cmd_serve.py` (new): `register(sub)` adds `serve --port N` (default 8000, range checked, bind failure -> UserError). `make_server(db_path, port)` returns an unstarted `ThreadingHTTPServer` on 127.0.0.1 with `server.db_path` set. Handler opens a fresh `core.connect` per request and closes it after. Routes: GET /accounts, GET+POST /transactions (GET accepts optional account/from/to), GET /balances?at=, GET /reports/income?from=&to=[&currency=], GET /reports/balance-sheet?at=[&currency=]. Report functions are imported lazily inside the handler (`cmd_reports.income_report`, `cmd_reports.balance_sheet`), so the CLI still starts if cmd_reports is missing. Status codes: 201 on POST, 400 on UserError or bad JSON or bad shape, 404 unknown path, 405 wrong method on known path (PUT/PATCH/DELETE routed to the same handler), 500 with traceback on stderr for anything else. Request logging silenced.
- `tests/test_serve.py` (new): 6 tests run against make_server in a thread on port 0. One report test is skipped until `fin.cmd_reports` has `income_report` and `balance_sheet`.
- `README.md` (new): every command with an example, how to run tests, Assumptions section per plan.
- Check: `python3 -m unittest tests.test_serve tests.test_basic` -> OK (skipped=1, the reports test). Also OK with `-W error::ResourceWarning`.
- No edits to shared files, so nothing added to `.claude/team/changes.md`. Did not touch core.py, __main__.py, cmd_basic.py, helpers.py.
- Not committed.

## In progress
- Nothing.

## Next step
- After the reports teammate merges `fin/cmd_reports.py`, rerun `python3 -m unittest tests.test_serve tests.test_basic`; the report test should run (not skip) and must pass.
- Before the final check, verify README examples for importer, reports and loan match their final CLI syntax (I wrote them from the plan: `import`, `rule add/list`, `budget set`, `report budget|income|balance-sheet|networth`, `recurring add/run`, `loan schedule`). If a flag differs, fix README.md only.

## Do not redo
- `main()` in `fin/__main__.py` connects to the DB before calling any command's fn, so `serve` needs an existing DB file, and `loan schedule` does too. README says so.
- A plain `urllib` HTTPError must be closed (`with e:`) or the tests emit ResourceWarning; already fixed in tests/test_serve.py.
- `core.parse_amount` quantizes with ROUND_HALF_UP, so JSON float 1.005 -> "1.01" (tested).
