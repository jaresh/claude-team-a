# fin — small-business finance system

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API.

```
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice --json txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json report income --from 2026-01-01 --to 2026-01-31
python3 -m fin --user alice serve --port 8080
python3 -m unittest discover -s tests
```

Global options (`--db PATH` default `./fin.db`, `--json`, `--user NAME`) come before the command.
Commands: `init`, `account`, `txn`, `balance`, `fx`, `convert`, `rule`, `import`, `budget`, `recurring`,
`report` (income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), `loan schedule`,
`user`, `audit list`, `period`, `tax`, `customer`, `vendor`, `invoice`, `bill`, `reconcile`, `serve`.
See the task specification for each command's arguments and output; `python3 -m fin COMMAND -h` shows usage.
User errors exit 2 with a message on stderr and nothing on stdout; they change nothing (each
data-changing command runs in one SQLite transaction).

## Layout

- `fin/core.py` — errors, money/date helpers, schema, accounts, posting, fx, audit, permissions, CLI framework.
- `fin/ledger.py` (accounts, transactions, balances, fx, users, audit, periods), `fin/imports.py` (rules, CSV import,
  budgets, recurring), `fin/invoicing.py` (tax, customers, vendors, invoices, bills, aging, tax report),
  `fin/reports.py` + `fin/loans.py` (reports, reconcile, loans), `fin/api.py` (HTTP).

## Assumptions

- Without `--json`, results are printed as indented JSON.
- Currencies are upper-cased on input. `init` with an invalid currency or empty admin name is a user error.
- Non-`init` commands on a missing database file are a user error (no file is created).
- A user error in a read command with an unknown `--user` is ignored; reads never need a user.
- `period close` of an already-closed month changes nothing and writes no audit entry.
- Amounts with more than two decimals are rounded half up to cents on input.
- Conversion: the direct FROM→TO rate (latest on or before the date) is preferred over the inverse; ties on one date go to the rate added last. Reports convert each account's per-currency balance (rounded per account) and total the rounded figures.
- Invoices and bills are assumed to be in the book's currency.
- A transaction on an account in another currency must balance within that currency; the blank posting takes the balancing amount in its account's currency.
- Import category accounts are in the book's currency; the import's ACCOUNT must already exist.
- Recurring occurrences are computed from the start date (n months / 7n days / n years), not iteratively.
- Invoice numbers count issued invoices per year; payment account for bills must exist (assumed an asset).
- The HTTP API binds to 127.0.0.1; `serve` itself needs no user, each POST needs `X-User`.
- See `.claude/team/handoff` notes (not shipped) for further small per-module decisions; the tests document behaviour.
