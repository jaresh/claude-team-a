# fin — small-business finance books

Double-entry bookkeeping with invoices, bills, budgets, bank import, reports and a JSON HTTP
API. Python 3.12+, standard library only. Data lives in one SQLite file.

## Usage

```
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
```

`--db` defaults to `./fin.db`. `--json` prints exactly one JSON document; without it output is
plain text (`key: value` lines or tab-separated tables). Commands that change data need
`--user`. A user error exits 2 with a message on stderr and changes nothing.

```sh
python -m fin init --currency EUR --admin alice
python -m fin --user alice account add Assets:Bank
python -m fin --user alice account add Expenses:Rent
python -m fin --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python -m fin --json balance --at 2026-01-31
python -m fin --json report income --from 2026-01-01 --to 2026-01-31
python -m fin serve --port 8080          # HTTP API; POSTs need header X-User
```

Commands:

| Area | Commands |
|---|---|
| Books | `init`, `account add/list`, `txn add/list`, `balance`, `fx add`, `convert` |
| Users | `user add/list`, `audit list [--by]`, `period close/status` |
| Banking | `rule add/list`, `import FILE --account A`, `budget set`, `recurring add/run`, `reconcile` |
| Sales/purchases | `tax add/list`, `customer add/list`, `invoice create/issue/pay/show/list`, `vendor add/list`, `bill create/pay/show/list` |
| Reports | `report income / balance-sheet / networth / budget / aging [--payables] / tax / trial-balance / ledger`, `loan schedule` |
| API | `serve --port N` |

Run `python -m fin COMMAND --help` for each command's options.

## Layout

- `fin/core.py`: the shared parts, meaning money (Decimal, round half up), dates, the SQLite schema, users and audit, accounts, posting transactions (balancing and closed-period checks) and FX.
- `fin/cli.py`: global options and dispatch. Every write command runs in one DB transaction, rolled back on error.
- `fin/books.py`, `fin/banking.py`, `fin/statements.py`, `fin/invoicing.py`: the commands, each over plain domain functions.
- `fin/api.py`: the HTTP server, which calls the same domain functions.
- `tests/`: `python -m unittest discover -s tests` (acceptance tests `test_accept_*`, unit tests per module).

## Assumptions

- Amounts given on input are rounded half up to cents. Stored as decimal text, never floats.
- Account names: non-empty colon-separated segments. Currencies: 3 letters, upper-cased.
- `init` on a file that exists but was never initialized is allowed. Any other command on a
  missing or uninitialized database is a user error.
- Read-only commands ignore `--user` (even an unknown name). Only `init` works without a user
  among write commands.
- A blank posting gets the amount that balances *its own account's currency*; every currency
  must then sum to zero. A posting may be zero.
- `balance` lists all currencies an account has postings in, including `"0.00"` sums.
- `fx add`: the rate must be positive; several rates on the same date: the last one added wins.
- `period close` of an earlier month still writes an audit entry (it is a successful command).
- Import: the CSV is read with Python's `csv` module; a bad date or amount in any row fails the
  whole import. Duplicate detection key: (account, date, description, amount). Rule accounts
  must exist when the rule is added. An unreadable file is a user error.
- Recurring: names are unique. Occurrences already created are remembered per date, so a later
  `run` with a later date only adds new ones. Occurrences before the period close make `run` fail.
- Reconcile with no `--clear` still counts as a change (audit entry `reconcile`).
- Reports with `--currency`: each account's balance in each currency is converted at the
  report date and rounded, and totals are sums of the shown values. In multi-currency books,
  that rounding can leave the trial balance's debit and credit totals (or balance-sheet sides)
  a cent apart. A currency with no rate is an error even if its balance is zero.
  `report ledger` converts postings into the account's currency at `--to`.
- `from` after `to` is a user error.
- Invoices/bills: at least one line. Quantity > 0, price and bill line amounts ≥ 0, price
  rounded to cents. Payment accounts must be asset accounts and amounts > 0. Bill refs are
  unique per vendor. Invoice numbers are assigned at issue time, counted per invoice-date year.
  Drafts are excluded from aging and the tax report. The tax report's `by_code` lists every code on
  a line of an issued invoice or bill in the period (including zero tax).
- Aging for bills uses bills dated on or before the date and payments on or before it.
- API: binds to 127.0.0.1. An empty POST body counts as `{}`. Unknown invoice id → 400
  (a user error), a malformed path such as `/invoices/abc` → 404. Bad JSON → 400.
- Audit time is UTC, `YYYY-MM-DDTHH:MM:SSZ`.
