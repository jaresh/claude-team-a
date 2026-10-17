# fin — small-business finance system

Python 3.12+, standard library only. Storage: SQLite. Money: `Decimal`.

    python -m fin init --currency EUR --admin alice
    python -m fin --user alice account add Assets:Bank
    python -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --json balance
    python -m fin serve --port 8080        # HTTP API (POSTs need an X-User header)

Global options (`--db PATH`, `--json`, `--user NAME`) come before the command. Run tests with
`python -m unittest discover -s tests`. Layout: `fin/book.py` (all logic), `fin/cli.py`, `fin/server.py`, `fin/util.py`.

Exit code 0 on success; user errors exit 2 with a message on stderr, nothing on stdout, and no change to the data
(every mutating command runs in one SQLite transaction, audit entry included).

## Assumptions

- Without `--json`, output is the same document, indented. `serve` logs its address to stderr.
- Amounts with more than two decimals are rounded half up to cents on input. Lines' `quantity` is kept as typed.
- `fx`/`convert`: the latest direct rate on or before the date is used; only if no direct rate exists, the inverse of
  the latest opposite-direction rate (`1 / rate`). Same-day rates: the last added wins.
- Reports convert each account's per-currency balance to the target currency (rounded to cents) and sum.
- `rule add` requires an existing account and a valid regex; patterns are matched with `re.search`, case-insensitive.
  Zero-amount import rows go to `Income:Uncategorized`. Blank CSV lines are ignored. A closed period check applies to
  every row of an import, including rows that would be skipped as duplicates.
- Budgets can only be set for expense accounts. `actual` counts postings in the account's own currency.
- `period close` is written to the audit log even if it changes nothing. `--user` given to read-only commands is ignored.
- `loan schedule` needs no database. Interest on row n uses the unrounded-payment convention in the spec.
- `invoice pay` / `bill pay` accounts must be existing asset accounts; payments may be dated before the document.
  `Liabilities:SalesTax` / `Assets:TaxReceivable` are only created when tax is non-zero.
- Invoice statuses: `draft`, `issued`, `partial`, `paid`; bills: `open`, `partial`, `paid`. Aging considers every
  non-draft invoice dated on or before the date, whatever its current status.
- `reconcile --clear` accepts `--clear 1 --clear 2` or `--clear 1 2`; matching uses the exact account (not
  descendants). Statements that clear a transaction dated after `--date` are rejected.
- Ledger report rows only include postings in the account's currency.
- API: `GET` on a missing invoice → 404; `POST` errors including missing invoice → 400; auth is checked before routing
  (401), then the role (403) before the body is parsed. Extra read endpoints: `/bills`, `/bills/ID`,
  `/reports/tax`, `/reports/trial-balance`.
