# fin

A small-business finance tool: a double-entry book in a single SQLite file, with
a command line interface and a JSON HTTP API over the same operations.
Python 3.12+, standard library only.

## Running

```sh
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
```

Global flags go **before** the command: `fin --json audit list` works, `fin audit list --json` does not (argparse exits 2).

- `--db PATH`: the book file. Default `./fin.db`.
- `--json`: print JSON instead of text tables.
- `--user NAME`: the acting user. Required for any command that changes data; reads need no user.

Errors print `error: ...` on stderr, exit 1, and leave stdout empty. Bad usage exits 2.

## Quick start

```sh
python -m fin init --currency usd --admin ann
python -m fin --user ann user add --name ed --role editor
python -m fin --user ann account add --name Assets:Bank
python -m fin --user ann account add --name Income:Sales
python -m fin --user ann txn add --date 2026-01-02 --description "Sale" \
    --posting "Assets:Bank=300" --posting "Income:Sales"
python -m fin report income --from 2026-01-01 --to 2026-01-31
python -m fin --json balance --account Assets:Bank --date 2026-01-31
```

## Commands

| Area | Commands |
| --- | --- |
| Book | `init --currency C --admin NAME`, `serve --port N` |
| Accounts | `account add --name N [--currency C]`, `account list` |
| Transactions | `txn add --date D --description T --posting ACCT[=AMOUNT] ...`, `txn list [--account A] [--from D] [--to D]`, `balance --account A [--date D] [--currency C]` |
| Currency | `fx add --from C --to C --date D --rate R`, `convert --amount X --from C --to C [--date D]` |
| Import | `rule add --pattern P --account A`, `rule list`, `import --account A --file CSV` |
| Budgets | `budget set --account A --month M --amount X`, `report budget --account A --month M` |
| Recurring | `recurring add --name N --every monthly\|weekly\|yearly --start D --posting ...`, `recurring run [--asof D]` |
| Loans | `loan schedule --principal X --rate R --months N --start D` |
| Reports | `report income`, `report balance-sheet`, `report networth`, `report trial-balance`, `report ledger --account A`, `report tax`, `report aging` (each takes `--date` or `--from/--to` as shown by `--help`) |
| Users | `user add --name N --role admin\|editor\|viewer`, `user list` |
| Audit | `audit list` |
| Periods | `period close --month M`, `period status` |
| Tax codes | `tax add --code C --rate R`, `tax list` |
| Customers and invoices | `customer add --name N [--terms DAYS]`, `customer list`, `invoice create --party N --date D --line "DESC;QTY;PRICE;ACCOUNT;TAX_CODE" ...`, `invoice issue --id N`, `invoice pay --id N --account A [--amount X] [--date D]`, `invoice show --id N`, `invoice list` |
| Vendors and bills | `vendor add --name N [--terms DAYS]`, `vendor list`, `bill create --party N --date D --line ...`, `bill pay --id N --account A [--amount X] [--date D]`, `bill show --id N`, `bill list` |
| Reconciliation | `reconcile --account A [--mark ID ...] [--unmark ID ...] [--statement X]` |

Run `python -m fin COMMAND --help` for the full option list.

## HTTP API

```sh
python -m fin --db book.db serve --port 8080
```

The server binds to `127.0.0.1` only.

- `GET /api/<command words>?arg=value` runs a read. Example: `GET /api/balance?account=Assets:Bank&date=2026-01-31`.
- `POST /api/<command words>` runs a command with a JSON object body. Example: `POST /api/txn/add`.
- The acting user comes from the `X-User` header, or a `user` field in the body.
- Status codes: 400 for invalid input, 401 for a missing or unknown user on a write, 403 when the user's role is not allowed, 404 for an unknown route or command, 500 for anything unexpected. Error bodies are `{"error": "..."}`.
- Every response carries `Content-Length`.

## Assumptions

