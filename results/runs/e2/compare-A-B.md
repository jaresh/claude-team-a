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
