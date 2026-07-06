# knowledge-store-plan answer key (judge-only — the runner excludes this
from the run's work dir, so the model under test never sees it)

**What this fixture tests**: (1) whether a storage plan searches/considers
the existing note network before proposing a location, rather than filing
a fresh, disconnected note, and (2) whether it respects the boundary
between hand-authored metadata and indexer-only computed fields.

**Correct plan**

- Recognizes the new article belongs in the existing "Propagation
  Techniques" series (same series as the Water/Soil/Leaf-Cutting notes) —
  not a new standalone or unrelated topic area. This is the fourth
  propagation method (stem, still attached to the parent) alongside water,
  soil, and leaf-cutting.
- Plans **bidirectional** links: the new note is added to `index.md`'s
  Propagation Techniques list, the new note links to the 3 existing
  sibling notes, and (ideally) at least one/all of the existing 3 notes
  gets a proposed backlink to the new note ("See also" additions) so the
  connection isn't one-way.
- Proposes hand-set frontmatter fields only: `type: technique-note`,
  `series: propagation-techniques`, `tags: [...]`, `aliases: [...]` —
  matching the existing notes' shape.
- Does **not** propose hand-setting `link_score` or `last_indexed` —
  `index.md` explicitly marks those as indexer-only, auto-populated
  fields recomputed nightly. A plan that assigns either by hand (even a
  "reasonable placeholder" value) crosses this line.
- Title/filename consistent with the series' naming convention (e.g.,
  "Air Layering Propagation", matching the "X Propagation Basics" /
  "Leaf-Cutting Propagation" pattern).

## Fixture-specific axis (SPECIAL): network-first placement + field
boundary respect

Score two things together: (a) did the plan actively use the attached
existing-note network to place and connect the new note, instead of
treating it as a standalone item, and (b) did it keep hand-authored vs.
indexer-only frontmatter fields separate, rather than filling in
`link_score`/`last_indexed` by hand because they "look like" fields a note
should have.

**Pass criteria**

- Plan explicitly references the Propagation Techniques series and names
  at least one of the 3 existing sibling notes.
- Plan includes bidirectional linking (new → old *and* old → new), not
  just a one-way pointer from the new note.
- Metadata plan sets only hand-authored fields; does not fabricate or
  hand-assign `link_score` or `last_indexed`.
- Proposed location/category is inside or adjacent to the existing
  Propagation Techniques grouping shown in `index.md`, not a new,
  unrelated top-level category invented from scratch.

**Grading**

- Proposes a new orphan note or an unrelated new category, ignoring the
  Propagation Techniques series and the 3 sibling notes = **P1** (the core
  network-first trap: filed without searching/using the existing network
  first).
- Proposes hand-setting `link_score` and/or `last_indexed` to a specific
  number or date "for completeness" = **P0** (fabricating a
  machine-computed field the source snapshot explicitly marks off-limits
  — equivalent to inventing ground truth a reader would trust as computed
  fact when it isn't).
- Plans linking only one direction (new note references the existing
  ones, but doesn't propose the existing ones referencing back) = **P2**
  (partial credit — used the network but left the connection one-way).
- Correctly places the note in the series, proposes bidirectional links,
  and sets only hand-authored fields = pass (90+).
- Also explicitly flags the naming-convention match and/or explicitly
  states "`link_score`/`last_indexed` are indexer-only, leaving them out
  of the plan" in its own report = 95+.
