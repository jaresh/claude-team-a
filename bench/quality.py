#!/usr/bin/env python3
"""Code-quality metrics of a built benchmark app (standard library only).

    bench/quality.py WORKSPACE [--json OUT]

App code is every .py file outside tests/ (and outside .claude/ and .git/); test code is
everything under tests/. Prints and optionally writes one JSON object."""
import ast
import json
import os
import re
import sys
from collections import Counter

ws = sys.argv[1]
app, tests = {}, {}
for root, dirs, files in os.walk(ws):
    dirs[:] = [d for d in dirs if d not in (".git", ".claude", "__pycache__")]
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, ws)
            (tests if rel.split(os.sep)[0] == "tests" else app)[rel] = open(path, encoding="utf-8", errors="replace").read()


def code_lines(src):
    return sum(1 for l in src.splitlines() if l.strip() and not l.strip().startswith("#"))


def complexity(fn):
    n = 1
    for node in ast.walk(fn):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler, ast.IfExp,
                             ast.Assert, ast.match_case)):
            n += 1
        elif isinstance(node, ast.BoolOp):
            n += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            n += 1 + len(node.ifs)
    return n


funcs, doc_total, doc_have, parse_errors = [], 0, 0, []
float_calls = bare_except = broad_except = sql_format = 0
for rel, src in app.items():
    try:
        tree = ast.parse(src)
    except SyntaxError:
        parse_errors.append(rel)
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append((rel, node.name, node.end_lineno - node.lineno + 1, complexity(node)))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            doc_total += 1
            doc_have += ast.get_docstring(node) is not None
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "float":
                float_calls += 1
            if isinstance(f, ast.Attribute) and f.attr in ("execute", "executemany", "executescript") and node.args:
                q = node.args[0]
                if isinstance(q, ast.JoinedStr) and any(isinstance(v, ast.FormattedValue) for v in q.values) \
                        or isinstance(q, ast.BinOp) and isinstance(q.op, (ast.Mod, ast.Add)) \
                        or isinstance(q, ast.Call) and isinstance(q.func, ast.Attribute) and q.func.attr == "format":
                    sql_format += 1
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                bare_except += 1
            elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                broad_except += 1

# Duplication: share of normalized 6-line windows of app code that occur more than once.
windows = Counter()
for src in app.values():
    lines = [re.sub(r"\s+", " ", l.strip()) for l in src.splitlines()]
    lines = [l for l in lines if l and not l.startswith("#") and l not in ("pass", "return", ")", "]", "}")]
    for i in range(len(lines) - 5):
        windows["\n".join(lines[i:i + 6])] += 1
dup = sum(c for c in windows.values() if c > 1) / max(sum(windows.values()), 1)

lengths = [f[2] for f in funcs]
cx = [f[3] for f in funcs]
app_lines = sum(code_lines(s) for s in app.values())
test_lines = sum(code_lines(s) for s in tests.values())
result = {
    "app_files": len(app), "app_lines": app_lines, "test_files": len(tests), "test_lines": test_lines,
    "test_functions": sum(len(re.findall(r"^\s*def test_", s, re.M)) for s in tests.values()),
    "test_to_app_ratio": round(test_lines / max(app_lines, 1), 2),
    "functions": len(funcs),
    "mean_function_lines": round(sum(lengths) / max(len(lengths), 1), 1),
    "max_function_lines": max(lengths, default=0),
    "functions_over_50_lines": sum(l > 50 for l in lengths),
    "mean_complexity": round(sum(cx) / max(len(cx), 1), 1),
    "max_complexity": max(cx, default=0),
    "functions_complexity_over_10": sum(c > 10 for c in cx),
    "most_complex": [f"{r}:{n} ({c})" for r, n, _, c in sorted(funcs, key=lambda f: -f[3])[:3]],
    "docstring_coverage": round(doc_have / max(doc_total, 1), 2),
    "duplicate_share": round(dup, 3),
    "float_calls": float_calls, "sql_built_from_strings": sql_format,
    "bare_except": bare_except, "broad_except": broad_except, "parse_errors": parse_errors,
}
print(json.dumps(result, indent=2))
if "--json" in sys.argv:
    json.dump(result, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=2)
