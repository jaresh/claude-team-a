# fin — small-business finance system

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API.

## Usage

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python3 -m fin --db books.db init --currency EUR --admin alice
    python3 -m fin --db books.db --user alice account add Assets:Bank
    python3 -m fin --db books.db --user alice txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --db books.db balance
    python3 -m fin --db books.db serve --port 8080      # HTTP API (POST needs X-User header)

Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loan schedule,
user, audit, period, tax, customer, invoice, vendor, bill, reconcile, serve.
User errors exit with code 2 (message on stderr, nothing changed). Output is always one JSON
document (pretty-printed without `--json`).

Tests: `python3 -m unittest discover -s tests`.

Layout: `fin/core.py` (money, dates, schema, Ctx), `fin/cli.py` (registry, auth, dispatch),
one module per area (`books`, `automation`, `billing`, `reports`, `loan`, `api`).

## Assumptions

- Whole command runs in one SQLite transaction; any error rolls everything back.
- `python` may not be on PATH; use `python3`.
- Posting amounts with more than two decimals are rounded half up to cents.
- Transaction descriptions must be non-blank. `fx add` rejects same-currency pairs and rates <= 0.
  `convert --at` is required.
- `period close` of an already covered month is a no-op with no audit entry.
- Import: one transaction per file (any bad or closed-period row fails the whole file); duplicates
  keyed on (account, date, description, amount), repeats in one file skipped; first matching rule wins
  (regex `search`, case-insensitive); a rule's account must exist; zero amounts are errors; category
  account must share the import account's currency. Audit entry `import` only if rows were imported;
  `recurring.run` only if something was created.
- Budgets: expense accounts only, amount >= 0; `actual` converted to the book currency at month end.
- Recurring: occurrences computed from the start date (no day drift); start in a closed period is
  rejected at add time; recurring names are unique.
- Invoices: quantity must be > 0; bill and invoice payment accounts must be asset accounts.
  Tax rates are stored and shown as given.
- Reports: amounts per account are converted (at the report date) per currency then rounded;
  ledger converts descendant postings in other currencies at the `--to` date.
- Reconcile marks are kept per account/transaction; clearing already-cleared transactions is fine.
- Without `--user`, read commands work; the API needs `X-User` only on POST.
