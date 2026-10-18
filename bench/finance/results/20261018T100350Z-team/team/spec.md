# The user's request, word for word (their messages in this session, oldest first)

Build a small-business finance system in this repository (it is empty). Work with team on it.

Write tests as you go and make sure they pass. No one will answer questions while you work: where something below is not specified, decide, and list your assumptions in README.md. When everything is done, write the current UTC time (`date -u +%FT%TZ`) to a file named `.bench-end` in the repository root. That must be your last action.

## Stack and conventions

- Python 3.12+, standard library only (no pip installs): `sqlite3` for storage, `decimal.Decimal` for money (never float), `http.server` for the API, `unittest` for tests.
- A package `fin/`, run as `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`. Global options come before the command. `--db` defaults to `./fin.db`. With `--json`, a command prints exactly one JSON document to stdout. `--user` names the acting user (section 11).
- Exit code 0 on success. A user error (bad input, unbalanced transaction, unknown account, missing exchange rate, missing permission, closed period, ...) exits with code 2, prints a message to stderr and nothing to stdout, and changes nothing.
- Amounts in JSON are strings with exactly two decimals (`"-12.50"`, `"0.00"`); zero is always `"0.00"`, never `"-0.00"`. Rounding is half up to cents. Dates are `YYYY-MM-DD`, months `YYYY-MM`.

## 1. Books and accounts

- `init --currency CUR --admin NAME` creates the database with a default currency (a 3-letter code) and its first user, NAME, with the role `admin`. It needs no `--user`. Running it on an existing database is a user error.
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
- Section 11 applies to the API too: every `POST` needs the header `X-User: NAME`. A missing or unknown user → 401, a role that may not do it → 403, both with `{"error": "..."}`. `GET` requests need no user.
- Also: `GET /invoices`, `GET /invoices/ID`, `POST /invoices` (body: `{"customer": "...", "date": "...", "lines": [{"description": "...", "quantity": "...", "price": "...", "tax_code": "..."}]}`, `tax_code` optional) → 201 and the draft invoice, `POST /invoices/ID/issue` → 200 and the invoice, `POST /invoices/ID/payments` (body: `{"amount": "...", "date": "...", "account": "..."}`) → 200 and the invoice, `GET /reports/aging?at=DATE` (add `&payables=1` for bills), `GET /audit`.

## 11. Users, roles and audit log

