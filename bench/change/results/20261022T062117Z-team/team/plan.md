# Plan
Goal: the lead already implemented all three items in wms/ (see `git diff`). Teammate `tests` adds tests.
Check: `python3 -m unittest discover -s tests`

## tests
Owns: tests/test_changes.py (new). Must not edit wms/, docs/, tests/test_smoke.py.
Read .claude/team/spec.md (the user's request) and `git diff` for the implementation. Write unittest
tests in the style of tests/test_smoke.py (subprocess CLI with --db temp, --json, --now; also an HTTP test
via `serve` on a free port with X-User header is optional). Cover:
1. `--at` exactly at a movement time includes it, for `valuation --at` and `stock --at`; just before excludes.
2. Archiving: archive/unarchive output, version +1, `archived` key only when archived, errors (unknown=exit 2,
   already in that state, stock, in-transit, open/partial PO, non-shipped/cancelled SO), product list / --archived / --search,
   receive/adjust/po create/so create/price set/promo add --sku/return create/product edit refused and change nothing,
   reorder skips archived, audit actions, role manager needed (clerk refused), HTTP endpoints (200/400/404, ?archived=1, PATCH 400).
3. Credit limits: customer add --credit-limit, customer limit NAME AMOUNT|none, 2-decimal printing, bad amounts (0, -1, 1.234, abc),
   unknown customer, `credit_limit` key only when set, customer list, so confirm refused when over, allowed when exactly the limit,
   other orders count only when confirmed/backordered/partially_shipped (cancelled, shipped, draft don't), audit `customer.limit`.
Done check: `python3 -m unittest discover -s tests` passes in under a minute. If a test fails because of a real
bug in wms/, don't edit wms/: describe it in the handoff.
