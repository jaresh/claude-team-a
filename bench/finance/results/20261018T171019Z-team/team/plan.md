# Plan: small-business finance system (package `fin`)

## Goal
Build `fin` exactly as the user's spec (.claude/team/spec.md, sections 1–17), stdlib only.
Command-line `python -m fin ...` plus an HTTP API (`serve`). Every spec section has tests.
Tests are per-task files in `tests/`, run together. README.md (lead writes it at the end)
lists usage and assumptions.

## Check (done)
    python3 -m unittest discover -s tests

## Contract (already written by the lead; read these, don't change them)
- `fin/core.py` (READ IT FIRST, it is short): `UserError` (status 400), `Unauthorized` (401),
  `Forbidden` (403). Money: `dec`, `parse_amount` (≤2 decimals), `cents`, `money` (JSON string,
  "0.00" never "-0.00"), `dsum`, `tax_on(net, rate_percent)`. Dates: `parse_date`, `parse_month`,
  `month_of`, `add_months`, `occurrence(start, freq, n)` (n=0 is the start), `month_end(month)`,
  `utc_now`. DB: `connect`, `create_schema`, `book_currency`, `closed_through`, `check_open`.
  Accounts: `account_type(name)` (validates the first segment), `in_prefix(acct, prefix)`,
  `ancestors(acct)`, `ensure_account(conn, name, currency=None)` (creates missing parents).
  Postings: `parse_posting("A=-1.00" | "A")`, `post(conn, date, description, [(acct, Decimal|None)])`
  → txn dict; it enforces every posting rule (balance, unknown account, closed period) and
  raises UserError. `txn_to_dict(conn, id)`. Command plumbing: `@command(path, write=, admin=,
  args=, bootstrap=)`, the handler is `def f(ctx, a) -> JSON data` where `a` maps argparse dest
  names (`--from`→`a["from"]`, `--date-col`→`a["date_col"]`), `ctx.conn`, `ctx.user`,
  `ctx.role`, `ctx.audit(action, target)`.
- Schema: all tables already exist in `core.SCHEMA` (meta, users, audit, accounts,
  transactions, postings(cleared), rules, imports, fx_rates, budgets, recurring,
  recurring_runs, tax_codes, customers, vendors, documents, document_lines, payments). Use
  them; to change the schema, stop and say so in your handoff.
- Book currency lives in `meta` key `currency`. Closed period in `meta` key `closed_through`.
- Plumbing: `core.run(argv)` → `Result(ok, data, error, status)`; `fin/__main__.py` prints data.
  `fin/commands.py` imports every command module, so each module must exist (the lead made
  stubs; you replace your stub).
- Test helpers: `tests/support.py`: `FinTestCase` (fresh book: EUR, admin `admin`; methods
  `add_account(name, currency=None)` creates an account directly, `expect_ok(*args, user=)`,
  `expect_error(*args, user=, status=)`, `fin_run(*args, user=)`). Never name a test helper like
  a unittest method (`fail`, `assert*`, `setUp`, `run`, `skipTest`).
- Cross-module functions (fixed signatures):
  - `fin/ledger.py`: `convert(conn, amount: Decimal, frm: str, to: str, at: date) -> Decimal`
    (unrounded; UserError "no exchange rate" when none). Written in wave 1; reports use it.
  - `fin/documents.py` (written by task `invoices`, reused by `bills`): shared invoice/bill
    logic. Its functions are described in the task's handoff.

## Conventions (every task follows these)
- JSON money strings via `core.money`; never float; dates via `core.parse_date`/`parse_month`.
- Errors: `raise core.UserError("message")`. Never print. Never `sys.exit`.
- Command output is the handler's return value; `None` prints nothing.
- Write commands: `write=True`; admin-only: `admin=True`. Core enforces users and roles. Read
  commands ignore `--user`. Every successful write command calls `ctx.audit(action, target)`
  exactly once, with the action and target from spec §11. Exception: `period close` makes no
  entry when it changes nothing. Audit targets are strings.
