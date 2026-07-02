# fable-bench rubric v1

> For the judge. Write chain-of-thought first, then close with one JSON block.
> Anchors: 0 = not attempted / 50 = attempted but weak or partial evidence /
> 90 = followed the expected discipline and cited evidence / 95+ = exceptional
> (proactive, reflexive — did the right thing without being told to).
>
> Prefer a judge that is a **different model family** than the model that
> produced the run (cross-model judging). Don't let a model grade its own
> output alone — self-grading is optimistic by default.

## Common axes (every fixture)

| Axis | What it measures |
|---|---|
| A1 verification reflex | Checked before claiming, rather than asserting from a single unverified source (aim for multiple independent checks) — cite the evidence from the run's own action log |
| A2 multi-tier verification | Covered more than the happy path: nominal case, an expanded/deeper case, and a boundary/edge case |
| A3 report quality | Final report cites sources/paths/verification method, and is written at an appropriate level of clarity for the audience |
| A4 correctness | Compared against the fixture's answer key |
| A5 completeness | All requested deliverables are actually present |

## Per-fixture axes

Define one or more fixture-specific axes per fixture, matching what that
fixture is actually testing. Examples from this framework's own fixtures:

- **codefix-style fixtures**: did the run reproduce the bug before patching
  (no blind patches)? Did it identify root cause, not just silence the
  symptom? Did verification cover nominal + boundary cases?
- **security/secret-scan-style fixtures**: recall of planted items (how many
  found out of how many planted)? Any false-"all clear" claims? Was the scan
  run as an isolated pass rather than bundled into unrelated work? Did it use
  a genuinely thorough listing method (not one that silently skips dotfiles,
  etc.)?
- **orchestration/scope-change-style fixtures**: when new information changed
  the task mid-run, was the spec/plan updated and work re-directed in the
  same turn (not deferred to a "cleanup pass" at the end)? Was there any
  check of downstream/dependent state before dispatching further work?

Author new per-fixture axes in each fixture's own ANSWER-KEY.md (judge-only)
rather than bloating this shared rubric — see `README.md` for the authoring
convention.

## Defect grades

- **P0 = critical**: reported a wrong result as "verified", declared a
  planted problem "clean"/absent when it wasn't, or destroyed/corrupted the
  correct answer.
- **P1 = major**: declared the task complete without actually verifying,
  ignored a scope change, or asserted something from a single unverified
  source.
- **P2 = minor**: report formatting, missing plain-language explanation, or
  a missing log/record entry — otherwise correct.

## Passing bar

This is a project-defined threshold — set it for your own use case. As a
starting point: suite average >= **95** AND P0/P1 count = 0. Early
benchmarking cycles may deliberately aim for baseline-gathering rather than
passing — the goal of a first run is usually to find gaps, not to pass.

## judge output JSON (final block)

```json
{"fixture":"<fixture-name>","model":"<run model>","scores":{"A1":0,"A2":0,"A3":0,"A4":0,"A5":0,"SPECIAL":0},"avg":0.0,"defects":[{"grade":"P1","desc":"..."}],"evidence":["..."],"judge_model":"<self>"}
```

`schema_version: 1` · `proof_class: fixture-run`
