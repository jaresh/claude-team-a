#!/usr/bin/env bash
# Benchmark run: one fixed prompt, built by the team or by a single model session in a fresh
# empty repo, then scored with hidden acceptance tests, measured, recorded, and deleted.
#
#   bench/run.sh <bench> team|solo      e.g. bench/run.sh finance team
#
# team: team_kit.py is installed in the workspace and the session starts as `team_kit.py lead`
#       does; the prompt says "Work with team on it."
# solo: no kit, no subagents (the Agent tool is removed too); the prompt says to do the work
#       alone. Otherwise the same tools as team mode.
# Both: the same model (MODEL=sonnet), effort (EFFORT=medium) and 1-hour prompt cache.
#
# Every run is scored three ways: the hidden acceptance tests, code-quality metrics
# (bench/quality.py), and a blind review by a fixed reviewer (REVIEW_MODEL=opus, REVIEW_EFFORT=
# medium, read-only tools, rubric in bench/<bench>/review.md) after .claude/ is removed, so it
# can't tell the arm. The review's cost is recorded apart from the run's.
#
# Results go to bench/<bench>/results/<UTC stamp>-<mode>/ (cost, scores, quality, review, the
# team's plan and handoffs, the app's README) and are committed. The built app is deleted
# (KEEP=1 keeps it).
#
# The workspace is bench/work/<bench>-<mode> (git-ignored): a git worktree of this repo on an
# empty orphan branch, bench/<bench>-<mode>, re-created for each run. A worktree shares this
# repo's trust, so background sessions start there; a nested `git init` would not be trusted.
# Sessions there don't load this repo's CLAUDE.md, but they do list its skills and agents (the
# same for both arms; solo has no Agent tool). Auto memory is off in both arms.
set -euo pipefail
bench=${1:?usage: bench/run.sh <bench> team|solo}
mode=${2:?usage: bench/run.sh <bench> team|solo}
repo=$(git rev-parse --show-toplevel)
here=$repo/bench/$bench
[ -f "$here/prompt.md" ] || { echo "No such benchmark: $bench" >&2; exit 1; }
case $mode in
  team) mode_line="Work with team on it." ;;
  solo) mode_line="Do all the work yourself in this session, without subagents." ;;
  *) echo "mode must be team or solo" >&2; exit 1 ;;
