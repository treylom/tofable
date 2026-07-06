# Tooling & resourcing inventory — production team

Reference doc for whatever we've got on hand to execute image requests
with. Kept up to date by production leads; flag if something below is
stale.

## Tools

**PromptCanvas** — text-to-image generator. Takes a text prompt and
produces a brand-new image from scratch (no source-image input).
Optimized for English-language prompts. Release notes for the current
version note that non-Latin scripts (Korean, Japanese, Arabic, etc.)
frequently render as garbled or malformed glyphs rather than legible
text.

**RetouchModel** — image-editing model. Takes a source image plus a
natural-language edit instruction and returns an edited image.
Documentation describes it as built for localized edits (adding,
removing, or modifying a specific region of an existing image) while
preserving the rest of the composition. In practice it typically takes
1-2 attempts to get it to stay strictly inside a specified region.

**Rasterkit** (in-house) — a small Python toolkit the team maintains for
direct pixel-level edits on an existing image file: draws text at a
specified position using a specified font file, size, and color; also
handles basic crop / recolor / layer-composite operations. Fast and
fully scriptable. It draws exactly what's specified and nothing more —
no automatic style-matching, blending, or anti-aliasing beyond the font
renderer's default.

**LayerCraft** — the team's standard vector/layout design application.
Can place an existing raster image (e.g. a PNG) as a locked background
layer and add new vector objects — including real, editable text objects
in any installed font — on top of it. Exports a flattened raster
(PNG/JPG) at a specified pixel resolution. Any production team member
can open and edit LayerCraft files; no special access required.

## People

Rina Alsop, the freelance illustrator who originally drew the Lumen Notes
hero illustration, is out this week (planned time off, fully offline).
She delivered the original commission as a single flattened PNG — the
team does not have a layered source file for it.

## Fonts / brand reference

Existing Korean-market storefront assets set on-image labels in **Noto
Sans KR, Bold**, usually in the illustration's line-art color
(`#3A2E2A`, a warm dark brown) when placed on a light or mid-tone
background.
