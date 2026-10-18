# Plan: small-business finance system

## Goal

A stdlib-only Python package `fin/` implementing sections 1-17 of the user's request, which is
copied word for word in `.claude/team/spec.md` (sections there are numbered 1-17 and cited below as
"spec §N"). CLI: `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`; HTTP API via
`serve`. `README.md` explains usage and lists assumptions.

Python on this machine is `python3` (3.14). Use `python3` in every command; the spec's `python`
means `python3` here.

## Check

`python3 -m unittest discover -s tests` exits 0. Each task also has its own done check (below).

Tests: the user gave the check (the suite), so there is no lead-written acceptance suite. Each
teammate writes its own test file FIRST, runs it to see it fail, then implements.

## Contract

### Errors (fin/core.py)

- `class UserError(Exception)`: a user error. CLI: exit 2, message on stderr, nothing on stdout.
  API: 400 `{"error": msg}`.
- `class Unauthorized(UserError)`: no `--user`, or an unknown user. API: 401.
- `class Forbidden(UserError)`: the role may not run the command. API: 403.
- Messages are short, lower case, and name the thing: `unknown account: Expenses:Foo`.

### Money, dates, parsing (fin/core.py)

- `parse_money(text) -> Decimal`: strict. Optional sign, digits, optional `.` and at most two
  decimals, no spaces, no exponent. Returns the value quantized to cents. Otherwise UserError.
