# Experiments

Protocol: `lab/protocol.md`. One section per run; cost reports in `results/metrics/`.

| Run | Feature | Rules | Base commit | Window (UTC) | Total $ | Lead $ | Team $ | Tool calls | Max peak ctx | Accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| m0 | Base game, 3 waves, 5 teammates (shakedown, not A/B) | v0 | 85f0c78 | 19:58:30-20:07:36 | 2.31 | 2.24 | 0.069 | lead 34, team 52 | 73K (game) | yes: 81/81 tests, browser smoke ok, 200-seed bot run |
| e1-A | Camera + inventory panel, 2 teammates in parallel | v0 (long lead session) | 445f130 | 20:21:18-20:22:53 | 0.445 | 0.421 | 0.024 | lead 6, team 19 | 61K (screen) | yes: 95/95 tests, 8/8 acceptance, smoke 5/5 |
| e1-B | Camera + inventory panel, 2 teammates in parallel | v1 (fresh lead session, dev agent) | 445f130 | 20:39:02-20:40:56 | 0.360 | 0.341 | 0.020 | lead 7, team 23 | 39K (screen) | yes: 91/91 tests, 8/8 acceptance, smoke 5/5 |
| e2-A | Balance + end screen and HP bar, 2 teammates | v2; lead Opus 5.5 xhigh, 1h cache | c006911 | 20:57:17-21:02:08 | 0.796 | 0.768 | 0.028 | lead 13, team 44 | 42K (tuner) | yes, after 1 lead fix: 97/97 tests, 7/7 acceptance, smoke ok |
| e2-B | Balance + end screen and HP bar, 2 teammates | v2; lead Sonnet 5.5 medium (cache 1h: 5m not applied) | c006911 | 20:57:24-21:01:03 | 0.301 | 0.274 | 0.027 | lead 7, team 62 | 47K (tuner) | yes, first check: 97/97 tests, 7/7 acceptance, smoke ok |
| e3-A | Monster abilities + legend, 2 teammates | v2.1; Haiku context uncapped | 791875b | 69e643b4 session | 0.208 | 0.181 | 0.028 | lead 6, team 53 | 52K (abilities) | yes, first check |
| e3-B | Monster abilities + legend, 2 teammates | v2.1; Haiku auto-compact at 100K | 791875b | 4f70ac1a session | 0.215 | 0.181 | 0.034 | lead 6, team 53 | 59K (abilities) | yes, first check |
| e4-A | Traps + help overlay, 2 teammates | kit 3.0 (/team skill); full spec | 19369db | a8dfb567 session | 0.191 (cold 0.289) | 0.156 | 0.035 | lead 5, team 41 | 62K (traps) | yes, first check: 128 tests, 35 acceptance, smoke ok |
| e4-B | Traps + help overlay, 2 teammates | kit 3.0 (/team skill); goal only, lead plans | 19369db | 20ab6038 session | 0.267 (cold 0.365) | 0.234 | 0.033 | lead 11, team 53 | 61K (traps) | yes, after 1 lead fix (balance: player hp 30 to 34) |
| e4-C | Traps + help overlay, 2 teammates | kit 3.1; goal only, lead plans | b430470 (base + kit 3.1) | 87a904e7 session | 0.246 (cold 0.345) | 0.202 | 0.044 | lead 8, team 66 | 63K (traps) | yes, first check; but traps changed minDepth outside contract |
| e4-D | Traps + help overlay, 2 teammates | kit 3.2; goal only, lead plans | 003a776 (base + kit 3.2) | 616fa41a session | 0.258 (cold 0.356) | 0.219 | 0.039 | lead 7, team 64 | 56K (traps) | yes, first check; tuning within the contract |
| e5-A | Score, stats + high scores, 2 teammates | kit 3.3; goal only; default lead tools | 55561f3 | 156cf93c session | 0.229 (cold 0.328) | 0.201 | 0.028 | lead 7, team 44 | 51K (summary) | yes, first check |
| e5-B | Score, stats + high scores, 2 teammates | kit 3.4; goal only; `team_kit.py lead` (removal list) | 55561f3 | 9e3c2255 session | 0.255 (cold 0.255) | 0.224 | 0.031 | lead 7, team 53 | 55K (summary) | yes, first check |
| e6-A | Shop (pilot of the plain-prompt flow), 2 teammates | kit 3.6; plain request; `team_kit.py lead` | c560560 | 46038565 session | 0.436 (cold 0.478) | 0.398 | 0.038 | lead 15, team 58 | 54K (ui) | yes, first check (167 tests, 52 acceptance; lead's own tests); staged |

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

### e3 notes

A/B of a 100K auto-compact window for Haiku teammates. Never triggered (peaks 52K/59K), so the
variants were identical in practice: totals within 3%, team cost within 24% (noise level).
A probe showed the cap works after an overrun but can't prevent one turn over 100K.
Adopted as a backstop with a per-turn intake rule (v2.2). Details: `results/runs/e3/`.

### e4 notes

Kit 3.0 (one file, `/team` skill). A: the lead follows a full spec with teammate prompts. B: the
lead gets the goal, the contract sections and the check, and plans with the skill, as in real
use. B costs 26% more at a cold start, all in the lead (11 turns vs 6): 3 turns of planning, and
an extra merge round because its plan didn't tell the balance-sensitive task what it could tune.
"Cold" totals add the cached start-up prefix as if written by the run (new in `team_kit.py
cost`); the e3 runs were also cache-warm (cold: 0.307 and 0.313). Details:
`results/runs/e4/compare-A-B.md`. Main keeps its e3 game code; A's code is on `run/e4/A`.
C (B on kit 3.1, tasks name what they may change) removed B's merge round: lead 8 turns, 6%
cheaper than B, still 19% over A. Its plan gave the balance task too little room, and the
teammate stepped outside it (trap `minDepth`); kit 3.2 addresses both sides.
D (kit 3.2): first check, no fix round, all tuning within the contract, same cost as C. Kit 3.2
adopted: goal-only planning costs about 20-25% more than a full spec, at the same quality.

### e5 notes

Lean lead: `team_kit.py lead` starts the session without the tools a lead never uses (kit 3.4's
removal list; the user preferred it to an allow-list, so new or unknown tools stay). Start-up
prompt 40K to 25K tokens; 22% cheaper at a cold start, same quality. Adopted as the
recommended way to start a team session (a plain session with `/team` still works). A first B
attempt with a `--tools` allow-list never started (the list option swallowed the prompt);
discarded and fixed. Details: `results/runs/e5/compare-A-B.md`.

### e6 notes

Pilot of the user's flow: a new session, a plain request, no prepared contract or tests. With
kit 3.6 the lead loaded the skill, wrote the contract and acceptance tests first, ran the team
and staged the result; first check, real tests. 4 lead turns were lost to a staging-folder bug
in the testbed's `npm run stage` (fixed). Review: `results/runs/e6/review.md`.
