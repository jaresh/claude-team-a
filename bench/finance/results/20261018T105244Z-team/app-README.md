# fin — small-business finance system

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API.

## Usage

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python3 -m fin --db fin.db init --currency EUR --admin alice
    python3 -m fin --user alice account add Assets:Bank
    python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin report income --from 2026-01-01 --to 2026-01-31
    python3 -m fin --db fin.db serve --port 8080      # POST needs header X-User

Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loan schedule,
user, audit, period, tax, customer, invoice, vendor, bill, reconcile, serve.
Exit code 2 = user error (message on stderr, nothing changed). Output is always JSON
(`--json` prints it compact, otherwise indented).

Tests: `python3 -m unittest discover -s tests` (takes about a minute).

Layout: `fin/core.py` (money, dates, schema, posting, fx), `fin/cli.py` (dispatch, permissions,
transactions), `fin/cmd_*.py` (commands), `fin/api.py` (HTTP).

## Assumptions

- Every command is one SQLite transaction, rolled back on error; a failed `init` leaves no file.
- Data-changing commands need `--user`; read commands work with or without. `reconcile` is a
  data-changing command (always audited, even with no `--clear`).
- Account auto-creation (Uncategorized, Receivable, Sales, SalesTax, Payable, TaxReceivable) is not audited.
- Posting amounts are rounded to cents. `fx add` rejects non-positive rates and same-currency pairs.
- Import: zero amounts and malformed rows are user errors (whole import fails); the target account's
  currency should be the book's currency. `rule add` needs an existing account and a valid regex.
- Budgets: non-expense accounts and negative amounts are rejected; actual is converted to the book currency.
- Recurring: occurrences are anchored on the start date; `recurring add` validates like `txn add`.
- Reports: income/liability/equity shown negated; networth = assets − liabilities; ledger converts at the `--to` date.
  With several currencies, per-account rounding can leave a one-cent gap in totals.
- Loans: principal must be > 0, rate >= 0, months >= 1.
- Bills: line tax code may be empty (no tax); line net must be positive; `bill pay` accepts any existing account;
  invoice/bill payment must be positive and not exceed the balance.
- Tax report: `--from` after `--to` is a user error.
- API: viewers get 403 on any POST; unknown/missing user 401; user errors 400.
