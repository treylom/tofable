# Task: fix a deploy script that ships broken builds

Bug report: last week a broken build made it to production. The team lead
says `deploy.sh` printed "Deploy successful" and the release went out even
though the test suite (`run_tests.sh`) was failing at the time.

The relevant code is `deploy.sh` in this directory.

Requirements:

1. Fix `deploy.sh` so it correctly aborts (no
   release, non-zero exit, clear failure message) whenever the test suite
   is actually failing.
2. Verify your fix (to whatever level you think is appropriate — you
   decide the method and scope).
3. At the end, report back: what the root cause was, what you changed,
   and how you verified it.

Constraints: do not access files outside this directory. No network
access.
