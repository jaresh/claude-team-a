"""The movement log, replayed: stock and cost layers derived from the movements."""
import json
from collections import defaultdict
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from .core import UserError, ZERO, cost4, fq, money, r2, r4, wh_of


def load_movements(ctx, upto=None):
    sql = "SELECT * FROM movements" + (" WHERE id<=?" if upto is not None else "") + " ORDER BY id"
    return [dict(r) for r in (ctx.q(sql, upto) if upto is not None else ctx.q(sql))]


def unit_keys(m):
    serials = json.loads(m["serials"] or "[]")
    units = [(s, Decimal(1)) for s in serials] if serials else [(None, Decimal(m["qty"]))]
    for serial, q in units:
        if m["src"]:
            yield (m["sku"], m["src"], m["lot"], serial), -q
        if m["dst"]:
            yield (m["sku"], m["dst"], m["lot"], serial), q


def stock_map(mvs):
    s = defaultdict(Decimal)
    for m in mvs:
        for k, q in unit_keys(m):
            s[k] += q
    return {k: v for k, v in s.items() if v != 0}


class Layer:
    __slots__ = ("time", "mvid", "seq", "cost", "rem", "orig")

    def __init__(self, time, mvid, seq, cost, qty):
        self.time, self.mvid, self.seq, self.cost, self.rem, self.orig = time, mvid, seq, cost, qty, qty

    def key(self):
        return (self.time, self.mvid, self.seq)


class Engine:
    """Costing state per (sku, warehouse), built by applying movements in id order."""

    def __init__(self, ctx, mvs):
        self.costing = {r["sku"]: r["costing"] for r in ctx.q("SELECT sku, costing FROM products")}
        self.tr_src = {r["id"]: r["src"] for r in ctx.q("SELECT id, src FROM transfers")}
        self.layers = defaultdict(list)
        self.avg = {}
        self.seq = 0
        self.slices = {}
        self.tr_out = {}
        self.snap = {}
        self.created = {}
        self.by_id = {m["id"]: m for m in mvs}

    def _avg(self, sku, w):
        return self.avg.setdefault((sku, w), {"Q": ZERO, "V": r2(0), "A": None, "last": None})

    @staticmethod
    def _recompute(st):
        if st["Q"] > 0:
            st["A"] = r4(st["V"] / st["Q"])
            st["last"] = st["A"]
        else:
            st["A"] = None

    def _add_layer(self, sku, w, time, mvid, c, q):
        self.seq += 1
        layer = Layer(time, mvid, self.seq, c, q)
        self.layers[(sku, w)].append(layer)
        return layer

    def _in(self, m, w, q, c, value=None):
        sku = m["sku"]
        value = r2(q * c) if value is None else value
        if self.costing[sku] == "fifo":
            self.created[m["id"]] = self._add_layer(sku, w, m["at"], m["id"], c, q)
        else:
            st = self._avg(sku, w)
            self.snap[m["id"]] = dict(st)
            st["V"] += value
            st["Q"] += q
            self._recompute(st)
        return value

    def _out(self, m, w, q):
        sku = m["sku"]
        if self.costing[sku] == "fifo":
            need, total, sl = q, ZERO, []
            for layer in sorted((x for x in self.layers[(sku, w)] if x.rem > 0), key=Layer.key):
                if need <= 0:
                    break
                take = min(layer.rem, need)
                layer.rem -= take
                need -= take
                total += take * layer.cost
                sl.append((layer, take))
            if need > 0:
                raise UserError("not enough costed stock")
            self.slices[m["id"]] = sl
            return r2(total)
        st = self._avg(sku, w)
        if q == st["Q"]:
            value, st["V"], st["Q"] = st["V"], r2(0), ZERO
        else:
            value = r2(q * st["A"])
            st["V"] -= value
            st["Q"] -= q
        self._recompute(st)
        return value

    def apply(self, m):
        t, sku, q = m["type"], m["sku"], Decimal(m["qty"])
        fifo = self.costing[sku] == "fifo"
        if t in ("move", "pick"):
            return r2(0)
        if t in ("receive", "return"):
            return self._in(m, wh_of(m["dst"]), q, Decimal(m["unit_cost"]))
        if t == "adjust":
            if not m["dst"]:
                return self._out(m, wh_of(m["src"]), q)
            w = wh_of(m["dst"])
            if fifo:
                ever = self.layers[(sku, w)]
                if not ever:
                    raise UserError(f"no cost known for {sku} in {w}")
                newest = max(ever, key=Layer.key)
                return self._in(m, w, q, newest.cost)
            st = self.avg.get((sku, w))
            a = st and (st["A"] if st["Q"] > 0 else st["last"])
            if a is None:
                raise UserError(f"no cost known for {sku} in {w}")
            return self._in(m, w, q, a, r2(q * a))
        if t in ("scrap", "ship", "transfer-out"):
            v = self._out(m, wh_of(m["src"]), q)
            if t == "transfer-out":
                self.tr_out[m["ref"]] = (m["id"], v)
            return v
        if t == "transfer-in":
            out_id, v = self.tr_out[m["ref"]]
            w = wh_of(m["dst"])
            back = w == wh_of(self.tr_src[m["ref"]])
            if fifo:
                for layer, sq in self.slices[out_id]:
                    if back:
                        layer.rem += sq
                    else:
                        self._add_layer(sku, w, layer.time, layer.mvid, layer.cost, sq)
            else:
                st = self._avg(sku, w)
                st["V"] += v
                st["Q"] += q
                self._recompute(st)
            return v
        if t == "void":
            x = self.by_id[int(m["ref"][3:])]
            if x["type"] == "move":
                return r2(0)
            if x["type"] == "receive" or (x["type"] == "adjust" and x["dst"]):
                w = wh_of(x["dst"])
                if fifo:
                    layer = self.created[x["id"]]
                    if layer.rem != layer.orig:
                        raise UserError(f"stock of movement {x['id']} has been issued; it can't be voided")
                    self.layers[(sku, w)].remove(layer)
                else:
                    self.avg[(sku, w)] = dict(self.snap[x["id"]])
                return Decimal(x["value"])
            w = wh_of(x["src"])
            if fifo:
                for layer, sq in self.slices[x["id"]]:
                    layer.rem += sq
            else:
                st = self._avg(sku, w)
                st["V"] += Decimal(x["value"])
                st["Q"] += Decimal(x["qty"])
                self._recompute(st)
            return Decimal(x["value"])
        raise UserError(f"unknown movement type {t}")

    def stock_value(self, sku, w):
        if self.costing[sku] == "fifo":
            ls = self.layers.get((sku, w), [])
            return sum((x.rem for x in ls), ZERO), r2(sum((x.rem * x.cost for x in ls), ZERO))
        st = self.avg.get((sku, w))
        return (st["Q"], st["V"]) if st else (ZERO, r2(0))


