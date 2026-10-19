# wms: inventory and order management

Python 3.12+, standard library only. Run `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`
(global options first). Tests: `python3 -m unittest discover -s tests -t .`

Layout: `wms/util.py` (validation, decimals), `wms/core.py` (schema, transactions, CLI), `wms/stock.py` (movements, costing),
`wms/reserve.py` (reservations), `wms/commands/*` (commands), `wms/http_api.py` (HTTP API).
Every command runs in one SQLite `BEGIN IMMEDIATE` transaction, so it is all-or-nothing and concurrent requests are serialised.

## Assumptions
- Without `--json`, output is the same JSON, indented. `serve` needs no `--user`.
- Min/max of a product may be 0. Unit prices and costs may be 0, never negative. Warehouse names up to 100 characters,
  supplier up to 60, reasons up to 200 characters.
- Promo percent in (0, 100] with 2 decimals; a customer's price list need not exist as a price list.
- CSV import: read as UTF-8 (BOM allowed), blank lines skipped; errors for bad rows are printed one `error: row N: ...` per line.
- `po close` accepts only `open`/`partial` POs, as written. `po create` needs at least one line. The 5% over-receipt limit
  is cumulative per line (ordered × 1.05 rounded down, minus net received). `po.receive` audit target is the movement id.
- `adjust --count` is the absolute count at that location (and lot). Increases are costed like a receipt (fifo: newest layer
  ever in that warehouse; average: current average, or the last one when Q is 0). Serial products cannot be adjusted.
- `valuation`/`stock --at T` use the book as of the last movement at or before T; `aging --at DATE` replays to the end of DATE.
- A `transfer-in` into the source warehouse (cancel) restores the very layers; into another warehouse it creates layers keeping age.
- `so show` has `hold` null until the order is first confirmed.
- Reservation expiry is released before each command, with `reservation.expire` audit entries by user `system`.
- HTTP: see spec section 14; user errors map to 400, unknown objects 404, 401/403 for auth, 412/428 for ETag handling.
