# fin — small-business finance

Python 3.12+, standard library only. Storage: SQLite. Money: `Decimal`, rounded half up to cents.

## Usage

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python3 -m fin init --currency EUR --admin alice
    python3 -m fin --user alice account add Assets:Bank
    python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --json balance
    python3 -m fin --db fin.db serve --port 8080      # HTTP API (POST needs header X-User)

Commands: `init`, `user`, `audit`, `account`, `txn`, `balance`, `fx`, `convert`, `rule`, `import`,
`budget`, `recurring`, `period`, `tax`, `customer`, `vendor`, `invoice`, `bill`, `reconcile`,
`loan schedule`, `report` (`income`, `balance-sheet`, `networth`, `budget`, `aging`, `tax`,
`trial-balance`, `ledger`), `serve`. User errors exit 2 with a message on stderr and change nothing
(each command runs in one SQLite transaction).

Code layout: `fin/core.py` (errors, money, dates, posting), `ledger.py`, `tools.py`, `billing.py`,
`reports.py`, `api.py`, `cli.py`. Tests: `python3 -m unittest discover -s tests` (takes ~2 min; they drive the CLI by subprocess).

## Assumptions

- Without `--json` the output is the same JSON, pretty-printed.
- Posting amounts are rounded to cents; every currency is assumed to have 2 decimals.
- Commands that change data need `--user`; `loan schedule`, `convert`, reports and lists are read-only (except `reconcile`, which writes cleared marks).
- `account add` audits only the named account, not auto-created parents.
- `period close` of an earlier month still writes an audit entry (it changes nothing else).
- `init` on a failed attempt leaves no database file.
- `convert`/reports: a direct FROM→TO rate (latest on or before the date) wins over an inverse rate even if the inverse is newer.
- Report conversion rounds per account; totals are sums of rounded figures (see reports handoff notes in code).
- Rate strings in `tax list` are shown exactly as given.
- Other choices are documented in the module docstrings and tests.
