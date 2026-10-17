# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(global options before the command; `--db` defaults to `./fin.db`). Tests: `python3 -m unittest discover -s tests`.

## Usage
```
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice account add Expenses:Rent
python3 -m fin --user alice --json txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json balance
python3 -m fin --user alice serve --port 8080      # HTTP API; POSTs need header X-User
```
Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, loan, user, audit,
period, tax, customer, invoice, vendor, bill, reconcile, serve, and `report` (income, balance-sheet,
networth, budget, aging, tax, trial-balance, ledger). Without `--json` output is indented JSON.
Errors: exit 2, message on stderr, nothing on stdout, nothing changed (each command runs in one DB transaction).

## Layout
`fin/core.py` shared money/date helpers, `Book` (posting, FX, audit); `fin/cli.py` parsing, roles, dispatch;
one module per area (ledger, admin, banking, schedule, reports, invoicing, billing, tax_aging, api).
The API calls the CLI in-process, so documents match `--json` output exactly.

## Assumptions
- Roles: commands are `read`, `write` or `admin`; read commands need no user, but an unknown `--user` given to any command is an error.
- Amounts with more than two decimals in postings are rounded half up to cents when stored.
- Exchange rate ties on the same date: the latest added wins; a direct FROM→TO rate beats an inverse one.
- Reports convert each account's postings per currency at the report date and round once per account, so with `--currency` totals may differ by a cent from the sum of parts.
- `report ledger` converts nothing across accounts; its currency is the account's.
- Import: all-or-nothing; zero amounts go to `Income:Uncategorized`; a duplicate row in a closed month is skipped; rule accounts must exist.
- `budget set` needs an existing expense account and a non-negative amount. `reconcile` matches the exact account name.
- Invoice create is allowed in closed periods (only issue and pay post). Payments must be positive and in the account's currency matching Receivable/Payable.
- Bill pay account must be an existing asset account; invoice pay likewise.
- Aging counts only payments dated on/before the report date. Tax report `by_code` lists every code on invoices or bills in the period.
- `period close` is audited even if it changes nothing. `user add` prints `{"name","role"}`; `period close` prints `{"closed_through": ...}`.
- Teammate handoffs hold further minor decisions (`.claude/team/handoff/`, git-ignored).
