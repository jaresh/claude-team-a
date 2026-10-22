#!/usr/bin/env bash
# Benchmark run: one fixed prompt, built by the team or by a single model session in a fresh
# empty repo, then scored with hidden acceptance tests, measured, recorded, and deleted.
#
#   bench/run.sh <bench> team|team1|solo      e.g. bench/run.sh finance team
#
# team: team_kit.py is installed in the workspace and the session starts as `team_kit.py lead`
#       does; the prompt says "Work with team on it."
# team1: the same as team, but the prompt says "Work with team on it, one teammate at a time."
# solo: no kit, no subagents (the Agent tool is removed too); the prompt says to do the work
#       alone. Otherwise the same tools as team mode.
# Both: the same model (MODEL=sonnet), effort (EFFORT=medium) and 1-hour prompt cache.
#
# Single-change experiments: VARIANT=<name> installs the kit as bench/variants/<name>.py changes
# it (its version becomes <kit>+<name>); CLAUDE_ARGS adds session flags (e.g. "--advisor
# sonnet"); ARM names the arm in the results (default: the mode, plus the model when it isn't
# sonnet), so spread.py keeps each arm apart.
#
# Every run is scored three ways: the hidden acceptance tests, code-quality metrics
# (bench/quality.py), and a blind review by a fixed reviewer (REVIEW_MODEL=opus, REVIEW_EFFORT=
# medium, read-only tools, rubric in bench/<bench>/review.md). The reviewer reads a copy in a
# new temporary folder (review-XXXXXX/app), without .git (its branch is named after the arm),
# .claude/ or Markdown files (the app's README may say how it was built), so neither the path,
# the git status nor the files show the arm. The review's cost is recorded apart from the run's. REVIEWS=N runs N
# independent reviews of the same code in parallel (default 1), to measure the reviewer's noise.
# REVIEW2_MODEL=sonnet adds one review by another model (review-alt.json, "review_alt"), to check
# whether the reviewer favours code from its own model family.
#
# A benchmark with a base/ folder (see bench/change) starts from that repository instead of an empty one.
#
# Results go to bench/<bench>/results/<UTC stamp>-<mode>/ (cost, scores, quality, review, the
# team's plan and handoffs, the app's README) and are committed. The built app is deleted
# (KEEP=1 keeps it).
#
# The workspace is bench/work/<bench>-<mode> (git-ignored): a git worktree of this repo on an
# empty orphan branch, bench/<bench>-<mode>, re-created for each run. SLOT=N appends -N to both,
# so runs of the same arm can go in parallel (Claude Code keeps each session's team apart). A worktree shares this
# repo's trust, so background sessions start there; a nested `git init` would not be trusted.
# Sessions there don't load this repo's CLAUDE.md, but they do list its skills and agents (the
# same for both arms; solo has no Agent tool). Auto memory is off in both arms.
set -euo pipefail
bench=${1:?usage: bench/run.sh <bench> team|team1|solo}
mode=${2:?usage: bench/run.sh <bench> team|team1|solo}
repo=$(git rev-parse --show-toplevel)
here=$repo/bench/$bench
[ -f "$here/prompt.md" ] || { echo "No such benchmark: $bench" >&2; exit 1; }
case $mode in
  team) mode_line="Work with team on it." ;;
  team1) mode_line="Work with team on it, one teammate at a time." ;;
  solo) mode_line="Do all the work yourself in this session, without subagents." ;;
  *) echo "mode must be team, team1 or solo" >&2; exit 1 ;;
