"""Brief item 2: enforce the teammates' per-turn intake rule with a PreToolUse hook.

For teammates only: a Read without a limit on a file over 60 KB gets limit 600, and a test
command whose output isn't already piped or redirected runs through `tail -n 40` (with
pipefail, so its exit status is kept). Every change is logged to .claude/team/scratch/hooks.log."""
from common import HOOK_CMD, add_hooks

HANDLERS = '''
TEST_CMD = re.compile(r"\\b(unittest|pytest|npm( run)? test|node --test|go test|cargo test|make test)\\b")


def hook_intake(d):
    """PreToolUse for teammates: page large Reads, keep test output short."""
    if not d.get("agent_id") or d.get("agent_type", "team-dev") != "team-dev":
        return None
    tool, inp = d.get("tool_name"), dict(d.get("tool_input") or {})
    if tool == "Read" and not inp.get("limit"):
        path = inp.get("file_path", "")
        if not (os.path.isfile(path) and os.path.getsize(path) > 60_000):
            return None
        inp["limit"] = 600
    elif tool == "Bash":
        cmd = inp.get("command", "")
        if not TEST_CMD.search(cmd) or "|" in cmd or ">" in cmd:
            return None
        inp["command"] = f"set -o pipefail; ( {cmd} ) 2>&1 | tail -n 40"
    else:
        return None
    log_hook({"hook": "intake", "agent": d.get("agent_type"), "tool": tool, "input": inp})
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                   "updatedInput": inp}}


HOOKS = {"intake": hook_intake}
'''


def apply(src):
    return add_hooks(src, HANDLERS, '{"PreToolUse": [{"matcher": "Read|Bash", "hooks": '
                     '[{"type": "command", "command": "' + HOOK_CMD + ' intake", "timeout": 10}]}]}')
