# fin — small-business finance system

Python 3.12+, standard library only. Storage: SQLite. Money: `Decimal`.

    python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python -m fin --db books.db init --currency EUR --admin alice
    python -m fin --db books.db --user alice account add Assets:Bank
    python -m fin --db books.db --user alice --json txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --db books.db serve --port 8080          # JSON API
    python -m unittest discover -s tests                    # run the tests

Global options go before the command. `--db` defaults to `./fin.db`. Exit code 0 on success; user errors
exit 2 with a message on stderr, nothing on stdout, and no change to the database (every command runs in
one SQL transaction). All sections of the specification are implemented: books/accounts, transactions,
balances, exchange rates, CSV import with rules, budgets, recurring transactions, income / balance-sheet /
net-worth / aging / tax / trial-balance / ledger reports, loans, users/roles/audit log, closed periods,
tax codes, customers, invoices, vendors, bills, reconciliation, and the HTTP API
(`fin/api.py`; `POST` needs `X-User`; 401 unknown/missing user, 403 role, 400 user error, 404 unknown path
or unknown invoice).

Layout: `fin/core.py` (all logic, class `Book`), `fin/cli.py` (argparse), `fin/api.py` (HTTP), `tests/`.

## Assumptions

- Without `--json`, output is the same document pretty-printed (indented JSON); with `--json` it is one line.
- All currencies use 2 decimals; every input amount is rounded half up to cents. Currency codes are upper-cased.
- `init` on an existing non-empty file is an error (an empty file is accepted). Other commands on a missing
  database are user errors and do not create the file.
- Duplicate tax codes are an error. Recurring names need not be unique. Customer/vendor duplicates are errors.
- `reconcile` always counts as a data-changing command (needs `--user`, appends an audit entry), as do
  `import` and `recurring run` even when they create nothing. `period close` of an already-closed month
  changes nothing and writes no audit entry.
- Reads (`--user` optional) ignore an unknown `--user`. `loan schedule` needs no database; `convert` does.
- `rule add` requires the target account to exist and the pattern to compile; regex uses `re.search`.
  Import dedup key is (account, date, description, amount); the closed-period check covers every row,
  including rows that would be skipped as duplicates.
- Budgets: expense accounts only, non-negative. `actual` sums raw posting amounts of the account and
  descendants (no currency conversion).
- Reports convert each account's balance (one currency per account) to the target currency at the
  report's end date and round per account; totals sum the rounded figures, so with conversion the balance
  sheet identity can be off by a cent from rounding.
- `report networth` also accepts `--currency`. `trial-balance` converts to the book currency.
- Invoice `price` is shown with two decimals when it has at most two, otherwise as given. Lines are
  `DESC;QTY;PRICE;TAX` (a missing 4th field means no tax; description may contain `;`).
- Invoice/bill payments need an asset account in the book currency, a positive amount no more than the
  balance. Issue/pay are blocked if the transaction date is in a closed month; `bill create` too.
- Invoice numbers count issued invoices of the invoice date's year. Bills and invoices have separate id
  sequences. Aging includes bills/invoices dated on or before the date with a positive remaining balance.
- `report tax` counts issued (non-draft) invoices; `by_code` omits lines without a tax code.
- Reconciliation clears are exact-account (descendants are not included).
- Unknown invoice ids: user error in the CLI, 404 in the API.
