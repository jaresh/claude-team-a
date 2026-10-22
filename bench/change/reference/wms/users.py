"""Users and roles."""
import re
from .core import Ctx, NotFound, ROLES, SCHEMA, UserError


def valid_name(name):
    if not re.fullmatch(r"[a-z0-9._-]{1,32}", name or ""):
        raise UserError(f"bad user name {name!r}")


def init(conn, now, currency, admin):
    if conn.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone():
        raise UserError("the book already exists")
    if not re.fullmatch(r"[A-Z]{3}", currency or ""):
        raise UserError("bad currency")
    valid_name(admin)
    conn.executescript(SCHEMA)
    ctx = Ctx(conn, now, admin)
    ctx.set_meta("currency", currency)
    ctx.ex("INSERT INTO users VALUES(?, 'admin', 1)", admin)
    ctx.audit("init", currency)
    return {"currency": currency, "admin": admin}


def enabled_admins(ctx):
    return [r["name"] for r in ctx.q("SELECT name FROM users WHERE role='admin' AND enabled=1")]


def user_add(ctx, name, role):
    valid_name(name)
    if role not in ROLES:
        raise UserError(f"unknown role {role}")
    if ctx.one("SELECT 1 FROM users WHERE name=?", name):
        raise UserError(f"user {name} exists")
    ctx.ex("INSERT INTO users VALUES(?, ?, 1)", name, role)
    ctx.audit("user.add", name)
    return user_json(ctx, name)


def get_user(ctx, name):
    u = ctx.one("SELECT * FROM users WHERE name=?", name)
    if not u:
        raise NotFound(f"unknown user {name}")
    return u


def user_role(ctx, name, role):
    u = get_user(ctx, name)
    if role not in ROLES:
        raise UserError(f"unknown role {role}")
    if u["role"] == "admin" and role != "admin" and u["enabled"] and enabled_admins(ctx) == [name]:
        raise UserError("can't lower the last admin")
    ctx.ex("UPDATE users SET role=? WHERE name=?", role, name)
    ctx.audit("user.role", name)
    return user_json(ctx, name)


def user_disable(ctx, name):
    u = get_user(ctx, name)
    if u["role"] == "admin" and u["enabled"] and enabled_admins(ctx) == [name]:
        raise UserError("can't disable the last admin")
    ctx.ex("UPDATE users SET enabled=0 WHERE name=?", name)
    ctx.audit("user.disable", name)
    return user_json(ctx, name)


def user_json(ctx, name):
    u = get_user(ctx, name)
    return {"name": u["name"], "role": u["role"], "enabled": bool(u["enabled"])}


def user_list(ctx):
    return [user_json(ctx, r["name"]) for r in ctx.q("SELECT name FROM users ORDER BY name")]
