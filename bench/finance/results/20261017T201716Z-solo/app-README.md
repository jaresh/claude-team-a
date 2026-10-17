# fin – small-business finance system

Python 3.12+, standard library only (sqlite3, decimal, http.server, unittest).

```
python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json balance
python3 -m fin --db fin.db serve --port 8080
python3 -m unittest discover -s tests
```

Global options go before the command; `--db` defaults to `./fin.db`. `--json` prints one JSON
document; without it the same data is printed as plain text. User errors (including permission
errors and argparse usage errors) exit with code 2, print to stderr only and change nothing
(every command runs in one SQLite transaction that is rolled back on error).
Commands: `init user audit account txn balance fx convert rule import budget recurring loan
period tax customer vendor invoice bill reconcile report serve` (see the task spec for details).
Layout: `fin/core.py` (all logic), `fin/cli.py`, `fin/server.py` (HTTP), `tests/`.

## Assumptions

- Amounts are rounded half-up to cents when parsed (postings, budgets, payments, ...). Conversion
  results and report values are rounded half-up once per account/amount.
- A command that "reads" needs no user; an unknown `--user` on a read is ignored. Any other command
  needs a valid user. `reconcile` always counts as a change (it records marks), as do `import` and
  `recurring run` even when they create nothing, and `period close` even if it closes nothing new;
  each appends an audit entry.
- Account names: non-empty segments, no surrounding spaces. New parents take the currency of the new
  account. `ledger`/`budget` sum descendants without conversion.
- `rule add` requires an existing account. A zero import amount goes to `Income:Uncategorized`
  (only negative amounts go to Expenses). Imported-row identity is (account, date, description
  stripped, amount). Empty CSV rows are ignored.
- `convert`: if any direct FROM→TO rate exists on or before the date, the latest direct one is used;
  only otherwise the inverse of the latest TO→FROM rate. Rates must be positive.
- Reports convert each account's balance (an account has one currency) and sum the rounded values,
  so with conversion `total_assets = total_liabilities + total_equity` can differ by a cent.
  Trial balance, networth and balance-sheet also accept `--currency`.
- Budgets must be for existing expense accounts and non-negative; a repeated tax code, customer,
  vendor or user is an error. Tax rates are stored and shown as given.
- Recurring postings are balanced when added (the blank amount is fixed then). `recurring run`
  creates the due occurrences of all recurring items in date order and remembers progress per item.
- Invoices/bills are in the book's currency. Quantity must be > 0, price ≥ 0; line price shown with
  2 decimals unless it has more precision. `--line` is split from the right on `;`, so descriptions may
  contain `;`; the tax code may be omitted or empty. Invoices need an asset payment account; bills
  accept any existing book-currency account. Unknown `--status` values are user errors.
- Aging/tax reports ignore draft invoices. `by_code` lists codes of lines in the period (also with 0 tax).
- Reconciliation uses postings to the exact account (not descendants).
- HTTP: single-threaded server on 127.0.0.1 (`serve --host` to change). Unknown invoice id → 404,
  unsupported method → 405. Authorization (401/403) is checked before the body is parsed. Extra
  GET endpoints: `/bills`, `/bills/ID`, `/reports/{trial-balance,networth,tax,budget}`.
- `loan schedule` is a pure calculation and does not need a database.
