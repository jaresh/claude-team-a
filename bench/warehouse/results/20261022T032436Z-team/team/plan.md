# Plan: WMS (inventory + order management), Python 3.12+ stdlib only

Full user spec: `.claude/team/spec.md` (read the sections named in your task; it is the authority).
**Check** (whole project): `python3 -m unittest discover -s tests -t .` ; task check = your own test file(s) + whatever of `tests/test_acceptance.py` your task covers.
Acceptance tests `tests/test_acceptance.py`, `tests/helpers.py` are the lead's: never edit them. Add your own `tests/test_<task>.py` (use `tests.helpers.Base`/`Wms`).

## Architecture / Conventions (already written, READ `wms/core.py` and `wms/cli.py` first, ~250 lines)
- `wms/core.py` is shared: `UserError`, `round2/round4/fmt2/fmt4/fmt_qty`, `parse_qty/parse_money/parse_time/parse_date/check_re/check_lot/parse_serials`, core DDL (tables: meta users audit products warehouses locations movements lots reservations counters), `Ctx` (`ctx.conn, ctx.now, ctx.today, ctx.user, ctx.audit(action,target), ctx.next_id('PO')`), `get_product/get_warehouse/parse_loc/wh_of/lot_expiry`, `insert_movement/movement_json`, `reserved_qty/reserved_serials`, `command(path, role, args)` decorator, `schema(ddl)` for module tables, `PRE_HOOKS`. Never write your own version of these. If you need a change in core.py, append one line to `.claude/team/changes.md` and make the minimal edit.
- Each module `wms/<name>.py` registers commands with `@core.command('product add', 'manager', [(('sku',),{}), (('--name',),{'required':True}), (('--line',),{'action':'append'})])`; the handler is `fn(ctx, a)` and returns the JSON-able result (dict/list). `a` is an argparse Namespace; all values are STRINGS (or lists for append), handlers validate them. Argument dest = longest name without `--`, `-`→`_`. Role = minimum role from spec §1. Options not given are None. Module tables: `core.schema("CREATE TABLE IF NOT EXISTS ...")` at import.
- Money/qty: Decimal everywhere, stored in sqlite as TEXT (`str(Decimal)`), never float. Formats via `fmt2/fmt4/fmt_qty(qty, product['unit'])`.
- Errors: `raise core.UserError("message")`. Everything runs in one transaction (core.execute) that is rolled back on error, so validate-then-write or just raise anywhere. Never print in handlers. Multi-line user errors: message lines joined by `\nerror: ` (only the importer needs this).
- Every command that changes data calls `ctx.audit(action, target)` exactly once (spec §13 names actions/targets).
- Lists: sorted as the spec says, otherwise by id/code. JSON key names exactly as spec examples.
- Test with `Wms().ok(...)/err(...)` (in-process). Don't name helpers like unittest methods (`fail`, `assert*`, `run`, `setUp`).

