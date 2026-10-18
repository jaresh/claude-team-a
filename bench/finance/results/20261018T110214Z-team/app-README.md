# fin — small-business finance system

Python 3.12+, standard library only.

## Usage
    python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python -m fin --db books.db init --currency EUR --admin alice
    python -m fin --db books.db --user alice account add Assets:Bank
    python -m fin --db books.db --user alice txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --db books.db --json balance
    python -m fin --db books.db serve --port 8080      # POST needs header X-User

Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loan, user, audit,
period, tax, customer, invoice, vendor, bill, reconcile, serve. See the task spec for each command's
output. User errors exit 2 with a message on stderr and change nothing.

Tests: `python -m unittest discover -s tests`.

## Layout
`fin/core.py` shared helpers (money, dates, accounts, transactions, fx); `fin/cli.py` parser and
transaction wrapper (each command runs in one SQLite transaction, rolled back on user error);
`fin/ctx.py` permissions and audit; one module per feature; `fin/api.py` HTTP server reusing the
same service functions.

## Assumptions
- Without `--json`, output is the same JSON, pretty-printed. `init` prints `{"currency","admin"}`; `account add` prints the account.
- Read-only commands never need `--user`. `reconcile` counts as a write (viewer denied) and is always audited, even with no `--clear`.
- Currency codes are upper-cased. Rates and budgets must be positive / non-negative; FROM=TO in `fx add` is rejected.
- Direct FROM→TO rate (latest on or before the date) beats the inverse of a TO→FROM rate, even if the inverse is newer.
- Report conversion: each account's per-currency balance is converted then rounded once; totals sum the rounded values (a 1-cent imbalance is possible with many converted accounts). `report ledger` converts to the account's currency.
- Import: rows identical to an already-imported row (or repeated in the file) are skipped; any closed-period row fails the whole import; zero amounts go to `Income:Uncategorized`; rule accounts must exist; empty or invalid regexes are rejected; an import is audited even if it imports 0 rows.
- Recurring: occurrence k is the start plus k periods (no drift); a rule may be added for past/closed dates but `run` fails if any pending occurrence is closed; `recurring.run` is audited even if it creates 0.
- Budgets: non-negative amounts on existing expense accounts.
- Loans: principal at most 2 decimals; row n dated start + n months.
- Invoices: at least one line; payments must be positive with ≤2 decimals to an existing asset account; any non-draft invoice counts as issued for aging and tax reports; aging bucket `90+` means more than 90 days past due.
- Internal transactions of invoices, bills, imports and recurring runs get no separate `txn.add` audit entry.
- API: `GET /transactions` also accepts `account`, `from`, `to`; errors are `{"error": ...}`; each request uses its own SQLite connection.
