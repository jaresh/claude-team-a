# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

- 2026-10-21, setup, wms/core.py, SCHEMA (products, layers, orders CREATE statements): moved the trailing `-- comment` after `);` onto its own line so `split(";\n")` in cli.execute runs one statement per chunk. No SQL text changed.

