# Cycle 2 runbook — what the next measurement pass must answer

Drafted 2026-07-12 (pre-registered before running, so the questions can't
drift toward whatever the numbers happen to show).

## Questions, in priority order

1. **Do the two newest gates move their target axes?**
   `subordinate-evidence` → `delegation-evidence-trap`, `blind-retry-gate` →
   `blind-retry-diagnosis`. Arms: harness-on vs vanilla, 2–3 seeds each.
   Expected shape (from cycle 1's exchange rate): one gate ≈ one defect axis
   removed on its target fixture; no regression elsewhere.
2. **Does ledger v5.1 keep the gate's catch rate while cutting friction?**
   Replay corpus must stay 5/5 blocked (it does — verified at patch time).
   Live side: sample new-session ledgers after a week; the
   "bounced-with-evidence-already-present" share should drop from ~96% of
   change sessions to near the true-positive floor.
3. **Rubric v2 re-baseline.** Cycle-1 numbers are rubric v1 (A1–A5+SPECIAL);
   v2 adds A6–A8 process axes. Re-run the 14-fixture set under v2 so the
   public scoreboard becomes v2-comparable. Do not average v1 and v2.
4. **Judge diversity.** Cycle 1 was single cross-family judge; add a second
   judge family on at least the fixtures where a defect grade decides the
   headline, and report agreement.

## Mechanics

```bash
# per fixture × model × seed
bench/run.sh <fixture> <model-id> cycle2-<arm>-s<seed>
# grade with a cross-family judge, rubric v2
bench/judge-run.sh <run-dir>
# aggregate
python3 bench/aggregate.py ~/.fable-bench/runs --out results-cycle2.md
```

- Substrate snapshot taken 2026-07-12 (pre-transition):
  `{"replay_blocked":5,"replay_total":5,"probes_pass":6,"probes_total":6,"hooks_present":9}`.
  Re-run `bench/substrate-check.sh` after any reasoning-model transition —
  the delta must be 0 before behavioral numbers are compared across it.
- Threats to validity to carry into the writeup: 2–3 seeds per cell
  (±10-point per-fixture noise — read arm averages), fixture set is one
  user's workload sample, v1↔v2 scores are not average-comparable.
