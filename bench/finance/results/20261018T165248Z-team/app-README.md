# fin — small-business finance system

Double-entry bookkeeping, invoicing, bills, budgets, reports and a JSON HTTP API.
Python 3.12+, standard library only (SQLite storage, `Decimal` money).

## Quick start

```sh
python3 -m fin init --currency EUR --admin alice
python3 -m fin --user alice account add Assets:Bank
python3 -m fin --user alice account add Expenses:Rent
python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent \
    --posting Expenses:Rent=900 --posting Assets:Bank
python3 -m fin --json balance
python3 -m fin report income --from 2026-01-01 --to 2026-01-31
python3 -m fin serve --port 8080        # JSON API
```

Global options go before the command: `--db PATH` (default `./fin.db`), `--json` (print exactly
one JSON document), `--user NAME` (acting user; required for every command that changes data).
Exit codes: 0 success, 2 user error (message on stderr, nothing on stdout, nothing changed).
Without `--json`, lists of records print as a table and other documents as indented JSON.
`python3 -m fin --help` and `python3 -m fin COMMAND --help` list every option.

## Commands

| Area | Commands |
|---|---|
| Books, users | `init --currency CUR --admin NAME`, `user add NAME --role admin\|editor\|viewer`, `user list`, `audit list [--by NAME]` |
| Periods | `period close MONTH`, `period status` |
| Accounts | `account add NAME [--currency CUR]`, `account list` |
| Transactions | `txn add --date D --desc T --posting ACC=AMT [--posting ACC]...`, `txn list [--account P] [--from D] [--to D]`, `balance [--at D]` |
| FX | `fx add DATE FROM TO RATE`, `convert AMOUNT FROM TO --at DATE` |
| Bank | `rule add PATTERN ACCOUNT`, `rule list`, `import FILE --account ACC [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]`, `reconcile ACC --date D --balance AMT [--clear ID]...` |
| Budgets | `budget set ACCOUNT MONTH AMOUNT`, `report budget MONTH` |
| Recurring | `recurring add NAME --every monthly\|weekly\|yearly --start D --posting ...`, `recurring run --until D` |
| Reports | `report income --from D --to D [--currency C]`, `report balance-sheet --at D [--currency C]`, `report networth --from M --to M [--currency C]`, `report trial-balance --at D`, `report ledger ACC --from D --to D`, `report aging --at D [--payables]`, `report tax --from D --to D` |
| Loans | `loan schedule PRINCIPAL RATE MONTHS --start D` (no database needed) |
| Sales | `tax add CODE RATE`, `tax list`, `customer add NAME [--terms DAYS]`, `customer list`, `invoice create --customer N --date D --line "DESC;QTY;PRICE;TAXCODE"...`, `invoice issue ID`, `invoice pay ID AMT --date D --account ACC`, `invoice show ID`, `invoice list [--status S]` |
| Purchases | `vendor add NAME [--terms DAYS]`, `vendor list`, `bill create --vendor N --ref R --date D --line "DESC;AMOUNT;ACCOUNT;TAXCODE"...`, `bill pay ID AMT --date D --account ACC`, `bill show ID`, `bill list [--status S]` |
| API | `serve --port N` |

Roles: `admin` everything; `editor` everything except `user add` and `period close`; `viewer`
read-only commands.

## HTTP API

`python3 -m fin --db fin.db serve --port 8080` serves the same JSON documents as `--json`:
`GET /accounts`, `/transactions`, `/balances?at=D`, `/reports/income?from=D&to=D`,
`/reports/balance-sheet?at=D`, `/invoices`, `/invoices/ID`, `/reports/aging?at=D[&payables=1]`,
`/audit`; `POST /transactions`, `/invoices`, `/invoices/ID/issue`, `/invoices/ID/payments`.
POSTs need the `X-User` header (401 missing/unknown user, 403 role not allowed); user errors
give 400, unknown paths and unknown invoice ids 404, all with `{"error": "..."}`.

