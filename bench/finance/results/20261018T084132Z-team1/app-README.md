# fin: small-business finance

A double-entry book for one small business, kept in a single SQLite file. It uses only the Python
standard library and needs Python 3.14 or later (`python3`).

## Running it

Every command goes through one entry point:

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...

- `--db PATH` is the book file. It defaults to `./fin.db` and is created on first use.
- `--json` prints compact JSON. Without it, output is pretty JSON (indent 2).
- `--user NAME` names the acting user. Commands that change the book need it; read-only commands do not.
- Errors go to stderr as `error: MESSAGE`. The exit code is 0 on success, 2 for a user error or a bad
  command line.

## Commands

Amounts are decimal strings such as `12.50`. Dates are `YYYY-MM-DD`. Months are `YYYY-MM`. Account
names are colon-separated and start with `Assets`, `Liabilities`, `Equity`, `Income` or `Expenses`.

### Book and users

    python3 -m fin --db book.db init --currency EUR --admin alice
    python3 -m fin --db book.db --user alice user add bob --role editor     # admin, editor or viewer
    python3 -m fin --db book.db user list
    python3 -m fin --db book.db audit list [--by NAME]
    python3 -m fin --db book.db --user alice period close 2026-01         # admin only
    python3 -m fin --db book.db period status

### Accounts, transactions, currencies

    python3 -m fin --db book.db --user bob account add Expenses:Rent [--currency USD]
    python3 -m fin --db book.db account list
    python3 -m fin --db book.db --user bob txn add --date 2026-01-05 --desc "Rent" \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --db book.db txn list [--account NAME] [--from DATE] [--to DATE]
    python3 -m fin --db book.db balance [--at DATE]
    python3 -m fin --db book.db --user bob fx add 2026-01-01 USD EUR 0.92
    python3 -m fin --db book.db convert 100 USD EUR --at 2026-01-31

`--posting ACCOUNT=AMOUNT` gives a signed amount. `--posting ACCOUNT` alone takes whatever balances
the transaction; at most one posting may do that.

### Reports

    python3 -m fin --db book.db report income --from 2026-01-01 --to 2026-03-31 [--currency EUR]
    python3 -m fin --db book.db report balance-sheet --at 2026-03-31 [--currency EUR]
    python3 -m fin --db book.db report networth --from 2026-01-01 --to 2026-03-31 [--currency EUR]
    python3 -m fin --db book.db report trial-balance --at 2026-03-31 [--currency EUR]
    python3 -m fin --db book.db report ledger Expenses:Rent --from 2026-01-01 --to 2026-03-31
    python3 -m fin --db book.db loan schedule 10000 0.06 12 --start 2026-01-01

### Bank statement import, rules, budgets, recurring entries

    python3 -m fin --db book.db --user bob rule add "(?i)rent" Expenses:Rent
    python3 -m fin --db book.db rule list
    python3 -m fin --db book.db --user bob import statement.csv --account Assets:Bank \
        [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]
    python3 -m fin --db book.db --user bob budget set Expenses:Rent 2026-01 1000
    python3 -m fin --db book.db report budget 2026-01
    python3 -m fin --db book.db --user bob recurring add rent --every monthly --start 2026-01-01 \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --db book.db --user bob recurring run --until 2026-12-31

Column numbers start at 0. The defaults are date 0, description 1 and amount 2.

### Reconciliation

    python3 -m fin --db book.db --user bob reconcile Assets:Bank --date 2026-01-31 --balance 4100.00 \
        [--clear TXN_ID ...]

### Invoices, bills, tax, aging

    python3 -m fin --db book.db --user alice tax add VAT20 20
    python3 -m fin --db book.db --user alice customer add Acme [--terms 30]
    python3 -m fin --db book.db --user alice vendor add Supplies [--terms 14]
    python3 -m fin --db book.db --user bob invoice create --customer Acme --date 2026-01-10 \
        --line "Consulting;10;95.00;VAT20"
    python3 -m fin --db book.db --user bob invoice issue 1
    python3 -m fin --db book.db --user bob invoice pay 1 100.00 --date 2026-01-20 --account Assets:Bank
    python3 -m fin --db book.db invoice show 1
    python3 -m fin --db book.db invoice list [--status draft|issued|partial|paid]
    python3 -m fin --db book.db --user bob bill create --vendor Supplies --ref INV-7 --date 2026-01-12 \
        --line "Paper;5;12.00;VAT20"
    python3 -m fin --db book.db --user bob bill pay 1 60.00 --date 2026-01-30 --account Assets:Bank
    python3 -m fin --db book.db bill show 1
    python3 -m fin --db book.db bill list [--status open|partial|paid]
    python3 -m fin --db book.db report aging --at 2026-02-28 [--payables]
    python3 -m fin --db book.db report tax --from 2026-01-01 --to 2026-03-31

An invoice or bill line is `DESCRIPTION;QUANTITY;PRICE;TAXCODE`. The tax code may be left empty.

### Serving the HTTP API

    python3 -m fin --db book.db serve [--port 8000]

This prints `serving on http://127.0.0.1:PORT` to stderr and runs until interrupted (Ctrl+C).
Each request runs the same command as the CLI, with the same permissions, closed-period checks and
audit entries. The routes are:

