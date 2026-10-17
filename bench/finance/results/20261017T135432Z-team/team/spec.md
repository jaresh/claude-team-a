# SPEC (user's request; amounts in JSON are strings with exactly two decimals ("-12.50","0.00"; never "-0.00"); rounding half up; dates YYYY-MM-DD, months YYYY-MM)
Python 3.12 stdlib only. Package fin/, `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`. With --json one JSON document to stdout. User error => exit 2, message on stderr, nothing on stdout, nothing changed.

## 1. Books and accounts
- init --currency CUR --admin NAME (done by lead). Account names: colon paths, first segment Assets/Liabilities/Equity/Income/Expenses (types asset/liability/equity/income/expense).
- account add NAME [--currency CUR] (default book currency) creates account and missing parents (same currency). Existing => user error.
- account list -> [{"name","type","currency"}] sorted by name.
## 2. Transactions
- txn add --date DATE --desc TEXT --posting ACCOUNT=AMOUNT [--posting ...]: 2+ postings; posting currency = account's currency. At most one posting may be just ACCOUNT (gets balancing amount). Each currency sums to zero else user error. Unknown account => user error (never creates accounts).
  -> {"id":1,"date":"2026-01-05","description":"Rent","postings":[{"account":"Expenses:Rent","amount":"900.00","currency":"EUR"},...]}. Ids from 1; postings keep order.
