# fin — small-business finance system

Python 3.12+, standard library only. Run as `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(the sandbox only had `python3`; `python -m fin` is the same). Tests: `python3 -m unittest discover -s tests`.

    python3 -m fin init --currency EUR --admin alice
    python3 -m fin --user alice account add Assets:Bank
    python3 -m fin --user alice account add Expenses:Rent
    python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin balance
    python3 -m fin --user alice serve --port 8080

Commands cover accounts, transactions, balances, fx/convert, rules/import, budgets, recurring, reports
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loans, users/audit/periods,
tax codes, customers/invoices, vendors/bills, reconcile and the HTTP API (see the spec sections 1-17).
Layout: `fin/core.py` (money, dates, schema, shared posting logic), `fin/cli.py` (parsing, permissions,
one transaction per command), one module per area (`ledger`, `automation`, `billing`, `reports`, `api`).
The API translates each request into the CLI command, so both behave the same.

## Assumptions
- Output is always JSON (pretty-printed), with or without `--json`. A missing database is a user error.
- Write commands need `--user`; reads work without. `serve` needs no user; POSTs need `X-User`
  (viewer → 403). The server binds 127.0.0.1; request amounts must be JSON strings; unknown ids on GET
  return 400 (404 only for unknown paths). Invoice line descriptions cannot contain `;`.
- Amounts are rounded half up to cents on input. Commands that change nothing (closing an earlier month,
  import with zero new rows, reconcile marking nothing new) write no audit entry.
- Output of commands whose shape the spec leaves open: `account add` → `{name,type,currency}`,
  `fx add` → `{date,from,to,rate}`, `user add` → `{name,role}`, `period close` → `{closed_through}`.
- `fx add` rejects rates <= 0 and same-currency pairs. `convert` requires `--at`.
- Balance includes ancestors; accounts summing to zero show `0.00`. `txn list --account` matches the account
  or colon-segment descendants.
- Rules: target accounts must exist; first matching rule wins. Import is all-or-nothing; foreign-currency
  import accounts fail as unbalanced. Budgets: expense accounts, amount >= 0; `actual` includes descendants.
- Recurring: occurrences computed from the start date (so Jan 31 → Feb 28 → Mar 31); `recurring add`
  validates postings like `txn add`.
- Invoices: number assigned on issue (count of existing numbers with that year + 1); quantity > 0, price >= 0;
  tax per line; payments must be positive and <= balance; only issued/partial invoices can be paid.
  Bill lines may use any existing non-income account; bill status `open`/`partial`/`paid`.
- Reports: grouped by posting account name; `--from` after `--to` is an error; trial balance has no
  `--currency` and uses the book currency (multi-currency books may differ by a cent between totals).
  `report tax` counts non-draft invoices and all bills in the period. `reconcile` matches the exact account.
  `report networth` = assets − liabilities at month end.
