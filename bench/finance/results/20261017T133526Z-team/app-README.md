# fin — small-business finance system

Python 3.12+, standard library only (sqlite3, Decimal, http.server, unittest).

## Usage

    python -m fin init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --json balance
    python -m fin serve --port 8080      # JSON API; POSTs need header X-User

Global options (`--db PATH` default `./fin.db`, `--json`, `--user NAME`) come before the command.
Commands: init, user, audit, period, account, txn, balance, fx, convert, rule, import, budget,
recurring, loan, tax, customer, invoice, vendor, bill, reconcile, report
(income, balance-sheet, networth, budget, aging [--payables], tax, trial-balance, ledger), serve.
User errors exit 2 with a message on stderr and change nothing.

Tests: `python -m unittest discover -s tests`

Layout: `fin/core.py` (money, schema, posting, fx), `fin/cli.py` (command registry), one module per area.

## Assumptions
- Without `--json`, commands print the same document as indented JSON.
- Posting amounts with more than two decimals are rounded half up to cents.
- Read-only commands accept `--user` but it must name an existing user if given.
- `init` failing leaves no database file; an existing db is never touched.
- Tax rates and terms must be >= 0; names are case-sensitive; duplicates are user errors.
- Dedup of imported rows is by (account, date, description, amount).
- Import/recurring/audit: `import`, `recurring run` and `reconcile` write an audit entry even when nothing changes.
- Import: rule accounts need not exist (created on use, book currency); zero amounts go to Income:Uncategorized; a bank account in a non-book currency fails unless category accounts exist in its currency.
- Budgets: account must exist and be an expense account; amount >= 0; `actual` counts only the account's own currency.
- Recurring: names need not be unique; closed-period occurrence fails the whole run; `recurring add` is allowed for a start in a closed month.
- Loan: `payment` is the regular payment; the last row differs by rounding; total_interest sums the rounded row interests.
- Invoices: at least one line; quantity kept as given; net uses the unrounded price; invoice number = count of numbers already issued for that year + 1; payment account must be an existing asset account in the book currency; `--status` must be a valid status.
- Bills: line accounts must already exist (expense or asset); payment checks as for invoices; bill pay output is the bill.
- Reports: per-account amounts converted then rounded, totals sum the rounded values (with `--currency` totals can differ by a cent from an exact identity); accounts are filtered by type before conversion; draft invoices are excluded from aging/tax; ledger converts each posting at its own date.
- Reconcile: "posting to ACCOUNT" means the exact account (not descendants); reconcile is not blocked by closed periods.
- API: each endpoint runs the CLI command in-process, so bodies equal `--json` output; unexpected errors give 500.
