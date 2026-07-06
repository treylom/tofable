# Content Brief — Clip 3: "Choosing a Branching Strategy"

**Series**: Practical Git Workflows (6-clip internal training series)
**Audience**: engineers who are comfortable with basic git commands (add,
commit, push, pull) from solo work, now joining a team of ~8 that shares a
single repo.
**Target runtime**: ~12 minutes
**Format**: same video template as the rest of the series — one instructor
on camera plus slides, slides shown full-screen during explanation
segments.

## Concepts to cover (4)

1. **Why branching strategy matters.** Without an agreed strategy, teams
   hit two recurring pains: merge conflicts that pile up right before a
   release, and "surprise" commits landing on the release branch that
   nobody reviewed. Ground this with a short relatable scenario before
   naming the concept.

2. **Trunk-based development vs. feature branching.** Explain both models,
   the tradeoff between them (integration frequency vs. isolation), and
   give the team a simple decision rule based on release cadence and team
   size (we ship weekly with 8 engineers — this should point toward a
   specific recommendation, not leave it open-ended).

3. **Branch naming and hygiene.** Our naming convention
   (`type/short-description`, e.g. `feat/checkout-retry`), why short-lived
   branches are preferred, and the cleanup habit (delete after merge).

4. **Merge vs. rebase.** What each does to commit history, why it matters
   for a shared branch, and which one our team uses for feature branches
   vs. release branches.

## Requested shape

- Open with a short, relatable "this went wrong" scenario (a merge-conflict
  fire drill or a bad release) to hook the audience before naming the
  problem.
- Each of the 4 concepts should get enough room to explain the idea *and*
  show at least one concrete example (a naming example, a before/after
  history diagram for merge vs. rebase, etc.) — don't compress an idea and
  its example onto one slide if that makes it feel like a wall of text.
- Close with a short recap / checklist the audience can act on
  immediately.
- **Style note**: keep the same title-slide template and footer branding
  as the rest of the series so the deck family stays visually consistent —
  see the attached outline for Clip 2 (`previous-clip-outline.md`) for
  reference.

## Deliverable requested

A slide-by-slide outline (title + 1-2 line description per slide) for
review before anyone builds the actual slide deck.
