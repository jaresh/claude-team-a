# fin — a small-business finance system

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API, `unittest` tests.

```
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
python -m unittest discover -s tests
```

Global options go before the command. `--db` defaults to `./fin.db`. With `--json` a command prints exactly
one JSON document; without it, a plain-text rendering of the same data. A user error (bad input, unbalanced
transaction, unknown account, missing rate, missing permission, closed period, ...) exits with 2, prints
`error: ...` to stderr, prints nothing to stdout and changes nothing (every command runs in one database
transaction that is rolled back on error).

## Quick start

```
python -m fin init --currency EUR --admin alice
python -m fin --user alice account add Assets:Bank
python -m fin --user alice account add Expenses:Rent
python -m fin --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin --json balance
python -m fin --user alice customer add Acme --terms 30
python -m fin --user alice tax add VAT20 20
python -m fin --user alice invoice create --customer Acme --date 2026-01-10 --line "Consulting;10;95.00;VAT20"
python -m fin --user alice invoice issue 1
python -m fin --user alice invoice pay 1 500 --date 2026-01-20 --account Assets:Bank
python -m fin report aging --at 2026-03-01
python -m fin --user alice serve --port 8080      # JSON API; POSTs need the X-User header
```

## Commands

| Area | Commands |
| --- | --- |
| Books | `init`, `account add/list`, `txn add/list`, `balance` |
| Rates | `fx add DATE FROM TO RATE`, `convert AMOUNT FROM TO --at DATE` |
| Banking | `rule add/list`, `import FILE --account A [--date-col --desc-col --amount-col --skip-header]`, `reconcile ACCOUNT --date D --balance B [--clear ID ...]` |
| Planning | `budget set`, `recurring add/run`, `loan schedule` |
| Reports | `report income/balance-sheet/networth/budget/aging/tax/trial-balance/ledger` |
| Access | `user add/list`, `audit list [--by]`, `period close/status` |
| Billing | `tax add/list`, `customer add/list`, `invoice create/issue/pay/show/list`, `vendor add/list`, `bill create/pay/show/list` |
| API | `serve --port N` |

Roles: `admin` can do everything, `editor` everything except `user add` and `period close`, `viewer` only
read-only commands. Commands that change data need `--user`; read-only commands work with or without it.

HTTP API (`serve`): `GET /accounts /transactions /balances?at= /reports/income?from=&to=
/reports/balance-sheet?at= /reports/aging?at=[&payables=1] /invoices /invoices/ID /audit`;
`POST /transactions /invoices /invoices/ID/issue /invoices/ID/payments` (header `X-User` required:
401 missing/unknown user, 403 role not allowed, 400 user error with `{"error": ...}`, 404 unknown path).

## Layout

`fin/ledger.py` accounts, transactions, balances, FX, closed periods · `fin/banking.py` rules, import,
reconciliation · `fin/planning.py` budgets, recurring, loans · `fin/reports.py` statements ·
`fin/billing.py` tax, customers, vendors, invoices, bills, aging · `fin/access.py` users, roles, audit ·
`fin/cli.py` command table and parser · `fin/api.py` HTTP server · `fin/db.py` schema and sessions.

## Assumptions

- Amounts are rounded half up to cents on input (e.g. `0.005` → `0.01`); quantities and rates keep full precision.
- Currency codes are case-insensitive and stored upper-case. Dates and months are validated strictly (`YYYY-MM-DD`, `YYYY-MM`).
- `init` prints `{"currency", "admin"}`; other write commands print the created/updated object (account, user, rule, tax code, ...). `period close` prints the period status.
- A blank-amount posting balances only its own currency; every currency must still sum to zero.
- `txn list --account PREFIX` matches the account itself and descendants (whole path segments only).
- `rule add` requires the target account to exist and the pattern to compile; patterns use `re.search`, ignoring case. Uncategorised imports use `Expenses:Uncategorized` for negative amounts and `Income:Uncategorized` otherwise (including zero). Import rows with identical (account, date, description, amount) to an earlier import are skipped; blank CSV lines are ignored; any malformed row fails the whole import.
- `fx add` for the same pair and date twice: the later one wins. `convert`/reports prefer a direct rate over an inverse one, even an older direct one. Zero amounts need no rate in reports.
- Reports convert each account's total (not each posting) and round per account; with several currencies the totals are sums of the rounded account figures, so the accounting identity can differ by a cent. Account names are not rolled up in reports. `networth` also accepts `--currency`.
- `budget set` only accepts expense accounts; `report budget` sums the account's own currency without conversion.
- Recurring occurrences are anchored on the start date (not chained); the same recurring name may be added twice; creation order is by date then definition order.
- `period close` of an already-closed month is a successful no-op and writes no audit entry. Unknown `--user` on a read-only command is ignored. `reconcile` always needs a user and writes an audit entry (it records cleared marks); reconcile only looks at postings to the exact account, not descendants.
- Invoices: quantity must be positive and price non-negative; a draft needs at least one line; `;` inside a description is allowed (the last three `;` fields are quantity, price, tax code). Invoice numbers count per year of the invoice date in order of issue. Payments need an asset account; bills may be paid from an asset or liability account. Bill lines go to expense or asset accounts, with the line `AMOUNT` as net; negative amounts are allowed on bills.
- `report aging` counts issued invoices (and all bills) dated on or before the date, with payments dated on or before it; the `paid` field of an invoice shows all payments regardless of date.
- `report tax`: `collected` covers issued invoices (drafts excluded), `paid` all bills; lines without a tax code are not in `by_code`.
- `report ledger` sums postings to the account and descendants in the account's currency only.
- API: an unknown invoice id is 404 for `GET` and 400 for `POST`; request numbers in JSON bodies are accepted (read as their literal text); the server binds to 127.0.0.1 and logs nothing. `loan schedule` needs no database.
- Audit timestamps are UTC, second precision (`2026-01-05T09:30:00Z`).
