# fin — small-business finance system

Python 3.12+, standard library only. Run `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(`--db` defaults to `./fin.db`). Start with `python -m fin init --currency EUR --admin alice`, then use
`--user alice` for every command that changes data. Commands: `account`, `txn`, `balance`, `fx`, `convert`,
`rule`, `import`, `budget`, `recurring`, `report` (income, balance-sheet, networth, budget, aging, tax,
trial-balance, ledger), `loan schedule`, `tax`, `customer`, `vendor`, `invoice`, `bill`, `reconcile`,
`user`, `audit`, `period`, `serve --port N`. Output is always one JSON document; user errors exit 2.

Tests: `python3 -m unittest discover -s tests`.

Layout: `fin/core.py` (money, dates, schema, `Book`, posting/fx helpers), `fin/cli.py` (registry, permissions,
audit, `execute()` also used by the API), one module per feature area.

## Assumptions
- Output is JSON also without `--json` (pretty printed). Read commands accept an optional `--user`, which must exist if given.
- Write commands always append an audit entry (even `recurring run` creating 0). Failures change nothing (transaction rollback).
- Amounts with more than 2 decimals in postings are rounded half up. Elided posting takes the balancing amount of its account's currency.
- Rate lookup: FROM→TO rate if any on/before the date, else the inverse of TO→FROM.
- Reports convert each account's postings and round per account; with several currencies totals can differ by a cent.
- Tax codes match `[A-Za-z0-9_-]+`, rates non-negative; `invoice create` needs at least one line; payments must be positive and not exceed the balance; bill lines and payments are in the book currency, bill line amounts non-negative.
- Rules need an existing account; patterns use `re.search`, case-insensitive. Import rows: bad date/amount, zero amount or too few columns fail the whole file; blank rows skipped; fallback category currency must equal the bank account's.
- Budgets: expense accounts only, amount >= 0, converted at month end. Recurring occurrences are computed from the start by index (no day drift).
- Loan schedule: each repayment capped at the remaining balance; no upper limit on months.
- Reconcile marks only the given account's posting; `report tax` `by_code` includes codes with zero tax; `--from` after `--to` is an error there.
- API: query filters pass through on list endpoints; body errors (400) are checked before the user (401/403); `GET /invoices/abc` is 404; `;` in invoice line fields is a 400.
