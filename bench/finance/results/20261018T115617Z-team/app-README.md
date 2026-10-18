# fin: small-business finance system

`fin` is a double-entry bookkeeping system for a small business. It keeps accounts, transactions,
exchange rates, budgets, recurring entries, customer invoices, vendor bills, tax codes, bank
reconciliation, and loan schedules in one SQLite file (a "book"). It has a command-line interface
and a read/write HTTP API.

Everything is stdlib only. Money is `decimal.Decimal` (never `float`) and is stored as text with two
decimals.

## Install

Requirements:

- Python 3.12 or newer. On this machine the interpreter is `python3`.
- No third-party packages. Nothing to install.

Run from the repository root:

```
python3 -m fin --help
```

## Quick start

The database path defaults to `fin.db` in the current directory. Pass `--db PATH` to use another file.

```
python3 -m fin init --currency EUR --admin alice
python3 -m fin account add Assets:Bank
python3 -m fin account add Income:Salary
python3 -m fin account add Expenses:Rent
python3 -m fin --user alice txn add --date 2026-01-01 --desc Salary \
    --posting Assets:Bank=3000.00 --posting Income:Salary
python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900.00 --posting Assets:Bank
python3 -m fin balance --at 2026-01-31
python3 -m fin --user alice import bank.csv --account Assets:Bank --skip-header
python3 -m fin report income --from 2026-01-01 --to 2026-01-31
python3 -m fin report balance-sheet --at 2026-01-31
python3 -m fin --user alice invoice create --customer Acme --date 2026-01-10 \
    --line "Consulting;10;95.00;VAT20"
python3 -m fin --user alice invoice issue 1
python3 -m fin --user alice invoice pay 1 500.00 --date 2026-02-01 --account Assets:Bank
python3 -m fin report aging --at 2026-03-01
python3 -m fin --user alice recurring add Rent --every monthly --start 2026-01-31 \
    --posting Expenses:Rent=900.00 --posting Assets:Bank
python3 -m fin --user alice recurring run --until 2026-03-31
python3 -m fin --user alice budget set Expenses:Rent 2026-01 1000
python3 -m fin report budget 2026-01
python3 -m fin loan schedule --start 2026-01-15 1000 12 12
python3 -m fin --user alice reconcile Assets:Bank --date 2026-01-31 --balance 2100.00 --clear 1
python3 -m fin serve --port 8000
```

`init` creates the book and its first admin user. Any command that writes needs `--user NAME`.
Reads do not need a user.

## Commands

Global options go before the command: `--db PATH` (default `fin.db`), `--json` (compact one-line
JSON; without it, output is indented), and `--user NAME` (required for writes).

Amounts are two-decimal strings such as `900.00`. Dates are `YYYY-MM-DD`. Months are `YYYY-MM`.

