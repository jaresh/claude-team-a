# WMS: inventory and order management

Python 3.12+, standard library only. Run `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`.
Tests: `python3 -m unittest discover -s tests -t .`
Layout: `wms/core.py` (shared helpers, schema, dispatch), `cli.py`, and one module per area
(users, catalog, costing, inventory, sales_catalog, purchasing, transfers, orders, returns, importer, http_api).

## Assumptions (spec left open)
- Output shapes of write commands without a stated shape: `init` → `{"currency","admin"}`; `user add/role/disable` → user object;
  `customer add`, `price set`, `promo add` → the matching list object.
- `user disable` on a disabled user is an error; setting the same role is allowed (audited); `user add --role` is required; disabled admins don't count as admins.
- `audit list --user` filters by the acting user (internal dest `by_user`). `po receive`/`po close` audit target is the PO id.
- Names: warehouse name 1–100 chars; customer 1–60; supplier 1–100 (stripped). A PO needs ≥1 line; `product edit` with nothing to edit is an error.
- Serial uniqueness is checked across all warehouses. `adjust`/`scrap`/`void` need a non-empty reason (stored, not shown in movement JSON).
- Moves to a `SHIP` location are only possible via `so pick`.
- Costing: "newest layer" for an increasing adjust is by time, movement id, then creation; `aging --at` uses the current layers (not historical); negative ages count in `0-30`.
- Orders: `so list --status` accepts only the six statuses; `hold` is null until confirm; `expires` is the earliest unpicked reservation expiry; `--hold` must be a whole number 1–720; cancelling a cancelled or partly shipped order is an error. Lots without an expiry row are treated as unexpired.
- `available` counts all storage stock minus reservations, including lots that `so confirm` would skip as expired (literal spec).
- Returns: `--to` required for `good`, forbidden for `damaged`; damaged returns count toward the returned quantity; lot returns check only that the lot shipped on the line.
- Import: blank lines skipped; wrong column count reported per row; an empty file imports 0 and is still audited.
- HTTP: one global lock serializes requests (all-or-nothing, no double reservation); idempotency keys are stored forever.
