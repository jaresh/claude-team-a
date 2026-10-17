| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.229 | 0.255 | +11% |
| Total $, cold start | 0.328 | 0.255 | -22% |
| Lead $ | 0.201 | 0.224 | +12% |
| Team $ | 0.028 | 0.031 | +8% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.070 | 0.045 | -36% |
| Lead cache write $ | 0.103 | 0.154 | +49% |
| Lead output $ | 0.027 | 0.025 | -7% |
| Lead messages | 8 | 8 | +0% |
| Lead tool calls | 7 | 7 | +0% |
| Lead output tokens | 2737 | 2542 | -7% |
| Lead start-up prompt | 40K | 25K | -37% |
| Lead peak context | 52K | 38K | -26% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 44 | 53 | +20% |
| Team peak context | 51K | 55K | +8% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e5-A.json lead=sonnet effort=medium cache=1h
B: results/metrics/e5-B.json lead=sonnet effort=medium cache=1h args=--disallowedTools=Artifact,ArtifactComments,ArtifactData,DesignSync,SendFeedback,ReportFindings,ReadNotifications,FetchInboxMessage,EndConversation,mcp__claude_ai_Gmail
