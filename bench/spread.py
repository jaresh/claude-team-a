#!/usr/bin/env python3
"""Run-to-run spread and stability of a benchmark's results.

    bench/spread.py bench/finance/results [--kit 3.9]

Groups the runs of the latest prompt version by arm (team runs also by kit version; solo runs
don't use the kit, so they form one group) and prints n, median and range per metric. A run
reviewed more than once (REVIEWS=N) counts with the median of its reviews, and the reviewer's
own spread on identical code is listed apart: that is the noise floor of the review.

Then the stability check, team on --kit (default: the newest kit with team runs) against solo:
for each metric, which arm is better on the medians, and whether that still holds after
leaving out any one run of either arm. "stable" means no single run decides the conclusion. A
review difference no larger than the noise floor (the widest spread of one run's reviews) is a
tie."""
import datetime as dt
import json
import os
import statistics
import sys


def load(results):
    runs = []
    for name in sorted(os.listdir(results)):
        path = os.path.join(results, name, "summary.json")
        if os.path.exists(path):
            runs.append(json.load(open(path)) | {"dir": name})
    return runs


def overall(r):
    vals = [x["overall"] for x in r.get("reviews") or [r.get("review", {})] if x.get("overall") is not None]
    return statistics.median(vals) if vals else None


def score(k):
    def f(r):
        vals = [x["scores"][k] for x in r.get("reviews") or [r.get("review", {})] if x.get("scores")]
        return statistics.median(vals) if vals else None
    return f


def minutes(r):
    t = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return round((t(r["ended"]) - t(r["started"])).total_seconds() / 60, 1)


# (label, value, better): better is "high" or "low"; review scores are compared within the noise floor
METRICS = [("Hidden tests passed", lambda r: r["accept_passed"], "high"),
           ("Review overall", overall, "high"),
           ("Review consistency", score("consistency"), "high"),
           ("Review tests", score("tests"), "high"),
           ("Review structure", score("structure"), "high"),
           ("Own tests' coverage", lambda r: r.get("coverage"), "high"),
           ("Cost $, cold start", lambda r: r["cost_cold"], "low"),
           ("Lead / solo messages", lambda r: r["lead_messages"], "low"),
           ("Wall minutes", minutes, "low")]


def stats(runs, f):
    vals = [v for v in map(f, runs) if v is not None]
    if not vals:
        return None, "-"
    med = statistics.median(vals)
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) and v < 5 else f"{v:g}"
    return med, f"{fmt(med)} ({fmt(min(vals))}-{fmt(max(vals))})"


def verdict(a, b, f, better, tol=0):
    ma, mb = stats(a, f)[0], stats(b, f)[0]
    if ma is None or mb is None or abs(ma - mb) <= tol:
        return "tie"
    return "team" if (ma > mb) == (better == "high") else "solo"


def main():
    results = sys.argv[1]
    runs = load(results)
    prompt = runs[-1]["prompt"]
    runs = [r for r in runs if r["prompt"] == prompt]
    groups = {}
    for r in runs:
        key = f'team, kit {r.get("kit", "?")}' if r["mode"] == "team" else "solo"
        groups.setdefault(key, []).append(r)
    names = sorted(groups, key=lambda k: (k == "solo", k))
    print(f"Prompt version {prompt}: median (min-max) per group\n")
    print("| Metric | " + " | ".join(f"{k} (n={len(groups[k])})" for k in names) + " |")
    print("|" + "---|" * (len(names) + 1))
    for label, f, _ in METRICS:
        print(f"| {label} | " + " | ".join(stats(groups[k], f)[1] for k in names) + " |")

    noisy = [r for r in runs if len(r.get("reviews") or []) > 1]
    floor = max((max(x["overall"] for x in r["reviews"]) - min(x["overall"] for x in r["reviews"])
                 for r in noisy), default=0)
    if noisy:
        print("\nReviewer noise (the same code reviewed several times):\n")
        for r in noisy:
            vals = [x["overall"] for x in r["reviews"]]
            print(f"- {r['dir']}: overall {vals}, range {max(vals) - min(vals)}")
        print(f"\nNoise floor: review differences of {floor} or less are ties.")

    kits = sorted({r.get("kit") for r in runs if r["mode"] == "team"}, key=lambda v: [int(x) for x in v.split(".")])
    kit = sys.argv[sys.argv.index("--kit") + 1] if "--kit" in sys.argv else kits[-1]
    team, solo = groups.get(f"team, kit {kit}", []), groups.get("solo", [])
    if len(team) < 2 or len(solo) < 2:
        print(f"\nStability check needs at least 2 runs per arm (team kit {kit}: {len(team)}, solo: {len(solo)}).")
        return
    print(f"\nStability, team kit {kit} (n={len(team)}) vs solo (n={len(solo)}): better on the medians, "
          "and whether leaving out any one run changes it\n")
    print("| Metric | Better | Leave-one-out |")
    print("|---|---|---|")
    for label, f, better in METRICS:
        tol = floor if label.startswith("Review") else 0
        base = verdict(team, solo, f, better, tol)
        alts = {verdict(team[:i] + team[i + 1:], solo, f, better, tol) for i in range(len(team))}
        alts |= {verdict(team, solo[:i] + solo[i + 1:], f, better, tol) for i in range(len(solo))}
        print(f"| {label} | {base} | {'stable' if alts == {base} else 'flips: ' + '/'.join(sorted(alts))} |")


if __name__ == "__main__":
    main()
