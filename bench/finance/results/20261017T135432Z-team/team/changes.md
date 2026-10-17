# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

- 2026-10-17, consistency, fin/core.py, new helpers: due_date, check_currency, parse_postings (moved from ledger), subtree_sql, _check_account_name, Book.resolve_postings (balance rules split out of post_txn), Book.tax_on; add_account/ensure_account use the new name check; no behaviour change; removed unused imports json, InvalidOperation.
- 2026-10-17, consistency, fin/cli.py, _init uses core.check_currency; removed unused Cmd import.
- 2026-10-17, consistency, fin/schedule.py, removed _check_postings (use Book.resolve_postings) and local split_posting loop (use parse_postings).
- 2026-10-17, consistency, fin/ledger.py, removed _currency and parse_postings (now core); subtree SQL via subtree_sql.
- 2026-10-17, consistency, fin/reports.py, _currency uses check_currency; ledger report uses subtree_sql; removed import re.
- 2026-10-17, consistency, fin/banking.py, budget_report uses subtree_sql.
- 2026-10-17, consistency, fin/billing.py, removed _due (core due_date) and _tax (Book.tax_on); removed unused imports.
- 2026-10-17, consistency, fin/invoicing.py, _line_amounts uses Book.tax_on; create_invoice due date via due_date; removed unused imports.

