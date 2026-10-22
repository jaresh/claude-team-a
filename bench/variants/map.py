"""Navigation map: the lead generates .claude/team/map.md (team_kit.py map: files, line counts and
definitions with line numbers, sized to about 6K tokens) before planning, plans from it instead of
exploring, and gives each teammate the map lines of the files it owns plus the read-by-name rule.
The `map` command is in the kit; this variant wires it into the SKILL and the teammate, and keeps
it fresh: a PostToolUse hook on Edit, Write, MultiEdit and Bash runs `map --quiet`, which rebuilds
the file only when a source file is newer than it (hooks live in settings.local.json, ignored)."""
from common import SETTINGS as SETTINGS_OLD, rep


def apply(src):
    cmd = 'python3 \\"$CLAUDE_PROJECT_DIR/.claude/skills/team/team_kit.py\\" map --quiet'
    src = rep(src, SETTINGS_OLD, SETTINGS_OLD[:-1] + ',\n                "hooks": {"PostToolUse": [{"matcher": "Edit|Write|MultiEdit|Bash", "hooks": [{"type": "command", "command": "' + cmd + '"}]}]}}')
    a = '''| `plan.md` | goal, check, contract, one section per task (the current task only) |'''
    src = src.replace(a, a + '''
| `map.md` | files and their definitions with line numbers (generated; refresh after big edits) |''', 1)
    b = "Otherwise read only what planning needs:"
    assert b in src
    src = src.replace(b, '''Start with `python3 .claude/skills/team/team_kit.py map` and read `.claude/team/map.md`: it
lists every source file with its definitions and line numbers, so you find code by name with
`grep -n` and read ranges, not whole files. In each task section of the plan, copy the map lines
of the files the task owns or reads. An empty or tiny repo needs no map.

''' + b, 1)
    c = "- Keep command output small:"
    assert c in src
    src = src.replace(c, '''- Navigate by name: your task section has the map lines of your files. Find a definition with
  `grep -n 'name' file`, read it with `sed -n 'A,Bp' file`; open a whole file only when the
  task is about all of it. The map is rebuilt after edits, but your own line numbers drift
  as you edit: re-find with `grep -n`.
''' + c, 1)
    return src
