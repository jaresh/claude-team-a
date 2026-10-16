#!/usr/bin/env python3
"""Tokens, peak context and USD cost per agent, from Claude Code transcripts.

Reads every transcript (*.jsonl) of this project under ~/.claude/projects/: lead sessions and
their teammates. Prints numbers only, never message content.

  teamcost.py --latest-session [--until ISO] [--json OUT]   # a run in a fresh session
  teamcost.py --session ID [--until ISO] [--json OUT]        # a given lead session, in full
  teamcost.py --since ISO [--until ISO] [--json OUT]         # a time window, all sessions
  teamcost.py --compare A.json B.json                        # A/B table in Markdown
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
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cw5m": 2.50, "cw1h": 4.00, "cr": 0.20},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cw5m": 0.125, "cw1h": 0.20, "cr": 0.01,
                         "long_over": 100_000, "long_mult": 5.0},
}
LONG = 100_000
CHARS_PER_TOKEN = 3.5
PARTS = ("cost_in", "cost_cr", "cost_cw", "cost_out")


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def prompt_size(u):
    return (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0))


def message_cost(model, u):
    """Cost parts of one response: input, cache read, cache write, output. None if unpriced."""
    p = PRICES.get(model)
    if p is None:
        return None
    cw = u.get("cache_creation_input_tokens", 0)
    cc = u.get("cache_creation") or {}
    cw1h = cc.get("ephemeral_1h_input_tokens", 0)
    cw5m = cc.get("ephemeral_5m_input_tokens", cw - cw1h)
    mult = p.get("long_mult", 1.0) if prompt_size(u) > p.get("long_over", float("inf")) else 1.0
    return {"cost_in": mult * p["in"] * u.get("input_tokens", 0) / 1e6,
            "cost_cr": mult * p["cr"] * u.get("cache_read_input_tokens", 0) / 1e6,
            "cost_cw": mult * (p["cw5m"] * cw5m + p["cw1h"] * cw1h) / 1e6,
            "cost_out": mult * p["out"] * u.get("output_tokens", 0) / 1e6}


def session_of(path):
    """Lead session id of a transcript: its own name, or the folder above subagents/."""
    parts = path.split(os.sep)
    if len(parts) >= 3 and parts[-2] == "subagents":
        return parts[-3]
    return os.path.basename(path)[:-len(".jsonl")]


def agent_effort(project, agent_type):
    """`effort:` from the project's .claude/agents/<type>.md frontmatter, if any."""
    path = os.path.join(project, ".claude", "agents", f"{agent_type}.md")
    if not agent_type or not os.path.exists(path):
        return ""
    m = re.search(r"^effort:\s*(\S+)", open(path).read().split("---")[1], re.M)
    return m.group(1) if m else ""


