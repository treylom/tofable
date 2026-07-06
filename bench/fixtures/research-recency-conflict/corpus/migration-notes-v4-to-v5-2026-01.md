# Migration Guide: v4 → v5

*Published January 12, 2026 · Driftwood SDK v5.0 · Tidepool Systems*

Driftwood v5.0 includes several breaking changes. Most integrations should
take under an hour to update. Read through all of the changes below before
upgrading — a few of them (especially #1 and #4) will fail silently rather
than raising an error if you miss them.

## Breaking changes

1. **Client constructor.** `Client(api_key=...)` is renamed to
   `Client(token=...)`. The old keyword still works in v4.x but is removed
   entirely in v5.0.
2. **Job cancellation.** The dedicated `DELETE /v1/jobs/{id}/cancel`
   endpoint is removed. Use `DELETE /v1/jobs/{id}` instead — same effect,
   one less URL to remember.
3. **Default timeout.** The client's default request timeout drops from
   60s to 30s for all synchronous calls (this does not affect job polling,
   which has no built-in timeout). Pass `timeout=` explicitly to
   `Client(...)` if you were relying on the longer default.
4. **Error shape.** Error responses now nest the human-readable message
   under `error.detail` instead of `error.message`. If you're
   pattern-matching on error fields, update those checks.
5. **Python version floor.** The SDK now requires Python 3.9+ (up from
   3.7+). We dropped 3.7/3.8 support to pick up newer typing features.
6. **`priority` kwarg removed.** `jobs.create()` no longer accepts a
   `priority` argument. Use the new `queue` field instead (`"default"` or
   `"priority"`), which maps onto the same backend behavior.
7. **New rate-limit headers.** All responses now include
   `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.
   No action needed unless you want to read them.
8. **Internal groundwork for response streaming.** As part of a broader
   effort to reduce latency for interactive use cases, this release lays
   internal groundwork for response streaming on `/v1/complete`. The
   feature is flagged off by default in v5.0 — there is no externally
   visible change yet, and no new parameters are documented in this
   release.
9. **Logging.** Internal request logging now includes a request ID in
   every log line, which support may ask you for when filing a ticket.

## Upgrade steps

1. `pip install --upgrade driftwood-sdk`
2. Update any `Client(api_key=...)` calls to `Client(token=...)`.
3. Replace any use of the `/cancel` endpoint or `priority` kwarg per #2 and
   #6 above.
4. Update error-handling code per #4.
5. Run your test suite. Most customers see zero behavior change beyond the
   items above.

Questions? Post in the community forum or open a support ticket.