esac
model=${MODEL:-sonnet}
effort=${EFFORT:-medium}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
ws=$repo/bench/work/$bench-$mode
branch=bench/$bench-$mode
out=$here/results/$stamp-$mode
version=$(cat "$here/prompt.md" "$here"/accept/*.py "$here/review.md" "$repo/bench/quality.py" | sha256sum | cut -c1-12)

git -C "$repo" worktree remove --force "$ws" 2>/dev/null || true
git -C "$repo" branch -D "$branch" >/dev/null 2>&1 || true
mkdir -p "$(dirname "$ws")" "$out"
git -C "$repo" worktree add -q --orphan -b "$branch" "$ws"
deny=$(python3 "$repo/team_kit.py" lead --print-args)
if [ "$mode" = team ]; then
  python3 "$repo/team_kit.py" install "$ws" >/dev/null
else
  deny="$deny,Agent"
fi
prompt=$(MODE="$mode_line" python3 -c 'import os,sys; print(open(sys.argv[1]).read().replace("{{MODE}}", os.environ["MODE"]))' "$here/prompt.md")

cd "$ws"
started=$(date -u +%FT%TZ)
launch=$(claude --bg --model "$model" --effort "$effort" --permission-mode auto "$deny" \
         --settings '{"promptCacheTtl":"1h","autoMemoryEnabled":false}' "$prompt" 2>&1) || true
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

# Score: the app's own tests, then the hidden acceptance tests (never in the workspace).
(cd "$ws" && timeout 900 python3 -m unittest discover -s tests > "$out/own-tests.txt" 2>&1) || true
FIN_DIR="$ws" timeout 900 python3 -m unittest discover -s "$here/accept" -v > "$out/accept.txt" 2>&1 || true
python3 "$repo/team_kit.py" cost --project "$ws" --session "$id" --until "$(cat "$ws/.bench-end")" \
  --label "bench $bench $mode model=$model effort=$effort prompt=$version" --json "$out/cost.json" \
  > "$out/cost.txt"
[ -d "$ws/.claude/team" ] && cp -r "$ws/.claude/team" "$out/team" && rm -f "$out/team/.kit.json"
[ -f "$ws/README.md" ] && cp "$ws/README.md" "$out/app-README.md"

# Quality: metrics, then the blind review (nothing in the workspace may show which arm built it).
python3 "$repo/bench/quality.py" "$ws" --json "$out/quality.json" > /dev/null
rm -rf "$ws/.claude" "$ws/.bench-end" "$ws/fin.db"
review_prompt="$(cat "$here/review.md")
$(sed 's/ {{MODE}}//' "$here/prompt.md")"
(cd "$ws" && timeout 1800 claude -p --model "${REVIEW_MODEL:-opus}" --effort "${REVIEW_EFFORT:-medium}" \
   --tools=Read,Glob,Grep --output-format json "$review_prompt" < /dev/null > "$out/review-raw.json" 2>/dev/null) || true
python3 - "$out" <<'PY'
import json, sys
out = sys.argv[1]
try:
    raw = json.load(open(f"{out}/review-raw.json"))
    text = raw.get("result", "")
    review = json.loads(text[text.index("{"):text.rindex("}") + 1])
    review["review_cost"] = round(raw.get("total_cost_usd") or 0, 4)
except (ValueError, OSError) as e:
    review = {"error": f"no review: {e}"}
json.dump(review, open(f"{out}/review.json", "w"), indent=2)
PY
rm -f "$out/review-raw.json"
lines=$(cd "$ws" && git ls-files --others --exclude-standard --cached -- '*.py' | xargs cat 2>/dev/null | wc -l)

python3 - "$out" "$bench" "$mode" "$model" "$effort" "$version" "$started" "$(cat "$ws/.bench-end")" "$lines" <<'EOF'
import json, re, sys
out, bench, mode, model, effort, version, started, ended, lines = sys.argv[1:]
def tally(path):
    text = open(path).read()
    ran = re.search(r"Ran (\d+) test", text)
    bad = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", text.split("Ran ")[-1]))
    n = int(ran.group(1)) if ran else 0
    return n, max(n - bad, 0)
acc, own = tally(f"{out}/accept.txt"), tally(f"{out}/own-tests.txt")
cost = json.load(open(f"{out}/cost.json"))
lead = [a for a in cost["agents"] if a["role"] == "lead"]
team = [a for a in cost["agents"] if a["role"] == "teammate"]
quality = json.load(open(f"{out}/quality.json"))
review = json.load(open(f"{out}/review.json"))
s = {"bench": bench, "mode": mode, "model": model, "effort": effort, "prompt": version,
     "started": started, "ended": ended, "accept_passed": acc[1], "accept_total": acc[0],
     "own_passed": own[1], "own_total": own[0], "python_lines": int(lines),
     "cost": round(cost["total_cost"], 4), "cost_cold": round(cost["cold_start_cost"], 4),
     "lead_cost": round(sum(a["cost"] for a in lead), 4),
     "team_cost": round(sum(a["cost"] for a in team), 4),
     "teammates": [a["agent"] for a in team],
     "lead_messages": sum(a["msgs"] for a in lead),
     "lead_peak_ctx": max((a["peak_ctx"] for a in lead), default=0),
     "lead_compactions": sum(a["compactions"] for a in lead),
     "team_peak_ctx": max((a["peak_ctx"] for a in team), default=0),
     "quality": quality, "review": review}
json.dump(s, open(f"{out}/summary.json", "w"), indent=2)
print(json.dumps(s, indent=2))
EOF
if [ "${KEEP:-0}" != 1 ]; then
  git -C "$repo" worktree remove --force "$ws"
  git -C "$repo" branch -D "$branch" >/dev/null 2>&1 || true
  echo "Deleted the built app ($ws, branch $branch)"
fi
cd "$repo"
git add "$out"
git commit -q -m "Bench $bench $mode $stamp (prompt $version)"
git push -q origin HEAD
echo "Recorded $out"
