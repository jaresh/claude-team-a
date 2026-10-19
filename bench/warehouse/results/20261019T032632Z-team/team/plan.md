# Plan: warehouse management system (wms/)

Goal: implement the spec in `.claude/team/spec.md` (the user's request, word for word). Lead already wrote the
core; teammates add command modules. Check for all: `python3 -m unittest discover -s tests -t .` (each task's own check
is listed below).

## Existing core (read before starting; do not rewrite, do not duplicate)
- `wms/app.py`: CLI parsing + `run()` (one SQLite transaction per command, rolls back on UserError, expires
  reservations first, role check). `wms/registry.py`: `@command('po receive', 'clerk', setup)` registers
  `handler(ctx, args) -> JSON-able result`; `setup(parser)` adds argparse args. Dest names must not be
  db/json/user/now/_cmd/_sub (use `dest='frm'` for `--from`, `dest='to'`...). Modules in `app.MODULES` are auto-imported.
  The registered role is the minimum role (see spec section 1). Handlers raise `wms.errors.UserError("message")` for any user error.
  Handlers return the exact JSON shapes of the spec (decimals as strings). Handlers must call `ctx.audit(action, target)` (spec section 13).
- `wms/db.py`: `SCHEMA` (all tables, already defined for every feature; read it), `Ctx` (`ctx.q/q1/x` SQL helpers,
  `ctx.now`, `ctx.today`, `ctx.user`, `ctx.audit`, `ctx.next_id('PO'|'SO'|'TR'|'RT')` -> 'PO-0001'). All quantity/money
  columns are TEXT holding `str(Decimal)`; read with `Decimal(x)`. Lot columns use `''` for "no lot" (print as null). Locations are stored as 'WH/LOC' text.
- `wms/util.py`: `parse_qty(s, unit)`, `parse_money(s, places)`, `round2/round4`, `fmt2/fmt4/fmt_qty(d, unit)`, `parse_time/parse_date`,
  `check_re`, `parse_serials`, `add_hours`. NEVER use float; never write your own rounding/formatting/validation.
- `wms/engine.py`: stock + costing + movements. Use ONLY these for any stock change: `post(ctx, type, p, qty, frm, to, lot, serials, ref, line, unit_cost, reason, unreserved, costfn)`
  (read its docstring), `do_receive`, `void_movement`, `stock_qty`, `reserved_qty`, `reserved_serials`, `serials_at`, `get_product/get_loc/get_warehouse`,
  `mv_json(ctx, row)`, `wh_state`, `fifo_slices`, `transfer_in_cost`, `transfer_back_cost`, `lot_expiry`. `movements.line` stores the order/PO line number for pick/ship/receive movements.
  `mv_wh(mv, sku, wh, qty_after, value_after)` holds a snapshot of the warehouse's qty/value of the product after each movement that changed it (use for `valuation --at`).
- `wms/status.py`: `so_status`, `so_line_qtys` (reserved, picked, shipped), `po_status`, `po_line_received`.
- `wms/stock.py`, `wms/admin.py`, `wms/catalog.py` (product add, warehouse add, location add, `add_product(ctx, ...)` validator), lead-owned.
- Tests: subclass `tests.helpers.Wms` (see `tests/test_core.py`; `self.basic()` sets up WH1 + A-01/A-02 + BOLT(each,fifo) + FLOUR(kg,average); `self.ok(...)`, `self.err(...)`).
  Test only through the CLI. Name test helpers carefully (never `fail`, `run`, `assert*`, `setUp`).
- Rules: follow the spec exactly (sorting, key names, rounding, error = UserError). Make every error case a UserError, never a traceback.
  Validate all input BEFORE changing anything is not required (the transaction rolls back), but never swallow errors. Match the style of existing modules.
- You may edit only your own files. If you find a bug in a lead-owned file, make the smallest fix and log one line in `.claude/team/changes.md`. Append a line to changes.md for any shared-file edit.
- Add unit/CLI tests in your own test file as you go; they must pass.

## Wave 1 tasks

## catalogue
Files: `wms/products.py` (keep `product_obj(ctx, sku)`; add `product show`, `product list [--search]`, `product edit` with --version check/bump, `import products FILE`), `wms/commerce.py` (`customer add/list`, `price set/list`, `promo add/list`), `tests/test_catalogue.py`; also `warehouse list`, `location list WH` in `wms/products.py`.
Spec sections 2, 3 (list commands), 7 (data and commands only, not pricing calculation), 12. Roles per spec section 1. Import uses `catalog.add_product` per row inside the same transaction; collect all row errors and raise one UserError whose message is `row 2: MSG` plus `\nerror: row 4: MSG` for later rows (main prints "error: " before the message); empty cells map to None. Audit: `product.add` already done; `product.edit`, `import` (target `products`), `customer.add`, `price.set` (`LIST/SKU`), `promo.add`. Print `price set`/`promo add`/`customer add` results as the corresponding list-item object.
Done: `python3 -m unittest tests.test_catalogue tests.test_core`
Do not touch: other modules.

## purchasing
Files: `wms/purchasing.py`, `tests/test_purchasing.py`. Spec section 6. `po receive` calls `engine.do_receive(..., type='receive', ref=PO id, line=N)` at the line's unit cost; location must be in the PO's warehouse; 5% overage rule (ordered*1.05 rounded down to the unit precision, based on received incl. this receipt); receiving on received/closed PO is an error; use `status.po_status/po_line_received`. `value_received` = sum of values of non-voided receipt movements of the PO (fmt2). Audit `po.create`, `po.receive` (target PO id), `po.close`. Lines `SKU:QTY:UNITCOST` validated (qty by product unit, cost <= 4 decimals); at least one line; warehouse must exist; po ids via `ctx.next_id('PO')`.
Done: `python3 -m unittest tests.test_purchasing tests.test_core`
Do not touch: other modules.

## pricing
Files: `wms/pricing.py`, `tests/test_pricing.py` (tests call the function directly with a Ctx on a temp DB: see `wms/app.py`/`db.py`; insert rows by SQL or via the CLI commands `price set`, `promo add`, `customer add` which exist after `catalogue` is done — so insert with SQL: tables `prices`, `promos`, `customers`; `min_qty`, `percent`, `unit_price`, `threshold` are Decimal strings; dates in `from_`/`to_`).
Spec section 7 (calculation: unit price selection, line promos, order promos, rounding). Contract:
`price_order(ctx, customer: str, lines: list[tuple[str, Decimal]], today: str) -> dict` returns
`{'lines': [{'unit_price','gross','discount','net'}...], 'subtotal','order_discount','total'}` all Decimal (unit_price unrounded as stored, up to 4 dp; gross/discount/net/subtotal/... already round2'd), in the same order as `lines`. Raises UserError if a line has no price (customer's list, then STANDARD). Promotions are valid when from_ <= today <= to_. Keep the module small and pure (no writes).
Done: `python3 -m unittest tests.test_pricing tests.test_core`
Do not touch: other modules.

## sales
Files: `wms/sales.py`, `tests/test_sales.py`. Spec section 8 except `stock`, `available` (reports does those); plus audit `so.*`. Commands: `so create/confirm/allocate/pick/ship/cancel/show/list`. Use `wms.pricing.price_order(ctx, customer, [(sku, qty)...], ctx.today) -> {'lines':[{'unit_price','gross','discount','net'}], 'subtotal','order_discount','total'}` (Decimals; written by teammate `pricing` in parallel — until it exists, test with a tiny stub in your test file's setup by inserting price rows... the real module will be there when you finish; if it is missing while you test, write the code against the contract and note it in your handoff). Store prices as `str(Decimal)` in `so_lines`/`so`. Reservations live in table `reservations` (one row per order line, location, lot, or per serial with qty '1'; `state` 'reserved' with `expires`, or 'picked' with loc = the SHIP location and expires NULL). Reserve only from `storage` locations of the order's warehouse, skipping lots expired before today, using available = stock − reserved (reserved_qty includes picked). Pick: `engine.post(ctx,'pick',p,qty,src,ship_loc,lot,serials,ref=so,line=line,unreserved=False)` one per SKU/source location/lot; ship: `post(ctx,'ship',p,qty,ship_loc,None,lot,serials,ref=so,line=line,unreserved=False)` one per line and lot, line order; update `so_lines.shipped`; delete picked rows. Status via `wms/status.py`. Hold hours 1..720 (default 48). Order state column: draft/confirmed/cancelled. `so create` lines `SKU:QTY`, customer and warehouse must exist, product units respected. Expired reservations are already released by app.run before your handler.
Done: `python3 -m unittest tests.test_sales tests.test_core`
Do not touch: other modules (pricing is another teammate's).

## reports
Files: `wms/reports.py`, `tests/test_reports.py`. Spec: `stock` and `available` (section 8), `valuation`, `aging` (section 5), `reorder` (section 11). `stock --at` replays movements with `at <= TIME` (qty delta −frm/+to, serials from movement serials JSON; ordered by id). Plain `stock` reads tables `stock`, `serials`, `reservations`. `valuation` current = `engine.wh_state`; `--at` = latest `mv_wh` snapshot per (sku, wh) among movements with at <= TIME; in-transit from table `transfers` (`value`, `out_mv`, `in_mv`; a transfer is in transit at TIME if its out movement is at/before TIME and its in/cancel movement is not; status `in_transit` now) — transfers are written by another teammate with columns as in db.py; test with rows inserted by SQL. `incoming`, `backordered` use `po`, `po_lines`, `so`, `so_lines`, `reservations` tables and `wms/status.py` helpers (`po_status`, `so_status`, `so_line_qtys`). `aging` uses the `layers` table (`at`, `remaining`, `unit_cost`) of fifo products. Unknown warehouse/SKU is a UserError. Tests: build data through CLI commands that exist (receive, move, scrap, adjust, movement void, po/so are by other teammates: insert po/so rows by SQL if needed).
Done: `python3 -m unittest tests.test_reports tests.test_core`
Do not touch: other modules.

## transfers
Files: `wms/transfers.py`, `tests/test_transfers.py`. Spec section 9, audit `transfer.create|receive|cancel` (target TR id). Use `engine.post` with `costfn=engine.transfer_in_cost(out_mv, value)` for `transfer receive` and `costfn=engine.transfer_back_cost(out_mv, value)` for `transfer cancel`; transfer-out via `post(ctx,'transfer-out',p,qty,frm,None,lot,serials,ref=TR id)`, which gives the value and (fifo) records the consumed slices. Rules: source `storage` location, destination `storage` or `receiving` of a different warehouse, unreserved stock only (post checks it), lot/serial rules via `engine.check_tracking_args/check_serial_count`. Table `transfers` (columns `out_mv`, `in_mv`, `serials` JSON, `value`, `status` in_transit/received/cancelled). Roles per spec section 1. Only `in_transit` transfers can be received/cancelled.
Done: `python3 -m unittest tests.test_transfers tests.test_core`
Do not touch: other modules.

## Wave 2 tasks (wave 1 is merged; all modules in wms/ now exist and pass `python3 -m unittest discover -s tests -t .`)

## returns
Files: `wms/returns.py`, `tests/test_returns.py`. Spec section 10 + audit `return.create` (target RT id). Shipped data: `ship` movements have `ref`=SO id, `line`=line number, lot, serials JSON, value, `voided_by` (ship cannot be voided). Update `so_lines.returned`. Good return: `engine.post(ctx,'return',p,qty,None,to_loc,lot,serials,ref=RT id,unit_cost=unit_cost)` (fifo: layer at return time; average: pool). Damaged: no movement, value "0.00", unit_cost still computed and printed. Unit cost = round4(sum of `ship` movement values of that line / line shipped qty). Credit = round2(QTY * net / qty of line). Lot returns: lot must be one shipped on that line (and qty <= shipped in that lot minus returned in that lot: track via earlier `returns` rows); serials: must be shipped on that line and not returned yet. `return list [--order SO]`, `return create` is role manager; list is viewer. Use sales' `wms.sales` code only if needed; read tables directly otherwise. For test setup use the CLI (po/receive, so create/confirm/pick/ship, price set, customer add).
Done: `python3 -m unittest tests.test_returns`

## server
Files: `wms/server.py`, `tests/test_server.py`. Spec section 14. `serve(args)` (called by app.main with parsed args: `args.db`, `args.port`) starts `ThreadingHTTPServer` on 127.0.0.1; register `@command('serve','viewer', setup adding --port int default 8080)` (handler unused). Each route builds a CLI argv and calls `wms.app.execute(db, user, now, argv)` (it is serialised by a lock and all-or-nothing); map UserError to 400, but check first: missing/unknown/disabled user -> 401 (look up the users table), role too low -> 403 (compare with `registry.COMMANDS[...].role`), unknown path/object -> 404 (unknown product/SO is a UserError whose message begins `unknown`; check existence directly for GET /products/SKU, /sales-orders/SO). Body values quantities/amounts/costs must be JSON strings else 400. Reuse the real commands for all semantic work: e.g. POST /receipts -> `receive SKU QTY --at AT --cost COST [--lot --expires --serial a,b]`; POST /sales-orders -> `so create` then return the `so show` object, 201; confirm -> `so confirm SO [--hold H]` (hold may be an int in JSON); GET /stock -> `stock`, GET /valuation -> `valuation`; GET /products list with `limit`, `after`, `search`, `next` (use `product list --search` then slice in Python); PATCH with If-Match (428 without, 412 on mismatch; else `product edit SKU --version N ...`; null clears min/max -> 'none'); ETag header `"N"`. Idempotency-Key on POST: table `idempotency(key,path,body,status,response)`; do the check+execute+store atomically under a process-wide lock using a separate sqlite connection (the table exists after init); same key + different path or body -> 409; store every status. Reservation-expiry/audit behaviour comes for free from execute. Tests start the server on a free port in a thread/subprocess, using urllib, including concurrent POST /sales-orders/SO/confirm requests competing for the same stock (never over-reserve) and idempotent replays.
Done: `python3 -m unittest tests.test_server`