- `parse_decimal(text) -> Decimal`: strict decimal of any scale (rates, quantities, prices).
- `cents(d) -> Decimal`: quantize to 0.01 with ROUND_HALF_UP (ties away from zero).
- `fmt(d) -> str`: two decimals, `"-12.50"`, zero is `"0.00"` (never `"-0.00"`).
- `parse_date(text) -> datetime.date`: strict `YYYY-MM-DD`, a real calendar date. Otherwise UserError.
- `fmt_date(d) -> str`, `month_of(d) -> str` ("YYYY-MM"), `parse_month(text) -> str` (strict
  "YYYY-MM", returned unchanged if valid), `month_end(d) -> date`,
  `add_months(d, n) -> date` (keeps the day, clamps to the month's last day).
- `parse_posting(text) -> (account, amount_text_or_None)`: `ACCOUNT=AMOUNT` or `ACCOUNT`. Split on
  the first `=`. An empty amount means None. Account names never contain `=`.

### Database (fin/core.py)

- `open_db(path) -> sqlite3.Connection`: `isolation_level=None`, `row_factory=sqlite3.Row`,
  `PRAGMA foreign_keys=ON`. Creates the file if it is missing.
- `create_schema(conn)`: runs the DDL below (`IF NOT EXISTS`).
- `create_book(conn, currency, admin) -> dict`: validates currency (3 upper-case letters),
  requires that no book exists yet (UserError), writes meta `currency`, the admin user (role
  admin), and audit entry 1 `(user=admin, action="init", target=currency)`. Returns
  `{"currency": ..., "admin": ...}`.
- `run(db_path, fn, user=None, init=False) -> result`: the one entry point for CLI and API. Opens
  the DB; if `init`, creates the schema; otherwise UserError `not initialized: run init first`
  when meta has no currency. Then `BEGIN IMMEDIATE`, `result = fn(ctx)`, `COMMIT`. On any
  exception: `ROLLBACK` and re-raise. Always closes the connection. Returns `result`.
- `class Context`: attributes `conn`, `user` (str or None), `role` (str or None: None when there
  is no user or it is unknown), `currency` (book currency). Methods:
  - `require_write()`: Unauthorized if there is no user or it is unknown; Forbidden if role is `viewer`.
  - `require_admin()`: Unauthorized as above; Forbidden unless role is `admin`.
  - `audit(action, target)`: appends an audit row for `user`, with `at` = UTC now as
    `YYYY-MM-DDTHH:MM:SSZ`.
- `command_group(sub, name, help) -> subparsers`: returns the subparsers of top-level group
  `name` (e.g. `txn`, `report`), creating it on first use. Several modules add leaves to the same
  group (e.g. `report`), so always go through this helper. Groups are required subparsers.

### Accounts and postings (fin/core.py)

- `ACCOUNT_TYPES = {"Assets": "asset", "Liabilities": "liability", "Equity": "equity",
  "Income": "income", "Expenses": "expense"}`.
- `account_type(name) -> str`: UserError for an unknown first segment or an empty name.
- `ensure_account(ctx, name, currency=None)`: creates the account and any missing parents (parents
  get the same currency); currency defaults to `ctx.currency`; no-op if the account exists.
- `resolve_account(conn, name) -> sqlite3.Row`: UserError `unknown account: NAME`.
- `check_open(ctx, date)`: UserError `period closed: MONTH` if `month_of(date) <= closed_through`.
- `closed_through(conn) -> str or None`.
- `resolve_postings(conn, postings) -> list of (account, Decimal, currency)`: `postings` is a list
  of `(account, amount_text_or_None)`. Rules: at least 2 postings; at most one None; every account
  exists; a None posting in currency C gets `-(sum of the other postings in C)`; then the sum per
  currency must be zero, else UserError `unbalanced transaction`. Currency = the account's currency.
- `post_transaction(ctx, date, description, postings) -> dict`: `date` is a `date` or a
  `YYYY-MM-DD` string; description is stripped and must be non-empty; calls `check_open`,
  `resolve_postings`, inserts into `transactions` and `postings` (`cleared=0`), and returns
  `{"id", "date", "description", "postings": [{"account", "amount", "currency"}]}` (the spec
  §2 shape). It does NOT audit; the caller does.
- `convert(conn, amount, frm, to, at) -> Decimal`: `at` is a date. Same currency: 1:1. Else the
  most recent `fx_rates` row on or before `at` for (frm, to); if none, 1 / the most recent for
  (to, frm). No rate: UserError `no exchange rate FROM->TO on or before DATE`. Result is cents.

### Schema (fin/core.py, `create_schema`; this DDL is the contract, do not change it without the lead)

```sql
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, role TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, user TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, type TEXT NOT NULL, currency TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS postings (id INTEGER PRIMARY KEY AUTOINCREMENT, txn_id INTEGER NOT NULL REFERENCES transactions(id), pos INTEGER NOT NULL, account TEXT NOT NULL REFERENCES accounts(name), amount TEXT NOT NULL, currency TEXT NOT NULL, cleared INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS fx_rates (date TEXT NOT NULL, from_cur TEXT NOT NULL, to_cur TEXT NOT NULL, rate TEXT NOT NULL, PRIMARY KEY (date, from_cur, to_cur));
CREATE TABLE IF NOT EXISTS rules (pos INTEGER PRIMARY KEY AUTOINCREMENT, pattern TEXT NOT NULL, account TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS imported (account TEXT NOT NULL, date TEXT NOT NULL, description TEXT NOT NULL, amount TEXT NOT NULL, txn_id INTEGER NOT NULL, PRIMARY KEY (account, date, description, amount));
CREATE TABLE IF NOT EXISTS budgets (account TEXT NOT NULL, month TEXT NOT NULL, amount TEXT NOT NULL, PRIMARY KEY (account, month));
CREATE TABLE IF NOT EXISTS recurring (name TEXT PRIMARY KEY, every TEXT NOT NULL, start TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recurring_postings (name TEXT NOT NULL REFERENCES recurring(name), pos INTEGER NOT NULL, account TEXT NOT NULL, amount TEXT, PRIMARY KEY (name, pos));
CREATE TABLE IF NOT EXISTS recurring_runs (name TEXT NOT NULL REFERENCES recurring(name), date TEXT NOT NULL, txn_id INTEGER NOT NULL, PRIMARY KEY (name, date));
CREATE TABLE IF NOT EXISTS tax_codes (code TEXT PRIMARY KEY, rate TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (name TEXT PRIMARY KEY, terms INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS vendors (name TEXT PRIMARY KEY, terms INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT UNIQUE, customer TEXT NOT NULL REFERENCES customers(name), date TEXT NOT NULL, due TEXT NOT NULL, status TEXT NOT NULL, txn_id INTEGER);
CREATE TABLE IF NOT EXISTS invoice_lines (invoice_id INTEGER NOT NULL REFERENCES invoices(id), pos INTEGER NOT NULL, description TEXT NOT NULL, quantity TEXT NOT NULL, price TEXT NOT NULL, tax_code TEXT REFERENCES tax_codes(code), net TEXT NOT NULL, tax TEXT NOT NULL, PRIMARY KEY (invoice_id, pos));
CREATE TABLE IF NOT EXISTS invoice_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER NOT NULL REFERENCES invoices(id), date TEXT NOT NULL, amount TEXT NOT NULL, account TEXT NOT NULL REFERENCES accounts(name), txn_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS bills (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor TEXT NOT NULL REFERENCES vendors(name), ref TEXT NOT NULL, date TEXT NOT NULL, due TEXT NOT NULL, status TEXT NOT NULL, txn_id INTEGER NOT NULL, UNIQUE (vendor, ref));
CREATE TABLE IF NOT EXISTS bill_lines (bill_id INTEGER NOT NULL REFERENCES bills(id), pos INTEGER NOT NULL, description TEXT NOT NULL, account TEXT NOT NULL REFERENCES accounts(name), tax_code TEXT REFERENCES tax_codes(code), net TEXT NOT NULL, tax TEXT NOT NULL, PRIMARY KEY (bill_id, pos));
CREATE TABLE IF NOT EXISTS bill_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, bill_id INTEGER NOT NULL REFERENCES bills(id), date TEXT NOT NULL, amount TEXT NOT NULL, account TEXT NOT NULL REFERENCES accounts(name), txn_id INTEGER NOT NULL);
```

Storage conventions: dates are `YYYY-MM-DD` TEXT; money is `fmt()` TEXT (rates and quantities
are `str(parse_decimal(...))` TEXT); `postings.amount` is the signed amount of that posting
(debit positive). Sum with Decimal in Python, never in SQL.

### CLI (fin/cli.py, fin/__main__.py)

- `main(argv=None) -> int`. Top-level options: `--db` (default `fin.db`), `--json`, `--user`.
  Then a required subcommand (`dest="command"`). `MODULES` lists the 11 modules: books, imports,
  budgets, recurring, loans, invoices, bills, statements, ledger, taxes, api. `main` imports each
  and calls `module.register(sub)`.
- A leaf command's `set_defaults(handler=fn, init=False)`. `fn(ctx, args) -> result`. `init`
  leaves set `init=True`. `main` calls `core.run(args.db, lambda ctx: args.handler(ctx, args),
  user=args.user, init=args.init)`, prints the result as JSON (`json.dumps(result,
  ensure_ascii=False, indent=None if args.json else 2)`), and returns 0.
- `UserError` (and subclasses): message to stderr, return 2. argparse errors also exit 2.
- `fin/__main__.py`: `sys.exit(cli.main())`.

### Module contract (every fin/<module>.py)

- `register(sub)` adds the module's leaves (via `core.command_group` for groups). Leaves carry
  `handler`/`init` defaults. Use dest names that are not Python keywords (`--from` → `from_date`).
- Command logic is plain functions taking `ctx` first, then string/int args exactly as the CLI
  gives them (dates `YYYY-MM-DD` strings, postings as `[(account, amount_text_or_None), ...]`,
  line lists as tuples). The API calls these same functions. Name them `<group>_<sub>` or the
  command name, e.g. `txn_add(ctx, date, description, postings)`, `report_income(ctx, from_date,
  to_date, currency=None)`, `invoice_issue(ctx, invoice_id)`. Return JSON-able data only.
- Commands never open the DB or print. They raise UserError.
- Permissions: data-changing commands call `ctx.require_write()`; admin-only ones call
  `ctx.require_admin()`; read-only ones call nothing (they work without a user).
- A data-changing command calls `ctx.audit(action, target)` once on success, with action/target
  from spec §11. A command that changes nothing (e.g. `import` with zero rows, `reconcile` with no
  `--clear`, `period close` of an already-closed month, `recurring run` with nothing due) writes no
  audit entry.
- Money uses Decimal and `core.fmt` / `core.cents`. Never float.
- Own files only. Do not edit core.py, cli.py or support.py. If you need a helper they lack,
  write it in your own module and say so in the handoff.

### Test support (tests/support.py, written by task core)

- `new_book(testcase, currency="EUR", admin="alice") -> str`: makes a temp dir (cleaned up with
  `testcase.addCleanup`), initializes a book there via `core.run(path, ..., init=True)`, returns
  the DB path.
- `call(path, fn, user="alice")`: `core.run(path, fn, user=user)`.
- Test files import it as `import support` (the discover top-level is `tests/`). Test helper
  names must not be unittest method names (`fail`, `assert*`, `setUp`, `run`, `skipTest`).
- Test files are `tests/test_<task>.py`.

### Output conventions (all commands)

- Amounts are `fmt()` strings. Dates are `YYYY-MM-DD`, months `YYYY-MM`.
- Read commands return the spec shape. Adds with no shape in the spec return the created record:
  `init` → `{"currency","admin"}`; `user add` → `{"name","role"}`; `account add` →
  `{"name","type","currency"}`; `fx add` → `{"date","from","to","rate"}`; `rule add` →
  `{"pattern","account"}`; `budget set` → `{"account","month","amount"}`; `recurring add` →
  `{"name","every","start"}`; `period close` → `{"closed_through"}`; `tax add` → `{"code","rate"}`;
  `customer add` / `vendor add` → `{"name","terms"}`.
- Assumptions made by a task go in its handoff under `## Assumptions`. The README is built from them.

### Handoff format (`.claude/team/handoff/<task>.txt`)

```
## Done
- what works, with the paths
## Check
<the done-check command> → OK (test count) | failing output lines
## Assumptions
- ...
## Next step
- none, or what the next task needs to know
```

## Conventions for the team

- Build order: wave 1 `core`; wave 2 nine tasks in parallel; wave 3 `taxes` and `api`; wave 4
  `readme`.
- Stub modules `fin/books.py` … `fin/api.py` exist from the start (each has only `register`).
  Their owners replace them.

## Tasks

### core

Files owned: `fin/__init__.py`, `fin/core.py`, `fin/cli.py`, `fin/__main__.py`,
`tests/support.py`, `tests/test_core.py`, `tests/test_cli.py`.

What to do: implement everything under "Errors", "Money, dates, parsing", "Database", "Accounts
and postings", "Schema", "CLI" and "Test support" of the Contract, exactly. Spec sections: §1
(account name rules), §2 (posting output shape), §11 (roles, audit `at` format), §12 (closed
periods), §4 (convert). Test first: `tests/test_core.py` covers parse_money
(including `-0.00` → `0.00`, three decimals rejected), cents half-up, fmt, parse_date, add_months
(Jan 31 → Feb 28/29 → Mar 31 → Apr 30), account_type, ensure_account (parents), resolve_postings
(auto balance, unbalanced error, one blank only), post_transaction, check_open, convert (direct,
inverse, same currency, missing), run (rollback on UserError, not-initialized error), Context
permission checks, audit. `tests/test_cli.py` covers the global options, the exit code 2 with
empty stdout for a user error, `--json` compactness, and `command_group` reuse. Keep the test
for `--json` to a single line of output.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_cli.py'`

May change: only the files listed above. Must not touch: other modules' files, the DDL (if you
think it is wrong, say so in the handoff and stop).

