# fin — small-business finance system

Python 3.12+, standard library only (sqlite3, Decimal, http.server, unittest).

## Use

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python3 -m fin --db books.db init --currency EUR --admin alice
    python3 -m fin --db books.db --user alice account add Assets:Bank
    python3 -m fin --db books.db --user alice txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --db books.db report income --from 2026-01-01 --to 2026-01-31
    python3 -m fin --db books.db serve --port 8080      # POSTs need header X-User: NAME

Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, loan, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), user, audit, period,
tax, customer, invoice, vendor, bill, reconcile, serve. Exit code 2 = user error (message on stderr,
nothing on stdout, nothing changed). Run `python3 -m fin COMMAND -h` for options.

Layout: `fin/core.py` (money, dates, schema, Book), `fin/cli.py` (registry/dispatch), `admin.py`
(accounts, txns, fx, users, audit, periods), `banking.py` (rules, import, budgets, recurring, loans),
`invoicing.py` (tax, customers, vendors, invoices, bills, aging), `reports.py` (reports, reconcile),
`api.py` (HTTP). Each feature is also available as plain Python functions taking a `Book`.

## Tests

    python3 -m unittest discover -s tests

## Assumptions

- Output is JSON also without `--json` (pretty-printed); `--json` prints it compact.
- Account currencies: `fx add` needs 3 uppercase-letter codes, distinct, rate > 0. `convert` requires `--at`.
- `account add` returns the new account; parents are created silently and only the named account is audited.
- `period close` is audited on every successful call, even if it changes nothing.
- `audit list --by` for an unknown user returns `[]`. Transaction descriptions may be empty.
- `txn list --account` matches the exact account or descendants (colon boundary).
- Import: rows validated first (bad date/amount, zero amount, closed month) — any failure imports nothing;
  dedupe key is (account, date, description, amount); blank CSV lines skipped; category created on demand.
- Budgets only for expense accounts; `actual`/`remaining` in the account's currency, remaining = budget − actual.
- Recurring: all due occurrences are checked against closed periods before any is created.
- Loans: rate ≥ 0, principal > 0, months ≥ 1.
- Reports: income/balance-sheet convert per account and currency at the report's end date; ledger converts
  nothing (account currency). With several currencies per-account rounding may leave a one-cent mismatch.
  `networth` and `trial-balance` use the book currency. Tax report treats invoice/bill tax as book currency.
- Invoices: price is shown with two decimals, quantity as given; numbers are max+1 within the invoice year;
  customers/vendors/tax codes/bill refs must be unique; negative terms, rates, quantities, prices are errors.
  Aging excludes drafts and zero/negative balances. Bill payment account must be an asset account;
  bill line accounts must be expense or asset accounts.
- Reconcile validates all `--clear` ids before marking any; marking is idempotent.
- HTTP: role checks use the same matrix as the CLI (viewer cannot POST, editor can).
