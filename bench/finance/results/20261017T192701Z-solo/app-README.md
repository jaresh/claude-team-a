# fin — small-business finance system

Python 3.12+, standard library only. Storage is a single SQLite file; money is `decimal.Decimal`.

## Usage

```
python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
python3 -m fin --db books.db init --currency EUR --admin alice
python3 -m fin --db books.db --user alice account add Assets:Bank
python3 -m fin --db books.db --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --db books.db --json balance
python3 -m fin --db books.db serve --port 8080      # HTTP API; POSTs need header X-User
python3 -m unittest discover -s tests               # run the tests
```

(Use `python` if that is what your system calls Python 3.)

Command groups: `init account txn balance fx convert rule import budget recurring user audit period tax
customer vendor invoice bill reconcile report loan serve`. Reports: `report income|balance-sheet|networth|budget|aging|tax|trial-balance|ledger`.
Exit code 0 on success, 2 on any user error (message on stderr, nothing on stdout, nothing changed:
each command runs in one SQLite transaction that is rolled back on error).
With `--json` the command prints one compact JSON document; without it the same document is pretty-printed.

## Assumptions

- Commands that change data need `--user`; `init` is the exception (the new admin is the acting user, audit entry 1).
  A viewer (or missing/unknown user) is rejected before anything else is checked. Read-only commands ignore `--user`.
- `reconcile`, `recurring run` and `import` are data-changing and are audited even if they end up creating nothing.
  Implicit account creation (Income:Sales, Expenses:Uncategorized, ...) is not audited separately.
- Posting/other amounts with more than two decimals are rounded half up to cents on input. Invoice quantity
  and price may have more decimals; line net is rounded. Price is shown with two decimals unless given with more.
- `rule add` requires the target account to exist. `import` zero amounts go to `Income:Uncategorized`.
  Blank CSV rows are ignored; a malformed row fails the whole import. Duplicate detection uses the
  (account, date, description, amount) of earlier imports only (including earlier rows of the same file).
  The closed-period check on `import`/`recurring run` covers every row/occurrence, including skipped ones.
- `balance` never converts (per-currency sums). `ledger` converts descendant postings in a
  different currency into the ledger account's currency at the posting date. Budget "actual" converts the same way
  (at the month's end). Reports convert each account's per-currency sum at the report date; totals are sums of the
  rounded per-account values, so with conversions the balance-sheet identity can be off by cents.
- `report networth` also accepts `--currency`; it counts asset and liability accounts only.
- Exchange rates: on the same date the later `fx add` wins; the direct rate is preferred over the inverse
  whenever one exists on or before the date, regardless of which is newer.
- Recurring transactions are tracked by occurrence date; the posting list is stored as given (so a balancing posting
  is recomputed on each run). Duplicate recurring names are allowed.
- Invoice numbers count issued invoices per invoice-date year. Invoice `pay` and bill `pay` need an existing asset account.
  Paying an invoice before its date is allowed. Drafts can be created in closed periods (only issuing is blocked).
- Invoice/bill payments reduce `paid`/`balance` in the invoice's own right; aging counts only payments dated on/before the date.
- `report tax` counts issued (non-draft) invoices and all bills dated in the period; `by_code` lists codes of lines in the period.
- Reconcile marks and `uncleared` consider postings to exactly the given account (not descendants).
  Clearing the same transaction twice is fine.
- Trial balance and `rows` use the posting account names (no ancestors) and convert to the book currency at DATE.
- API: user errors are 400, except missing invoice/bill on `GET` (404). Unknown paths 404 (before authentication).
  Missing/unknown `X-User` is 401 and an insufficient role 403 (checked before the body is parsed). Invoice line
  quantities and prices may be JSON numbers or strings. Extra endpoints: `/bills`, `/bills/ID`, `/reports/tax`,
  `/reports/trial-balance`, and the query parameter `currency` for the income/balance-sheet reports.
- Account names may not contain `=` or `;`, nor empty segments or surrounding spaces. Users named in `init --admin` are trimmed.
