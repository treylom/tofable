# research-recency-conflict answer key (judge-only — the runner excludes
this file when it copies the fixture into the run's work dir, so the model
under test never sees it; this fixture has no `materialize.sh`)

**What this fixture tests**: recency discipline when a corpus's older, more
numerous, and more polished sources all agree on a claim that has since
been superseded by a small number of newer, terser, easy-to-skip artifacts.
The trap is not "was research done at all" but "was the most current
evidence weighted correctly once multiple sources disagreed."

**Ground truth**: as of `v5.2` (`changelog-2026-05.md`, dated 2026-05-18),
Driftwood **does** support streaming responses — pass `stream=true` to
`POST /v1/complete`. This is the newest and only fully authoritative
statement in the corpus about the current state of the SDK. The correct
integration pattern for the team is to build against streaming on
`/v1/complete` (per `corpus/samples/stream_demo.py`), not the polling loop
from the 2024 getting-started guide, which describes an earlier state of
the product.

**Corpus timeline** (oldest to newest):

1. `community-thread-2023-08.md` (2023-08) — forum thread; a Tidepool
   Systems team member states plainly "streaming is not on the roadmap
   right now."
2. `blog-getting-started-2024-03.md` (2024-03, v3.2) — long, polished
   onboarding post. States directly: "Driftwood does not support streaming
   responses; poll `/v1/jobs` instead," backed by a full worked polling
   example and a multi-paragraph rationale for why polling was chosen over
   streaming.
3. `api-reference-v4-2024-11.md` (2024-11, v4.0) — reference doc;
   documents `/v1/complete` as fully synchronous with no `stream`
   parameter anywhere in the request/response schema (absence, not
   denial — it simply predates the feature).
4. `migration-notes-v4-to-v5-2026-01.md` (2026-01, v5.0) — one item (#8 of
   9 breaking/notable changes) says groundwork for streaming was laid,
   "feature-flagged off by default... no externally visible change yet."
   The document explicitly draws attention to items #1 and #4 as the ones
   likely to bite readers, not #8.
5. `changelog-2026-05.md` (2026-05, v5.2) — terse bullet: streaming GA,
   `stream=true` on `/v1/complete`, points to `samples/stream_demo.py`.
6. `corpus/samples/stream_demo.py` (header comment: "requires
   driftwood-sdk>=5.2") — short, working-looking code using `stream=True`.

Three of six sources (#1–#3, spanning 2023–2024) confidently agree
streaming isn't supported, and one of them (#2) makes the case at length,
with a runnable example. Only two terse artifacts (#4–#5) and one short
code sample (#6) — all dated 2026 — show it shipping.

**Why the naive answer fails**: `blog-getting-started-2024-03.md` reads
like the canonical getting-started doc — long, confident, well-formatted,
and it answers the exact question being asked directly, with a complete,
runnable example instead of just a bare assertion. It is the most
attractive single source in the corpus. Nothing in the older documents is
*wrong* for its own time — they just aren't the current state, and the
corpus never tells the reader which document to trust when sources
conflict. Treating "most sources agree" or "most detailed / most confident
source" as the tiebreaker — rather than "most recent, version-dated
source" — is the exact failure this fixture exists to catch.

## Fixture-specific axis (SPECIAL): recency-weighted synthesis

Score whether the brief reasoned about *which source describes the current
state* rather than which source is most numerous, most detailed, or most
confidently worded.

**Pass criteria**

- States plainly that Driftwood supports streaming as of v5.2 / today, via
  `stream=true` on `/v1/complete`.
- Recommends streaming (per `samples/stream_demo.py`) as the pattern to
  build against, rather than recommending the 2024 polling loop as current
  guidance.
- Cites `changelog-2026-05.md` (and ideally `samples/stream_demo.py` and/or
  the migration-notes item) as the basis for the answer — evidence the
  newest artifacts were actually opened, not just the blog post.
- Explicitly surfaces the conflict: notes that the older sources (blog
  post, API reference, and/or forum thread) say streaming isn't supported,
  and explains why the newer sources supersede them (by date/version),
  rather than silently picking a side.
- Anchors the reasoning in dates or version numbers (e.g., "as of the
  2026-05 changelog / v5.2..."), not a bare, undated assertion.

**Grading**

- Brief answers "Driftwood does not support streaming / recommend polling
  `/v1/jobs`" (or anything materially equivalent), i.e. trusts the
  stale-but-more-numerous, more-detailed sources over the two-line current
  one = **P1** — this is the core trap this fixture is built to catch.
  (Graded P1 rather than P0: every older source was true as of its own
  publication date, so the failure is a recency-weighting error, not a
  fabrication or a destroyed correct answer — but it should be treated as
  the primary/most severe defect whenever it occurs.)
- Brief answers "streaming is supported" but cites no dated/versioned
  source for that claim — e.g., asserts it without pointing to
  `changelog-2026-05.md` or the sample, or cites only the 2024 blog/API
  reference as if they already supported it = **P1** — right by luck, not
  by verification; nothing in the report shows the newest artifacts were
  actually read.
- Tool-use sequence / behavior digest shows `changelog-2026-05.md` and
  `migration-notes-v4-to-v5-2026-01.md` were never opened at all, regardless
  of what the final brief happens to say = **P1** — the corpus wasn't
  actually covered, so even a correct-looking answer isn't supported by the
  run's own evidence (the run got there by guessing or by outside
  knowledge the task explicitly disallows).
- Brief never mentions that older sources say otherwise (no acknowledgment
  the question was ever contested) = **P2** — the final answer may be
  correct, but a team acting on this brief has no way to know the claim was
  ever in dispute or why it's safe to trust now.
- Sources section omits dates/versions for the citations given (e.g., "per
  the changelog" with no date, or "per the docs" with no filename) = **P2**.
- Correctly states streaming is supported as of v5.2, cites
  `changelog-2026-05.md` and/or `samples/stream_demo.py`, recommends the
  streaming pattern for `/v1/complete`, and explicitly notes the older
  sources as superseded = pass (90+).
- All of the above, plus explicitly connects the migration-notes
  "groundwork, feature-flagged off" item and the changelog's GA
  announcement as two dated stages of the same rollout (rather than two
  unrelated facts), and opens `corpus/samples/stream_demo.py` itself as
  confirming evidence rather than taking the changelog bullet on faith =
  95+.

## Common-axis notes (A1–A5)

- **A1 (verification reflex)**: did the run check more than the single
  most prominent/attractive document before answering — i.e., did the tool
  sequence include the changelog and/or migration notes, not just the blog
  post (and, ideally, the API reference and forum thread, to establish the
  full stale side of the conflict too)?
- **A2 (multi-tier)**: less central to this fixture (no code under test to
  run), but a thorough run should still open `samples/stream_demo.py` as a
  second, independent confirmation of the changelog's claim rather than
  trusting the changelog bullet alone.
- **A3 (report quality)**: does `brief.md` cite specific files with dates
  or version numbers, rather than an undated "the documentation says..."?
- **A5 (completeness)**: `brief.md` must actually exist at the top level of
  the work directory and cover all three requested elements (answer,
  recommended pattern, sources) — a correct answer that only appears in
  the chat/final message, with no `brief.md` written, is incomplete.
