# fin

A command-line double-entry bookkeeping tool backed by one SQLite file. It keeps
accounts, balanced transactions, multi-currency rates, invoices, bills, loans,
recurring entries, budgets, bank imports and reconciliation, and it prints
reports. A small JSON HTTP API runs the same commands.

## Running

Run from the repository root:

```sh
python -m fin --help
```

Where `python` is absent (only `python3` installed), use:

```sh
python3 -m fin --help
```

The examples below use `python3 -m fin`. Use `python -m fin` if that is what
your system has.

Run the test suite from the repository root:

```sh
python3 -m unittest discover -s tests
```

### Database and global options

Every command except `init` and the read-only `convert` and `loan schedule`
needs a database file. These options go before the command name:

| Option | Meaning |
| --- | --- |
| `--db PATH` | SQLite file. Default `./fin.db`. |
| `--json` | Compact JSON output. Without it, output is the same JSON indented 2 spaces. |
| `--user NAME` | Acting user. Required for every command that changes data. |

Output is one JSON document followed by a newline. A list or a dict command
prints once.

Exit codes: `0` on success; `2` for any error: a bad argument, a missing or
unknown user, a forbidden action, a missing database, or a closed period. The
error text goes to stderr as `error: MESSAGE`.

```sh
python3 -m fin --db books.db init --currency EUR --admin alice
python3 -m fin --db books.db --user alice --json balance
```

`init` creates the file and the first user, who is an admin. It refuses to run
if the file already exists.

## Command reference

Commands are grouped. `python3 -m fin GROUP --help` lists a group's commands.
Each entry below gives one example. Dates are `YYYY-MM-DD`, months are
`YYYY-MM`, and amounts are decimal strings with at most two decimals.

### Setup and users

```sh
python3 -m fin --db books.db init --currency EUR --admin alice
python3 -m fin --db books.db --user alice user add bob --role editor
python3 -m fin --db books.db user list
```

`user add NAME --role admin|editor|viewer` (admin only). `user list`.

### Accounts

```sh
python3 -m fin --db books.db --user alice account add Expenses:Food:Groceries
python3 -m fin --db books.db account list
```

`account add NAME [--currency CUR]` creates the account and any missing parent
accounts. `account list`. The first segment of the name sets the type: `Assets`,
`Liabilities`, `Equity`, `Income` or `Expenses`.

### Transactions and balances

```sh
python3 -m fin --db books.db --user bob txn add --date 2026-01-05 --desc "Groceries" \
    --posting Expenses:Food:Groceries=12.50 --posting Assets:Bank
python3 -m fin --db books.db txn list --account Expenses --from 2026-01-01 --to 2026-01-31
python3 -m fin --db books.db balance --at 2026-01-31
```

`txn add --date DATE --desc TEXT --posting ACCOUNT=AMOUNT` (repeatable). A
transaction must balance per currency. One posting per transaction may leave
out its amount; it is filled with the balancing amount. `txn list [--account
PREFIX] [--from DATE] [--to DATE]` lists transactions in date and id order;
`--account` matches the account and everything under it. `balance [--at DATE]`
prints the signed balance of each account and its parents, per currency.

### Currency rates

```sh
python3 -m fin --db books.db --user bob fx add 2026-01-01 USD EUR 0.92
python3 -m fin --db books.db convert 100 USD EUR --at 2026-01-15
```

`fx add DATE FROM TO RATE` means 1 FROM = RATE TO from DATE on. `convert AMOUNT
FROM TO --at DATE` uses the latest rate on or before that date.

### Parties and tax codes

```sh
python3 -m fin --db books.db --user bob customer add Acme --terms 14
python3 -m fin --db books.db --user bob vendor add Supplier
python3 -m fin --db books.db --user bob tax add VAT20 20
python3 -m fin --db books.db customer list
```

`customer add NAME [--terms DAYS]`, `vendor add NAME [--terms DAYS]` (terms
default 30), `tax add CODE RATE` (rate in percent), and `list` for each.

### Invoices

