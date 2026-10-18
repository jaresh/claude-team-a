# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

- 2026-10-18 lead: fin/core.py ensure_schema now runs statements one by one with conn.execute (no implicit COMMIT); safe inside write commands.
- 2026-10-18 lead: fin/api.py _body: empty POST body is {} (POST /invoices/ID/issue sends none).
