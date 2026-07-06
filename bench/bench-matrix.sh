#!/bin/bash
# fable-bench matrix — fixtures x arms x seeds, bounded parallelism, resume-safe.
#
# usage: bench-matrix.sh [max_parallel] [seeds] [runs_dir]
#   defaults: parallel=3, seeds=2, runs_dir=$HOME/.fable-bench/cycle4-runs
#
# Seeds are independent re-samples of the same combo (the API has no seed
# control; the label is bookkeeping). n=1-per-combo was cycle3's loudest
# validity threat — a single 96↔68 swing dominated an arm average.
#
# Resume: a combo is skipped when a run dir matching *-<fixture>-<tag>-s<N>
# already contains meta.json, so a killed matrix relaunches where it stopped.
# Fixtures whose directory doesn't exist yet (e.g. pending review) are
# skipped with a notice — rerun the matrix after they land and only the
# missing combos execute.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$SCRIPT_DIR")"
MAXP="${1:-3}"
SEEDS="${2:-2}"
RUNS="${3:-${FABLE_BENCH_RUNS_DIR:-$HOME/.fable-bench/cycle4-runs}}"
export FABLE_BENCH_RUNS_DIR="$RUNS"

FIXTURES=(example-codefix pipe-exit-masking absence-claim-trap fact-check-bidirectional
          delegation-evidence-trap deck-outline knowledge-store-plan qa-cards-no-fabrication
          continuation-trap destructive-surfacing
          image-edit-decision threads-style-fidelity research-recency-conflict digest-skip-gate)
# arm = model:harness:tag
ARMS=("claude-opus-4-8:vanilla:opus-van" "claude-opus-4-8:tofable:opus-tof"
      "claude-sonnet-5:vanilla:son-van" "claude-sonnet-5:tofable:son-tof"
      "claude-sonnet-5:tofable-compact:son-tofc")

mkdir -p "$RUNS"
echo "matrix: ${#FIXTURES[@]} fixtures x ${#ARMS[@]} arms x ${SEEDS} seeds -> $RUNS (parallel=$MAXP)"
i=0
for f in "${FIXTURES[@]}"; do
  if [ ! -d "$REPO/bench/fixtures/$f" ]; then echo "skip (no fixture yet): $f"; continue; fi
  for arm in "${ARMS[@]}"; do
    model="${arm%%:*}"; rest="${arm#*:}"; harness="${rest%%:*}"; base="${rest#*:}"
    for seed in $(seq 1 "$SEEDS"); do
      tag="$base-s$seed"
      done_already=0
      for d in "$RUNS"/*-"$f"-"$tag"; do
        [ -f "$d/meta.json" ] && done_already=1 && break
      done
      if [ "$done_already" = "1" ]; then echo "skip (done): $f/$tag"; continue; fi
      while [ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$MAXP" ]; do sleep 5; done
      i=$((i+1))
      echo "[$i] launch: $f x $tag"
      ( "$REPO/bench/run.sh" "$f" "$model" "$tag" "$harness" >/dev/null 2>&1 \
          && echo "done: $f/$tag" || echo "FAIL: $f/$tag" ) &
      sleep 2
    done
  done
done
wait
echo "--- matrix complete ---"
ls "$RUNS" | wc -l
