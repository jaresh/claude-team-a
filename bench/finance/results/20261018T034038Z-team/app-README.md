# fin — small-business finance system

Python 3.12+, standard library only (sqlite3, Decimal, http.server, unittest).

## Use

    python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...

Global options go before the command; `--db` defaults to `./fin.db`. Start with
`python -m fin init --currency EUR --admin alice`, then pass `--user alice` for every
command that changes data. Commands: `init`, `user`, `audit`, `period`, `account`, `txn`,
`balance`, `fx`, `convert`, `rule`, `import`, `budget`, `recurring`, `loan`, `tax`,
`customer`, `invoice`, `vendor`, `bill`, `reconcile`, `report` (income, balance-sheet,
networth, budget, aging [--payables], tax, trial-balance, ledger), `serve --port N`
(HTTP API; POST needs `X-User`). With `--json` a command prints one JSON document;
without it the same JSON is pretty-printed. User errors exit 2 with a message on stderr.

Layout: `fin/cli.py` (parsing, permissions, transactions, init/user/audit/period),
`fin/core.py` (posting, accounts, rates, audit), `fin/money.py`, `fin/db.py` (schema),
one module per area (`ledger`, `importer`, `sales`, `purchases`, `reports`, `api`).

## Tests

    python -m unittest discover -s tests

## Assumptions

- Every command runs in one SQLite transaction; any user error rolls everything back.
- A data-changing command with no/unknown `--user` is a user error; a known user with a
  read-only command or unknown `--user` on a read command: unknown user is an error, none is fine.
- Output shapes not given in the spec: `account add` → `{name,type,currency}`, `fx add` →
  `{date,from,to,rate}`, `budget set` → `{account,month,budget}`, `user add`/`init` echo their input.
- `fx add` rejects FROM = TO and rates <= 0; the same date/pair replaces the rate. A direct
  FROM→TO rate on or before the date is preferred over an inverse one, even if older.
  `convert` requires `--at`.
- Reports convert each account's per-currency balance at the report date, round, then sum.
- `balance` shows accounts whose postings sum to zero as `"0.00"`.
- Currency codes are upper-cased 3 letters; condition on `init`, `--currency`, `fx`.
- Import: dedupe key is (account, date, description, amount); the same row into another
  account is imported again; first matching rule wins (`re.search`, case-insensitive);
  a zero amount goes to `Income:Uncategorized`; import audit is written even if all rows skip.
  A rule's account must exist when the rule is added.
- Budgets: expense accounts only, amount >= 0. Recurring: a start date in a closed month is
  accepted on `add` and fails on `run`; occurrences are computed from the start date.
- Invoices/bills need at least one line; lines have exactly four `;`-separated fields;
  negative quantity/price/amount is an error. Payments must be positive, <= balance, into an
  asset account (not Assets:Receivable for invoices). Bill refs are unique per vendor.
  Payment dates are not checked against the document date.
- Aging excludes drafts; tax report counts non-draft invoices and all bills.
- Reports with a reversed range (e.g. networth from > to) give an empty result or an error as
  documented in the tests.
- API: bad JSON → 400; the API runs the same code as the CLI per request (so errors match).
