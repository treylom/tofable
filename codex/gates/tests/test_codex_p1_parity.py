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

from test_support import EXAMPLE_CWD, blocked, denied, run_hook  # noqa: E402

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


class CodexTurnLedgerPersistenceTests(unittest.TestCase):
    """Regression (2026-07-13 rereview C4): UserPromptSubmit fires on every
    user TURN, not once per session — it must seed the ledger only on first
    touch, never wipe pending verification obligations from an earlier turn.
    (The ledger is already per-session: its key hashes session_id.)
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="tofable-codex-c4-")
        self.env = {"FABLE_STATE_DIR": self.tmp.name}
        self.session = {"session_id": "c4-sess", "cwd": EXAMPLE_CWD}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_next_turn_does_not_erase_pending_obligation(self) -> None:
        # turn N: a code change lands, unverified
        run_hook(
            GATES / "post_tool_use.py",
            {**self.session, "tool_name": "Write", "tool_input": {"file_path": f"{EXAMPLE_CWD}/src/app.py"}},
            self.env,
        )
        # turn N+1: the next user message arrives
        run_hook(GATES / "user_prompt_submit.py", {**self.session}, self.env)
        # stopping without any verification must still bounce
        self.assertTrue(blocked(run_hook(GATES / "stop_gate.py", {**self.session}, self.env)))

    def test_first_touch_still_seeds_a_ledger(self) -> None:
        run_hook(GATES / "user_prompt_submit.py", {**self.session}, self.env)
        self.assertEqual(len(list(Path(self.tmp.name).rglob("*.json"))), 1)


class CodexSmallFixParityTests(unittest.TestCase):
    """Codex parity for the rereview LOW batch (C9a/C9b/C9c)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="tofable-codex-small-")
        self.env = {"FABLE_STATE_DIR": self.tmp.name}
        self._old_env = os.environ.get("FABLE_STATE_DIR")

    def tearDown(self) -> None:
        if self._old_env is None:
            os.environ.pop("FABLE_STATE_DIR", None)
        else:
            os.environ["FABLE_STATE_DIR"] = self._old_env
        self.tmp.cleanup()

    def pre(self, command: str, session: str = "small-1"):
        return run_hook(
            GATES / "pre_tool_use.py",
            {"session_id": session, "cwd": EXAMPLE_CWD, "tool_name": "Bash", "tool_input": {"command": command}},
            self.env,
        )

    def test_search_mention_of_content_patterns_passes(self) -> None:
        self.assertFalse(denied(self.pre('grep -rn "shutil.rmtree(" src/')))
        self.assertFalse(denied(self.pre('rg "DROP TABLE" migrations/ | head -5', session="small-2")))

    def test_inline_execution_still_denied(self) -> None:
        self.assertTrue(denied(self.pre("python3 -c \"import shutil; shutil.rmtree('build')\"", session="small-3")))

    def test_more_languages_classify_as_code(self) -> None:
        for name in ("handler.php", "App.kt", "main.dart", "Service.cs", "network.tf", "schema.proto", "index.html"):
            self.assertEqual(lib.classify_path_kind(f"/workspace/proj/src/{name}"), "code", name)

    def test_stale_ledger_pruned_on_first_touch(self) -> None:
        import time

        os.environ["FABLE_STATE_DIR"] = self.tmp.name
        stale = lib.save_ledger({"session_id": "stale-sess", "cwd": "/w"}, lib.default_ledger())
        Path(f"{stale}.lock").touch()
        old = time.time() - 40 * 86400
        os.utime(stale, (old, old))
        fresh = lib.save_ledger({"session_id": "fresh-sess", "cwd": "/w"}, lib.default_ledger())

        lib.load_ledger({"session_id": "new-sess", "cwd": "/w"})

        self.assertFalse(stale.exists())
        self.assertFalse(Path(f"{stale}.lock").exists())
        self.assertTrue(fresh.exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
