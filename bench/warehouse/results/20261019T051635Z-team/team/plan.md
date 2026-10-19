# Plan
**Goal**: inventory & order management system `wms/` per `.claude/team/spec.md` (the user's full spec; READ the sections for your task
carefully, every number format and rule matters). Python 3.12+, stdlib only.
**Check**: `python3 -m unittest discover -s tests -t . 2>&1 | tail -15` (all tests, incl. teammates' own unit tests in `tests/test_<task>.py`).

## Foundation (written by lead, DO NOT EDIT; report needed changes in your handoff)
- `wms/util.py`: UserError/NotFound/Unauthorized/Forbidden, parse_qty/fmt_qty/parse_money/round2/round4/fmt2/fmt4/floor_to, D (Decimal),
  check_name/check_text, regexes (SKU_RE, WH_RE, LOC_RE, LOT_RE, USER_RE), split_loc, split_serials, parse_date/parse_time, add_hours.
  ALL validation/rounding/formatting goes through it. Never use float.
- `wms/core.py`: SCHEMA (read it: it is the data contract; tables are fixed, all numbers stored as TEXT decimals), `Command(role, setup, run)`,
  `Ctx` (ctx.db sqlite3 with row_factory Row, ctx.user, ctx.now, ctx.today, ctx.product(sku), ctx.warehouse(code), ctx.location("WH/LOC"),
  ctx.audit(action,target), ctx.next_id('po'|'so'|'tr'|'rt'), ctx.currency()), `run_command(db, user, now, argv)`, `main`.
  Transactions, role check, reservation expiry and exit codes are handled by core: a command just does its work with ctx.db and RETURNS the
  JSON-able result, or raises UserError (everything is rolled back). Never commit/rollback yourself. Check ALL validation before writing
  where convenient, but rollback makes partial writes safe.
- Commands: each module `wms/commands/<name>.py` defines `COMMANDS = {"product add": Command("manager", setup, run), ...}` (key = the words of the
  command; role = minimum role from spec section 1; `setup(parser)` adds argparse args; `run(ctx, args)`). Auto-discovered; no registration elsewhere.
  Options absent -> None. Use `action="append"` for `--line`. Output keys exactly as in the spec.
- `tests/helpers.py`: `WmsCase` (self.ok / self.bad / self.run_cli / self.bootstrap()). Tests use it; each test class in `tests/test_<task>.py`.
- Audit: every data-changing command calls `ctx.audit(action, target)` exactly once (spec section 13).
- Don't name test helpers like unittest methods (fail, run, setUp, assert*...).

## Stock API (module `wms/stock.py`, owned by task `stock`; later tasks import these exact functions)
Quantities/costs are Decimal; `p` is the product Row (ctx.product(sku)); locations are "WH/LOC" strings; lot is str or None; serials list[str].
Every function writes the movement (+ stock, serials, lots, layers/avg_state) and returns the movement dict in spec JSON shape (via `movement_dict(row)`),
and raises UserError for rule violations.
- `receive_stock(ctx, p, qty, at, unit_cost, lot=None, expires=None, serials=(), ref=None, mtype="receive")` (mtype "return" for good returns; full receive validation).
- `move_stock(ctx, p, qty, frm, to, lot=None, serials=(), mtype="move", ref=None, check_reserved=True)` (pick uses mtype="pick", check_reserved=False, to=SHIP; the SHIP-destination ban applies only when mtype=="move").
- `issue_stock(ctx, p, qty, frm, mtype, lot=None, serials=(), ref=None, check_reserved=True, reason=None)` stock leaving the book (scrap/ship/adjust-down) with costing; ship passes check_reserved=False.
- `transfer_out(ctx, p, qty, frm, lot=None, serials=(), ref=None)` -> movement (type transfer-out, slices recorded in layer_use for fifo);
  `transfer_in(ctx, out_movement_id, to, ref, mtype="transfer-in")` -> movement: brings the transfer-out's stock+value into location `to` (destination warehouse for receive; source for cancel), per spec section 9.
- `onhand(ctx, sku, loc, lot="")`, `reserved_qty(ctx, sku, loc, lot="")` (sum of reservations rows incl. picked), `movement_dict(row)`.
- Linking documents: callers insert `doc_moves(doc,line,mv)` themselves after the call.
- The `reservations` table (owned by task `sales`) is created empty at init; `stock` only reads it.

## Waves
1. `catalog`, `stock` (parallel)  2. `po`, `sales`, `xfer` (parallel)  3. `serve`

## catalog
Files: `wms/commands/users.py`, `products.py`, `warehouses.py` (warehouse+location), `customers.py` (customer, price, promo), `imports.py` (import products), `audit.py`; tests `tests/test_catalog.py`.
Spec sections 1, 2, 3, 7 (only the data commands; NOT pricing at confirm time: expose `price_for(ctx, customer_row, sku, qty) -> Decimal|None` and `promo_percent(ctx, sku, day)`/`order_promo_percent(ctx, subtotal, day)` helper functions in `wms/commands/customers.py` for task sales), 12, 13 (`audit list`; viewer).
Also `product show/list` shape and `product_dict(row)` helper in products.py. Import: share validation with `product add` (one function). `import products` reads FILE with csv module; one error line per bad row `row N: MESSAGE` — core prints one `error: ` line, so raise a UserError whose message is the lines joined as "row 2: msg\nerror: row 3: msg" (first line prefixed by core).
May change: only your files. Must not touch: foundation, other modules.
Done: `python3 -m unittest tests.test_catalog 2>&1 | tail -5`

## stock
Files: `wms/stock.py`, `wms/commands/stockcmds.py` (receive, move, adjust, scrap, movement list, movement void, stock, valuation, aging); tests `tests/test_stock.py`.
Spec sections 4 and 5 (plus the `stock`/`valuation`/`aging` commands from 8/5; `available`/reserved logic NOT yours except `stock` command reading `reservations`). Implement the Stock API above exactly. Notes: costing per warehouse (fifo layers in `layers`/`layer_use`, average in `avg_state`); `valuation --at` / `stock --at`: replay from movements/layers (layer remaining at time T = qty minus signed layer_use of movements with id <= last movement id at/before T). Void must restore the very layers consumed (negative layer_use rows). Movement `value` for move/pick "0.00". Audit actions receive/move/adjust/scrap = movement id string; movement.void = voided id. Because other tasks call your functions, the audit call is made by the COMMAND, not by stock.py functions.
Tests: write also a few multi-step fifo/average examples by hand-computation.
May change: only your files. Done: `python3 -m unittest tests.test_stock 2>&1 | tail -5`

## po
Files: `wms/commands/po.py`, `tests/test_po.py`. Spec section 6. Use `stock.receive_stock` + `doc_moves(doc=PO id,line,mv)`; received per line = receipts whose movement is not voided (`movements.voided_by IS NULL`). Provide `po_dict(ctx, po_id)`; also helper `incoming(ctx, wh, sku)` (open qty on the warehouse's POs; closed -> 0) for tasks sales/xfer. Audit: po.create/po.receive/po.close.
May change only your files. Done: `python3 -m unittest tests.test_po 2>&1 | tail -5`

## sales
Files: `wms/commands/sales.py` (so create/confirm/allocate/pick/ship/cancel/show/list, available), `wms/reserve.py`, `tests/test_sales.py`. Spec sections 7 (pricing at confirm, using catalog helpers from `wms/commands/customers.py`: price_for, promo_percent, order_promo_percent — written in wave 1), 8 (not `stock`, done by stock). Status derived from reservations/line quantities; shipped quantity via doc_moves(doc=SO id, line, mv) for `ship` movements; returned quantity from `returns` table (not shown in status). `incoming` via `wms.commands.po.incoming`. Provide `backordered(ctx, wh, sku)` and `available_qty(ctx, wh, sku)` helpers in `wms/reserve.py` for task xfer's reorder. Pick uses `stock.move_stock(..., mtype="pick", ref=SO, check_reserved=False)`; ship uses `stock.issue_stock(..., mtype="ship", check_reserved=False)`. Reservation rows: one per (line, loc, lot, serial); `picked=1` rows have loc = the SHIP location. Reservation expiry is already done by core.
May change only your files. Done: `python3 -m unittest tests.test_sales 2>&1 | tail -5`

## xfer
Files: `wms/commands/xfer.py` (transfer create/receive/cancel/show/list; return create/list; reorder), `tests/test_xfer.py`. Spec sections 9, 10, 11. Use stock.transfer_out/transfer_in; return uses `stock.receive_stock(mtype="return")`; line shipped values from `doc_moves` + movements of type ship; reorder uses `wms.reserve.available_qty/backordered` and `wms.commands.po.incoming`. Audit as spec 13.
May change only your files. Done: `python3 -m unittest tests.test_xfer 2>&1 | tail -5`

## serve
Files: `wms/http_api.py` exposing `serve(db_path, port)` (blocks until stopped; lead already wired `serve [--port N]` in core.main, do not edit core), `tests/test_http.py` (start the server in a thread on port 0 / a free port; add `make_server(db_path, port)` returning the ThreadingHTTPServer for tests). Also include a concurrency test (parallel receipts + confirms never over-reserve).
May change only your files. Done: `python3 -m unittest tests.test_http 2>&1 | tail -5`
