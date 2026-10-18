# fin — small-business finance system

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API.

## Usage
```
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
python -m fin --db books.db init --currency EUR --admin alice
python -m fin --db books.db --user alice account add Assets:Bank
python -m fin --db books.db --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin --db books.db --json balance
python -m fin --db books.db serve --port 8080      # POST needs header X-User
```
Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loan schedule,
user, audit, period, tax, customer, invoice, vendor, bill, reconcile, serve.
Exit 0 on success, 2 on a user error (message on stderr, nothing on stdout, nothing changed).
Without `--json` the same JSON is printed indented.

Layout: `fin/core.py` (Book, money/date helpers), `fin/cli.py` (registry/driver), `fin/admin.py`
(init, users, audit, periods), one module per feature area; tests in `tests/`.
Run tests: `python3 -m unittest discover -s tests`.

## Assumptions
- Currency codes are upper-cased; posting amounts are rounded half up to cents.
- A posting with no amount needs another amount in its account's currency; otherwise user error.
- Commands that change data are exactly those that audit; `reconcile` always counts as changing data (viewers refused, audit entry every run). `import`, `recurring run` write one audit entry even if nothing is created. `period close` of an earlier month changes nothing and writes no audit entry.
- Unknown `--user` on a read-only command is ignored.
- `fx add` rejects non-positive rates and same-currency pairs; the direct rate wins over an inverse one even if the inverse is newer.
- `txn add` rejects blank descriptions; `txn list --from > --to` returns `[]`; `--account` matches the account and descendants only.
- Rules: the account must exist when added; first rule (by order added) wins; the category account must have the import account's currency; zero amounts, blank descriptions or missing columns fail the whole import. Closed months are checked on every row first.
- Budgets: expense accounts only, non-negative; actuals are converted to the budget account's currency at month end. Recurring names are unique; occurrences are computed from the start date (not chained).
- Loans: principal > 0 (rounded to cents), rate >= 0, months 1–1200.
- Invoices: at least one line, quantity > 0, price >= 0; payments > 0, at most two decimals, to an existing asset account; numbering counts issued invoices per invoice-date year. Draft invoices are excluded from the tax report and aging.
- Bills: line net > 0, ref required and unique per vendor; payment account must be an asset; a line account in a foreign currency makes the posting fail as unbalanced.
- HTTP: 404 for unknown paths and non-numeric ids, 400 for unknown numeric ids and bad bodies; auth is checked after routing and before body parsing; empty POST body is `{}`.
- Reports use `retained_earnings` = income − expenses up to the date; networth months are inclusive and `--from > --to` is a user error.
