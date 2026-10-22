"""Authoring tool: split a single-module wms/app.py into the package of modules that base/ and reference/ use (not part of the benchmark)."""
import ast, re, sys, os, collections
src_path, out_dir = sys.argv[1:3]
src = open(src_path).read()
lines = src.splitlines(keepends=True)
tree = ast.parse(src)
marks = [(i + 1, m.group(1)) for i, l in enumerate(lines) if (m := re.match(r"# -{10,} (.*)", l))]
NAMES = {"the movement log, replayed": "ledger", "users": "users", "products, warehouses, locations": "catalog",
         "stock movements": "stock", "costing reports": "reports", "purchase orders": "purchasing",
         "customers, prices, promotions": "pricing", "sales orders": "orders", "transfers": "transfers",
         "returns": "returns", "running a command": "cli", "HTTP": "http"}
first = marks[0][0]
def module_of(lineno):
    mod = "core"
    for ln, title in marks:
        if lineno >= ln:
            mod = NAMES[title]
    return mod
chunks = collections.OrderedDict()
defs = {}
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        continue
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    # include comment lines directly above
    while start > 1 and lines[start - 2].startswith("#") and not re.match(r"# -{10,}", lines[start - 2]):
        start -= 1
    m = module_of(node.lineno)
    if isinstance(node, ast.FunctionDef) and node.name in ("connect", "authorize", "run"):
        m = "session"
    chunks.setdefault(m, []).append((start, node.end_lineno, node))
    names = []
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        names = [node.name]
    elif isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
    for n in names:
        defs[n] = m
stdlib_imports = [l for l in lines[:first] if re.match(r"(import|from) ", l)]
def used(nodes):
    u = set()
    for _, _, n in nodes:
        for x in ast.walk(n):
            if isinstance(x, ast.Name):
                u.add(x.id)
    return u
os.makedirs(out_dir, exist_ok=True)
deps = collections.defaultdict(set)
DOC = {"core": "Errors, parsing and formatting helpers, the schema and the command context.",
       "ledger": "The movement log, replayed: stock and cost layers derived from the movements.",
       "users": "Users and roles.", "catalog": "Products, warehouses and locations.",
       "stock": "Stock movements: receive, move, adjust, scrap, void.",
       "reports": "Costing reports: valuation and aging.", "purchasing": "Purchase orders.",
       "pricing": "Customers, price lists and promotions.", "orders": "Sales orders and reservations, stock reports, reordering.",
       "transfers": "Transfers between warehouses.", "returns": "Returns against shipped sales orders.",
       "cli": "Running a command: users and authorisation, the argument parser, dispatch.", "http": "The HTTP API.", "session": "Opening the book and running one all-or-nothing command as a user."}
for m, nodes in chunks.items():
    u = used(nodes)
    own = {n for n, mm in defs.items() if mm == m}
    need = collections.defaultdict(list)
    for n in sorted(u):
        if n in defs and defs[n] != m:
            need[defs[n]].append(n); deps[m].add(defs[n])
    body = "".join("".join(lines[s - 1:e]) + "\n\n" for s, e, _ in nodes)
    body = re.sub(r"\n{4,}", "\n\n\n", body).rstrip() + "\n"
    # imports: keep only stdlib import lines whose bound name is used
    keep = []
    for l in stdlib_imports:
        names = [x.strip().split(" as ")[-1] for x in re.sub(r"^(from \S+ )?import ", "", l).split(",")]
        if any(n in u or re.search(rf"\b{n}\b", body) for n in names):
            keep.append(l)
    imp = "".join(keep)
    rel = "".join(f"from .{mm} import {', '.join(ns)}\n" for mm, ns in sorted(need.items()))
    open(f"{out_dir}/{m}.py", "w").write(f'"""{DOC[m]}"""\n{imp}{rel}\n\n{body}')
print({m: sorted(d) for m, d in deps.items()})
