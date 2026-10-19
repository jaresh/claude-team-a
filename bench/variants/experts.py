"""Specialized teammates: a few experts, each holding one area of the spec, kept across tasks.

At planning the lead groups the work into experts (core, domain engine, feature families, API)
plus a `tester`, and writes each a brief with `team_kit.py brief`: the expert's own sections and
every section of spec-wide rules, copied word for word from .claude/team/spec.md (no lead output
tokens). The text before the first heading stays with the lead: in a benchmark it holds the
end-of-run instruction, which a teammate must not follow. Every task names its expert; an expert's later
tasks go to the same teammate by SendMessage, so it doesn't read its brief and files again. The
tester writes acceptance tests from the spec alone in the first wave; after the last wave the
lead runs them and sends each failure to the expert that owns the code."""
from common import rep

BRIEF = '''
def brief(argv):
    """Write .claude/team/experts/NAME.md: the named sections of the spec, word for word. brief
    NAME [--from FILE] (--all | HEADING...); a HEADING matches every section whose heading starts
    with it ("Conventions", "4." but not "14."). The text before the first heading (the
    request's opening, meant for the lead) is left out; --all takes every section."""
    if not argv or argv[0].startswith("-"):
        sys.exit("usage: team_kit.py brief NAME [--from FILE] (--all | HEADING...)")
    name, rest = argv[0], argv[1:]
    src = ".claude/team/spec.md"
    if "--from" in rest:
        i = rest.index("--from")
        src, rest = rest[i + 1], rest[:i] + rest[i + 2:]
    root = repo_root(".")
    path = src if os.path.isabs(src) else os.path.join(root, src)
    if not os.path.exists(path):
        sys.exit(f"No {src}: run `team_kit.py request` first, or name the spec with --from.")
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
    title = "# The user's request, word for word"
    start = 1 if lines and lines[0].startswith(title) else 0
    heads, fence = [], False   # (line, level, text) of each heading outside code fences
    for i in range(start, len(lines)):
        if lines[i].lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"(#{1,6})\\s+(.*)", lines[i])
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    def starts(text, pat):   # "1." and "1" match "1. Setup", never "14. HTTP API"
        text, pat = text.lower(), pat.lower()
        return text.startswith(pat) and not (pat[-1:].isdigit() and text[len(pat):][:1].isdigit())

    if "--all" in rest:
        picked = [(heads[0][0] if heads else start, len(lines))]
        names = ["every section"]
    elif not rest:
        sys.exit("Name at least one heading, or --all.")
    else:
        picked, names = [], []
        for pat in rest:
            hits = [h for h in heads if starts(h[2], pat)]
            if not hits:
                sys.exit(f"No heading starts with {pat!r}. Headings: "
                         + "; ".join(t for _, _, t in heads))
            for i, level, text in hits:
                end = next((j for j, lv, _ in heads if j > i and lv <= level), len(lines))
                picked.append((i, end))
                names.append(text)
    keep = sorted({k for a, b in picked for k in range(a, b)})
    rel = f".claude/team/experts/{name}.md"
    body = (f"# Brief: {name}\\n\\nFrom {src}, word for word: " + "; ".join(names) + ".\\n\\n"
            + "".join(lines[k] for k in keep).strip() + "\\n")
    write(os.path.join(root, rel), body)
    print(f"Wrote {rel}: {'every section' if '--all' in rest else f'{len(names)} section(s)'}, "
          f"{len(body.split())} words.")

'''