```sh
python3 -m fin --db books.db --user bob invoice create --customer Acme --date 2026-02-01 \
    --line "Consulting;2;100;VAT20"
python3 -m fin --db books.db --user bob invoice issue 1
python3 -m fin --db books.db --user bob invoice pay 1 240 --date 2026-02-10 --account Assets:Bank
python3 -m fin --db books.db invoice list --status issued
```

`invoice create --customer NAME --date DATE --line DESCRIPTION;QUANTITY;PRICE;TAXCODE`
(repeatable; `TAXCODE` may be empty) makes a draft. `invoice issue ID` numbers it
(`INV-YYYY-NNNN`) and posts it. `invoice pay ID AMOUNT --date DATE --account
ACCOUNT` records money received. `invoice show ID`. `invoice list [--status
draft|issued|partial|paid]`.

### Bills

```sh
python3 -m fin --db books.db --user bob bill create --vendor Supplier --ref B-1 \
    --date 2026-02-03 --line "Paper;100;Expenses:Office;VAT20"
python3 -m fin --db books.db --user bob bill pay 1 50 --date 2026-02-12 --account Assets:Bank
python3 -m fin --db books.db bill list --status open
```

`bill create --vendor NAME --ref TEXT --date DATE --line DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE`
(repeatable; `AMOUNT` is the net amount). `bill pay ID AMOUNT --date DATE
--account ACCOUNT`. `bill show ID`. `bill list [--status open|partial|paid]`.

### Reports

```sh
python3 -m fin --db books.db report income --from 2026-01-01 --to 2026-12-31
python3 -m fin --db books.db report balance-sheet --at 2026-12-31
python3 -m fin --db books.db report networth --from 2026-01 --to 2026-06
python3 -m fin --db books.db report trial-balance --at 2026-12-31
python3 -m fin --db books.db report ledger Expenses:Food --from 2026-01-01 --to 2026-12-31
python3 -m fin --db books.db report tax --from 2026-01-01 --to 2026-12-31
python3 -m fin --db books.db report aging --at 2026-03-01 --payables
python3 -m fin --db books.db report budget 2026-01
```

- `report income --from DATE --to DATE [--currency CUR]`: income and expenses
  over a period, with the net.
- `report balance-sheet --at DATE [--currency CUR]`: assets, liabilities and
  equity, including retained earnings.
- `report networth --from MONTH --to MONTH`: one row per month, in the book
  currency, valued at the month's last day.
- `report trial-balance --at DATE`: debit and credit per account, in the book
  currency.
- `report ledger ACCOUNT --from DATE --to DATE`: postings of the account and its
  children, with running balance.
- `report tax --from DATE --to DATE`: tax collected on invoices and paid on
  bills, per tax code.
- `report aging --at DATE [--payables]`: open invoices (or bills with
  `--payables`) by days past due.
- `report budget MONTH`: budget, actual and remaining for each budgeted
  expense account.

### Budgets

```sh
python3 -m fin --db books.db --user bob budget set Expenses:Food 2026-01 400
```

`budget set ACCOUNT MONTH AMOUNT` sets (or replaces) an expense account's budget
for a month. The report is `report budget MONTH` above.

### Loans

```sh
python3 -m fin loan schedule 1000 12 3 --start 2026-01-31
```

`loan schedule PRINCIPAL RATE MONTHS --start DATE` prints the payment schedule
of a fixed-rate loan. `RATE` is an annual percent (`12` means 12%). It reads no
database and needs no user.

### Recurring entries

```sh
python3 -m fin --db books.db --user bob recurring add Rent --every monthly --start 2026-01-31 \
    --posting Expenses:Office=500 --posting Assets:Bank
python3 -m fin --db books.db --user bob recurring run --until 2026-03-31
```

`recurring add NAME --every monthly|weekly|yearly --start DATE --posting
ACCOUNT=AMOUNT` stores a template. `recurring run --until DATE` posts every due
occurrence up to that date. A run that has already posted an occurrence skips it,
so running again is safe.

### Bank imports and rules

