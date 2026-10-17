| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.246 | 0.258 | +5% |
| Total $, cold start | 0.345 | 0.356 | +3% |
| Lead $ | 0.202 | 0.218 | +8% |
| Team $ | 0.044 | 0.039 | -11% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.070 | 0.074 | +6% |
| Lead cache write $ | 0.107 | 0.116 | +9% |
| Lead output $ | 0.025 | 0.028 | +13% |
| Lead messages | 8 | 8 | +0% |
| Lead tool calls | 8 | 7 | -12% |
| Lead output tokens | 2501 | 2815 | +13% |
| Lead start-up prompt | 40K | 40K | +0% |
| Lead peak context | 53K | 55K | +4% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 66 | 64 | -3% |
| Team peak context | 63K | 56K | -12% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e4-C.json lead=sonnet effort=medium cache=1h
B: results/metrics/e4-D.json lead=sonnet effort=medium cache=1h
