# wms — inventory and order management

Python 3.12+, standard library only. Run `python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...`.
Tests: `python3 -m unittest discover -s tests -t .`

Layout: `wms/app.py` (CLI, one SQLite transaction per command), `engine.py` (stock, movements, costing),
`registry.py` (command table), modules per area (`stock`, `catalog`, `products`, `commerce`, `purchasing`,
`pricing`, `sales`, `transfers`, `returns`, `reports`, `admin`, `server`).

## Assumptions
- Without `--json`, output is the same JSON, indented.
- Quantities/money are stored as decimal strings in SQLite; all arithmetic uses `Decimal`.
- `product add` accepts min/max of zero; `15.0` is accepted for `each` (value is whole).
- Untracked products reject `--lot`/`--serial`; lot-tracked reject `--serial`; serial-tracked reject `--lot`.
- `adjust` works at any location; reason must be non-blank. Disabling an already disabled user is an error.
- Supplier names: any non-blank text. Customer/price/promo rules as in the spec.
- Valuation/stock `--at` order movements by id among those with `at <= TIME`.
- Movement ids, document counters never reuse numbers (a failed command rolls back its counter too).
- HTTP: one process-wide lock serialises requests; each request is one transaction.
