# Brief: catalog

From .claude/team/spec.md, word for word: Conventions; 1. Setup and users; 2. Products; 3. Warehouses and locations; 7. Customers, prices and promotions; 12. Import; 13. Audit.

## Conventions

- Python 3.12+, standard library only (sqlite3, decimal, http.server, unittest, ...). The package is `wms/`, run as `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`. Global options come before the command. `--db` defaults to `wms.db` in the current directory.
- `--now` sets the current time for the command, as `YYYY-MM-DDTHH:MM:SSZ` (UTC); without it, the real current time. Every time the system stores or prints is UTC in that format. "Today" is the date part of the current time. Dates are `YYYY-MM-DD`.
- With `--json`, a successful command prints exactly one JSON document on stdout, in the shapes below; without it, any readable text. Exit code 0.
- A user error (bad input, a broken rule, an unknown object, a missing permission) prints a message starting with `error: ` on stderr, nothing on stdout, exits with code 2, and changes nothing at all: every command is all-or-nothing.
- Every command except `init` needs `--user NAME`, naming an existing, enabled user whose role allows the command (section 1). Otherwise it is a user error.
- Quantities follow the product's unit: `each` takes whole numbers, `kg` up to 3 decimals. More decimals, a non-number, or zero or less where a quantity is needed is a user error. Quantities print as strings: `each` as an integer (`"12"`), `kg` with exactly 3 decimals (`"1.250"`).
- Money is in the book's currency. Amounts print as strings with exactly 2 decimals (`"12.30"`); unit costs and unit prices are accepted with up to 4 decimals and print with exactly 4 (`"1.2500"`). Never use binary floating point for money or quantities. All rounding is half up: round2 rounds to 2 decimals, round4 to 4.
- Lists in JSON output are sorted as stated; where nothing is stated, by id or code, ascending.
- Ids are assigned in order of creation: movements are integers from 1; documents are `PO-0001`, `SO-0001`, `TR-0001` and `RT-0001`, with a separate counter per kind.

## 1. Setup and users

- `init --currency CUR --admin NAME` creates the book. CUR is 3 uppercase letters; NAME becomes the first user, with role `admin`. A second `init` on the same database is a user error. `init` needs no `--user`.
- User names are 1 to 32 characters from `a-z`, `0-9`, `.`, `_` and `-`. Roles, from least to most: `viewer`, `clerk`, `manager`, `admin`. Each role may do everything the roles below it may:
  - viewer: every command that only reads (lists, shows, reports).
  - clerk: `receive`, `move`, `adjust`, `scrap`, `po receive`, `so pick`, `so ship`, `transfer create`, `transfer receive`.
  - manager: `product add`, `product edit`, `import products`, `warehouse add`, `location add`, `customer add`, `price set`, `promo add`, `po create`, `po close`, `so create`, `so confirm`, `so allocate`, `so cancel`, `transfer cancel`, `return create`, `movement void`.
  - admin: `user add`, `user role`, `user disable`.
- `user add NAME --role ROLE`; `user role NAME ROLE` changes a role; `user disable NAME`. `user list` → `[{"name": "alice", "role": "admin", "enabled": true}, ...]`, sorted by name. A duplicate name, an unknown role, or an unknown user is a user error. Lowering the role of, or disabling, the last enabled admin is a user error.

## 2. Products

- `product add SKU --name TEXT [--unit each|kg] [--tracking none|lot|serial] [--costing fifo|average] [--min QTY] [--max QTY]`. Defaults: `each`, `none`, `fifo`, no minimum, no maximum. A SKU is 3 to 20 characters from `A-Z`, `0-9` and `-`, starts with a letter, and is unique. `serial` tracking needs unit `each`. The name is 1 to 100 characters once surrounding spaces are removed (they are). When both are given, max must be at least min.
- `product show SKU` → `{"sku": "BOLT-M8", "name": "Bolt M8", "unit": "each", "tracking": "none", "costing": "fifo", "min": "100", "max": "500", "version": 1}`; `min` and `max` are null when unset.
- `product list [--search TEXT]` → a list of those objects, sorted by SKU. `--search` keeps products whose SKU or name contains TEXT, ignoring case.
- `product edit SKU --version N [--name TEXT] [--min QTY|none] [--max QTY|none]`. N must equal the product's current version, otherwise it is a user error (someone changed the product in between). A successful edit adds 1 to the version. `none` clears the minimum or maximum. The min/max rule above holds after the edit. Unit, tracking and costing never change.

