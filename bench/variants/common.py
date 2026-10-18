"""Helpers the variants share: an exact, single-match replace, and the kit's hook entry point."""


def rep(src, old, new):
    assert src.count(old) == 1, f"expected one match, found {src.count(old)}: {old[:60]!r}"
    return src.replace(old, new)


SETTINGS = '''SETTINGS_ADD = {"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"},
                "modelSettings": {"claude-haiku-5-5": {"autoCompactWindow": 100000}}}'''

# `team_kit.py hook NAME` reads a hook's JSON input on stdin and runs HOOKS[NAME]. A handler
# returns None (let it through), a JSON object to print, or {"exit": 2, "stderr": ...}.
HOOK_ENTRY = '''
def hook(argv):
    """Run the kit's hook ARGV[0] on the JSON input on stdin. Fail-soft: on any error the call
    goes through as if there were no hook."""
    try:
        out = HOOKS[argv[0]](json.load(sys.stdin)) if argv and argv[0] in HOOKS else None
    except Exception as e:   # a hook bug must never block the session
        log_hook({"hook": argv[:1], "error": repr(e)})
        out = None
    if out and out.get("exit") == 2:
        print(out["stderr"], file=sys.stderr)
        sys.exit(2)
    print(json.dumps(out or {}))


def log_hook(entry):
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        os.makedirs(os.path.join(root, ".claude/team/scratch"), exist_ok=True)
        with open(os.path.join(root, ".claude/team/scratch/hooks.log"), "a") as f:
            f.write(json.dumps(entry) + "\\n")
    except OSError:
        pass

'''


def add_hooks(src, handlers, hooks_setting):
    """Add the hook entry point, the handlers (source text ending with a HOOKS dict), the
    `hook` subcommand, and the hooks to SETTINGS_ADD."""
    src = rep(src, "def status(repo):", HOOK_ENTRY + handlers + "\n\ndef status(repo):")
    src = rep(src, '''    if len(sys.argv) > 1 and sys.argv[1] == "request":
        return request()''', '''    if len(sys.argv) > 1 and sys.argv[1] == "request":
        return request()
    if len(sys.argv) > 1 and sys.argv[1] == "hook":
        return hook(sys.argv[2:])''')
    return rep(src, SETTINGS, SETTINGS[:-1] + ",\n                \"hooks\": " + hooks_setting + "}")


HOOK_CMD = 'python3 \\"$CLAUDE_PROJECT_DIR/.claude/skills/team/team_kit.py\\" hook'
