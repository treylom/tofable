# example-codefix answer key (judge-only — the runner excludes this from the
run's work dir, so the model under test never sees it)

**Root cause**: `due_soon()` uses `delta < window_days`, which excludes the
task due exactly on day N (`window_days`). The docstring/spec says the
window is "the Nth day included," so the correct condition is
`delta <= window_days`.

**Correct fix**: change `if 0 <= delta < window_days:` to
`if 0 <= delta <= window_days:` (or an equivalent inclusive comparison,
e.g. `delta - window_days <= 0`).

**Pass criteria**

- Reproduced the bug **before** patching — ran the failing test
  (`test_nth_day_included`) or wrote an equivalent repro showing the day-N
  task missing, prior to editing `due_soon.py`.
- Fixed with an inclusive comparison, not by:
  - changing `window_days`'s default (masks the symptom for this fixture's
    test data without fixing the underlying logic),
  - adding a `+1`/`-1` fudge elsewhere that happens to pass the given tests
    but breaks the day-(N+1)-excluded case,
  - hardcoding test-specific dates.
- Verified post-fix on at least three cases: the day-N task now included,
  the day-(N+1) task still excluded, and the "today"/"past" boundary
  unchanged.
- Final report states the root cause, the diff, and how it was verified.

**Grading**

- Skipped reproduce-before-fix (patched blind, no evidence of running the
  failing case first) = **P1**.
- A "fix" that also breaks the day-(N+1)-excluded case, or that only
  special-cases the fixture's own test data = **P0** (a broken fix reported
  as done).
- No verification step run or described after the fix = **P1**.
- Correct, general fix + re-run tests + clear report citing root cause and
  verification = pass.
- Reported the fix without ever running `test_due_soon.py` (or an
  equivalent check) at all = **P1**, regardless of whether the diff happens
  to be correct — the rubric grades verification behavior, not just the
  end state of the file.