## Module contracts (signatures others rely on; `p` = product row, `wh` = warehouse code, qty/cost/value = Decimal unless "str")
**costing.py** (spec §5). Per (sku, wh) cost state, written by these calls; `mv` = id of the already-inserted movement. Tables are costing's own (layers: id, sku, wh, origin_mv, at, orig_qty, rem_qty, unit_cost, created_mv; consumption log per taking movement: mv, layer id, qty, unit_cost; average state Q,V,last_avg; snapshot table `cost_snap(mv, sku, wh, qty, value)` written after every call below, used for `valuation --at`).
- `add_in(ctx, p, wh, mv, qty, unit_cost) -> value` receipt/return: fifo new layer (time ctx.now, origin_mv=mv); avg V+=round2(q*c), Q+=q. value = round2(qty*unit_cost).
- `adjust_in(ctx, p, wh, mv, qty) -> (unit_cost, value)` increasing adjust (fifo: newest layer ever's cost; avg: current A or last A); UserError if none ever.
- `take_out(ctx, p, wh, mv, qty) -> value` stock leaving the warehouse (ship, scrap, decreasing adjust, transfer-out); logs consumed slices under `mv`.
- `restore(ctx, p, wh, taken_mv, mv, qty, value)` puts back exactly what movement `taken_mv` took (fifo: into the very layers; avg: V+=value, Q+=qty). Used by void of a decrease and by transfer cancel.
- `transfer_in(ctx, p, wh, taken_mv, mv, qty, value)` destination of a transfer: fifo new layers copying each consumed slice's unit cost, time and origin_mv; avg V+=value,Q+=qty.
- `undo_in(ctx, p, wh, orig_mv, mv)` void of a receipt / increasing adjust: remove its layer / value (UserErrors per spec §4 last bullet); `orig_mv` movement's value and qty are read from `movements`.
- Commands `valuation`, `aging` (viewer). `valuation_rows(conn, at=None)` helper may be exposed.
**inventory.py** (spec §4; owns `receive move adjust scrap movement list movement void stock available?` NO: `available` belongs to orders). Stock is derived from `movements` (replay; `--at` = movements with `at <= T`, in id order; voids are movements). A movement's `value` is set by calling costing after insert (insert with 0 then `UPDATE movements SET value`).
- `stock_map(conn, at=None) -> {(sku, loc, lot_or_None): {"qty": Decimal, "serials": [sorted]}}` only qty>0.
- `on_hand(conn, sku, loc, lot=None) -> Decimal`.
- `receive(ctx, sku, qty_str, loc, cost_str, lot, expires, serial_str, ref=None, only_wh=None) -> movement dict` (full `receive` validation, ref e.g. PO id; `only_wh` restricts to that warehouse code; registers lot expiry in `lots`).
- Internal movers, all Decimal/list args, return `movement_json` dict, check stock sufficiency (not reservations, caller decides): `pick(ctx, sku, qty, frm_loc, lot, serials, ref)` (to WH/SHIP, value 0), `ship(ctx, sku, qty, wh, lot, serials, ref)` (from WH/SHIP, `to` None, valued), `transfer_out(ctx, sku, qty, frm_loc, lot, serials, ref)` (also checks unreserved), `transfer_in(ctx, sku, qty, to_loc, lot, serials, out_mv, ref, cancel=False)` (cancel=True → costing.restore, into the source loc), `return_in(ctx, sku, qty, to_loc, lot, serials, unit_cost, ref)`.
- The `ship` movement and the lot/serials it shipped must be findable: orders records them in its own `ship_log`.
**sales_catalog.py** (§7): `price_lines(ctx, customer, lines) -> {"lines": [{"unit_price","gross","discount","net"} Decimals per input line], "subtotal","order_discount","total"}`; `lines` = `[(sku, qty Decimal)]`, `customer` a name; UserError when no price. Uses `ctx.today` for promos.
**purchasing.py** (§6): tables po, po_lines; `incoming_qty(conn, wh, sku) -> Decimal` (sum of `open` over the warehouse's POs).
**orders.py** (§8): tables `orders(id, customer, warehouse, status stored? compute it, hold, expires?, subtotal, order_discount, total, priced)`, `order_lines(order_id, line, sku, qty, unit_price, gross, discount, net, shipped, returned)`, `ship_log(order_id, line, mv, qty, lot, serials)`, `returned_serials(order_id, line, serial)`. Registers the reservation-expiry `core.PRE_HOOKS` entry. Commands: `so *`, `available`, `reorder` (§11). Uses `reservations` table of core (state 'reserved'/'picked', one row per sku/loc/lot, or per serial with qty 1).
**transfers.py** (§9), **returns.py** (§10), **users.py** (§1 + `audit list` §13 + `init`), **catalog.py** (§2, §3), **importer.py** (§12), **http_api.py** (§14, registers `serve`; calls `core.execute` with `core.make_args(core.COMMANDS[path], {...})` under `core.lock()` on a connection per request).

## Rules (spec §; copy-check in review)
- Exit 2 + `error: ` on stderr + nothing on stdout for any user error; all-or-nothing (§Conventions).
- Role per command exactly as §1 (viewer reads, clerk ops, manager setup/creation/cancel/void, admin users).
- Quantities by unit (each whole, kg ≤3 dec), >0 where a quantity is needed; printed `each` int string, `kg` 3 decimals. Money amounts 2 dec, unit costs/prices 4 dec on output, input ≤4 dec. Half-up rounding.
- Ids: movements 1.., `PO-0001` `SO-` `TR-` `RT-` separate counters. Lists sorted as stated (§ each command), else by id/code.
- Audit: exactly one entry per data-changing command with §13 target; `reservation.expire` entries by user `system`.
- Stock never below zero; reserved/picked stock cannot be moved/scrapped/transferred/adjusted below reserved.
- Product SKU `[A-Z][A-Z0-9-]{2,19}`; name 1–100 stripped; serial needs unit each; max ≥ min.
- Dates `YYYY-MM-DD`, times `YYYY-MM-DDTHH:MM:SSZ`; "today" = date part of ctx.now.

## Tasks (waves). Each teammate: own files only; tests `tests/test_<task>.py`.
### users  (wave 1)
Files: `wms/users.py`, `tests/test_users.py`. Spec §1, §13 (`init`, `user add|role|disable|list`, `audit list`). `init` is registered with role `viewer` (not checked; core skips user check for it); it sets meta currency, creates the admin, audits `init` with user = admin name. Lowering/disabling the last enabled admin is an error. Disabled users can't act. User name rule `[a-z0-9._-]{1,32}`. Done: `python3 -m unittest tests.test_users tests.test_acceptance.Users`.
### catalog  (wave 1)
Files: `wms/catalog.py`, `wms/importer.py`, `tests/test_catalog.py`. Spec §2, §3, §12. Expose `validate_product(fields: dict, errors context) -> row dict` used by both `product add` and import (import reports `error: row N: MSG` one line per bad row, N = file line number, header line 1, all bad rows reported; raise one UserError with lines joined by `\nerror: ` after the first). Warehouse add also creates RECV (receiving) and SHIP (shipping). Done: `python3 -m unittest tests.test_catalog tests.test_acceptance.Users tests.test_acceptance.PoImport.test_import` (the acceptance Users test needs the users task too; run only what passes by your code).
### costing  (wave 1)
Files: `wms/costing.py`, `tests/test_costing.py`. Spec §5 and the costing parts of §4 (void). Implement the contract above exactly; unit tests may create products/warehouses by inserting rows directly via `core.open_db` + SQL and calling functions with a `core.Ctx`. `valuation` and `aging` commands per §5 (valuation: rows from latest `cost_snap` per (sku, wh) with movement `at` ≤ --at and qty>0; in_transit = transfers (table `transfers` from transfers.py: columns id, sku, qty, from_loc, to_loc, lot, serials, status, value, out_mv, in_mv) with status in_transit — at the time of `--at` use movements: out_mv ≤ last mv and not yet in/cancelled by then; guard with try if the table doesn't exist yet). Done: `python3 -m unittest tests.test_costing`.
### sales_catalog  (wave 1)
Files: `wms/sales_catalog.py`, `tests/test_sales_catalog.py`. Spec §7 (`customer add|list`, `price set|list`, `promo add|list`, `price_lines`). Done: `python3 -m unittest tests.test_sales_catalog`.
### inventory  (wave 2, after costing, catalog, users)
Files: `wms/inventory.py`, `tests/test_inventory.py`. Spec §4 whole + `stock` command (§8; `reserved` = `core.reserved_qty`; `--at` rows have no reserved/available). Void rules per §4 (uses costing.undo_in/restore/take_out/add_in; void of a move/adjust/scrap/receive; mark original `voided=1`; void movement `ref` "MV-<id>", same value; reversal may not leave stock < 0 or < reserved). Lots: expired-before-today lots only matter to orders. Done: `python3 -m unittest tests.test_inventory tests.test_acceptance.Costing`.
### purchasing  (wave 3)
Files: `wms/purchasing.py`, `tests/test_purchasing.py`. Spec §6. Uses `inventory.receive(..., ref=po, only_wh=po warehouse)`. Received qty per line = sum of qty of non-voided `receive` movements with ref=PO and matching line: store line in a `po_receipts(po, line, mv)` table. Cap = floor(ordered*1.05 to unit precision). Done: `python3 -m unittest tests.test_purchasing tests.test_acceptance.PoImport`.
### transfers  (wave 3)
Files: `wms/transfers.py`, `tests/test_transfers.py`. Spec §9; table `transfers` with the columns named in the costing task. Uses inventory.transfer_out/transfer_in. Done: `python3 -m unittest tests.test_transfers tests.test_acceptance.Transfers`.
### orders  (wave 3)
Files: `wms/orders.py`, `tests/test_orders.py`. Spec §8 (all of it, incl. expiry hook, `available`, order status derivation) and §11 `reorder`. Uses sales_catalog.price_lines, inventory.pick/ship, purchasing.incoming_qty (import lazily inside functions). Done: `python3 -m unittest tests.test_orders tests.test_acceptance.Orders.test_expiry_and_backorder`.
### returns  (wave 4)
Files: `wms/returns.py`, `tests/test_returns.py`. Spec §10; reads `wms/orders.py` tables. Uses inventory.return_in. Done: `python3 -m unittest tests.test_returns tests.test_acceptance.Orders`.
### http_api  (wave 4)
Files: `wms/http_api.py`, `tests/test_http.py`. Spec §14. `http.server.ThreadingHTTPServer` on 127.0.0.1, one global `core.lock()` around each request's connection+execute; start the server in a thread in tests on port 0. Idempotency table (key, path, body, status, response). Map JSON body → string args (a JSON number for a qty/amount → 400). Done: `python3 -m unittest tests.test_http`.
