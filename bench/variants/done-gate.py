"""Brief item 3: gate "done" with a hook.

TeammateIdle (it names the teammate): a teammate goes idle only once its handoff exists with
the four sections and its task's done check from plan.md passes; otherwise exit 2 sends it back
with the reason. At most two blocks per teammate, then the lead decides. Logged to
.claude/team/scratch/hooks.log."""
from common import HOOK_CMD, add_hooks

HANDLERS = '''
def done_check(plan, task):
    """The first backticked command after "done" in the plan's section for TASK, if any."""
    if not os.path.exists(plan):
        return None
    m = re.search(rf"^##+ *`?{re.escape(task)}`?\\b[^\\n]*\\n(.*?)(?=^##+ |\\Z)", open(plan).read(),
                  re.M | re.S)
    c = re.search(r"[Dd]one[^`\\n]*`([^`]+)`", m.group(1)) if m else None
    return c.group(1) if c else None


def hook_gate(d):
    """TeammateIdle: idle only with the handoff written and the done check passing."""
    name = d.get("teammate_name")
    if not name:
        return None
    root = d.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    team = os.path.join(root, ".claude", "team")
    state_path = os.path.join(team, "scratch", "gate.json")
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    if state.get(name, 0) >= 2:
        return None
    hand = os.path.join(team, "handoff", name + ".txt")
    text = open(hand).read().lower() if os.path.exists(hand) else ""
    missing = [s for s in ("Done", "In progress", "Next step", "Do not redo") if s.lower() not in text]
    problem, check = None, None
    if missing:
        problem = (f"Write .claude/team/handoff/{name}.txt with its sections "
                   f"({', '.join(missing)} missing) before you finish.")
    else:
        check = done_check(os.path.join(team, "plan.md"), re.sub(r"-\\d+$", "", name))
        if check:
            r = subprocess.run(check, shell=True, cwd=root, capture_output=True, text=True,
                               timeout=170)
            if r.returncode != 0:
                problem = (f"Your done check `{check}` fails:\\n{(r.stdout + r.stderr)[-1500:]}\\n"
                           "Fix it and update your handoff before you finish.")
    log_hook({"hook": "gate", "teammate": name, "check": check, "blocked": bool(problem),
              "problem": (problem or "")[:300]})
    if not problem:
        return None
    state[name] = state.get(name, 0) + 1
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    json.dump(state, open(state_path, "w"))
    return {"exit": 2, "stderr": problem}


HOOKS = {"gate": hook_gate}
'''


def apply(src):
    return add_hooks(src, HANDLERS, '{"TeammateIdle": [{"hooks": [{"type": "command", "command": "'
                     + HOOK_CMD + ' gate", "timeout": 180}]}]}')
