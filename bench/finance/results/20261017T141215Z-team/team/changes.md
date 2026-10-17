# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

2026-10-17 consistency fin/core.py balance_postings (new), post_txn: posting checks moved into balance_postings; post_txn still checks length and check_open first; messages unchanged
2026-10-17 consistency fin/imports.py _check_postings: removed; add_recurring calls core balance_postings for validation (unbalanced message now includes currency and amount)
