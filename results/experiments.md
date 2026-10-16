# Experiments

Protocol: `kit/protocol/experiments.md`. One section per run; cost reports in `results/metrics/`.

| Run | Feature | Rules | Base commit | Window (UTC) | Total $ | Lead $ | Team $ | Tool calls | Max peak ctx | Accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| m0 | Base game, 3 waves, 5 teammates (shakedown, not A/B) | v0 | 85f0c78 | 19:58:30-20:07:36 | 2.31 | 2.24 | 0.069 | lead 34, team 52 | 73K (game) | yes: 81/81 tests, browser smoke ok, 200-seed bot run |
| e1-A | Camera + inventory panel, 2 teammates in parallel (row copied from `run/e1/A`) | v0 (long lead session) | 445f130 | 20:21:18-20:22:53 | 0.445 | 0.421 | 0.024 | lead 6, team 19 | 61K (screen) | yes: 95/95 tests, 8/8 acceptance, smoke 5/5 |
| e1-B | Camera + inventory panel, 2 teammates in parallel | v1 (fresh lead session, `dev` agent) | b36fdaf | 20:30:15-20:32:02 | 0.218 (raw 0.395, see e1 notes) | 0.198 | 0.021 | lead 8, team 28 | 40K (screen) | yes: 94/94 tests, 8/8 acceptance, smoke 5/5 |

### m0 notes

Details: `results/runs/m0/notes.md`. Cost report: `results/metrics/m0.json`.

### e1 notes

A/B of rules v0 vs v1 on one feature. Details and caveats: `results/runs/e1/result.md`. Cost
reports: `results/metrics/e1-A.json` (branch `run/e1/A`), `results/metrics/e1-B.json`. The e1-B
total leaves out $0.176 from another session (`55f7d26e`) that was active during B's window;
the raw JSON still includes it.
