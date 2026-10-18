# fin — small-business finance books

A double-entry bookkeeping tool with a command-line interface and a small JSON
HTTP API. It is written in Python 3.12+ and uses only the standard library
(SQLite for storage).

## Running

```sh
python -m fin [--db PATH] [--json] [--user NAME] COMMAND ...
```

- `--db PATH` — the book file. Defaults to `./fin.db`.
- `--json` — print exactly one JSON document on stdout.
- `--user NAME` — the acting user. Required for every command that changes data; reads ignore it.

Exit codes: `0` on success. `2` for a user error (bad input, unknown account,
unbalanced transaction, closed period, missing permission). A user error prints
`error: ...` on stderr and changes nothing.

Tests:

```sh
python -m unittest discover -s tests
```

(On machines where only `python3` exists, use `python3` instead.)

## Setting up a book

```sh
python -m fin init --currency EUR --admin ann
python -m fin --user ann account add Assets:Bank
python -m fin --user ann account add Income:Sales
python -m fin --user ann txn add --date 2026-01-05 --desc "Sale" \
    --posting Assets:Bank=100.00 --posting Income:Sales
```

Accounts are colon paths. The first segment sets the type: `Assets` → asset,
`Liabilities` → liability, `Equity` → equity, `Income` → income, `Expenses` → expense.

Amounts are strings with exactly two decimals (`12`, `12.5` and `12.50` are all
accepted; more than two decimals is an error). Rounding is half-up. Zero is
always printed as `0.00`, never `-0.00`. Dates are `YYYY-MM-DD`, months are `YYYY-MM`.

## Command reference

| Area | Commands |
| --- | --- |
| Book | `init --currency CODE --admin NAME` |
| Users | `user add NAME --role {admin,editor,viewer}`, `user list` |
| Audit | `audit list [--by NAME]` |
| Accounts | `account add PATH`, `account list` |
| Transactions | `txn add --date D --desc TEXT --posting ACCOUNT=AMOUNT [--posting ACCOUNT] ...`, `txn list [--account A] [--from D] [--to D]` |
| Balances | `balance [--at D]` |
| FX | `fx add DATE FROM TO RATE`, `convert AMOUNT FROM TO [--at D]` |
| Import | `import FILE --account A [--date-col N --desc-col N --amount-col N --skip-header]` |
| Rules | `rule add PATTERN ACCOUNT`, `rule list` |
| Budgets | `budget set ACCOUNT MONTH AMOUNT`, `report budget MONTH` |
| Recurring | `recurring add NAME --every {monthly,weekly,yearly} --start D --posting ...`, `recurring run --until D` |
| Loans | `loan schedule PRINCIPAL RATE MONTHS --start D` |
| Reconcile | `reconcile ACCOUNT --date D --balance AMOUNT [--clear TXN_ID ...]` |
| Tax codes | `tax add CODE RATE`, `tax list` |
| Customers | `customer add NAME [--terms DAYS]`, `customer list` |
| Vendors | `vendor add NAME [--terms DAYS]`, `vendor list` |
| Invoices | `invoice create --customer C --date D --line "DESC;QTY;PRICE;TAX"...`, `invoice issue ID`, `invoice pay ID AMOUNT --date D --account A`, `invoice show ID`, `invoice list [--status S]` |
| Bills | `bill create --vendor V --ref R --date D --line "DESC;AMOUNT;ACCOUNT;TAX"...`, `bill pay ID AMOUNT --date D --account A`, `bill show ID`, `bill list [--status S]` |
| Periods | `period close YYYY-MM` (admin), `period status` |
| Reports | `report income --from D --to D`, `report balance-sheet --at D`, `report networth --from YYYY-MM --to YYYY-MM`, `report trial-balance --at D`, `report ledger ACCOUNT --from D --to D`, `report aging --at D [--payables]`, `report tax --from D --to D`, `report budget MONTH` |
| Server | `serve --port N` |

Run `python -m fin COMMAND --help` for the full options of any command.

### Documents

- An invoice line is `"DESCRIPTION;QUANTITY;PRICE;TAX_CODE"`. The TAX_CODE part may be empty.
- A bill line is `"DESCRIPTION;AMOUNT;ACCOUNT;TAX_CODE"`.
- Per-line net is `round(quantity × price)` and tax is `round(net × rate / 100)`.
- Issuing an invoice assigns `INV-YYYY-NNNN` (numbered per invoice-date year) and posts
  Assets:Receivable (+total), Income:Sales (−net) and Liabilities:SalesTax (−tax, if any).
