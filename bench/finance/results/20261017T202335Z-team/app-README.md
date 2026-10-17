# fin — small-business finance system

Python 3.12+, standard library only. Run from the repository root (use `python3` if `python` is not on PATH):

    python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...

Global options come before the command. `--db` defaults to `./fin.db`. Output is always one JSON document
(`--json` prints it compact, otherwise indented). User errors exit 2, message on stderr, nothing on stdout, nothing changed.

    python -m fin init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice account add Expenses:Rent
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin balance
    python -m fin report income --from 2026-01-01 --to 2026-01-31
    python -m fin --user alice serve --port 8080      # HTTP API (POSTs need header X-User)

Commands cover: accounts, transactions, balances, fx/convert, CSV import with rules, budgets, recurring, reports
(income, balance-sheet, networth, trial-balance, ledger, budget, aging, tax), loans, users/roles/audit, closed periods,
tax codes, customers/invoices, vendors/bills, reconciliation, and the HTTP API. See the spec sections for exact shapes.

Layout: `fin/core.py` (errors, money/date helpers, schema, posting), one module per area (`ledger`, `imports`, `reports`,
`sales`, `purchases`, `bizreports`, `api`), tests in `tests/`: `python -m unittest discover -s tests`.
The API runs each request through the same command code (`fin.__main__.execute`), so documents match the CLI.

## Assumptions
- Output without `--json` is the same JSON, indented. `init` prints `{"currency","admin"}`; `account add` prints `{name,type,currency}`.
- Amounts with more than 2 decimals in postings are rounded half up to cents. Invoice prices and payments must have at most 2 decimals.
- `txn add`: blank description rejected. `txn list --account` matches the account or its descendants (path-aware).
- `balance` includes zero-sum accounts that have postings, and all ancestors. Currencies are per account.
- `fx add` rejects FROM == TO and non-positive rates; `convert` requires `--at`. Later rate on same date wins.
- `period close` of an earlier/equal month succeeds with no change and no audit entry; future months allowed. Reads need no user.
- Import: rules use `re.search`, case-insensitive, first match wins; zero amounts go to Income:Uncategorized; rule accounts must exist;
  malformed rows fail the whole import. Dedupe key (account, date, description, amount).
- `budget set` only for expense accounts; `report budget` assumes one currency per account tree.
- Recurring: postings validated at add; nothing posted until `run`; `run` is atomic; `--until` before start creates nothing.
- `reconcile` needs write permission; a bad `--clear` fails the whole command.
- Invoices: quantity > 0, price >= 0, tax rate >= 0, terms >= 0; payment account must be an asset account (not Assets:Receivable);
  invoice numbers count already-numbered invoices of that year. Bills: tax code may be empty, pay account must be an asset account,
  line amounts are not sign-checked; bill pay amount > 0 and <= balance.
- `report aging` and `report tax` use the book's currency without conversion; `--from` later than `--to` is an error.
- API binds 127.0.0.1, handles requests sequentially; unexpected internal errors are not turned into JSON 500s.