- txn list [--account PREFIX] [--from DATE] [--to DATE] -> list of txns ordered by date, id. --account keeps txns with a posting to that account or a descendant; from/to inclusive.
## 3. Balances
- balance [--at DATE] -> {"Assets:Bank":{"EUR":"100.00"},...}: every account with postings on/before DATE (default all) and every ancestor of such; signed sum per currency of postings to account and descendants. Raw signs (debit +, credit -).
## 4. FX
- fx add DATE FROM TO RATE: 1 FROM = RATE TO from DATE on.
- convert AMOUNT FROM TO --at DATE -> {"amount":"...","currency":"TO"} using most recent rate on/before DATE: FROM->TO if exists else 1/(TO->FROM). Same currency 1:1. None => user error.
## 5. Import and rules
- rule add PATTERN ACCOUNT: case-insensitive regex matched against description. rule list -> [{"pattern","account"}] in order added.
- import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]: CSV, 0-based cols (defaults 0,1,2), dates YYYY-MM-DD, amounts like -12.50. Each row => txn on that date, row's description, between ACCOUNT (row's amount) and a category account (opposite amount): account of first matching rule, else Expenses:Uncategorized (negative amount) / Income:Uncategorized (positive) (created if missing, book currency). A row identical to one already imported into the same ACCOUNT (same date, description, amount) is skipped, including repeats within one file. -> {"imported":N,"skipped":M}
## 6. Budgets
- budget set ACCOUNT MONTH AMOUNT (expense account; sets or replaces).
- report budget MONTH -> [{"account","budget","actual","remaining"}] one per account with a budget that month, sorted by account; actual = sum of that month's postings to account and descendants; remaining = budget - actual.
## 7. Recurring
- recurring add NAME --every monthly|weekly|yearly --start DATE --posting ACCOUNT=AMOUNT [--posting ...]: same posting rules as txn add, checked when added.
- recurring run --until DATE: creates every occurrence from start up to DATE inclusive not yet created, as txns with description NAME; rerun creates nothing new. Monthly keeps start's day of month, last day of shorter months (Jan31->Feb28/29->Mar31->Apr30); weekly +7 days; yearly keeps month/day (Feb 29 -> Feb 28 in non-leap years). -> {"created":N}
## 8. Reports
Amounts in book currency or `--currency CUR`, converted at the report's date (--to or --at) as `convert`; missing rate => user error. Income, liabilities, equity shown positive (negated raw). Accounts appear by the name postings are on, only if they have postings in range (zero-sum shows "0.00").
- report income --from DATE --to DATE [--currency CUR] -> {"income":{"Income:Salary":"3000.00"},"expenses":{"Expenses:Rent":"900.00"},"total_income","total_expenses","net"}
- report balance-sheet --at DATE [--currency CUR] -> {"assets":{},"liabilities":{},"equity":{},"retained_earnings","total_assets","total_liabilities","total_equity"} postings on/before DATE. retained_earnings = all income minus all expenses up to DATE; total_equity includes it; total_assets = total_liabilities + total_equity.
- report networth --from MONTH --to MONTH -> [{"month":"2026-01","assets","liabilities","networth"}] one per month, as of month's last day.
## 9. Loans
- loan schedule PRINCIPAL RATE MONTHS --start DATE (RATE annual percent) -> {"payment","total_interest","rows":[{"n":1,"date","payment","interest","principal","balance"}]}. r=RATE/1200; payment=PRINCIPAL*r/(1-(1+r)^-MONTHS) rounded to cents (RATE 0: PRINCIPAL/MONTHS rounded). Each month interest=round(balance*r), principal=payment-interest. Last row repays remaining balance (payment = balance + its interest), final balance "0.00". Row n date = start + n months by the monthly rule of section 7.
## 10. HTTP API
`serve --port N`: same documents as --json output.
- GET /accounts, /transactions, /balances?at=DATE, /reports/income?from=&to=, /reports/balance-sheet?at=
- POST /transactions body {"date","description","postings":[{"account","amount"}]} (amount may be omitted on one) -> 201 + txn; user error -> 400 {"error":"..."}. Unknown paths 404.
- Every POST needs header X-User: NAME. Missing/unknown user -> 401, role may not -> 403, both {"error"}. GET needs no user.
- Also GET /invoices, GET /invoices/ID, POST /invoices (body {"customer","date","lines":[{"description","quantity","price","tax_code"}]}, tax_code optional) -> 201 draft invoice; POST /invoices/ID/issue -> 200 invoice; POST /invoices/ID/payments (body {"amount","date","account"}) -> 200 invoice; GET /reports/aging?at=DATE (&payables=1 for bills); GET /audit.
## 11. Users, roles, audit
- Roles: admin (everything), editor (everything except `user add` and `period close`), viewer (only commands that change nothing).
- user add NAME --role admin|editor|viewer (admin only); existing => user error. user list -> [{"name","role"}] sorted by name.
- Every data-changing command needs --user (missing/unknown/role not allowed => user error). Read-only commands work with or without --user.
- Every successful data-changing command appends one audit entry. audit list [--by NAME] -> [{"seq":1,"at":"<UTC ISO 8601>","user":"alice","action":"init","target":"EUR"}] oldest first, exactly those keys. init is entry 1. Actions/targets: init (currency), user.add (name), account.add (name), txn.add (id), fx.add (FROM/TO), rule.add (pattern), import (account), budget.set ("ACCOUNT MONTH"), recurring.add (name), recurring.run (--until date), period.close (month), tax.add (code), customer.add / vendor.add (name), invoice.create, invoice.issue, invoice.pay, bill.create, bill.pay (invoice or bill id), reconcile (account). Targets are strings.
## 12. Closed periods
- period close MONTH (admin only) closes that month and all earlier. period status -> {"closed_through":"2026-01"} (null if none). Closing an earlier month than already closed changes nothing.
- Anything posting a txn dated in a closed month is a user error: txn add, import (any row in closed month => whole import fails, nothing imported), recurring run (likewise), invoice issue, invoice pay, bill create, bill pay.
## 13. Tax codes, customers, invoices
- tax add CODE RATE (percent e.g. 20); tax list -> [{"code":"VAT20","rate":"20"}] sorted by code, rate shown as given.
- customer add NAME [--terms DAYS] (default 30); customer list -> [{"name","terms":30}] sorted by name.
- invoice create --customer NAME --date DATE --line "DESCRIPTION;QUANTITY;PRICE;TAXCODE" [--line ...] (TAXCODE may be empty) -> draft:
  {"id":1,"number":null,"customer":"Acme","date":"2026-01-10","due":"2026-02-09","status":"draft","lines":[{"description":"Consulting","quantity":"10","price":"95.00","tax_code":"VAT20","net":"950.00","tax":"190.00"}],"net":"950.00","tax":"190.00","total":"1140.00","paid":"0.00","balance":"1140.00"}
  Per line net=round(quantity*price), tax=round(net*rate/100); quantity shown as given, tax_code null without tax. Invoice net/tax/total(net+tax) are line sums; due = date + customer terms days; balance=total-paid. Unknown customer/tax code => user error.
