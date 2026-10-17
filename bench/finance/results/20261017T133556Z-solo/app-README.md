# fin — small-business finance system

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API.

    python3 -m fin --db books.db init --currency EUR --admin alice
    python3 -m fin --db books.db --user alice account add Assets:Bank
    python3 -m fin --db books.db --user alice --json txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --db books.db --json balance
    python3 -m fin --db books.db serve --port 8000      # POST needs header "X-User: alice"

Global options (`--db`, `--json`, `--user`) come before the command. Without `--json` the result is printed as
indented JSON. Exit code 2 = user error (message on stderr, nothing on stdout, nothing changed).
Commands are those of the specification: `init account txn balance fx convert rule import budget recurring
report (budget income balance-sheet networth aging tax trial-balance ledger) loan user audit period tax customer
vendor invoice bill reconcile serve`. Every data-changing command runs in one SQLite transaction together with
its audit entry.

Tests: `python3 -m unittest discover -s tests`.

## Assumptions

- Amounts with more than two decimals are rounded half up to cents on input. Currency codes are case-insensitive, stored upper case.
- Dates and months are validated strictly (`YYYY-MM-DD`, `YYYY-MM`).
- `rule add` requires the target account to exist; the regex must compile. Rules use `re.search`.
- `import`: blank CSV lines are ignored; a malformed row fails the whole import. All rows (even duplicates) are checked against closed periods. Dedup keys on (account, date, description, amount).
- `fx add`: rates must be positive and the currencies differ. Same-date rates: the later one added wins. A FROM→TO rate (any date ≤ DATE) takes precedence over the inverse of a TO→FROM rate.
- Reports convert each account's balance and round it, then sum the rounded values, so with exchange rates the balance-sheet equation can be off by a cent. Income/balance-sheet/networth accept `--currency`; trial balance is always in the book currency.
- `report networth` with `--from` after `--to` is a user error. Net worth = asset accounts − liability accounts (equity and P&L accounts are ignored).
- `report budget` amounts are in the account's own currency (no conversion). `budget set` requires an existing expense account.
- `recurring add` allows duplicate names; the elided posting is resolved when added. `recurring run` is all-or-nothing (a closed month fails the whole run). Occurrences are created ordered by date.
- `period close` of an earlier month leaves the state unchanged but still writes an audit entry (it is a data-changing command); the same holds for an `import` or `recurring run` that creates nothing.
- Duplicate tax codes, customers, vendors, users and accounts are user errors. Tax rates are stored as given text.
- Invoice line format is `DESCRIPTION;QUANTITY;PRICE;TAXCODE` (split from the right, so descriptions may contain `;`; all four fields required, TAXCODE may be empty). Bill lines: `DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE`.
- Payment accounts for invoices and bills must be asset accounts; payments must be positive. Posting accounts like `Assets:Receivable` that exist in another currency make the transaction fail as unbalanced.
- Aging counts invoices that have been issued (numbered); bills count from their creation date. Buckets: days past due ≤0 current, 1–30, 31–60, 61–90, 91+ → `90+`.
- `report tax` includes a code in `by_code` if any issued invoice/bill line in the period used it (even with a zero tax amount).
- `reconcile`: "a posting to ACCOUNT" means the exact account, not descendants. Clearing an already cleared transaction is fine.
- `report ledger` includes ACCOUNT's descendants that share ACCOUNT's currency.
- Audit timestamps are UTC, second resolution, `YYYY-MM-DDTHH:MM:SSZ`.
- API: user errors → 400; a missing invoice/bill in the path → 404 (also on `POST`); authentication (401/403) is checked after the route is known (unknown paths → 404 regardless of user) and before the body is read. A viewer is 403 for every POST. `GET /transactions` accepts `account`, `from`, `to`; `GET /invoices` accepts `status`; `GET /audit` accepts `by`; report endpoints accept `currency`.
- The `python` executable may be called `python3` on your system.
