# Plan
Full user spec: .claude/team/spec.md (sections 1-17; read the sections your task names).

**Goal**: stdlib-only Python 3.12+ finance system, package `fin/`, run `python3 -m fin ...` (no `python` binary here).
**Check**: `python3 -m unittest discover -s tests` (final). Each task's own check is its test module.

## Contract (already written by lead — READ fin/core.py, fin/cli.py, tests/helpers.py first)
- `fin/core.py`: UserError, AuthError, ForbiddenError, dec, q2, fmt, parse_date, parse_month, month_end, add_months, add_years,
  account_type, parse_posting_arg, SCHEMA (ALL tables already exist: do not alter the schema), Book
  (conn, user, currency, audit(action,target), check_open(date), account(name), ensure_account(name,currency=None),
  post_txn(date,desc,[(acct,Decimal|None)]) -> txn dict, get_txn(id), balances(at=None), rate, convert(amount,frm,to,at)).
  Core bugs/needs: you may NOT edit core.py or cli.py; ask via handoff "Next step" if something is missing (work around meanwhile).
- Each feature module `fin/<name>.py` defines `register(reg)` and calls `reg.add("txn add", setup_fn, handler_fn, write_bool)`.
  `handler(book, args) -> JSON-serialisable data` (the CLI prints it; amounts via `fmt`). Write commands MUST call `book.audit(action, target)`
  exactly once on success (target per spec section 11; targets are strings). Never commit; cli.py commits. Raise UserError for bad input.
- ALSO expose each feature as plain functions taking `book` and python values (not argparse args), e.g. `list_accounts(book)`,
  `add_txn(book, date, desc, postings)`, `income_report(book, frm, to, currency=None)`, so the HTTP API can reuse them; handlers are thin wrappers.
  Function results are exactly the JSON documents of the spec. Document public function signatures in your handoff (a "Public API" list).
- Module owners: admin.py (sections 1,2,3,4 basics + 11 + 12), banking.py (5,6,7,9), invoicing.py (13,14), reports.py (8,15,16,17), api.py (10, wave 2).
- Money: Decimal everywhere, `fmt()` for output, `q2()` rounding. Reports convert via `book.convert(amount, cur, target, at)` per posting-currency total.
- Registry names: "init" is handled in cli.py. Command spellings exactly as in the spec ("report income", "loan schedule", "invoice pay", ...).
  Option dest names: argparse default (`--date-col` -> `date_col`). Repeatable options use action="append".
- Tests: unittest in `tests/test_<task>.py`, subclass `tests.helpers.CliCase` (run_cli/ok/fail_). Cover every section of your task, incl. error exit 2 cases. Keep each test file < 30 s.
- Schema notes: invoices/bills tables: see fin/core.py SCHEMA. Invoice lines store net/tax as Decimal text. tax rate stays as given text in `taxes.rate`.
  A bill's tax lines in `bill_lines`; invoices count for tax report when status != 'draft'.
- Assumptions to mention in handoff (lead puts them in README): any decision you made where spec is silent.

## admin
Files: fin/admin.py, tests/test_admin.py. Spec sections 1, 2, 3, 4 (account, txn, balance, fx, convert), 11 (user add/list, audit list; `init` itself is in cli.py — test it),
12 (period close / status). `period close`: store meta key closed_through (max with existing). Done: `python3 -m unittest tests.test_admin`.
Permission matrix is enforced by cli.py (viewer/editor/admin); test it here with a few commands. Must not touch other files.

## banking
Files: fin/banking.py, tests/test_banking.py. Sections 5 (rule, import), 6 (budget set, report budget), 7 (recurring add/run), 9 (loan schedule).
Use book.post_txn; import: all rows validated and closed-period checked before any insert (whole import fails atomically; cli rolls back on UserError anyway). Dedupe via `imported` table (also within a file).
Audit: rule.add, import (the account), budget.set ("ACCOUNT MONTH"), recurring.add, recurring.run (the --until date). Done: `python3 -m unittest tests.test_banking`. `loan schedule` is read-only. Must not touch other files.

## invoicing
Files: fin/invoicing.py, tests/test_invoicing.py. Sections 13 (tax, customer, invoice, report aging) and 14 (vendor, bill, aging --payables). Registers "report aging" (both receivables and --payables). Section 12: issue/pay/bill create/bill pay check closed period (post_txn does).
Audit: tax.add, customer.add, vendor.add, invoice.create/issue/pay, bill.create/pay (id as string). Expose functions e.g. create_invoice(book, customer, date, lines), issue_invoice(book,id), pay_invoice(book,id,amount,date,account), list_invoices(book,status=None), get_invoice(book,id), aging(book, at, payables=False), plus bill equivalents and tax/customer/vendor add/list.
Done: `python3 -m unittest tests.test_invoicing`. Must not touch other files.

## reports
Files: fin/reports.py, tests/test_reports.py. Sections 8 (report income, balance-sheet, networth), 15 (report tax; reads invoices/bills tables from SCHEMA — tests may create invoices by inserting rows via sqlite3 directly, or through CLI commands if present), 16 (reconcile), 17 (report trial-balance, report ledger). Tests for these use `txn add` / `fx add` / `account add` from admin (those commands exist once the admin task is merged; if not yet, insert via fin.core.Book in the test setUp).
Audit: reconcile (the account). Expose functions e.g. income_report(book, frm, to, currency=None), balance_sheet(book, at, currency=None), networth(book, frm, to), tax_report(book, frm, to), reconcile(book, account, date, balance, clear_ids), trial_balance(book, at), ledger(book, account, frm, to). Done: `python3 -m unittest tests.test_reports`. Must not touch other files.

## api (wave 2)
Files: fin/api.py, tests/test_api.py. Section 10 + 11 for HTTP + `serve --port N` command registered as read-only (write=False) with an argument `--port`. Use http.server with ThreadingHTTPServer; each request opens its own Book (Book.open(db, user)). POST needs X-User; use book.check_permission("<cmd name>", True) mapping: POST /transactions -> "txn add", POST /invoices -> "invoice create", /issue -> "invoice issue", /payments -> "invoice pay". Errors: AuthError->401, ForbiddenError->403, UserError->400 {"error":...}, unknown path 404. commit after success, rollback on error. Call the plain functions of the other modules (see handoffs in .claude/team/handoff/). Calls audit like the CLI does (txn.add etc). Tests: start server in a thread or subprocess on a free port. Done: `python3 -m unittest tests.test_api`.