- Roles: `admin` (everything), `editor` (everything except `user add` and `period close`), `viewer` (only commands that change nothing).
- `user add NAME --role admin|editor|viewer` (admin only); adding an existing user is a user error. `user list` → `[{"name": "alice", "role": "admin"}, ...]`, sorted by name.
- Every command that changes data needs `--user`: a missing or unknown user, or a role that may not run the command, is a user error. Commands that only read work with or without `--user`.
- Every successful command that changes data appends one audit entry. `audit list [--by NAME]` (only that user's entries) → `[{"seq": 1, "at": "<UTC time, ISO 8601>", "user": "alice", "action": "init", "target": "EUR"}, ...]`, oldest first, with exactly those keys. `init` is entry 1. Actions and targets: `init` (the currency), `user.add` (the name), `account.add` (the name), `txn.add` (the id), `fx.add` (`FROM/TO`), `rule.add` (the pattern), `import` (the account), `budget.set` (`ACCOUNT MONTH`), `recurring.add` (the name), `recurring.run` (the `--until` date), `period.close` (the month), `tax.add` (the code), `customer.add` and `vendor.add` (the name), `invoice.create`, `invoice.issue`, `invoice.pay`, `bill.create`, `bill.pay` (the invoice or bill id), `reconcile` (the account). Targets are strings.

## 12. Closed periods

- `period close MONTH` (admin only) closes that month and every earlier one. `period status` → `{"closed_through": "2026-01"}` (`null` when nothing is closed). Closing a month earlier than one already closed changes nothing.
- Anything that would post a transaction dated in a closed month is a user error: `txn add`, `import` (if any row is in a closed month, the whole import fails and nothing is imported), `recurring run` (likewise), `invoice issue`, `invoice pay`, `bill create`, `bill pay`.

## 13. Tax codes, customers and invoices

- `tax add CODE RATE` (RATE in percent, e.g. `20`); `tax list` → `[{"code": "VAT20", "rate": "20"}, ...]`, sorted by code, rates shown as given.
- `customer add NAME [--terms DAYS]` (payment terms, default 30); `customer list` → `[{"name": "Acme", "terms": 30}, ...]`, sorted by name.
- `invoice create --customer NAME --date DATE --line "DESCRIPTION;QUANTITY;PRICE;TAXCODE" [--line ...]` (TAXCODE may be empty: no tax) creates a draft invoice:
  `{"id": 1, "number": null, "customer": "Acme", "date": "2026-01-10", "due": "2026-02-09", "status": "draft", "lines": [{"description": "Consulting", "quantity": "10", "price": "95.00", "tax_code": "VAT20", "net": "950.00", "tax": "190.00"}], "net": "950.00", "tax": "190.00", "total": "1140.00", "paid": "0.00", "balance": "1140.00"}`.
  Per line, net = round(quantity × price) and tax = round(net × rate / 100); `quantity` is shown as given, `tax_code` is `null` without tax. The invoice's `net`, `tax` and `total` (net + tax) are sums over its lines; `due` is the date plus the customer's terms in days; `balance` = `total` − `paid`. An unknown customer or tax code is a user error.
- `invoice issue ID` gives a draft its number, `INV-YYYY-NNNN` (YYYY: the invoice date's year; NNNN: 0001 for the first invoice issued with that year, then 0002, ...), sets status `issued`, and posts one transaction dated on the invoice date, description `Invoice INV-...`: `Assets:Receivable` +total, `Income:Sales` −net, and `Liabilities:SalesTax` −tax if the tax isn't zero (these accounts are created if missing, in the book's currency). Issuing an invoice that isn't a draft is a user error.
- `invoice pay ID AMOUNT --date DATE --account ACCOUNT` (an asset account) posts a transaction, description `Payment INV-...`: ACCOUNT +AMOUNT, `Assets:Receivable` −AMOUNT. The status becomes `partial`, or `paid` once the balance is zero. Paying a draft, a paid invoice, or more than the balance is a user error.
- `invoice show ID` → the invoice; `invoice list [--status STATUS]` → invoices ordered by id. Every invoice command that succeeds prints the invoice.
- `report aging --at DATE` → `{"current": "...", "1-30": "...", "31-60": "...", "61-90": "...", "90+": "...", "total": "..."}`: the balances, as of DATE, of issued invoices dated on or before DATE, counting only payments dated on or before DATE, put in buckets by days past due (DATE − due; zero or less is `current`). Invoices with nothing left to pay are left out.

## 14. Vendors and bills

- `vendor add NAME [--terms DAYS]` (default 30); `vendor list`, like `customer list`.
- `bill create --vendor NAME --ref TEXT --date DATE --line "DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE" [--line ...]`: AMOUNT is the line's net; ACCOUNT must be an existing expense or asset account; tax per line = round(net × rate / 100). A vendor's `--ref` must be unique. The bill is posted at once, dated DATE, description `Bill REF`: each line's ACCOUNT +net, `Assets:TaxReceivable` +the bill's tax if not zero, `Liabilities:Payable` −total (accounts created if missing).
  → `{"id": 1, "vendor": "Office Ltd", "ref": "A-17", "date": "...", "due": "...", "status": "open", "lines": [{"description": "...", "account": "...", "tax_code": "VAT20", "net": "...", "tax": "..."}], "net": "...", "tax": "...", "total": "...", "paid": "0.00", "balance": "..."}`.
- `bill pay ID AMOUNT --date DATE --account ACCOUNT` posts `Liabilities:Payable` +AMOUNT, ACCOUNT −AMOUNT, description `Payment REF`; status `partial` or `paid` as for invoices, and the same errors. `bill show ID`, `bill list [--status STATUS]`.
- `report aging --at DATE --payables`: the same report for bills.

## 15. Tax report

- `report tax --from DATE --to DATE` → `{"collected": "...", "paid": "...", "net": "...", "by_code": {"VAT20": {"collected": "...", "paid": "..."}, ...}}`: `collected` is the tax of issued invoices dated in the period, `paid` the tax of bills dated in the period, `net` = collected − paid. `by_code` has every tax code used in the period.

## 16. Bank reconciliation

- `reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID] [--clear ...]` marks the given transactions as cleared for ACCOUNT (one `--clear` per transaction, repeated like `--posting`; each must have a posting to ACCOUNT dated on or before DATE, else it is a user error and nothing is marked) and reports `{"account": "...", "date": "...", "statement_balance": "...", "cleared_balance": "...", "difference": "...", "uncleared": [ids]}`. `cleared_balance` is the sum of ACCOUNT's cleared postings dated on or before DATE; `difference` = statement − cleared; `uncleared` lists, ascending, the transactions with a posting to ACCOUNT dated on or before DATE that aren't cleared. Cleared marks are kept for later runs.

## 17. Ledger reports

- `report trial-balance --at DATE` → `{"rows": [{"account": "...", "debit": "...", "credit": "..."}, ...], "total_debit": "...", "total_credit": "..."}`: one row per account with postings on or before DATE (by the name the postings are on, sorted), its raw balance in the book's currency (converted at DATE as in section 8): a positive balance is a debit, a negative one a credit (as a positive number), the other side `"0.00"`. The totals are equal.
- `report ledger ACCOUNT --from DATE --to DATE` → `{"account": "...", "opening": "...", "rows": [{"date": "...", "id": 1, "description": "...", "amount": "...", "balance": "..."}, ...], "closing": "..."}` in ACCOUNT's currency: `opening` is the balance of ACCOUNT and its descendants before FROM, then one row per posting to them in the period (by date, then id) with the running balance; `closing` is the last balance (or the opening one).

## Done

`python -m unittest discover -s tests` passes and covers every section, and README.md explains how to use the system and lists your assumptions.
