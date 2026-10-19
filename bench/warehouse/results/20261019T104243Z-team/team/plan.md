# Plan: warehouse management system (spec: .claude/team/spec.md, the user's request, word for word)

## Goal
CLI + HTTP inventory/order system in `wms/`, stdlib only, Python 3.12. Check: `python3 -m unittest discover -s tests -t . 2>&1 | tail -20`
(the tester's acceptance tests in tests/acceptance/, plus each expert's unit tests in tests/unit_<area>.py).

## Contract (already written by the lead and working: READ wms/core.py and wms/cli.py first)
- `wms/core.py`: UserError (+NotFound 404, Unauthorized 401, Forbidden 403, Conflict 409, PreconditionFailed 412,
  PreconditionRequired 428), D/round2/round4/fmt2/fmt4/fmt_qty/parse_qty/parse_money/parse_number/require_match,
  parse_time/fmt_time/parse_date, `Ctx` (db, now, now_s, today, user, audit(), next_seq(), next_doc_id(), product(), warehouse(),
  location() , currency), `run(db_path,user,now,role,fn)`, and the full SQLite SCHEMA with comments. The schema is the contract between
  modules; do NOT change it. If you truly need a change, append a line to changes.md and tell the lead in your handoff.
  Decimals are stored as TEXT (`str(Decimal)`); read with `D(...)`. Never use float.
- `wms/cli.py`: each module `wms/<name>.py` exposes `COMMANDS = [Command(name="po create", role="manager", add_args=fn(parser), run=fn(ctx, ns))]`.
  `run` returns the JSON-able data (the exact shapes of the spec), does its audit via `ctx.audit(action, target)`, and raises UserError for any
  user error. All DB work through `ctx.db` (sqlite3.Row rows). The transaction, user/role check and reservation expiry are done by core.run.
  Command names are space-separated ("product add"). Module names: catalog, parties, inventory, reports, purchasing, sales, api.
  Quantities in options are parsed with parse_qty(text, product_unit) after looking up the product; printed with fmt_qty(d, unit).
  JSON output must be built with the spec's key names/order; money via fmt2/fmt4 (strings).
