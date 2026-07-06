#!/bin/bash
# run_tests.sh — small test suite for the billing summary helper (calc.py).
# Exits 0 if every check passes, non-zero if any check fails.
# Run standalone with: ./run_tests.sh
set -u

pass=0
fail=0

check() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "ok - $desc"
    pass=$((pass + 1))
  else
    echo "not ok - $desc (expected '$expected', got '$actual')"
    fail=$((fail + 1))
  fi
}

HERE="$(cd "$(dirname "$0")" && pwd)"

check "totals a simple list" "6" "$(python3 "$HERE/calc.py" --sum 1,2,3)"
check "totals an empty list" "0" "$(python3 "$HERE/calc.py" --sum '')"
check "rejects a list with a negative value" "rejected" "$(python3 "$HERE/calc.py" --sum 1,-2,3)"
check "formats a currency total" '$6.00' "$(python3 "$HERE/calc.py" --currency 1,2,3)"

echo "---"
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
