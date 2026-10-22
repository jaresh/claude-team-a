# wms

Inventory and order management: a command-line tool and an HTTP API over one SQLite book.

    python3 -m wms [--db PATH] [--json] [--user NAME] [--now TIME] COMMAND ...
    python3 -m wms --db wms.db serve --port 8080
    python3 -m unittest discover -s tests

The behaviour is specified in `docs/SPEC.md`; code is in `wms/app.py`. Changes keep the existing
behaviour, and update `docs/SPEC.md` and the tests with the code.
