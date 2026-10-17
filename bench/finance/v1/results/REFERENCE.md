# Finance benchmark: reference results (prompt v1, version 71e981f2a7dc)

First pair, 2026-10-17: the same prompt (`bench/finance/prompt.md`) built by the team (kit 3.6,
`team_kit.py lead` flags) and by Sonnet alone (no subagents), both Sonnet 5.5 at effort
medium with the 1-hour cache, scored with the 25 hidden tests. Later runs compare against
these with `bench/compare.py bench/finance/results/20261017T090429Z-solo bench/finance/results/20261017T090404Z-team <new run>`.

| Metric |  |  |
|---|---|---|
| Run | 20261017T090429Z-solo | 20261017T090404Z-team |
| Mode | solo | team |
| Model / effort | sonnet / medium | sonnet / medium |
| Prompt version | 71e981f2a7dc | 71e981f2a7dc |
| Hidden tests passed | 25/25 | 25/25 |
| Own tests passed | 18/18 | 36/36 |
| Python lines | 1218 | 1513 |
| Total $ | 0.626 | 0.430 |
| Total $, cold start | 0.626 | 0.472 |
| Lead / solo $ | 0.626 | 0.355 |
| Team $ | 0.000 | 0.074 |
| Teammates | 0 | 3 |
| Lead / solo messages | 9 | 9 |
| Lead / solo peak context | 57K | 47K |
| Lead / solo compactions | 0 | 0 |
| Team peak context | 0K | 58K |
| Wall time | 09:04-09:08 | 09:04-09:10 |

- **Same quality.** Both passed all 25 hidden tests and their own tests; the team wrote twice
  as many tests (36 vs 18) and 24% more code.
- **Team 25% cheaper at a cold start.** The saving is output tokens: Sonnet alone wrote 33K
  output tokens ($0.33, half its cost); the team lead wrote 14K (the shared core module, the
  plan, three prompts), and three Haiku teammates wrote 76K for $0.074 together. The leads'
  context and turns were about the same (9 messages each).
- **Team flow.** The lead wrote `fin/core.py` (storage, accounts, transactions) itself, ran its
  tests, wrote the plan, and started `importer`, `reports` and `server` in parallel; one merge
  check passed. No teammate came near its budget (peak 59K), so there were no successors.
  `reports` left no handoff file (importer and server did); nothing depended on it.
- **Smaller than intended.** Solo finished in 9 turns and 4 minutes with a 57K peak context;
  the team took 6 minutes. A bigger benchmark would be needed to make teammates hand off to
  successors and to see how both arms scale.
