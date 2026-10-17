# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(`--db` defaults to `./fin.db`). Start with `init --currency EUR --admin alice`, then e.g.
`--user alice account add Assets:Bank`, `txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank`,
`balance`, `report income --from 2026-01-01 --to 2026-01-31`, `serve --port 8080` (HTTP API; POST needs `X-User`).
All commands of the specification are implemented (accounts, transactions, balances, FX, CSV import and rules,
budgets, recurring, reports, loans, API, users/roles/audit, closed periods, tax, invoices, bills, reconciliation,
trial balance, ledger). User errors exit 2 with a message on stderr and change nothing (one SQL transaction per command).

Layout: `fin/core.py` shared helpers, `fin/cli.py` dispatch/permissions, and one module per area
(`books`, `ledger`, `banking`, `invoicing`, `reports`, `api`). Tests: `python3 -m unittest discover -s tests`.

## Assumptions
- Without `--json`, output is the same JSON, indented.
- `fx add` rejects FROM == TO and non-positive rates; `convert` requires `--at`.
- `account add` of an existing name (including an existing parent) is an error.
- `txn list --account` matches the exact name or descendants (not plain string prefixes).
- Data-changing commands need `--user`; read commands work without. Missing/unknown user and insufficient role are user errors (API: 401/403).
- `init` on an existing database is an error; a failed `init` leaves no database file.
- Amounts are rounded half up to cents when stored.
- Further module-level decisions (budgets only on existing expense accounts, import dedupe, etc.) are covered by the tests in `tests/`.
