# fin

A small double-entry personal finance tool. Pure standard library Python 3, one SQLite file per book.

Run it from the project folder with `python3 -m fin`. Global options go before the command:

```
python3 -m fin [--db PATH] [--json] COMMAND ...
```

- `--db PATH` is the book file (default `./fin.db`).
- `--json` prints compact JSON on one line. Without it the output is pretty JSON.

Errors go to stderr as `error: ...` and the exit code is 2. Nothing is printed to stdout on error.

## Quick start

```
python3 -m fin --db home.db init --currency EUR
python3 -m fin --db home.db account add Assets:Bank
python3 -m fin --db home.db account add Expenses:Rent
python3 -m fin --db home.db account add Income:Salary
python3 -m fin --db home.db txn add --date 2026-01-01 --desc "January pay" \
    --posting Assets:Bank=3000 --posting Income:Salary
python3 -m fin --db home.db txn add --date 2026-01-05 --desc "Rent" \
    --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --db home.db balance
```

## Commands

### init

Creates a new book with its base currency. Fails if the file already exists.

```
python3 -m fin --db home.db init --currency EUR
```

### account

Accounts are named with colons and start with one of `Assets`, `Liabilities`, `Equity`, `Income` or `Expenses`. Parent accounts are created automatically. An account may have its own currency; it defaults to the book currency.

```
python3 -m fin --db home.db account add Assets:Cash:Wallet --currency USD
python3 -m fin --db home.db account list
```

### txn

A transaction has a date, a description and at least two postings. Each posting is `ACCOUNT=AMOUNT`. At most one posting may leave out the amount (`ACCOUNT` alone); it gets the amount that balances the transaction. Postings must balance per currency.

```
python3 -m fin --db home.db txn add --date 2026-02-01 --desc "Groceries" \
    --posting Expenses:Food=84.50 --posting Assets:Bank
python3 -m fin --db home.db txn list
python3 -m fin --db home.db txn list --account Expenses --from 2026-01-01 --to 2026-01-31
```

`txn list` filters: `--account` matches the account and its sub-accounts, `--from` and `--to` are inclusive dates.

### balance

Balances per account, including parent accounts, grouped by currency. Without `--at` it uses all transactions.

```
python3 -m fin --db home.db balance
python3 -m fin --db home.db balance --at 2026-01-31
```

### fx and convert

Exchange rates are stored per day. `convert` uses the latest rate on or before `--at`, in either direction. A rate must be positive.

```
python3 -m fin --db home.db fx add 2026-01-01 EUR USD 1.25
python3 -m fin --db home.db convert 10 EUR USD --at 2026-02-01
```

### import

Imports a CSV file of bank lines into an account. Each row becomes a transaction between that account and a category account. Columns are zero-based (`--date-col`, `--desc-col`, `--amount-col`, defaults 0, 1, 2). Use `--skip-header` when the first line is a header.

```
python3 -m fin --db home.db import bank-jan.csv --account Assets:Bank --skip-header
```

Rows already imported to the same account (same date, description and amount) are skipped, including repeats inside the same file. The import is atomic: if any row is bad, nothing is imported and the command fails. Output: `{"imported": N, "skipped": M}`.

Unmatched rows go to `Expenses:Uncategorized` (negative amounts) or `Income:Uncategorized` (positive amounts). A zero amount goes to `Expenses:Uncategorized`.

### rule

Rules assign a category account to imported lines. The pattern is a case-insensitive regular expression searched in the description. The first matching rule wins. The account must already exist.

```
python3 -m fin --db home.db account add Expenses:Groceries
python3 -m fin --db home.db rule add "tesco|lidl" Expenses:Groceries
python3 -m fin --db home.db rule list
```

### budget

Sets a monthly budget for an expense account. The account must exist and be of type expense. Setting a budget again replaces the old value.

```
python3 -m fin --db home.db budget set Expenses:Groceries 2026-01 400
python3 -m fin --db home.db report budget 2026-01
```

