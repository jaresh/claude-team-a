"""Brief item 7: run each wave as a dynamic workflow instead of agent-team teammates.

The lead plans, writes the contract, conventions and tests as now, but launches each wave as one
workflow (parallel() agents on team-dev, with a JSON schema for the result), so the wave's
results reach it as one message instead of one notice per teammate. The kit's settings allow
the Workflow tool, so a background session needn't be asked."""
from common import SETTINGS, rep


def apply(src):
    src = rep(src, SETTINGS, SETTINGS[:-1] + ',\n                "permissions": {"allow": ["Workflow"]}}')
    return rep(src, '''path), and start every task of the wave in parallel with the Agent tool:
`subagent_type: "team-dev"`, `name: "<task>"`, `model: "haiku"`, `effort: "medium"`, prompt:

> You are teammate `<task>`; the lead is the main session. Your task is section `<task>` of
> .claude/team/plan.md; read it and the Contract section. Done when `<done check>` passes.
> Write .claude/team/handoff/<task>.txt before your final message.

Then end the turn. Completion notices wake you: don't poll, sleep, or check on teammates.''',
               '''path), and run every task of the wave as one dynamic workflow, not with the Agent tool.
The first time, load the `workflow-authoring` skill with the Skill tool for the script format.
The script runs the wave's tasks with `parallel()`: one `agent()` per task, on the `team-dev`
agent type with model haiku and effort medium, a label naming the task, this prompt, and a
schema for `{"task": string, "check_passed": boolean, "handoff": string}`:

> You are teammate `<task>`; the lead is the main session. Your task is section `<task>` of
> .claude/team/plan.md; read it and the Contract section. Done when `<done check>` passes.
> Write .claude/team/handoff/<task>.txt before your final message.

Launch it with the Workflow tool, then end the turn: the wave's results come back as one message
when every agent has finished. Don't poll, sleep, or check on the agents.''')
