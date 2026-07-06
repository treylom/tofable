#!/bin/bash
# repo-hygiene.sh — public-repo hygiene scan. Run before every push.
#
# Catches the leak class that slipped into public twice in one week: a
# private person-reference / internal handle sitting inside an otherwise-
# fine commit (once in a code comment, once in a planning doc).
# Generalization passes kept missing prose, so this is the mechanical
# backstop.
#
# The private token list itself lives OUTSIDE the public tree, in
# scripts/.hygiene-tokens (gitignored, one extended-regex alternation per
# line, lines joined with |) — a scrubber that lists its own targets in a
# tracked file would republish exactly what it exists to remove. This scan
# is a maintainer pre-push gate: downstream clones have no token file and
# no reason to run it; the secret-shape scan below still works for them.
#
# usage: scripts/repo-hygiene.sh   (from anywhere inside the repo)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TOKEN_FILE="scripts/.hygiene-tokens"
if [ -f "$TOKEN_FILE" ]; then
  PRIVATE_TOKENS="$(grep -v '^\s*\(#\|$\)' "$TOKEN_FILE" | paste -sd'|' -)"
  if [ -n "$PRIVATE_TOKENS" ]; then
    HITS=$(git grep -nE "$PRIVATE_TOKENS" -- . || true)
    if [ -n "$HITS" ]; then
      echo "repo-hygiene: private tokens found in tracked files:" >&2
      echo "$HITS" >&2
      exit 1
    fi
  fi
else
  echo "repo-hygiene: note — no $TOKEN_FILE (private-token scan skipped; maintainer-only)" >&2
fi

# Secret shapes (belt over the reviewer's braces).
SECRETS=$(git grep -nE 'sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|xox[baprs]-[A-Za-z0-9-]{12,}|ntn_[A-Za-z0-9]{12,}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY' -- ':!scripts/repo-hygiene.sh' || true)
if [ -n "$SECRETS" ]; then
  echo "repo-hygiene: secret-shaped strings found:" >&2
  echo "$SECRETS" >&2
  exit 1
fi

echo "repo-hygiene: clean ($(git ls-files | wc -l | tr -d ' ') tracked files scanned)"
