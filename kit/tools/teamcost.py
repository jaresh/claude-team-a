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


CHARS_PER_TOKEN = 3.5


def session_of(path):
    """Lead session id of a transcript: its own name, or the folder above subagents/."""
    parts = path.split(os.sep)
    if len(parts) >= 3 and parts[-2] == "subagents":
        return parts[-3]
    return os.path.basename(path)[:-len(".jsonl")]


def scan(path, since, until):
    # Teammate transcripts keep the usage from the start of each response (stop_reason null), so
    # their output_tokens are far too low. For those responses, output is estimated from the
    # visible content (text and tool inputs). Hidden thinking stays uncounted.
    usage, final, chars = {}, set(), Counter()
    tools, agent, first, last, started = set(), None, None, None, None
    with open(path) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") != "assistant":
                continue
            ts = parse_time(e.get("timestamp"))
            started = started or ts
            if ts and ((since and ts < since) or (until and ts > until)):
                continue
            m = e.get("message") or {}
            if not m.get("id") or m.get("model") in (None, "<synthetic>"):
                continue
            usage[m["id"]] = (m["model"], m.get("usage") or {})
            if m.get("stop_reason"):
                final.add(m["id"])
            for c in m.get("content") or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use":
                    tools.add(c.get("id"))
                    chars[m["id"]] += len(json.dumps(c.get("input") or {}))
                chars[m["id"]] += len(c.get("text") or "") + len(c.get("thinking") or "")
            agent = agent or e.get("agentId")
            first = first or ts
            last = ts
    if not usage:
        return None
    # Teammates have <transcript>.meta.json; the name is the spawn description up to ':'.
    meta, name = path[:-len(".jsonl")] + ".meta.json", None
    if os.path.exists(meta):
        with open(meta) as f:
            meta = json.load(f)
        name = meta.get("description", "").split(":")[0].strip() or None
    else:
        meta = {}
    models = Counter(model for model, _ in usage.values())
    row = {"agent": name or agent or "lead:" + os.path.basename(path)[:8],
           "effort": meta.get("effort", ""),
           "file": path, "session": session_of(path),
           "started": started.isoformat() if started else None,
           "model": models.most_common(1)[0][0], "msgs": len(usage),
           "tools": len(tools), "input": 0, "cache_w": 0, "cache_r": 0, "output": 0,
           "peak_ctx": 0, "over_100k": 0, "cost": 0.0, "unpriced": 0, "out_est": 0,
           "first": first.isoformat() if first else None,
           "last": last.isoformat() if last else None}
    for mid, (model, u) in usage.items():
        if mid not in final:
            estimate = round(chars[mid] / CHARS_PER_TOKEN)
            if estimate > u.get("output_tokens", 0):
                u = dict(u, output_tokens=estimate)
            row["out_est"] += 1
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
    ap.add_argument("--fresh-only", action="store_true",
                    help="count only lead sessions that started at or after --since, in full, "
                         "with their teammates (a run in a fresh session; leaves out other open "
                         "sessions)")
    ap.add_argument("--latest-session", action="store_true",
                    help="count only the most recently started lead session, in full, with its "
                         "teammates. Run it from the run's own lead session.")
    a = ap.parse_args()
    pdir = os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-",
                                                             os.path.abspath(a.project)))
    since, until = parse_time(a.since), parse_time(a.until)
    # With --fresh-only, a run is its whole fresh session (including the first message, which
    # writes the cached prefix); --since only selects which sessions count.
    scan_since = None if (a.fresh_only or a.latest_session) else since
    rows = [r for p in sorted(glob.glob(pdir + "/**/*.jsonl", recursive=True))
            if (r := scan(p, scan_since, until))]
    if a.fresh_only:
        if not since:
            ap.error("--fresh-only needs --since")
        fresh = {r["session"] for r in rows if r["file"].endswith(r["session"] + ".jsonl")
                 and r["started"] and parse_time(r["started"]) >= since}
        rows = [r for r in rows if r["session"] in fresh]
    if a.latest_session:
        leads = [r for r in rows if r["file"].endswith(r["session"] + ".jsonl") and r["started"]]
        if leads:
            latest = max(leads, key=lambda r: r["started"])["session"]
            rows = [r for r in rows if r["session"] == latest]
    rows.sort(key=lambda r: r["first"] or "")

    cols = ["agent", "model", "effort", "msgs", "tools", "input", "cache_w", "cache_r", "output",
            "out_est", "peak_ctx", "over_100k", "cost"]
    fmt = lambda r, c: f"{r[c]:.4f}" if c == "cost" else str(r[c]).replace("claude-", "")
    table = [cols] + [[fmt(r, c) for c in cols] for r in rows]
    by_model = {}
    for r in rows:
        t = by_model.setdefault(r["model"], {c: 0 for c in cols[3:]})
        for c in cols[3:]:
            t[c] = max(t[c], r[c]) if c == "peak_ctx" else t[c] + r[c]
    for model, t in by_model.items():
        table.append(["TOTAL", model.replace("claude-", ""), ""] + [fmt(t, c) for c in cols[3:]])
    widths = [max(len(row[i]) for row in table) for i in range(len(cols))]
    for row in table:
        print("  ".join(v.ljust(w) if i < 3 else v.rjust(w)
                        for i, (v, w) in enumerate(zip(row, widths))))
    total = sum(r["cost"] for r in rows)
    print(f"total ${total:.4f}" + ("  (some messages unpriced)" if any(r["unpriced"] for r in rows)
                                   else ""))
    if any(r["out_est"] for r in rows):
        print("out_est: responses whose output was estimated from visible content "
              f"({CHARS_PER_TOKEN} chars/token); hidden thinking is not counted.")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"since": a.since, "until": a.until, "total_cost": total,
                       "by_model": by_model, "agents": rows}, f, indent=2)


if __name__ == "__main__":
    main()
