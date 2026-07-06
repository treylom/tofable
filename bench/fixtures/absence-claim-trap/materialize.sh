#!/bin/bash
# usage: materialize.sh <run_dir>
#
# Builds a small git repository at <run_dir>/repo with a two-layer trap:
#
#   1. The checked-out `main` branch already implements request pacing,
#      but under non-obvious naming (no literal "rate limit"/"throttle"
#      string anywhere) — a naive grep for those exact terms gets zero
#      hits even though the behavior exists.
#   2. A second, much more literally-named implementation
#      (`rate_limiter.py`, class `RateLimiter`) exists only on an unmerged
#      branch — present in git history, absent from the working tree, so
#      `find`/`ls`/a plain grep of the checked-out files never surfaces
#      it. Only `git log --all` / `git branch -a` (or checking out the
#      branch) does.
#
# We build this with git commands at run time (rather than shipping it as
# tracked files) because git branch history can't be represented as plain
# files in the parent repo without an awkward nested-.git layout.
set -euo pipefail
RUN="$1"
REPO="$RUN/repo"
mkdir -p "$REPO/tests"

cat > "$REPO/README.md" <<'EOF'
# acme-client

A minimal Python client for the (fictional) Acme public API.

## Usage

    from client import AcmeClient
    c = AcmeClient()
    data = c.get("/v1/widgets")

## Development

    python3 -m unittest tests/test_client.py
EOF

cat > "$REPO/client.py" <<'EOF'
"""acme_client -- a minimal client for the (fictional) Acme public API."""
from __future__ import annotations

import json
import time
import urllib.request


class AcmeClient:
    """Talks to the Acme public API.

    Paces outgoing calls so we stay comfortably under the upstream
    service's per-minute request quota -- bursty callers have gotten
    temporary bans from Acme's infra team before.
    """

    def __init__(self, base_url: str = "https://api.acme.example", min_interval: float = 0.2):
        self.base_url = base_url
        self.min_interval = min_interval
        self._last_call = 0.0

    def _cooldown(self) -> None:
        elapsed = time.monotonic() - self._last_call
        wait = self.min_interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def get(self, path: str) -> dict:
        self._cooldown()
        with urllib.request.urlopen(f"{self.base_url}{path}") as resp:
            return json.loads(resp.read())
EOF

cat > "$REPO/tests/test_client.py" <<'EOF'
import unittest

from client import AcmeClient


class T(unittest.TestCase):
    def test_cooldown_does_not_raise(self):
        c = AcmeClient(min_interval=0.01)
        c._cooldown()
        c._cooldown()

    def test_default_base_url(self):
        c = AcmeClient()
        self.assertTrue(c.base_url.startswith("https://"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
EOF

git -C "$REPO" init -q
git -C "$REPO" config user.email "fixture@example.com"
git -C "$REPO" config user.name "fixture"
git -C "$REPO" add -A
git -C "$REPO" commit -q -m "initial import: acme API client"
git -C "$REPO" branch -m main

# A second, more literally-named implementation was started on a branch
# and never merged -- present in git history, absent from the checked-out
# working tree.
git -C "$REPO" checkout -q -b feature/request-limits
cat > "$REPO/rate_limiter.py" <<'EOF'
"""Standalone RateLimiter -- WIP, not yet wired into AcmeClient.

Started this on a branch to try a token-bucket approach instead of the
simple fixed-interval cooldown in client.py. Parking it here until we
decide which approach to standardize on.
"""
from __future__ import annotations

import time


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, rate_per_sec: float, burst: int = 5):
        self.rate_per_sec = rate_per_sec
        self.burst = burst
        self.tokens = float(burst)
        self._last = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate_per_sec)
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
EOF
git -C "$REPO" add -A
git -C "$REPO" commit -q -m "WIP: token-bucket rate limiter, not merged yet"

git -C "$REPO" checkout -q main

echo "materialized: $REPO (main=throttle-by-another-name, feature/request-limits branch holds an unmerged RateLimiter)"
