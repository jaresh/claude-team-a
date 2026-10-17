# Spec (user's request, sections 1-17; global conventions first)

Python 3.12+, standard library only: sqlite3, decimal.Decimal for money (never float), http.server, unittest.
Package `fin/`, run as `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`. Global options before the command. `--db` default `./fin.db`. With `--json`, exactly one JSON document to stdout.
Exit 0 on success. A user error (bad input, unbalanced txn, unknown account, missing rate, missing permission, closed period, ...) exits 2, message to stderr, nothing to stdout, changes nothing.
Amounts in JSON are strings with exactly two decimals ("-12.50", "0.00"); zero always "0.00" never "-0.00". Rounding half up to cents. Dates YYYY-MM-DD, months YYYY-MM.

## 1. Books and accounts
- `init --currency CUR --admin NAME`; account names colon paths, first segment Assets/Liabilities/Equity/Income/Expenses. `account add NAME [--currency CUR]` creates missing parents (same currency). `account list` -> [{"name","type","currency"}] sorted by name.
## 2. Transactions
- `txn add --date --desc --posting ACCOUNT=AMOUNT ...` (one posting may omit amount). Returns {"id","date","description","postings":[{"account","amount","currency"}]}. `txn list [--account PREFIX] [--from] [--to]` ordered by date, id.
## 3. Balances
- `balance [--at DATE]` -> {"Assets:Bank": {"EUR": "100.00"}}, ancestors included, raw signs.
## 4. Exchange rates
- `fx add DATE FROM TO RATE`; `convert AMOUNT FROM TO --at DATE` -> {"amount","currency"}; most recent rate on/before DATE, FROM->TO else 1/(TO->FROM); same currency 1:1; none = user error.
## 5. Bank statement import and rules
- `rule add PATTERN ACCOUNT`: case-insensitive regex matched (search) against the description. `rule list` -> [{"pattern","account"}] in order added.
- `import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]` CSV (0-based; defaults date 0, desc 1, amount 2; dates YYYY-MM-DD; amounts like -12.50). Each row becomes a transaction on that date, with the row's description, between ACCOUNT (the row's amount) and a category account (opposite amount): account of the first rule whose pattern matches, else `Expenses:Uncategorized` for negative, `Income:Uncategorized` for positive (created if missing, book currency). A row identical to one already imported into the same ACCOUNT (same date, description, amount) is skipped, including repeats within one file. -> {"imported": N, "skipped": M}.
## 6. Budgets
- `budget set ACCOUNT MONTH AMOUNT` (expense account; set or replace). `report budget MONTH` -> [{"account","budget","actual","remaining"}] one per account with a budget that month, sorted by account. actual = sum of that month's postings to the account and its descendants. remaining = budget - actual.
## 7. Recurring transactions
- `recurring add NAME --every monthly|weekly|yearly --start DATE --posting ACCOUNT=AMOUNT ...` same posting rules as txn add, checked when added.
- `recurring run --until DATE` creates every occurrence from start up to DATE inclusive not created yet, as transactions whose description is NAME; running again creates nothing new. Monthly keeps the start's day of month, last day of shorter months (Jan 31 -> Feb 28/29 -> Mar 31 -> Apr 30); weekly +7 days; yearly keeps month and day (Feb 29 -> Feb 28 in non-leap years). -> {"created": N}.
## 8. Reports
Amounts in the book's currency, or `--currency CUR`, converted at the report's date (`--to` or `--at`) as `convert` does; missing rate = user error. Reports show income, liabilities, equity as positive numbers (negated raw balance). Accounts appear by the name the postings are on, only if they have postings in the report's range (an account whose postings sum to zero shows "0.00").
- `report income --from DATE --to DATE [--currency CUR]` -> {"income": {"Income:Salary": "3000.00"}, "expenses": {"Expenses:Rent": "900.00"}, "total_income","total_expenses","net"} for postings in the period.
- `report balance-sheet --at DATE [--currency CUR]` -> {"assets": {...}, "liabilities": {...}, "equity": {...}, "retained_earnings", "total_assets", "total_liabilities", "total_equity"} postings on or before DATE. retained_earnings = all income minus all expenses up to DATE; total_equity includes it, so total_assets = total_liabilities + total_equity.
- `report networth --from MONTH --to MONTH` -> [{"month","assets","liabilities","networth"}] one per month, as of the month's last day.
## 9. Loans
- `loan schedule PRINCIPAL RATE MONTHS --start DATE` (RATE annual percent, 6 = 6%) -> {"payment","total_interest","rows":[{"n","date","payment","interest","principal","balance"}]}. r = RATE/1200; payment = PRINCIPAL*r/(1-(1+r)^-MONTHS) rounded to cents (RATE 0: PRINCIPAL/MONTHS rounded). Each month interest = round(balance*r), principal = payment - interest. Last row repays the remaining balance (its payment = that balance + its interest), final balance "0.00". Row n's date = start plus n months by the monthly rule of section 7.
## 10. HTTP API
`python -m fin [--db PATH] serve --port N` serves JSON until stopped, same documents as `--json` output:
- GET /accounts, GET /transactions, GET /balances?at=DATE, GET /reports/income?from=DATE&to=DATE, GET /reports/balance-sheet?at=DATE
- POST /transactions body {"date","description","postings":[{"account","amount"}]} (amount may be left out on one) -> 201 and the transaction; user error -> 400 {"error": "..."}.
- Unknown paths 404.
- Every POST needs header X-User: NAME. Missing/unknown user -> 401, role may not do it -> 403, both {"error"}. GET needs no user.
- Also GET /invoices, GET /invoices/ID, POST /invoices (body {"customer","date","lines":[{"description","quantity","price","tax_code"}]}, tax_code optional) -> 201 draft invoice, POST /invoices/ID/issue -> 200 invoice, POST /invoices/ID/payments (body {"amount","date","account"}) -> 200 invoice, GET /reports/aging?at=DATE (add &payables=1 for bills), GET /audit.
## 11. Users, roles, audit
- Roles: admin (everything), editor (everything except `user add` and `period close`), viewer (only commands that change nothing).
- `user add NAME --role`, `user list`, every data-changing command needs --user. Audit actions/targets: init (currency), user.add (name), account.add (name), txn.add (id), fx.add (FROM/TO), rule.add (pattern), import (account), budget.set ("ACCOUNT MONTH"), recurring.add (name), recurring.run (the --until date), period.close (month), tax.add (code), customer.add, vendor.add (name), invoice.create, invoice.issue, invoice.pay, bill.create, bill.pay (the invoice or bill id), reconcile (the account). Targets are strings. `audit list [--by NAME]`.
## 12. Closed periods
- `period close MONTH`, `period status`. Anything that would post a transaction dated in a closed month is a user error: txn add, import (any row closed -> whole import fails, nothing imported), recurring run (likewise), invoice issue, invoice pay, bill create, bill pay.
## 13. Tax codes, customers, invoices
- `tax add CODE RATE` (percent e.g. 20); `tax list` -> [{"code":"VAT20","rate":"20"}] sorted by code, rates as given.
- `customer add NAME [--terms DAYS]` (default 30); `customer list` -> [{"name":"Acme","terms":30}] sorted by name.
- `invoice create --customer NAME --date DATE --line "DESCRIPTION;QUANTITY;PRICE;TAXCODE" [--line ...]` (TAXCODE may be empty = no tax) creates a draft:
  {"id":1,"number":null,"customer":"Acme","date":"2026-01-10","due":"2026-02-09","status":"draft","lines":[{"description":"Consulting","quantity":"10","price":"95.00","tax_code":"VAT20","net":"950.00","tax":"190.00"}],"net":"950.00","tax":"190.00","total":"1140.00","paid":"0.00","balance":"1140.00"}
  Per line net = round(quantity*price), tax = round(net*rate/100); quantity shown as given, tax_code null without tax. Invoice net/tax/total(net+tax) are sums over lines; due = date + customer's terms days; balance = total - paid. Unknown customer or tax code = user error.
