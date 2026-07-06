#!/usr/bin/env python3
"""Aggregate judged bench runs into arm/fixture tables + a tiebreak list.

usage: aggregate.py [runs_dir]   (default: $FABLE_BENCH_RUNS_DIR or ~/.fable-bench/cycle4-runs)

Reads every run dir containing meta.json + judge.json. Seeds are runs whose
tag ends in -s<N>; they aggregate per (fixture, arm) as mean score and the
WORST defect grade across seeds (a defect that appears in any seed is real
enough to count). Combos whose seeds diverge (>TIEBREAK_PTS points or a
P0/P1 grade mismatch) are listed with ready-to-run s3 commands.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

TIEBREAK_PTS = 8.0
SEED_RE = re.compile(r"^(?P<base>.+)-s(?P<seed>\d+)$")
ARM_ORDER = ["opus-van", "opus-tof", "opus-tof2", "son-van", "son-tof", "son-tof2", "son-tofc"]
ARM_HARNESS = {"opus-van": "vanilla", "opus-tof": "tofable", "opus-tof2": "tofable",
               "son-van": "vanilla", "son-tof": "tofable", "son-tof2": "tofable",
               "son-tofc": "tofable-compact"}
ARM_MODEL = {"opus-van": "claude-opus-4-8", "opus-tof": "claude-opus-4-8",
             "opus-tof2": "claude-opus-4-8",
             "son-van": "claude-sonnet-5", "son-tof": "claude-sonnet-5",
             "son-tof2": "claude-sonnet-5", "son-tofc": "claude-sonnet-5"}
# Defect-integrated score: fold P0/P1 into the number itself so defects
# can't hide behind style points. Per fixture×arm cell,
# composite = seed-mean − P0_PENALTY·p0 − P1_PENALTY·p1
# (defect counts = max across seeds, same rule the flags use). Weights chosen
# so one P0 outweighs any style-point spread (~judge noise band) and can't be
# washed out by a pretty report; sensitivity to ±50% weight changes is worth
# checking before reading small composite gaps.
P0_PENALTY = 15.0
P1_PENALTY = 5.0


def tag_of(run_dir_name: str, fixture: str) -> str:
    # <timestamp>-<fixture>-<tag>
    marker = f"-{fixture}-"
    idx = run_dir_name.find(marker)
    return run_dir_name[idx + len(marker):] if idx >= 0 else run_dir_name


def defect_counts(defects: list[dict]) -> tuple[int, int]:
    p0 = sum(1 for d in defects if str(d.get("grade", "")).upper() == "P0")
    p1 = sum(1 for d in defects if str(d.get("grade", "")).upper() == "P1")
    return p0, p1


def main() -> int:
    runs = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "FABLE_BENCH_RUNS_DIR", str(Path.home() / ".fable-bench" / "cycle4-runs")))
    combos: dict[tuple[str, str], list[dict]] = defaultdict(list)  # (fixture, base_tag) -> seed rows
    for d in sorted(runs.glob("*/")):
        meta_p, judge_p = d / "meta.json", d / "judge.json"
        if not (meta_p.exists() and judge_p.exists()):
            continue
        meta = json.loads(meta_p.read_text())
        judge = json.loads(judge_p.read_text())
        fixture = meta.get("fixture", "?")
        tag = tag_of(d.name, fixture)
        m = SEED_RE.match(tag)
        base, seed = (m.group("base"), int(m.group("seed"))) if m else (tag, 1)
        p0, p1 = defect_counts(judge.get("defects", []))
        combos[(fixture, base)].append({
            "seed": seed, "avg": float(judge.get("avg") or 0.0), "p0": p0, "p1": p1,
            "cost": float(meta.get("total_cost_usd") or 0.0), "dur": int(meta.get("duration_sec") or 0),
            "dir": d.name,
        })

    if not combos:
        print(f"no judged runs under {runs}")
        return 1

    # per-(fixture, arm): mean avg across seeds, max defects across seeds
    cell: dict[tuple[str, str], dict] = {}
    for (fixture, base), rows in combos.items():
        rows.sort(key=lambda r: r["seed"])
        cell[(fixture, base)] = {
            "mean": sum(r["avg"] for r in rows) / len(rows),
            "n": len(rows),
            "p0": max(r["p0"] for r in rows),
            "p1": max(r["p1"] for r in rows),
            "spread": (max(r["avg"] for r in rows) - min(r["avg"] for r in rows)) if len(rows) > 1 else 0.0,
            "rows": rows,
        }

    fixtures = sorted({f for f, _ in cell})
    arms = [a for a in ARM_ORDER if any(b == a for _, b in cell)] or sorted({b for _, b in cell})

    print(f"# aggregate — {runs}  (judged combos: {len(cell)})\n")
    print("## Arm scoreboard (mean of per-fixture seed-means)")
    print(f"composite = avg − {P0_PENALTY:.0f}·P0 − {P1_PENALTY:.0f}·P1 per fixture cell "
          "(defects can't hide behind style points)")
    print("| arm | fixtures | avg | **composite** | P0 | P1 | cost | avg dur |")
    print("|---|---|---|---|---|---|---|---|")
    for a in arms:
        cs = [c for (f, b), c in cell.items() if b == a]
        if not cs:
            continue
        rows = [r for c in cs for r in c["rows"]]
        composite = sum(max(0.0, c["mean"] - P0_PENALTY * c["p0"] - P1_PENALTY * c["p1"]) for c in cs) / len(cs)
        print(f"| {a} | {len(cs)} | {sum(c['mean'] for c in cs)/len(cs):.1f} "
              f"| **{composite:.1f}** "
              f"| {sum(c['p0'] for c in cs)} | {sum(c['p1'] for c in cs)} "
              f"| ${sum(r['cost'] for r in rows):.2f} | {sum(r['dur'] for r in rows)//max(len(rows),1)}s |")

    print("\n## Fixture x arm (seed-mean, defects flagged)")
    print("| fixture | " + " | ".join(arms) + " |")
    print("|---|" + "---|" * len(arms))
    for f in fixtures:
        cells = []
        for a in arms:
            c = cell.get((f, a))
            if not c:
                cells.append("—")
                continue
            flag = (" P0!" if c["p0"] else "") + (" P1!" if c["p1"] else "")
            cells.append(f"{c['mean']:.1f}{flag} (n={c['n']})")
        print(f"| {f} | " + " | ".join(cells) + " |")

    print("\n## Tiebreak candidates (seed spread > "
          f"{TIEBREAK_PTS} pts or seeds disagree on P0/P1)")
    any_tb = False
    for (f, b), c in sorted(cell.items()):
        if c["n"] < 2:
            continue
        grades = {(r["p0"] > 0, r["p1"] > 0) for r in c["rows"]}
        if c["spread"] > TIEBREAK_PTS or len(grades) > 1:
            any_tb = True
            model, harness = ARM_MODEL.get(b, "?"), ARM_HARNESS.get(b, "?")
            print(f"- {f}/{b}: spread={c['spread']:.1f} "
                  f"seeds={[r['avg'] for r in c['rows']]} -> "
                  f"bench/run.sh {f} {model} {b}-s3 {harness}")
    if not any_tb:
        print("- none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
