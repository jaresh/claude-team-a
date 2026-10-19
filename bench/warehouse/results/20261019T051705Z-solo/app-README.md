# wms — inventory and order management

Python 3.12+, standard library only. Run `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`.
Tests: `python3 -m unittest discover -s tests -t .`

Layout: `wms/core.py` (schema, stock and costing primitives), `wms/cmds_a.py` (users, products, stock,
valuation), `wms/cmds_b.py` (POs, pricing, sales orders, transfers, returns), `wms/cli.py`, `wms/server.py`.
Each command runs in one SQLite transaction (`BEGIN IMMEDIATE`); a user error rolls everything back.

## Assumptions

- Without `--json` the output is the same JSON, pretty-printed.
- `product edit` with no change option is a user error. `min`/`max` of `0` are accepted; `each` quantities may be written `5.0`.
- Movement `serials` and stock `serials` are sorted. A voided receipt's cost layer is discarded (not "newest layer ever").
- A draft order shows `hold`, `expires` and all prices as null. `so confirm` on a non-draft order is a user error.
- Reservation expiry is "expires <= now". Expiry audit entries use the command's time.
- `--at` on `stock`/`valuation` uses the set of movements whose own time is <= TIME (not an id cutoff).
- `po.*`, `so.*`, `transfer.*`, `return.create` audit targets are document ids; `po.receive` targets the PO id.
- Average costing: voiding a receipt/increase fails if any later movement of the product crossed the warehouse boundary
  (internal moves do not count). A fifo increasing-adjust uses the newest live layer by (time, movement id).
- A damaged return records the return document only (`to` is null, value `0.00`); lot-tracked returns are also checked per lot.
- Pick/ship consume reservations of the order; cancelling an order after pick leaves the stock in `SHIP` unreserved.
- Idempotency keys are global (not per user); a stored response includes error responses (401/403/400...).
- HTTP: authentication (401) is checked before routing (404) and role (403). 404 is used only for unknown paths and
  unknown objects in the path; unknown objects named in a body are 400. All requests are serialized by a global lock.
- `serve` and `init` take no `--user`. `init` validates before creating the database file.