```sh
python3 -m fin --db books.db --user bob rule add "coffee" Expenses:Food
python3 -m fin --db books.db --user bob import statement.csv --account Assets:Bank --skip-header
python3 -m fin --db books.db rule list
```

`rule add PATTERN ACCOUNT` sends descriptions matching a case-insensitive regular
expression to ACCOUNT. `rule list` lists rules in the order added.
`import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N]
[--skip-header]` reads a CSV bank statement. Columns are counted from 0; the
defaults are 0 for date, 1 for description and 2 for amount.

### Reconciliation

```sh
python3 -m fin --db books.db --user bob reconcile Assets:Bank --date 2026-01-31 --balance 1234.56 \
    --clear 6 --clear 7
```

`reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID]...` reports the
cleared balance, the difference from the statement balance and the uncleared
transaction ids. Each `--clear` marks a transaction as cleared. Leave out
`--clear` for a read-only report.

### Periods

```sh
python3 -m fin --db books.db --user alice period close 2026-01
python3 -m fin --db books.db period status
```

`period close MONTH` closes that month and every earlier one (admin only).
`period status` shows the closed-through month. Transactions, invoices, bills,
imports and recurring runs dated in a closed month are refused.

### Audit log

```sh
python3 -m fin --db books.db audit list --by bob
```

`audit list [--by NAME]` lists entries oldest first. See the Audit log section
below.

### Server

```sh
python3 -m fin --db books.db serve --port 8000
```

`serve --port N` runs the HTTP API until stopped. See the HTTP API section below.

## HTTP API

`serve` listens on `127.0.0.1` only. Each request runs the matching CLI command
in-process with `--json`, so the responses are the same JSON the CLI prints.

### Routes

| Method | Path | CLI equivalent | Status |
| --- | --- | --- | --- |
| GET | `/accounts` | `account list` | 200 |
| GET | `/transactions?account=&from=&to=` | `txn list` | 200 |
| GET | `/balances?at=` | `balance` | 200 |
| GET | `/reports/income?from=&to=` | `report income` | 200 |
| GET | `/reports/balance-sheet?at=` | `report balance-sheet` | 200 |
| GET | `/reports/aging?at=&payables=1` | `report aging` | 200 |
| GET | `/invoices?status=` | `invoice list` | 200 |
| GET | `/invoices/ID` | `invoice show` | 200 |
| GET | `/audit?by=` | `audit list` | 200 |
| POST | `/transactions` | `txn add` | 201 |
| POST | `/invoices` | `invoice create` | 201 |
| POST | `/invoices/ID/issue` | `invoice issue` | 200 |
| POST | `/invoices/ID/payments` | `invoice pay` | 200 |

GET requests take no user and only read data. POST requests change data and
need the acting user.

### Users and the X-User header

Every POST takes the acting user from the `X-User` header. The role rules are
the same as on the CLI (see Roles).

```sh
curl -s -X POST http://127.0.0.1:8000/transactions \
    -H 'X-User: bob' -H 'Content-Type: application/json' \
    -d '{"date": "2026-01-05", "description": "Groceries",
         "postings": [{"account": "Expenses:Food", "amount": "12.50"},
                      {"account": "Assets:Bank"}]}'
```

### Request bodies

- `POST /transactions`: `{date, description, postings: [{account, amount}]}`.
  A posting with no `amount` (or `null`) is the balancing posting.
- `POST /invoices`: `{customer, date, lines: [{description, quantity, price,
  tax_code?}]}`. Each line needs `description`, `quantity` and `price`.
- `POST /invoices/ID/issue`: no body.
- `POST /invoices/ID/payments`: `{amount, date, account}`.

### Status codes and errors

- `200` for reads and for issue and payment; `201` for created records.
- `400` for a bad request: invalid JSON, a bad field, a domain error such as an
  unbalanced transaction or a closed period, or a missing database file.
- `401` when `X-User` is missing or names an unknown user.
- `403` when the user's role may not run the action.
- `404` for an unknown path.
- `500` with `{"error": "internal error"}` for an unexpected failure.

