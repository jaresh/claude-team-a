#!/usr/bin/env python3
"""Team kit for Claude Code: a lead skill and a Haiku teammate agent, in one file.

Install it into a repo, then in a Claude Code session there type `/team <task>` (or ask for "the
team"). The session's model is the lead: it plans, splits the work into bounded tasks, runs
`team-dev` teammates (Haiku 5.5, effort medium) in parallel, merges and checks. Everything goes
into the repo's `.claude/` and is hidden from git through `.git/info/exclude`, so the repo's
tracked files, `.gitignore` and `CLAUDE.md` stay as they are.

  python3 team_kit.py install [REPO] [--force]       install or update (default REPO: cwd)
  python3 team_kit.py uninstall [REPO] [--keep-work] remove everything install added
  python3 team_kit.py status [REPO]                  what is installed
  python3 team_kit.py lead [TASK] [--deny NAMES] [-- CLAUDE_ARGS]
                                                     start a lean lead session on /team TASK
  python3 team_kit.py cost [--session ID] [...]      tokens and USD per agent of a session
                                                     (default: the latest one; cost --help)
  python3 team_kit.py request                        in a session: save the user's messages
                                                     to .claude/team/spec.md, word for word

Installed files (all git-ignored):

  .claude/skills/team/SKILL.md     the lead's playbook, loaded when the team is asked for
  .claude/skills/team/team_kit.py  a copy of this file (request, cost, status, uninstall)
  .claude/agents/team-dev.md       the teammate: Haiku, effort medium, its rules in its body
  .claude/rules/team.md            three lines, always loaded: a team request loads the skill
  .claude/settings.local.json      + agent teams on, Haiku auto-compact at 100K (merged)
  .claude/team/                    working files: plan, status, change log, handoffs, scratch

Restart Claude Code sessions that are already open in the repo to pick up the settings.
`lead` is optional: it starts `claude` without the tools a team lead never uses (LEAD_DENY:
artifacts and design, feedback and review reports, outside messages, the Gmail connector),
which cuts the start-up prompt the lead re-reads every turn from about 38K to 24K tokens.
Everything else stays, including tools and connectors this list doesn't know. `--deny A,B`
removes more; other claude flags (`--model`, ...) go after `--`; `lead --print-args` prints
the flags, for scripts.
Cost notes: the lead re-reads its whole context every turn, so a fresh session for a big team
task is cheaper than a long one; a Sonnet lead costs much less than Opus for a well-defined task.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime

KIT_VERSION = "3.12"

SKILL = """\
---
name: team
description: Lead an agent team of Haiku teammates on a coding task - clarify it, plan it, split it into bounded parallel tasks, run them, merge, test, deploy to staging when asked, and report. Use whenever the user asks to work with the team, teammates or an agent team, in any words ("work with team on it", "use the team", /team).
---

# Lead the team

You are the lead (this session); your teammates are `team-dev` agents on Haiku 5.5 at effort
medium. Aim: the user's task done and checked, at low token cost. You re-read your whole context
on every turn, so your context size and your number of turns cost more than the teammates do:
keep your turns few and your reads small. Put independent steps in one turn: several commands in
one Bash call, or parallel tool calls.

Working files, all in `.claude/team/` (git-ignored):

| File | What |
|---|---|
| `plan.md` | goal, check, contract, one section per task (the current task only) |
| `status.md` | one row per teammate and per heavy job (the current task only) |
| `changes.md` | one line per edit to a shared file; teammates append |
| `handoff/<name>.txt` | each teammate's handoff |
| `scratch/<name>/` | each teammate's scratch files |

## 1. Plan

If the user names a spec or plan file, follow it instead: it replaces this step, and its
teammate prompts are used word for word.

Otherwise read only what planning needs: the repo's CLAUDE.md or README for build, test and
deploy commands, the files the task touches, and the parts of any contract or spec that the
checks depend on (targets, allowed changes). Read with `grep`, `head` and line ranges, not
whole large files.

If the request leaves a choice that is the user's (what the feature does, where it goes, what
"done" means), ask once, all questions together, before planning. If no one can answer, decide,
and list your assumptions in the plan and in your report.

Then overwrite `.claude/team/plan.md` with:

