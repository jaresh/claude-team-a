#!/usr/bin/env python3
"""Line coverage of a built app by its own tests (standard library only, Python 3.12+).

    bench/coverage.py WORKSPACE [--json OUT]

Runs `python -m unittest discover -s tests` in WORKSPACE with a sitecustomize hook that records
executed lines (sys.monitoring) in every Python process the tests start, so tests that call the
CLI or the HTTP server through a subprocess count too. App code is every .py file outside
tests/, .claude/ and .git/. Coverage = executed lines / executable lines of the app."""
import json
import os
import subprocess
import sys
import tempfile

HOOK = r'''
import atexit, os, signal, sys
_root = os.environ["BENCH_COV_ROOT"]
_skip = tuple(os.path.join(_root, d) + os.sep for d in ("tests", ".claude", ".git"))
_hits = set()
_M = sys.monitoring
_M.use_tool_id(_M.COVERAGE_ID, "benchcov")
def _line(code, line):
    f = code.co_filename
    if f.startswith(_root) and not f.startswith(_skip):
        _hits.add((f, line))
    return _M.DISABLE
_M.register_callback(_M.COVERAGE_ID, _M.events.LINE, _line)
_M.set_events(_M.COVERAGE_ID, _M.events.LINE)
@atexit.register
def _dump():
    with open(os.path.join(os.environ["BENCH_COV_OUT"], f"{os.getpid()}.txt"), "a") as fh:
        fh.write("".join(f"{f}\t{l}\n" for f, l in _hits))
try:
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))   # a stopped test server still reports
except (ValueError, OSError):
    pass
'''


def executable_lines(path):
    try:
        code = compile(open(path, encoding="utf-8", errors="replace").read(), path, "exec")
    except SyntaxError:
        return set()
    lines, todo = set(), [code]
    while todo:
        c = todo.pop()
        lines.update(l for _, _, l in c.co_lines() if l is not None)
        todo.extend(k for k in c.co_consts if hasattr(k, "co_lines"))
    return lines


def main():
    ws = os.path.realpath(sys.argv[1])
    app = []
    for root, dirs, files in os.walk(ws):
        dirs[:] = [d for d in dirs if d not in (".git", ".claude", "__pycache__")]
        if os.path.relpath(root, ws).split(os.sep)[0] == "tests":
            continue
        app += [os.path.join(root, f) for f in files if f.endswith(".py")]
    with tempfile.TemporaryDirectory() as tmp:
        hook_dir, hits_dir = os.path.join(tmp, "hook"), os.path.join(tmp, "hits")
        os.makedirs(hook_dir)
        os.makedirs(hits_dir)
        open(os.path.join(hook_dir, "sitecustomize.py"), "w").write(HOOK)
        env = dict(os.environ, BENCH_COV_ROOT=ws, BENCH_COV_OUT=hits_dir,
                   PYTHONPATH=os.pathsep.join(filter(None, [hook_dir, os.environ.get("PYTHONPATH")])))
        try:
            r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ws,
                               env=env, capture_output=True, text=True, timeout=1200)
            tests_ok = r.returncode == 0
        except subprocess.TimeoutExpired:
            tests_ok = False
        hits = set()
        for name in os.listdir(hits_dir):
            for row in open(os.path.join(hits_dir, name)):
                f, _, l = row.rstrip("\n").partition("\t")
                hits.add((f, int(l)))
    per_file, total, covered = {}, 0, 0
    for path in sorted(app):
        lines = executable_lines(path)
        got = {l for f, l in hits if f == path} & lines
        total += len(lines)
        covered += len(got)
        per_file[os.path.relpath(path, ws)] = round(len(got) / len(lines), 3) if lines else None
    least = sorted((v, k) for k, v in per_file.items() if v is not None)[:3]
    result = {"coverage": round(covered / total, 3) if total else 0.0, "covered_lines": covered,
              "executable_lines": total, "tests_passed_under_coverage": tests_ok,
              "least_covered": [f"{k} ({v:.0%})" for v, k in least], "per_file": per_file}
    print(json.dumps(result, indent=2))
    if "--json" in sys.argv:
        json.dump(result, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=2)


if __name__ == "__main__":
    main()