esac
model=${MODEL:-sonnet}
effort=${EFFORT:-medium}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
ws=$repo/bench/work/$bench-$mode${SLOT:+-$SLOT}
branch=bench/$bench-$mode${SLOT:+-$SLOT}
out=$here/results/$stamp-$mode
# The benchmark's version: what the model and the graders see. Measuring tools (quality.py,
# coverage.py) only add fields, so they aren't part of it.
version=$(cat "$here/prompt.md" "$here"/accept/*.py "$here/review.md" | sha256sum | cut -c1-12)
kit=$(sed -n 's/^KIT_VERSION = "\(.*\)"$/\1/p' "$repo/team_kit.py")   # solo uses its tool list too
reviews=${REVIEWS:-1}
kitfile=$repo/team_kit.py
if [ -n "${VARIANT:-}" ]; then
  kitfile=$(mktemp -d "${TMPDIR:-/tmp}/kit-XXXXXX")/team_kit.py
  python3 "$repo/bench/variants/make.py" "$VARIANT" "$kitfile"
  kit=$(sed -n 's/^KIT_VERSION = "\(.*\)"$/\1/p' "$kitfile")
fi
arm=${ARM:-$mode$([ "$model" = sonnet ] || echo "-$model")}

git -C "$repo" worktree remove --force "$ws" 2>/dev/null || true
git -C "$repo" branch -D "$branch" >/dev/null 2>&1 || true
mkdir -p "$(dirname "$ws")" "$out"
git -C "$repo" worktree add -q --orphan -b "$branch" "$ws"
# A benchmark with a base/ folder starts from that existing repository (committed as the first
# commit), not from an empty one: the task is a change to it.
if [ -d "$here/base" ]; then
  cp -r "$here/base/." "$ws/"
  git -C "$ws" add -A
  git -C "$ws" -c user.name=bench -c user.email=bench@localhost commit -qm "Base: the existing repository"
fi
# Both arms also lose the worktree tools and `git push`: solo sessions entered a worktree of this
# whole repo (hidden tests included) and pushed their branches to origin.
deny="$(python3 "$repo/team_kit.py" lead --print-args),EnterWorktree,ExitWorktree"
if [ "$mode" != solo ]; then
  python3 "$kitfile" install "$ws" >/dev/null
else
  deny="$deny,Agent"
fi
prompt=$(MODE="$mode_line" python3 -c 'import os,sys; print(open(sys.argv[1]).read().replace("{{MODE}}", os.environ["MODE"]))' "$here/prompt.md")

cd "$ws"
started=$(date -u +%FT%TZ)
# shellcheck disable=SC2086  # CLAUDE_ARGS is a list of flags
launch=$(claude --bg --model "$model" --effort "$effort" --permission-mode auto "$deny" ${CLAUDE_ARGS:-} \
         --settings '{"promptCacheTtl":"1h","autoMemoryEnabled":false,"permissions":{"deny":["Bash(git push:*)"]}}' "$prompt" 2>&1) || true
id=$(grep -oE 'backgrounded · [0-9a-f]+' <<<"$launch" | awk '{print $3}')
[ -n "$id" ] || { echo "Could not start the session: $(tail -c 400 <<<"$launch")" >&2; rm -rf "$out"; exit 1; }
echo "Bench $bench/$mode (prompt $version): session $id in $ws"
deadline=$((SECONDS + ${BENCH_TIMEOUT:-10800}))
until [ -s "$ws/.bench-end" ]; do
  if [ $SECONDS -ge $deadline ]; then
    echo "Timed out; stopping $id. Workspace kept: $ws" >&2
    claude stop "$id" >/dev/null 2>&1 || true
    exit 1
  fi
  sleep 15
done
sleep 30   # let the session finish its last message
claude stop "$id" >/dev/null 2>&1 || true
ended=$(cat "$ws/.bench-end")

# Score: the app's own tests, then the hidden acceptance tests (never in the workspace).
(cd "$ws" && timeout 900 python3 -m unittest discover -s tests > "$out/own-tests.txt" 2>&1) || true
python3 "$repo/bench/coverage.py" "$ws" --json "$out/coverage.json" > /dev/null || echo '{}' > "$out/coverage.json"
APP_DIR="$ws" FIN_DIR="$ws" timeout 1200 python3 -m unittest discover -s "$here/accept" -v > "$out/accept.txt" 2>&1 || true
python3 "$repo/team_kit.py" cost --project "$ws" --session "$id" --until "$ended" \
  --label "bench $bench $mode model=$model effort=$effort prompt=$version" --json "$out/cost.json" \
  > "$out/cost.txt"
[ -d "$ws/.claude/team" ] && cp -r "$ws/.claude/team" "$out/team" && rm -f "$out/team/.kit.json"
[ -f "$ws/README.md" ] && cp "$ws/README.md" "$out/app-README.md"

# Quality: metrics, then the blind review of a neutral copy (nothing it sees may show the arm).
python3 "$repo/bench/quality.py" "$ws" --json "$out/quality.json" > /dev/null
rev=$(mktemp -d "${TMPDIR:-/tmp}/review-XXXXXX")/app
mkdir -p "$rev"
(cd "$ws" && tar -cf - --exclude=./.git --exclude=./.claude --exclude=./.bench-end --exclude='*.db' \
   --exclude='__pycache__' --exclude='*.md' .) | tar -xf - -C "$rev"
review_prompt="$(cat "$here/review.md")
$(sed 's/ {{MODE}}//' "$here/prompt.md")"
for i in $(seq 1 "$reviews"); do
  (cd "$rev" && timeout 1800 claude -p --model "${REVIEW_MODEL:-opus}" --effort "${REVIEW_EFFORT:-medium}" \
     --tools=Read,Glob,Grep --output-format json "$review_prompt" < /dev/null > "$out/review-raw-$i.json" 2>/dev/null) &
done
if [ -n "${REVIEW2_MODEL:-}" ]; then
  (cd "$rev" && timeout 1800 claude -p --model "$REVIEW2_MODEL" --effort "${REVIEW_EFFORT:-medium}" \
     --tools=Read,Glob,Grep --output-format json "$review_prompt" < /dev/null > "$out/review-raw-alt.json" 2>/dev/null) &
fi
wait || true
python3 - "$out" "$reviews" "${REVIEW2_MODEL:-}" <<'PY'
import json, os, sys
out, n, alt = sys.argv[1], int(sys.argv[2]), sys.argv[3]
def load(i):
    try:
        raw = json.load(open(f"{out}/review-raw-{i}.json"))
        text = raw.get("result", "")
        review = json.loads(text[text.index("{"):text.rindex("}") + 1])
        if "overall" not in review and "overall" in review.get("scores", {}):   # misplaced by the reviewer
            review["overall"] = review["scores"].pop("overall")
        review["review_cost"] = round(raw.get("total_cost_usd") or 0, 4)
    except (ValueError, OSError) as e:
        review = {"error": f"no review: {e}"}
    return review
reviews = [load(i) for i in range(1, n + 1)]
json.dump(reviews[0], open(f"{out}/review.json", "w"), indent=2)
if n > 1:
    json.dump(reviews, open(f"{out}/reviews.json", "w"), indent=2)
if alt:
    json.dump(dict(load("alt"), model=alt), open(f"{out}/review-alt.json", "w"), indent=2)
PY
rm -f "$out"/review-raw-*.json
rm -rf "$(dirname "$rev")"
lines=$(cd "$ws" && git ls-files --others --exclude-standard --cached -- '*.py' | xargs cat 2>/dev/null | wc -l)

python3 - "$out" "$bench" "$mode" "$model" "$effort" "$version" "$started" "$ended" "$lines" "$kit" "$arm" "${CLAUDE_ARGS:-}" "$here" <<'EOF'
import ast, glob, json, os, re, sys
out, bench, mode, model, effort, version, started, ended, lines, kit, arm, claude_args, here = sys.argv[1:]
def tally(path):
    text = open(path).read()
    ran = re.search(r"Ran (\d+) test", text)
    bad = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", text.split("Ran ")[-1]))
    n = int(ran.group(1)) if ran else 0
    return n, max(n - bad, 0)
acc, own = tally(f"{out}/accept.txt"), tally(f"{out}/own-tests.txt")
# Hidden tests per tier: class names start with T1, T2, T3 (benchmarks without tiers get none).
tiers, failed = {}, set(re.findall(r"^(?:FAIL|ERROR): \w+ \([\w.]*?\.(\w+)\.(\w+)\)", open(f"{out}/accept.txt").read(), re.M))
for path in glob.glob(f"{here}/accept/*.py"):
    for node in ast.parse(open(path).read()).body:
        m = re.match(r"(T\d)", node.name) if isinstance(node, ast.ClassDef) else None
        if m:
            tests = [f.name for f in node.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test")]
            t = tiers.setdefault(m.group(1), [0, 0])
            t[1] += len(tests)
            t[0] += sum((node.name, n) not in failed for n in tests)
cost = json.load(open(f"{out}/cost.json"))
lead = [a for a in cost["agents"] if a["role"] == "lead"]
team = [a for a in cost["agents"] if a["role"] == "teammate"]
quality = json.load(open(f"{out}/quality.json"))
coverage = json.load(open(f"{out}/coverage.json"))
review = json.load(open(f"{out}/review.json"))
more = json.load(open(f"{out}/reviews.json")) if os.path.exists(f"{out}/reviews.json") else [review]
s = {"bench": bench, "mode": mode, "arm": arm, "claude_args": claude_args, "model": model,
     "effort": effort, "prompt": version, "kit": kit,
     "started": started, "ended": ended, "accept_passed": acc[1], "accept_total": acc[0],
     "accept_tiers": {k: tiers[k] for k in sorted(tiers)} if acc[0] else {},
     "own_passed": own[1], "own_total": own[0], "python_lines": int(lines),
     "cost": round(cost["total_cost"], 4), "cost_cold": round(cost["cold_start_cost"], 4),
     "lead_cost": round(sum(a["cost"] for a in lead), 4),
     "team_cost": round(sum(a["cost"] for a in team), 4),
     "advisor_calls": sum(a.get("advisor_calls", 0) for a in cost["agents"]),
     "advisor_cost": round(sum(a.get("cost_adv", 0) for a in cost["agents"]), 4),
     "teammates": [a["agent"] for a in team],
     "lead_messages": sum(a["msgs"] for a in lead),
     "lead_peak_ctx": max((a["peak_ctx"] for a in lead), default=0),
     "lead_compactions": sum(a["compactions"] for a in lead),
     "team_peak_ctx": max((a["peak_ctx"] for a in team), default=0),
     "coverage": coverage.get("coverage"), "least_covered": coverage.get("least_covered", []),
     "quality": quality, "review": review,
     "reviews": [{"overall": r.get("overall"), "scores": r.get("scores"),
                  "review_cost": r.get("review_cost")} for r in more]}
if os.path.exists(f"{out}/review-alt.json"):
    a = json.load(open(f"{out}/review-alt.json"))
    s["review_alt"] = {k: a.get(k) for k in ("model", "overall", "scores", "review_cost")}
json.dump(s, open(f"{out}/summary.json", "w"), indent=2)
print(json.dumps(s, indent=2))
EOF
if [ "${KEEP:-0}" != 1 ]; then
  git -C "$repo" worktree remove --force "$ws"
  git -C "$repo" branch -D "$branch" >/dev/null 2>&1 || true
  echo "Deleted the built app ($ws, branch $branch)"
fi
cd "$repo"
(   # runs of the two arms may finish together
  flock 9
  git add "$out"
  git commit -q -m "Bench $bench $mode $stamp (prompt $version, kit $kit)"
  git push -q origin HEAD
) 9>"$repo/.git/bench.lock"
echo "Recorded $out"