Stub modules: do not touch them. The `MODULES` list in cli.py must import all 11 modules, which
all exist as stubs now, so `register` must be defined in each stub. Leave the stubs alone.

### books

Files owned: `fin/books.py`, `tests/test_books.py`.

What to do: spec §1 `account add` and `account list`; §2 `txn add` and `txn list`; §3 `balance`;
§4 `fx add` and `convert`; §11 `user add` and `user list` (admin only for `user add`) and `audit
list [--by NAME]`; §12 `period close MONTH` (admin only; closes that month and earlier; closing
an earlier month than already closed changes nothing, so no audit) and `period status`. Also
`init --currency CUR --admin NAME` (`init=True`, calls `core.create_book`). `init` needs no
user. Audit for `account.add`, `txn.add` (id), `fx.add` (`FROM/TO`), `user.add`, `period.close`
(month). `txn add` takes repeated `--posting` (`parse_posting`). `txn list` filters `--account`
(exact name or descendant), `--from`, `--to` (inclusive), sorted by date then id. `balance --at`
(raw signed sums per currency, every ancestor included). `convert AMOUNT FROM TO --at DATE`
uses `core.convert` and returns `{"amount", "currency"}`. `account list` sorted by name.

Permissions: `init` none; writes need `require_write`; `user add` and `period close` need
`require_admin`. Reads need nothing; `--user` on a read is ignored.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_books.py'`

