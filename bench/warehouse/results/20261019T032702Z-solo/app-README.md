# wms — inventory and order management

Python 3.12+, standard library only. Run `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`;
tests: `python3 -m unittest discover -s tests`.

Layout: `wms/util.py` (parsing, rounding, errors), `wms/core.py` (users, products, stock, costing, movements, reports),
`wms/docs.py` (POs, prices, sales orders, transfers, returns, reorder), `wms/app.py` (one SQLite transaction per
command), `wms/cli.py`, `wms/server.py` (HTTP, requests serialised by a global lock).

## Assumptions
- Quantities are stored as integer thousandths. A value such as `5.0` is accepted for `each` (it is whole); `1.2500`
  is accepted for `kg` (3 decimals by value). `min`/`max` and `adjust --count` may be 0; other quantities must be > 0.
- Command order inside a transaction: expire reservations, check user and role, run. Any user error rolls back all of it,
  including the `reservation.expire` entries.
- Audit targets for documents: PO/SO/TR/RT id (`po.receive` uses the PO id); `receive/move/adjust/scrap` use the movement id.
- `product edit` with nothing to change is a user error. `user disable` of an already disabled user is a no-op success.
- Draft orders show `hold` and `expires` as null. A draft order may be cancelled. Cancelling an order with shipped goods is an error.
- `so show` `expires` is the earliest expiry among the order's unpicked reservations.
- FIFO "newest layer" (for increasing adjusts) is by (time, movement id) over layers still on record; a layer deleted by
  voiding its receipt is no longer on record. Transferred layers keep their original time/movement id.
- Average costing: after Q reaches 0 the last average is kept for later increasing adjusts.
- Returns: lot-tracked returns are also capped by what was shipped from that lot; a damaged return ignores `--to`
  (output `to` null) and still counts as returned. Return unit cost uses the line's total shipped quantity.
- Movements `value` for `pick`/`move` is `0.00`; `void` copies the original value; cost-neutral movements have no `unit_cost`.
- `valuation --at` / `stock --at` use movements whose `at` is <= TIME, taken in id order; `aging --at` uses current layers.
- Line promotions/order promotions use the day of the confirming command's time. Order promotion thresholds compare with the subtotal exactly.
- `available` does not exclude expired lots; only reservation does.
- HTTP: `PATCH` null for min/max clears it; unknown paths give 404 before authentication; idempotency keys are stored in the
  database (table `idem`) with the canonical JSON body; the stored response includes error responses.
  `GET /valuation` and `GET /stock` take `warehouse`/`sku` query parameters.
- `import products` rejects SKUs that already exist in the book as well as duplicates inside the file.
- A non-initialised database file path gives a user error for every command except `init`.
