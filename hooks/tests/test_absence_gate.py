#!/usr/bin/env python3
"""absence-gate (ledger v2) 3-tier tests (nominal/deep/boundary).

Run: python3 hooks/tests/test_absence_gate.py
Same subprocess conventions as test_gate.py. The absence check lives inside
stop-verify-gate.py and consumes (a) git-usage evidence recorded by
verify-ledger.py and (b) the turn's final assistant message read from
transcript_path.
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
LEDGER_HOOK = HOOKS / "verify-ledger.py"
STOP_HOOK = HOOKS / "stop-verify-gate.py"

EXAMPLE_CWD = "/workspace/example-project"

ABSENCE_TEXT = (
    "## Findings\n\nI checked the repository. There are no other files or "
    "branches implementing throttling — git log shows a single commit, so "
    "there's no prior history hiding removed logic."
)
KOREAN_ABSENCE_TEXT = "조사 결과, 다른 브랜치에 관련 코드가 없습니다. 여기까지가 전부입니다."
NEUTRAL_TEXT = "Done. I fixed the bug and the tests pass; summary above."
NO_ISSUES_TEXT = "Review complete — there are no issues and no errors in the change."


def run_hook(hook: Path, payload: dict | str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("FABLE_GATE_OFF", None)
    env.pop("FABLE_GATE_PILOT", None)
    env.pop("FABLE_SESSION_NAME", None)
    env.update(extra_env or {})
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(hook)], input=raw, capture_output=True, text=True, env=env, timeout=30
    )


def blocked(r: subprocess.CompletedProcess) -> bool:
    for line in (r.stdout or "").strip().splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and d.get("decision") == "block":
            return True
    return False


def block_reason(r: subprocess.CompletedProcess) -> str:
    for line in (r.stdout or "").strip().splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and d.get("decision") == "block":
            return str(d.get("reason") or "")
    return ""


class AbsenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="fable-absence-test-")
        self.env = {"FABLE_STATE_DIR": self.tmp.name}
        self.session = {"session_id": "absence-sess", "cwd": EXAMPLE_CWD}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # -- helpers ---------------------------------------------------------

    def make_transcript(self, final_text: str) -> str:
        path = Path(self.tmp.name) / "transcript.jsonl"
        entry = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": final_text}]},
        }
        path.write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
        return str(path)

    def record_bash(self, command: str, stdout: str = "") -> None:
        r = run_hook(
            LEDGER_HOOK,
            {**self.session, "tool_name": "Bash", "tool_input": {"command": command}, "tool_response": {"stdout": stdout, "exit_code": 0}},
            self.env,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def stop(self, final_text: str, extra: dict | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
        payload = {**self.session, "transcript_path": self.make_transcript(final_text), **(extra or {})}
        return run_hook(STOP_HOOK, payload, {**self.env, **(env or {})})

    def ledger(self) -> dict:
        d = Path(self.tmp.name) / "ledgers"
        files = sorted(d.glob("*.json")) if d.exists() else []
        self.assertTrue(files, "expected a ledger file")
        return json.loads(files[0].read_text(encoding="utf-8"))

    # -- nominal ---------------------------------------------------------

    def test_nominal_absence_after_plain_git_blocks_with_checklist(self) -> None:
        self.record_bash("git -C repo log --oneline -5", "703e1eb initial import")
        r = self.stop(ABSENCE_TEXT)
        self.assertTrue(blocked(r), r.stdout)
        self.assertIn("git log --oneline --all", block_reason(r))

    def test_nominal_boundary_expansion_passes(self) -> None:
        self.record_bash("git -C repo log --oneline --all", "703e1eb initial import\nabc feature")
        r = self.stop(ABSENCE_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    def test_nominal_branch_a_counts_as_boundary(self) -> None:
        self.record_bash("git log --oneline -3")
        self.record_bash("git branch -a", "* main\n  remotes/origin/feature/x")
        r = self.stop(ABSENCE_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    def test_nominal_no_git_usage_out_of_scope(self) -> None:
        self.record_bash("grep -rn throttle .", "")
        r = self.stop(ABSENCE_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    def test_nominal_neutral_final_text_passes(self) -> None:
        self.record_bash("git log --oneline -5")
        r = self.stop(NEUTRAL_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    # -- deep ------------------------------------------------------------

    def test_deep_bounce_capped_at_one(self) -> None:
        self.record_bash("git log --oneline -5")
        r1 = self.stop(ABSENCE_TEXT)
        self.assertTrue(blocked(r1))
        r2 = self.stop(ABSENCE_TEXT)
        self.assertFalse(blocked(r2), "absence gate must bounce at most once per session")

    def test_deep_ledger_records_git_and_boundary_flag(self) -> None:
        self.record_bash("git -C repo log --oneline -5")
        led = self.ledger()
        self.assertTrue(any("git" in c for c in led.get("git_commands", [])))
        self.assertFalse(led.get("boundary_expansion_seen"))
        self.record_bash("git -C repo branch -a")
        led = self.ledger()
        self.assertTrue(led.get("boundary_expansion_seen"))

    def test_deep_korean_absence_claim_blocks(self) -> None:
        self.record_bash("git log --oneline -5")
        r = self.stop(KOREAN_ABSENCE_TEXT)
        self.assertTrue(blocked(r), r.stdout)

    def test_deep_change_gate_takes_priority(self) -> None:
        # unverified code change + absence text → the change-verification
        # block fires first; absence bounce is not consumed.
        r = run_hook(
            LEDGER_HOOK,
            {**self.session, "tool_name": "Edit", "tool_input": {"file_path": f"{EXAMPLE_CWD}/src/app.py"}},
            self.env,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.record_bash("git log --oneline -5")
        r = self.stop(ABSENCE_TEXT)
        self.assertTrue(blocked(r))
        self.assertIn("harness/code surface", block_reason(r))
        led = self.ledger()
        self.assertEqual(int(led.get("absence_blocks") or 0), 0)

    # -- boundary --------------------------------------------------------

    def test_boundary_no_issues_phrasing_not_matched(self) -> None:
        self.record_bash("git log --oneline -5")
        r = self.stop(NO_ISSUES_TEXT)
        self.assertFalse(blocked(r), "generic 'no issues/errors' must not arm the absence gate")

    def test_boundary_kill_switch(self) -> None:
        self.record_bash("git log --oneline -5")
        r = self.stop(ABSENCE_TEXT, env={"FABLE_GATE_OFF": "1"})
        self.assertFalse(blocked(r))

    def test_boundary_stop_hook_active_passes(self) -> None:
        self.record_bash("git log --oneline -5")
        r = self.stop(ABSENCE_TEXT, extra={"stop_hook_active": True})
        self.assertFalse(blocked(r))

    def test_boundary_missing_transcript_fails_open(self) -> None:
        self.record_bash("git log --oneline -5")
        payload = {**self.session, "transcript_path": str(Path(self.tmp.name) / "nope.jsonl")}
        r = run_hook(STOP_HOOK, payload, self.env)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(blocked(r))

    def test_boundary_garbage_stdin_fails_open(self) -> None:
        r = run_hook(STOP_HOOK, "{not json", self.env)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(blocked(r))


if __name__ == "__main__":
    unittest.main(verbosity=2)