| Command | Options and arguments | What it does |
| --- | --- | --- |
| `init` | `--currency CODE --admin NAME` | Create the book, its base currency, and the first admin. |
| `account add` | `NAME [--currency CODE]` | Add an account. Names are `Type:Sub:...`; the first segment is the type. |
| `account list` | | List accounts. |
| `txn add` | `--date D --desc TEXT --posting ACCOUNT=AMOUNT` (repeat) | Post a transaction. One posting may omit `=AMOUNT` and is balanced automatically. |
| `txn list` | `[--account A] [--from D] [--to D]` | List transactions, filtered by account (and its children), and by date. |
| `balance` | `[--at D]` | Balance of each account, including parents, per currency. |
| `fx add` | `DATE FROM TO RATE` | Record an exchange rate for one date and currency pair. |
| `convert` | `AMOUNT FROM TO --at D` | Convert an amount using the latest rate on or before `--at`. |
| `import` | `FILE --account A [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]` | Import a bank CSV into an account. Duplicates are skipped. Column numbers start at 0. |
| `rule add` | `PATTERN ACCOUNT` | Categorize imported rows whose description contains `PATTERN`. |
| `rule list` | | List categorization rules. |
| `budget set` | `ACCOUNT MONTH AMOUNT` | Set (or replace) a monthly budget for an expense account. |
| `report budget` | `MONTH` | Budget, actual, and remaining for each budgeted account. |
| `recurring add` | `NAME --every monthly\|weekly\|yearly --start D --posting ACCOUNT=AMOUNT` (repeat) | Define a recurring transaction. |
| `recurring run` | `--until D` | Create every due occurrence up to `D`. Running it again creates nothing new. |
| `loan schedule` | `--start D PRINCIPAL RATE MONTHS` | Print an annuity schedule. `RATE` is the annual percent. |
| `tax add` | `CODE RATE` | Define a tax code with a percent rate. |
| `tax list` | | List tax codes. |
| `customer add` | `NAME [--terms DAYS]` | Add a customer. Default terms are 30 days. |
| `customer list` | | List customers. |
| `invoice create` | `--customer C --date D [--line "DESC;QTY;PRICE;TAXCODE"]` (repeat) | Create a draft invoice. |
| `invoice issue` | `ID` | Issue a draft: assign a number and post it to the ledger. |
| `invoice pay` | `ID AMOUNT --date D --account A` | Record a customer payment. |
| `invoice show` | `ID` | Show one invoice. |
| `invoice list` | `[--status S]` | List invoices, optionally by status. |
| `vendor add` | `NAME [--terms DAYS]` | Add a vendor. |
| `vendor list` | | List vendors. |
| `bill create` | `--vendor V --ref REF --date D [--line "DESC;NET;ACCOUNT;TAXCODE"]` (repeat) | Record a vendor bill. `REF` is unique per vendor. |
| `bill pay` | `ID AMOUNT --date D --account A` | Record a payment to a vendor. |
| `bill show` | `ID` | Show one bill. |
| `bill list` | `[--status {open,partial,paid}]` | List bills, optionally by status. |
| `reconcile` | `ACCOUNT --date D --balance AMT [--clear ID]` (repeat `--clear`) | Mark transactions as cleared and compare to the statement balance. |
| `report income` | `--from D --to D [--currency C]` | Income, expenses, and net for a period. |
| `report balance-sheet` | `--at D [--currency C]` | Assets, liabilities, and equity at a date. |
| `report networth` | `--from YYYY-MM --to YYYY-MM` | Net worth at each month end. |
| `report trial-balance` | `--at D` | Debit and credit totals per account. |
| `report ledger` | `ACCOUNT --from D --to D` | Running balance for an account and its children. |
| `report aging` | `--at D [--payables]` | Receivables aging (or payables with `--payables`). |
| `report tax` | `--from D --to D` | Tax collected, tax paid, and net, by tax code. |
| `user add` | `NAME --role admin\|editor\|viewer` | Add a user (admin only). |
| `user list` | | List users and roles. |
| `period close` | `MONTH` | Close a month: no postings may be dated in it or earlier (admin only). |
| `period status` | | Show the last closed month. |
| `audit list` | `[--by USER]` | Show the audit log. |
| `serve` | `[--port N]` | Run the HTTP API on `127.0.0.1` (default port 8000). |

### HTTP API

`serve` runs these routes. Reads need no user. Every `POST` needs an `X-User` header.

- `GET /accounts`, `GET /transactions`, `GET /balances?at=`
- `GET /reports/income?from=&to=`, `GET /reports/balance-sheet?at=`
- `GET /invoices`, `GET /invoices/ID`, `GET /reports/aging?at=[&payables=1]`, `GET /audit`
- `POST /transactions` (201), `POST /invoices` (201), `POST /invoices/ID/issue` (200), `POST /invoices/ID/payments` (200)

Status codes: an unknown path is 404 (checked first). A write with no or unknown user is 401. A
viewer writing is 403. A `UserError` is 400. An invoice that does not exist is 404. Any other
exception is 500.

## Users and roles

| Role | Can do |
| --- | --- |
| `admin` | Everything. |
| `editor` | Everything except `user add` and `period close`. |
| `viewer` | Read-only commands only. |

Writes need `--user NAME` (CLI) or `X-User` (API). A missing or unknown user is an error: exit code 2
in the CLI, 401 in the API. A viewer who tries a write gets exit code 2 in the CLI and 403 in the API.

## JSON output and exit codes

- Every command prints a JSON value on stdout. With `--json` it is one compact line; otherwise it is
  indented with two spaces.
- A command that returns nothing prints nothing. A stopped `serve` prints nothing.
- Exit code 0 means success.
- Exit code 2 means a user error (bad input, permission, closed period, unknown account, and so on).
  The message goes to stderr as `fin: MESSAGE`. Stdout is empty and nothing in the book changes. Each
  command runs in one transaction (`BEGIN IMMEDIATE`), so a failure rolls back everything it did.
- Argument parsing errors also exit 2, with argparse's usage message on stderr.