- invoice issue ID: gives draft number INV-YYYY-NNNN (YYYY invoice date's year; NNNN 0001 for first invoice issued with that year, then 0002...), status issued, posts one txn dated invoice date, description "Invoice INV-...": Assets:Receivable +total, Income:Sales -net, Liabilities:SalesTax -tax if tax nonzero (accounts created if missing, book currency). Non-draft => user error.
- invoice pay ID AMOUNT --date DATE --account ACCOUNT (asset account): txn "Payment INV-...": ACCOUNT +AMOUNT, Assets:Receivable -AMOUNT. Status partial, or paid when balance zero. Paying a draft, a paid invoice, or more than balance => user error.
- invoice show ID -> invoice; invoice list [--status STATUS] ordered by id. Every successful invoice command prints the invoice.
- report aging --at DATE -> {"current","1-30","31-60","61-90","90+","total"}: balances as of DATE of issued invoices dated on/before DATE, counting only payments dated on/before DATE, bucketed by days past due (DATE - due; <=0 is current). Invoices with nothing left to pay are left out.
## 14. Vendors and bills
- vendor add NAME [--terms DAYS] (default 30); vendor list like customer list.
- bill create --vendor NAME --ref TEXT --date DATE --line "DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE" [--line ...]: AMOUNT is line net; ACCOUNT must be existing expense or asset account; line tax=round(net*rate/100). Vendor's --ref unique. Posted at once, dated DATE, description "Bill REF": each line's ACCOUNT +net, Assets:TaxReceivable +bill tax if nonzero, Liabilities:Payable -total (accounts created if missing).
  -> {"id":1,"vendor":"Office Ltd","ref":"A-17","date","due","status":"open","lines":[{"description","account","tax_code","net","tax"}],"net","tax","total","paid":"0.00","balance"}
- bill pay ID AMOUNT --date DATE --account ACCOUNT: Liabilities:Payable +AMOUNT, ACCOUNT -AMOUNT, description "Payment REF"; status partial/paid as invoices, same errors. bill show ID, bill list [--status STATUS].
- report aging --at DATE --payables: same report for bills.
## 15. Tax report
- report tax --from DATE --to DATE -> {"collected","paid","net","by_code":{"VAT20":{"collected","paid"}}}: collected = tax of issued invoices dated in period, paid = tax of bills dated in period, net = collected - paid. by_code has every tax code used in the period.
## 16. Reconciliation
- reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID ...]: marks given txns cleared for ACCOUNT (each must have a posting to ACCOUNT dated on/before DATE, else user error and nothing marked); -> {"account","date","statement_balance","cleared_balance","difference","uncleared":[ids]}. cleared_balance = sum of ACCOUNT's cleared postings dated on/before DATE; difference = statement - cleared; uncleared = ascending ids of txns with a posting to ACCOUNT on/before DATE not cleared. Cleared marks kept for later runs.
## 17. Ledger reports
- report trial-balance --at DATE -> {"rows":[{"account","debit","credit"}],"total_debit","total_credit"}: one row per account with postings on/before DATE (by name postings are on, sorted), raw balance in book currency (converted at DATE as in sec 8): positive = debit, negative = credit (as positive number), other side "0.00". Totals equal.
- report ledger ACCOUNT --from DATE --to DATE -> {"account","opening","rows":[{"date","id","description","amount","balance"}],"closing"} in ACCOUNT's currency: opening = balance of ACCOUNT and descendants before FROM; one row per posting to them in period (by date, id) with running balance; closing = last balance (or opening).
## Done
`python3 -m unittest discover -s tests` passes and covers every section; README.md explains usage and lists assumptions.
