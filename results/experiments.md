# Experiments

Protocol: `kit/protocol/experiments.md`. One section per run; cost reports in `results/metrics/`.

| Run | Feature | Rules | Base commit | Window (UTC) | Total $ | Lead $ | Team $ | Tool calls | Max peak ctx | Accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| m0 | Base game, 3 waves, 5 teammates (shakedown, not A/B) | v0 | 85f0c78 | 19:58:30-20:07:36 | 2.31 | 2.24 | 0.069 | lead 34, team 52 | 73K (game) | yes: 81/81 tests, browser smoke ok, 200-seed bot run |

| e1-A | Camera + inventory panel, 2 teammates in parallel | v0 (long lead session) | 445f130 | 20:21:18-20:22:53 | 0.445 | 0.421 | 0.024 | lead 6, team 19 | 61K (screen) | yes: 95/95 tests, 8/8 acceptance, smoke 5/5 |

### m0 notes

Details: `results/runs/m0/notes.md`. Cost report: `results/metrics/m0.json`.