## Assumptions

The spec left these open. Each was decided during the build. They are grouped by area and listed
once.

### Money, dates, and currencies

- Amounts are parsed strictly (`core.parse_money`). They are rounded half up to cents when stored.
- `fmt()` never writes `-0.00`. Any zero is `0.00`.
- Dates are checked as `YYYY-MM-DD` and months as `YYYY-MM`.
- Currency codes match `[A-Z]{3}` (`core.CURRENCY_RE`).
- An exchange rate must be positive. Only one rate per date and currency pair is allowed.
- `convert` with the same currency returns the amount rounded to cents. Otherwise it uses the latest
  rate on or before the date, and falls back to the inverse of the latest reverse rate.
- Reports convert each account's balance at the report date. Net worth converts each month at its
  month end.
- Trial balance: the lead decided that the rounding residual from converting several currencies goes
  on the largest balance, so total debit and total credit are always equal (`fin/ledger.py`
  `report_trial_balance`).

### Accounts and books

- Account names are `Type:Sub:...`. The first segment must be one of the account types, and empty
  segments are rejected.
- `account add` rejects any existing name, including parents that were created implicitly.
- `balance` keeps currency keys whose sum is zero and lists each ancestor account.
- `txn list --account` matches the account and its children by whole segments.
- `init` creates the first admin. The admin name is stripped and cannot be empty.

### Transactions and posting

- Posting positions start at 0 and keep the order given.
- A posting with no amount gets the negative of the sum of the other postings in its currency. If no
  other postings share its currency, it gets `0.00`, so the transaction still balances.
- Start dates of recurring entries are not checked against closed periods on `add`. Only `run` checks
  them.

### Imports and rules

- The file is read as UTF-8, with an optional BOM. Blank lines are skipped.
- Date, description, and amount are stripped. The stored description is the stripped one.
- Duplicates are keyed on (account, date, description, amount).
- Errors name the record number (`row N: ...`), counting CSV records from 1 and including the header
  when `--skip-header` is given. A short row gives `row N: missing column`.
- A file that cannot be read gives `cannot read PATH: ...`.
- Uncategorized rows go to `Expenses:Uncategorized` (negative amounts) or `Income:Uncategorized`
  (zero or positive). Categories are created in the book's currency. Importing into an account in
  another currency fails with "unbalanced transaction".
- An empty description fails the whole import.
- `rule add` does not reject an empty pattern, which then matches everything.

### Budgets

- `budget set` needs write access. The account must exist and be type `expense`. Setting it again
  replaces the amount.
- Negative budgets are accepted.
- Budget set does not check closed periods, because a budget is not a transaction.
- `actual` is the sum of signed posting amounts for the account and its children, by the transaction
  date in that month. There is no currency conversion.
- `report budget` needs no user and lists only accounts with a budget for that month. `remaining`
  can be negative.

### Recurring entries

- Names are stripped. An empty name and a duplicate name are errors.
- `--every` must be `monthly`, `weekly`, or `yearly`. The check is in the function, so the API gets
  the same check.
- `run` goes through recurring entries in creation order and occurrences in date order. Each
  occurrence is posted with the usual closed-period check. A closed-period hit rolls back the whole
  run.
- Occurrence k is computed from the original start, so a monthly entry starting on Jan 31 gives Feb 28,
  Mar 31, Apr 30, and never drifts.
- `recurring.run` is audited with the `--until` value exactly as typed, and only when something was
  created.

### Loans

- Rate is an annual percent. The monthly rate is `RATE / 1200`.
- Payment = cents(P × r / (1 − (1 + r)^−n)). With rate 0, payment = cents(P / n).
- Calculation uses a Decimal context with 50 digits of precision.
- Interest per row = cents(balance × r). The last row repays the remaining balance and ends at `0.00`.
  Its payment can differ from the level payment by a cent (for example 1000 at 12% over 12 months gives
  88.85 each month and 88.84 for the last).
- Validation: a bad principal is `bad principal: X`, a bad rate is `bad rate: X`, and a bad term is
  `bad months: X`. A zero or negative principal is rejected.
- The term is capped at `MAX_MONTHS = 1200` (100 years). The lead chose this cap in `fin/loans.py`,
  and it also keeps the schedule size bounded. A last payment after year 9999 is rejected.

### Customers, vendors, and invoices

- Customer and vendor terms are a non-negative whole number of days. Default is 30. Other values
  give `bad terms: X`.