| Method | Path | Notes |
|---|---|---|
| GET | `/accounts` | `account list` |
| GET | `/transactions?account=&from=&to=` | `txn list` |
| GET | `/balances?at=` | `balance` |
| GET | `/reports/income?from=&to=&currency=` | `report income` |
| GET | `/reports/balance-sheet?at=&currency=` | `report balance-sheet` |
| GET | `/reports/aging?at=&payables=1` | `report aging` |
| GET | `/invoices?status=` | `invoice list` |
| GET | `/invoices/ID` | `invoice show` |
| GET | `/audit?by=` | `audit list` |
| POST | `/transactions` | body `{"date", "description", "postings": [{"account", "amount"?}]}` |
| POST | `/invoices` | body `{"customer", "date", "lines": [{"description", "quantity", "price", "tax_code"?}]}` |
| POST | `/invoices/ID/issue` | `invoice issue` |
| POST | `/invoices/ID/payments` | body `{"amount", "date", "account"}` |

GET needs no user. POST needs an `X-User: NAME` header:

    curl -s -H 'X-User: bob' -H 'Content-Type: application/json' \
        -d '{"date":"2026-01-05","description":"Rent","postings":[{"account":"Expenses:Rent","amount":"900"},{"account":"Assets:Bank"}]}' \
        http://127.0.0.1:8000/transactions

Responses are the same JSON documents the CLI prints with `--json`. Errors are `{"error": MESSAGE}`.

## Running the tests

    python3 -m unittest discover -s tests

The tests use temporary books. They do not touch `./fin.db`. One test starts `serve` as a subprocess on
a free port, so the run needs a local TCP port but no network access.

## Assumptions

These come from the code, not from a separate spec.

- **Output.** Commands print one JSON document. It is pretty-printed unless `--json` is given. Errors go to
  stderr and exit with status 2.
- **Atomicity.** Each command runs in one SQLite transaction (`BEGIN IMMEDIATE`). If it fails, nothing it
  wrote is kept. The same applies to each `import` and `recurring run`.
- **Initialisation.** `init` works only on a new book. It sets the book currency and creates the first
  admin. Every other command refuses to run until the book is initialised.
- **Users.** User names are case-sensitive. Roles are admin, editor and viewer. Viewers cannot write.
  `user add` and `period close` need an admin. Read commands need no user. Write commands need `--user`
  on the CLI or `X-User` in the API. An unknown name is a 401 and a wrong role is a 403.
- **Accounts.** The first segment of a name must be one of the five types. Parent accounts are created
  automatically in the same currency. Accounts default to the book currency unless `--currency` is given.
  `account list` is sorted by name.
- **Money.** Amounts are decimal, never float. They are rounded half up to cents, stored as text, and shown
  with two decimals, never `-0.00`.
- **Balancing.** A transaction must balance in each currency. At most one posting may omit its amount, and
  that posting takes the balancing figure. A transaction needs at least two postings.
- **Closed periods.** A month is closed through a date set by `period close`. Any transaction, invoice,
  bill, payment or recurring occurrence dated in a closed month is refused. Imports and recurring runs are
  all-or-nothing, so one closed row stops the whole run.
- **Imports.** A row is skipped as a duplicate when the same account, date, description and amount were
  already imported. Rows with no matching rule go to `Income:Uncategorized` if positive and to
  `Expenses:Uncategorized` if not. Rules are regular expressions, matched case-insensitively, and the first
  rule that matches wins. Rule patterns must not be empty.
- **Budgets.** Budgets can be set only on expense accounts. Setting a budget again for the same account and
  month replaces it. Budget amounts cannot be negative.
- **Recurring entries.** Occurrence `k` of a schedule is posted at most once, however often `recurring run`
  is repeated. A monthly entry on the 31st moves to the last day of shorter months. Runs stop at `--until`.
- **Invoices and bills.** Quantity must be positive and price must not be negative. Tax is charged on the net
  amount at the tax code's rate, and no code means no tax. Terms default to 30 days. An invoice must be a
  draft to be issued. A payment must be positive and no larger than the balance. Payments go to an asset
  account in the book currency. Status becomes `paid` when the balance reaches zero. A bill ref is unique
  per vendor. Bill lines need an expense or asset account in the book currency.
- **Aging.** Payments dated on or before `--at` are counted. Days past due go into the buckets `current`
  (zero or less), `1-30`, `31-60`, `61-90` and `90+`.
- **Exchange rates.** A rate must be positive, and the two currencies must differ. A conversion uses the latest
  rate on or before the date. If only the reverse pair is stored, its inverse is used.
- **Reports.** Each account's balance is summed per currency, converted at the report date, and then rounded.
  Totals add up those rounded figures.
- **Loans.** `loan schedule` needs a positive principal and a positive whole number of months. The rate may
  be zero but not negative.
- **HTTP API.** It binds to `127.0.0.1` only and has no password. The `X-User` name is trusted, so anyone who can
  reach the port can act as any user. Only the routes in the table above exist. Bills, imports, budgets,
  reconciliation, ledger and loan schedule are CLI-only. An unknown path or method returns 404. A body that is
  not a JSON object returns 400. An unexpected server error returns 500 with `{"error": "internal error"}`.
- **Concurrency.** SQLite allows one writer at a time. While `serve` runs, it does not hold the write lock, so
  CLI commands can run against the same book.
