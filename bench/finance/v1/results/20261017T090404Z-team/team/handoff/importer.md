# Handoff: importer

## Done
Files (all new, no shared files touched, so no changes.md rows):
- `fin/cmd_import.py`: `rule add|list`, `import FILE --account ... [--date-col --desc-col --amount-col --skip-header]`. Functions: `add_rule`, `list_rules`, `import_csv`.
- `fin/cmd_budget.py`: `budget set` in `register(sub)`; `register_report(rsub)` adds `report budget MONTH`. Functions: `set_budget`, `budget_report(conn, month)`.
- `fin/cmd_recurring.py`: `recurring add|run`. Functions: `add_recurring`, `run_recurring`, `_occurrences`.
- `tests/test_import.py` (7 tests), `tests/test_budget.py` (4 tests), `tests/test_recurring.py` (4 tests).

Checks:
- `python3 -m unittest tests.test_import tests.test_budget tests.test_recurring tests.test_basic`: 19 tests, OK.
- `python3 -m unittest discover -s tests`: 36 tests, OK (at the time of the run).

Behaviour choices beyond the plan (review if they matter):
- `rule add` rejects an empty pattern.
- `budget set` rejects a negative amount; amounts are rounded half up at entry.
- `budget report` lists only accounts that have a budget for that month. Descendant postings in another currency are converted with `core.convert` at month end, then added (same per-account approach as reports).
- `import` output: `skipped` counts duplicates only. Blank rows are ignored and not counted. Zero amounts go to Expenses:Uncategorized.
- `import` with a rule target or uncategorised account in a different currency from ACCOUNT fails with core's "transaction does not balance". Core has no cross-currency transactions, so this is not fixed here.
- `recurring run` rolls back everything on a UserError, so a failure creates nothing.
- `_occurrences` stops quietly on OverflowError near year 9999.

## In progress
Nothing. The `report budget` CLI route is not tested end to end: `report` is created by the reports teammate's `cmd_reports.register`, which must call `cmd_budget.register_report(rsub)`. `tests/test_budget.py::test_register_report_adds_budget` covers the registration on a bare argparse parser. The budget report itself is covered by calling `budget_report` directly.

## Next step
After the reports module is merged, check the CLI route with:
`python3 -m fin --db /tmp/x.db --json report budget 2026-01`
(create the db first with `init --currency EUR`). Then run the full suite: `python3 -m unittest discover -s tests`.

## Do not redo
- Ran the done-check command above: 19 tests pass. Full discovery: 36 pass.
- One failure during the run came from my own test fixture (semicolon-separated CSV read by the comma-delimited csv reader). It is fixed in `tests/test_import.py`. The importer code was not at fault.
- core.py, __main__.py, cmd_basic.py, helpers.py were not edited.