Error bodies are JSON: `{"error": "MESSAGE"}`.

## Roles

| Role | Can read | Can change data | Admin-only actions |
| --- | --- | --- | --- |
| `admin` | yes | yes | yes |
| `editor` | yes | yes | no |
| `viewer` | yes | no | no |

- `user add` and `period close` are admin only.
- A viewer is refused every changing command.
- Read-only commands (`account list`, `txn list`, `balance`, `report ...`,
  `convert`, `loan schedule`, `audit list`, and the `list` and `show` commands)
  do not check the user, so they run without `--user`.
- `reconcile` checks the user only when it is given `--clear`.

## Audit log

Each successful change writes one row to the `audit` table: `seq`, `at` (UTC
time), `user`, `action` and `target`. A failed command writes nothing. Read-only
commands never write.

| Action | Written by | Target |
| --- | --- | --- |
| `init` | `init` | book currency |
| `user.add` | `user add` | user name |
| `account.add` | `account add` | account name |
| `period.close` | `period close` | month |
| `fx.add` | `fx add` | `FROM/TO` |
| `customer.add` | `customer add` | customer name |
| `vendor.add` | `vendor add` | vendor name |
| `tax.add` | `tax add` | tax code |
| `txn.add` | `txn add` | transaction id |
| `invoice.create` | `invoice create` | invoice id |
| `invoice.issue` | `invoice issue` | invoice id |
| `invoice.pay` | `invoice pay` | invoice id |
| `bill.create` | `bill create` | bill id |
| `bill.pay` | `bill pay` | bill id |
| `rule.add` | `rule add` | pattern |
| `import` | `import` | account (only when rows were imported) |
| `budget.set` | `budget set` | `ACCOUNT MONTH` |
| `recurring.add` | `recurring add` | template name |
| `recurring.run` | `recurring run` | until date (only when occurrences were posted) |
| `reconcile` | `reconcile --clear` | account (only when a posting changed) |

`audit list` shows the entries oldest first, with `--by NAME` to filter by user.

## Assumptions

The rules below are choices the code makes where the specification is silent.
They are grouped by area.

### Core: CLI, database, users, periods

- `init` refuses an existing file. If `init` fails after creating the file, the
  file is removed, so a retry works.
- A command other than `init` on a missing database file exits 2 with
  `no database: PATH`.
- Read-only commands accept an unknown `--user`. Changing commands refuse a
  missing or unknown user (401 in the API, exit 2 on the CLI).
- A viewer is refused every changing action. An editor is refused `user add` and
  `period close`.
- `account add` returns `{name, type, currency}`. `user add` returns
  `{name, role}`. `init` returns `{currency, admin}`. `period close` returns
  `{closed_through}`. `period status` returns `{closed_through}`, or `null` when no
  month is closed. These shapes are not fixed by the specification.
- Closing a month that is not after the current closed-through month changes
  nothing and writes no audit row.
- `--help` is printed by argparse to the real stdout, not to the output stream
  used by the handlers.
- Human output is the JSON indented by 2 spaces; `--json` gives compact JSON.
  Both end with a newline. Handlers that return nothing print nothing.
- Account types come from the first segment of the name: `Assets`,
  `Liabilities`, `Equity`, `Income` or `Expenses`.

### Ledger: transactions and balances

- Posting `seq` is 1-based, in the order given.
- Amounts with more than two decimals are refused, not rounded, on the CLI and
  in the shared posting check.
- `txn add` refuses a blank description. The shared create function accepts one,
  so imports are not blocked by it.
- Transactions balance per currency. A blank posting gets the negative of the
  sum of its currency; the other currencies must sum to zero.
- `txn list --account` with an unknown account gives an empty list, not an error.
- `balance` lists an account (and its parents) if it has any posting on or before
  `--at`, even when the balance is zero. Accounts with postings only after `--at`
  are absent.
- A bad `--at`, `--from` or `--to` date is a user error.
- `txn list` and `balance` do not check the user.
- `--user` must come before the command name, as the global options do.