- **Goal** in two or three lines, and the **Check**: one command that decides "done" (the
  repo's tests, a build, a lint, or tests you write first).
- **Contract**: what tasks working in parallel must agree on (function signatures, data shapes,
  file formats), exact enough that they fit together without talking to each other.
- **Conventions**: the shared module(s) for code more than one task needs (validation, parsing,
  rounding and formatting, errors, command-line or request handling), which you write and test
  before the team starts, and the rules every task follows (naming, how options, errors and
  output are handled). Teammates import the shared code and never write their own version, so
  modules written by different teammates read as one codebase.
- **Tasks**, as many as the work needs, one section each, headed `## <task>`: the files it owns (no file in
  two tasks), what to do, what it may change to make its checks pass (all the tuning a contract
  allows for those checks, not a subset), its done check (one command, under a minute, that includes every
  existing check the task must keep passing), and what it must not touch. A teammate that isn't
  told what it may change stops and asks, which costs you a merge round. A task fits one
  teammate's ~100K-token context: a few files, one module.
  Work that needs another task's result goes in a later wave, and so does a layer over other
  tasks' code (an HTTP API over the commands, a UI over an API), so its tests run against the
  real code. Use names not already in `handoff/`. Name tasks after what they build (`ledger`,
  `invoices`); avoid names with "report", "summary", "review" or "analysis": Claude Code refuses
  Markdown files written by subagents named like that.

Teammates see only files, never this conversation. When tasks need more of the user's request
than the plan quotes, run `python3 .claude/skills/team/team_kit.py request` before the first
wave: it copies the user's messages from this session's transcript to `.claude/team/spec.md`,
word for word, so you never retype them. Make sure every file the plan or a prompt names
exists.

Tests first: unless the user gave a check, write acceptance tests for the contract, each
interface between tasks included, in the repo's test layout, before starting the team, and run
them once to see them fail. They are yours: teammates don't edit them, and they add unit tests
for their own code. Never give a test helper the name of a test-framework method (in unittest:
`fail`, `assert...`, `setUp`, `run`, `skipTest`): the framework calls its own, and a shadowed
`fail` turns every failing assertion into a pass.

Tell the user the plan in a few lines.

## 2. Run a wave

In one turn: update `status.md` (for the first wave, overwrite it with a row per task in the
plan, later waves included as `waiting`: name, task, model, state, handoff path), and start every task of the wave in parallel with the Agent tool:
`subagent_type: "team-dev"`, `name: "<task>"`, `model: "haiku"`, `effort: "medium"`, prompt:

> You are teammate `<task>`; the lead is the main session. Your task is section `<task>` of
> .claude/team/plan.md; read it and the Contract section. Done when `<done check>` passes.
> Write .claude/team/handoff/<task>.txt before your final message.

Then end the turn. Completion notices wake you: don't poll, sleep, or check on teammates.

If the user asks for one teammate at a time, every wave has one task, in an order where each
task builds on the code before it. It takes about twice as long and gives more consistent
code. A task that reuses earlier code must still follow the spec where that code does more than
the task needs: reusing it unchanged can add a check the spec doesn't ask for.

## 3. Merge and check

When every teammate of the wave has handed back, in one turn: read `changes.md` and each
handoff's Done and Next step (the rest only when a decision needs it), update `status.md`, and
run the check once on the merged result. Teammates' reports aren't trusted until it passes.
A logged change outside a task's permissions is a design decision: revert it, or keep it and
say so in your report.

- If it fails: one fix round. Fix a small problem yourself, or start a successor (`<task>-2`,
  then `-3`) whose prompt names the handoff and the failing output. A successor reads the
  handoff and the files it names, not the old transcript.
- If a handoff is missing, write it from the teammate's report before starting a successor.
- Then the next wave; after the last one, step 4 or 5.

## 4. Deploy (only when the user asked)

Use the repo's documented staging deploy (README, CLAUDE.md, docs, package scripts, Makefile),
never production. It is a heavy job: you run it, after the check passes, then verify the
deployed copy with its smoke or health check. If no staging deploy is documented, ask the user
how; if no one can answer, skip it and say so.

## 5. Finish

Finish only when every row in `status.md` is done and every teammate has handed back. Then
update `status.md` and report to the user, in under 200 words, so they can assess the work:
what changed (paths), how to try it (staging URL and steps), the tests added and the check
result, your assumptions, what is still open, and how to undo it. Don't commit, even at the
end: leave the changes in the working tree for the user to review, unless they asked you to
commit.

## Rules

- **Model.** Every helper you start is a teammate: `team-dev` on Haiku at effort medium,
  for research and exploring too. Don't start Explore, Plan or other agent types, which run on
  bigger models, and never start a teammate on another model; raise the effort only when the
  user asks. Without `team-dev`, use `general-purpose` with `model: "haiku"`.
- **Budget.** A teammate's budget is its context, about 100K tokens; above that Haiku costs 5x
  per token. Size tasks to fit. Completion notices show the tokens used; a teammate that ran
  out hands off, and you start a successor.
- **Heavy jobs** (longer than about a minute, or holding a shared resource such as a server, a
  device or a benchmark machine): only you run them, one at a time per resource, each with a row
  in `status.md` (output file, done check). Teammates run quick checks only.
- **Measurements.** Before and after numbers use the same input list, written once to a file.
  Try a small sample before a full run. Generated output goes to a new empty folder; never
  overwrite a baseline someone is measuring against.
- **Reading.** Don't read teammates' transcripts: read their handoffs and the files they name.
  Ask for counts and paths, not logs. Don't re-read a file you just wrote, and don't repeat a
  check that a handoff already reports.
- **Stopping.** A teammate that has handed back is already stopped: no TaskStop. Use TaskStop
  only on one that is still running and must not continue.
- **Cost.** After the session, `python3 .claude/skills/team/team_kit.py cost` reports its tokens
  and USD per agent. Don't measure a session from inside itself.
"""

AGENT = """\
---
name: team-dev
description: Teammate for one bounded coding task from the team lead (the /team skill). Haiku at effort medium, file and shell tools only.
tools: Read, Write, Edit, Bash, Glob, Grep
model: haiku
effort: medium
---

You are a teammate on an agent team. The lead (the main session) gives you one bounded task: you
do it, write a handoff, and stop. Never start another task on your own. The team's working
files are in `.claude/team/`.

## Scope

- Change only the files your task names. Read only what you need: your task, the contract, the
  files you change, and any handoff your task names. A successor (`<task>-2`) reads the handoff
  and the files it names.
- If another teammate's file looks wrong, say so in your handoff; don't edit it.
- Follow the plan's Conventions: import the shared helpers it names and never write your own
  version of one. If you need a helper that doesn't exist, write it in your own files and say so
  in your handoff, so the lead can move it.
- Stay within what your task says you may change. If your checks can't pass within that, stop
  and write the handoff with the options you found; never widen your own permissions.
- Scratch files go only in `.claude/team/scratch/<your name>/`, generated output in a new empty
  folder.
- Log each edit to a shared file (a config, a data table, a shared generator) with one line in
  `.claude/team/changes.md`: date, your name, file, function or row, what changed. Change shared
  tables by appending rows with Edit, unless your task says to change values; never rewrite a
  whole shared file.
- Don't commit. Don't run heavy jobs (longer than about a minute, or holding a server or another
  shared resource) and don't launch the program: the lead does. Quick checks (tests or syntax
  checks that finish in under a minute) are yours to run.

