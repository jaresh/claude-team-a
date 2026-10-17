# Plan
Goal: small-business finance system, python3 stdlib only (use `python3`). Full spec: the user's
task, summarized per module below (teammates: spec text for your sections is in your task section).
Check: `python3 -m unittest discover -s tests`.

## Contract (already written by lead; READ fin/core.py and fin/cli.py first, do not edit them)
- Each module `fin/<name>.py` defines `register(sub)` (sub = top-level subparsers action; create
  commands with `sub.add_parser("account")` then `.add_subparsers(dest="subcmd", required=True,
  parser_class=type(sub.choices... )` -> simply use `parser_class=fin.cli.Parser`) and optional
  `SCHEMA` (CREATE TABLE IF NOT EXISTS ... string; use unique table names prefixed by your module).
- Every leaf parser calls `.set_defaults(handler=fn, write=<bool>, admin=<bool>)`. write=True for
  anything changing data; admin=True only for user add/period close (not yours). Roles/--user are
  enforced by cli.py, don't re-check.
- `fn(ctx, args) -> JSON-able result` (dict/list). Raise `core.UserError` for any user error (cli
  exits 2, rolls back everything). Write handlers must call `ctx.audit(action, target)` exactly
  once on success (actions/targets listed per task). Never print. Never use float.
- Use core helpers: q/fmt/parse_amount/parse_decimal/check_date/check_month/check_currency/
  add_months/month_end/ensure_account/post_transaction/get_txn/direct_balances/rollup/convert/
  to_currency/check_open. Money in output always via `fmt`. Dates are ISO strings in the DB.
  Postings: positive=debit. post_transaction already checks balance, accounts, closed periods.
- Tests: `tests/test_<module>.py` using `tests.helpers.FinCase` (see it). Subprocess per command,
  so keep test counts reasonable. Another teammate's commands may not exist yet: only depend on
  commands owned by the core (init,user,audit,period) and your own, plus `txn add`/`account add`
  (ledger, built in parallel; if absent when you test, insert through core.post_transaction in
  a Python-level test, or wait-free: write tests that use them and run them at the end).
