# Plan: WMS (inventory & order management), Python 3.12 stdlib only
Full spec = `.claude/team/spec.md` (the user's request, word for word; section numbers below refer to it). Read the sections of your task fully.
**Check**: `python3 -m unittest discover -s tests -t .` (each task also has its own test file).

## Conventions (already written by lead; READ wms/core.py and wms/cli.py first, tests/util.py for test base class)
- Never write your own rounding/qty/money/validation: use wms.core (`round2`, `fmt2`, `fmt4`, `parse_qty`, `fmt_qty`, `parse_unit_cost`, `parse_date`, `need_re`, `split_serials`, `UserError`, `NotFound`...). Money/qty are Decimal in code, TEXT in sqlite (`str(Decimal)`); read with `D()`.
- A command module defines `@command("product add", "manager", setup)` handlers `handler(ctx, ns)` returning a JSON-able object (or None); `setup(parser)` adds argparse args (`parser.add_argument`). Register in a module named as listed in `core.COMMAND_MODULES` (cmd_setup, cmd_stock, cmd_views, cmd_po, cmd_transfer, cmd_orders, cmd_returns, cmd_serve). Command names are exactly as in the spec ("po receive", "so pick", ...). Authorization and the transaction are done by `cli.execute`: handlers just raise `UserError`/`NotFound` (unknown object) and call `ctx.audit(action, target)`.
- Schema is fixed in `core.SCHEMA` (comments explain each table). If you need a schema change, ask nothing: add the smallest change in core.py and log it in `.claude/team/changes.md` (one line: file, what). Otherwise do not edit core.py/cli.py.
- Output JSON keys in the exact order and string formats of the spec; lists sorted as stated. Handlers return data only; cli prints it.
- Tests: `tests/test_<task>.py` using `tests.util.Env` (`self.init()`, `self.ok(...)`, `self.bad(...)`, `self.run_cli`). Never name a helper like a unittest method. Test the spec's formats and error cases for your commands.
- Do not use pytest, third-party libs, or binary floats.

## Engine contract (module `wms/engine.py`, owned by task `engine`; later tasks import it)
All take `ctx`, raise UserError on rule violations, return the spec movement dict (via `core.insert_movement`) unless stated. `loc` args are 'WH/LOC' strings; `qty`, `cost` Decimal; `lot` str|None; `serials` list|None.
- `receive(ctx, sku, qty, at, cost, lot=None, expires=None, serials=None, ref=None, mtype="receive", unit_cost_override=None)` — all `receive` rules (§4) incl. lot/serial validation, location type receiving|storage, layers/average (§5). `mtype="return"` is used by returns (location must be storage is checked by the caller).
- `move_stock(ctx, mtype, sku, qty, frm, to, lot=None, serials=None, ref=None, check_reserved=True)` — stock between locations (no cost change, value 0.00). `move` command checks same warehouse, not to SHIP; `pick` uses `mtype="pick", check_reserved=False`.
- `remove_stock(ctx, mtype, sku, qty, frm, lot=None, serials=None, ref=None, check_reserved=True)` — stock leaves the book/warehouse (`scrap`, `ship`, `transfer-out`; `to` null), consumes layers / average per §5, records `consumptions` rows, value set. `ship` uses check_reserved=False.
- `adjust_stock(ctx, sku, at, count, reason, lot=None)` — §4 adjust.
- `void_movement(ctx, mid, reason)` — §4 void; also must fix `reservations`-independent state only; PO received qty is derived from `po_receipts` joined to `movements.voided=0`.
- `transfer_in(ctx, out_movement_id, to, ref)` — brings back the stock of a `transfer-out` movement into `to` (destination receive, or cancel into the source) as a `transfer-in` movement with the out movement's value; fifo: copies each consumed slice as a layer in the destination warehouse with same unit cost, same `at` and `mv` as the layer it came from (for same warehouse = cancel: add back into the very layers); average: adds value/qty; lot expiry kept; serials restored with new location.
- `reserved_qty(ctx, sku, loc, lot)` -> Decimal (sum of reservations rows, state reserved or picked, at that location/lot); `on_hand(ctx, sku, loc, lot)` -> Decimal; `serials_at(ctx, sku, loc)` -> sorted list.
- `wh_qty_value(ctx, wh, sku)` -> (Decimal qty, Decimal value) current valuation per §5.
Stock rows: table `stock` (lot '' when untracked), `serials` table for serial units.

## Rules (from spec; reviewed against code)
- Errors: stderr `error: ...`, nothing on stdout, exit 2, all-or-nothing (§Conventions). Unknown objects NotFound.
- Roles per command exactly as §1 (the `command` decorator role arg: viewer for all read-only commands).
- Qty: each whole numbers, kg ≤3 decimals; zero/negative where qty needed = error; printed as strings (each int, kg 3 decimals). Money 2 decimals, unit costs/prices accepted ≤4 decimals printed 4; half-up rounding.
- Lists sorted as stated (by id/code ascending otherwise). Ids: movements from 1; PO-0001 etc. per-kind counters.
- Audit: every data-changing command → one audit entry with action/target exactly as §13.
- Product SKU/name/min/max rules §2; warehouse/location code rules §3; user rules §1 (last enabled admin).
- Stock never below zero; reserved stock can't move/scrap/transfer; stock in SHIP is the order's.
- fifo layers ordered by (at, mv); average per §5; values round2.
- Reservation order & rules §8 (storage only, expired lots never, lot expiry/lot/location order).

## Tasks
### setup  (wave 1)
Files: wms/cmd_setup.py, tests/test_setup.py. Commands: `init`, `user add|role|disable|list`, `product add|show|edit|list`, `warehouse add|list`, `location add|list`, `customer add|list`, `price set|list`, `promo add|list`, `import products`, `audit list`; §1,2,3,7(first part: customers, prices, promos CRUD only),12,13. `init` handler: create admin user, set meta currency, audit 'init' with user=admin name (ctx.user is None for init). May change: core.py minimal additions. Don't touch other cmd_ files. Done: `python3 -m unittest tests.test_setup`.
### engine  (wave 1)
Files: wms/engine.py, wms/cmd_stock.py, tests/test_engine.py. Implement the Engine contract above and commands `receive`, `move`, `adjust`, `scrap`, `movement void` (movement list is task `views`). §4, §5 (costing semantics, layers, average, void rules). Tests need products/warehouses: create them through the CLI commands `product add`, `warehouse add`, `location add`, `user add` — these are being written in parallel by task `setup`; until they exist insert test fixtures with direct SQL on the db (via a small test helper) OR wait/retry later; final tests must pass with the real commands. May change: core.py minimal additions. Done: `python3 -m unittest tests.test_engine`.
### views  (wave 1)
Files: wms/cmd_views.py (stock with --at but WITHOUT reserved/available when --at is given; WITH reserved from `reservations` table otherwise; `movement list`; `valuation` incl. --at and in_transit from `transfers` table; `aging`). §4 (movement list, stock), §5 (valuation, aging), §8 (stock output format). `available` and `reorder` belong to task `orders`. For --at replay `movements` (signed qty by from/to, signed value per warehouse; for fifo/average use movement values; transfers in transit at time T: derive from transfer-out/in movements by ref). Tests: tests/test_views.py inserting movements/layers with direct SQL via helper, plus real commands once available. Done: `python3 -m unittest tests.test_views`.

### po  (wave 2) Files: wms/cmd_po.py, tests/test_po.py. `po create|receive|close|show|list` §6 (uses engine.receive, table po_receipts).
### transfers (wave 2) Files: wms/cmd_transfer.py, tests/test_transfer.py. §9 using engine.remove_stock / engine.transfer_in.
### orders (wave 2) Files: wms/cmd_orders.py, tests/test_orders.py. `so create|confirm|allocate|pick|ship|cancel|show|list`, `available`, `reorder`; §7 pricing, §8, §11. Uses engine.move_stock/remove_stock. Reservation expiry already handled in cli.
### returns (wave 3) Files: wms/cmd_returns.py, tests/test_returns.py. §10.
### api (wave 3) Files: wms/cmd_serve.py, tests/test_api.py. §14 via `cli.execute(db, user, now, argv)`; one global lock around execute; ThreadingHTTPServer; map NotFound→404, Unauthorized→401, PermissionDenied→403, UserError→400; idempotency table `idem`. Body-based POSTs translate to argv lists. Needs `serve` registered with role viewer but run without auth.