**Money.** Amounts are decimal strings with at most two decimal places, and are
output with exactly two decimals (`"1200.00"`). Zero is `"0.00"`, never `"-0.00"`.
Rounding is half-up to the cent. Arithmetic uses 50-digit decimals, so no
binary floats are involved.

**Dates.** Dates are `YYYY-MM-DD` and months are `YYYY-MM`. Adding months clamps
to the month end (Jan 31 + 1 month = Feb 28/29). A yearly recurrence on Feb 29
falls on Feb 28 in non-leap years.

**Accounts.** An account name is a colon-separated path. The first segment sets
the type: `Assets`, `Liabilities`, `Equity`, `Income` or `Expenses`. Accounts must
be created before use. Posting to an unknown account is an error. A posting
belongs to an account if it matches the account name or sits below it (`in_family`).

**Transactions.** Each transaction must balance per currency. One posting may omit
its amount, and that amount is filled in to balance. A posting in a currency
other than the account's is converted with the latest stored rate on or before the
transaction date, or with the inverse of the reverse-direction rate if only that
exists. Without a rate, the posting is rejected.
Every posting goes through the same path: account checks, closed-period check,
balance check, then insert.

**One transaction per invocation.** Each command runs in a single SQLite
transaction (`BEGIN IMMEDIATE`). Output is printed only after the commit. If a
command fails, nothing is written, no audit row is added, and stdout is empty.

**Closed periods.** `period close --month M` closes every month up to and including
M. It only moves forward. Transactions dated in a closed month are rejected.

**Users and roles.**
- `admin` can do everything.
- `editor` can change data but cannot manage users, tax codes or periods.
- `viewer` can only read.
- Writes without `--user` fail. An unknown user fails with 401. A viewer, or an
  editor on an admin command, fails with 403.

**Audit log.** Each successful write adds one row: user, action, target (JSON of
the arguments), and an `at` timestamp in UTC (`Z` suffix). Failed writes and reads
add nothing. Reconciliation marks and unmarks are audited where they happen.

**Import.** CSV needs `Date`, `Description` and `Amount` columns. Rows already
imported (same date, description and amount for the same account) are skipped.
The first rule whose pattern matches the description wins. Rows with no matching
rule go to `Equity:Suspense`.

**Recurring.** `recurring run` posts every occurrence due on or before `--asof`
(default today) that has not yet been posted. Running it again posts nothing new.
A posting with no amount is worked out at each run.

**Invoices and bills.**
- Invoices are numbered `INV-YYYY-NNNN` and bills `BILL-YYYY-NNNN`, unique per kind.
  Numbers are assigned when the document is issued (invoices) or created (bills).
- Issuing an invoice debits `Assets:Receivables` for the total, credits each
  income account for its net, and credits `Liabilities:Sales Tax` for the tax.
- Creating a bill debits each expense account for its net, debits
  `Assets:Input Tax` for the tax, and credits `Liabilities:Payables` for the total.
- Paying an invoice debits the bank and credits `Assets:Receivables`. Paying a bill
  debits `Liabilities:Payables` and credits the bank.
- Statuses: invoice `draft` → `issued` → `partial` / `paid`; bill `open` → `partial` / `paid`.
  Drafts post nothing. Overpayment is rejected.
- Line format: `DESCRIPTION;QUANTITY;PRICE;ACCOUNT;TAX_CODE`. The tax code may be empty.
- Due dates come from the party's payment terms in days.

**Tax codes.** Each code has a rate between 0 and 100 and a unique name.
`report tax` totals sales and purchases by code, counting only issued invoices
and created bills.

**Reconciliation.** Cleared marks are stored per account, so marks in one account
do not affect another. `cleared_balance` is the sum of marked transactions,
`uncleared_balance` is book minus cleared, and `difference` is the statement
balance minus cleared balance when `--statement` is given.

**Database.** A book is a SQLite file. `init` refuses to overwrite an existing
file. The default location is `./fin.db`.

## Tests

```sh
python -m unittest discover -s tests
```

The suite covers each feature area in its own module under `tests/`. It includes
the CLI as a subprocess and the HTTP API on a real socket.
