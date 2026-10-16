#!/usr/bin/env bash
# Start a team run in a fresh lead session; measure it after you exit the session.
#
#   kit/run.sh results/runs/<run>/spec.md [variant]
#
# With a variant, the run happens on branch run/<run>/<variant>, created from tag
# run/<run>/base when it doesn't exist yet. After the session, the run's cost report goes to
# results/metrics/<run>-<variant>.json, is compared with the other variants' reports, and is
# committed and pushed.
#
# Lead settings come from the environment (defaults are the rules' run lead):
#   LEAD_MODEL=sonnet  LEAD_EFFORT=medium  CACHE_TTL=5m
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
spec=${1:?usage: kit/run.sh results/runs/<run>/spec.md [variant]}
[ -f "$spec" ] || { echo "No such spec: $spec" >&2; exit 1; }
variant=${2:-}
run=$(basename "$(dirname "$spec")")
name=${variant:-run}
branch=""
if [ -n "$variant" ]; then
  branch="run/$run/$variant"
  git diff --quiet && git diff --cached --quiet || { echo "Commit or stash your changes first." >&2; exit 1; }
  if git rev-parse -q --verify "refs/heads/$branch" >/dev/null; then
    git checkout -q "$branch"
  else
    git checkout -q -b "$branch" "run/$run/base"
  fi
fi

model=${LEAD_MODEL:-sonnet}
effort=${LEAD_EFFORT:-medium}
ttl=${CACHE_TTL:-5m}
label="lead=$model effort=$effort cache=$ttl"
session=$(python3 -c 'import uuid; print(uuid.uuid4())')
end_file="results/runs/$run/$name.end"
metrics="results/metrics/$run-$name.json"
echo "Run $run${variant:+ variant $variant}: $label, session $session"

CLAUDE_CODE_PROMPT_CACHE_TTL=$ttl claude --session-id "$session" --model "$model" --effort "$effort" \
  "Run $spec as the lead${variant:+, variant $variant on branch $branch}. Your end-time file is $end_file." \
  || true

# Measured after the session ends, so every message in the transcript is complete.
[ -f "$end_file" ] || { echo "No $end_file: the run did not finish, so it was not measured." >&2; exit 1; }
python3 kit/tools/teamcost.py --session "$session" --until "$(cat "$end_file")" \
  --label "$label" --json "$metrics"
files=("$metrics")
if [ -n "$variant" ]; then
  for other in $(git for-each-ref --format='%(refname:short)' "refs/heads/run/$run/" \
                 | sed "s#^run/$run/##" | grep -vx "$variant" || true); do
    other_json="results/metrics/$run-$other.json"
    git show "run/$run/$other:$other_json" > "$other_json" 2>/dev/null || { rm -f "$other_json"; continue; }
    a=$other; b=$variant
    if [[ "$other" > "$variant" ]]; then a=$variant; b=$other; fi
    out="results/runs/$run/compare-$a-$b.md"
    python3 kit/tools/teamcost.py --compare "results/metrics/$run-$a.json" "results/metrics/$run-$b.json" | tee "$out"
    files+=("$other_json" "$out")
  done
fi
git add "${files[@]}"
git commit -q -m "Run $run${variant:+ variant $variant}: cost report ($label)"
git push -q origin HEAD
echo "Committed and pushed: ${files[*]}"
