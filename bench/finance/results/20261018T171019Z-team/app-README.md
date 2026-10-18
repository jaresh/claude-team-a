# fin: a small-business finance system

Double-entry books, bank import, budgets, recurring entries, loans, invoices and bills, reports,
bank reconciliation, roles, and an HTTP API. Python 3.12+, standard library only (sqlite3,
decimal, http.server, unittest).

## Running

    python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python -m unittest discover -s tests

Global options come before the command. `--db` defaults to `./fin.db`. Output is one JSON
document (indented, or compact with `--json`). A user error exits with code 2, prints the message
to stderr, prints nothing to stdout, and changes nothing.

Quick start:

    python -m fin init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice account add Expenses:Rent
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin balance
    python -m fin report balance-sheet --at 2026-01-31

Serve the API:

    python -m fin --db fin.db serve --port 8080
    curl -H 'X-User: alice' -H 'Content-Type: application/json' \
        -d '{"date":"2026-01-06","description":"Coffee","postings":[{"account":"Expenses:Food","amount":"4.50"},{"account":"Assets:Bank"}]}' \
        http://127.0.0.1:8080/transactions

## Layout

- `fin/core.py`: errors, money and dates, schema, posting rules, command registry, dispatch.
- `fin/books.py`: init, users, accounts, audit log, closed periods.
- `fin/ledger.py`: transactions, balances, exchange rates, convert.
- `fin/importer.py`: categorisation rules and CSV import.
- `fin/budgets.py`, `fin/recurring.py`, `fin/loans.py`, `fin/reconcile.py`.
- `fin/contacts.py`: tax codes, customers, vendors.
- `fin/documents.py`: shared invoice and bill logic. `fin/invoices.py`, `fin/bills.py`: commands.
- `fin/reports.py`: income, balance sheet, net worth, trial balance, ledger, tax.
- `fin/server.py`: HTTP API. Each request becomes one `core.run` call.

## Assumptions

Money and dates
- Amounts are at most two decimals (postings, payments, budgets, prices). Rates and quantities
  may have more decimals. Rounding is half up to cents, applied per line or per account, never
  to the totals of already-rounded values.
- A zero amount is shown as `0.00`, never `-0.00`.

Books and users
- Currency codes are three ASCII letters, stored uppercase (book, accounts, fx).
- `init` prints nothing. Names (users, admin) must be non-empty after trimming.
- Read commands ignore `--user`. Write commands need a known `--user` (missing or unknown is
  401 in the API, exit 2 on the CLI). Viewers get 403 on writes.
- Every successful write command writes one audit entry. `period close` changes nothing and
  writes no entry when the month is not later than the closed month; it still returns the status.
- `audit list --by NAME` for an unknown name returns `[]`.

Transactions and reports
- `txn list --account` matches whole account segments (`Exp` does not match `Expenses`).
- `balance` includes every account with postings on or before the date, plus its ancestors,
  with zero sums shown as `0.00`.
- `convert` uses the latest direct rate on or before the date. Only if there is none does it
  use the inverse of the reverse-direction rate. The same currency converts 1:1.
- Report currency conversion converts each account's total at the report date and rounds that
  account's value. `networth` uses the book currency at each month end.
- `report budget` sums only postings in the budget account's currency.
- `report trial-balance` and `report balance-sheet` are exact only when every account is in the
  report currency; with mixed currencies the per-account rounding can leave a cent of difference.

Imports and recurring
- Import: the bank account must already exist. A row matching an existing imported row (same
  account, date, description, amount), or an earlier row in the same file, is skipped. Skipped
  rows are checked before the closed-period check, so re-importing rows already in a closed month
  succeeds. A new row in a closed month fails the whole import.
- Blank rows and the header row (with `--skip-header`) are skipped. The file is read as UTF-8
  with an optional BOM. A zero amount counts as income (`Income:Uncategorized`).
- A rule's account is created at import time if missing (book currency).
- `recurring add` checks the postings by posting them in a savepoint, then rolling back.
  Occurrences are computed from the start date, so monthly day-of-month clamping is correct.

Invoices and bills
- Invoice quantity must be greater than zero and is shown as given. The price must be at least
  zero and is shown with two decimals. Net is round(quantity × price).
- Customer and vendor names are stored as typed; invoices and bills look them up by that string.
- Tax codes cannot be empty or contain `;`. An empty tax code on a line means no tax.
- Payments are not checked against issue or bill dates. The pay account must be an existing
  asset account (for both invoices and bills).
- Invoice numbers are `INV-YYYY-NNNN`, counted per invoice year.
- Bill refs are unique per vendor (the same ref under another vendor is allowed). A bill is
  posted immediately. Bill lines may use an expense or an asset account; zero net is allowed.
- `report aging` and `report tax` look only at the documents' own dates; `report tax` counts
  non-draft invoices and all bills.

Reconciliation
- `--clear` takes transaction ids. `cleared_balance` and `uncleared` use the exact account name
  (not descendants). Cleared marks persist across runs.

Loans
- Monthly interest is rounded to cents each month; the last row repays the remaining balance
  with its interest, so the final balance is `0.00`.

HTTP API
- `serve` listens on 127.0.0.1. Reads need no user. POST needs `X-User`. Success returns 201
  for `POST /transactions` and `POST /invoices`, and 200 otherwise. Errors return the status of
  the user error with `{"error": ...}`. Unknown routes return 404.

## Not done / open

- Nothing is committed; see the git status of this worktree.
- Authentication is only the `X-User` header, with no tokens: the API is for trusted networks.
- Only the CLI and API described above exist; there is no import of other formats, no PDF output.
