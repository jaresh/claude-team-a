# fin

A small double-entry book keeper for one company, in Python 3.12+ with only the standard library.
The book is one SQLite file. The command line is the main interface, and `serve` exposes the same
operations as a JSON HTTP API on localhost.

## Usage

Run everything from the project directory:

```
python3 -m fin --db ./fin.db init --currency EUR --admin alice
python3 -m fin --db ./fin.db --user alice account add Assets:Bank
python3 -m fin --db ./fin.db --user alice account add Expenses:Rent
python3 -m fin --db ./fin.db --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --db ./fin.db balance --at 2026-01-31
```

- Global options (`--db PATH`, `--json`, `--user NAME`) come before the command.
  `--db` defaults to `./fin.db`.
- `init` creates the book and its first admin user. It refuses to run if the file exists.
- Every command that changes data needs `--user NAME`, and that user must not be a viewer.
- Without `--json` the output is one JSON document, indented. With `--json` it is the same
  document on one line. A failed command prints `error: MESSAGE` on stderr, prints nothing on
  stdout, and exits with status 2. Each command runs in one SQLite transaction, so a failure
  changes nothing.
- `python3 -m fin --help` and `python3 -m fin COMMAND --help` list every command and flag.

Main commands, by area:

- Users and setup: `user add NAME --role ROLE`, `account add NAME [--currency C]`,
  `tax add CODE RATE`, `customer add NAME [--terms DAYS]`, `period close`.
- Ledger: `txn add`, `txn list`, `balance --at DATE`, `fx add`, `convert AMOUNT FROM TO --at DATE`.
- Reports: `report income`, `report balance-sheet`, `report networth`, `report trial-balance`,
  `report ledger`, `report budget`, `report aging [--payables]`, `report tax`.
- Invoices and bills: `invoice create|issue|pay|show|list`, `vendor add`, `vendor list`,
  `bill create|pay|show|list`.
- Imports and planning: `rule add`, `rule list`, `import FILE --account ACCOUNT`,
  `recurring add`, `recurring run`, `budget set`, `loan schedule`, `reconcile ACCOUNT`.
- Audit: `audit list`. Every successful change writes an audit row.

## HTTP API

```
python3 -m fin --db ./fin.db serve --port 8080
```

`serve` listens on `127.0.0.1` only, one request at a time. Each request runs the matching CLI
command in-process and returns its JSON document.

Routes (spec section 10):

| Method | Path | Notes |
|---|---|---|
| GET | `/accounts` | |
| GET | `/transactions` | optional `account`, `from`, `to` query parameters |
| GET | `/balances?at=DATE` | |
| GET | `/reports/income?from=DATE&to=DATE` | |
| GET | `/reports/balance-sheet?at=DATE` | |
| GET | `/reports/aging?at=DATE[&payables=1]` | |
| GET | `/invoices` | |
| GET | `/invoices/ID` | 404 when there is no such invoice |
| GET | `/audit` | same document as `audit list` |
| POST | `/transactions` | body: `{"date", "description", "postings": [{"account", "amount"}]}`; leave one amount out to balance it |
| POST | `/invoices` | body: `{"customer", "date", "lines": [{"description", "quantity", "price", "tax_code"}]}` |
| POST | `/invoices/ID/issue` | |
| POST | `/invoices/ID/payments` | body: `{"amount", "date", "account"}` |

Rules for the API:

- Every POST needs an `X-User: NAME` header. Missing or unknown user gives 401. A viewer gives 403.
  GET needs no user.
- Creates return 201. Other successful requests return 200.
- Bad input (malformed JSON, missing fields, a CLI error such as an unknown account or an
  unbalanced transaction) returns 400. An unknown path returns 404.
- Every error body is `{"error": "MESSAGE"}`.
- Line fields for invoices may not contain `;`, because the CLI separates them with `;`.

Example:

```
curl -s -X POST http://127.0.0.1:8080/transactions \
    -H 'X-User: alice' -H 'Content-Type: application/json' \
    -d '{"date": "2026-01-05", "description": "Rent", "postings": [
          {"account": "Expenses:Rent", "amount": "900"},
          {"account": "Assets:Bank"}]}'
```

## Tests

