# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(`python -m fin` if `python` exists on your PATH). Tests: `python3 -m unittest discover -s tests`.

## Usage
```
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice account add Expenses:Rent
python3 -m fin --user alice --json txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json balance
python3 -m fin --json report income --from 2026-01-01 --to 2026-01-31
python3 -m fin --user alice serve --port 8080      # HTTP API, POST needs header X-User
```
Commands cover: accounts, transactions, balances, fx/convert, rules and CSV import, budgets, recurring,
reports (income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loans, users/audit,
closed periods, tax codes, customers/invoices, vendors/bills, reconciliation. See the spec sections for outputs.
Layout: `fin/cli.py` (dispatch, auth, transactions), `db.py` (schema, `Book` helpers), `money.py`, one module per feature area.

## Assumptions
- Without `--json`, output is the same JSON, indented. Commands with no result document
  (account add, user add, fx add, period close, ...) print nothing.
- Amounts are rounded half away from zero to cents on input and output; converted values are rounded per account
  (so in multi-currency books with inexact rates, balance-sheet / trial-balance totals can differ by a few cents).
- Currency codes are upper-cased. `fx add` rejects equal currencies and non-positive rates.
- Descriptions must be non-empty. `period close` of an already-closed month prints nothing and writes no audit entry.
- Import: ACCOUNT must exist; zero amounts, bad rows, or any row in a closed month fail the whole file. Duplicate key is
  (account, date, description, amount). Rules: first match by insertion order; target account is created on use.
- Ranged reports reject FROM > TO. `report ledger` converts each posting at its own date into the account's currency.
- `reconcile` writes an audit entry only when at least one `--clear` is given; it ignores closed periods.
- Bill payments may come from any existing account; invoice payments need an asset account.
- The HTTP API calls the same command handlers in-process; it binds to 127.0.0.1.
- Per-teammate detail on remaining gaps was decided case by case and covered in tests.
