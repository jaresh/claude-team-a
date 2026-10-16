# Experiments

Protocol: `kit/protocol/experiments.md`. One section per run; cost reports in `results/metrics/`.

| Run | Feature | Rules | Base commit | Window (UTC) | Total $ | Lead $ | Team $ | Tool calls | Max peak ctx | Accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| m0 | Base game, 3 waves, 5 teammates (shakedown, not A/B) | v0 | 85f0c78 | 19:58:30-20:07:36 | 2.31 | 2.24 | 0.069 | lead 34, team 52 | 73K (game) | yes: 81/81 tests, browser smoke ok, 200-seed bot run |
| e1-B | Camera + inventory panel, 2 teammates in parallel | v1 (fresh lead session, dev agent) | 445f130 | 20:39:02-20:40:56 | 0.319 | 0.299 | 0.020 | lead 7, team 23 | 39K (screen) | yes: 91/91 tests, 8/8 acceptance, smoke 5/5 |

### m0 notes

Details: `results/runs/m0/notes.md`. Cost report: `results/metrics/m0.json`.

### e1 notes

A/B of rules v0 (A, long lead session) vs v1 (B, fresh lead session per run, `dev` teammate
agent). B costs 28% less with the same acceptance result; the saving is the lead's context (peak
320K to 47.5K). Comparison: `results/runs/e1/result.md`. Cost reports: `results/metrics/e1-A.json`
(branch `run/e1/A`), `results/metrics/e1-B.json`.