May change: `fin/books.py`, `tests/test_books.py`. Must not touch: core.py, cli.py, other modules.

### imports

Files owned: `fin/imports.py`, `tests/test_imports.py`.

What to do: spec §5. `rule add PATTERN ACCOUNT` (validate regex with `re.compile`; ACCOUNT must
exist; audit `rule.add` = pattern) and `rule list` (in insertion order, from `rules`). `import
FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]`: the
account must exist; read the CSV with the `csv` module (0-based columns, defaults 0/1/2; the date
is `YYYY-MM-DD`; the amount via parse_money). Each row becomes a transaction on that date with
description = the row's description, between ACCOUNT (the row's amount) and a category account
(the opposite amount). The category: the first rule (lowest pos) whose pattern matches the
description (`re.search`, IGNORECASE); else `Expenses:Uncategorized` for a negative amount,
`Income:Uncategorized` for a positive one. Create that category with `core.ensure_account` if
missing. Skip a row already in `imported` for the same account (date, description, amount),
including repeats within the file: check and insert `imported` rows as you go. Use
`core.post_transaction` for the rows. All-or-nothing: any error (closed period, bad row) makes
the whole run fail (core.run rolls back). Output `{"imported": N, "skipped": M}`. Audit
`import` (target = ACCOUNT) only when imported > 0. Permission: require_write for both
`rule add` and `import`.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_imports.py'`

