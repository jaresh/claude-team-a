# WMS — inventory and order management

Python 3.12, standard library only. Run: `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`
Tests: `python3 -m unittest discover -s tests -t .`

Layout: `wms/core.py` (errors, rounding, validation, schema, movements), `wms/cli.py` (dispatch, auth, one transaction per command,
reservation expiry), `wms/engine.py` (stock, costing, voids), `wms/cmd_*.py` (commands), `wms/cmd_serve.py` (HTTP API).

## Assumptions
- Output without `--json` is the same JSON, indented.
- Min/max quantities of a product must be greater than zero; `none` clears them.
- Reasons for `adjust`, `scrap` and `movement void` are required and validated but not stored (no field in the movement shape).
- `adjust` is allowed at any location of the book, including `SHIP`.
- Disabling an already disabled user is a no-op that still writes an audit entry.
- Short stock at `so confirm`/`so allocate` is not an error: the order reserves what is free and becomes `backordered`.
- `price set` without `--min-qty` stores minimum 0 in the unit's format.
- `GET /valuation` without `warehouse` returns all warehouses.
- Unknown objects are HTTP 404; other user errors 400. `serve` runs outside the command transaction; each request is one serialized transaction (a global lock), which guarantees no double reservation.
- Valuation `--at` is replayed from movement values, so a fifo product may differ by a cent from layer-based rounding.
- Reservation expiry runs at the start of every command once the book exists, inside that command's transaction.
