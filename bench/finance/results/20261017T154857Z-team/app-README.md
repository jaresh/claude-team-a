# fin — small-business finance system

Python 3.12+, standard library only. Run `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(global options before the command; `--db` defaults to `./fin.db`). Every successful command prints one JSON
document (with or without `--json`; `--json` is compact). User errors exit with code 2, message on stderr,
nothing on stdout, nothing changed (each command runs in one SQLite transaction).

    python -m fin init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice account add Expenses:Rent
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin balance
    python -m fin serve --port 8080      # HTTP API; POSTs need header X-User

Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, loan, report
(income, balance-sheet, networth, budget, trial-balance, ledger, aging, tax), user, audit, period, tax,
customer, invoice, vendor, bill, reconcile, serve.

Layout: `fin/core.py` (money, dates, Book, posting engine, schema), `fin/cli.py` (parser, permissions,
transactions), one module per feature area, `tests/` (`python3 -m unittest discover -s tests`).

## Assumptions
General
- Output is always JSON (pretty unless `--json`). Reads need no `--user`. Names of users match `[\w.@+-]+`; descriptions must be non-blank.
- `init` prints `{"currency","admin"}`; other write commands print the created/changed object.
- Balance entries include descendants' postings and all ancestors; currency keys sorted.
- Closing an earlier month than the closed one succeeds, changes nothing, and is audited.
- Audit entries are written for every successful data-changing command, even if it changed nothing (e.g. an import of 0 rows, `recurring run` creating 0).
- Tax codes `[A-Za-z0-9_.-]+`, non-negative rate stored as given.

Rates, import, rules
- fx rate must be > 0, FROM != TO; later entry on the same date wins. `convert --at` is required; rounded once.
- Rule pattern must be a valid non-empty regex (`re.search`, case-insensitive), account must exist at `rule add`.
- CSV: UTF-8 (BOM ok), blank lines skipped, fields stripped, zero amounts are errors, import is atomic; already-imported duplicates are skipped even in closed months.

Budgets, recurring, loans
- Budgets in the book currency, non-negative, expense accounts only; actuals converted at month end.
- `recurring add` rejects duplicate/empty names and a start in a closed period; a closed-period occurrence fails the whole `recurring run`.
- Loan principal is rounded to cents first; `loan schedule` needs an existing book.

Reports
- Each account is converted and rounded once; totals sum the rounded figures. `--from` later than `--to` is an error.
- Tax report counts non-draft invoices and all bills by document date; only lines with a tax code; `by_code` includes zero-rate codes.
- Aging: balance = total − payments dated on or before `--at`; drafts and future-dated documents excluded.
- Reconcile counts only postings on exactly ACCOUNT; duplicate `--clear` ids are de-duplicated; audited only when something is cleared.

Invoices and bills
- Invoice line `--line` is split from the right, so descriptions may contain `;`. Zero-total invoices can be issued but not paid.
- Payments must be positive, at most the balance, into an existing asset account (not Receivable/Payable).
- Bill tax code may be empty (no tax); bill line amounts must be ≥ 0; bills in non-book currencies are not supported.

API
- Each route runs the matching CLI command in-process; errors map to 400 (input), 401 (missing/unknown X-User), 403 (role), 404 (path).