- Movements: `movements` table, `extra` JSON keys: `deltas` (fifo layer deltas `[[layer_id, signed_qty], ...]`: + new/restored, − consumed),
  `avg` (average costing: `{"wh","q","v","a"}` state of the warehouse/product AFTER the movement), `line` (PO/SO line), `reason`.
  `stock --at`, `valuation --at`, in-transit and fifo/avg values at a past time are rebuilt from movements (+ layers table for unit costs/ages).
  Void movements carry the same deltas/avg bookkeeping so that history replays correctly (void sets original's `voided_by`).
- Stock rows: `stock(sku, location 'WH/LOC', lot '' if none, qty)`; serial units in `serials`. Reservations in `reservations`
  (state reserved|picked). Stock in a SHIP location belongs to picked reservations.
- `wms/engine.py` (owned by `inventory`; other modules call it, never write stock/movements/layers themselves):
  - `mv_dict(row) -> dict` movement JSON shape of spec section 4 (id, at, user, type, sku, qty, from, to, lot, serials, unit_cost, value, ref).
  - `get_stock(ctx, sku, location, lot='') -> Decimal`; `reserved_qty(ctx, sku, location, lot='') -> Decimal` (reserved + picked rows).
  - `receive_stock(ctx, mtype, sku, qty: Decimal, to, cost: Decimal, lot=None, expires=None, serials=None, ref=None, extra=None) -> dict`
    mtype 'receive' or 'return'; applies all tracking/location rules of `receive`, makes the layer / average update; returns movement dict.
  - `shift_stock(ctx, mtype, sku, qty, from_, to, lot=None, serials=None, ref=None, extra=None) -> dict` stock moves inside one warehouse
    (mtype 'move' or 'pick'): checks stock exists, serial locations; NO reservation check, NO SHIP-destination rule (callers do those).
  - `remove_stock(ctx, mtype, sku, qty, from_, lot=None, serials=None, ref=None, extra=None) -> dict` stock leaving the book
    (mtype 'ship','scrap','transfer-out'; adjust uses it internally): checks stock, values per costing, records deltas/avg; NO reservation check.
  - `bring_in_transfer(ctx, out_mv_id, to, ref, restore: bool) -> dict` makes the `transfer-in` movement for a transfer-out movement
    (restore=False: new layers in destination wh keeping src_mv/src_at; restore=True (cancel): back into the original layers); lots keep expiry.
  - `product_unit(ctx, sku)`; helper `wh_of(location_text)`.
  Errors: UserError. Engine functions raise before changing anything or are rolled back by the transaction (everything is one transaction).
- Audit actions/targets exactly as spec section 13. `reservation.expire` is done by core.

## Conventions
- Each module's unit tests go in `tests/unit_<expert>.py` (unittest, run through the CLI via subprocess with a temp db, or via wms.core.run). Never name a test helper like a unittest method (fail, run, setUp, assert*).
- Module-level code style: plain functions, no classes needed beyond Command; short comments only where the rule is non-obvious. Use core helpers; never re-implement parsing/rounding/formatting.
- Validate everything before writing. Unknown objects: NotFound. Text from options is stripped only where the spec says so.
- Do not touch files you do not own. Log edits to shared files in .claude/team/changes.md (one line each).
- Decide unspecified details sensibly and list assumptions in your handoff (the lead puts them in README.md).

## Experts
- tester: acceptance tests from the spec alone.
- catalog: users, products, warehouses, locations, customers, prices, promos, import, audit list.
- inventory: engine.py, receive/move/adjust/scrap/movement void.
- reports (wave 2): stock, valuation, aging, movement list, available, reorder.
- purchasing (wave 2): PO and transfers.
- sales (wave 2): pricing, sales orders, reservations, pick/ship/cancel, returns.
- api (wave 3): `serve` HTTP API.

## tester
Files: tests/acceptance/__init__.py, tests/acceptance/helpers.py, tests/acceptance/test_*.py (several files by area). Write acceptance tests from the spec only (never read wms/ code, change no app code): a helper running `python3 -m wms --db DB --json [--user U] [--now T] cmd...` via subprocess and checking exit code/stdout/stderr; tests for every section 1-13 (exact output shapes and numbers, rounding, permissions per role, all-or-nothing errors, audit entries, expiry of reservations incl. audit, voids, costing fifo/average examples with hand-computed numbers, transfers, returns, imports with row errors) and a few HTTP tests of section 14 (start `serve --port` on a free port in a subprocess). Done check: `python3 -m unittest discover -s tests/acceptance -t . 2>&1 | tail -5` loads and runs (failures expected until code exists; no import/syntax errors). Don't touch wms/.

## catalog
Owns wms/catalog.py (users, product, warehouse, location, import products, audit list) and wms/parties.py (customer add/list, price set/list, promo add/list). Spec sections 1, 2, 3, 7 (only the commands, validation and listing; the pricing calculation belongs to sales), 12, 13 (audit list; audit entries for your commands). Unit tests tests/unit_catalog.py. Done check: `python3 -m unittest tests.unit_catalog 2>&1 | tail -5`. May change: only your files and tests. `import products` row checks must reuse the same validation function as `product add` (one function), and the last-enabled-admin rules.

## inventory
Owns wms/engine.py and wms/inventory.py (commands receive, move, adjust, scrap, movement void). Spec sections 4 (all but `movement list`), 5 (costing rules; valuation/aging commands are NOT yours), 13. Implements the engine contract above exactly. Reservation checks (move/scrap/adjust/void need unreserved stock; adjust count below reserved is an error) use engine.reserved_qty. Void rules per spec. Unit tests tests/unit_inventory.py: fifo and average examples (incl. value rounding, void restoring layers, serials, lots). Products/warehouses/locations are created by the catalog expert in parallel, so in unit tests insert rows with SQL directly through wms.core.run + SCHEMA after init (`python3 -m wms init`), not via catalog commands. Done check: `python3 -m unittest tests.unit_inventory 2>&1 | tail -5`.

## Wave 2 notes
Engine extras written by inventory: `require_unreserved(ctx, sku, location, qty, lot="", serials=None)`, `void_movement`, `tracking_key(p, qty, lot, serials) -> (lot_key, serial_list)`. READ wms/engine.py (function signatures + docstrings) and wms/inventory.py as a style example. catalog's helpers are in wms/catalog.py (e.g. check_product). Other modules are being written in parallel; never edit them. Unit tests: set up data via the CLI (`python3 -m wms ...` in-process via wms.cli.main like tests/unit_inventory.py does) — catalog and inventory commands already work.

## reports
Owns wms/reports.py and tests/unit_reports.py. Commands: `movement list`, `stock`, `valuation`, `aging`, `available`, `reorder` (all role viewer), exact shapes per spec sections 4, 5, 8, 11. `--at` variants are rebuilt from movements/layers per the movement `extra` contract (read engine.py to see exactly what it records: deltas, avg). `available`/`reorder` read pos/po_lines/po_receipts, orders/order_lines/reservations tables (written by other experts; in unit tests insert those rows with SQL). Also export `available_qty(ctx, sku, wh)`, `incoming_qty(ctx, sku, wh)`, `backordered_qty(ctx, sku, wh)` (Decimals) in reports.py. Order status derivation helper (for backordered): orders.state 'open' with order_lines qty vs reservations(reserved+picked)+shipped. Done check: `python3 -m unittest tests.unit_reports 2>&1 | tail -5`.

## purchasing
Owns wms/purchasing.py and tests/unit_purchasing.py. Commands: `po create/receive/close/show/list`, `transfer create/receive/cancel/show/list`; spec sections 6, 9, 13 (audit actions). Uses engine.receive_stock / remove_stock / bring_in_transfer; po receive writes po_receipts (mv_id, po, line, qty) and extra={"line":N}. Transfer create needs unreserved stock (engine.require_unreserved), source must be a storage location, destination storage/receiving of a different warehouse; serials in transit are not at any location. Done check: `python3 -m unittest tests.unit_purchasing 2>&1 | tail -5`.

## sales
Owns wms/sales.py and tests/unit_sales.py. Commands: `so create/confirm/allocate/pick/ship/cancel/show/list`, `return create/list`; spec sections 7 (pricing calculation at first confirm), 8 (all but stock/available), 10, 13. Reservations table per Contract; reservation order rules; hold/expiry; pick via engine.shift_stock(mtype 'pick', ref=order id, extra {"line":N}) to WH/SHIP and update reservation rows to state 'picked'; ship via engine.remove_stock from SHIP (one per line and lot, extra {"line":N}); updates order_lines.shipped; return create uses ship movements' values (movements with ref=order id, type ship, extra line) and engine.receive_stock(mtype 'return'). Export `order_status(ctx, order_id)` and `show_order(ctx, order_id)` in sales.py. Done check: `python3 -m unittest tests.unit_sales 2>&1 | tail -5`.

## api
Owns wms/api.py and tests/unit_api.py. Command `serve [--port N]` (Command with raw=True, run(ns) uses ns.db; ThreadingHTTPServer on 127.0.0.1, X-User / X-Now headers). Spec section 14 in full. Every request runs through core.run(db_path, user, now, role, fn) (it already serializes with a global lock and rolls back on error; map UserError.status to the HTTP status; 401 for missing/unknown/disabled user, 403 role too low); reuse the command logic by calling functions in catalog.py/inventory.py/engine.py/sales.py/reports.py (read them; refactor nothing: if a command's logic is only inside its `run(ctx, ns)`, build a small argparse.Namespace and call that run function, which keeps audit and rules identical). Idempotency table `idempotency` exists in the schema; the idempotency check, the request and the stored response must be in one transaction so concurrent same-key requests behave. JSON numbers for quantities -> 400. Unknown path/object 404. Done check: `python3 -m unittest tests.unit_api 2>&1 | tail -5` (start the server in a thread/subprocess on a free port; include a concurrency test: parallel confirms of orders competing for the same stock never over-reserve).
