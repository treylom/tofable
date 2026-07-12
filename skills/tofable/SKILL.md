---
name: tofable
description: Use at the start of any non-trivial task (build / fix / analyze / deliver) to run it under the tofable working discipline — honest decomposition, prompt refinement via /prompt when installed (basic-prompting fallback when not), evidence-first execution, and honest completion. Also use when asked to "apply tofable", "work like fable", or "tofable로 진행".
---

# tofable — working discipline (skill form)

Run the task through 5 checkpoints. Do not skip one because it feels obvious; as you pass each, state it in one line.

## 0. Decompose honestly
- Restate the goal in ≤2 sentences: what the requester holds when this is done.
- Split into verifiable units — each unit names the evidence that will prove it (a command, a diff, a file, a number).
- Mark what is explicitly NOT in scope (1 line).

## 1. Refine the prompt (integration point)
- If a prompt-refinement skill is installed (e.g. `/prompt` from the `prompt-engineering-skills` plugin — check your available skills), invoke it on the task statement before executing (`/prompt --batch <task>`) and adopt the refined structure.
- If it is NOT installed, fall back to basic prompting: rewrite the task as role + context + constraints + expected output format (4 lines suffice). Never start executing from a bare one-line goal.

## 2. Execute with evidence
- After every change, run the verification that unit named (test / build / probe) — before moving on, not batched at the end.
- Delegating? The first message carries the complete HOW (tools, paths, parallelism, forbidden routes). A delegate's "done" is a claim, not evidence — re-verify after it returns.
- The same command failed twice? Stop. Diagnose before any retry.

## 3. Report blockers plainly
- Blocked = say so immediately: what is blocked, and whose decision unblocks it. Not at the end, not narrated around.
- Never invent busywork while blocked on someone else's decision.

## 4. Close honestly
- Before saying "done": re-run the top-level verification and state its grade — deterministic check / scenario replay / independent evaluator / human review.
- Any claim with a number ("83 files", "byte-identical") needs a mechanical check in the log (wc / grep -c / diff / shasum).
- Remaining gaps are listed as gaps; they are never absorbed into "done".

## Notes
- This skill is the proactive twin of the tofable gates (`hooks/` in the tofable repo): the gates bounce you when evidence is missing at stop time; this skill makes that evidence exist before the gate ever fires.
- Gates docs & kill switch: `hooks/README.md` (`FABLE_GATE_OFF=1`).
