#!/bin/bash
# fable-bench Codex runner — executes ONE fixture against Codex in either a
# stock arm (codex-van) or the bundled tofable Codex gate arm (codex-tof).
#
# usage: run-codex.sh <fixture-name> <model|codex-default> [run_tag] [harness]
#
# Output mirrors bench/run.sh:
#   work/             fixture copy under test
#   transcript.jsonl  stdout event stream from `codex exec --json`
#   rollouts/         persisted Codex session JSONL files copied from CODEX_HOME
#   transcript.txt    plain dialogue adapter output for the judge
#   raw-output.json   last Codex result event plus coarse tool-use count
#   stderr.log        stderr from Codex
#   meta.json         run metadata, including fable-state ledger presence
set -euo pipefail

FIXTURE="${1:?usage: run-codex.sh <fixture> <model|codex-default> [run_tag] [harness]}"
MODEL="${2:?usage: run-codex.sh <fixture> <model|codex-default> [run_tag] [harness]}"
TAG="${3:-run}"
HARNESS="${4:-codex-van}"
case "$HARNESS" in codex-van|codex-tof) ;; *) echo "harness must be codex-van|codex-tof" >&2; exit 1;; esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
FABLE_BENCH_DIR="${FABLE_BENCH_DIR:-$SCRIPT_DIR/fixtures}"
FABLE_BENCH_RUNS_DIR="${FABLE_BENCH_RUNS_DIR:-$HOME/.fable-bench/runs}"

SRC="$FABLE_BENCH_DIR/$FIXTURE"
[ -d "$SRC" ] || { echo "no fixture: $SRC" >&2; exit 1; }
[ -f "$SRC/TASK.md" ] || { echo "fixture missing TASK.md: $SRC" >&2; exit 1; }

TS="$(date +%Y%m%dT%H%M%S)"
RUN="$FABLE_BENCH_RUNS_DIR/$TS-$FIXTURE-$TAG"
mkdir -p "$RUN"

rsync -a --exclude 'ANSWER-KEY.md' --exclude 'materialize.sh' "$SRC/" "$RUN/work/"
if [ -x "$SRC/materialize.sh" ]; then bash "$SRC/materialize.sh" "$RUN/work"; fi

CODEX_HOME_DIR="$RUN/codex-home"
mkdir -p "$CODEX_HOME_DIR"
chmod 700 "$CODEX_HOME_DIR"
if [ -f "$HOME/.codex/auth.json" ]; then
  cp "$HOME/.codex/auth.json" "$CODEX_HOME_DIR/auth.json"
  chmod 600 "$CODEX_HOME_DIR/auth.json"
fi
if [ -f "$HOME/.codex/installation_id" ]; then
  cp "$HOME/.codex/installation_id" "$CODEX_HOME_DIR/installation_id"
fi
cleanup_auth() {
  rm -f "$CODEX_HOME_DIR/auth.json"
}
trap cleanup_auth EXIT

export FABLE_STATE_DIR="$RUN/fable-state"
mkdir -p "$FABLE_STATE_DIR"

EXTRA_ARGS=()
if [ "$MODEL" != "codex-default" ] && [ "$MODEL" != "default" ]; then
  EXTRA_ARGS+=(--model "$MODEL")
fi

if [ "$HARNESS" = "codex-tof" ]; then
  python3 - "$REPO_DIR" "$CODEX_HOME_DIR/hooks.json" <<'PY'
import json
import pathlib
import sys

repo = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2])
data = json.loads((repo / "codex" / "gates" / "hooks.json").read_text(encoding="utf-8"))

def replace(value):
    if isinstance(value, str):
        return value.replace("${PLUGIN_ROOT}", str(repo))
    if isinstance(value, list):
        return [replace(item) for item in value]
    if isinstance(value, dict):
        return {key: replace(item) for key, item in value.items()}
    return value

