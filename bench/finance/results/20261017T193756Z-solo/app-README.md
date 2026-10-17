# fin — small-business finance system

Python 3.12+, standard library only. Storage is SQLite, money is `Decimal`, the API is `http.server`.

```
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
python -m unittest discover -s tests
```

Global options go before the command; `--db` defaults to `./fin.db`. Start with
`python -m fin init --currency EUR --admin alice`, then e.g.

```
python -m fin --user alice account add Assets:Bank
python -m fin --user alice account add Expenses:Rent
python -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin balance
python -m fin report income --from 2026-01-01 --to 2026-01-31
python -m fin --user alice serve --port 8080      # HTTP API; POSTs need header X-User
```

Commands: `init account txn balance fx convert rule import budget recurring report
(income balance-sheet networth budget aging tax trial-balance ledger) loan user audit period tax
customer vendor invoice bill reconcile serve`. Exit code 0 = success, 2 = user error (message on
stderr, nothing on stdout, nothing changed — every command runs in one SQLite transaction).

Layout: `fin/core.py` (all logic, `Book.execute`), `fin/cli.py` (argparse), `fin/server.py` (HTTP),
`tests/`.

## Assumptions

- Without `--json`, commands print the same documents, indented. Commands whose output is not
  specified print a small object (e.g. `account add` → `{"name","type","currency"}`, `user add`,
  `fx add`, `rule add`, `budget set`, `tax add`, `period close`, `recurring add`).
- Currency codes are 3 letters, upper-cased. Posting amounts are rounded half up (away from zero)
  to cents when entered. Rates and tax rates must be non-negative decimals (FX rates positive).
- `convert`/reports: if any FROM→TO rate exists on or before the date, the latest one is used;
  only otherwise the inverse of the latest TO→FROM rate. Report totals are sums of the displayed
  (rounded) account values; each account/currency subtotal is converted and rounded separately.
- `loan schedule` needs no database. `serve` needs an initialised database.
- `rule add` requires the target account to exist. Rules/imports: a zero amount counts as income.
  Import duplicates are tracked per ACCOUNT in a separate table (so they stay skipped even if the
  transaction is later changed). Closed-period check covers every row, including duplicates.
- Duplicate tax codes, customers, vendors are user errors. Quantity must be > 0.
  Invoice/bill payment accounts must be existing asset accounts.
- Invoice numbers count issued invoices per year. "Issued" invoices in aging/tax reports means
  every non-draft invoice (issued, partial, paid).
- `period close` of an already-closed month changes nothing and writes no audit entry. A
  `recurring run` or `import` that creates nothing still writes its audit entry.
- Reconcile marks only postings to exactly ACCOUNT (not descendants); `reconcile` always audits.
- HTTP: 401/403 are checked before the body is validated; unknown invoice id → 404; other user
  errors → 400. `GET /invoices?status=`, `/transactions?account=&from=&to=`, `/audit?by=` are
  supported as filters, `--currency`-style `currency=` on the income/balance-sheet reports.
- A `viewer` may run every read-only command; `serve` is not a data change and needs no user.