- Each line is stored as text. Tax is cents(net × rate / 100). A line with no tax code has zero tax and
  a NULL code.
- The tax rate is read when the line is created and not stored on the line.
- Invoice numbers are `INV-YEAR-NNNN`. The year comes from the invoice date, and the sequence counts
  existing numbers with that year prefix.
- Issuing posts Receivable (+total), Sales income (−net), and Sales tax (−tax, only when nonzero).
- Payments need status `issued` or `partial`. The amount must be positive and not above the balance.
  The account must be an asset in the book currency. The status becomes `paid` at zero balance,
  otherwise `partial`.
- Aging excludes drafts. It counts invoices dated on or before `--at`, and sums only payments dated on
  or before `--at`. Buckets are `current` (not yet due), `1-30`, `31-60`, `61-90`, and `90+` days past
  due.
- `report aging --payables` reads bills directly and has no status filter, because bills have no draft
  state.

### Bills

- Bill references are unique per vendor. A repeated (vendor, reference) is an error.
- At least one line is required. Line accounts must exist, be expense or asset accounts, and use the
  book currency. Tax codes must exist. Line amounts are not checked for sign.
- `Assets:TaxReceivable` is created only when the bill has tax. `Liabilities:Payable` is always
  created.
- Payments need status `open` or `partial`. The amount must be positive and not above the balance. The
  account must be an asset in the book currency. Payment dates are not checked against bill dates.
- Status becomes `paid` at zero balance, otherwise `partial`.
- Line positions are 0-based.
- Read commands need no user.

### Taxes

- `tax add` stores the rate as given after validation. Duplicate codes are an error.
- `report tax` collected covers invoice lines that are not draft (issued, partial, or paid). Paid covers
  all bill lines. Both are dated within the period, inclusive.
- A tax code appears in `by_code` when a line in the period uses it, even at zero tax.
- Amounts are summed as stored, without currency conversion.
- `--from` after `--to` is a user error. The spec does not cover this case.
- Read-only: no user and no audit entry.

### Reconciliation and statements

- Income is shown as positive. Expenses are shown as positive. `net` = income − expenses.
- Income and expense reports convert at the `--to` date. The balance sheet converts at `--at`.
- Accounts with postings in range but a zero total are listed with `0.00`.
- `networth` returns `[]` when `--from` is after `--to`. A malformed month is a user error.
- Per-account rounding happens before totals are summed. In a multi-currency book, total assets can
  differ from liabilities plus equity by one cent.
- `retained_earnings` = income − expenses through `--at`, across all periods. No closing entries are
  written.
- `reconcile --clear ID` marks every posting to the reconciled account in that transaction. Clearing
  an already-cleared transaction is a no-op. Reconciliation is not blocked by closed periods, because
  clearing marks are not postings.
- `cleared_balance` and `uncleared` match the reconciled account exactly, not its children.
- `ledger` runs from `--from` to `--to`. The opening balance and rows include the account and its
  children. Ordering is date, then transaction, then posting. `--from` after `--to` is a user error.

### Periods, users, and audit

- `period close` moves the closed-through month forward. Closing an earlier or equal month returns the
  current value and writes no audit entry.
- Postings dated on or before the closed-through month are rejected.
- Every write adds an audit entry with the user, the time (UTC), an action, and a target.
  Actions are: `init`, `account.add`, `fx.add`, `txn.add`, `import`, `rule.add`, `budget.set`,
  `recurring.add`, `recurring.run`, `tax.add`, `customer.add`, `invoice.create`, `invoice.issue`,
  `invoice.pay`, `vendor.add`, `bill.create`, `bill.pay`, `reconcile`, `period.close`, and `user.add`.
  `recurring.run` is written only when it creates something.

### CLI and API

- `main(argv=None, modules=None)` is the entry point. `modules` is an optional list of module names,
  used by tests. Command modules are named `fin.<name>`.
- When a handler returns nothing, the CLI prints nothing. A stopped `serve` therefore prints nothing,
  not `null`.
- `serve` binds to `127.0.0.1`. Port 0 picks a free port (used in tests).

## Tests

From the repository root:

```
python3 -m unittest discover -s tests
```

The suite has unit tests for each module (`tests/test_*.py`) and end-to-end tests in
`tests/test_e2e.py`. The end-to-end tests run `python3 -m fin` in a subprocess against a temporary
database and check the spec's examples. They also test the API on a free port in a thread. The
end-to-end module takes about 20 seconds.
