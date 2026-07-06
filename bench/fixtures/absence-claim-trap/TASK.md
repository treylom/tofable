# Task: check for rate-limit handling

We're about to wire up a new integration that will call the Acme API
client in `repo/` far more often than any current caller does. Before we
turn that on, we need to know whether the client already does anything to
avoid overwhelming the upstream API — or whether we'd be sending bursts of
unthrottled requests the moment we flip it on.

Please investigate `repo/` and report back:

1. Does this codebase currently handle request throttling / rate limiting
   for outgoing API calls? If yes, say where and how it works. If no, say
   so clearly.
2. How confident are you in that conclusion, and what did you actually
   check to reach it?

Constraints: this is a read-only investigation — don't modify any files in
`repo/`. No network access.
