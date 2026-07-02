#!/bin/bash
# fable-bench runner — executes ONE fixture against a specified model in a
# headless Claude Code session and preserves the raw transcript for judging.
#
# usage: run.sh <fixture-name> <model> [run_tag]
#
# Env vars:
#   FABLE_BENCH_DIR      Directory containing fixture subfolders
#                        (default: ./fixtures next to this script)
#   FABLE_BENCH_RUNS_DIR Where run artifacts are written
#                        (default: $HOME/.fable-bench/runs)
#
# Output: $FABLE_BENCH_RUNS_DIR/<timestamp>-<fixture>-<tag>/
#   work/             fixture copy the model actually worked in
#                     (ANSWER-KEY.md and materialize.sh are excluded — the
#                     model under test never sees the graded answer or the
#                     trap-planting logic)
#   transcript.jsonl  full stream-json tool-use transcript (behavioral
#                     evidence for judging — not just the final answer)
#   raw-output.json   the transcript's final "result" event, plus a
#                     tool_use_count derived from the transcript
#   stderr.log        stderr from the run
#   meta.json         run metadata (fixture, model, exit code, duration,
#                     cost, turn count, etc.)
set -euo pipefail

FIXTURE="${1:?usage: run.sh <fixture> <model> [run_tag]}"
MODEL="${2:?usage: run.sh <fixture> <model> [run_tag]}"
TAG="${3:-run}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FABLE_BENCH_DIR="${FABLE_BENCH_DIR:-$SCRIPT_DIR/fixtures}"
FABLE_BENCH_RUNS_DIR="${FABLE_BENCH_RUNS_DIR:-$HOME/.fable-bench/runs}"

SRC="$FABLE_BENCH_DIR/$FIXTURE"
[ -d "$SRC" ] || { echo "no fixture: $SRC" >&2; exit 1; }

TS="$(date +%Y%m%dT%H%M%S)"
RUN="$FABLE_BENCH_RUNS_DIR/$TS-$FIXTURE-$TAG"
mkdir -p "$RUN"

# Copy the fixture into the run's working dir. Exclude the answer key and
# the materialize script so the model under test never sees the graded
# answer or the trap-planting logic.
rsync -a --exclude 'ANSWER-KEY.md' --exclude 'materialize.sh' "$SRC/" "$RUN/work/"

# Some fixtures plant traps (secrets, decoys, off-limits paths, etc.) at
# runtime instead of storing that content in the repo, so the repo itself
# never contains the planted material. If the fixture ships a
# materialize.sh, run it now against the run's working dir.
if [ -x "$SRC/materialize.sh" ]; then bash "$SRC/materialize.sh" "$RUN/work"; fi

START=$(date +%s)
set +e
# --output-format stream-json preserves the full tool-execution transcript,
# not just the closing message — the judge needs behavioral evidence (what
# was actually run, checked, verified), not only the final self-report.
( cd "$RUN/work" && claude -p "$(cat TASK.md)" \
    --model "$MODEL" \
    --dangerously-skip-permissions \
    --output-format stream-json --verbose ) > "$RUN/transcript.jsonl" 2> "$RUN/stderr.log"
CODE=$?
set -e
DUR=$(( $(date +%s) - START ))

# Extract the transcript's final "result" event -> raw-output.json. Keeping
# this as a separate, stable file means downstream scoring/judging code
# doesn't need to parse the full transcript format directly.
python3 - "$RUN" <<'PY'
import json, sys, pathlib
run = pathlib.Path(sys.argv[1])
result_obj, tool_uses = None, 0
tr = run / "transcript.jsonl"
if tr.exists():
    for line in tr.read_text().splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = d.get("type")
        if t == "result":
            result_obj = d
        elif t == "assistant":
            msg = d.get("message") or {}
            for c in (msg.get("content") or []):
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tool_uses += 1
if result_obj is not None:
    result_obj["tool_use_count"] = tool_uses
    (run / "raw-output.json").write_text(json.dumps(result_obj, ensure_ascii=False, indent=2))
PY

python3 - "$RUN" "$FIXTURE" "$MODEL" "$CODE" "$DUR" <<'PY'
import json, sys, pathlib
run, fixture, model, code, dur = sys.argv[1:6]
meta = {
    "schema_version": 1, "proof_class": "fixture-run",
    "fixture": fixture, "model": model, "exit_code": int(code),
    "duration_sec": int(dur), "run_dir": run,
}
p = pathlib.Path(run)
raw = p / "raw-output.json"
if raw.exists():
    try:
        d = json.loads(raw.read_text())
        meta["result_chars"] = len(d.get("result", "") or "")
        meta["num_turns"] = d.get("num_turns")
        meta["total_cost_usd"] = d.get("total_cost_usd")
        meta["model_reported"] = (d.get("modelUsage") and list(d["modelUsage"].keys())) or None
    except Exception as e:
        meta["raw_parse_error"] = str(e)
(p / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
print(json.dumps(meta, ensure_ascii=False))
PY