- Append one line to .claude/team/changes.md for any edit outside your own files (you may not edit
  others' files at all, nor fin/core.py, fin/cli.py, tests/helpers.py).
- Output: no pretty text. Done check per task = `python3 -m unittest tests.test_<module>`.
- Unknown/odd input -> UserError, never a traceback. Parse every amount/date with core helpers.

## ledger  (files: fin/ledger.py, tests/test_ledger.py)
Commands (spec):
- `account add NAME [--currency CUR]` (audit account.add NAME; first segment must be
  Assets|Liabilities|Equity|Income|Expenses else error; creates missing parents with same currency;
  existing -> error; returns {"name","type","currency"}). `account list` -> [{"name","type","currency"}] sorted by name (read).
- `txn add --date D --desc T --posting ACCOUNT=AMOUNT ... (>=2; at most one `ACCOUNT` w/o amount)` -> core.post_transaction;
  audit txn.add <id>; returns get_txn dict. Posting with '=' split on the LAST '='? Account names have no '='; split on first '='.
  `txn list [--account PREFIX] [--from D] [--to D]` -> list of txn dicts ordered by date, id. PREFIX matches the account itself or descendants (name == P or startswith P+":"); inclusive dates.
- `balance [--at D]` -> {"Assets:Bank": {"EUR":"100.00"}} for every account with postings <= D and every ancestor: core.rollup(core.direct_balances(ctx, at=D)); values via fmt. Raw signs.
- `fx add DATE FROM TO RATE` (audit fx.add "FROM/TO"; rate positive decimal, stored as given str; currencies via check_currency; return {"date","from","to","rate"}).
- `convert AMOUNT FROM TO --at D` -> {"amount": fmt(core.convert(...)), "currency": TO}. read-only. --at required.
Done: tests cover all of the above incl. errors (bad account name, duplicate, unbalanced, unknown account, missing rate, inverse rate, 1:1, multi-currency txn balances per currency).

## banking  (files: fin/banking.py, tests/test_banking.py)
- `rule add PATTERN ACCOUNT` (audit rule.add PATTERN; validate regex compiles & account name valid type; return {"pattern","account"}); `rule list` -> [{"pattern","account"}] in order added (read).
- `import FILE --account ACCOUNT [--date-col N=0] [--desc-col N=1] [--amount-col N=2] [--skip-header]`: csv module, 0-based cols. ACCOUNT must exist. Per row: txn on that date with row description between ACCOUNT (amount) and category account (-amount): first rule (in order) whose pattern `re.search(..., re.I)` matches description -> its account (ensure_account), else `Expenses:Uncategorized` if amount<0 / `Income:Uncategorized` if >0 (ensure_account, book currency; amount 0 -> Expenses:Uncategorized). Skip row identical (date, description, amount) to one already imported into the same ACCOUNT (keep own table banking_imported(account,date,description,amount) — record each imported row; also skip repeats within the file). If any row is in a closed period (core.check_open) or invalid, whole import fails, nothing imported (cli rolls back). Empty/short rows -> UserError. Audit `import` ACCOUNT always. Returns {"imported":N,"skipped":M}. Use ensure_account for category accounts, post_transaction for txns.
- `budget set ACCOUNT MONTH AMOUNT` (account must exist & be expense type; table banking_budget; replace; audit budget.set "ACCOUNT MONTH"; return {"account","month","amount"}). `report budget MONTH` (read) -> [{"account","budget","actual","remaining"}] sorted by account; actual = sum of month's postings (date within the month) to account and descendants (book currency amounts; use account's postings sum as-is); remaining = budget - actual.
- `recurring add NAME --every monthly|weekly|yearly --start DATE --posting A=AMT ... ` (same posting rules as txn add: >=2, one may omit amount, validated at add — validate by parsing and checking accounts exist and balance, without storing a txn; table banking_recurring; audit recurring.add NAME; return {"name","every","start","postings":[...]}). `recurring run --until DATE`: for each recurring (by id), every occurrence date from start..until not yet created (table banking_recurring_done(recurring_id,date)) -> core.post_transaction with description NAME; if any is in a closed month the whole run fails (rollback). Audit recurring.run DATE once. Returns {"created":N}. Monthly: add_months(start, k, day=start.day); weekly +7k days; yearly: add_months(start,12k, day=start.day) (Feb 29 -> Feb 28 non-leap).
- `reconcile ACCOUNT --date D --balance AMOUNT [--clear ID ...]` (write; `--clear` action="append", type int): each ID must be a txn with a posting to ACCOUNT dated <= D, else UserError and nothing marked. Mark cleared in table banking_cleared(account,txn_id). Return {"account","date","statement_balance","cleared_balance","difference","uncleared":[ids asc]}; cleared_balance = sum of ACCOUNT's postings in cleared txns dated <= D (account exact, not descendants); difference = statement - cleared; uncleared = txns with posting to ACCOUNT dated <= D not cleared. Audit reconcile ACCOUNT.
Done: tests cover each, incl. leap-day/month-end recurrence, idempotent run, import dedupe, closed period (use `period close`).