def scan(path, since, until, project):
    # Teammate transcripts keep the usage from the start of each response (stop_reason null), so
    # their output_tokens are far too low. For those responses, output is estimated from the
    # visible content (text and tool inputs). Hidden thinking stays uncounted.
    usage, final, chars = {}, set(), Counter()
    tools, agent, first, last, started, compactions = set(), None, None, None, None, 0
    with open(path) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
                compactions += 1
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
    session = session_of(path)
    role = "lead" if os.path.basename(path) == session + ".jsonl" else "teammate"
    meta = {}
    if os.path.exists(path[:-len(".jsonl")] + ".meta.json"):
        with open(path[:-len(".jsonl")] + ".meta.json") as f:
            meta = json.load(f)
    name = meta.get("name") or meta.get("description", "").split(":")[0].strip() or None
    models = Counter(model for model, _ in usage.values())
    row = {"agent": name or agent or "lead:" + session[:8], "role": role,
           "effort": meta.get("effort") or agent_effort(project, meta.get("customAgentType")),
           "file": path, "session": session,
           "started": started.isoformat() if started else None,
           "model": models.most_common(1)[0][0], "msgs": len(usage),
           "tools": len(tools), "input": 0, "cache_w": 0, "cache_r": 0, "output": 0,
           "peak_ctx": 0, "over_100k": 0, "compactions": compactions, "cost": 0.0,
           "unpriced": 0, "out_est": 0,
           **{k: 0.0 for k in PARTS},
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
            continue
        for k in PARTS:
            row[k] += c[k]
        row["cost"] += sum(c.values())
    return row


def totals(agents, role):
    rows = [r for r in agents if r.get("role", "lead" if r["agent"].startswith("lead:")
                                         else "teammate") == role]
    t = {k: sum(r.get(k, 0) for r in rows) for k in ("cost", "msgs", "tools", "output",
                                                     "over_100k", "compactions") + PARTS}
    t["peak_ctx"] = max((r["peak_ctx"] for r in rows), default=0)
    t["models"] = sorted({r["model"].replace("claude-", "") for r in rows})
    t["count"] = len(rows)
    return t


def compare(path_a, path_b):
    a, b = (json.load(open(p)) for p in (path_a, path_b))
    la, lb = totals(a["agents"], "lead"), totals(b["agents"], "lead")
    ta, tb = totals(a["agents"], "teammate"), totals(b["agents"], "teammate")

    def pct(x, y):
        return f"{(y - x) / x * 100:+.0f}%" if x else ""

    rows = [("Total $", a["total_cost"], b["total_cost"], "$"),
            ("Lead $", la["cost"], lb["cost"], "$"),
            ("Team $", ta["cost"], tb["cost"], "$"),
            ("Lead model", ", ".join(la["models"]), ", ".join(lb["models"]), "s"),
            ("Lead cache read $", la["cost_cr"], lb["cost_cr"], "$"),
            ("Lead cache write $", la["cost_cw"], lb["cost_cw"], "$"),
            ("Lead output $", la["cost_out"], lb["cost_out"], "$"),
            ("Lead messages", la["msgs"], lb["msgs"], "n"),
            ("Lead tool calls", la["tools"], lb["tools"], "n"),
            ("Lead output tokens", la["output"], lb["output"], "n"),
            ("Lead peak context", la["peak_ctx"], lb["peak_ctx"], "k"),
            ("Teammates", ta["count"], tb["count"], "n"),
            ("Team tool calls", ta["tools"], tb["tools"], "n"),
            ("Team peak context", ta["peak_ctx"], tb["peak_ctx"], "k"),
            ("Team messages over 100K", ta["over_100k"], tb["over_100k"], "n"),
            ("Team compactions", ta["compactions"], tb["compactions"], "n")]
    fmt = {"$": lambda v: f"{v:.3f}", "n": str, "k": lambda v: f"{v / 1000:.0f}K", "s": str}
    print(f"| Metric | A | B | B vs A |\n|---|---|---|---|")
    for label, x, y, kind in rows:
        delta = "" if kind == "s" else pct(x, y)
        print(f"| {label} | {fmt[kind](x)} | {fmt[kind](y)} | {delta} |")
    print(f"\nA: {path_a} {a.get('label', '')}\nB: {path_b} {b.get('label', '')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--json")
    ap.add_argument("--project", default=os.getcwd(), help="repo path (default: cwd)")
    ap.add_argument("--fresh-only", action="store_true",
                    help="count only lead sessions that started at or after --since, in full, "
                         "with their teammates")
    ap.add_argument("--latest-session", action="store_true",
                    help="count only the most recently started lead session, in full, with its "
                         "teammates. Run it from the run's own lead session.")
    ap.add_argument("--session", help="count only this lead session (id or prefix), in full, "
                                      "with its teammates")
    ap.add_argument("--compare", nargs=2, metavar=("A_JSON", "B_JSON"),
                    help="print an A/B comparison table of two --json reports")
    ap.add_argument("--label", default="", help="free text stored in the --json report, such "
                                                "as the lead's model, effort and cache TTL")
    a = ap.parse_args()
    if a.compare:
        return compare(*a.compare)

    project = os.path.abspath(a.project)
    pdir = os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", project))
    since, until = parse_time(a.since), parse_time(a.until)
    whole = a.fresh_only or a.latest_session or a.session
    # Whole-session modes count each selected session in full (including its first message,
    # which writes the cached prefix); --since then only selects sessions.
    rows = [r for p in sorted(glob.glob(pdir + "/**/*.jsonl", recursive=True))
            if (r := scan(p, None if whole else since, until, project))]
    leads = [r for r in rows if r["role"] == "lead" and r["started"]]
    keep = None
    if a.fresh_only:
        if not since:
            ap.error("--fresh-only needs --since")
        keep = {r["session"] for r in leads if parse_time(r["started"]) >= since}
    if a.latest_session and leads:
        keep = {max(leads, key=lambda r: r["started"])["session"]}
    if a.session:
        keep = {r["session"] for r in leads if r["session"].startswith(a.session)}
    if keep is not None:
        rows = [r for r in rows if r["session"] in keep]
    rows.sort(key=lambda r: r["first"] or "")

    cols = ["agent", "model", "effort", "msgs", "tools", "input", "cache_w", "cache_r", "output",
            "out_est", "peak_ctx", "over_100k", "compactions", "cost"]
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
            json.dump({"label": a.label, "since": a.since, "until": a.until,
                       "session": a.session, "total_cost": total, "by_model": by_model,
                       "agents": rows}, f, indent=2)


if __name__ == "__main__":
    main()