- `invoice issue ID` gives a draft number INV-YYYY-NNNN (YYYY the invoice date's year; NNNN 0001 for the first invoice issued with that year, then 0002...), status issued, posts one transaction dated the invoice date, description `Invoice INV-...`: Assets:Receivable +total, Income:Sales -net, Liabilities:SalesTax -tax if tax not zero (accounts created if missing, book currency). Issuing a non-draft = user error.
- `invoice pay ID AMOUNT --date DATE --account ACCOUNT` (an asset account) posts description `Payment INV-...`: ACCOUNT +AMOUNT, Assets:Receivable -AMOUNT. Status becomes partial, or paid once balance zero. Paying a draft, a paid invoice, or more than the balance = user error.
- `invoice show ID` -> invoice; `invoice list [--status STATUS]` ordered by id. Every successful invoice command prints the invoice.
- `report aging --at DATE` -> {"current","1-30","31-60","61-90","90+","total"}: the balances, as of DATE, of issued invoices dated on or before DATE, counting only payments dated on or before DATE, bucketed by days past due (DATE - due; zero or less = current). Invoices with nothing left to pay are left out.
## 14. Vendors and bills
- `vendor add NAME [--terms DAYS]` (default 30); `vendor list` like customer list.
- `bill create --vendor NAME --ref TEXT --date DATE --line "DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE" [--line ...]`: AMOUNT is the line's net; ACCOUNT must be an existing expense or asset account; tax per line = round(net*rate/100). A vendor's --ref must be unique. Posted at once, dated DATE, description `Bill REF`: each line's ACCOUNT +net, Assets:TaxReceivable +the bill's tax if not zero, Liabilities:Payable -total (accounts created if missing).
  -> {"id":1,"vendor":"Office Ltd","ref":"A-17","date":"...","due":"...","status":"open","lines":[{"description","account","tax_code","net","tax"}],"net","tax","total","paid":"0.00","balance"}
- `bill pay ID AMOUNT --date DATE --account ACCOUNT` posts Liabilities:Payable +AMOUNT, ACCOUNT -AMOUNT, description `Payment REF`; status partial or paid as invoices, same errors. `bill show ID`, `bill list [--status STATUS]`.
- `report aging --at DATE --payables`: same report for bills.
## 15. Tax report
- `report tax --from DATE --to DATE` -> {"collected","paid","net","by_code":{"VAT20":{"collected","paid"}}}: collected = tax of issued invoices dated in the period, paid = tax of bills dated in the period, net = collected - paid. by_code has every tax code used in the period.
## 16. Bank reconciliation
- `reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID ...]` marks the given transactions cleared for ACCOUNT (each must have a posting to ACCOUNT dated on or before DATE, else user error and nothing marked) and reports {"account","date","statement_balance","cleared_balance","difference","uncleared":[ids]}. cleared_balance = sum of ACCOUNT's cleared postings dated on or before DATE; difference = statement - cleared; uncleared lists ascending the txns with a posting to ACCOUNT on/before DATE not cleared. Cleared marks kept for later runs.
## 17. Ledger reports
- `report trial-balance --at DATE` -> {"rows":[{"account","debit","credit"}],"total_debit","total_credit"}: one row per account with postings on/before DATE (by the name the postings are on, sorted), raw balance in book currency (converted at DATE as in section 8): positive = debit, negative = credit (positive number), other side "0.00". Totals equal.
- `report ledger ACCOUNT --from DATE --to DATE` -> {"account","opening","rows":[{"date","id","description","amount","balance"}],"closing"} in ACCOUNT's currency: opening = balance of ACCOUNT and descendants before FROM, then one row per posting to them in the period (by date, id) with running balance; closing = last balance (or the opening).