## reports  (files: fin/reports.py, tests/test_reports.py)
All amounts in book currency or `--currency CUR`, each account's per-currency balance converted via core.to_currency at the report's date (--to / --at) then rounded (fmt) -- convert each (account) total then q; missing rate -> UserError. Reports show income/liabilities/equity negated (positive). Accounts appear by the name postings are on (NOT rolled up), only if they have postings in range (zero sum shows "0.00"). Read-only commands (write=False).
- `report income --from D --to D [--currency C]` -> {"income":{acct:str},"expenses":{acct:str},"total_income","total_expenses","net"} (net=income-expenses; totals = sums of the rounded per-account values).
- `report balance-sheet --at D [--currency C]` -> {"assets","liabilities","equity" dicts,"retained_earnings","total_assets","total_liabilities","total_equity"}; postings <= D; retained_earnings = all income minus all expenses to D (equity-side positive); total_equity = sum equity + retained_earnings; so total_assets = total_liabilities + total_equity. Compute retained earnings from unrounded converted sums then q, so identity holds when books balance; if rounding breaks identity, derive retained_earnings = total_assets - total_liabilities - sum(equity).
- `report networth --from MONTH --to MONTH` -> [{"month","assets","liabilities","networth"}] per month as of month's last day (core.month_end), liabilities positive, networth=assets-liabilities; conversion at that last day; currency option too.
- `report trial-balance --at D` -> {"rows":[{"account","debit","credit"}],"total_debit","total_credit"}: rows sorted by account name, accounts with postings <= D, raw balance converted to book currency at D (and rounded); positive->debit, negative->credit (abs), other side "0.00".
- `report ledger ACCOUNT --from D --to D` -> {"account","opening","rows":[{"date","id","description","amount","balance"}],"closing"} in ACCOUNT's currency (no conversion): opening = sum of postings to ACCOUNT and descendants dated < FROM; rows = each such posting dated FROM..TO ordered by date, txn id (then posting id), running balance; closing = last balance or opening. Unknown account -> UserError.
- `loan schedule PRINCIPAL RATE MONTHS --start DATE` (read): r=RATE/1200 (Decimal; set decimal context prec 50); payment=round_half_up(P*r/(1-(1+r)^-N)) (RATE 0: P/N rounded); each month interest=q(balance*r), principal=payment-interest, balance-=principal; last row: principal=remaining balance, payment=balance+interest, final balance "0.00". Row n date = add_months(start, n, day=start.day). Output {"payment","total_interest","rows":[{"n","date","payment","interest","principal","balance"}]} (n int, rest strings via fmt; total_interest sum of interest). MONTHS positive int, PRINCIPAL > 0, RATE >= 0 else UserError.
Done: tests cover all, with hand-checked numbers (e.g. loan 1200 at 0% 12 months; a multi-currency income report with fx).