May change: `fin/imports.py`, `tests/test_imports.py`. Must not touch: core.py, cli.py, other modules.

### budgets

Files owned: `fin/budgets.py`, `tests/test_budgets.py`.

What to do: spec §6. `budget set ACCOUNT MONTH AMOUNT`: the account must exist and be an
expense account (type `expense`), MONTH via `parse_month`, AMOUNT via parse_money; replaces an
existing budget for that account and month (`budgets` table). Output `{"account","month",
"amount"}`. Audit `budget.set` with target `ACCOUNT MONTH`. `report budget MONTH`: one entry per
account with a budget that month, sorted by account. `actual` = the sum of that month's postings
(dates in that month) to the account and its descendants (exact name or `name:` prefix).
`remaining` = budget − actual. Output a list of `{"account","budget","actual","remaining"}`.
Permission: `budget set` require_write; `report budget` none. Register `report budget` with
`core.command_group(sub, "report", ...)`.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_budgets.py'`

May change: `fin/budgets.py`, `tests/test_budgets.py`. Must not touch: core.py, cli.py, other modules.

### recurring

Files owned: `fin/recurring.py`, `tests/test_recurring.py`.

What to do: spec §7. Tables `recurring`, `recurring_postings`, `recurring_runs` (DDL in the
Contract). `recurring add NAME --every monthly|weekly|yearly --start DATE --posting ACCOUNT=AMOUNT
[...]`: same posting rules as `txn add`, checked now with `core.resolve_postings` (store a
balancing posting with `amount` NULL). A NAME that already exists is a UserError. Output
`{"name","every","start"}`. Audit `recurring.add` (name). `recurring run --until DATE`: for each
recurring, in creation order, the occurrences from start up to and including DATE. Occurrence k:
monthly `add_months(start, k)`, yearly `add_months(start, 12*k)`, weekly `start + 7k days`
(`datetime.timedelta`). Skip occurrences already in `recurring_runs`. Create each with
`core.post_transaction` (description = NAME; a NULL amount is balanced at each run) and insert
into `recurring_runs`. If any occurrence is in a closed period, the whole run fails (UserError;
core.run rolls back). Output `{"created": N}`. Audit `recurring.run` (target = the `--until`
date as given) only when N > 0. Permission: add and run need require_write.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_recurring.py'`

May change: `fin/recurring.py`, `tests/test_recurring.py`. Must not touch: core.py, cli.py, other modules.

### loans

Files owned: `fin/loans.py`, `tests/test_loans.py`.

What to do: spec §9 `loan schedule PRINCIPAL RATE MONTHS --start DATE`. Pure calculation: it
does not use the DB (the command still runs under core.run; it just reads nothing). Validate:
PRINCIPAL > 0 (parse_money), RATE ≥ 0 (parse_decimal), MONTHS an integer ≥ 1, START a date.
r = RATE/1200 as Decimal (use a Decimal context with at least 50 digits of precision for the
annuity formula). payment = cents(PRINCIPAL·r / (1 − (1+r)^−MONTHS)); with RATE 0, payment =
cents(PRINCIPAL / MONTHS). Each row n = 1..MONTHS: date = `add_months(start, n)`, interest =
cents(balance·r), principal = payment − interest, balance after = balance − principal. The last
row: principal = remaining balance, payment = remaining balance + interest, balance after `0.00`.
`total_interest` = sum of interest. Output `{"payment","total_interest","rows":[{"n","date",
"payment","interest","principal","balance"}]}`. No audit (read-only).

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_loans.py'`

May change: `fin/loans.py`, `tests/test_loans.py`. Must not touch: core.py, cli.py, other modules.

### invoices

Files owned: `fin/invoices.py`, `tests/test_invoices.py`.

