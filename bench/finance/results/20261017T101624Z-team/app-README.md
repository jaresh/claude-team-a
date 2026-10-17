# fin — small-business finance system

Python 3.12+, standard library only. Run from the repository root:

    python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
    python3 -m unittest discover -s tests

Quick start:

    python3 -m fin init --currency EUR --admin alice
    python3 -m fin --user alice account add Assets:Bank
    python3 -m fin --user alice account add Expenses:Rent
    python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin balance
    python3 -m fin report income --from 2026-01-01 --to 2026-01-31
    python3 -m fin --db fin.db serve --port 8080      # HTTP API (POST needs header X-User)

Commands: `init account user audit period txn balance fx convert rule import budget recurring
report (income balance-sheet networth budget trial-balance ledger aging tax) loan tax customer
invoice vendor bill reconcile serve`. Layout: `fin/core.py` (shared helpers, schema),
`fin/cli.py` (dispatch, permissions, per-command DB transaction), one module per feature area.

## Assumptions
- Output is JSON in both modes (`--json` prints it compact, otherwise indented). Money is rounded half up to cents when parsed.
- Every command runs in one DB transaction; a user error rolls back everything and `init` removes a half-made database.
- Commands that need an existing book fail (exit 2) if the database file does not exist. `loan schedule` needs no database.
- `--user` is checked for data-changing commands only; read-only commands ignore an unknown user.
- `reconcile` always writes an audit entry, even without `--clear`.
- `fx add` rejects equal currencies and non-positive rates; `convert` requires `--at`.
- `txn list --account` matches whole path segments (`Assets:Ban` does not match `Assets:Bank`).
- Reconciliation uses the exact account's postings, not descendants.
- Tax report counts issued/partial/paid invoices (not drafts) by invoice date.
- The API listens on 127.0.0.1; no authentication beyond the X-User header.
- Other choices made by individual modules are in `.claude/team/handoff/*.txt` (not versioned).