## billing  (files: fin/billing.py, tests/test_billing.py)
Tables billing_* (tax, customers, vendors, invoices, invoice_lines, bills, bill_lines, payments). Details:
- `tax add CODE RATE` (rate percent kept as given string; audit tax.add CODE; duplicate -> error; return {"code","rate"}); `tax list` -> [{"code","rate"}] sorted by code.
- `customer add NAME [--terms DAYS=30]` (audit customer.add; dup error; return {"name","terms"}); `customer list` sorted by name -> [{"name","terms"(int)}]. Same for `vendor add/list` (audit vendor.add).
- `invoice create --customer N --date D --line "DESC;QTY;PRICE;TAXCODE" ...` (>=1 line; split on ';' into exactly 4 fields, TAXCODE may be empty; audit invoice.create ID) -> draft: {"id","number":null,"customer","date","due","status":"draft","lines":[{"description","quantity"(as given string),"price"(fmt),"tax_code"(null if none),"net","tax"}],"net","tax","total","paid":"0.00","balance"}. line net=q(qty*price), tax=q(net*rate/100); invoice net/tax = sums of lines, total=net+tax, due=date+terms days, balance=total-paid. Unknown customer/tax code -> error. QTY positive decimal.
- `invoice issue ID` (draft only; number INV-YYYY-NNNN, YYYY = invoice date year, NNNN count per year issued +1, zero padded 4; status issued; post txn on invoice date, description "Invoice INV-..": Assets:Receivable +total, Income:Sales -net, Liabilities:SalesTax -tax if tax != 0; ensure_account them (book currency); postings via core.post_transaction (checks closed period); audit invoice.issue ID).
- `invoice pay ID AMOUNT --date D --account ACC` (ACC existing asset account; invoice must be issued/partial; amount >0 and <= balance; txn "Payment INV-..": ACC +AMT, Assets:Receivable -AMT; status partial or paid when balance zero; audit invoice.pay ID). `invoice show ID`, `invoice list [--status S]` ordered by id (reads). Every invoice command prints the invoice (list prints a list).
- `bill create --vendor N --ref R --date D --line "DESC;AMOUNT;ACCOUNT;TAXCODE" ...` (AMOUNT = line net; ACCOUNT existing expense or asset account; tax=q(net*rate/100); (vendor,ref) unique else error; posts at once on DATE, description "Bill REF": each line's ACCOUNT +net, Assets:TaxReceivable +tax total if != 0, Liabilities:Payable -total (ensure_account); audit bill.create ID) -> {"id","vendor","ref","date","due","status":"open","lines":[{"description","account","tax_code","net","tax"}],"net","tax","total","paid":"0.00","balance"}.
- `bill pay ID AMOUNT --date D --account ACC` (posts Liabilities:Payable +AMT, ACC -AMT, description "Payment REF"; status partial/paid; same errors; audit bill.pay ID). `bill show ID`, `bill list [--status S]`.
- `report aging --at D [--payables]` (read): invoices (or bills) dated <= D (invoices must be issued, i.e. not draft), balance as of D counting only payments dated <= D, bucket by days = D - due (<=0 current; 1-30; 31-60; 61-90; 90+), skip zero balances. -> {"current","1-30","31-60","61-90","90+","total"} fmt strings.
- `report tax --from D --to D` (read) -> {"collected","paid","net","by_code":{CODE:{"collected","paid"}}}: collected = tax of issued (non-draft) invoices dated in period (by line tax_code), paid = tax of bills dated in period; by_code has every code used in the period (both keys, "0.00" default). net = collected - paid.
- Payment on closed month, issue closed month, bill create/pay closed month -> UserError via post_transaction (do the checks before mutating invoice state; cli rolls back anyway).
Also export plain functions for the API: none needed.
Done: tests cover all incl. numbering across years, partial payments, aging buckets, closed periods, overpay.

## api  (files: fin/api.py, tests/test_api.py)
`serve(db_path, port)` (called by cli `serve`): http.server.HTTPServer on 127.0.0.1, serves until stopped (KeyboardInterrupt ok). Implement each request by calling `fin.cli.execute(db_path, user, argv)` (returns JSON-able result; raises UserError/AuthError/Forbidden) so docs match CLI --json output. Responses JSON (Content-Type application/json).
- GET /accounts -> ["account","list"]; /transactions -> ["txn","list"] (also pass optional query account/from/to); /balances?at=D -> ["balance","--at",D]; /reports/income?from&to (optional currency); /reports/balance-sheet?at; /invoices -> ["invoice","list"] (optional status); /invoices/ID -> ["invoice","show",ID]; /reports/aging?at=D[&payables=1]; /audit -> ["audit","list"] (optional by). GET needs no user (user=None).
- POST /transactions: body {"date","description","postings":[{"account","amount"?}]} -> ["txn","add","--date",..,"--desc",..,"--posting","ACC=AMT" or "ACC"] -> 201 + result. POST /invoices body {"customer","date","lines":[{"description","quantity","price","tax_code"?}]} -> ["invoice","create","--customer",..,"--date",..,"--line","desc;qty;price;tax"] -> 201. POST /invoices/ID/issue -> 200; POST /invoices/ID/payments body {"amount","date","account"} -> ["invoice","pay",ID,amount,"--date",d,"--account",a] -> 200.
- Every POST needs header `X-User`: missing or unknown user -> 401 {"error":..}, role not allowed -> 403 (cli.execute raises AuthError / Forbidden; check those before general UserError since they subclass it), other UserError -> 400 {"error":msg}. Unknown path -> 404 {"error":..}. Malformed JSON body / wrong types -> 400. Reject ';' in description for invoice lines with 400 (or handle). Prefix argv values safely (values starting with '-' like negative amounts: pass `--posting=ACC=-5` style / `--opt=value` forms so argparse does not misread).
- Tests: start `python3 -m fin --db X serve --port P` (free port) in a subprocess or use fin.api with a thread (design `make_server(db_path, port) -> HTTPServer` so tests can run it in a thread; `serve` = make_server(...).serve_forever()). Use urllib. Invoice endpoints can be tested only if billing exists at test time; run the full check at the end after others land (lead merges anyway).
Done: `python3 -m unittest tests.test_api`.
