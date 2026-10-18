# fin — small-business finance system

Python 3.12+, standard library only. Run `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(use `python3` where `python` is not installed). Tests: `python3 -m unittest discover -s tests`.

## Quick start
    python -m fin --db fin.db init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice account add Expenses:Rent
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --json balance
    python -m fin --json report income --from 2026-01-01 --to 2026-01-31
    python -m fin --db fin.db serve --port 8080      # HTTP API; POSTs need header X-User

Commands: init, account, txn, balance, fx, convert, rule, import, budget, recurring, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), loan schedule,
user, audit, period, tax, customer, invoice, vendor, bill, reconcile, serve. See the task spec for
arguments. Without `--json` the same document is printed indented. User errors exit 2 (message on stderr,
nothing on stdout, nothing changed). Changing commands need `--user`; roles: admin, editor, viewer.

Layout: `fin/core.py` (money, dates, schema, posting, fx), `fin/cli.py` (parsing, auth, dispatch),
`books.py`, `ledger.py`, `bank.py`, `reports.py`, `invoices.py`, `api.py` (command modules; the API
calls the same commands through `cli.execute`).

## Assumptions
- Amounts with more than two decimals are rounded half up to cents on input.
- Every command runs in one DB transaction; on error all is rolled back.
- Commands on a database not yet initialised are a user error. Argparse errors are user errors (exit 2).
- init returns `{"currency","admin"}`; `period close` of an earlier month changes nothing and writes no audit entry.
- Transactions in different currencies must each balance per currency; a blank posting balances its own account's currency.
- rule add: invalid regex/empty pattern/unknown account is an error. Import: blank lines ignored; zero amount
  goes to `Income:Uncategorized`; closed-period check applies to every row (duplicates included); importing into
  an account whose currency differs from the book's fails (unbalanced).
- budget set: expense accounts only, non-negative. `actual` is the raw (debit-positive) sum; remaining = budget − actual.
- Recurring occurrences are tracked by index; a closed month in any occurrence fails the whole run.
- fx add rejects equal currencies and non-positive rates. `balance` keeps zero-sum currency entries.
- Ledger report converts foreign postings to the account's currency at each transaction's date. Trial balance
  puts conversion rounding residue on the largest row so totals agree.
- reconcile requires a user (it changes data) and writes an audit entry on each run.
- Invoice numbers count issued invoices per invoice-date year. Bills use status open/partial/paid.
- API: 401 for missing/unknown X-User, 403 for insufficient role, 400 user error, 404 unknown path.
