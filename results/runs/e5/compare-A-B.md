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

## Verdict

B (`team_kit.py lead`, kit 3.4 removal list) is adopted. Quality first: both were accepted on
the first check with no fix round; B's teammates changed only the files its plan gave them, and
its lead made no call to a missing tool. Cost: B is 22% cheaper at a cold start ($0.255 vs
$0.328). Its start-up prompt was 25K tokens against 40K, its peak 38K against 52K, and its
cache reads 36% lower. The plain totals point the other way (+11%) only because A's start-up
prefix happened to be cached already, while B's leaner prefix was written fresh.

One teammate handoff write (`handoff/summary.md`, by `summary`) was refused by a Claude Code
guard ("Subagents should return findings as text, not write report files"). That doesn't depend
on the lead's tools. The lead wrote the handoff from the report, as the skill says. Kit 3.5: a
teammate whose handoff write is refused puts the four sections in its final message.