- Creating a bill posts each line's account (+net), Assets:TaxReceivable (+tax) and
  Liabilities:Payable (−total).
- Payments post the chosen account against the receivable or payable.
- Invoice status is `draft`, `issued`, `partial` or `paid`.
- Aging buckets: `current`, `1-30`, `31-60`, `61-90`, `90+` days past due.

## Roles and permissions

| Action | admin | editor | viewer |
| --- | --- | --- | --- |
| Read commands and reports | yes | yes | yes |
| Record changes (transactions, documents, imports, ...) | yes | yes | no |
| `user add`, `period close` | yes | no | no |

A change without `--user` is a user error. An unknown user is a user error.
Over HTTP, an unknown or missing `X-User` is 401 and a role violation is 403.

## Closed periods

`period close YYYY-MM` closes that month and every earlier one. Closing an earlier
month than one that is already closed changes nothing and still exits 0.
`period status` prints `{"closed_through": "2026-01"}`, or `null` when nothing is closed.

Anything that would post a transaction dated in a closed month is rejected:
`txn add`, `import`, `recurring run`, `invoice issue`, `invoice pay`, `bill create`
and `bill pay`. For `import` and `recurring run`, if any row falls in a closed
month the whole operation fails and nothing is written.

## HTTP API

```sh
python -m fin --db fin.db serve --port 8080
# serving on http://127.0.0.1:8080
```

The server binds to `127.0.0.1` only, is single-threaded, and uses one SQLite connection.

Reads (no `X-User` needed):

| Path | Query |
| --- | --- |
| `GET /accounts` | |
| `GET /transactions` | `account`, `from`, `to` |
| `GET /balances` | `at` |
| `GET /reports/income` | `from`, `to`, `currency` |
| `GET /reports/balance-sheet` | `at`, `currency` |
| `GET /invoices` | `status` |
| `GET /invoices/<id>` | |
| `GET /reports/aging` | `at`, `payables` |
| `GET /audit` | `by` |

Writes (`X-User` header required, editor level or above):

| Path | Success | Body |
| --- | --- | --- |
| `POST /transactions` | 201 | `{"date", "description", "postings": [{"account", "amount"?}, ...]}` |
| `POST /invoices` | 201 | `{"customer", "date", "lines": [{"description", "quantity", "price", "tax_code"?}]}` |
| `POST /invoices/<id>/issue` | 200 | |
| `POST /invoices/<id>/payments` | 200 | `{"amount", "date", "account"}` |

Errors are `{"error": "..."}`. A `FinError` uses its status (400, 401, 403 or 404).
Malformed JSON, bad values and SQLite errors are 400. A missing or unknown invoice or
bill is 404.

## Assumptions

Where the specification left a choice open, these are the decisions made:

1. `--json` always prints one document. `null` is printed for a `None` result.
2. Text output is plain tables for lists and `key: value` lines for flat results.
3. `init` takes its file path from the global `--db`.
4. Read commands ignore `--user`.
5. A FX rate on the same date and currency pair replaces the earlier rate.
6. Budgets are in the account's currency.
7. `import` needs an account in the book currency.
8. Rule accounts must already exist when the rule is added.
9. `;` is not allowed in CLI line descriptions, because it separates invoice and bill fields.
10. A missing invoice or bill is NotFound (404 over HTTP).
11. Bills store price = net and have quantity NULL.
12. An invoice's `number` is null until it is issued.
13. Imports dedupe on (account, date, description, cents) across files, so re-importing the same file skips every row.
14. `period close` is always written to the audit log, even when it changes nothing.
15. `reconcile` without `--clear` lists the ids of uncleared transactions.
16. `report ledger` converts each posting at its own date.
17. `serve` prints its URL to stderr and binds to 127.0.0.1.
18. For POST requests, `X-User` and the role are checked before the body is parsed.
19. Every POST route requires editor level.
20. `tax add` rejects negative rates and duplicate codes. Rates are shown as given.
21. Closing an earlier month is a no-op that exits 0.
22. `period close` takes `YYYY-MM`.
23. `report income` and `report balance-sheet` take full dates. `report networth` takes months.
24. `tax list` returns `[{"code": ..., "rate": ...}]` in code order.
25. An invoice line without a tax code has tax_code null and no tax.
26. Invoice due date is the invoice date plus the customer's terms in days (default 30).
