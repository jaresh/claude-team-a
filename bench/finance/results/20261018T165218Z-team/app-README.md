# fin — a small-business finance system

Double-entry bookkeeping, bank import, budgets, recurring transactions, reports, loans,
invoices, bills, tax, reconciliation, users/roles/audit and an HTTP API.
Python 3.12+, standard library only (SQLite storage, `Decimal` money).

## Usage

```
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
```

Global options go before the command. `--db` defaults to `./fin.db`. `--json` prints exactly one
JSON document; without it a plain-text rendering is printed. Exit code 0 on success, 2 on a
user error (message on stderr, nothing on stdout, nothing changed).

```sh
python -m fin init --currency EUR --admin alice
python -m fin --user alice user add bob --role editor
python -m fin --user bob account add Assets:Bank
python -m fin --user bob account add Expenses:Rent
python -m fin --user bob txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin --json balance --at 2026-01-31
python -m fin --json report income --from 2026-01-01 --to 2026-01-31
python -m fin serve --port 8080      # HTTP API
```

Commands (see the spec sections in parentheses for the exact JSON shapes):

| Area | Commands |
|---|---|
| Books (1–4) | `init`, `account add/list`, `txn add/list`, `balance`, `fx add`, `convert` |
| Bank (5) | `rule add/list`, `import FILE --account A [--date-col --desc-col --amount-col --skip-header]` |
| Budgets (6) | `budget set ACCOUNT MONTH AMOUNT`, `report budget MONTH` |
| Recurring (7) | `recurring add NAME --every monthly\|weekly\|yearly --start D --posting ...`, `recurring run --until D` |
| Reports (8, 17) | `report income`, `report balance-sheet`, `report networth`, `report trial-balance`, `report ledger` |
| Loans (9) | `loan schedule PRINCIPAL RATE MONTHS --start D` |
| API (10) | `serve --port N` |
| Users (11) | `user add NAME --role admin\|editor\|viewer`, `user list`, `audit list [--by NAME]` |
| Periods (12) | `period close MONTH`, `period status` |
| Sales (13) | `tax add/list`, `customer add/list`, `invoice create/issue/pay/show/list`, `report aging` |
| Purchases (14) | `vendor add/list`, `bill create/pay/show/list`, `report aging --payables` |
| Tax (15) | `report tax --from --to` |
| Reconcile (16) | `reconcile ACCOUNT --date D --balance AMT [--clear ID ...]` |

## Layout

- `fin/core.py` — errors, money/date helpers, schema, users/audit, accounts, transactions, fx.
- `fin/cli.py` — command registry, global options, output and exit codes.
- `fin/books.py`, `fin/banking.py`, `fin/statements.py`, `fin/invoicing.py`, `fin/api.py`.
- `tests/` — `test_accept_*.py` acceptance tests per area plus unit tests per module.

Run the tests: `python -m unittest discover -s tests`.

## Assumptions

General
- Without `--json`, output is a simple text rendering (key: value lines, tab-separated tables).
- Argument parsing errors (missing/unknown options) are user errors: exit 2.
- Amounts given with more than two decimals are rounded half up to cents when stored.
- Currency codes are case-insensitive and stored upper-case. Any 3 letters are accepted.
- Account name segments may not be empty or have surrounding spaces.
- Read-only commands ignore `--user` (even an unknown name). `init` ignores `--user`; its audit
  user is the admin. `loan schedule` needs no database.
- Every successful data-changing command writes one audit entry even if it ends up changing
  nothing (e.g. `period close` of an earlier month, `recurring run` creating 0). Accounts or
  transactions created as a side effect (import, invoices, bills) are not audited separately.

Transactions, balances, fx
- The balancing posting (no amount) balances its own account's currency.
- `txn list --account X` matches X and `X:...` descendants (not mere string prefixes).
- `fx add` on the same date and pair replaces the rate. Conversions are rounded to cents; the
  inverse rate is used at full precision (1 / rate).

Import, rules, budgets, recurring, reconcile
- Rules: the account must exist; an invalid regex is a user error; matching uses `re.search`.
- Zero-amount import rows go to `Income:Uncategorized`; blank lines are skipped; a bad row
  (date/amount) fails the whole import. Descriptions are stripped.
- Budgets may only be set on expense accounts; `actual` is the raw sum in the month.
- Recurring names are unique; the run creates occurrences in date order per schedule.
- Reconcile matches postings on exactly ACCOUNT (not descendants); `--clear` ids are validated
  before anything is marked.

Reports
- Each account's sum is converted to the report currency separately, rounded, then totalled; in
  multi-currency books this can create a one-cent rounding gap between totals.
- `report networth` also accepts `--currency`. `report ledger` includes descendants.
- `report trial-balance` totals are equal for single-currency books (see rounding above).

Invoices and bills
- Invoice numbers use the invoice date's year; the counter advances only when issuing.
- Invoice payments must come from an asset account; bill payments from an asset or liability
  account. Payments must be > 0 and ≤ the balance.
- Payment terms are whole, non-negative days. Bill line accounts must be expense or asset.
- Aging and the tax report count non-draft invoices (issued/partial/paid) and all bills.
  `by_code` lists codes with a non-empty tax code used on those documents in the period.
- Line text may not contain `;` (it is the field separator for `--line`).

API
- `GET /invoices/ID` for an unknown id → 404. Malformed JSON bodies → 400.
- The server is single-threaded and opens a database connection per request.
- `payables=1` (or `true`) on `/reports/aging` selects bills. Unknown query parameters are ignored.
- POST checks run in order: path (404), then `X-User` and role (401/403), then body (400).
- An unknown method on a known path → 404.