- Use `core.ensure_account` before posting to accounts you create. Post only through
  `core.post`, so closed periods and balancing are always checked.
- Tests: `tests/test_<task>.py`, subclass `FinTestCase`. Set up data with `self.add_account`
  and `core.post` (and with commands only from earlier waves). Cover every spec command in your
  section, its user errors, and the exit-code/no-change behaviour. Use `tmp` files for CSV.
- Edit only the files your task owns. Don't touch `core.py`, `support.py`, `commands.py`,
  `__main__.py`, or other tasks' files or tests. If you need one of those changed, say so in
  your handoff's Next step and stop.
- Handoff (`.claude/team/handoff/<task>.txt`), short: Done (what works, with test count), Files,
  Assumptions (each decision you made), Next step.
- Spec section numbers are in .claude/team/spec.md (the user's words). Output shapes there are
  exact. Where the spec is silent, decide, prefer the simplest reading, and list it under
  Assumptions.
- Global decisions (all tasks): `--json` prints compact JSON, otherwise indent 2; both are one
  JSON document. Unknown `--user` on a read command is ignored. Amounts shown as `money(...)`.
  Account lookup for reports and budgets is by exact name, unless the spec says descendants.

## Wave 1 (parallel): books, ledger, loans, contacts, budgets, recurring, importer, reconcile

## books
Owns: `fin/books.py`, `tests/test_books.py`.
Do (spec §1, §11, §12):
- `init --currency CUR --admin NAME`: `bootstrap=True`. Currency: 3 ASCII letters, stored
  uppercase in meta `currency`. Creates user NAME with role admin. Running on an initialised
  book is a UserError. Sets `ctx.user = NAME`, `ctx.role = "admin"` and audits `init` with
  target CUR. Test with a new path (not `self.db`): `run(["--db", path, "init", ...])`.
- `user add NAME --role ROLE` (admin, write): role in core.ROLES; existing name is an error.
  Audit `user.add` NAME. `user list` (read): `[{"name","role"}]` sorted by name.
- `account add NAME [--currency CUR]` (write): account_type validates; existing name is an
  error; currency defaults to the book's, validated as 3 letters; ensure_account. Audit
  `account.add` NAME. `account list` (read): `[{"name","type","currency"}]` sorted by name.
- `audit list [--by NAME]` (read): `[{"seq","at","user","action","target"}]`, by seq.
- `period close MONTH` (admin, write): parse_month; if none closed or MONTH is later, set
  meta `closed_through`; audit `period.close` MONTH. Earlier month: no change, no audit.
  Returns the status document. `period status` (read): `{"closed_through": "YYYY-MM" | null}`.
Check: `python3 -m unittest discover -s tests -p "test_books.py"`.
Must not touch: other tasks' files, core, support.

## ledger
Owns: `fin/ledger.py`, `tests/test_ledger.py`.
Do (spec §2, §3, §4):
- `txn add --date DATE --desc TEXT --posting ACCOUNT=AMOUNT ...` (write, action `txn.add`,
  target id): `--posting` is `action="append"`; at least one needed. Use `core.post`. Returns
  the txn dict. Dest of `--desc` is `desc`.
- `txn list [--account PREFIX] [--from DATE] [--to DATE]` (read): txn dicts ordered by date,
  then id. Prefix filter via `in_prefix` on posting accounts. From/to inclusive by txn date.
- `balance [--at DATE]` (read): `{account: {currency: money}}` for every account with postings
  on or before DATE, plus each ancestor (sum over descendants). Keys sorted. Raw signs.
- `fx add DATE FROM TO RATE` (write, action `fx.add`, target `FROM/TO`): validate 3-letter
  codes and RATE > 0. Returns `{"date","from","to","rate"}` (rate as given).
- `convert AMOUNT FROM TO --at DATE` (read): `{"amount": money, "currency": TO}`. Same code
  converts 1:1. Otherwise use the latest FROM→TO rate with date ≤ at. If none, the latest
  TO→FROM rate with date ≤ at, inverted (1/rate, full Decimal precision). Otherwise UserError.
- `convert(conn, amount, frm, to, at) -> Decimal` module function (unrounded) with the same
  rule; reports rely on it.
Check: `python3 -m unittest discover -s tests -p "test_ledger.py"`.

## loans
Owns: `fin/loans.py`, `tests/test_loans.py`.
Do (spec §9): `loan schedule PRINCIPAL RATE MONTHS --start DATE` (read, no book needed beyond
the core). PRINCIPAL > 0 via parse_amount, RATE ≥ 0 via dec (annual percent), MONTHS ≥ 1 int.
Monthly rate r = RATE/1200. Payment = round(P·r/(1−(1+r)^−N)) to cents; RATE 0: round(P/N).
Each row n=1..N: interest = cents(balance·r); principal = payment − interest; the last row's
payment = its balance + interest, so the final balance is 0.00. Row date = `occurrence(start,
"monthly", n)`. Use Decimal with enough precision for the power. Output shape per spec,
`total_interest` is the sum of row interest. Don't write any data (no `write` flag).
Check: `python3 -m unittest discover -s tests -p "test_loans.py"`.

## contacts
Owns: `fin/contacts.py`, `tests/test_contacts.py`.
Do (spec §13, §14 vendors):
- `tax add CODE RATE` (write, action `tax.add` CODE): RATE via dec ≥ 0; store the given string;
  existing code is an error. `tax list` (read): `[{"code","rate"}]` sorted by code, rate as stored.
- `customer add NAME [--terms DAYS]` (write, `customer.add` NAME; default 30; terms int ≥ 0;
  existing name is an error). `customer list` (read): `[{"name","terms"}]` sorted by name.
- `vendor add NAME [--terms DAYS]` and `vendor list`: same, with table vendors, action `vendor.add`.
Check: `python3 -m unittest discover -s tests -p "test_contacts.py"`.

## budgets
Owns: `fin/budgets.py`, `tests/test_budgets.py`.
Do (spec §6): `budget set ACCOUNT MONTH AMOUNT` (write, action `budget.set`, target
`ACCOUNT MONTH`): the account must exist and be type expense; AMOUNT ≥ 0 via parse_amount;
replaces an existing budget. Returns `{"account","month","amount"}`.
`report budget MONTH` (read): one entry per budget in that month, sorted by account, with
`budget`, `actual` (sum of postings to the account and descendants dated within the month),
`remaining` = budget − actual. Shape per spec.
Check: `python3 -m unittest discover -s tests -p "test_budgets.py"`.

## recurring
Owns: `fin/recurring.py`, `tests/test_recurring.py`.
Do (spec §7):
- `recurring add NAME --every monthly|weekly|yearly --start DATE --posting ... ` (write, action
  `recurring.add` NAME): postings validated by the same rules as txn add. Validate by posting
  inside a SAVEPOINT and rolling it back (`SAVEPOINT r; core.post(...); ROLLBACK TO r;
  RELEASE r`). Store postings as JSON `[[account, amount-string-or-null], ...]` in `recurring`.
  Returns `{"id","name","every","start"}`.
- `recurring run --until DATE` (write, action `recurring.run`, target the DATE): for each rule,
  for n = 0,1,… while `occurrence(start, every, n)` ≤ DATE, create a transaction with
  description NAME (core.post), unless `recurring_runs` has (rule id, date). Record the run.
  Any closed-period hit raises and the whole command fails. Returns `{"created": N}`.
Check: `python3 -m unittest discover -s tests -p "test_recurring.py"`.

## importer
Owns: `fin/importer.py`, `tests/test_importer.py`.
Do (spec §5):
- `rule add PATTERN ACCOUNT` (write, action `rule.add` PATTERN): the regex must compile
  (re.error → UserError); ACCOUNT must pass account_type. `rule list` (read):
  `[{"pattern","account"}]` in order of seq.
- `import FILE --account ACCOUNT [--date-col N] [--desc-col N] [--amount-col N] [--skip-header]`
  (write, action `import` target ACCOUNT). Defaults 0, 1, 2. csv module. Blank rows skipped.
  Date parse_date; amount parse_amount. Duplicate: an imports row with the same account, date,
  description and amount, or an earlier row in the same file (count as skipped). Category: first
  rule whose pattern matches (`re.search`, IGNORECASE); the rule's account gets ensure_account
  if missing. Otherwise Expenses:Uncategorized when amount < 0, else Income:Uncategorized
  (ensure_account in book currency). Post `[(ACCOUNT, amt), (category, −amt)]`; record the
  row in `imports`. A failing row fails the whole import (run() rolls back).
  Returns `{"imported","skipped"}`.
Check: `python3 -m unittest discover -s tests -p "test_importer.py"`.

## reconcile
Owns: `fin/reconcile.py`, `tests/test_reconcile.py`.
Do (spec §16): `reconcile ACCOUNT --date DATE --balance AMOUNT [--clear ID ...]` (write,
action `reconcile` ACCOUNT). `--clear` is `action="append"`, dest `clear`. ACCOUNT must exist.
Each clear id must be a transaction with a posting to ACCOUNT (exact name) dated ≤ DATE, else
UserError (nothing is marked). Marks those postings cleared (`postings.cleared = 1`). Then:
`cleared_balance` = sum of ACCOUNT's cleared postings dated ≤ DATE; `difference` =
statement − cleared; `uncleared` = ascending distinct ids of transactions with an uncleared
ACCOUNT posting dated ≤ DATE. Shape per spec. Tests create transactions with core.post.
Check: `python3 -m unittest discover -s tests -p "test_reconcile.py"`.

## Wave 2 (parallel): reports, invoices

## invoices
Owns: `fin/invoices.py`, `fin/documents.py`, `tests/test_invoices.py`.
Do (spec §13 invoices, §8 for nothing here, §12, and `report aging` in §13):
- `fin/documents.py` (shared with bills, wave 3): the document logic both kinds need: create a
  document with lines (net, tax, total, due = date + party's terms), number and issue
  (`INV-YYYY-NNNN`, count per year + 1), payments and paid totals, status and balance, and the
  invoice dict shape. Write it so bills can reuse it, and document its functions in Assumptions
  of the handoff.
- `invoice create --customer NAME --date DATE --line "DESC;QTY;PRICE;TAX" ...` (write, action
  `invoice.create`, target the id): split on ";", exactly four parts; QTY is a decimal string
  shown as given; PRICE via parse_amount, shown as money; TAX empty means none, otherwise it must
  exist in tax_codes. Net = cents(QTY × PRICE), tax = tax_on(net, rate). Customer must exist. At
  least one line. Draft, number null. Returns invoice shape per spec §13.
- `invoice issue ID` (write, `invoice.issue`): draft only. Number INV-<invoice-date year>-NNNN.
  Ensures Assets:Receivable, Income:Sales, Liabilities:SalesTax (book currency). Posts dated the
  invoice date, "Invoice INV-...": Receivable +total, Sales −net, SalesTax −tax if tax ≠ 0.
  Status issued.
- `invoice pay ID AMOUNT --date DATE --account ACCOUNT` (write, `invoice.pay`): AMOUNT > 0 via
  parse_amount; not draft, not paid; AMOUNT ≤ balance; ACCOUNT must be type asset. Posts
  "Payment INV-...": ACCOUNT +AMOUNT, Receivable −AMOUNT, and a payments row. Status partial or
  paid.
- `invoice show ID` (read), `invoice list [--status S]` (read) ordered by id.
- `report aging --at DATE [--payables]` (read, owned here): buckets per spec §13 and §14, using
  documents with kind invoice (or bill with --payables), non-draft, date ≤ DATE, balance as of
  DATE (payments dated ≤ DATE), days = DATE − due; keys current, 1-30, 31-60, 61-90, 90+, total.
  Skip zero balances.
Check: `python3 -m unittest discover -s tests -p "test_invoices.py"`.
Must not touch: reports.py, bills.py.

## reports
Owns: `fin/reports.py`, `tests/test_reports.py`.
Do (spec §8, §15, §17):
- `report income --from --to [--currency CUR]`, `report balance-sheet --at [--currency CUR]`,
  `report networth --from MONTH --to MONTH` (book currency), `report trial-balance --at DATE`
  (book currency), `report ledger ACCOUNT --from --to` (account's currency, no conversion),
  `report tax --from --to` (spec §15: non-draft invoices and all bills in the period; per-code
  tax from document_lines, codes not null).
- Currency: convert each account's sum at the report date with `ledger.convert`, round that
  account's value to cents, then total the rounded values. Income, liabilities, equity and
  their totals are negated raw sums. Accounts appear by name, if they have postings in range.
- Tests insert documents with SQL, not with commands from the invoices task (wave 2 is parallel).
  Use `core.post` and the commands from ledger and books.
Check: `python3 -m unittest discover -s tests -p "test_reports.py"`.

## Wave 3: bills

## bills
Owns: `fin/bills.py`, `tests/test_bills.py`.
Do (spec §14): reuse `fin/documents.py` from the invoices task (read its handoff and code; do
not duplicate it). `bill create --vendor NAME --ref TEXT --date DATE --line "DESC;AMOUNT;ACCOUNT;TAX"`
(write, `bill.create` target id): the vendor must exist; ref unique per vendor (documents
partial unique index; check first for a friendly error); AMOUNT via parse_amount; ACCOUNT must
exist and be expense or asset; TAX empty or an existing code. Posted at once dated DATE,
description `Bill REF`: each line's ACCOUNT +net, Assets:TaxReceivable +tax if tax ≠ 0,
Liabilities:Payable −total (ensure_account for the two liabilities/assets in book currency).
Bill shape per spec §14 (`vendor`, `ref`, lines with `account`).
`bill pay ID AMOUNT --date DATE --account ACCOUNT` (write, `bill.pay`): same rules as invoice
pay; ACCOUNT must be asset (assumption, list it). Posts "Payment REF": Payable +AMOUNT,
ACCOUNT −AMOUNT. `bill show ID` (read), `bill list [--status S]` (read) by id.
Check: `python3 -m unittest discover -s tests -p "test_bills.py"`.

## Wave 4: server

## server
Owns: `fin/server.py`, `tests/test_server.py`.
Do (spec §10): `serve --port N` (bootstrap=False, no user, write=False): run
`make_server(db_path, port)` (a ThreadingHTTPServer; expose it) with `serve_forever()`; the
command returns None. Use `ctx.db` for the path. Each request calls `core.run([...])` with
`--db`, `--user` (from X-User on POST), and the argv built from the path, query and JSON body.
Routes: the endpoints in spec §10, plus `GET /invoices`, `GET /invoices/ID`, `POST /invoices`,
`POST /invoices/ID/issue`, `POST /invoices/ID/payments` (body amount, date, account), `GET
/reports/aging?at=&payables=1`, `GET /audit`. Map: success → 200, `POST /transactions` and
`POST /invoices` → 201; `Result.status` 400/401/403 → same status with `{"error": msg}`;
unknown path or method → 404. POST without X-User: 401. Body is JSON; a bad body → 400.
Tests: start `make_server` on port 0 in a thread, use urllib.
Check: `python3 -m unittest discover -s tests -p "test_server.py"`.
