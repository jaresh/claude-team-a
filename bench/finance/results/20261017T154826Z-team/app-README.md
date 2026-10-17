# fin — small-business finance system

Python 3.12+, standard library only. Run `python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`.

    python -m fin init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --json balance
    python -m fin serve --port 8000        # HTTP API (POSTs need X-User header)

Tests: `python -m unittest discover -s tests`

Layout: `fin/core.py` (money, dates, schema, posting), `fin/cli.py` (parsing, permissions, audit, atomic commands),
`fin/cmd_*.py` (commands), `fin/server.py` (HTTP API).

## Assumptions
- Without `--json`, output is the same JSON, pretty-printed.
- Every data-changing command runs in one SQLite transaction; any error rolls back everything and exits 2.
- `balance-sheet`: `total_equity` = total assets − total liabilities, `retained_earnings` is the balancing part
  (equals income − expenses in a single currency; differs only by rounding when converting).
- `trial-balance` puts any per-account conversion rounding residue on the largest balance so totals match.
- `report ledger` converts nothing when currencies match; otherwise each posting at its own date.
- `report budget` and `report networth` use the book currency (no `--currency`).
- Unspecified details (ids, ordering, validation of dates/currencies) follow the spec literally; invalid dates,
  amounts or currencies are user errors. Argparse errors also exit 2.
- Other per-module assumptions are in `.claude/team/handoff/*.txt` (not committed).
