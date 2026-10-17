#!/usr/bin/env python3
"""Compare benchmark runs: bench/compare.py bench/finance/results/<run> [<run> ...]

One column per run, from each run's summary.json. Runs are comparable only with the same
prompt version (the hash of prompt.md and the hidden tests)."""
import json, os, sys

runs = [json.load(open(os.path.join(p, "summary.json"))) | {"dir": os.path.basename(p.rstrip("/"))}
        for p in sys.argv[1:]]
if len({r["prompt"] for r in runs}) > 1:
    print("WARNING: different prompt versions; the runs are not comparable.\n")
rows = [("Run", lambda r: r["dir"]), ("Mode", lambda r: r["mode"]),
        ("Model / effort", lambda r: f'{r["model"]} / {r["effort"]}'),
        ("Prompt version", lambda r: r["prompt"]),
        ("Hidden tests passed", lambda r: f'{r["accept_passed"]}/{r["accept_total"]}'),
        ("Own tests passed", lambda r: f'{r["own_passed"]}/{r["own_total"]}'),
        ("Python lines", lambda r: r["python_lines"]),
        ("Total $", lambda r: f'{r["cost"]:.3f}'), ("Total $, cold start", lambda r: f'{r["cost_cold"]:.3f}'),
        ("Lead / solo $", lambda r: f'{r["lead_cost"]:.3f}'), ("Team $", lambda r: f'{r["team_cost"]:.3f}'),
        ("Teammates", lambda r: len(r["teammates"])),
        ("Lead / solo messages", lambda r: r["lead_messages"]),
        ("Lead / solo peak context", lambda r: f'{r["lead_peak_ctx"] // 1000}K'),
        ("Lead / solo compactions", lambda r: r["lead_compactions"]),
        ("Team peak context", lambda r: f'{r["team_peak_ctx"] // 1000}K'),
        ("Wall time", lambda r: r["started"][11:16] + "-" + r["ended"][11:16]),
        ("**Review overall** (1-10)", lambda r: r.get("review", {}).get("overall", "-")),
        *[(f"Review: {k}", (lambda k: lambda r: r.get("review", {}).get("scores", {}).get(k, "-"))(k))
          for k in ("structure", "readability", "correctness_risks", "error_handling", "data_safety",
                    "tests", "consistency")],
        *[(f"Metric: {k}", (lambda k: lambda r: r.get("quality", {}).get(k, "-"))(k))
          for k in ("app_lines", "test_to_app_ratio", "mean_function_lines", "functions_over_50_lines",
                    "max_complexity", "functions_complexity_over_10", "duplicate_share",
                    "docstring_coverage", "float_calls", "sql_built_from_strings", "bare_except")],
        ("Review cost $ (not in total)", lambda r: r.get("review", {}).get("review_cost", "-"))]
print("| " + " | ".join(["Metric"] + [""] * len(runs)) + " |")
print("|" + "---|" * (len(runs) + 1))
for label, f in rows:
    print(f"| {label} | " + " | ".join(str(f(r)) for r in runs) + " |")
