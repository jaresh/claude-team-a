# Plan
Goal: small-business finance system, spec in .claude/team/spec.md (the user's full request; read the sections for your task).
Check: `python3 -m unittest discover -s tests` (each teammate runs its own test file: `python3 -m unittest tests.test_<task>`).

## Contract (already written by the lead; READ fin/core.py, fin/cli.py, fin/ctx.py, fin/books.py, fin/db.py first)
- Python 3.12+ stdlib only. Money = Decimal; use core.q2 (half-up), core.fmt (2-decimal string, no "-0.00"), core.parse_amount/parse_date/parse_month.
- Every error the user can cause: `raise UserError(msg)` (fin.errors). Never print in handlers; return JSON-able data.
- Each command module `fin/<name>.py` defines `register(sub)` (see books.py) and handlers `cmd_x(ctx, args)`; groups via `cli.group(sub, "report")` (shared by several modules; never call sub.add_parser for a group name directly). Attach `set_defaults(func=..., write=True/False, admin=False)`. write=True for anything changing data -> requires --user, viewer denied. Handlers call `ctx.audit(action, target)` exactly once per successful mutation (action names in spec sec 11). Handlers run inside a transaction, rolled back on UserError.
- Put the logic in plain service functions taking `(ctx or conn, plain args)` returning dicts (not argparse), because the HTTP API (a later wave) calls them. Name them in your handoff.
- Schema is fixed in fin/db.py (all tables exist, including yours); if you need a change, edit only the table of your feature and log it in .claude/team/changes.md.
- Posting transactions: `core.add_txn(conn, date, desc, [(account, Decimal|None)])` (checks closed period & balance). Use `core.ensure_account(conn, name)` to auto-create accounts. Audit entries for the invoice/bill/etc actions come from your handler; the internal txn posting does NOT add a `txn.add` audit entry (use core.add_txn, not books.create_txn).
- Reports/convert: core.convert, core.get_rate, core.balances, core.postings_rows, core.month_range, core.month_end, core.add_months.
- Tests: `tests/test_<task>.py` using unittest, a helper in tests/helpers.py (lead-written: `Env()` makes a temp db, `env.run(*args, user="admin", ok=True)` -> parsed JSON, `env.fail(*args)` asserts exit 2 with empty stdout). Do not edit helpers.py or other files' tests. Also test through the CLI with --json.
- Only edit files you own. Do not edit fin/core.py, cli.py, books.py, ctx.py, db.py; if you find a bug there, log it in changes.md and work around it.
- Never name a test helper like a unittest method.

## fx  (owns fin/fx.py, tests/test_fx.py)
Spec sec 4: `fx add`, `convert` (write=False). Service fn `convert_cmd`. Audit `fx.add` target `FROM/TO`. Validate currency codes, positive rate, date.
Done: python3 -m unittest tests.test_fx

## importer  (owns fin/importer.py, tests/test_importer.py)
Spec sec 5 (`rule add/list`, `import`) + closed-period rule of sec 12 (any row in closed month -> whole import fails, nothing imported; the cli transaction rollback handles it). Import writes via core.add_txn (no txn.add audit; one `import` audit entry with target the account; `rule.add` target the pattern). Validate regex when adding a rule. Dedup via table `imported` (n = occurrence index within identical rows so repeats in one file count as skipped; a row identical to an already imported one is skipped). Rule account must exist or be created? -> decide: must exist, else user error at rule add.
Done: python3 -m unittest tests.test_importer

## budgetsrecur  (owns fin/budgets.py, fin/recurring.py, tests/test_budgets.py, tests/test_recurring.py)
Spec sec 6 (`budget set`, `report budget MONTH` via cli.group "report") and sec 7 (`recurring add/run`). budget account must be an existing expense account. recurring run: all occurrences start..until not in recurring_done; closed period -> whole run fails. Occurrence k of monthly = core.add_months(start, k) (never chain from the previous occurrence). Audit: budget.set `ACCOUNT MONTH`, recurring.add name, recurring.run until-date. Postings with blank amount are resolved when each txn is created.
Done: python3 -m unittest tests.test_budgets tests.test_recurring

## ledgerreports  (owns fin/reports.py, tests/test_reports.py)
Spec sec 8 (`report income`, `report balance-sheet`, `report networth`) and sec 17 (`report trial-balance`, `report ledger`), `--currency`. Conversion at the report's date via core.convert per posting-account balance (convert each account's per-currency balance, then round to cents; sums of converted values are summed unrounded and rounded at the end of each account, totals = sums of the rounded displayed values so statements add up). Service fns: income_report(conn, frm, to, currency), balance_sheet(conn, at, currency), networth(...), trial_balance(...), ledger(...), taking conn. Note sec 17 trial balance rows and sec 8: "only if they have postings in range".
Done: python3 -m unittest tests.test_reports

