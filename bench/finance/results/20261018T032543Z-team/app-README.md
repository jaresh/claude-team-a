# fin — small-business finance system

Python 3.12+, standard library only. Run `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(global options first; `--db` defaults to `./fin.db`). Output is always one JSON document on stdout
(`--json` is accepted; output is pretty-printed JSON either way). User errors exit 2 with a message on stderr.

```
python -m fin --db b.db init --currency EUR --admin alice
python -m fin --db b.db --user alice account add Assets:Bank
python -m fin --db b.db --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin --db b.db report income --from 2026-01-01 --to 2026-01-31
python -m fin --db b.db serve --port 8000     # JSON API, POSTs need header X-User
```

Commands: init, user, account, txn, balance, fx, convert, rule, import, budget, recurring, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loan schedule, tax, customer,
invoice, vendor, bill, reconcile, period, audit, serve. See the specification sections for each.

Layout: `fin/core.py` (money, dates, storage, posting, conversion), `fin/cli.py` (dispatch, one transaction per
command, rollback on error), one module per command group, `tests/` (run `python3 -m unittest discover -s tests`).

## Assumptions
General
- Output is JSON even without `--json`. Roles are checked before any change; writers need `--user`.
- `reconcile` is a write command (viewers refused, audited on every run). `loan schedule` is read-only.
- Principal/amounts with more than 2 decimals in transactions are rounded half up to cents; invoice prices and payment amounts with more than 2 decimals are rejected.
- Multi-currency books: reports convert per account then round, so totals may differ by 0.01 from perfect balance.
- Reports (trial-balance, ledger) use the book currency; ledger rows convert to the account's currency at period end.
- Income statement lists every income/expense account with postings in the period, including zero totals.
- `networth` months are inclusive, valued at month end.

Import / budget / recurring
- `import` is audited even if all rows are skipped. Zero-amount rows go to `Income:Uncategorized`.
- `rule add` requires the rule's account to exist. `budget set` accepts only expense accounts and non-negative amounts.
- `recurring add` ignores closed periods (only `recurring run` is checked); past start dates are allowed.

Invoices / bills / tax
- Tax per line = net × rate / 100 rounded half up; lines without tax code have no tax. Customer/vendor terms default 30 and must be ≥ 0.
- Invoice numbers are assigned at issue, sequential per invoice-date year. Payment accounts must exist (asset accounts) in the book currency; amounts must be positive and ≤ balance.
- Bill lines need existing expense or asset accounts, non-negative amounts; `--ref` unique per vendor. Bill statuses: open, partial, paid.
- Aging amounts are in the book currency. `report tax` with from > to gives zeros; `by_code` lists every code on a tax-coded line in the period (bills counted by bill date).
- Reconcile: `--clear` needs a posting to exactly ACCOUNT (not children); re-clearing is a no-op.
- Loans: principal must be > 0, rate ≥ 0, months ≥ 1.

HTTP API
- `serve --port` defaults to 8000, binds 127.0.0.1, logs nothing. Missing params/fields → 400; wrong method on a known path → 404; unknown invoice id → 400; unexpected errors → 500.
- Extra filters: `/transactions` (account, from, to), `/audit?by=`, `/invoices?status=`, `?currency=` on income/balance-sheet. Bill endpoints are not exposed.
