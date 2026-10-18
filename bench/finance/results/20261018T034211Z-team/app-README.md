# fin — small-business finance system

Python 3.12+, standard library only. Run `python3 -m fin [--db PATH] [--json] [--user NAME] COMMAND ...`
(global options first; `--db` defaults to `./fin.db`). Tests: `python3 -m unittest discover -s tests`.

## Usage
    python3 -m fin init --currency EUR --admin alice
    python3 -m fin --user alice account add Assets:Bank
    python3 -m fin --user alice txn add --date 2026-01-05 --desc Rent --posting Expenses:Rent=900 --posting Assets:Bank
    python3 -m fin balance ; python3 -m fin report income --from 2026-01-01 --to 2026-01-31
    python3 -m fin --user alice serve --port 8080     # API; POSTs need header X-User

Commands: init, user, audit, period, account, txn, balance, fx, convert, rule, import, budget, report
(income, balance-sheet, networth, budget, aging, tax, trial-balance, ledger), recurring, loan schedule,
tax, customer, vendor, invoice, bill, reconcile, serve. Layout: `fin/common.py` (shared helpers, schema),
`fin/cli.py` (dispatch, permissions), one `*_cmds.py` module per area, `fin/server.py` (HTTP).
Errors exit 2 with a message on stderr. Without `--json` output is indented JSON (same documents).

## Assumptions
- Command is `python3` here; tests invoke `sys.executable -m fin`.
- Non-JSON output is the same document, pretty-printed. `init` prints `{"currency","admin"}`; other mutating commands without a specified output print the created/changed record.
- txn: description not blank. `--account` matches the account or its descendants (not a raw string prefix). balance lists zero-sum accounts as "0.00".
- fx add: FROM != TO, rate > 0; output `{"date","from","to","rate"}`; a direct rate on/before the date beats a newer inverse one. convert requires `--at`.
- Import: whole file validated first (bad row, closed period, zero amount => nothing imported); dedup against earlier imports and earlier rows in the same file; audit entry only if something was imported; importing to an account in a non-book currency with a book-currency category fails (unbalanced). Rule accounts must be valid names; categories created on demand.
- Budget: expense accounts only; actual converted to the budget account's currency at month end. recurring run audits only if something was created; a closed period fails the whole run.
- Reports: each account converted at the report date and rounded per account; totals sum the rounded values (may differ by a cent in multi-currency books). trial-balance is always in the book currency. `--from` after `--to` is an error. Ledger report converts descendant postings at their own date.
- Invoices/bills: line format `a;b;c;d` split on `;` (no `;` in descriptions); quantity > 0, price >= 0, tax rate >= 0, terms >= 0; at least one line. Invoice/bill ids are per kind. Drafts may be created in a closed period (issuing is refused). Payment accounts must be asset accounts; payment must be > 0 and <= balance. Aging excludes drafts. Tax report excludes drafts; by_code lists codes used even if tax is zero.
- Permissions: viewer = read-only commands; editor = all but `user add`, `period close`; `init` needs no user. `serve` itself is started without a user.
- API: binds 127.0.0.1; `;` in invoice line fields rejected (400); numbers in bodies accepted; other HTTP methods → 501; internal errors → 500; unknown path → 404 (checked before auth for POST? see tests).