What to do: spec §13 in full, with the tables in the Contract. `tax add CODE RATE` (rate
parse_decimal, store as given; duplicate code is UserError; output `{"code","rate"}`; audit
`tax.add` = code; require_write) and `tax list` (sorted by code, rates as given). `customer add
NAME [--terms DAYS]` (default 30; duplicate UserError; audit `customer.add`), `customer list`.
`invoice create --customer NAME --date DATE --line "DESCRIPTION;QUANTITY;PRICE;TAXCODE" [...]`:
creates a draft (`invoices.status='draft'`, number NULL, txn_id NULL). Each line splits on `;`
into exactly 4 fields (TAXCODE may be empty = no tax; otherwise it must exist in `tax_codes`).
QUANTITY is parse_decimal; PRICE is parse_money; net = cents(qty × price); tax = cents(net ×
rate / 100). Store in `invoice_lines`. Due = date + customer terms days. The invoice's
net/tax/total are sums over lines; paid = sum of `invoice_payments` for it; balance = total −
paid. `invoice issue ID`: must be a draft (else UserError). Number `INV-YYYY-NNNN` with YYYY =
invoice date's year and NNNN = 1 + the count of invoices already numbered in that year, padded
to 4. Status `issued`. Post one transaction via `core.post_transaction` dated the invoice date,
description `Invoice INV-...`: `Assets:Receivable` +total, `Income:Sales` −net, and
`Liabilities:SalesTax` −tax only if tax ≠ 0 (create the accounts with `ensure_account` if
missing). Store txn_id. Audit `invoice.issue` (target = the id, per §11: "the invoice or bill
id"; use the numeric id). `invoice create` audit `invoice.create` (target = id). `invoice pay ID
AMOUNT --date DATE --account ACCOUNT`: ACCOUNT must exist and be `asset`; AMOUNT parse_money > 0;
the invoice must be issued or partial (else UserError); AMOUNT ≤ balance (else UserError). Post
`ACCOUNT +AMOUNT`, `Assets:Receivable −AMOUNT`, description `Payment INV-...`. Insert
`invoice_payments`. Status `paid` when balance is 0, else `partial`. Audit `invoice.pay` (target
= id). `invoice show ID` → the invoice. `invoice list [--status S]` → by id. Every invoice command
that succeeds returns the invoice (issue, pay, show, create). Invoice JSON shape: §13 exactly,
with `number` null while draft and `tax_code` null without tax. Invoice ID not found → UserError
`unknown invoice: N`. Expose `invoice_get(ctx, id)` returning the dict for the API too.

`report aging --at DATE [--payables]` (register `report aging` with `command_group`): buckets over
issued invoices (or, with `--payables`, bills, read from `bills`/`bill_lines`/`bill_payments`,
which the bills task creates; query the tables directly, do not import bills.py) dated on or
before DATE. Balance = total − payments dated on or before DATE. Drop balance ≤ 0. Days past due
= DATE − due; ≤ 0 → `current`; 1–30; 31–60; 61–90; more than 90 → `90+`. Output `{"current",
"1-30", "31-60", "61-90", "90+", "total"}`. Bills status for payables: bills have no draft, so
every bill row counts. Test payables aging by inserting `vendors`/`bills`/`bill_lines`/
`bill_payments` rows directly in the test.

Dates: due uses `datetime.timedelta`. Every money output `fmt()`.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_invoices.py'`

May change: `fin/invoices.py`, `tests/test_invoices.py`. Must not touch: core.py, cli.py, other modules.

### bills

Files owned: `fin/bills.py`, `tests/test_bills.py`.

What to do: spec §14 `vendor add NAME [--terms DAYS]` (default 30; duplicate UserError; audit
`vendor.add`), `vendor list`; `bill create --vendor NAME --ref TEXT --date DATE --line
"DESCRIPTION;AMOUNT;ACCOUNT;TAXCODE" [...]`: each line splits on `;` into exactly 4 fields
(TAXCODE may be empty = no tax; otherwise it must exist in `tax_codes`); AMOUNT is parse_money
(the net); ACCOUNT must exist and be `expense` or `asset`, and its currency must be the book's
currency (else UserError). Tax per line = cents(net × rate / 100). Vendor must exist; a repeated
`--ref` for the same vendor is UserError. Due = date + vendor terms days. Post at once via
`core.post_transaction`, dated DATE, description `Bill REF`: each line's ACCOUNT +net,
`Assets:TaxReceivable` +bill tax if not zero, `Liabilities:Payable` −total (create missing
accounts with `ensure_account`). Insert `bills` (status `open`, txn_id) and `bill_lines`. Output
the bill JSON in §14 shape (`paid` "0.00" at creation). Audit `bill.create` (target = id).
`bill pay ID AMOUNT --date DATE --account ACCOUNT`: ACCOUNT must be `asset`; AMOUNT > 0; bill must
be open or partial; AMOUNT ≤ balance. Post `Liabilities:Payable +AMOUNT`, ACCOUNT −AMOUNT,
description `Payment REF`. Insert `bill_payments`. Status `paid` at zero balance, else `partial`.
Audit `bill.pay` (target = id). `bill show ID`, `bill list [--status S]` (by id). Expose
`bill_get(ctx, id)` for others. Unknown bill ID → UserError `unknown bill: N`. Do not implement
`report aging`; the invoices task does it. Permission: writes require_write.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_bills.py'`

May change: `fin/bills.py`, `tests/test_bills.py`. Must not touch: core.py, cli.py, other modules.

### statements

Files owned: `fin/statements.py`, `tests/test_statements.py`.

What to do: spec §8. Registers `report income`, `report balance-sheet`, `report networth` (via
`command_group(sub, "report")`). Currency rule: each account's per-currency total is converted
to the report currency (`--currency` or the book currency) at the report date (`--to` or
`--at`; networth: each month's end) with `core.convert`, then summed. Round after converting.
A missing rate is UserError from convert.
- `report income --from --to [--currency]`: postings dated in the period. `income` = dict over
  Income accounts with postings in range, value = −(raw sum); `expenses` similarly for Expenses
  (value = raw sum). `total_income`, `total_expenses`, `net` = income − expenses. Keys are the
  posting account names (not parents). Sorted by name.
- `report balance-sheet --at [--currency]`: postings on or before DATE. `assets` (Assets,
  raw sum), `liabilities` (Liabilities, −raw), `equity` (Equity, −raw). `retained_earnings` =
  (−raw sum of Income) − (raw sum of Expenses), all up to DATE. `total_equity` = sum of equity
  + retained_earnings; `total_assets` and `total_liabilities` are sums. Shape as §8.
- `report networth --from MONTH --to MONTH` (no currency option; the book currency): one entry per
  month from `--from` to `--to`, inclusive, as of the month's last day: `assets` = total assets
  (asset accounts, raw), `liabilities` = −raw liabilities, `networth` = assets − liabilities.
  Output `[{"month","assets","liabilities","networth"}]`. `--from` after `--to` → empty list.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_statements.py'`

May change: `fin/statements.py`, `tests/test_statements.py`. Must not touch: core.py, cli.py, other modules.

### ledger

Files owned: `fin/ledger.py`, `tests/test_ledger.py`.

What to do: spec §16 `reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID] [...]`,
and spec §17 `report trial-balance --at DATE` and `report ledger ACCOUNT --from DATE --to DATE`.
(Spec §15 is the tax report and belongs to the taxes task; ignore it.)
- Reconcile: ACCOUNT must exist. Each `--clear ID` must be a transaction with a posting to
  ACCOUNT (exact name) dated on or before DATE, else UserError and nothing marked (core.run rolls
  back). Set `postings.cleared=1` for those ACCOUNT postings. Output `{"account","date",
  "statement_balance","cleared_balance","difference","uncleared":[ids ascending]}`.
  `cleared_balance` = sum of ACCOUNT's cleared postings (exact account) dated on or before DATE;
  `difference` = statement − cleared; `uncleared` = distinct transaction ids with a posting to
  ACCOUNT dated on or before DATE and not cleared. Audit `reconcile` (target ACCOUNT) only when at
  least one `--clear` was given. Permission: require_write only when `--clear` is given; no
  `--clear` is a read (no user needed).
- `report trial-balance --at DATE`: one row per account name with postings on or before DATE,
  sorted by name. Raw balance per account, converted to the book currency at DATE with
  `core.convert` (round after converting). Positive → `debit`, negative → `credit` (as a
  positive number), the other side `"0.00"`. Output `{"rows":[{"account","debit","credit"}],
  "total_debit","total_credit"}`.
- `report ledger ACCOUNT --from DATE --to DATE`: in ACCOUNT's currency. `opening` = raw sum of
  ACCOUNT and its descendants before FROM. Rows: one per posting to them in the period, by date
  then transaction id (then posting id), each `{"date","id","description","amount","balance"}`,
  running balance from opening. `closing` = last balance (or opening). Output `{"account",
  "opening","rows","closing"}`. Unknown ACCOUNT → UserError.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_ledger.py'`

May change: `fin/ledger.py`, `tests/test_ledger.py`. Must not touch: core.py, cli.py, other modules.

### taxes

Files owned: `fin/taxes.py`, `tests/test_taxes.py`.

Wave 3: start after wave 2 is merged (it reads invoices and bills tables).

What to do: spec §15 `report tax --from DATE --to DATE` (register via `command_group(sub,
"report")`). `collected` = sum of invoice line tax for invoices with status ≠ `draft`, dated in the
period. `paid` = sum of bill line tax for bills dated in the period. `net` = collected − paid.
`by_code` has every tax code used in that period by such an invoice or bill: `{"collected",
"paid"}` per code, with `"0.00"` where none. All money `fmt()`. No conversion (tax is in the
book currency). Read-only. Test by driving the real commands (`invoice_create`, `invoice_issue`,
`bill_create`, etc.) through `support.call`, so the test runs on the real code. Import those
functions from fin.invoices and fin.bills.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_taxes.py'`

May change: `fin/taxes.py`, `tests/test_taxes.py`. Must not touch: core.py, cli.py, other modules.

### api

Files owned: `fin/api.py`, `tests/test_api.py`.

Wave 3: start after wave 2 is merged; it calls the other modules' functions.

What to do: spec §10. `python3 -m fin [--db PATH] serve --port N` (register `serve` with
`handler`; `init=False`). The server is `http.server.HTTPServer` (single-threaded) serving JSON.
Expose `make_server(db_path, port) -> HTTPServer` (port 0 allowed; read the bound port from
`server.server_address`) so tests can run it in a thread. `serve` blocks until stopped (catch
KeyboardInterrupt → return 0 without printing). Routes: `GET /accounts` (`account_list`),
`GET /transactions` (`txn_list`, with optional `account`, `from`, `to` query params), `GET
/balances?at=` (`balance`), `GET /reports/income?from=&to=` (`report_income`), `GET
/reports/balance-sheet?at=` (`report_balance_sheet`), `GET /invoices` (`invoice_list`),
`GET /invoices/ID` (`invoice_get`; unknown → 404), `GET /reports/aging?at=` (add `&payables=1` for
bills), `GET /audit` (`audit_list`), `POST /transactions` (body `{"date","description",
"postings":[{"account","amount"}]}`, amount optional on one posting → `txn_add`; 201 and the
transaction), `POST /invoices` (body `{"customer","date","lines":[{"description","quantity",
"price","tax_code"}]}` → `invoice_create`; tax_code optional; 201), `POST /invoices/ID/issue`
(200), `POST /invoices/ID/payments` (body `{"amount","date","account"}`; 200 and the invoice).
Unknown path → 404 `{"error"}`. Every POST needs `X-User`: missing or unknown → 401 (use the
Unauthorized exception from the same call path); role may not → 403 (Forbidden); other UserError
→ 400 `{"error": msg}`. GET needs no user. Each request runs through `core.run(db_path, fn,
user=header_or_None)` so it commits or rolls back like the CLI. Reads from the other modules must
call the same functions the CLI uses, so responses match `--json` output. Responses are
`application/json`. Parse the JSON body; invalid JSON or missing fields → 400.

Use the function names other modules expose (read their files with grep; do not guess). If a
function you need doesn't exist yet, say so in the handoff and stop; do not implement it in another
module.

Done check: `python3 -m unittest discover -s tests -p 'test_core.py' && python3 -m unittest discover -s tests -p 'test_api.py'`

May change: `fin/api.py`, `tests/test_api.py`. Must not touch: core.py, cli.py, other modules.

### readme

Wave 4: start after waves 2 and 3 are merged.

Files owned: `README.md`, `tests/test_e2e.py`.

What to do: README.md with: what the system is; install (stdlib only; Python 3.12+; `python3` on
this machine); quick start (init, account add, txn add, balance, import, reports, invoices,
bills, recurring, budgets, loans, reconcile, serve); the commands and their options (one line
each); the users and roles; the JSON output and exit code rules; the list of assumptions, taken
from each handoff's `## Assumptions` (read every file in `.claude/team/handoff/` — they are the
source), grouped by area, deduplicated. Also say how to run tests (`python3 -m unittest discover
-s tests`).

`tests/test_e2e.py`: end-to-end tests that run `python3 -m fin` via `subprocess` against a
temp DB and check the spec's examples (§1–§17 in brief): init, accounts, txn with the
auto-balanced posting, balance, fx/convert, import with rules and dedupe, budget report,
recurring run idempotence, income and balance-sheet, networth, loan schedule final balance 0.00,
invoice lifecycle with aging, bill lifecycle, tax report, reconcile, trial balance equality,
ledger, permissions (viewer → exit 2, closed period → exit 2 with empty stdout), audit list,
and the API via `api.make_server` on port 0 in a thread. Keep the whole file under 60 seconds.

Done check: `python3 -m unittest discover -s tests`

May change: `README.md`, `tests/test_e2e.py`. Must not touch: any `fin/` file. If a test
reveals a bug in `fin/`, do not fix it: list it in the handoff.

## Waves

1. core
2. books, imports, budgets, recurring, loans, invoices, bills, statements, ledger
3. taxes, api
4. readme
