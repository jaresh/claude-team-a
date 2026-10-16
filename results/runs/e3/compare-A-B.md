| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.208 | 0.215 | +3% |
| Lead $ | 0.181 | 0.181 | -0% |
| Team $ | 0.028 | 0.034 | +24% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.059 | 0.060 | +0% |
| Lead cache write $ | 0.099 | 0.097 | -2% |
| Lead output $ | 0.023 | 0.024 | +6% |
| Lead messages | 7 | 7 | +0% |
| Lead tool calls | 6 | 6 | +0% |
| Lead output tokens | 2266 | 2406 | +6% |
| Lead peak context | 51K | 50K | -1% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 53 | 53 | +0% |
| Team peak context | 52K | 59K | +12% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e3-A.json lead=sonnet effort=medium cache=1h
B: results/metrics/e3-B.json lead=sonnet effort=medium cache=1h extra={"modelSettings":{"claude-haiku-5-5":{"autoCompactWindow":100000}}}

## Verdict (planning session)

The 100K auto-compact window for Haiku teammates never triggered: peaks of 52K (A) and 59K (B),
no compactions, no message over 100K. With the cap otherwise unused, the two variants were the
same configuration, so this run doubles as a noise measurement: totals differ by 3%, team cost by
24% (`abilities` tuned for more iterations in B).

A separate probe (`results/runs/e3/probe.md`) showed the cap reaches teammates and compacts after
an overrun, but can't stop a single turn from crossing 100K: ten parallel 500-line reads took a
teammate from 18K to 242K in one step, and that turn alone cost $0.14 at the 5x rate.

Adopted in rules v2.2: the cap as a backstop in `kit/settings/settings.json` (cost: nothing when
unused), plus a per-turn intake limit for teammates, which is the actual protection. Main has B's
code (win rate 29.5%; A's 15.5% sat at the floor).
