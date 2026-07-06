# NimbusSync v4.2 — Changelog

Released 2026-06-15.

## New

- Automatic conflict resolution for simultaneous edits: when two clients
  edit the same file while offline, NimbusSync now merges non-overlapping
  changes automatically and only prompts for manual resolution when edits
  actually overlap on the same lines.
- Offline editing on mobile: the mobile app now queues edits made while
  offline and syncs them automatically the next time the device has a
  connection.

## Improved

- Sync latency reduced by 40% on average across our benchmark file set,
  from a rewritten diffing engine (see engineering notes for details).

## Fixed

- Fixed a bug where shared-folder permissions could take up to a minute
  to propagate to all members.

See also: `changelog-appendix.md` for security and compliance notes for
this release.
