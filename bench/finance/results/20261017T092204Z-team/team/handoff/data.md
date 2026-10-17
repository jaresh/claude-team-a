# Handoff: data (spec sections 4-7)

## Done
- `fin/cmd_data.py`: COMMANDS for fx add, convert, rule add, rule list, import, budget set, report budget,
  recurring add, recurring run. SCHEMA tables: rule_rules, import_imported, budget_budgets, recur_items, recur_created.
- `tests/test_data.py`: 30 tests (FxTest, RuleTest, ImportTest, BudgetTest, RecurringTest). Setup is in-process
  (`Book(self.db, schemas=[SCHEMA])`, currency EUR, users admin/viewer, accounts), so it does not depend on cmd_books.
- Checks:
  - `python3 -m unittest tests.test_data -q`: Ran 30 tests, OK. (The shell has no `python`; use `python3`.)
  - `python3 -m py_compile fin/cmd_data.py tests/test_data.py`: OK.
  - `python3 -m unittest discover -s tests -q`: 105 tests run, failures only in `test_invoices` and `test_reports`
    (teammates' files, still in progress; the failing set changed between two runs). None in data.

## In progress
- Nothing. Module and tests are complete.

## Next step
- Lead: no action needed from data. Re-run when invoices/reports settle:
  `cd /home/jaca/claude-team-a/bench/work/finance-team && python3 -m unittest tests.test_data -q`
- Lead: add these assumptions to the README (unspecified in spec):
  1. Category accounts for import are created in the book currency; an existing rule target in another currency
     is a user error ("account X is in USD, not EUR") for that row.
  2. Import rows with amount 0 go to Income:Uncategorized (amount < 0 goes to Expenses:Uncategorized).
  3. Amounts with more than two decimals are rejected (import, budget, recurring posting). `fx` rate may have any precision.
  4. Import is all-or-nothing: any bad row (including a closed-period row, even a repeat) fails the whole file.
     Dedupe key is (account, date, description, amount); repeats and within-file duplicates are skipped and counted.
  5. Budgets: expense accounts only, non-negative, at most two decimals, one per (account, month), INSERT OR REPLACE.
     `report budget` sums each budget account and its descendants for the month, converts each posting to the account's
     currency at month end, and reports remaining = budget - actual. Output sorted by account name.
  6. Rule target accounts are validated by name (valid type and name) only; they need not exist and are created on import.
     Rules are case-insensitive regex, first match wins, ordered by insertion.
  7. Recurring: `--every` is monthly, weekly, or yearly. Monthly and yearly keep the start day, clamped to month end
     (Jan 31 -> Feb 28 -> Mar 31; Feb 29 yearly -> Feb 28 in non-leap years). Each occurrence is tracked in
     recur_created (recur_id, date), so reruns create only new occurrences. A recurring run is atomic through the CLI rollback.
     Postings are given as `ACCOUNT=AMOUNT`, with at most one bare `ACCOUNT` that balances the rest.
  8. Audit: fx.add target "FROM/TO"; rule.add target pattern; import target account; budget.set target "ACCOUNT MONTH";
     recurring.add target name; recurring.run target until-date.
- Core bug (lead, not fixed here; core.py is not mine): `Book.postings` builds `account LIKE account+":%"` without escaping,
  so `_` or `%` in an account name acts as a wildcard and can match sibling accounts. Fix by escaping LIKE or using
  `substr(p.account, 1, len(?)+1) = ?`. Not covered by my tests.

## Do not redo
- Checked `tests/helpers.py`: `ok`/`fails` take `user=` (default "admin"; `user=None` omits --user). Tests use this as written.
- Checked `fin/core.py`: `post_txn`, `convert`, `add_months`, `parse_posting`, `check_open` behave as my module expects.
  Did not edit core.py, cli.py, helpers.py, or any other teammate's file.
- The `timeout` command is not present in this shell; `python` is not on PATH (use `python3`). Not a code issue.
- No commit made (per team rules).
