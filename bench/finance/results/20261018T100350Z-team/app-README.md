# fin — small-business finance system

Python 3.12+, standard library only (sqlite3, decimal, http.server, unittest).

## Use

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...

Global options come before the command; `--db` defaults to `./fin.db`. With `--json` a command
prints exactly one JSON document. A user error exits with code 2, prints a message to stderr,
and changes nothing.

    python3 -m fin --db b.db init --currency EUR --admin alice
    python3 -m fin --db b.db --user alice account add Assets:Bank
    python3 -m fin --db b.db --user alice account add Expenses:Rent
    python3 -m fin --db b.db --user alice txn add --date 2026-01-05 --desc Rent \
        --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin --db b.db --json balance
    python3 -m fin --db b.db serve --port 8080

Commands: `init`, `account`, `txn`, `balance`, `fx`, `convert`, `rule`, `import`, `budget`,
`recurring`, `report` (income, balance-sheet, networth, budget, aging, tax, trial-balance,
ledger), `loan schedule`, `user`, `audit`, `period`, `tax`, `customer`, `vendor`, `invoice`,
`bill`, `reconcile`, `serve`. Run any with `-h` for its options.

Layout: `fin/core.py` (money, dates, schema, posting, fx), `fin/cli.py` (dispatch, permissions,
transactions), one module per feature area, `tests/` (`python3 -m unittest discover -s tests`,
about 2.5 minutes because most tests call the CLI as a subprocess).

## Assumptions

- Each command runs in one SQLite transaction; a user error rolls everything back.
- Posting amounts are rounded half up to cents on input. Account names must have no empty segment.
- `init` requires a 3-letter uppercase currency. Argument-parsing errors are user errors (exit 2).
- Viewers and users-less calls may run read-only commands; `serve` needs no user, and API
  GET requests need none. Write commands fail with 401 (missing/unknown user) or 403 over HTTP.
- Closing a month earlier than the closed one still writes an audit entry (`period.close`) but changes nothing else.
- Several exchange rates on one date: the last added wins.
- Audit entries are written for every successful data-changing command, including those that change nothing in effect.
- Where the spec is silent, module-level docstrings and tests document the decision
  (see also `.claude/team/handoff/*.txt` if present).
