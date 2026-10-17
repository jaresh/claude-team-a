| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.267 | 0.246 | -8% |
| Total $, cold start | 0.365 | 0.345 | -6% |
| Lead $ | 0.234 | 0.202 | -14% |
| Team $ | 0.033 | 0.044 | +33% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.099 | 0.070 | -29% |
| Lead cache write $ | 0.105 | 0.107 | +2% |
| Lead output $ | 0.030 | 0.025 | -16% |
| Lead messages | 11 | 8 | -27% |
| Lead tool calls | 11 | 8 | -27% |
| Lead output tokens | 2964 | 2501 | -16% |
| Lead start-up prompt | 40K | 40K | +0% |
| Lead peak context | 52K | 53K | +1% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 53 | 66 | +25% |
| Team peak context | 61K | 63K | +4% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e4-B.json lead=sonnet effort=medium cache=1h
B: results/metrics/e4-C.json lead=sonnet effort=medium cache=1h
