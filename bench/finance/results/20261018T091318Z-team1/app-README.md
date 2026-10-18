# fin — small-business finance system

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API.

## Usage
```
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
python -m fin --db b.db init --currency EUR --admin alice
python -m fin --db b.db --user alice account add Assets:Bank
python -m fin --db b.db --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin --db b.db --json balance
python -m fin --db b.db serve --port 8000     # HTTP API; POSTs need header X-User
```
Commands: init, user, audit, period, account, txn, balance, fx, convert, rule, import, budget,
recurring, report (income, balance-sheet, networth, budget, trial-balance, ledger, aging, tax),
loan schedule, tax, customer, invoice, vendor, bill, reconcile, serve.
User errors exit 2 with a message on stderr, change nothing. Tests: `python -m unittest discover -s tests`.

## Assumptions
- Without `--json`, output is the same JSON document, pretty-printed. Default `--db` is `./fin.db`.
- Blank transaction descriptions, same-currency fx pairs and rates <= 0 are user errors.
- `account add` on an auto-created parent is an "exists" error. `txn list --account` matches the
  exact name or descendants (`NAME:`), not raw string prefixes.
- Posting amounts are rounded to cents. Balance keys include ancestors.
- Import: zero-amount and blank-description rows are errors; a bad row or closed-period row fails the
  whole file; blank lines ignored; Uncategorized accounts created only when needed; `import` is audited
  even if nothing was imported. Rules: first match wins, target account must exist.
- Budgets: expense accounts only, amount >= 0. Recurring names unique; occurrences counted from the
  start date (no day drift); a closed period anywhere in a run fails the whole run.
- Reports: accounts appear only under the exact name postings are on. Foreign-currency amounts are
  converted per account at the report date, so with foreign accounts totals may differ by a cent.
  Networth `--from` must not be after `--to`. Ledger converts other-currency postings to the account's currency.
- Invoices: quantity > 0, price >= 0, at least one line; creating a draft is allowed in closed periods
  (issue/pay are not); payments must go to an asset account other than Assets:Receivable. Tax rates stored as given.
- Aging: buckets <=0 current, 1-30, 31-60, 61-90, 90+; zero balances omitted.
- Bills: line amount >= 0; refs unique per vendor; payment account must be an asset; blank ref refused.
- Tax report: drafts excluded; `by_code` includes zero-rate codes; `--from` after `--to` is an error.
- Reconcile: needs write permission (even without `--clear`), is always audited, counts only postings
  on the exact account, duplicate `--clear` ids collapse.
- API: bad JSON → 400; non-numeric invoice id → 404; methods other than GET/POST → 501; invoice line
  fields cannot contain `;`.
- Audit `at` is UTC `YYYY-MM-DDTHH:MM:SSZ`; `init` is audited under the admin name.
