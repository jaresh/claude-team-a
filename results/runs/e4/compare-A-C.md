| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.191 | 0.246 | +29% |
| Total $, cold start | 0.289 | 0.345 | +19% |
| Lead $ | 0.156 | 0.202 | +29% |
| Team $ | 0.035 | 0.044 | +27% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.049 | 0.070 | +42% |
| Lead cache write $ | 0.088 | 0.107 | +22% |
| Lead output $ | 0.019 | 0.025 | +32% |
| Lead messages | 6 | 8 | +33% |
| Lead tool calls | 5 | 8 | +60% |
| Lead output tokens | 1894 | 2501 | +32% |
| Lead start-up prompt | 40K | 40K | +0% |
| Lead peak context | 48K | 53K | +10% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 41 | 66 | +61% |
| Team peak context | 62K | 63K | +2% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e4-A.json lead=sonnet effort=medium cache=1h
B: results/metrics/e4-C.json lead=sonnet effort=medium cache=1h