`report budget` lists every budgeted account with `budget`, `actual` (postings in that month, including sub-accounts) and `remaining` (budget minus actual).

### recurring

A recurring transaction is a template with postings that is posted again on a schedule. Postings are stored as given. A blank posting is resolved when the transaction is created, so the balancing amount can change each time.

```
python3 -m fin --db home.db recurring add Rent --every monthly --start 2026-01-05 \
    --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --db home.db recurring run --until 2026-06-30
```

`--every` is `monthly`, `weekly` or `yearly`. Occurrences start at `--start` and run through `--until`, inclusive. Monthly keeps the start day, clamped to the month's last day. Yearly from Feb 29 falls on Feb 28. Each occurrence is created once; running again creates nothing new. Output: `{"created": N}`.

### report

All report amounts are in the book currency unless `--currency CUR` is given. Each account total is converted at the report date, so a missing rate is an error.

```
python3 -m fin --db home.db report income --from 2026-01-01 --to 2026-12-31
python3 -m fin --db home.db report balance-sheet --at 2026-12-31 --currency USD
python3 -m fin --db home.db report networth --from 2026-01 --to 2026-06
python3 -m fin --db home.db report budget 2026-01
```

- `report income` gives income and expenses for a date range, with `total_income`, `total_expenses` and `net`.
- `report balance-sheet` gives assets, liabilities and equity as of a date. Retained earnings are income minus expenses to date, and the totals add up.
- `report networth` gives one row per month, as of the month end. Liabilities are positive and `networth` is assets minus liabilities. A `--from` after `--to` is an error.

### loan

Prints a loan repayment schedule with a fixed monthly payment. The last row repays the remaining balance. Rates are annual percentages; `0` gives equal principal payments.

```
python3 -m fin --db home.db loan schedule 10000 6.5 12 --start 2026-01-15
```

Like the other commands, it needs an existing book file.

### serve

Runs a JSON HTTP API on `127.0.0.1` (not reachable from other machines). The default port is 8000.

```
python3 -m fin --db home.db serve --port 8080
```

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/accounts` | list of accounts |
| GET | `/transactions` | optional `account`, `from`, `to` |
| POST | `/transactions` | body `{"date", "description", "postings": [{"account", "amount"?}]}`; returns 201 and the transaction |
| GET | `/balances` | optional `at` |
| GET | `/reports/income` | `from` and `to` required; optional `currency` |
| GET | `/reports/balance-sheet` | `at` required; optional `currency` |

Example:

```
curl -s -X POST http://127.0.0.1:8080/transactions -H 'Content-Type: application/json' \
    -d '{"date": "2026-01-05", "description": "Rent", "postings": [{"account": "Expenses:Rent", "amount": "900"}, {"account": "Assets:Bank"}]}'
```

Errors are JSON `{"error": "..."}`: 400 for bad input, 404 for an unknown path, 405 for a wrong method on a known path.

## Running the tests

Requires Python 3 only. From the project folder:

```
python3 -m unittest discover -s tests
```

To run one module:

```
python3 -m unittest tests.test_serve
```

## Assumptions

- Non-JSON output is pretty-printed JSON. `--json` gives compact JSON.
- Amounts with more than two decimals are rounded half up when they are entered (for example `1.005` becomes `1.01`). Amounts are stored with two decimals.
- Zero amounts are allowed in postings.
- The book file must exist for every command except `init`.
- Currency codes are three letters and are stored upper-case.
- An exchange rate must be greater than 0.
- Import is atomic: any bad row aborts the whole file.
- Import rules require existing accounts.
- Reports convert each account's total at the report date, not each posting. Totals are sums of the displayed, rounded values.
- A budget requires an expense account.
- An imported line of zero amount is categorised as an expense (`Expenses:Uncategorized`).
- Recurring postings are stored as given; a blank posting is resolved at run time.
- The HTTP server listens on `127.0.0.1` only and has no authentication.
- A networth report with `--from` after `--to` is an error.
