#!/usr/bin/env python3
"""Codex parity for the 2026-07-13 rereview P1 fixes (C2 ledger lock, C3
transcript tail cap) — same contracts as hooks/tests/test_ledger_concurrency.py
and hooks/tests/test_transcript_tail.py, against codex/gates/lib.py.

Run: cd codex/gates/tests && python3 test_codex_p1_parity.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATES))
import lib  # noqa: E402

WORKER = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
import lib

data = {"session_id": "lock-race", "cwd": sys.argv[3]}
ledger = lib.load_ledger(data)
time.sleep(0.05)
ledger["verification_commands"] = list(ledger.get("verification_commands", [])) + [sys.argv[2]]
lib.save_ledger(data, ledger)
"""


class CodexLedgerConcurrencyTests(unittest.TestCase):
    def test_parallel_appends_all_survive(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tofable-codex-lock-") as tmp:
            env = {**os.environ, "FABLE_STATE_DIR": tmp}
            cwd = "/workspace/lock-race-project"
            procs = [
                subprocess.Popen(
                    [sys.executable, "-c", WORKER, str(GATES), f"marker-{i}", cwd],
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


def assistant_line(text: str) -> str:
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})


def filler_line(i: int) -> str:
    return json.dumps({"type": "user", "message": {"content": "x" * 200}, "seq": i})


class CodexTranscriptTailTests(unittest.TestCase):
    def write(self, tmp: Path, lines: list[str]) -> str:
        path = tmp / "transcript.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    def test_final_assistant_found_in_large_transcript(self) -> None:
        cap = getattr(lib, "TRANSCRIPT_TAIL_BYTES", 400_000)
        n_filler = (cap * 3) // 220
        with tempfile.TemporaryDirectory(prefix="tofable-codex-tail-") as tmp:
            lines = [filler_line(i) for i in range(n_filler)] + [assistant_line("최종 메시지입니다.")]
            path = self.write(Path(tmp), lines)
            self.assertGreater(Path(path).stat().st_size, cap)
            self.assertEqual(lib.last_assistant_text_from_transcript(path), "최종 메시지입니다.")

    def test_assistant_beyond_cap_is_out_of_contract(self) -> None:
        cap = getattr(lib, "TRANSCRIPT_TAIL_BYTES", 400_000)
        n_filler = (cap * 3) // 220
        with tempfile.TemporaryDirectory(prefix="tofable-codex-tail-") as tmp:
            lines = [assistant_line("stale head message")] + [filler_line(i) for i in range(n_filler)]
            path = self.write(Path(tmp), lines)
            self.assertEqual(lib.last_assistant_text_from_transcript(path), "")


if __name__ == "__main__":
    unittest.main(verbosity=1)