From the project directory:

```
python3 -m unittest discover -s tests                   # all tests
python3 -m unittest discover -s tests -p 'test_server.py'
python3 -m unittest tests.test_acceptance.HttpApi       # HTTP API against a real serve process
```

`tests/test_server.py` runs the server in a thread on a free port with its own book, and checks
routes, status codes and auth. `tests/test_acceptance.py` runs the CLI and `serve` as
subprocesses against the spec's examples.

## Assumptions

Where the spec is silent, these choices apply.

Output and errors:

- Without `--json` the output is indented JSON. With `--json` it is compact. Both print exactly
  one document on success.
- Errors raise a `FinError`: exit 2, message on stderr, nothing on stdout.
- Global options (`--db`, `--json`, `--user`) come before the command.
- An unknown `--user` is an error for every command. Write commands without `--user` are errors.
- `serve` decides 401 and 403 by checking the `users` table. Other errors come from the CLI.

Money, dates and currency:

- Money is `Decimal`, rounded to cents with ROUND_HALF_UP. Posting amounts have at most two
  decimals; more is a user error.
- Convert: each amount is converted and rounded to cents, then the results are summed.
- `convert AMOUNT` uses `core.money`, so `12.345` is an error. `--at` is required on `convert`.
- `get_rate` looks for a direct rate first, then falls back to the inverse (lead decision).
- A report with `--currency` different from the book currency needs a rate on the report date,
  even when there are no postings in that currency (lead decision).
- `fx add` returns `{"date", "from", "to", "rate"}`. The rate must be above zero and the two
  currencies must differ.
- Dates are ISO strings (`YYYY-MM-DD`). Months are `YYYY-MM`.
- `networth` and `trial-balance` take `--currency` as an extension; the default is the book
  currency. `ledger` takes no `--currency` and shows each amount in its account's currency,
  converted at the posting date.
- `--from` after `--to` is a user error.
- Parent accounts created by `account add` take the child's currency.

Ledger and accounts:

- `txn list --account` matches the account and any name starting with `ACCOUNT:`. Output lists
  all postings of each matching transaction.
- `recurring add` returns `{"name", "every", "start"}`. `recurring run` writes occurrences to
  `recurring_occurrences`, so running it again creates nothing new. It audits every run, even
  when nothing is created.
- `budget set` returns `{"account", "month", "budget"}`. It accepts any valid money amount, and
  an unknown or non-expense account is an error.
- `init`, `user add`, `account add` and `period close` print small JSON objects. `user add`
  requires `--role`.

Invoices and bills:

- Due date is the invoice date plus the customer's terms. Terms are 0 to 3650 days, default 30.
  Tax rate must be zero or more.
- Each invoice line account must already exist, except `Assets:TaxReceivable` and
  `Liabilities:Payable`, which are created when needed. Line accounts must be in the book
  currency. A line net must be above zero. Line description and account must not be empty.
- Tax codes come from `tax add`. An unknown code is an error. An empty code means no tax and is
  stored as NULL.
- An empty description, negative quantity or price, or a missing tax code where one is needed is
  an error.
- `invoice create --line` and `bill create --line` split on `;`. Descriptions with `;` are not
  supported through the API.

Loans, imports and reconcile:

- Loan principal must be above zero, RATE zero or more, and MONTHS a whole number of at least 1.
  Otherwise the command fails.
- A zero-rate schedule uses PRINCIPAL/MONTHS rounded, and the last row absorbs the difference.
  The Decimal context (precision 40) is set locally, not globally.
- `rule add` rejects an empty pattern and an invalid regex. It checks ACCOUNT's type only and does
  not require the account to exist, since `import` creates it.
- `import` splits on `,` and uses the `csv` module for quoting. Blank lines are ignored. A zero
  amount is an error, and the whole import fails.
- `reconcile` is a write command, so viewers cannot run it, even without `--clear`. It audits
  every successful run. An unknown ACCOUNT is an error. `--clear` marks all postings of that
  transaction, not just one.

Serve:

- `serve` is single-threaded and runs each request in-process with a fresh connection.
- `--port 0` picks a free port.
- The server only listens on `127.0.0.1`. It has no authentication beyond the `X-User` header.
