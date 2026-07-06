#!/bin/bash
# Judge every run in a runs dir that has meta.json but no judge.json yet.
# usage: judge-all.sh [max_parallel] [runs_dir]
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAXP="${1:-3}"
RUNS="${2:-${FABLE_BENCH_RUNS_DIR:-$HOME/.fable-bench/cycle4-runs}}"
for d in "$RUNS"/*/; do
  [ -f "$d/meta.json" ] || continue
  [ -f "$d/judge.json" ] && { echo "skip (judged): $(basename "$d")"; continue; }
  while [ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$MAXP" ]; do sleep 5; done
  ( bash "$SCRIPT_DIR/judge-run.sh" "$d" ) &
  sleep 2
done
wait
echo "--- judging complete ---"
ls "$RUNS"/*/judge.json 2>/dev/null | wc -l
