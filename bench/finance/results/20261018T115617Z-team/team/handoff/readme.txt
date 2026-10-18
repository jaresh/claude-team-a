DONE
----
Files changed (only these two, both owned by the readme task):
- /home/jaca/claude-team-a/bench/work/finance-team/README.md (new): system overview, install (stdlib, Python 3.12+, python3), quick start covering init through serve, one-line options per command (CLI, plus the API routes and status mapping), users and roles, JSON and exit-code rules, assumptions grouped by area and deduplicated from all 12 handoffs (api.txt has no Assumptions heading, so its routes, status mapping and serve notes were taken from its text), how to run tests.
- /home/jaca/claude-team-a/bench/work/finance-team/tests/test_e2e.py (new): 20 tests. 19 use subprocess `python3 -m fin --db <tmp> --json`; 1 is the API test (api.make_server(db, 0) in a thread). Covers spec sections 1-17 in brief, including permissions (viewer exit 2, closed period exit 2 with empty stdout), audit, and reconcile.
- Lead decisions reflected in README: trial-balance rounding residual goes on the largest balance (verified in fin/ledger.py); cli.main prints nothing when a handler returns None (verified in fin/cli.py lines 53-56); loans MAX_MONTHS = 1200 (verified in fin/loans.py line 11).

Check results:
- `python3 -m unittest discover -s tests` from the repo root: Ran 395 tests, OK (run twice, the second after the README audit-list edit).
- `python3 -m unittest tests.test_e2e` alone: 20 tests, OK, about 18 s (under the 60 s limit).
- One failure found and fixed in my own test code: the bad API body had one posting, so the error was "at least 2 postings", not "unknown account". Fixed by giving it two postings. No fin/ file was touched.
- No commit made. git status shows only README.md, fin/ and tests/ as untracked (fin/ and tests/ are not mine).

IN PROGRESS
-----------
Nothing. The task is complete.

NEXT STEP
---------
Lead: review README.md and tests/test_e2e.py, then commit. Command to re-check:
  cd /home/jaca/claude-team-a/bench/work/finance-team && python3 -m unittest discover -s tests

Points for the lead to review in the README:
- The Quick start block was written by hand from the verified CLI usage lines. It was not executed as a script, so a copy-paste run is the real test.
- The assumption list is deduplicated but worded by me. The handoffs were the source; no handoff text was changed.
- ledger.txt's Next step asked the lead to decide the 1-cent trial-balance gap. The lead's residual decision now covers it, so the README states the residual rule and not an open question.
- statements.txt and invoices.txt say they were "not tested" or "for the lead to review". The README states their behavior as implemented. The e2e tests cover the main paths in those areas, not every edge case.

DO NOT REDO
-----------
- Option names were checked with `python3 -m fin <group> <leaf> --help` for txn add, invoice create, bill create, report income/ledger/tax/budget/networth/aging/trial-balance/balance-sheet, loan schedule, recurring add, import, reconcile (--clear is repeatable, action=append), serve, user add, account add, fx add, budget set, bill pay, invoice pay, invoice list, bill list, customer add, vendor add, tax add, period close, audit list, balance, convert, init, rule add. Do not re-check.
- Audit action names were checked with grep of audit("...") calls in fin/*.py. Do not re-check.
- The e2e test's ledger, balance-sheet, aging, and tax expected values were all confirmed by running the suite, so a failure there means a product change, not a test error.
- Ruled out: the e2e failure was a test-side error (see above), not a product bug. No product bug was found by the e2e tests.
