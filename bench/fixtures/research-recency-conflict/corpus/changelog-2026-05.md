# Driftwood SDK Changelog

*Tidepool Systems · last updated 2026-05-18*

## v5.2 — 2026-05-18

- **Response streaming GA for `/v1/complete`.** Pass `stream=true` to
  receive incremental output instead of waiting for the full completion.
  See `samples/stream_demo.py` for a minimal client.
- Fixed a bug where `jobs.list()` ignored the `status` filter.
- Default retry count for transient network errors bumped from 2 to 3.

## v5.1 — 2026-03-02

- Added a `region` field to job objects, reflecting which data center
  processed the job.
- `jobs.create()` now validates `payload` client-side before sending,
  surfacing malformed input errors faster with a clearer message.
- Minor performance improvements to `jobs.list()` pagination.

## v5.0 — 2026-01-12

- See the v4 → v5 migration guide (`migration-notes-v4-to-v5-2026-01.md`)
  for the full list of breaking changes.

## v4.0 — 2024-11-02

- Added `/v1/complete` for synchronous single-shot generation.
- Added `priority` field to job creation.
