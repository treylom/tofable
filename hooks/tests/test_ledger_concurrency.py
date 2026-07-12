#!/usr/bin/env python3
"""Regression (2026-07-13 rereview C2): concurrent load→mutate→save cycles on
the same ledger must not silently lose appends.

Run: python3 hooks/tests/test_ledger_concurrency.py

Each worker subprocess widens the read→write window with a short sleep, so
without a critical section around the cycle most of the eight appends are
clobbered by whichever save lands last. With the flock-based lock the final
ledger must carry all eight markers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]

WORKER = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
import fable_lib

data = {"session_id": "lock-race", "cwd": sys.argv[3]}
ledger = fable_lib.load_ledger(data)
time.sleep(0.05)  # widen the read->write window so unlocked cycles overlap
ledger["verification_commands"] = list(ledger.get("verification_commands", [])) + [sys.argv[2]]
fable_lib.save_ledger(data, ledger)
"""


class LedgerConcurrencyTests(unittest.TestCase):
    def test_parallel_appends_all_survive(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tofable-lock-") as tmp:
            env = {**os.environ, "FABLE_STATE_DIR": tmp}
            cwd = "/workspace/lock-race-project"
            procs = [
                subprocess.Popen(
                    [sys.executable, "-c", WORKER, str(HOOKS), f"marker-{i}", cwd],
                    env=env,
                )
                for i in range(8)
            ]
            for proc in procs:
                self.assertEqual(proc.wait(timeout=30), 0)

            ledgers = [p for p in Path(tmp).rglob("*.json")]
            self.assertEqual(len(ledgers), 1, ledgers)
            data = json.loads(ledgers[0].read_text(encoding="utf-8"))
            got = {m for m in data.get("verification_commands", []) if isinstance(m, str) and m.startswith("marker-")}
            self.assertEqual(got, {f"marker-{i}" for i in range(8)})


if __name__ == "__main__":
    unittest.main(verbosity=1)
