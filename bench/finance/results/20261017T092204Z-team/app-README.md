# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(global options first; `--db` defaults to `./fin.db`). Tests: `python3 -m unittest discover -s tests`.

```
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice account add Expenses:Rent
python3 -m fin --user alice --json txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json report income --from 2026-01-01 --to 2026-01-31
python3 -m fin serve --port 8080     # HTTP API; POST needs header X-User
```
Commands: init, user, audit, account, txn, balance, period, fx, convert, rule, import, budget, recurring,
tax, customer, vendor, invoice, bill, reconcile, loan schedule, report (income, balance-sheet, networth, budget,
aging, tax, trial-balance, ledger), serve. See the module layout: `fin/core.py` (db, money, posting), `fin/cli.py`
(dispatch, auth, transactions), `fin/cmd_*.py` (commands).

## Assumptions
- Without `--json`, output is the same JSON, indented. `init` prints `{"currency","admin"}`; other write commands print the created/updated object.
- Each command runs in one DB transaction: any user error rolls everything back. Data-changing commands with a missing/unknown user or a viewer role are user errors (exit 2); over HTTP 401/403.
- Amounts with more than two decimals are rejected as user errors (fx rates may have any precision).
- `period close` on an already-closed month changes nothing and writes no audit entry.
- Implicit parent accounts take the new account's currency; existing parents keep theirs. `balance` lists ancestors even when they sum to zero.
- Import: all-or-nothing; zero amounts go to `Income:Uncategorized`; rule target accounts need not exist and are created in the book currency; a target in another currency is an error. Dedupe key is (account, date, description, amount).
- Budgets: expense accounts only, non-negative; actuals converted per posting at month end.
- Recurring: occurrences tracked per template, reruns create only new ones, atomic.
- Direct fx rate (on/before date) is preferred over an inverse one even if the inverse is newer. Report conversion rounds per posting/account to cents, so multi-currency totals can differ by a cent. Networth converts at each month end; ledger converts to the account's currency at `--to`.
- Retained earnings = −(income + expense balances); equity includes it.
- Invoices: number assigned at issue (per-year counter); empty tax code = no tax; payments must be > 0 and ≤ balance into an asset account. Aging includes non-draft invoices/all bills. `by_code` includes zero-rate codes.
- Reconcile: each `--clear` id must have a posting to exactly that account on/before `--date`; editor/admin only.
- API: binds 127.0.0.1, logs to stderr; POST without `X-User` → 401 before the body is read; invoice line fields cannot contain `;`; unexpected errors → 500; wrong method on a known path → 404.
