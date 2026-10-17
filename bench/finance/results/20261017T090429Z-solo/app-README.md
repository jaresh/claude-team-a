# fin — personal and small-business finance

Python 3.12+, standard library only. SQLite storage, `Decimal` money, `http.server` API.

    python -m fin [--db PATH] [--json] COMMAND ...      # --db defaults to ./fin.db

    python -m fin init --currency EUR
    python -m fin account add Assets:Bank
    python -m fin account add Expenses:Rent
    python -m fin txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python -m fin --json balance
    python -m fin --json report income --from 2026-01-01 --to 2026-01-31
    python -m fin serve --port 8080

Commands: `init`, `account add|list`, `txn add|list`, `balance`, `fx add`, `convert`,
`rule add|list`, `import`, `budget set`, `report budget|income|balance-sheet|networth`,
`recurring add|run`, `loan schedule`, `serve`. Global options go before the command.
User errors exit 2 with a message on stderr and nothing on stdout. Without `--json`
a plain-text rendering is printed. Tests: `python -m unittest discover -s tests`.

## Assumptions

- Amounts are rounded half-up to cents on input (e.g. `3000.005` → `3000.01`); input must be plain decimals (no thousands separators, exponent, NaN).
- Currency codes are case-insensitive 3-letter codes, stored upper-case. Descriptions of `txn add`/`recurring add` must be non-empty; imported descriptions may be empty.
- Account name segments must be non-empty with no surrounding whitespace. `account add` of a name that already exists (including one auto-created as a parent) is an error.
- An elided posting takes the amount balancing its own account's currency; all other currencies must then balance by themselves.
- `txn list --account` matches the account or its descendants on `:` boundaries (`Assets:Ban` does not match `Assets:Bank`).
- FX: if any FROM→TO rate exists on or before the date it is used (the latest, ties by insertion order), even if a TO→FROM rate is newer; the inverse is `1/rate` (28 digits) only otherwise. Rates must be positive between different currencies.
- Reports: each account's total is converted (unrounded, per currency) and rounded once; totals are sums of the displayed account values, so the balance-sheet identity can be off by a cent when rounding after conversion. Reports list accounts by the name postings are on (no roll-up to parents). `report networth` and `report budget` convert at the month's last day; budget amounts are taken to be in the book currency; `networth` also accepts `--currency`.
- `rule add` requires the target account to exist and the pattern to compile; matching uses `re.search`, case-insensitive. The category account must share the bank account's currency, otherwise the import fails (an error rolls back the whole import). Blank CSV lines are ignored; with `--skip-header` only the first line is dropped. De-duplication is keyed on (account, date, description, amount) and remembered even if the transaction is later changed.
- `budget set` requires an existing expense-type account (parents like `Expenses` allowed), non-negative amount.
- Recurring occurrences are tracked by index from the start date, so re-running never duplicates; descriptions equal the name; names need not be unique. A recurring template's accounts must still exist when run.
- Loan: months must be an integer ≥ 1, principal > 0, rate ≥ 0.
- HTTP: the server binds to 127.0.0.1 only and has no authentication; it handles requests serially. Extra GET query parameters: `/transactions?account=&from=&to=`, `currency=` on both reports. `/reports/*` need their date parameters (400 otherwise). POST amounts may be JSON strings or numbers.