def apply(src):
    src = rep(src, "def status(repo):", BRIEF + "\ndef status(repo):")
    src = rep(src, '''    if len(sys.argv) > 1 and sys.argv[1] == "request":
        return request()''', '''    if len(sys.argv) > 1 and sys.argv[1] == "request":
        return request()
    if len(sys.argv) > 1 and sys.argv[1] == "brief":
        return brief(sys.argv[2:])''')
    src = rep(src, '''    sub.add_parser("request", help="in a session: save the user's messages to .claude/team/spec.md")''',
              '''    sub.add_parser("request", help="in a session: save the user's messages to .claude/team/spec.md")
    sub.add_parser("brief", help="write an expert's brief from the spec: brief NAME (--all | HEADING...)",
                   add_help=False)''')

    # Plan: experts and the tester
    src = rep(src, '''  modules written by different teammates read as one codebase.
- **Tasks**, as many as the work needs,''', '''  modules written by different teammates read as one codebase.
- **Experts**: a few teammates, each the expert on one area of the work (for example the shared
  core, the domain engine, each family of features, the API or UI layer), who keep their area's
  knowledge across all its tasks. Every task belongs to one expert (`expert: <name>` in its
  section), and an expert's later tasks go to the same teammate (step 2). Unless the user gave
  the check, add a `tester` expert to the first wave: it writes acceptance tests from the spec
  alone (rules that cross areas, permissions, errors and robustness, every output detail the
  spec states, its general rules included), never reads the implementation, and changes no app
  code. Its done check is that its tests load and run; they fail until the code exists.
- **Tasks**, as many as the work needs,''')
    src = rep(src, '''word for word, so you never retype them. Make sure every file the plan or a prompt names
exists.''', '''word for word, so you never retype them. Then give each expert its brief, all in one Bash call:
`python3 .claude/skills/team/team_kit.py brief <expert> <heading>...` copies every section whose
heading starts with those words (`Conventions`, `4.`), word for word, into
`.claude/team/experts/<expert>.md` (`--from <file>` for a spec file the user named).
Name the sections the expert owns and every section of rules that apply everywhere
(conventions, formats, errors, permissions), so no expert misses a spec-wide rule; the tester
gets `--all`. Append, with `>>`, the few lines the spec can't give: the expert's files and the
Contract and Conventions parts it uses. Make sure every file the plan or a prompt names exists.''')

    # Run a wave: experts by name, reused by message
    src = rep(src, '''`subagent_type: "team-dev"`, `name: "<task>"`, `model: "haiku"`, `effort: "medium"`, prompt:

> You are teammate `<task>`; the lead is the main session. Your task is section `<task>` of
> .claude/team/plan.md; read it and the Contract section. Done when `<done check>` passes.
> Write .claude/team/handoff/<task>.txt before your final message.

Then end the turn. Completion notices wake you: don't poll, sleep, or check on teammates.''',
              '''`subagent_type: "team-dev"`, `name: "<expert>"`, `model: "haiku"`, `effort: "medium"`, prompt:

> You are teammate `<expert>`, the team's expert on <area>; the lead is the main session.
> Read your brief, .claude/team/experts/<expert>.md: it is the spec for your area. Your task
> is section `<task>` of .claude/team/plan.md; read it and the Contract section. Done when
> `<done check>` passes. Write .claude/team/handoff/<task>.txt before your final message.

Then end the turn. Completion notices wake you: don't poll, sleep, or check on teammates.

An expert that has handed back keeps what it has read. Give it its next task with SendMessage
(to `<expert>`: the task section, its done check and its handoff path) instead of starting a
new teammate, so it doesn't read its brief and files again. Start a fresh one (`<expert>-2`,
the same brief and prompt) only when its last completion notice shows more than about 60K
tokens.''')

    # Merge: the tester's tests after the last wave
    src = rep(src, '''- Then the next wave; after the last one, step 4 or 5.''',
              '''- Then the next wave. After the last one, run the tester's tests on the merged code. For each
  failure, read the spec: where the code is wrong, send the fix to the expert that owns that
  code (SendMessage, all its failures in one message); where the test misreads the spec, fix or
  drop the test. When those fixes are back, run the check, the tester's tests included, once
  more. Then step 4 or 5.''')

    # The teammate: brief first, later tasks by message
    src = rep(src, '''do it, write a handoff, and stop. Never start another task on your own. The team's working
files are in `.claude/team/`.''',
              '''do it, write a handoff, and stop. Never start another task on your own. If you are one of the
team's experts, the lead may message you your next task in your area later: do it the same way,
without re-reading what you already know (your brief, the contract, files unchanged since). The
team's working files are in `.claude/team/`.''')
    return rep(src, '''- Change only the files your task names. Read only what you need: your task, the contract, the
  files you change, and any handoff your task names. A successor (`<task>-2`) reads the handoff
  and the files it names.''',
               '''- Change only the files your task names. Read only what you need: your brief if your prompt
  names one, your task, the contract, the files you change, and any handoff your task names. A
  successor (`<task>-2`) reads the handoff and the files it names.''')
