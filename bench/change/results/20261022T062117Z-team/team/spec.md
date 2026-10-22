# The user's request, word for word (their messages in this session, oldest first)

You are working in an existing repository: a warehouse system (`wms/`, specified in `docs/SPEC.md`, see `README.md`). It is in use, and three things need doing. Work with team on it.

Keep every existing behaviour as it is. Add or update tests for what you change, and keep the existing tests passing. No one will answer questions while you work: where something below is not specified, decide, and list your assumptions in `CHANGES.md`. Update `docs/SPEC.md` for what you add. When everything is done, write the current UTC time (`date -u +%FT%TZ`) to a file named `.bench-end` in the repository root. That must be your last action.

## 1. Bug report

"`valuation --at TIME` and `stock --at TIME` leave out a movement made exactly at TIME. Per the spec, `--at` gives the state right after the last movement at or before TIME. We noticed it when a month-end valuation at 2026-03-31T23:59:59Z missed a receipt booked at that second."

Find the cause and fix it, for every report it affects.

## 2. Feature: archiving products

Products that are no longer sold should be archived, so they stop showing up and nobody books them by mistake.

- `product archive SKU` and `product unarchive SKU` (role manager). Both return the product object. Each adds 1 to the product's version, and each is a user error when the product is unknown (not found), already in that state, or (archive only) when the product still has stock anywhere in any warehouse, location or lot (including stock in transit between warehouses), is on a purchase order that is still `open` or `partial`, or is on a sales order that is neither `shipped` nor `cancelled`.
- An archived product's object has `"archived": true`; for a product that is not archived the object has no `archived` key at all, so every existing output stays exactly as it is.
- `product list` leaves archived products out; `product list --archived` lists only archived products (`--search` applies to both).
- Nothing new can be booked on an archived product: `receive`, `adjust`, `po create` (any line), `so create` (any line), `price set`, `promo add --sku`, `return create`, and `product edit` are user errors for it, and change nothing. Everything that only reads, and the history (movements, valuation `--at`, audit), stays as it is. `reorder` leaves archived products out.
- Audit actions `product.archive` and `product.unarchive`, the target is the SKU.
- HTTP API: `POST /products/SKU/archive` and `POST /products/SKU/unarchive` (role manager) → 200 and the product object; user errors are 400, an unknown SKU is 404. `GET /products?archived=1` lists only archived products. A `PATCH` of an archived product is a 400.

## 3. Feature: customer credit limits

- `customer add NAME [--price-list LIST] [--credit-limit AMOUNT]` and a new `customer limit NAME AMOUNT|none` (role manager) set or clear a customer's credit limit. AMOUNT is more than 0, with up to 2 decimals; it prints with exactly 2. Both return the customer object, `customer list` shows it too, and an unknown customer is not found (a user error); bad amounts are user errors. A customer's object has a `"credit_limit"` key only when a limit is set, so every existing output stays exactly as it is.
- `so confirm` is a user error, and changes nothing, when the order's total plus the totals of the customer's other orders that are confirmed and not yet fully shipped (`confirmed`, `backordered` or `partially_shipped`; cancelled and shipped orders don't count) is more than the limit. Exactly the limit is allowed. Customers without a limit are unaffected.
- Audit action `customer.limit` (the target is the customer's name) for `customer limit`.
