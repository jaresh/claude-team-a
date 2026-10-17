# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(global options first; `--db` defaults to `./fin.db`). Test: `python3 -m unittest discover -s tests`.

```
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice account add Expenses:Rent
python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json balance
python3 -m fin serve --port 8080      # HTTP API; POSTs need header X-User
```

Layout: `fin/core.py` (money, dates, schema, posting, fx), `fin/cli.py` (parsing, roles, audit, users,
periods), `fin/ledger.py` (accounts, txns, balances, fx), `fin/banking.py` (rules, import, budgets,
recurring, reconcile), `fin/reports.py` (income, balance sheet, net worth, trial balance, ledger, loans),
`fin/billing.py` (tax, customers/vendors, invoices, bills, aging, tax report), `fin/api.py` (HTTP; calls
the same command code as the CLI). Commands run in one SQLite transaction: any error rolls back everything.

## Assumptions
- Without `--json`, output is the same JSON, pretty-printed. `init` prints `{"currency","admin"}`; other
  write commands without a specified output print the created/changed object.
- Amounts are rounded half up to cents when parsed. Exchange rate lookups use the latest rate on or before the date, direct preferred over inverse; same-day ties go to the later entry.
- `fx add` rejects FROM == TO; account names may not contain `=` or empty segments.
- Reports convert each account's balance separately, then round. Ledger report ignores postings in other currencies than the account's.
- `period close` of an earlier month than the closed one changes nothing (still audited).
- Invoices/bills: `recurring`, `import`, and all postings go through one posting routine that enforces balance, known accounts and closed periods.
- Teammate-specific notes are in the module docstrings and tests (`tests/`).