## Budget

- Your budget is your context: about 100K tokens. Above 100K every call costs 5x. Tool calls are
  cheap: many small calls are fine while the context stays small.
- Take in at most about 25K tokens (about 100 KB of text) per turn: read large files in parts,
  one part per call, never several large reads in parallel.
- Keep command output small: pipe it through `tail`, `head` or `grep`; never print a whole log.
- Near 100K, at the next safe point, stop and write the handoff. Don't start a new step.

## Finish

- Run your task's done check and fix your own code until it passes. Never hand back while a job
  you started is still running, and never report a partial count as final.
- In tests, never name a helper after a test-framework method (in unittest: `fail`,
  `assert...`, `setUp`, `run`): a shadowed `fail` turns failing assertions into passes.
- Write `.claude/team/handoff/<your name>.txt` with four sections: **Done** (files changed,
  counts, check results), **In progress** (where you stopped), **Next step** (the exact next
  action and command, runnable without your history), **Do not redo** (what you checked and
  ruled out, with evidence).
- Final message: one status line and the handoff path. If writing the handoff is refused, put
  its four sections in your final message instead; the lead saves them.
"""

STATUS = """\
# Team status

| Teammate | Task | Model | State | Handoff |
|---|---|---|---|---|

| Heavy job | Output file | Done check | State |
|---|---|---|---|
"""

CHANGES = """\
# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

