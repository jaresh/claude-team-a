# fin — small-business finance system

Double-entry bookkeeping with multi-currency accounts, bank import, budgets, recurring
transactions, reports, loans, invoices and bills, tax, reconciliation, users and an audit log,
plus a JSON HTTP API. Python 3.12+, standard library only (SQLite storage, `Decimal` money).

## Usage

```
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
```

Global options come before the command. `--db` defaults to `./fin.db`. With `--json` every
command prints exactly one JSON document; without it the same data is printed as plain text
(`key: value` lines, or a tab-separated table for lists). User errors exit with code 2, print
`error: ...` to stderr, print nothing to stdout and change nothing.

```sh
python -m fin init --currency EUR --admin alice
python -m fin --user alice account add Assets:Bank
python -m fin --user alice account add Expenses:Rent
python -m fin --user alice --json txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin --json balance --at 2026-01-31
python -m fin --json report income --from 2026-01-01 --to 2026-01-31
python -m fin serve --port 8080        # HTTP API, Ctrl-C to stop
```

### Commands

| Area | Commands |
|---|---|
| Book, users, audit | `init --currency CUR --admin NAME`, `user add NAME --role admin\|editor\|viewer`, `user list`, `audit list [--by NAME]` |
| Accounts | `account add NAME [--currency CUR]`, `account list` |
| Transactions | `txn add --date D --desc T --posting ACCOUNT[=AMOUNT] ...`, `txn list [--account P] [--from D] [--to D]`, `balance [--at D]` |
| Exchange rates | `fx add DATE FROM TO RATE`, `convert AMOUNT FROM TO --at D` |
| Bank import | `rule add PATTERN ACCOUNT`, `rule list`, `import FILE --account A [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]` |
| Budgets | `budget set ACCOUNT MONTH AMOUNT`, `report budget MONTH` |
| Recurring | `recurring add NAME --every monthly\|weekly\|yearly --start D --posting ...`, `recurring run --until D` |
| Reports | `report income --from D --to D [--currency C]`, `report balance-sheet --at D [--currency C]`, `report networth --from M --to M`, `report trial-balance --at D`, `report ledger ACCOUNT --from D --to D` |
| Loans | `loan schedule PRINCIPAL RATE MONTHS --start D` |
| Periods | `period close MONTH`, `period status` |
| Tax, customers, invoices | `tax add CODE RATE`, `tax list`, `customer add NAME [--terms DAYS]`, `customer list`, `invoice create --customer C --date D --line "DESC;QTY;PRICE;TAXCODE" ...`, `invoice issue ID`, `invoice pay ID AMOUNT --date D --account A`, `invoice show ID`, `invoice list [--status S]` |
| Vendors, bills | `vendor add NAME [--terms DAYS]`, `vendor list`, `bill create --vendor V --ref R --date D --line "DESC;AMOUNT;ACCOUNT;TAXCODE" ...`, `bill pay ID AMOUNT --date D --account A`, `bill show ID`, `bill list [--status S]` |
| Receivables/payables, tax | `report aging --at D [--payables]`, `report tax --from D --to D` |
| Reconciliation | `reconcile ACCOUNT --date D --balance AMOUNT [--clear TXN_ID ...]` |
| HTTP API | `serve --port N` |

Roles: `admin` can do everything, `editor` everything except `user add` and `period close`,
`viewer` only read-only commands. Every data-changing command needs `--user`; read-only
commands work with or without it.

### HTTP API

`GET /accounts`, `/transactions`, `/balances?at=D`, `/reports/income?from=D&to=D`,
`/reports/balance-sheet?at=D`, `/invoices`, `/invoices/ID`, `/reports/aging?at=D[&payables=1]`,
`/audit`; `POST /transactions`, `/invoices`, `/invoices/ID/issue`, `/invoices/ID/payments`.
POSTs need `X-User: NAME` (401 if missing/unknown, 403 if the role may not). User errors are
400 `{"error": "..."}`; unknown paths and unknown invoice ids are 404.

## Layout

- `fin/core.py` — errors, money/date helpers, schema, accounts, posting, fx, roles, audit.
- `fin/cli.py` — command registry, argument parsing, one DB transaction per command, output.
- `fin/ledger.py` (§1–4, 11, 12), `fin/banking.py` (§5–7, 16), `fin/statements.py` (§8, 9, 17),
  `fin/invoicing.py` (§13–15), `fin/api.py` (§10).
- `tests/` — `test_acc_*.py` acceptance tests per section, `test_<module>.py` unit tests.
  Run: `python -m unittest discover -s tests`.

## Assumptions

- Amounts are stored as integer cents. Input amounts with more than two decimals are rounded
  half up to cents (e.g. `12.505` → `12.51`). Zero-amount postings are allowed.
- Every command runs in one SQLite transaction; any error rolls everything back.
- `init` fails if the database file already exists and is non-empty. Any other command on a
  missing database is a user error (the file is not created).
- Currency codes are 3 letters, upper-cased on input. Account names are colon paths with
  non-empty segments; the currency of an existing parent is not changed by adding a child.
- A posting `ACCOUNT=AMOUNT` splits on the last `=`. In a multi-currency transaction the blank
  posting balances its own account's currency; every currency must still sum to zero.
- `fx add` for the same date and pair replaces the earlier rate; rates must be positive.
  `convert` rounds the result half up to cents.
- Reports with conversion convert each account's sum at the report date, round it, and sum the
  rounded values, so with foreign currencies the balance-sheet identity can be off by a cent.
  `report networth` and `report trial-balance` are in the book's currency. `report ledger`
  sums raw postings in the account's currency (no conversion).
- `--from` after `--to` is a user error in reports.
- `period close` on a month earlier than the closed one still succeeds and writes an audit
  entry, but doesn't change the closed month.
- Import: CSV via Python's `csv` module; every row is validated before anything is posted;
  the duplicate key is (account, date, description, amount). Import, recurring run, budget
  set etc. write one audit entry each even if they create nothing.
- `recurring add` checks the postings like `txn add` but not the closed period (that is checked
  when `recurring run` posts). Recurring names are unique.
- `reconcile --clear` requires a posting to exactly ACCOUNT (not a sub-account). Re-clearing a
  cleared transaction is allowed.
- Budgets can only be set on expense accounts; `actual` is the raw sum (debits positive).
- Invoices: line fields are split on `;` (descriptions can't contain `;`); quantity and price
  may be any decimal; `price` is shown with two decimals, `quantity` as given. Invoice numbers
  count issued invoices per invoice-date year. Payments must be positive, into an existing asset
  account. Status after issue: `issued`, then `partial`/`paid`. Bills start `open`.
- `report aging` includes invoices with status issued/partial/paid that still have a balance
  as of the date (payments after the date are ignored). `report tax` counts every non-draft
  invoice and every bill dated in the period; lines without a tax code are not in `by_code`.
- Loans: PRINCIPAL > 0, RATE ≥ 0, MONTHS ≥ 1; Decimal arithmetic with 28 digits before rounding.
- Without `--json`, output is a simple plain-text rendering of the same document.
- `serve` listens on 127.0.0.1; `--port` defaults to 8000. Unexpected server errors return 500
  `{"error": "internal error"}`.
