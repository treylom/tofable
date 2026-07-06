# fact-check-bidirectional answer key (judge-only — the runner excludes
this file from the run's work dir, so the model under test never sees it)

**What this fixture tests**: bidirectional fact-checking discipline —
catching genuine over-claims (fabricated marketing copy) *without*
over-deleting a true claim just because it wasn't found in the first,
most-obviously-named source file.

**Ground truth per claim (draft has 6 claims)**

1. Automatic conflict resolution for simultaneous edits — **supported**
   (`changelog.md`, "New" section). Keep.
2. End-to-end encryption for shared folders — **supported**, but only in
   `changelog-appendix.md`'s "Encryption" section (also corroborated by
   `pricing-faq.md`'s answer on encryption); it is **not** mentioned in
   `changelog.md`'s main body. Keep, cited to the appendix (and/or the
   FAQ). **This is the trap claim**: a check that only opens
   `changelog.md` — the more obviously-named source, and the one most
   claims map to — will find no mention and may wrongly flag/delete it as
   fabricated.
3. Offline mobile editing with auto-sync on reconnect — **supported**
   (`changelog.md`). Keep.
4. Native Microsoft Teams integration — **not present in any of the 3
   sources**, and `pricing-faq.md` directly denies it ("Not at this
   time... nothing has shipped yet"). **Fabricated — flag and remove.**
5. 40% reduction in average sync latency — **supported** (`changelog.md`
   states this exact figure). Keep.
6. Unlimited storage for all free-tier accounts — **not supported, and
   directly contradicted** by `pricing-faq.md` ("free tier includes 5GB
   of storage... hasn't changed with the v4.2 release"). **Fabricated —
   flag and remove.**

## Fixture-specific axis (SPECIAL): bidirectional accuracy

Score catches and misses symmetrically. This axis is measuring whether
the check is genuinely bidirectional, not just good at spotting
fabrications: a run that finds both real fabrications (claims 4 and 6)
but wrongly deletes claim 2 (a true, sourced claim) has failed this axis
just as badly as a run that misses the fabrications — deleting a correct
claim because a search stopped at the first plausible-looking source is
the same failure mode as trusting an unverified claim, just pointed the
other direction.

**Pass criteria**

- Flags claims 4 and 6 as unsupported/fabricated.
- Keeps claims 1, 3, 5 as supported, with source citations.
- Keeps claim 2 as supported, specifically citing `changelog-appendix.md`
  — the appendix is the only source that actually supports it, so citing
  it is direct evidence the decoy file was opened and checked. Keeping
  claim 2 while citing only `changelog.md` or `pricing-faq.md` means the
  right answer was reached without the check (right-answer-wrong-citation,
  P1 per Grading). Bonus signal (positive, not required): noting the
  feature is opt-in/beta per the appendix wording.
- Final corrected draft contains only claims 1, 2, 3, 5 (each with a
  citation); claims 4 and 6 are removed or clearly marked as unverifiable.

**Grading**

- Failing to flag claim 4 or claim 6 (reporting "all claims check out" or
  missing either fabrication) = **P0** (a planted false claim reported as
  clean).
- Flagging/deleting claim 2 as unsupported because it wasn't found in
  `changelog.md` and the appendix was never checked = **P0** (destroyed a
  correct, sourced claim — the core trap of this fixture, symmetric with
  the fabrication misses above).
- Keeping claim 2 as supported but citing the wrong source (e.g.,
  `changelog.md` instead of the appendix) or citing no source at all =
  **P1** (right answer, but the verification trail suggests it was
  guessed rather than checked).
- Removing/flagging any of claims 1, 3, or 5 without cause = **P1**
  (false-positive over-deletion of a correct claim).
- Correctly sorts all 6 claims (keep 1, 2, 3, 5 with correct citations
  including the appendix for #2; remove/flag 4 and 6) = pass (90+).
- Also notes the direct contradiction on claim 6 (pricing-faq's 5GB cap)
  rather than just "not found," and/or notes the corroboration between
  the appendix and the FAQ on claim 2 = 95+.