"""

RULE = """\
When the user asks to work with the team, teammates or an agent team, in any words ("work with
team on it", "use the team", /team), load the `team` skill with the Skill tool before doing
anything else, and follow it.
"""

FILES = {".claude/skills/team/SKILL.md": SKILL, ".claude/agents/team-dev.md": AGENT,
         ".claude/rules/team.md": RULE}
WORK_FILES = {".claude/team/status.md": STATUS, ".claude/team/changes.md": CHANGES}
SELF = ".claude/skills/team/team_kit.py"
SETTINGS = ".claude/settings.local.json"
SETTINGS_ADD = {"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"},
                "modelSettings": {"claude-haiku-5-5": {"autoCompactWindow": 100000}}}
MANIFEST = ".claude/team/.kit.json"
EXCLUDE = [".claude/skills/team/", ".claude/agents/team-dev.md", ".claude/rules/team.md",
           ".claude/team/", SETTINGS]
BEGIN, END = "# team_kit.py begin", "# team_kit.py end"
# Tools a team lead never uses, removed by `lead`. A name the session doesn't have is harmless
# (claude prints a warning), so the list works in any environment; tools it doesn't name stay.
LEAD_DENY = ("Artifact,ArtifactComments,ArtifactData,DesignSync,SendFeedback,ReportFindings,"
             "ReadNotifications,FetchInboxMessage,EndConversation,mcp__claude_ai_Gmail")


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def repo_root(path):
    path = os.path.abspath(path)
    return git(path, "rev-parse", "--show-toplevel") or path


def leaves(d, prefix=()):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from leaves(v, prefix + (k,))
        else:
            yield prefix + (k,), v


def get_path(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None, False
        d = d[k]
    return d, True


def set_path(d, path, value):
    for k in path[:-1]:
        d = d.setdefault(k, {})
    d[path[-1]] = value


def del_path(d, path):
    """Delete a leaf, then any dicts left empty above it."""
    stack = []
    for k in path[:-1]:
        if not isinstance(d.get(k), dict):
            return
        stack.append((d, k))
        d = d[k]
    d.pop(path[-1], None)
    for parent, k in reversed(stack):
        if parent[k] == {}:
            del parent[k]


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def exclude_path(repo):
    p = git(repo, "rev-parse", "--git-path", "info/exclude")
    return None if p is None else os.path.join(repo, p) if not os.path.isabs(p) else p


def set_exclude(repo, lines):
    """Replace the kit's block in .git/info/exclude with `lines` (none: remove the block)."""
    path = exclude_path(repo)
    if path is None:
        return False
    text = open(path).read() if os.path.exists(path) else ""
    text = re.sub(rf"^{re.escape(BEGIN)}\n.*?^{re.escape(END)}\n", "", text, flags=re.S | re.M)
    if lines:   # first in the file, so removing it gives back the original text exactly
        text = "\n".join([BEGIN, *lines, END]) + "\n" + text
    write(path, text)
    return True


def install(repo, force=False):
    man_path = os.path.join(repo, MANIFEST)
    man = load_json(man_path, {"files": [], "settings_prior": None, "settings_created": None,
                               "settings_text": None})
    tracked = git(repo, "ls-files", "--", *FILES, SETTINGS, *WORK_FILES) or ""
    if tracked and not force:
        sys.exit(f"Tracked by git, so the kit would change the repo's content:\n{tracked}\n"
                 "Remove them from git first, or pass --force.")
    for rel, text in FILES.items():
        path = os.path.join(repo, rel)
        if (os.path.exists(path) and rel not in man["files"] and open(path).read() != text
                and not force):
            sys.exit(f"{rel} exists and isn't the kit's; pass --force to replace it.")
    for rel, text in FILES.items():
        write(os.path.join(repo, rel), text)
    for rel, text in WORK_FILES.items():
        if not os.path.exists(os.path.join(repo, rel)):
            write(os.path.join(repo, rel), text)
    os.makedirs(os.path.join(repo, ".claude/team/handoff"), exist_ok=True)
    me, dest = os.path.abspath(__file__), os.path.join(repo, SELF)
    if not os.path.exists(dest) or not os.path.samefile(me, dest):
        shutil.copyfile(me, dest)

    spath = os.path.join(repo, SETTINGS)
    if man["settings_created"] is None:
        man["settings_created"] = not os.path.exists(spath)
    settings = load_json(spath, {})
    if man["settings_prior"] is None:   # values before the first install, restored by uninstall
        man["settings_text"] = open(spath).read() if os.path.exists(spath) else None
        man["settings_prior"] = []
        for path, _ in leaves(SETTINGS_ADD):
            value, found = get_path(settings, path)
            man["settings_prior"].append([list(path), found, value])
    for path, value in leaves(SETTINGS_ADD):
        set_path(settings, path, value)
    write(spath, json.dumps(settings, indent=2) + "\n")

    excluded = set_exclude(repo, EXCLUDE)
    man.update(version=KIT_VERSION, files=sorted(FILES) + [SELF])
    write(man_path, json.dumps(man, indent=2) + "\n")
    print(f"team kit {KIT_VERSION} installed in {repo}")
    for rel in [*FILES, SELF, SETTINGS, ".claude/team/"]:
        print("  " + rel)
    print("  git: hidden through .git/info/exclude" if excluded
          else "  not a git repo: nothing hidden from version control")
    print("Use: in a Claude Code session in this repo, type /team <task>. "
          "Restart sessions that are already open.")


def uninstall(repo, keep_work=False):
    man = load_json(os.path.join(repo, MANIFEST), None)
    if man is None:
        sys.exit(f"No team kit installed in {repo} (no {MANIFEST}).")
    for rel in man["files"]:
        if os.path.exists(os.path.join(repo, rel)):
            os.remove(os.path.join(repo, rel))
    spath = os.path.join(repo, SETTINGS)
    if os.path.exists(spath):
        settings = load_json(spath, {})
        for path, found, value in man["settings_prior"] or []:
            if found:
                set_path(settings, path, value)
            else:
                del_path(settings, path)
        original = man.get("settings_text")
        if settings == {} and man["settings_created"]:
            os.remove(spath)
        elif original is not None and json.loads(original) == settings:
            write(spath, original)   # unchanged since install: restore it byte for byte
        else:
            write(spath, json.dumps(settings, indent=2) + "\n")
    work = os.path.join(repo, ".claude/team")
    if keep_work:
        os.remove(os.path.join(repo, MANIFEST))
    else:
        shutil.rmtree(work, ignore_errors=True)
    for d in (".claude/skills/team", ".claude/skills", ".claude/agents", ".claude/rules",
              ".claude"):
        try:
            os.rmdir(os.path.join(repo, d))   # only if empty
        except OSError:
            pass
    set_exclude(repo, [] if not keep_work else [".claude/team/"])
    print(f"team kit removed from {repo}" + (" (kept .claude/team/)" if keep_work else ""))


def lead(argv):
    """Replace this process with a lean lead session: claude without LEAD_DENY, on /team TASK."""
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    deny = LEAD_DENY
    if "--deny" in argv:
        i = argv.index("--deny")
        deny += "," + argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    # The '=' form: a list option followed by a bare argument would take it as one more name.
    flags = [f"--disallowedTools={deny}"]
    if "--print-args" in argv:
        print(" ".join(flags))
        return
    task = " ".join(argv).strip()
    os.execvp("claude", ["claude", *flags, *extra] + (["--", f"/team {task}"] if task else []))


def request():
    """Save the user's messages in this session, word for word, to .claude/team/spec.md."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        sys.exit("Run it from a command in a Claude Code session (CLAUDE_CODE_SESSION_ID isn't set).")
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    found = glob.glob(os.path.join(base, "projects", "*", sid + ".jsonl"))
    if not found:
        sys.exit(f"No transcript for session {sid} under {base}/projects.")
    texts = []
    for line in open(found[0], encoding="utf-8"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "user" or (d.get("origin") or {}).get("kind") != "human":
            continue
        c = d["message"]["content"]
        text = c if isinstance(c, str) else "\n".join(b.get("text", "") for b in c
                                                      if b.get("type") == "text")
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)   # /team TASK
        text = args.group(1) if args else text
        text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S).strip()
        if text:
            texts.append(text)
    if not texts:
        sys.exit("No message from the user in this session's transcript.")
    rel = ".claude/team/spec.md"
    body = ("# The user's request, word for word (their messages in this session, oldest first)\n\n"
            + "\n\n---\n\n".join(texts) + "\n")
    write(os.path.join(repo_root("."), rel), body)
    print(f"Wrote {rel}: {len(texts)} message(s), {len(body.split())} words.")


def status(repo):
    man = load_json(os.path.join(repo, MANIFEST), None)
    print(f"{repo}: " + (f"team kit {man.get('version')}" if man else "team kit not installed"))
    for rel in [*FILES, SELF, *WORK_FILES]:
        state = "missing"
        if os.path.exists(os.path.join(repo, rel)):
            state = "ok"
            if rel in FILES and open(os.path.join(repo, rel)).read() != FILES[rel]:
                state = "differs from this kit file (install updates it)"
        print(f"  {rel}: {state}")
    settings = load_json(os.path.join(repo, SETTINGS), {})
    for path, value in leaves(SETTINGS_ADD):
        print(f"  {SETTINGS} {'.'.join(path)}: "
              + ("ok" if get_path(settings, path) == (value, True) else "missing"))
    ex = exclude_path(repo)
    hidden = ex and os.path.exists(ex) and BEGIN in open(ex).read()
    print("  .git/info/exclude: " + ("ok" if hidden else "no kit block"))


# ---------------------------------------------------------------------------------------------
# cost: tokens, peak context and USD per agent, from Claude Code transcripts
#
# Reads every transcript (*.jsonl) of the repo under ~/.claude/projects/: lead sessions and their
# teammates. Prints numbers only, never message content.
# ---------------------------------------------------------------------------------------------

# USD per million tokens (checked 2026-10-16 against Claude Code's own cost-state records).
# Haiku 5.5 bills a whole prompt over 100K tokens at 5x.
PRICES = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cw5m": 5.00, "cw1h": 8.00, "cr": 0.20},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cw5m": 2.50, "cw1h": 4.00, "cr": 0.20},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cw5m": 0.125, "cw1h": 0.20, "cr": 0.01,
                         "long_over": 100_000, "long_mult": 5.0},
}
LONG = 100_000
CHARS_PER_TOKEN = 3.5
PARTS = ("cost_in", "cost_cr", "cost_cw", "cost_out")


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def prompt_size(u):
    return (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0))


def message_cost(model, u):
    """Cost parts of one response: input, cache read, cache write, output. None if unpriced."""
    p = PRICES.get(model)
    if p is None:
        return None
    cw = u.get("cache_creation_input_tokens", 0)
    cc = u.get("cache_creation") or {}
    cw1h = cc.get("ephemeral_1h_input_tokens", 0)
    cw5m = cc.get("ephemeral_5m_input_tokens", cw - cw1h)
    mult = p.get("long_mult", 1.0) if prompt_size(u) > p.get("long_over", float("inf")) else 1.0
    return {"cost_in": mult * p["in"] * u.get("input_tokens", 0) / 1e6,
            "cost_cr": mult * p["cr"] * u.get("cache_read_input_tokens", 0) / 1e6,
            "cost_cw": mult * (p["cw5m"] * cw5m + p["cw1h"] * cw1h) / 1e6,
            "cost_out": mult * p["out"] * u.get("output_tokens", 0) / 1e6}


def session_of(path):
    """Lead session id of a transcript: its own name, or the folder above subagents/."""
    parts = path.split(os.sep)
    if len(parts) >= 3 and parts[-2] == "subagents":
        return parts[-3]
    return os.path.basename(path)[:-len(".jsonl")]


def agent_effort(project, agent_type):
    """`effort:` from the project's .claude/agents/<type>.md frontmatter, if any."""
    path = os.path.join(project, ".claude", "agents", f"{agent_type}.md")
    if not agent_type or not os.path.exists(path):
        return ""
    m = re.search(r"^effort:\s*(\S+)", open(path).read().split("---")[1], re.M)
    return m.group(1) if m else ""


def scan(path, since, until, project):
    # Teammate transcripts keep the usage from the start of each response (stop_reason null), so
    # their output_tokens are far too low. For those responses, output is estimated from the
    # visible content (text and tool inputs). Hidden thinking stays uncounted.
    usage, final, chars = {}, set(), Counter()
    tools, agent, first, last, started, compactions = set(), None, None, None, None, 0
    with open(path) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
                compactions += 1
            if e.get("type") != "assistant":
                continue
            ts = parse_time(e.get("timestamp"))
            started = started or ts
            if ts and ((since and ts < since) or (until and ts > until)):
                continue
            m = e.get("message") or {}
            if not m.get("id") or m.get("model") in (None, "<synthetic>"):
                continue
            usage[m["id"]] = (m["model"], m.get("usage") or {})
            if m.get("stop_reason"):
                final.add(m["id"])
            for c in m.get("content") or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use":
                    tools.add(c.get("id"))
                    chars[m["id"]] += len(json.dumps(c.get("input") or {}))
                chars[m["id"]] += len(c.get("text") or "") + len(c.get("thinking") or "")
            agent = agent or e.get("agentId")
            first = first or ts
            last = ts
    if not usage:
        return None
    session = session_of(path)
    role = "lead" if os.path.basename(path) == session + ".jsonl" else "teammate"
    meta = {}
    if os.path.exists(path[:-len(".jsonl")] + ".meta.json"):
        with open(path[:-len(".jsonl")] + ".meta.json") as f:
            meta = json.load(f)
    name = meta.get("name") or meta.get("description", "").split(":")[0].strip() or None
    models = Counter(model for model, _ in usage.values())
    row = {"agent": name or agent or "lead:" + session[:8], "role": role,
           "effort": meta.get("effort") or agent_effort(project, meta.get("customAgentType")),
           "file": path, "session": session,
           "started": started.isoformat() if started else None,
           "model": models.most_common(1)[0][0], "msgs": len(usage),
           "tools": len(tools), "input": 0, "cache_w": 0, "cache_r": 0, "output": 0,
           "peak_ctx": 0, "over_100k": 0, "compactions": compactions, "cost": 0.0,
           "unpriced": 0, "out_est": 0,
           **{k: 0.0 for k in PARTS},
           "first": first.isoformat() if first else None,
           "last": last.isoformat() if last else None}
    for mid, (model, u) in usage.items():
        if mid not in final:
            estimate = round(chars[mid] / CHARS_PER_TOKEN)
            if estimate > u.get("output_tokens", 0):
                u = dict(u, output_tokens=estimate)
            row["out_est"] += 1
        row["input"] += u.get("input_tokens", 0)
        row["cache_w"] += u.get("cache_creation_input_tokens", 0)
        row["cache_r"] += u.get("cache_read_input_tokens", 0)
        row["output"] += u.get("output_tokens", 0)
        row["peak_ctx"] = max(row["peak_ctx"], prompt_size(u))
        row["over_100k"] += prompt_size(u) > LONG
        c = message_cost(model, u)
        if c is None:
            row["unpriced"] += 1
            continue
        for k in PARTS:
            row[k] += c[k]
        row["cost"] += sum(c.values())
    # A lead's first message can read a prompt prefix (tools, system prompt) that another
    # session cached within the TTL. cold_extra is what that message would cost more had it
    # written the prefix itself, so runs started at different times compare on a cold start.
    model, u = next(iter(usage.values()))
    p = PRICES.get(model)
    row["startup_ctx"], row["cold_extra"] = prompt_size(u), 0.0
    if role == "lead" and p:
        cc = u.get("cache_creation") or {}
        cw = p["cw1h"] if cc.get("ephemeral_1h_input_tokens") else p["cw5m"]
        row["cold_extra"] = (cw - p["cr"]) * u.get("cache_read_input_tokens", 0) / 1e6
    return row


def totals(agents, role):
    rows = [r for r in agents if r.get("role", "lead" if r["agent"].startswith("lead:")
                                         else "teammate") == role]
    t = {k: sum(r.get(k, 0) for r in rows) for k in ("cost", "msgs", "tools", "output",
                                                     "over_100k", "compactions",
                                                     "cold_extra") + PARTS}
    t["peak_ctx"] = max((r["peak_ctx"] for r in rows), default=0)
    t["startup_ctx"] = max((r.get("startup_ctx", 0) for r in rows), default=0)
    t["models"] = sorted({r["model"].replace("claude-", "") for r in rows})
    t["count"] = len(rows)
    return t


def compare(path_a, path_b):
    a, b = (json.load(open(p)) for p in (path_a, path_b))
    la, lb = totals(a["agents"], "lead"), totals(b["agents"], "lead")
    ta, tb = totals(a["agents"], "teammate"), totals(b["agents"], "teammate")

    def pct(x, y):
        return f"{(y - x) / x * 100:+.0f}%" if x else ""

    rows = [("Total $", a["total_cost"], b["total_cost"], "$"),
            ("Total $, cold start", a["total_cost"] + la["cold_extra"],
             b["total_cost"] + lb["cold_extra"], "$"),
            ("Lead $", la["cost"], lb["cost"], "$"),
            ("Team $", ta["cost"], tb["cost"], "$"),
            ("Lead model", ", ".join(la["models"]), ", ".join(lb["models"]), "s"),
            ("Lead cache read $", la["cost_cr"], lb["cost_cr"], "$"),
            ("Lead cache write $", la["cost_cw"], lb["cost_cw"], "$"),
            ("Lead output $", la["cost_out"], lb["cost_out"], "$"),
            ("Lead messages", la["msgs"], lb["msgs"], "n"),
            ("Lead tool calls", la["tools"], lb["tools"], "n"),
            ("Lead output tokens", la["output"], lb["output"], "n"),
            ("Lead start-up prompt", la["startup_ctx"], lb["startup_ctx"], "k"),
            ("Lead peak context", la["peak_ctx"], lb["peak_ctx"], "k"),
            ("Teammates", ta["count"], tb["count"], "n"),
            ("Team tool calls", ta["tools"], tb["tools"], "n"),
            ("Team peak context", ta["peak_ctx"], tb["peak_ctx"], "k"),
            ("Team messages over 100K", ta["over_100k"], tb["over_100k"], "n"),
            ("Team compactions", ta["compactions"], tb["compactions"], "n")]
    fmt = {"$": lambda v: f"{v:.3f}", "n": str, "k": lambda v: f"{v / 1000:.0f}K", "s": str}
    print(f"| Metric | A | B | B vs A |\n|---|---|---|---|")
    for label, x, y, kind in rows:
        delta = "" if kind == "s" else pct(x, y)
        print(f"| {label} | {fmt[kind](x)} | {fmt[kind](y)} | {delta} |")
    print(f"\nA: {path_a} {a.get('label', '')}\nB: {path_b} {b.get('label', '')}")


def cost_main(argv):
    ap = argparse.ArgumentParser(
        prog="team_kit.py cost",
        description="Tokens, peak context and USD cost per agent of Claude Code sessions in a "
                    "repo, from their transcripts. Default: the latest lead session, in full.")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--json")
    ap.add_argument("--project", default=repo_root(os.getcwd()),
                    help="the directory the sessions ran in (default: this repo)")
    ap.add_argument("--fresh-only", action="store_true",
                    help="count only lead sessions that started at or after --since, in full, "
                         "with their teammates")
    ap.add_argument("--latest-session", action="store_true",
                    help="count only the most recently started lead session, in full, with its "
                         "teammates (the default when no other selection is given)")
    ap.add_argument("--session", help="count only this lead session (id or prefix), in full, "
                                      "with its teammates")
    ap.add_argument("--compare", nargs=2, metavar=("A_JSON", "B_JSON"),
                    help="print an A/B comparison table of two --json reports")
    ap.add_argument("--label", default="", help="free text stored in the --json report, such "
                                                "as the lead's model, effort and cache TTL")
    a = ap.parse_args(argv)
    if not (a.compare or a.since or a.session or a.fresh_only):
        a.latest_session = True
    if a.compare:
        return compare(*a.compare)

    project = os.path.abspath(a.project)
    pdir = os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", project))
    since, until = parse_time(a.since), parse_time(a.until)
    whole = a.fresh_only or a.latest_session or a.session
    # Whole-session modes count each selected session in full (including its first message,
    # which writes the cached prefix); --since then only selects sessions.
    rows = [r for p in sorted(glob.glob(pdir + "/**/*.jsonl", recursive=True))
            if (r := scan(p, None if whole else since, until, project))]
    leads = [r for r in rows if r["role"] == "lead" and r["started"]]
    keep = None
    if a.fresh_only:
        if not since:
            ap.error("--fresh-only needs --since")
        keep = {r["session"] for r in leads if parse_time(r["started"]) >= since}
    if a.latest_session and leads:
        keep = {max(leads, key=lambda r: r["started"])["session"]}
    if a.session:
        keep = {r["session"] for r in leads if r["session"].startswith(a.session)}
    if keep is not None:
        rows = [r for r in rows if r["session"] in keep]
    rows.sort(key=lambda r: r["first"] or "")

    cols = ["agent", "model", "effort", "msgs", "tools", "input", "cache_w", "cache_r", "output",
            "out_est", "peak_ctx", "over_100k", "compactions", "cost"]
    fmt = lambda r, c: f"{r[c]:.4f}" if c == "cost" else str(r[c]).replace("claude-", "")
    table = [cols] + [[fmt(r, c) for c in cols] for r in rows]
    by_model = {}
    for r in rows:
        t = by_model.setdefault(r["model"], {c: 0 for c in cols[3:]})
        for c in cols[3:]:
            t[c] = max(t[c], r[c]) if c == "peak_ctx" else t[c] + r[c]
    for model, t in by_model.items():
        table.append(["TOTAL", model.replace("claude-", ""), ""] + [fmt(t, c) for c in cols[3:]])
    widths = [max(len(row[i]) for row in table) for i in range(len(cols))]
    for row in table:
        print("  ".join(v.ljust(w) if i < 3 else v.rjust(w)
                        for i, (v, w) in enumerate(zip(row, widths))))
    total = sum(r["cost"] for r in rows)
    print(f"total ${total:.4f}" + ("  (some messages unpriced)" if any(r["unpriced"] for r in rows)
                                   else ""))
    cold = sum(r["cold_extra"] for r in rows)
    if cold:
        print(f"cold start ${total + cold:.4f}: the lead's first message read a prefix another "
              f"session had cached; written by this run it would cost ${cold:.4f} more.")
    if any(r["out_est"] for r in rows):
        print("out_est: responses whose output was estimated from visible content "
              f"({CHARS_PER_TOKEN} chars/token); hidden thinking is not counted.")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"label": a.label, "since": a.since, "until": a.until,
                       "session": a.session, "total_cost": total,
                       "cold_start_cost": total + cold, "by_model": by_model,
                       "agents": rows}, f, indent=2)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 epilog=__doc__.split("\n", 2)[2],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("install", help="install or update the kit in a repo")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--force", action="store_true", help="replace files the kit didn't write")
    p = sub.add_parser("uninstall", help="remove everything install added")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--keep-work", action="store_true", help="keep .claude/team/ (plans, handoffs)")
    p = sub.add_parser("status", help="show what is installed")
    p.add_argument("repo", nargs="?", default=".")
    sub.add_parser("cost", help="tokens and USD per agent of a session (cost --help)",
                   add_help=False)
    sub.add_parser("lead", help="start a lean lead session: lead [TASK] [-- CLAUDE_ARGS]",
                   add_help=False)
    sub.add_parser("request", help="in a session: save the user's messages to .claude/team/spec.md")
    if len(sys.argv) > 1 and sys.argv[1] == "cost":
        return cost_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "lead":
        return lead(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "request":
        return request()
    a = ap.parse_args()
    repo = repo_root(a.repo)
    if a.cmd == "install":
        install(repo, a.force)
    elif a.cmd == "uninstall":
        uninstall(repo, a.keep_work)
    else:
        status(repo)


if __name__ == "__main__":
    main()
