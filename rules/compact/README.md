# Compact rule variant

Same disciplines as [`rules/`](../), rewritten as imperative checklists with
the concrete commands inlined and the war stories removed (~1/3 the tokens).

Why it exists: the cycle3 A/B bench measured that prose rules translate into
behavior on some models and not on others — one model ran `git log --all`
because a rule paragraph mentioned branches; another read the same paragraph
and didn't. Models that under-translate prose tend to execute short imperative
checklists more reliably. Use this variant (bench harness arm
`tofable-compact`) for those models; keep the prose originals where they
already work — the stories carry the *why*, which transfers better on
stronger models.

1:1 coverage contract: every bullet in the originals has a numbered
counterpart here; nothing is added. If you edit one side, mirror the other.
