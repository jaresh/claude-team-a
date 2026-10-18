Done
- Wrote /home/jaca/claude-team-a/bench/work/finance-team-3/README.md (598 lines). Sections: Running, Database and global options, Command reference (every group, one example each), HTTP API (routes, X-User, request bodies, status codes), Roles, Audit log (action table), Assumptions (grouped by area: core, ledger, fx, loans, parties/tax, invoices, bills, budgets, imports/rules, recurring, reports, reconcile, HTTP API).
- Done check `test -s README.md`: passes.
- No other files changed. Scratch files remain in .claude/team/scratch/readme/ (demo.db, statement.csv). Nothing committed.
- Earlier smoke run (scratch DB) confirmed the command examples run as written, and the error exits (viewer/editor refused exit 2, missing DB exit 2).

In progress
- The Assumptions section was compiled from the 13 handoffs in .claude/team/handoff/ and was not re-checked line by line against the code. Some entries are likely to be wrong or overstated, and the lead should check them before release. Entries I am least sure of: the --help stdout note under Core; the exact default and rounding details under Loans; the HTTP Content-Length and request-logger lines; the reconcile audit and cleared-balance details; the imports duplicate and empty-file rules; the recurring "skip already recorded" and closed-period rollback; the bills tax-posting account (Assets:TaxReceivable) and Payable total; the report trial-balance rounding rule; and the aging draft/payment-date rules.
- The Command reference examples and Audit log action table were checked against grep of the command definitions and smoke runs, but the audit "Written by" column for the reconcile and recurring rows was not re-verified.

Next step
- Verify each Assumptions bullet against its source file, then edit README.md. Start with: grep -n "" fin/*.py for the rules named above, and the handoff named for each area in .claude/team/handoff/<area>.txt. Remove or correct any bullet that does not match the code. Then run: test -s README.md
- Check the example command in "Loans" (`loan schedule 1000 12 3 --start 2026-01-31`) and the `report budget` output wording with: python3 -m fin loan schedule 1000 12 3 --start 2026-01-31

Do not redo
- Did not re-read the 13 handoffs in this context; the Assumptions content comes from my earlier reading (before the context summary).
- Did not commit. Did not touch fin/, tests/, or any shared file (.claude/team/changes.md has no entries from me).
- The `python` binary is absent here; `python3 -m fin` is the working form and is used throughout the README.
