# WMS — inventory and order management

Python 3.12+, standard library only. Run: `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`
(`init --currency EUR --admin alice` first). HTTP API: `serve [--port N]`.

Layout: `wms/core.py` (errors, numbers, time, SQLite schema, transaction runner), `wms/cli.py` (command registry),
`wms/catalog.py`, `parties.py` (setup data), `engine.py` + `inventory.py` (stock and costing), `reports.py`,
`purchasing.py` (POs, transfers), `sales.py` (orders, reservations, returns), `api.py`.

Tests: `python3 -m unittest tests.unit_catalog tests.unit_inventory tests.unit_reports tests.unit_purchasing tests.unit_sales tests.unit_api`
and the spec-based acceptance suite `python3 -m unittest discover -s tests/acceptance -t .` (about 5 minutes).

## Assumptions
- Every command is one SQLite transaction (`BEGIN IMMEDIATE`) behind a global lock; reservation expiry runs first inside it.
- Without `--json` the output is the same JSON, indented.
- Unknown objects (product, location, warehouse...) are user errors (exit 2; HTTP 404). Unknown warehouse in a filter is an error.
- `ship` and other non-receive movements have `unit_cost` null (as the spec says); `transfer receive`/`cancel` print the transfer object.
- Quantities: `each` must be whole, `kg` up to 3 decimals; unit costs/prices up to 4 decimals, amounts 2.
- Min/max quantities must be greater than 0. Returned serial lists are not guaranteed sorted except where the spec says so.
- PO: a `received` PO cannot be closed (only open/partial); receive cap is ordered × 1.05 rounded down to the unit precision.
- HTTP: unknown body fields give 400; idempotent replays return the stored response whoever sends them; unexpected errors give 500 and roll back.
- Receipts dated before the book's init time are accepted.
- Costing details: moves do not consume fifo layers (costing is per warehouse); see `wms/engine.py`.