out.write_text(json.dumps(replace(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  EXTRA_ARGS+=(--dangerously-bypass-hook-trust)
fi

START=$(date +%s)
set +e
( cd "$RUN/work" && CODEX_HOME="$CODEX_HOME_DIR" FABLE_STATE_DIR="$FABLE_STATE_DIR" codex exec \
    --ignore-user-config \
    --skip-git-repo-check \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    --output-last-message "$RUN/last-message.txt" \
    --cd "$RUN/work" \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
    "$(cat TASK.md)" ) < /dev/null > "$RUN/transcript.jsonl" 2> "$RUN/stderr.log"
CODE=$?
set -e
DUR=$(( $(date +%s) - START ))

mkdir -p "$RUN/rollouts"
if [ -d "$CODEX_HOME_DIR/sessions" ]; then
  while IFS= read -r -d '' file; do
    cp "$file" "$RUN/rollouts/$(basename "$file")"
  done < <(find "$CODEX_HOME_DIR/sessions" -type f -name '*.jsonl' -print0)
fi
cleanup_auth

python3 "$SCRIPT_DIR/codex-transcript-to-text.py" "$RUN" -o "$RUN/transcript.txt" || true

python3 - "$RUN" <<'PY'
import json
import pathlib
import sys

run = pathlib.Path(sys.argv[1])
result_obj = None
tool_uses = 0
for line in (run / "transcript.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
    try:
        event = json.loads(line)
    except Exception:
        continue
    if not isinstance(event, dict):
        continue
    kind = event.get("type") or event.get("event")
    item = event.get("item")
    if kind == "result":
        result_obj = event
    if isinstance(item, dict) and event.get("type") == "item.completed":
        if item.get("type") in {"command_execution", "file_change"}:
            tool_uses += 1
    if kind in {"tool_call", "tool_use"}:
        tool_uses += 1
    if kind == "assistant":
        message = event.get("message") or {}
        if isinstance(message, dict):
            for content in message.get("content") or []:
                if isinstance(content, dict) and content.get("type") == "tool_use":
                    tool_uses += 1
if result_obj is None:
    last = run / "last-message.txt"
    result_obj = {"type": "result", "result": last.read_text(encoding="utf-8", errors="replace") if last.exists() else ""}
result_obj["tool_use_count"] = tool_uses
(run / "raw-output.json").write_text(json.dumps(result_obj, ensure_ascii=False, indent=2), encoding="utf-8")
PY

python3 - "$RUN" "$FIXTURE" "$MODEL" "$CODE" "$DUR" "$HARNESS" <<'PY'
import json
import pathlib
import sys

run_s, fixture, model, code, dur, harness = sys.argv[1:7]
run = pathlib.Path(run_s)
ledgers = sorted((run / "fable-state").glob("ledgers/*.json"))
rollouts = sorted((run / "rollouts").glob("*.jsonl"))
meta = {
    "schema_version": 1,
    "proof_class": "codex-fixture-run",
    "fixture": fixture,
    "model": model,
    "harness": harness,
    "exit_code": int(code),
    "duration_sec": int(dur),
    "run_dir": str(run),
    "codex_home": str(run / "codex-home"),
    "transcript_jsonl": str(run / "transcript.jsonl"),
    "transcript_txt": str(run / "transcript.txt"),
    "rollout_count": len(rollouts),
    "fable_state_dir": str(run / "fable-state"),
    "fable_ledger_count": len(ledgers),
    "fable_ledgers": [str(path.relative_to(run)) for path in ledgers],
}
raw = run / "raw-output.json"
if raw.exists():
    try:
        data = json.loads(raw.read_text(encoding="utf-8"))
        meta["result_chars"] = len(data.get("result", "") or "")
        meta["tool_use_count"] = data.get("tool_use_count")
    except Exception as exc:
        meta["raw_parse_error"] = str(exc)
(run / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False))
PY

exit "$CODE"
