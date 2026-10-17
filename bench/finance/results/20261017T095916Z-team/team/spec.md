# SPEC (verbatim from the user)
Conventions: Python 3.12+, stdlib only; sqlite3, decimal.Decimal (never float), http.server, unittest. Package `fin/`, run as `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`. With `--json` a command prints exactly one JSON document to stdout. Exit 0 on success. A user error (bad input, unbalanced txn, unknown account, missing exchange rate, missing permission, closed period, ...) exits 2, prints message to stderr and nothing to stdout, changes nothing. Amounts in JSON are strings with exactly two decimals ("-12.50","0.00"); zero always "0.00". Rounding half up to cents. Dates YYYY-MM-DD, months YYYY-MM.

## 4. Exchange rates
- `fx add DATE FROM TO RATE` stores "1 FROM = RATE TO" from DATE on.
- `convert AMOUNT FROM TO --at DATE` → {"amount": "...", "currency": "TO"}, using the most recent rate on or before DATE: FROM→TO rate if there is one, otherwise 1 / the TO→FROM rate. Same currency converts 1:1. No usable rate is a user error.

## 5. Bank statement import and rules
- `rule add PATTERN ACCOUNT`: case-insensitive regex matched against the description. `rule list` → [{"pattern": "...", "account": "..."}] in order added.
- `import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]` reads a CSV (0-based columns; defaults date 0, description 1, amount 2; dates YYYY-MM-DD; amounts like -12.50). Each row becomes a transaction on that date, with the row's description, between ACCOUNT (the row's amount) and a category account (the opposite amount): the account of the first rule whose pattern matches, otherwise `Expenses:Uncategorized` for a negative amount and `Income:Uncategorized` for a positive one (created if missing, in the book's currency). A row identical to one already imported into the same ACCOUNT (same date, description and amount) is skipped, including repeats within one file. → {"imported": N, "skipped": M}.

## 6. Budgets
- `budget set ACCOUNT MONTH AMOUNT` sets or replaces an expense account's budget for a month.
- `report budget MONTH` → [{"account": "Expenses:Food", "budget": "300.00", "actual": "250.50", "remaining": "49.50"}, ...]: one entry per account with a budget that month, sorted by account. actual = sum of that month's postings to the account and its descendants.

## 7. Recurring transactions
- `recurring add NAME --every monthly|weekly|yearly --start DATE --posting ACCOUNT=AMOUNT [--posting ...]`: same posting rules as txn add, checked when added.
- `recurring run --until DATE` creates every occurrence from the start up to DATE (inclusive) not yet created, as transactions whose description is NAME; running again creates nothing new. Monthly keeps the start's day of month, using last day of shorter months (Jan 31 → Feb 28/29 → Mar 31 → Apr 30); weekly adds 7 days; yearly keeps month and day (Feb 29 → Feb 28 in non-leap years). → {"created": N}.

## 8. Reports
Report amounts are in the book's currency, or in `--currency CUR`, converted at the report's date (`--to` or `--at`) as `convert` does; a missing rate is a user error. Reports show income, liabilities and equity as positive numbers (the negated raw balance). Accounts appear by the name the postings are on, and only if they have postings in the report's range (an account whose postings sum to zero shows "0.00").
- `report income --from DATE --to DATE [--currency CUR]` → {"income": {"Income:Salary": "3000.00"}, "expenses": {"Expenses:Rent": "900.00"}, "total_income": "3000.00", "total_expenses": "900.00", "net": "2100.00"} for postings in the period.
- `report balance-sheet --at DATE [--currency CUR]` → {"assets": {...}, "liabilities": {...}, "equity": {...}, "retained_earnings": "...", "total_assets": "...", "total_liabilities": "...", "total_equity": "..."} for postings on or before DATE. retained_earnings = all income minus all expenses up to DATE; total_equity includes it, so total_assets = total_liabilities + total_equity.
- `report networth --from MONTH --to MONTH` → [{"month": "2026-01", "assets": "...", "liabilities": "...", "networth": "..."}, ...]: one entry per month, as of the month's last day.

## 9. Loans
- `loan schedule PRINCIPAL RATE MONTHS --start DATE` (RATE annual percent, 6 means 6%) → {"payment": "...", "total_interest": "...", "rows": [{"n": 1, "date": "...", "payment": "...", "interest": "...", "principal": "...", "balance": "..."}, ...]}.
  Monthly rate r = RATE/1200; payment = PRINCIPAL·r/(1−(1+r)^−MONTHS), rounded to cents (RATE 0: PRINCIPAL/MONTHS, rounded). Each month interest = round(balance·r), principal = payment − interest. The last row repays the remaining balance (its payment = that balance + its interest), so final balance is "0.00". Row n's date is start plus n months, by the monthly rule of section 7.

## 10. HTTP API
`python -m fin [--db PATH] serve --port N` serves JSON until stopped, same documents as the commands' --json output:
- GET /accounts, GET /transactions, GET /balances?at=DATE, GET /reports/income?from=DATE&to=DATE, GET /reports/balance-sheet?at=DATE
- POST /transactions body {"date","description","postings":[{"account","amount"}]} (one posting may omit amount) → 201 and the transaction; user error → 400 {"error": "..."}.
- Unknown paths → 404.
- Section 11 applies: every POST needs header `X-User: NAME`. Missing or unknown user → 401, role may not → 403, both {"error": "..."}. GET needs no user.
- Also: GET /invoices, GET /invoices/ID, POST /invoices (body {"customer","date","lines":[{"description","quantity","price","tax_code"}]}, tax_code optional) → 201 and the draft invoice, POST /invoices/ID/issue → 200 and invoice, POST /invoices/ID/payments (body {"amount","date","account"}) → 200 and invoice, GET /reports/aging?at=DATE (add &payables=1 for bills), GET /audit.

## 11. Users, roles, audit
- Roles: admin (everything), editor (everything except `user add` and `period close`), viewer (only commands that change nothing).
- `user add NAME --role admin|editor|viewer` (admin only); existing user is a user error. `user list`.
- Every command that changes data needs --user (missing/unknown user or role not allowed = user error). Read-only commands work with or without.
- Every successful data-changing command appends one audit entry. Actions/targets: init (currency), user.add (name), account.add (name), txn.add (id), fx.add (FROM/TO), rule.add (pattern), import (the account), budget.set ("ACCOUNT MONTH"), recurring.add (name), recurring.run (the --until date), period.close (month), tax.add (code), customer.add / vendor.add (name), invoice.create, invoice.issue, invoice.pay, bill.create, bill.pay (the invoice or bill id), reconcile (the account). Targets are strings.

## 12. Closed periods
- `period close MONTH` closes that month and earlier. Anything that would post a transaction dated in a closed month is a user error: txn add, import (if any row is in a closed month the whole import fails, nothing imported), recurring run (likewise), invoice issue, invoice pay, bill create, bill pay.

## 13. Tax codes, customers, invoices
- `tax add CODE RATE` (percent, e.g. 20); `tax list` → [{"code": "VAT20", "rate": "20"}, ...] sorted by code, rates shown as given.
- `customer add NAME [--terms DAYS]` (default 30); `customer list` → [{"name": "Acme", "terms": 30}, ...] sorted by name.
- `invoice create --customer NAME --date DATE --line "DESCRIPTION;QUANTITY;PRICE;TAXCODE" [--line ...]` (TAXCODE may be empty: no tax) creates a draft:
  {"id": 1, "number": null, "customer": "Acme", "date": "2026-01-10", "due": "2026-02-09", "status": "draft", "lines": [{"description": "Consulting", "quantity": "10", "price": "95.00", "tax_code": "VAT20", "net": "950.00", "tax": "190.00"}], "net": "950.00", "tax": "190.00", "total": "1140.00", "paid": "0.00", "balance": "1140.00"}.
  Per line net = round(quantity × price), tax = round(net × rate / 100); quantity shown as given, tax_code null without tax. Invoice net, tax, total (net+tax) are sums over lines; due = date + customer's terms days; balance = total − paid. Unknown customer or tax code is a user error.
- `invoice issue ID` gives a draft its number INV-YYYY-NNNN (YYYY: invoice date's year; NNNN: 0001 for first invoice issued with that year, then 0002...), status issued, and posts one transaction dated on the invoice date, description `Invoice INV-...`: Assets:Receivable +total, Income:Sales −net, and Liabilities:SalesTax −tax if tax not zero (accounts created if missing, book's currency). Issuing a non-draft is a user error.
- `invoice pay ID AMOUNT --date DATE --account ACCOUNT` (an asset account) posts description `Payment INV-...`: ACCOUNT +AMOUNT, Assets:Receivable −AMOUNT. Status becomes partial, or paid once balance is zero. Paying a draft, a paid invoice, or more than the balance is a user error.
- `invoice show ID` → the invoice; `invoice list [--status STATUS]` ordered by id. Every invoice command that succeeds prints the invoice.
- `report aging --at DATE` → {"current","1-30","31-60","61-90","90+","total"}: the balances, as of DATE, of issued invoices dated on or before DATE, counting only payments dated on or before DATE, bucketed by days past due (DATE − due; ≤0 is current). Invoices with nothing left to pay are left out.

## 14. Vendors and bills
- `vendor add NAME [--terms DAYS]` (default 30); `vendor list` like customer list.
- `bill create --vendor NAME --ref TEXT --date DATE --line "DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE" [--line ...]`: AMOUNT is the line's net; ACCOUNT must be an existing expense or asset account; tax per line = round(net × rate/100). A vendor's --ref must be unique. Posted at once, dated DATE, description `Bill REF`: each line's ACCOUNT +net, Assets:TaxReceivable +the bill's tax if not zero, Liabilities:Payable −total (accounts created if missing).
  → {"id": 1, "vendor": "Office Ltd", "ref": "A-17", "date": "...", "due": "...", "status": "open", "lines": [{"description","account","tax_code","net","tax"}], "net","tax","total","paid": "0.00","balance"}.
- `bill pay ID AMOUNT --date DATE --account ACCOUNT` posts Liabilities:Payable +AMOUNT, ACCOUNT −AMOUNT, description `Payment REF`; status partial or paid as for invoices, same errors. `bill show ID`, `bill list [--status STATUS]`.
- `report aging --at DATE --payables`: same report for bills.

## 15. Tax report
- `report tax --from DATE --to DATE` → {"collected","paid","net","by_code": {"VAT20": {"collected","paid"}, ...}}: collected = tax of issued invoices dated in the period, paid = tax of bills dated in the period, net = collected − paid. by_code has every tax code used in the period.

## 16. Bank reconciliation
- `reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID ...]` marks the given transactions cleared for ACCOUNT (each must have a posting to ACCOUNT dated on or before DATE, else user error and nothing marked) and reports {"account","date","statement_balance","cleared_balance","difference","uncleared": [ids]}. cleared_balance = sum of ACCOUNT's cleared postings dated on or before DATE; difference = statement − cleared; uncleared lists, ascending, the transactions with a posting to ACCOUNT dated on or before DATE that aren't cleared. Cleared marks are kept for later runs.

## 17. Ledger reports
- `report trial-balance --at DATE` → {"rows": [{"account","debit","credit"}, ...], "total_debit","total_credit"}: one row per account with postings on or before DATE (by the name the postings are on, sorted), its raw balance in the book's currency (converted at DATE as in section 8): positive balance = debit, negative = credit (as a positive number), the other side "0.00". Totals are equal.
- `report ledger ACCOUNT --from DATE --to DATE` → {"account","opening","rows":[{"date","id","description","amount","balance"}, ...],"closing"} in ACCOUNT's currency: opening = balance of ACCOUNT and its descendants before FROM, then one row per posting to them in the period (by date, then id) with running balance; closing = last balance (or the opening one).
