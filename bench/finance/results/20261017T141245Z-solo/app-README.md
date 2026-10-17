# fin — small-business finance system

Python 3.12+, standard library only. Storage: sqlite. Money: `decimal.Decimal`.

    python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python -m unittest discover -s tests      # run the tests

Quick start:

    python -m fin init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice account add Expenses:Rent
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --json balance
    python -m fin --db fin.db serve --port 8080

Commands: `init`, `account add|list`, `txn add|list`, `balance`, `fx add`, `convert`,
`rule add|list`, `import`, `budget set`, `recurring add|run`,
`report income|balance-sheet|networth|budget|aging|tax|trial-balance|ledger`, `loan schedule`,
`serve`, `user add|list`, `audit list`, `period close|status`, `tax add|list`,
`customer|vendor add|list`, `invoice create|issue|pay|show|list`, `bill create|pay|show|list`,
`reconcile`. Global options go before the command. User errors exit with 2, print to stderr, print
nothing to stdout and change nothing (every command runs in one database transaction).

Layout: `fin/book.py` (all logic), `fin/cli.py` (argparse, permissions, audit), `fin/server.py`
(HTTP API), `fin/util.py` (money/date helpers), `tests/`.

## Assumptions

- Without `--json`, output is the same JSON document, pretty-printed (no separate text format).
- Amounts on input must have at most two decimals (otherwise a user error); fx rates, tax rates,
  invoice quantities and prices may have any number of decimals. Currency codes are upper-cased.
- `convert`: a direct FROM→TO rate on or before the date wins over a newer TO→FROM rate; the inverse
  conversion divides by the rate. Same-date rates: the one added last wins. Duplicate tax codes,
  customers, vendors and users are user errors.
- `rule add` requires the account to exist and the pattern to compile; patterns use `re.search`.
- Import: blank CSV lines are ignored; descriptions are stripped; the dedupe key is
  (account, date, description, amount) among *imported* rows only; a zero amount goes to
  `Income:Uncategorized`. If the category account's currency differs from the account's, the
  transaction cannot balance and the import fails. Auto-created accounts do not add audit entries
  (one entry per command).
- Budgets can only be set on existing expense accounts; amounts of other currencies are converted
  to the book currency at month end for `report budget`.
- Recurring: occurrences are computed from the start date (not from the previous occurrence); the
  balancing posting is resolved when the rule is added; `recurring run` always writes an audit entry.
- Reports convert each account's per-currency sum at the report date, round, then add. Zero-sum
  accounts with postings show `0.00`. `networth` = assets − liabilities and accepts `--currency`.
  Ledger reports include only postings in the account's own currency.
- Audit: `period close` of an already-closed month is a no-op and writes no entry. A failed command
  writes nothing. Reads never need a user; `--user` is ignored for them.
- Invoices: the quantity is shown as given; the price is shown with two decimals when it has no more
  than two. Invoice and bill amounts are in the book currency; paying through an account in another
  currency fails (it cannot balance). Payments need an asset account and a positive amount.
  `report aging` counts issued/partial/paid invoices dated on/before the date with a remaining
  balance, ignoring later payments.
- Bills: line ACCOUNT must be an existing expense or asset account; `--ref` unique per vendor.
- Tax report: invoices count when not drafts; `by_code` lists codes that appear on a line in the period.
- Reconcile: `--clear` accepts repeated flags and/or several ids; cleared marks are per account and
  kept; only postings to exactly ACCOUNT count.
- HTTP: every POST is authenticated first (401 for a missing/unknown `X-User`, 403 for viewers)
  before the path or body are checked; a malformed body or user error is 400. `GET /invoices/ID`
  with an unknown id is 404 (other user errors are 400). Extra GET routes: `/bills`,
  `/reports/trial-balance`, `/reports/tax`, query filters on lists.
- The server binds to 127.0.0.1 by default (`--host` to change).