### Currency rates

- `fx add` refuses FROM equal to TO.
- The rate must be a strict decimal greater than zero. It is stored as given, so
  `1.10` stays `1.10`.
- A repeated date and pair replaces the earlier row.
- `convert` takes `--at` as required, with no default date. Its amount may have
  any number of decimals; the output is rounded to cents.
- Currency codes are three letters, stored uppercase. Any three-letter code is
  accepted; currencies are not checked against the book.
- A conversion uses the direct rate on the latest date on or before the given
  date. If there is none, it uses the inverse of the latest reverse rate. The
  direct rate wins over the inverse on the same date.

### Loans

- The principal has at most two decimals and must be positive. The months must
  be digits. The rate must not be negative.
- Each non-final month's interest is the balance times the rate divided by 1200,
  rounded to cents with `ROUND_HALF_UP`. The final row repays the remaining
  balance, so its payment absorbs the rounding.
- A zero rate gives a payment of the principal divided by the months, rounded to
  cents; the final row absorbs the difference.
- Row dates use `start + n months`, so a January 31 start gives February 28, March
  31, and so on.
- The command is read-only: no user, no audit, no database.

### Parties and tax codes

- Payment terms are digits only (`+3`, `1.5`, `-1` and `1e3` are refused).
  The default is 30 days.
- A tax rate must parse as a decimal and must not be negative. It is stored as
  given (`5.50` stays `5.50`).
- Names must not be blank after trimming. Customers and vendors are separate
  namespaces, so one name may be both.
- `customer add`, `vendor add` and `tax add` are allowed to editors and admins.

### Invoices

- Each line is exactly four `;`-separated fields. Quantity must be greater than
  zero and price must not be negative. Both are stored as entered.
- An empty tax code means no tax.
- Invoice numbers are `INV-YYYY-NNNN`, where the count is of issued invoices with
  that prefix, plus one. The year is the invoice date's year.
- The payment amount is checked (positive, at most two decimals) before the
  status checks.
- Aging skips drafts and uses the invoice date. A payment counts only if it is
  dated on or before the report date.
- Known limitation: aging sees only issued invoices. An invoice dated on or
  before the report date but issued after it is left out, because the invoice
  stores no issue timestamp. Exact handling would need an issue date on the
  invoice.

### Bills

- Each line is exactly four `;`-separated fields: description, net amount (at
  least zero, at most two decimals), account, and tax code (may be empty).
- A line's account must exist and be of type expense or asset.
- The reference is trimmed and must not be empty. It must be unique per vendor;
  the duplicate check runs before the lines are checked.
- Each line posts its own account with the net amount, one posting per line (lines
  are not merged by account). The tax is a single posting to
  `Assets:TaxReceivable`, only when the bill's tax is not zero. The total is
  posted to `Liabilities:Payable`.
- Payments are described as `Payment REF`. Error messages refer to the bill as
  `bill ID`.
- Aging for bills, like invoices, skips drafts (bills have no draft status).

### Budgets

- A negative budget is refused. Zero is allowed.
- Budgets have at most two decimals.
- Setting a budget replaces any earlier one for that account and month, and is
  always audited.
- `budget set` accepts only expense accounts.
- `actual` is the account's own currency only, including its child accounts; it
  does not convert other currencies. An account with no postings shows `0.00`.
- `report budget` is read-only, like the other reports.

### Bank imports and rules

- A rule pattern is a case-insensitive regular expression. An invalid pattern is
  refused. An empty pattern matches every description.
- A rule's account must exist and be in the book currency. There is no command to
  remove an account or a rule, so rules stay valid.
- Rules are tried in the order added; the first match wins. An unmatched row
  goes to `Expenses:Uncategorized` (negative) or `Income:Uncategorized`
  (positive), created when first needed.
- The import account must exist and be in the book currency.
- Every row is parsed before anything is written. A bad date, a bad amount, more
  than two decimals, a zero amount, an empty description or a missing column
  fails the whole import and names the line.