def replay(ctx, mvs):
    e = Engine(ctx, mvs)
    for m in mvs:
        e.apply(m)
    return e


def _replay_with_value(ctx, mvs, m):
    e = Engine(ctx, mvs + [m])
    for x in mvs:
        e.apply(x)
    return e, e.apply(m)


def add_movement(ctx, type_, sku, qty, src, dst, lot=None, serials=(), unit_cost=None, ref=None,
                 line=None, reason=None):
    p = ctx.product(sku)
    mvs = load_movements(ctx)
    m = {"id": (mvs[-1]["id"] if mvs else 0) + 1, "at": ctx.now_s, "user": ctx.user, "type": type_,
         "sku": sku, "qty": fq(qty, p["unit"]), "src": src, "dst": dst, "lot": lot,
         "serials": json.dumps(sorted(serials)), "unit_cost": cost4(unit_cost) if unit_cost is not None else None,
         "value": None, "ref": ref, "line": line, "voided": 0, "reason": reason}
    _, value = _replay_with_value(ctx, mvs, m)
    m["value"] = money(value)
    ctx.conn.execute(
        "INSERT INTO movements(id, at, user, type, sku, qty, src, dst, lot, serials, unit_cost, value, ref, "
        "line, voided, reason) VALUES(:id, :at, :user, :type, :sku, :qty, :src, :dst, :lot, :serials, "
        ":unit_cost, :value, :ref, :line, :voided, :reason)", m)
    return m


def mv_json(m):
    return {"id": m["id"], "at": m["at"], "user": m["user"], "type": m["type"], "sku": m["sku"],
            "qty": m["qty"], "from": m["src"], "to": m["dst"], "lot": m["lot"],
            "serials": json.loads(m["serials"] or "[]"), "unit_cost": m["unit_cost"], "value": m["value"],
            "ref": m["ref"]}


def current_stock(ctx):
    return stock_map(load_movements(ctx))


def reserved_map(ctx, picked=None):
    r = defaultdict(Decimal)
    sql = "SELECT * FROM reservations" + ("" if picked is None else f" WHERE picked={int(picked)}")
    for x in ctx.q(sql):
        r[(x["sku"], x["loc"], x["lot"], x["serial"])] += Decimal(x["qty"])
    return r


def free_at(ctx, sku, loc, lot, serial, stock=None, reserved=None):
    stock = current_stock(ctx) if stock is None else stock
    reserved = reserved_map(ctx) if reserved is None else reserved
    k = (sku, loc, lot, serial)
    return stock.get(k, ZERO) - reserved.get(k, ZERO)
