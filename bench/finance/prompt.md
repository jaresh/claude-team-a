Build a personal and small-business finance system in this repository (it is empty). {{MODE}}

Write tests as you go and make sure they pass. No one will answer questions while you work: where something below is not specified, decide, and list your assumptions in README.md. When everything is done, write the current UTC time (`date -u +%FT%TZ`) to a file named `.bench-end` in the repository root. That must be your last action.

## Stack and conventions

- Python 3.12+, standard library only (no pip installs): `sqlite3` for storage, `decimal.Decimal` for money (never float), `http.server` for the API, `unittest` for tests.
- A package `fin/`, run as `python -m fin [--db PATH] [--json] COMMAND ...`. Global options come before the command. `--db` defaults to `./fin.db`. With `--json`, a command prints exactly one JSON document to stdout.
- Exit code 0 on success. A user error (bad input, unbalanced transaction, unknown account, missing exchange rate, ...) exits with code 2, prints a message to stderr and nothing to stdout.
- Amounts in JSON are strings with exactly two decimals (`"-12.50"`, `"0.00"`); zero is always `"0.00"`, never `"-0.00"`. Rounding is half up to cents. Dates are `YYYY-MM-DD`, months `YYYY-MM`.

## 1. Books and accounts

- `init --currency CUR` creates the database with a default currency (a 3-letter code). Running it on an existing database is a user error.
- Account names are colon paths whose first segment sets the type: `Assets` (asset), `Liabilities` (liability), `Equity` (equity), `Income` (income), `Expenses` (expense). Any other first segment is a user error.
- `account add NAME [--currency CUR]` (default: the book's currency) creates the account and any missing parents (new parents get the same currency). Adding an existing account is a user error.
- `account list` → `[{"name": "Assets", "type": "asset", "currency": "EUR"}, ...]`: all accounts, sorted by name.

## 2. Transactions

- `txn add --date DATE --desc TEXT --posting ACCOUNT=AMOUNT [--posting ...]`: two or more postings; a posting's currency is its account's currency. At most one posting may be just `ACCOUNT` with no amount: it gets the amount that balances the transaction. The postings of each currency must sum to zero, otherwise it is a user error. An unknown account is a user error (transactions never create accounts).
  → `{"id": 1, "date": "2026-01-05", "description": "Rent", "postings": [{"account": "Expenses:Rent", "amount": "900.00", "currency": "EUR"}, {"account": "Assets:Bank", "amount": "-900.00", "currency": "EUR"}]}`. Ids start at 1 and increase; postings keep the order given.
- `txn list [--account PREFIX] [--from DATE] [--to DATE]` → a list of transactions in that shape, ordered by date, then id. `--account` keeps transactions with a posting to that account or one of its descendants; `--from` and `--to` are inclusive.

## 3. Balances

- `balance [--at DATE]` → `{"Assets:Bank": {"EUR": "100.00"}, ...}`: for every account with postings on or before DATE (default: all postings), and every ancestor of such an account, the signed sum per currency of the postings to that account and its descendants. Raw signs: debits are positive, credits negative, so income and liability balances are usually negative.

## 4. Exchange rates

- `fx add DATE FROM TO RATE` stores "1 FROM = RATE TO" from DATE on (RATE is a decimal string).
- `convert AMOUNT FROM TO --at DATE` → `{"amount": "...", "currency": "TO"}`, using the most recent rate on or before DATE: the FROM→TO rate if there is one, otherwise 1 / the TO→FROM rate. The same currency converts 1:1. No usable rate is a user error.

## 5. Bank statement import and rules

- `rule add PATTERN ACCOUNT`: a case-insensitive regular expression matched against the description. `rule list` → `[{"pattern": "...", "account": "..."}]` in the order added.
- `import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]` reads a CSV file (0-based columns; defaults: date 0, description 1, amount 2; dates `YYYY-MM-DD`; amounts like `-12.50`). Each row becomes a transaction on that date, with the row's description, between ACCOUNT (the row's amount) and a category account (the opposite amount): the account of the first rule whose pattern matches, otherwise `Expenses:Uncategorized` for a negative amount and `Income:Uncategorized` for a positive one (created if missing, in the book's currency). A row identical to one already imported into the same ACCOUNT (same date, description and amount) is skipped, including repeats within one file.
  → `{"imported": N, "skipped": M}`.

## 6. Budgets

- `budget set ACCOUNT MONTH AMOUNT` sets, or replaces, an expense account's budget for a month.
- `report budget MONTH` → `[{"account": "Expenses:Food", "budget": "300.00", "actual": "250.50", "remaining": "49.50"}, ...]`: one entry per account with a budget that month, sorted by account. `actual` is the sum of that month's postings to the account and its descendants.

## 7. Recurring transactions

- `recurring add NAME --every monthly|weekly|yearly --start DATE --posting ACCOUNT=AMOUNT [--posting ...]`: the same posting rules as `txn add`, checked when added.
- `recurring run --until DATE` creates every occurrence from the start up to DATE (inclusive) that has not been created yet, as transactions whose description is NAME; running it again creates nothing new. Monthly keeps the start's day of month, using the last day of shorter months (Jan 31 → Feb 28 or 29 → Mar 31 → Apr 30); weekly adds 7 days; yearly keeps month and day (Feb 29 → Feb 28 in non-leap years).
  → `{"created": N}`.

## 8. Reports

Report amounts are in the book's currency, or in `--currency CUR`, converted at the report's date (`--to` or `--at`) as `convert` does; a missing rate is a user error. Reports show income, liabilities and equity as positive numbers (the negated raw balance). Accounts appear by the name the postings are on, and only if they have postings in the report's range (an account whose postings sum to zero shows `"0.00"`).

- `report income --from DATE --to DATE [--currency CUR]` → `{"income": {"Income:Salary": "3000.00"}, "expenses": {"Expenses:Rent": "900.00"}, "total_income": "3000.00", "total_expenses": "900.00", "net": "2100.00"}` for postings in the period.
- `report balance-sheet --at DATE [--currency CUR]` → `{"assets": {...}, "liabilities": {...}, "equity": {...}, "retained_earnings": "...", "total_assets": "...", "total_liabilities": "...", "total_equity": "..."}` for postings on or before DATE. `retained_earnings` is all income minus all expenses up to DATE; `total_equity` includes it, so `total_assets` = `total_liabilities` + `total_equity`.
- `report networth --from MONTH --to MONTH` → `[{"month": "2026-01", "assets": "...", "liabilities": "...", "networth": "..."}, ...]`: one entry per month, as of the month's last day.

## 9. Loans

- `loan schedule PRINCIPAL RATE MONTHS --start DATE` (RATE: annual percent, `6` means 6%) → `{"payment": "...", "total_interest": "...", "rows": [{"n": 1, "date": "...", "payment": "...", "interest": "...", "principal": "...", "balance": "..."}, ...]}`.
  The monthly rate is r = RATE / 1200; payment = PRINCIPAL · r / (1 − (1 + r)^−MONTHS), rounded to cents (with RATE 0: PRINCIPAL / MONTHS, rounded). Each month, interest = round(balance · r) and principal = payment − interest. The last row repays the remaining balance (its payment = that balance + its interest), so the final balance is `"0.00"`. Row n's date is the start plus n months, by the monthly rule of section 7.

## 10. HTTP API

`python -m fin [--db PATH] serve --port N` serves JSON until it is stopped, with the same documents as the commands' `--json` output:

- `GET /accounts`, `GET /transactions`, `GET /balances?at=DATE`, `GET /reports/income?from=DATE&to=DATE`, `GET /reports/balance-sheet?at=DATE`
- `POST /transactions` with the body `{"date": "...", "description": "...", "postings": [{"account": "...", "amount": "..."}]}` (one posting may leave out `amount`) → 201 and the transaction; a user error → 400 and `{"error": "..."}`.
- Unknown paths → 404.

## Done

`python -m unittest discover -s tests` passes, and README.md explains how to use the system and lists your assumptions.
