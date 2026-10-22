"""Opening the book and running one all-or-nothing command as a user."""
import sqlite3
from .core import Ctx, HttpError, ROLES, UserError
from .orders import expire_reservations


def connect(path):
    conn = sqlite3.connect(path, isolation_level=None, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def authorize(ctx, name, need):
    if not name:
        raise HttpError(401, "--user is needed")
    u = ctx.one("SELECT * FROM users WHERE name=?", name)
    if not u or not u["enabled"]:
        raise HttpError(401, f"unknown or disabled user {name}")
    if ROLES.index(u["role"]) < ROLES.index(need):
        raise HttpError(403, f"{name} may not do this")


def run(db, now, user, need, fn):
    """One all-or-nothing command: expire reservations, check the user, run fn(ctx)."""
    conn = connect(db)
    try:
        if not conn.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone():
            raise UserError("no book here: run init first")
        conn.execute("BEGIN IMMEDIATE")
        ctx = Ctx(conn, now, user)
        try:
            expire_reservations(ctx)
            authorize(ctx, user, need)
            out = fn(ctx)
            conn.execute("COMMIT")
            return out
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
