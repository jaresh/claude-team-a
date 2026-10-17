# Handoff: invoices (spec sections 13, 14, 15)

## Done
- `fin/cmd_invoices.py` (new): COMMANDS for tax add/list, customer add/list, vendor add/list, invoice create/issue/pay/show/list, bill create/pay/show/list, report aging (`--payables`), report tax. SCHEMA creates `tax_codes`, `party_customers`, `party_vendors`, `inv_invoices`, `inv_lines`, `inv_payments`, `bill_bills`, `bill_lines`, `bill_payments`.
- `tests/test_invoices.py` (new): 34 tests covering sections 13-15, including error cases (exit 2, empty stdout, nothing changed), closed-period blocking for issue/pay/bill create/pay, viewer denial, and posting checks read directly from the `postings` table.
- Check results:
  - `python3 -m unittest tests.test_invoices -q`: Ran 34 tests, OK (about 33 s).
  - `python3 -m unittest discover -s tests -q`: Ran 139 tests, OK (about 81 s, run in the foreground).
- No shared files edited (`core.py`, `cli.py`, `helpers.py`, `changes.md` untouched). Nothing committed.

## In progress
- Nothing. The section is complete.

## Next step
- Lead: nothing needed from me. To re-verify: `cd /home/jaca/claude-team-a/bench/work/finance-team && python3 -m unittest tests.test_invoices -q`. There is no `python` binary in this shell, only `python3`.
- Note: EnterWorktree was not available in this session, so I worked directly in the shared checkout `/home/jaca/claude-team-a/bench/work/finance-team`. The new files are untracked (`fin/cmd_invoices.py`, `tests/test_invoices.py`) and need committing by the lead.

## Do not redo
- Account names: the top-level segment is `Expenses`, not `Expense` (core `TYPES`). Bill line accounts must be `Expenses:*` or `Assets:*`; the tests use `Expenses:Office`.
- Account type check for payments uses the stored `accounts.type` (`asset`), and for bill lines `expense` or `asset`. Both checks happen before any posting.
- Tests create accounts through the `cmd_books` CLI (`account add`) and close periods through `period close`. This depends on `cmd_books` being merged, which it is in this checkout.
- The `invoices` tests take about 33 s because each command is a subprocess. That is acceptable under the done check but slow; no change planned.

## Assumptions (for the README)
- Invoice numbers: `INV-YYYY-NNNN`, where YYYY is the invoice date's year and NNNN is a per-year counter in issue order (0001 first), counted from the stored numbers. The number is assigned at issue, not at draft creation. Draft numbers are `null`.
- Due dates: invoice due = date + customer terms (default 30 days); bill due = date + vendor terms (default 30 days). Terms are whole days, non-negative.
- Line amounts: `net = round(quantity * price)`, `tax = round(net * rate / 100)` per line. Invoice and bill totals are the sums of line values. Quantity and price are stored as given; price is output with `fmt`.
- An empty TAXCODE in a line means no tax: `tax_code` is `null` and tax is `0.00`. An unknown tax code is a user error. Tax rates must parse as decimals; negative amounts and quantities are rejected.
- Posting on issue: `Assets:Receivable` +total, `Income:Sales` -net, and `Liabilities:SalesTax` -tax only when tax is nonzero. Bill create: each line's account +net, `Assets:TaxReceivable` +tax when nonzero, `Liabilities:Payable` -total. Missing accounts are created with `ensure_account` in the book currency.
- Payments: amount is rounded to cents and must be > 0 and <= the balance. The payment account must be an asset account. Status becomes `partial` or `paid`. Paying a draft, an already-paid document, or overpaying is a user error.
- Aging: includes only non-draft invoices and all bills dated on or before `--at`. Only payments dated on or before `--at` reduce the balance. Days past due = `at - due`; `<= 0` is `current`, then `1-30`, `31-60`, `61-90`, `90+`. Zero-balance documents are excluded. Bills use `--payables`.
- Tax report: `collected` = tax of non-draft invoices dated in the range; `paid` = tax of bills dated in the range; `net = collected - paid`. `by_code` includes every code used on a line in the range, including zero-rate codes, with both keys.
- Viewer role: read-only commands (lists, show, aging, tax report) work for viewers; writes are denied with 403 by the CLI.

## Do not redo (core observations)
- No bugs found in `core.py`, `cli.py` or `helpers.py` that block this module.
- `period close` takes a month argument (`cmd_books`), used by the tests as `period close 2026-02`.
