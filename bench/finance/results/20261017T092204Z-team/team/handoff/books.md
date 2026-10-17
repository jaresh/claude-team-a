# Handoff: books

## Done
- `fin/cmd_books.py` (new): commands init, user add, user list, audit list [--by], account add, account list,
  txn add, txn list [--account --from --to], balance [--at], period close, period status. Exports `COMMANDS` only (no SCHEMA; core creates the shared tables).
- `tests/test_books.py` (new): 38 tests covering spec sections 1, 2, 3, 11, 12, incl. error cases (exit 2, empty stdout, nothing changed), roles (viewer/editor/admin, missing and unknown user), audit entries and keys.
- Check: `python3 -m unittest tests.test_books -q` gives **38 tests, OK**. There is no `python` binary on this machine, only `python3` (3.14).
- Global: `python3 -m unittest discover -s tests -q` gives 51 tests, 7 failures, all in `tests/test_reports.py` (balance, income, loan, balance-sheet). None are in books. The reports work is still in progress.
- No shared files edited, so `.claude/team/changes.md` is unchanged. Nothing committed.

## In progress
- Nothing. Task complete.

## Next step
- Lead: merge check with `python3 -m unittest discover -s tests -q`; once `cmd_reports` is finished, its failures should clear. No action for books.

## Do not redo
- Checked core.py, cli.py, helpers.py: `execute` handles auth (write/admin → 401/403), BEGIN/ROLLBACK, and init-on-existing-db. Books relies on them and does not duplicate them.
- `post_txn` already checks closed periods, balance, unknown accounts, and the "at most one blank posting" rule. `txn add` only adds: date parse, `_cents` check (more than 2 decimals → user error), and the audit call.
- `Book.postings()` with `account` and date filters gives `txn list` its rows. Dedupe is by `dict.fromkeys` on txn_id (order preserved).
- `balance` builds ancestors from posting account names. Zero sums show as `"0.00"`. Per-currency keys are kept.

## Assumptions (for README)
- `init` prints `{"currency": "EUR", "admin": "root"}`. The init audit entry's user is the admin name (passed explicitly to `book.audit`).
- `period close M` when already closed through ≥ M: returns the current `{"closed_through": ...}` and writes **no** audit entry (spec says "changes nothing"). Otherwise sets meta and audits `period.close` M. It returns `{"closed_through": M}`.
- `user add` returns `{"name","role"}`. `account add` returns `{"name","type","currency"}`. `txn add` returns the txn dict.
- `txn add --posting` is required (at least one; post_txn enforces 2+). Amounts with more than two decimals are a user error (`1.234`), to keep sums exact.
- Parent accounts created implicitly by `account add` get the given currency; existing parents keep theirs, so `Assets` can be EUR while `Assets:Usd` is USD.
- `balance` lists every ancestor of an account that has postings, even if its sum is zero.
- `user list` and `account list` are sorted in Python by name.
- `audit list --by NAME` filters on the user column.
