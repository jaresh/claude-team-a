#!/usr/bin/env python3
"""Install the team kit into another repo. Safe to run again.

  python3 kit/install.py /path/to/repo
"""
import json
import os
import shutil
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
IMPORT_LINE = "@kit/rules/team-rules.md"
GITIGNORE_LINES = ["scratch/", "out/", ".claude/settings.local.json"]
RESULT_FILES = {
    "results/team-status.md": "templates/team-status.md",
    "results/changes.md": "templates/changes.md",
    "results/experiments.md": "templates/experiments.md",
}


def copy_kit(target):
    dest = os.path.join(target, "kit")
    if os.path.realpath(dest) == os.path.realpath(KIT):
        return "kit/ already in place"
    shutil.copytree(KIT, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    return "copied kit/"


def add_import(target):
    path = os.path.join(target, "CLAUDE.md")
    text = open(path).read() if os.path.exists(path) else ""
    if IMPORT_LINE in text.split("\n"):
        return "CLAUDE.md already imports the rules"
    if not text:
        name = os.path.basename(os.path.abspath(target))
        text = f"# {name}\n\n<!-- Project notes for the team go here. -->\n"
    with open(path, "w") as f:
        f.write(text.rstrip("\n") + "\n\n" + IMPORT_LINE + "\n")
    return "added rules import to CLAUDE.md"


def merge_settings(target):
    path = os.path.join(target, ".claude", "settings.json")
    settings = {}
    if os.path.exists(path):
        with open(path) as f:
            settings = json.load(f)
    wanted = json.load(open(os.path.join(KIT, "settings", "settings.json")))
    env = settings.setdefault("env", {})
    missing = {k: v for k, v in wanted["env"].items() if env.get(k) != v}
    if not missing:
        return ".claude/settings.json already set"
    env.update(missing)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    return "set " + ", ".join(missing) + " in .claude/settings.json"


def install_agents(target):
    src = os.path.join(KIT, "agents")
    dest = os.path.join(target, ".claude", "agents")
    made = []
    for name in sorted(os.listdir(src)):
        path = os.path.join(dest, name)
        new = open(os.path.join(src, name)).read()
        if os.path.exists(path) and open(path).read() == new:
            continue
        os.makedirs(dest, exist_ok=True)
        with open(path, "w") as f:
            f.write(new)
        made.append(name)
    return "installed .claude/agents/" + ", ".join(made) if made else "agents already installed"


def update_gitignore(target):
    path = os.path.join(target, ".gitignore")
    lines = open(path).read().split("\n") if os.path.exists(path) else []
    missing = [l for l in GITIGNORE_LINES if l not in lines]
    if not missing:
        return ".gitignore already set"
    with open(path, "a") as f:
        if lines and lines[-1] != "":
            f.write("\n")
        f.write("# Team kit\n" + "\n".join(missing) + "\n")
    return "added " + " ".join(missing) + " to .gitignore"


def create_results(target):
    made = []
    for d in ("results/handoff", "results/metrics"):
        os.makedirs(os.path.join(target, d), exist_ok=True)
    for dest, src in RESULT_FILES.items():
        path = os.path.join(target, dest)
        if not os.path.exists(path):
            shutil.copy(os.path.join(KIT, src), path)
            made.append(dest)
    return "created " + ", ".join(made) if made else "results/ already in place"


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit(__doc__.strip())
    target = sys.argv[1]
    for step in (copy_kit, add_import, merge_settings, install_agents, update_gitignore,
                 create_results):
        print("-", step(target))
    print("Done. Restart Claude Code in", os.path.abspath(target), "to start the team.")


if __name__ == "__main__":
    main()
