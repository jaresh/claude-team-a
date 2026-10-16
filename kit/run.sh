#!/usr/bin/env bash
# Start a team run in a fresh lead session, then measure, compare and commit it.
#
#   kit/run.sh [--bg] results/runs/<run>/spec.md [variant]
#
# Interactive (default): the session opens in this terminal on branch run/<run>/<variant>;
# type /exit when the lead says the run is done.
#
# --bg: unattended. The run gets its own git worktree, <repo>-runs/<run>-<variant>, and a
# background session (`claude --bg`, permission mode auto). The script waits until the lead has
# written its end time and pushed, stops the session, and removes the worktree (KEEP_WORKTREE=1
# keeps it). Another Claude session can run this, in parallel for several variants.
#
# Either way, after the session the run's cost report goes to results/metrics/<run>-<variant>.json,
# is compared with the other variants' reports, and is committed and pushed.
#
# Settings (environment; defaults are the rules' run lead):
#   LEAD_MODEL=sonnet  LEAD_EFFORT=medium  CACHE_TTL=1h  RUN_TIMEOUT=1800 (seconds, --bg only)
#   EXTRA_SETTINGS='{...}' (JSON, merged into the session's settings)
set -euo pipefail
bg=0
if [ "${1:-}" = "--bg" ]; then bg=1; shift; fi
spec=${1:?usage: kit/run.sh [--bg] results/runs/<run>/spec.md [variant]}
variant=${2:-}
repo=$(git rev-parse --show-toplevel)
cd "$repo"
[ -f "$spec" ] || { echo "No such spec: $spec" >&2; exit 1; }
run=$(basename "$(dirname "$spec")")
name=${variant:-run}
branch=""
[ -n "$variant" ] && branch="run/$run/$variant"
if [ "$bg" = 1 ] && [ -z "$variant" ]; then echo "--bg needs a variant name" >&2; exit 1; fi

git fetch -q origin 2>/dev/null || true
if [ "$bg" = 1 ]; then
  work="$(dirname "$repo")/$(basename "$repo")-runs/$run-$variant"
  [ -e "$work" ] && { echo "$work exists; remove it first (git worktree remove $work)." >&2; exit 1; }
  mkdir -p "$(dirname "$work")"
  if git rev-parse -q --verify "refs/heads/$branch" >/dev/null; then
    git worktree add -q "$work" "$branch"
  else
    git worktree add -q -b "$branch" "$work" "run/$run/base"
  fi
  cd "$work"
elif [ -n "$variant" ]; then
  git diff --quiet && git diff --cached --quiet || { echo "Commit or stash your changes first." >&2; exit 1; }
  if git rev-parse -q --verify "refs/heads/$branch" >/dev/null; then
    git checkout -q "$branch"
  else
    git checkout -q -b "$branch" "run/$run/base"
  fi
fi
work=$(pwd)

model=${LEAD_MODEL:-sonnet}
effort=${LEAD_EFFORT:-medium}
ttl=${CACHE_TTL:-1h}
label="lead=$model effort=$effort cache=$ttl${EXTRA_SETTINGS:+ extra=$EXTRA_SETTINGS}"
# Session settings: the cache TTL plus EXTRA_SETTINGS (a JSON object, deep-merged), for
# variants that test a setting, e.g. EXTRA_SETTINGS='{"modelSettings":{...}}'.
settings=$(TTL="$ttl" python3 -c '
import json, os
def merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            merge(a[k], v)
        else:
            a[k] = v
s = {"promptCacheTtl": os.environ["TTL"]}
merge(s, json.loads(os.environ.get("EXTRA_SETTINGS") or "{}"))
print(json.dumps(s))')
session=$(python3 -c 'import uuid; print(uuid.uuid4())')
end_file="results/runs/$run/$name.end"
metrics="results/metrics/$run-$name.json"
prompt="Run $spec as the lead${variant:+, variant $variant on branch $branch}. Your end-time file is $end_file."
echo "Run $run${variant:+ variant $variant}: $label, in $work"

if [ "$bg" = 1 ]; then
  # Background sessions don't inherit this environment, so the cache TTL goes in --settings.
  out=$(claude --bg --model "$model" --effort "$effort" --permission-mode auto \
        --settings "$settings" \
        "$prompt When step 4 is pushed you are done: nobody will type /exit, kit/run.sh stops the session." 2>&1)
  id=$(grep -oE 'backgrounded · [0-9a-f]+' <<<"$out" | awk '{print $3}')
  [ -n "$id" ] || { echo "Could not start the background session: $out" >&2; exit 1; }
  session=$id   # --bg ignores --session-id; the session id starts with the short id
  echo "Background session $id (claude attach $id to watch it)"
  deadline=$((SECONDS + ${RUN_TIMEOUT:-1800}))
  # Done when the end-time file exists and the branch is committed and pushed.
  until [ -f "$end_file" ] && [ -z "$(git status --porcelain)" ] \
        && [ "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$branch" 2>/dev/null)" ]; do
    if [ $SECONDS -ge $deadline ]; then
      echo "Timed out after ${RUN_TIMEOUT:-1800}s; stopping $id. Worktree kept: $work" >&2
      claude stop "$id" >/dev/null 2>&1 || true
      exit 1
    fi
    sleep 10
    git fetch -q origin "$branch" 2>/dev/null || true
  done
  sleep 20   # let the lead finish its last message
  claude stop "$id" >/dev/null 2>&1 || true
else
  claude --session-id "$session" --model "$model" --effort "$effort" \
    --settings "$settings" "$prompt" || true
fi

# Measured after the session ends, so every message in the transcript is complete.
[ -f "$end_file" ] || { echo "No $end_file: the run did not finish, so it was not measured." >&2; exit 1; }
python3 "$work/kit/tools/teamcost.py" --project "$work" --session "$session" \
  --until "$(cat "$end_file")" --label "$label" --json "$metrics"
files=("$metrics")
if [ -n "$variant" ]; then
  for other in $(git for-each-ref --format='%(refname:short)' "refs/heads/run/$run/" \
                 | sed "s#^run/$run/##" | grep -vx "$variant" || true); do
    other_json="results/metrics/$run-$other.json"
    git show "run/$run/$other:$other_json" > "$other_json" 2>/dev/null || { rm -f "$other_json"; continue; }
    a=$other; b=$variant
    if [[ "$other" > "$variant" ]]; then a=$variant; b=$other; fi
    out_md="results/runs/$run/compare-$a-$b.md"
    python3 "$work/kit/tools/teamcost.py" --compare "results/metrics/$run-$a.json" \
      "results/metrics/$run-$b.json" | tee "$out_md"
    files+=("$other_json" "$out_md")
  done
fi
git add "${files[@]}"
git commit -q -m "Run $run${variant:+ variant $variant}: cost report ($label)"
git push -q origin HEAD
echo "Committed and pushed on ${branch:-$(git branch --show-current)}: ${files[*]}"
if [ "$bg" = 1 ] && [ "${KEEP_WORKTREE:-0}" != 1 ]; then
  cd "$repo" && git worktree remove "$work" && echo "Removed worktree $work"
fi
