# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(global options first; `--db` defaults to `./fin.db`). Tests: `python3 -m unittest discover -s tests`.

```
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice --json txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json report income --from 2026-01-01 --to 2026-01-31
python3 -m fin --db fin.db serve --port 8080      # JSON API; POST needs header X-User
```

Commands cover accounts, transactions, balances, fx/convert, rules/import, budgets, recurring, reports
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loans, reconcile, users/roles,
audit log, closed periods, tax codes, customers/invoices, vendors/bills, and the HTTP API (see the task spec for shapes).
Errors: exit 2, message on stderr, nothing on stdout, nothing changed (each command runs in one DB transaction).

Layout: `fin/core.py` (money, dates, schema, posting, rates), `fin/cli.py` (parsing, permissions, dispatch),
`ledger.py`, `banking.py`, `invoicing.py`, `statements.py`, `loans.py`, `api.py`.

## Assumptions
- Without `--json` the result is printed as indented JSON. Amounts are rounded to cents when entered.
- Command results for commands the spec doesn't shape (init, account add, fx add, rule add, ...) are small JSON objects.
- `init` prints the currency and admin; `loan schedule` and `convert` need an initialised book file but no `--user`.
- Read-only commands ignore an unknown `--user`; data-changing commands need a known user with a sufficient role.
- Reconcile and `rule add`/`import` etc. are data-changing (need editor/admin). Reconcile audits on every run.
- `import` audits only if at least one row was imported; `recurring run` audits only if something was created.
- `rule add` target account must exist; invalid regex is a user error. Import: bad rows (date, amount, missing columns, zero amount) fail the whole import; dedupe uses previously imported rows only (not manual transactions); rule categories must share the bank account's currency.
- `budget set`: expense account, amount >= 0. `report budget` converts descendant postings in other currencies at the month end.
- Recurring names are unique; occurrences are computed from the start date (Jan 31 → Feb 28 → Mar 31).
- Invoice numbers count existing issued numbers of the invoice year. Bill `--ref` is unique per vendor. Due date = date + terms. Blank tax code = no tax. Invoice line descriptions cannot contain `;`.
- Reports: convert each account/currency sum at the report date, sum unrounded, round once. `--from` after `--to` is a user error. Trial-balance totals are sums of unrounded balances (may differ from rounded rows by a cent in multi-currency books). Ledger converts each posting into the account's currency at its own date.
- `reconcile` uses the exact account (no descendants); a transaction is cleared per (transaction, account).
- Loans: principal > 0, rate >= 0, months >= 1.
- API: user errors (including unknown ids) → 400, unknown paths → 404, unexpected → 500; binds 127.0.0.1; `POST /bills`, `user add`, `period close` are not exposed; extra query filters `account`, `status`, `by` are accepted.
- Import dedupe key is (account, date, description, amount), so genuinely identical rows are skipped as the spec requires. Invoice/bill payment accounts must be in the book currency. The API role check mirrors the CLI's (viewer → 403 on POST). API 500 responses carry the error text.
