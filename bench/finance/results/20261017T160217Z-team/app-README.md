# fin — small-business finance system

Python 3.12+, standard library only. Double-entry ledger in SQLite, Decimal money.

## Usage

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python3 -m fin init --currency EUR --admin alice
    python3 -m fin --user alice account add Assets:Bank
    python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin balance
    python3 -m fin --db fin.db serve --port 8080      # JSON API; POSTs need header X-User

Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loan schedule,
user, audit, period, tax, customer, vendor, invoice, bill, reconcile, serve.
User errors exit 2 with a message on stderr and change nothing. Output is always JSON
(indented unless `--json`).

Layout: `fin/core.py` (accounts, txns, fx, users, audit, periods), `fin/db.py` (storage, posting),
`fin/commands.py` (registry, permissions, audit, transactions), `fin/bank.py`, `fin/reports.py`,
`fin/loans.py`, `fin/recon.py`, `fin/billing.py`, `fin/api.py`, `fin/cli.py`.
Tests: `python3 -m unittest discover -s tests`.

## Assumptions

- Use `python3` (no `python` alias assumed). Only one posting currency per account; amounts with more than two decimals are rounded half up to cents.
- A failed `init` leaves no database file. Non-`init` commands on a missing database are user errors.
- Audit: written for every successful data-changing command; `period close` of an already-closed month changes nothing and is not audited. `init` records the admin as user.
- Exchange rates: direct FROM→TO rate preferred over the inverse of TO→FROM, even if the inverse is more recent; same-day ties go to the latest added. Converted amounts are rounded to cents.
- Reports convert each account's per-currency total separately, so in multi-currency books totals can differ from the identity by a cent. `trial-balance` and `networth` use the book currency (no `--currency`).
- Rules: regex searched (`re.search`) case-insensitively; invalid patterns are rejected on `rule add`; `rule add` creates its category account if missing.
- Import: dedupe keys are (account, date, description, amount) of previously *imported* rows only; zero amounts, bad dates/numbers or missing columns fail the whole file; descriptions are stripped.
- Budgets need an existing expense account and an amount ≥ 0; `report budget` converts foreign-currency actuals at month end.
- Recurring names are unique; occurrences are computed from the start date.
- Billing works in the book currency only (accounts used must be in it). Invoice lines are `DESC;QTY;PRICE;TAXCODE` (the final semicolon is required, code may be empty). Invoice and bill ids each start at 1; a bill `--ref` is unique per vendor; payments must be positive; `bill pay` accepts an asset or liability account.
- Reconcile also echoes `date`; `--clear` ids must have a posting to exactly that account (not sub-accounts) dated on or before the date.
- Loans: principal > 0, rate ≥ 0, months ≥ 1.
- API: missing/unknown `X-User` on POST → 401, insufficient role → 403, user errors → 400.
