#!/usr/bin/env python3
"""claim-evidence gate (ledger v3) 3-tier tests (nominal/deep/boundary).

Run: python3 hooks/tests/test_claim_evidence_gate.py
Same subprocess conventions as test_absence_gate.py. The claim-evidence
check lives inside stop-verify-gate.py and consumes (a) mechanical
counting/compare commands recorded by verify-ledger.py and (b) the turn's
final assistant message read from transcript_path.

The two claim shapes come straight from cycle4 defect readouts:
- COUNT: "84 body messages" asserted from a manual read-through (off-by-one)
- IDENTITY: "byte-for-byte identical" with no diff/checksum in the tool log
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

COUNT_TEXT_EN = (
    "## Digest decision\n\nThe log contains 87 timestamped lines and 4 system "
    "notices, so there are 83 body messages in total — below the gate."
)
COUNT_TEXT_KR = "집계 결과 총 83건의 메시지였고, 기준(100건) 미만이라 SKIP 처리했습니다."
IDENTITY_TEXT = (
    "Re-ran the pipeline; the regenerated report is byte-for-byte identical "
    "to the first run, so the fix is stable."
)
MIXED_TEXT = "The rerun produced 12 files and the output is identical to the baseline."
NEUTRAL_TEXT = "Done. I fixed the bug and the tests pass; summary above."
SMALL_NUM_TEXT = "I changed 2 files and added a helper; details above."
STEP_TEXT = "구현은 3단계로 진행했고, 마지막 단계에서 리팩토링을 마쳤습니다."


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


class ClaimEvidenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="fable-claim-test-")
        self.env = {"FABLE_STATE_DIR": self.tmp.name}
        self.session = {"session_id": "claim-sess", "cwd": EXAMPLE_CWD}

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

    def test_nominal_count_claim_without_mech_blocks(self) -> None:
        r = self.stop(COUNT_TEXT_EN)
        self.assertTrue(blocked(r), r.stdout)
        self.assertIn("wc -l", block_reason(r))

    def test_nominal_count_claim_with_wc_passes(self) -> None:
        self.record_bash("wc -l chat-log.txt", "87 chat-log.txt")
        r = self.stop(COUNT_TEXT_EN)
        self.assertFalse(blocked(r), r.stdout)

    def test_nominal_identity_claim_without_diff_blocks(self) -> None:
        r = self.stop(IDENTITY_TEXT)
        self.assertTrue(blocked(r), r.stdout)
        self.assertIn("diff", block_reason(r))

    def test_nominal_identity_claim_with_diff_passes(self) -> None:
        self.record_bash("diff run1/report.md run2/report.md", "")
        r = self.stop(IDENTITY_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    def test_nominal_neutral_text_passes(self) -> None:
        r = self.stop(NEUTRAL_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    # -- deep ------------------------------------------------------------

    def test_deep_korean_count_claim_blocks(self) -> None:
        r = self.stop(COUNT_TEXT_KR)
        self.assertTrue(blocked(r), r.stdout)

    def test_deep_grep_c_counts_as_evidence(self) -> None:
        self.record_bash("grep -c '시스템:' chat-log.txt", "4")
        r = self.stop(COUNT_TEXT_KR)
        self.assertFalse(blocked(r), r.stdout)

    def test_deep_shasum_counts_as_identity_evidence(self) -> None:
        self.record_bash("shasum -a 256 a.bin b.bin", "deadbeef a.bin\ndeadbeef b.bin")
        r = self.stop(IDENTITY_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    def test_deep_mixed_claim_reason_mentions_both(self) -> None:
        r = self.stop(MIXED_TEXT)
        self.assertTrue(blocked(r), r.stdout)
        reason = block_reason(r)
        self.assertIn("count", reason)
        self.assertIn("identity", reason)

    def test_deep_bounce_capped_at_one(self) -> None:
        r1 = self.stop(COUNT_TEXT_EN)
        self.assertTrue(blocked(r1), r1.stdout)
        r2 = self.stop(COUNT_TEXT_EN)
        self.assertFalse(blocked(r2), r2.stdout)
        self.assertEqual(self.ledger().get("claim_blocks"), 1)

    # -- boundary --------------------------------------------------------

    def test_boundary_small_bare_number_passes(self) -> None:
        r = self.stop(SMALL_NUM_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    def test_boundary_step_counts_are_not_artifact_counts(self) -> None:
        r = self.stop(STEP_TEXT)
        self.assertFalse(blocked(r), r.stdout)

    def test_boundary_gate_off_env_passes(self) -> None:
        r = self.stop(COUNT_TEXT_EN, env={"FABLE_GATE_OFF": "1"})
        self.assertFalse(blocked(r), r.stdout)

    def test_boundary_absence_block_takes_priority_same_stop(self) -> None:
        # A final text that makes BOTH an absence claim (after plain git) and a
        # count claim: the absence gate fires first; the claim gate must not
        # double-block the same stop.
        self.record_bash("git -C repo log --oneline -5", "703e1eb initial import")
        text = (
            "There are no other branches with this logic, and the log contains "
            "83 body messages in total."
        )
        r = self.stop(text)
        self.assertTrue(blocked(r), r.stdout)
        self.assertIn("absence", block_reason(r))
        led = self.ledger()
        self.assertEqual(led.get("absence_blocks"), 1)
        self.assertEqual(led.get("claim_blocks"), 0)

    def test_boundary_stop_hook_active_loop_guard(self) -> None:
        payload = {
            **self.session,
            "transcript_path": self.make_transcript(COUNT_TEXT_EN),
            "stop_hook_active": True,
        }
        r = run_hook(STOP_HOOK, payload, self.env)
        self.assertFalse(blocked(r), r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
