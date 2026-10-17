# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(`--db` defaults to `./fin.db`; global options come before the command).

    python3 -m fin init --currency EUR --admin alice
    python3 -m fin --user alice account add Assets:Bank
    python3 -m fin --user alice account add Expenses:Rent
    python3 -m fin --user alice --json txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --json balance
    python3 -m fin --user alice serve --port 8080      # HTTP API; POST needs header X-User

Commands: init, user, account, txn, balance, fx, convert, rule, import, budget, recurring, period, audit,
tax, customer, invoice, vendor, bill, reconcile, loan schedule, serve, and `report`
(income, balance-sheet, networth, budget, aging [--payables], tax, trial-balance, ledger).
User errors exit with code 2 (message on stderr, nothing on stdout, nothing changed).
Without `--json` output is pretty-printed JSON.

Layout: `fin/core.py` (money, dates, Book, posting, audit), `fin/cli.py` (command registry), one module per
command group. Tests: `python3 -m unittest discover -s tests` (the CLI is run with `sys.executable`).

## Assumptions
- Posting amounts with more than two decimals are rounded half up to cents.
- A multi-currency transaction must balance per currency; the one blank posting balances its own account's currency.
- Rate lookup: FROM→TO if any such rate exists on or before the date, else 1/(TO→FROM). `convert --at` is required.
- Budgets are in the book's currency; `report budget` converts postings at month end.
- With `--currency`, conversion is done per account/currency group and rounded, so totals may differ by 0.01 in rare cases.
- `reconcile` writes an audit entry only when it clears transactions; reading status needs no user.
- `import`: a zero amount goes to `Income:Uncategorized`; a rule's account must exist at import time.
- `bill pay` / `invoice pay` reject amounts <= 0; payment dates are not checked against document dates.
- `report tax` counts invoices that are not drafts. Aging treats non-draft invoices (issued, partial, paid) as of the report date.
- API: invoice lines are passed to the CLI as `desc;qty;price;tax`, so a `;` in a description is unsupported; `serve --read-only` answers POSTs with 403.
- The HTTP server binds 127.0.0.1.
- No separate consistency-refactor pass was done; modules were written in parallel against `core.py`.
