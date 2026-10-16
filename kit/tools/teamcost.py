#!/usr/bin/env python3
"""Tokens, peak context and USD cost per agent, from Claude Code transcripts.

Reads every transcript (*.jsonl) of this project under ~/.claude/projects/: the lead session and
each teammate. Prints numbers only, never message content.

  python3 kit/tools/teamcost.py [--since ISO] [--until ISO] [--json OUT] [--project DIR]
"""
import argparse
import glob
import json
import os
import re
from collections import Counter
from datetime import datetime

# USD per million tokens (checked 2026-10-16 against Claude Code's own cost-state records).
# Haiku 5.5 bills a whole prompt over 100K tokens at 5x.
PRICES = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cw5m": 5.00, "cw1h": 8.00, "cr": 0.20},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cw5m": 0.125, "cw1h": 0.20, "cr": 0.01,
                         "long_over": 100_000, "long_mult": 5.0},
}
LONG = 100_000


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def prompt_size(u):
    return (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0))


def message_cost(model, u):
    p = PRICES.get(model)
    if p is None:
        return None
    cw = u.get("cache_creation_input_tokens", 0)
    cc = u.get("cache_creation") or {}
    cw1h = cc.get("ephemeral_1h_input_tokens", 0)
    cw5m = cc.get("ephemeral_5m_input_tokens", cw - cw1h)
    mult = p.get("long_mult", 1.0) if prompt_size(u) > p.get("long_over", float("inf")) else 1.0
    return mult * (p["in"] * u.get("input_tokens", 0) + p["out"] * u.get("output_tokens", 0)
                   + p["cr"] * u.get("cache_read_input_tokens", 0)
                   + p["cw5m"] * cw5m + p["cw1h"] * cw1h) / 1e6


def scan(path, since, until):
    usage, tools, agent, first, last = {}, set(), None, None, None
    with open(path) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") != "assistant":
                continue
            ts = parse_time(e.get("timestamp"))
            if ts and ((since and ts < since) or (until and ts > until)):
                continue
            m = e.get("message") or {}
            if not m.get("id") or m.get("model") in (None, "<synthetic>"):
                continue
            usage[m["id"]] = (m["model"], m.get("usage") or {})
            for c in m.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tools.add(c.get("id"))
            agent = agent or e.get("agentId")
            first = first or ts
            last = ts
    if not usage:
        return None
    models = Counter(model for model, _ in usage.values())
    row = {"agent": agent or "lead:" + os.path.basename(path)[:8],
           "file": path, "model": models.most_common(1)[0][0], "msgs": len(usage),
           "tools": len(tools), "input": 0, "cache_w": 0, "cache_r": 0, "output": 0,
           "peak_ctx": 0, "over_100k": 0, "cost": 0.0, "unpriced": 0,
           "first": first.isoformat() if first else None,
           "last": last.isoformat() if last else None}
    for model, u in usage.values():
        row["input"] += u.get("input_tokens", 0)
        row["cache_w"] += u.get("cache_creation_input_tokens", 0)
        row["cache_r"] += u.get("cache_read_input_tokens", 0)
        row["output"] += u.get("output_tokens", 0)
        row["peak_ctx"] = max(row["peak_ctx"], prompt_size(u))
        row["over_100k"] += prompt_size(u) > LONG
        c = message_cost(model, u)
        if c is None:
            row["unpriced"] += 1
        else:
            row["cost"] += c
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--json")
    ap.add_argument("--project", default=os.getcwd(), help="repo path (default: cwd)")
    a = ap.parse_args()
    pdir = os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-",
                                                             os.path.abspath(a.project)))
    since, until = parse_time(a.since), parse_time(a.until)
    rows = [r for p in sorted(glob.glob(pdir + "/**/*.jsonl", recursive=True))
            if (r := scan(p, since, until))]
    rows.sort(key=lambda r: r["first"] or "")

    cols = ["agent", "model", "msgs", "tools", "input", "cache_w", "cache_r", "output",
            "peak_ctx", "over_100k", "cost"]
    fmt = lambda r, c: f"{r[c]:.4f}" if c == "cost" else str(r[c]).replace("claude-", "")
    table = [cols] + [[fmt(r, c) for c in cols] for r in rows]
    by_model = {}
    for r in rows:
        t = by_model.setdefault(r["model"], {c: 0 for c in cols[2:]})
        for c in cols[2:]:
            t[c] = max(t[c], r[c]) if c == "peak_ctx" else t[c] + r[c]
    for model, t in by_model.items():
        table.append(["TOTAL", model.replace("claude-", "")] + [fmt(t, c) for c in cols[2:]])
    widths = [max(len(row[i]) for row in table) for i in range(len(cols))]
    for row in table:
        print("  ".join(v.ljust(w) if i < 2 else v.rjust(w)
                        for i, (v, w) in enumerate(zip(row, widths))))
    total = sum(r["cost"] for r in rows)
    print(f"total ${total:.4f}" + ("  (some messages unpriced)" if any(r["unpriced"] for r in rows)
                                   else ""))
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"since": a.since, "until": a.until, "total_cost": total,
                       "by_model": by_model, "agents": rows}, f, indent=2)


if __name__ == "__main__":
    main()
