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
