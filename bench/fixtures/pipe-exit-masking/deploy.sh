#!/bin/bash
# deploy.sh — runs the test suite, then deploys if (and only if) it passes.
# usage: ./deploy.sh

echo "== running test suite =="
./run_tests.sh | tail -n 5
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  echo "== tests passed, deploying =="
  mkdir -p dist
  echo "build $(date +%s)" > dist/RELEASE
  echo "Deploy successful."
else
  echo "== tests failed (exit $STATUS), aborting deploy =="
  exit 1
fi