```sh
curl -X POST localhost:8080/transactions -H 'X-User: alice' -d \
  '{"date":"2026-01-05","description":"Rent","postings":[{"account":"Expenses:Rent","amount":"900"},{"account":"Assets:Bank"}]}'
```

## Layout and tests

`fin/core.py` (money, dates, storage, accounts, posting, fx, audit), `fin/cli.py` (argument
parsing, permissions, one SQLite transaction per write command), `fin/books.py` (sections 1-4,
11, 12), `fin/bank.py` (import, rules, budgets, recurring, reconcile), `fin/reports.py`
(balances, statements, loans, ledger), `fin/invoicing.py` (tax, customers, vendors, invoices,
bills, aging, tax report), `fin/api.py` (HTTP server; translates each request into the
equivalent command, so CLI and API behave identically).

Run the tests: `python3 -m unittest discover -s tests`.

## Assumptions

- Amounts typed with more than two decimals are rounded half up to cents when stored
  (`0.005` → `0.01`). FX rates and tax rates are kept exactly as given.
- `init` with an invalid currency or on an existing database creates/changes nothing; every other
  command on a missing database is a user error (the file is not created).
- Account names: non-empty colon-separated segments. An account's type comes from its first
  segment; parent accounts created implicitly take the new account's currency.
- `account add` of an existing account (including one created implicitly as a parent) is an error.
- In a transaction, the posting without an amount balances its own account's currency; all other
  currencies must already balance. A zero-amount posting is allowed.
- `fx add` with the same date and pair replaces the earlier rate; the rate must be positive and
  FROM ≠ TO. Currency codes are case-insensitive and stored upper-case.
- `convert` and reports round converted amounts to cents. Reports convert each account's balance
  per currency separately, round, then sum the shown values, so totals always add up.
  `retained_earnings` is the negated sum of the converted income and expense balances.
- `report ledger` on an account whose descendants use another currency converts each posting at
  its own date. `report networth` also accepts `--currency`.
- `rule add` requires an existing account and a valid regular expression; rules match anywhere in
  the description (`re.search`).
- Import: every row must have a valid date and amount (otherwise the whole import fails); the
  dedup key is (account, date, description, amount) of rows previously imported by `import`
  (transactions entered by hand are not considered).
- Import: blank CSV lines are ignored; a row with too few columns is an error. The
  `*:Uncategorized` accounts are in the book currency, so a row whose category would be one of
  them cannot be imported into an account in another currency (unbalanced); use rules instead.
- Budgets may only be set on existing expense accounts, with non-negative amounts; `actual`
  converts other-currency postings to the book currency at the month's last day;
  `remaining` may be negative.
- Recurring names are unique. `recurring run` with no occurrences due still writes an audit entry.
- `reconcile` is a write command (it stores cleared marks) and needs an existing account.
  `--clear` of an already-cleared transaction is allowed.
- `period close` of an earlier month than the closed one succeeds without changing anything (and
  is still audited).
- Invoice and bill `--line` fields are separated by `;` (descriptions cannot contain `;`); all four
  fields are required, the tax code may be empty. Payments must be positive, go to an existing
  asset account, and draft invoices cannot be paid.
- Invoice prices are shown with two decimals; quantities as given. Quantities, prices, bill
  amounts, tax rates and payment terms must not be negative; at least one `--line` is required.
  `invoice list` / `bill list` return full documents.
- `report aging` buckets: ≤0 days past due `current`, 1-30, 31-60, 61-90, >90 `90+`.
- `report tax` counts invoices by issued status (issued, partial, paid) and all bills, by their
  dates; `by_code` lists only codes appearing on those documents' lines.
- Loan RATE 0 uses PRINCIPAL / MONTHS; MONTHS must be a positive integer.
- The API server is single-threaded and opens the database per request.