## 3. Warehouses and locations

- `warehouse add CODE --name TEXT`. CODE is 2 to 6 characters from `A-Z` and `0-9`, unique. Each new warehouse gets two locations: `RECV` (type `receiving`) and `SHIP` (type `shipping`).
- `location add WH/LOC [--type storage|receiving]` (default `storage`). LOC is 1 to 20 characters from `A-Z`, `0-9` and `-`, unique within its warehouse. Everywhere, a location is written `WH/LOC`.
- `warehouse list` → `[{"code": "WH1", "name": "Main"}, ...]`. `location list WH` → `[{"location": "WH1/A-01", "type": "storage"}, ...]`, sorted by location.

## 7. Customers, prices and promotions

- `customer add NAME [--price-list LIST]` (NAME 1 to 60 characters, unique); `customer list` → `[{"name": "Bistro", "price_list": "TRADE"}, ...]`, `price_list` null when unset.
- `price set LIST SKU UNITPRICE [--min-qty QTY]` sets a unit price in a price list (LIST is 1 to 10 characters from `A-Z` and `0-9`) for line quantities of at least QTY (default 0). Setting the same list, SKU and minimum quantity again replaces the price. `price list [--list LIST]` → `[{"list": "STANDARD", "sku": "BOLT-M8", "min_qty": "0", "unit_price": "0.2500"}, ...]`, sorted by list, SKU, then minimum quantity.
- A line's unit price is the price with the highest minimum quantity at most the line's quantity, from the customer's price list; if that list has no such price for the SKU, from the list `STANDARD`; with neither, confirming the order is a user error.
- `promo add CODE --sku SKU --percent P --from DATE --to DATE` adds a line promotion; `promo add CODE --order --threshold AMOUNT --percent P --from DATE --to DATE` adds an order promotion. CODE is unique, 1 to 20 characters from `A-Z`, `0-9` and `-`; P is more than 0 and at most 100, with up to 2 decimals; the dates are inclusive and from ≤ to. `promo list` → `[{"code": "SPRING", "kind": "line", "sku": "BOLT-M8", "threshold": null, "percent": "10.00", "from": "2026-03-01", "to": "2026-03-31"}, ...]` (`kind` `line` or `order`; `sku` null for order promotions, `threshold` null for line ones).
- Pricing happens when an order is first confirmed, with promotions valid on that day. For each line: `gross` = round2(qty × unit price); `discount` = round2(gross × P / 100) with P the largest percent among the line promotions for its SKU, or 0; `net` = gross − discount. Then `subtotal` = the sum of the nets; `order_discount` = round2(subtotal × P / 100) with P the largest percent among order promotions whose threshold is at most the subtotal, or 0; `total` = subtotal − order_discount. Prices never change after the first confirmation.

## 12. Import

- `import products FILE` reads a CSV file whose header is exactly `sku,name,unit,tracking,costing,min,max`. Empty `unit`, `tracking` or `costing` cells take the defaults; empty `min` or `max` cells leave them unset. Every row is checked by the rules of `product add`, and a SKU may appear only once in the file. If any row breaks a rule, nothing is imported, and stderr has one line per bad row, `error: row N: MESSAGE`, where N is the row's line number in the file (the header is line 1); exit code 2. Otherwise → `{"imported": 3}`.

## 13. Audit

- Every successful command that changes data appends one audit entry (plus `reservation.expire` entries, section 8). `audit list [--action ACTION] [--user NAME]` → `[{"seq": 1, "at": "2026-03-01T08:00:00Z", "user": "alice", "action": "init", "target": "EUR"}, ...]`, oldest first, with exactly those keys. Actions and targets: `init` (the currency), `user.add`, `user.role`, `user.disable` (the name), `product.add`, `product.edit` (the SKU), `import` (`products`), `warehouse.add` (the code), `location.add` (`WH/LOC`), `customer.add` (the name), `price.set` (`LIST/SKU`), `promo.add` (the code), `receive`, `move`, `adjust`, `scrap` (the movement id, as a string), `movement.void` (the id of the voided movement, as a string), `po.create`, `po.receive`, `po.close`, `so.create`, `so.confirm`, `so.allocate`, `so.pick`, `so.ship`, `so.cancel`, `transfer.create`, `transfer.receive`, `transfer.cancel`, `return.create` (the document id).
Your files: see section 'catalog' of .claude/team/plan.md. Also read wms/core.py, wms/cli.py and the Contract in plan.md.