- A row is a duplicate when the account, date, description and amount match an
  earlier import or an earlier row in the same file. Duplicates are skipped.
  Skipped rows do not run the closed-period check.
- The import runs in one database transaction: if any row fails, nothing is
  written.
- Blank CSV lines are skipped. The file is read as UTF-8, with an optional byte
  order mark. An unreadable file is a user error.
- Column numbers below zero are refused. Default columns are 0 (date), 1
  (description) and 2 (amount).
- The `import` audit row is written only when at least one row was imported.

### Recurring entries

- Names are not unique. Each template is identified by its id, and each run posts
  every template that is due.
- Blank postings stay blank in the template and are filled per occurrence.
- Occurrence `k` is computed from the start date (`start + k months`, `start + 7k
  days`, `start + k years`), so month-end clamping does not drift.
- A run skips occurrences already recorded for that template. A closed-period
  occurrence fails the whole run, and the database transaction undoes the
  occurrences posted earlier in that run.
- `recurring run` audits with the until date as the target, only when it created
  something.
- There is no command to list or remove templates.
- `recurring add` returns `{id, name, every, start, postings}`.

### Reports

- `report income` and `report balance-sheet` accept `--currency`; the default is
  the book currency. `report networth`, `report trial-balance` and `report tax`
  use the book currency.
- Each account's amount is converted and rounded to cents once; totals are sums of
  those rounded values. With several currencies, total assets may differ from
  liabilities plus equity by about a cent. Single-currency books balance exactly.
- Every currency present in the raw sums needs a rate on or before the report
  date, even when the balance is zero.
- `report ledger` converts each posting at the posting date. For an account in its
  own currency, the amounts are unchanged.
- In the trial balance, when the rounded rows differ from zero, the difference goes
  to the row with the largest absolute balance; ties go to the first account name.
- `report tax`: collected is the sum of invoice line tax in the period, and paid
  is the sum of bill line tax. Draft invoices are excluded. Lines with no tax code
  count in the totals but not in `by_code`.
- Period reports refuse a start date after the end date. `report networth` refuses
  a start month after the end month.
- `report ledger` filters postings in Python rather than with an index on account
  prefix. This suits a small book.
- All reports are read-only and do not check the user.

### Reconciliation

- A report without `--clear` is read-only. With `--clear`, the user must be an
  editor or an admin.
- Every `--clear` id is checked before any update. One bad id marks nothing, and
  the error names the id.
- Duplicate ids are removed. Clearing a transaction marks all of its postings to
  the account.
- An audit row is written only when at least one posting changed from uncleared to
  cleared. Clearing an already cleared transaction writes nothing.
- The cleared balance counts only the account's cleared postings dated on or
  before the statement date. It is summed in Python.
- `uncleared` lists the distinct transaction ids that have an uncleared posting to
  the account on or before the statement date, in ascending order.
- `difference` is the statement balance minus the cleared balance; zero shows as
  `0.00`.
- `--clear` ids must be integers. `--balance` may be negative and has at most two
  decimals.
- An unknown account is a user error.

### HTTP API

- The port defaults to 8000 and the server binds `127.0.0.1` only.
- A missing or zero `Content-Length` is an empty body, which becomes `{}` for
  POST.
- Unknown query parameters are ignored. For `/reports/aging`, only `payables=1`
  turns on bills.
- A missing database file gives 400 before any access check, because the
  connection would otherwise create an empty file.
- Order for POST: route match (404), then access check (401 or 403), then body
  parse (400), then the CLI command. A CLI error exit (code 2) becomes 400, with
  the stderr message minus the `error: ` prefix.
- POST `/transactions`: a posting with no amount or a null amount becomes an
  account-only posting. `postings` must be a list of objects with a string
  `account`; other field types give 400.
- POST `/invoices`: any field containing `;` gives 400, since it would break the
  line format. An absent `tax_code` means no tax.
- The server writes each request line to stderr (the default request logger).
- Error bodies are `{"error": "MESSAGE"}`. An unexpected exception gives a 500 with
  `{"error": "internal error"}`.
