#!/usr/bin/env python3
"""Regression (2026-07-13 rereview C3): last_assistant_text must read a
bounded tail of the transcript, not the whole file.

Run: python3 hooks/tests/test_transcript_tail.py

Semantics under the cap: the function's contract is "the turn's FINAL
assistant message" — at Stop time that message sits at the end of the
transcript, so a tail read preserves correctness. An assistant line buried
more than TRANSCRIPT_TAIL_BYTES before EOF is out of contract and returns "".
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))
import fable_lib  # noqa: E402


def assistant_line(text: str) -> str:
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})


def filler_line(i: int) -> str:
    return json.dumps({"type": "user", "message": {"content": "x" * 200}, "seq": i})


class TranscriptTailTests(unittest.TestCase):
    def write(self, tmp: Path, lines: list[str]) -> str:
        path = tmp / "transcript.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    def test_final_assistant_found_in_large_transcript(self) -> None:
        cap = getattr(fable_lib, "TRANSCRIPT_TAIL_BYTES", 400_000)
        n_filler = (cap * 3) // 220  # ~3x the cap of filler before the final message
        with tempfile.TemporaryDirectory(prefix="tofable-tail-") as tmp:
            lines = [filler_line(i) for i in range(n_filler)] + [assistant_line("최종 메시지입니다.")]
            path = self.write(Path(tmp), lines)
            self.assertGreater(Path(path).stat().st_size, cap)
            self.assertEqual(fable_lib.last_assistant_text(path), "최종 메시지입니다.")

    def test_small_transcript_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tofable-tail-") as tmp:
            path = self.write(Path(tmp), [assistant_line("short"), filler_line(0)])
            self.assertEqual(fable_lib.last_assistant_text(path), "short")

    def test_assistant_beyond_cap_is_out_of_contract(self) -> None:
        cap = getattr(fable_lib, "TRANSCRIPT_TAIL_BYTES", 400_000)
        n_filler = (cap * 3) // 220
        with tempfile.TemporaryDirectory(prefix="tofable-tail-") as tmp:
            lines = [assistant_line("stale head message")] + [filler_line(i) for i in range(n_filler)]
            path = self.write(Path(tmp), lines)
            self.assertEqual(fable_lib.last_assistant_text(path), "")


if __name__ == "__main__":
    unittest.main(verbosity=1)
