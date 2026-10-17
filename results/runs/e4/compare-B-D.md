| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.267 | 0.258 | -3% |
| Total $, cold start | 0.365 | 0.356 | -3% |
| Lead $ | 0.234 | 0.218 | -7% |
| Team $ | 0.033 | 0.039 | +18% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.099 | 0.074 | -25% |
| Lead cache write $ | 0.105 | 0.116 | +10% |
| Lead output $ | 0.030 | 0.028 | -5% |
| Lead messages | 11 | 8 | -27% |
| Lead tool calls | 11 | 7 | -36% |
| Lead output tokens | 2964 | 2815 | -5% |
| Lead start-up prompt | 40K | 40K | +1% |
| Lead peak context | 52K | 55K | +5% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 53 | 64 | +21% |
| Team peak context | 61K | 56K | -8% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e4-B.json lead=sonnet effort=medium cache=1h
B: results/metrics/e4-D.json lead=sonnet effort=medium cache=1h
