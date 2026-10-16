# Experiments

Protocol: `kit/protocol/experiments.md`. One section per run; cost reports in `results/metrics/`.

| Run | Feature | Rules | Base commit | Window (UTC) | Total $ | Lead $ | Team $ | Tool calls | Max peak ctx | Accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| m0 | Base game, 3 waves, 5 teammates (shakedown, not A/B) | v0 | 85f0c78 | 19:58:30-20:07:36 | 2.31 | 2.24 | 0.069 | lead 34, team 52 | 73K (game) | yes: 81/81 tests, browser smoke ok, 200-seed bot run |
| e1-A | Camera + inventory panel, 2 teammates in parallel | v0 (long lead session) | 445f130 | 20:21:18-20:22:53 | 0.445 | 0.421 | 0.024 | lead 6, team 19 | 61K (screen) | yes: 95/95 tests, 8/8 acceptance, smoke 5/5 |
| e1-B | Camera + inventory panel, 2 teammates in parallel | v1 (fresh lead session, dev agent) | 445f130 | 20:39:02-20:40:56 | 0.360 | 0.341 | 0.020 | lead 7, team 23 | 39K (screen) | yes: 91/91 tests, 8/8 acceptance, smoke 5/5 |
| e2-A | Balance + end screen and HP bar, 2 teammates | v2; lead Opus 5.5 xhigh, 1h cache | c006911 | 20:57:17-21:02:08 | 0.796 | 0.768 | 0.028 | lead 13, team 44 | 42K (tuner) | yes, after 1 lead fix: 97/97 tests, 7/7 acceptance, smoke ok |
| e2-B | Balance + end screen and HP bar, 2 teammates | v2; lead Sonnet 5.5 medium (cache 1h: 5m not applied) | c006911 | 20:57:24-21:01:03 | 0.301 | 0.274 | 0.027 | lead 7, team 62 | 47K (tuner) | yes, first check: 97/97 tests, 7/7 acceptance, smoke ok |

### m0 notes

Details: `results/runs/m0/notes.md`. Cost report: `results/metrics/m0.json`.

### e1 notes

A/B of rules v0 (A, long lead session) vs v1 (B, fresh lead session per run, `dev` teammate
agent). B costs 19% less with the same acceptance result (first reported as 28%: B's
lead measured itself while its last message was still being written); the saving is the lead's context (peak
320K to 47.5K). Comparison: `results/runs/e1/result.md`. Cost reports: `results/metrics/e1-A.json`,
`results/metrics/e1-B.json`. Variant A's code stays on branch `run/e1/A`; main has B's.

### e2 notes

A/B of the run lead under rules v2: Opus 5.5 xhigh (A) vs Sonnet 5.5 medium (B). B costs 62%
less and passed on the first check. Both ran unattended (`kit/run.sh --bg`) in parallel.
Comparison and caveats: `results/runs/e2/compare-A-B.md`. Main has B's code.