## loans  (owns fin/loans.py, tests/test_loans.py)
Spec sec 9 `loan schedule` (write=False). Use Decimal with context precision >= 50. Service fn schedule(principal, rate, months, start). Validate input (principal>0, months>=1, rate>=0).
Done: python3 -m unittest tests.test_loans

## invoicing  (owns fin/invoicing.py, fin/tax.py, tests/test_invoicing.py)
Spec sec 13 (tax add/list, customer add/list, invoice create/issue/pay/show/list, `report aging` receivables) and sec 15 (`report tax`, note: needs bills table: bills(…) lines in bill_lines with tax_code/tax; query the tables directly). `report aging` handler: the group "report" has `aging` registered by ONE module: you register it with a `--payables` flag and implement the bills side too, querying bills/bill_payments/bill_lines tables directly (the bills task writes them; layout in db.py; bill total = sum(net)+sum(tax), paid = sum(bill_payments.amount)). Do not parse "paid" status out of anything but the tables. Audit: tax.add code, customer.add name, invoice.create/issue/pay with invoice id. Service fns: create_invoice(ctx, customer, date, lines), issue_invoice(ctx,id), pay_invoice(ctx,id,amount,date,account), show_invoice(conn,id), list_invoices(conn,status), aging(conn, at, payables), tax_report(conn, frm, to). Closed period checks come from core.add_txn. Tax code rate shown as given. Invoice numbering: count of issued invoices with that year +1.
Done: python3 -m unittest tests.test_invoicing

## bills  (owns fin/bills.py, tests/test_bills.py)
Spec sec 14 (`vendor add/list`, `bill create/pay/show/list`), NOT `report aging` (invoicing owns it) and NOT tax codes (read table `taxes`). Tax code rates are in table `taxes` (rate as given text). Audit: vendor.add name, bill.create/bill.pay with bill id. Service fns: create_bill(ctx, vendor, ref, date, lines), pay_bill(ctx,id,amount,date,account), show_bill(conn,id), list_bills(conn,status). bill_lines.net/tax stored as 2-decimal strings.
Done: python3 -m unittest tests.test_bills

## reconcile  (owns fin/reconcile.py, tests/test_reconcile.py)
Spec sec 16. Validate all --clear ids before marking. Audit `reconcile` target the account. A posting is "cleared" if (txn_id, account) is in `cleared`; the account posting match is exact account name. Service fn reconcile(ctx, account, date, balance, clear_ids).
Done: python3 -m unittest tests.test_reconcile

## api  (wave 2; owns fin/api.py, tests/test_api.py)
Spec sec 10 + 11. `serve --port N` (write=False, no auth; handler blocks serving). http.server ThreadingHTTPServer, one sqlite connection per request via db.connect, begin/commit/rollback like cli.main, Ctx + authorize for POSTs (X-User header; PermissionDenied.status 401/403; UserError 400; unknown path 404; GET /transactions supports optional account/from/to). Reuse the service functions from books.py, reports.py, invoicing.py (read their handoffs/code). Tests start the server on a free port in a thread (ThreadingHTTPServer(("127.0.0.1",0),...)); expose `make_server(db_path, port)` returning the server.
Done: python3 -m unittest tests.test_api
