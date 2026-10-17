| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.191 | 0.258 | +35% |
| Total $, cold start | 0.289 | 0.356 | +23% |
| Lead $ | 0.156 | 0.218 | +40% |
| Team $ | 0.035 | 0.039 | +14% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.049 | 0.074 | +50% |
| Lead cache write $ | 0.088 | 0.116 | +32% |
| Lead output $ | 0.019 | 0.028 | +49% |
| Lead messages | 6 | 8 | +33% |
| Lead tool calls | 5 | 7 | +40% |
| Lead output tokens | 1894 | 2815 | +49% |
| Lead start-up prompt | 40K | 40K | +1% |
| Lead peak context | 48K | 55K | +15% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 41 | 64 | +56% |
| Team peak context | 62K | 56K | -11% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e4-A.json lead=sonnet effort=medium cache=1h
B: results/metrics/e4-D.json lead=sonnet effort=medium cache=1h
