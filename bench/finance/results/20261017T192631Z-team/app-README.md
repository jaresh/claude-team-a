# fin — small-business finance system

Python 3.12+, standard library only. Run: `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`

    python -m fin --db b.db init --currency EUR --admin alice
    python -m fin --db b.db --user alice account add Assets:Bank
    python -m fin --db b.db --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --db b.db report income --from 2026-01-01 --to 2026-01-31
    python -m fin --db b.db serve --port 8000      # JSON API (POST needs X-User header)

Commands cover accounts, transactions, balances, fx/convert, rules/import, budgets, recurring, loans, reports
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), users/audit/periods, tax codes,
customers/vendors, invoices, bills, reconciliation. Tests: `python -m unittest discover -s tests`.

Layout: `fin/core.py` shared helpers; `fin/cli.py` parsing/permissions/transactions; `books.py`, `bookkeeping.py`,
`docs.py`, `reports.py` command modules; `api.py` HTTP server. Each command runs in one SQLite transaction (user errors roll back).

## Assumptions
- Without `--json` output is the same JSON, pretty-printed. User errors: exit 2, message on stderr.
- `init` returns {"currency","admin"}; `account add` audits only the named account (not auto-created parents).
- Posting specs split on the first `=`; amounts are rounded half up to cents on input.
- `txn list --account` matches whole path segments (`Assets:Ban` does not match `Assets:Bank`).
- Import: rule patterns use `re.search`, case-insensitive; rule accounts are shape-checked at `rule add` and created on import;
  zero amounts go to `Income:Uncategorized`; description/date/amount dedupe key uses stripped description and normalized amount;
  rule/category accounts must share the import account's currency.
- Reports convert each posting amount at the report date, round once per account; totals are rounded from unrounded sums
  (multi-currency totals may differ by a cent from the sum of rows). `total_equity` = total_assets − total_liabilities.
- Networth/aging/tax follow the spec literally; invoices accept negative quantity/price (not rejected); invoice line
  descriptions cannot contain `;`.
- API binds 127.0.0.1; request bodies are validated before the `X-User` check; non-numeric invoice ids give 404;
  numbers in bodies keep their exact text.
- Not-specified behaviours (e.g. reconcile of already cleared items, duplicate users) are user errors where sensible.
