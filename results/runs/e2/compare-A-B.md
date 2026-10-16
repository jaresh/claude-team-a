| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.796 | 0.301 | -62% |
| Lead $ | 0.768 | 0.274 | -64% |
| Team $ | 0.028 | 0.027 | -5% |
| Lead model | opus-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.116 | 0.054 | -54% |
| Lead cache write $ | 0.513 | 0.199 | -61% |
| Lead output $ | 0.139 | 0.021 | -85% |
| Lead messages | 12 | 7 | -42% |
| Lead tool calls | 13 | 7 | -46% |
| Lead output tokens | 6938 | 2112 | -70% |
| Lead peak context | 64K | 50K | -22% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 44 | 62 | +41% |
| Team peak context | 42K | 47K | +10% |
| Team messages over 100K | 0 | 0 |  |

A: results/metrics/e2-A.json lead=opus effort=xhigh cache=1h
B: results/metrics/e2-B.json lead=sonnet effort=medium cache=5m

## Verdict (planning session)

Rules v2's run lead (Sonnet 5.5, effort medium) built the same feature for 62% less than the v1
lead (Opus 5.5, xhigh): output tokens -70%, messages -42%, lower prices on every part. B passed
acceptance on the first check; A needed one lead fix, caused by `hud`'s DOM order and
`smoke.mjs` tapping a hidden button (smoke now taps visible buttons only). Adopted: rules v2.

Caveat: B's label says `cache=5m`, but the background session didn't inherit
`CLAUDE_CODE_PROMPT_CACHE_TTL`, so both variants used 1-hour cache writes. The comparison
measures model and effort only. `kit/run.sh` now passes the TTL with `--settings` (checked with
a probe). n = 1 per variant; the gap is far above the ~20% noise threshold.
