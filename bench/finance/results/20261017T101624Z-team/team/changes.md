# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

2026-10-17 consistency fin/core.py WRITE_ROLES, add_days, total, add_to, closed_through, tax_rate, tax_on added (additive); check_open, post_transaction, make_ctx use them; timedelta import added
2026-10-17 consistency fin/bills.py _add_days removed (core.add_days); _lines uses core.tax_rate/tax_on; _paid, bill_json, do_bill_create, do_tax_report use core.total; unused Decimal/q/timedelta imports dropped
2026-10-17 consistency fin/invoices.py _add_days and _tax_rate removed (core.add_days, core.tax_rate/tax_on); _sums, _paid, do_aging use core.total; timedelta import dropped
2026-10-17 consistency fin/imports.py do_budget_report uses core.total; _occurrence weekly uses core.add_days(start, 7*k); unused datetime import dropped
2026-10-17 consistency fin/reports.py _balances, _value, do_income, do_balance_sheet, do_ledger use core.total / core.add_to
2026-10-17 consistency fin/ledger.py do_balance uses core.add_to; fin/recon.py do_reconcile uses core.total (unused Decimal import dropped); fin/admin.py period_close and period_status use core.closed_through; fin/api.py _writer uses core.WRITE_ROLES
