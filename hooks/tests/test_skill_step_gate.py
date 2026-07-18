#!/usr/bin/env python3
"""skill-step-gate.py (Stop) + skill-step-inject.py (PostToolUse) tests.

3-tier coverage (nominal / deep / boundary — see rules/verification.md).
Run: python3 hooks/tests/test_skill_step_gate.py

Both hooks are opt-in: everything here writes its own `skill-contracts.json`
into a throwaway project root (`self.root`) so the "no registry present"
behavior (silent no-op) is itself a first-class case, not just an implicit
default.
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
GATE = HOOKS / "skill-step-gate.py"
INJECT = HOOKS / "skill-step-inject.py"

# A generic two-surface contract (code block + named role) plus a glob-scoped
# artifact surface — the same shape shipped in skill-contracts.example.json,
# inlined here so the test doesn't depend on that file's exact content.
CONTRACTS = {
    "schema_version": 1,
    "mode": "block",
    "contracts": {
        "prompt-generator": {
            "surfaces": {
                "code_block": "```",
                "role_pattern": r"<role>\s*You are .{2,80}?[.\n]",
                "artifact_glob": ["**/prompts/**/*.md", "**/*-prompt-*.md"],
            },
            "interactive_escape": "which option would you like",
            "checklist": "[skill-step contract: prompt-generator] code block + named role + saved artifact required.",
        }
    },
}

# A fully-satisfying block: code fence + `<role>You are ...</role>` (matches
# role_pattern) + `<objective>` (satisfies the s1 marker check).
FULL_BLOCK = (
    "```\n"
    "<role>You are a branding consultant with 15 years in FMCG launches.</role>\n"
    "<objective>Produce three tagline options for the new product line.</objective>\n"
    "```\n"
)
# Same shape but the role line never says "You are" — role_pattern misses,
# while the literal "<objective" substring still satisfies the loose,
# content-first artifact check (mirrors the production incident's partial
# case: form present, the specific role-naming step skipped).
PARTIAL_BLOCK = "```xml\n<role>expert</role>\n<objective>Explain the goal.</objective>\n```\n"


def run_hook(hook: Path, payload: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    base_env = os.environ.copy()
    for key in ("FABLE_GATE_OFF", "FABLE_GATE_PILOT", "FABLE_SESSION_NAME"):
        base_env.pop(key, None)
    base_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=base_env,
        timeout=30,
    )


def blocked(proc: subprocess.CompletedProcess) -> tuple[bool, str]:
    out = proc.stdout.strip()
    if not out:
        return False, ""
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return False, ""
    if data.get("decision") == "block":
        return True, str(data.get("reason") or "")
    return False, ""


def injected(proc: subprocess.CompletedProcess) -> str:
    out = proc.stdout.strip()
    if not out:
        return ""
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return ""
    return str(data.get("hookSpecificOutput", {}).get("additionalContext") or "")


class SkillStepGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "project"
        self.root.mkdir()
        self.env = {"FABLE_STATE_DIR": str(self.tmp / "state")}

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers --------------------------------------------------------

    def write_registry(self, contracts: dict = CONTRACTS) -> None:
        (self.root / "skill-contracts.json").write_text(json.dumps(contracts), encoding="utf-8")

    def write_transcript(self, lines: list[dict], name: str = "transcript.jsonl") -> Path:
        path = self.tmp / name
        path.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
        return path

    def payload(self, transcript: Path, session_id: str = "s-skill-step", stop_hook_active: bool = False) -> dict:
        return {
            "session_id": session_id,
            "cwd": str(self.root),
            "transcript_path": str(transcript),
            "stop_hook_active": stop_hook_active,
        }

    @staticmethod
    def assistant_text(text: str) -> dict:
        return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}

    @staticmethod
    def assistant_skill_invoke(skill: str) -> dict:
        return {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": skill}}]},
        }

    @staticmethod
    def assistant_write(file_path: str, content: str) -> dict:
        return {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Write", "input": {"file_path": file_path, "content": content}}],
            },
        }

    # -- nominal ----------------------------------------------------------

    def test_no_registry_is_noop(self) -> None:  # nominal: opt-in default
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Sure, proceeding now."),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block, "no skill-contracts.json at cwd must be a silent no-op")

    def test_full_violation_blocks_with_all_three_named(self) -> None:  # nominal: the contract
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Sure, proceeding now."),
        ])
        block, reason = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertTrue(block)
        for token in ("code_block", "role_pattern", "artifact_saved"):
            self.assertIn(token, reason, reason)

    def test_full_contract_pass_via_write_and_real_file(self) -> None:  # nominal: compliant flow
        self.write_registry()
        artifact = self.root / "prompts" / "launch-prompt.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(FULL_BLOCK, encoding="utf-8")
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_write(str(artifact), FULL_BLOCK),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block)

    # -- deep ---------------------------------------------------------------

    def test_content_first_pass_on_arbitrary_unwritten_path(self) -> None:  # deep: R2 content-first
        self.write_registry()
        # This path never gets a real file on disk and doesn't match any
        # artifact_glob — the contract must still pass because the Write
        # *content* itself satisfies role_pattern (content-first judging).
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_write("/tmp/scratch/output.md", FULL_BLOCK),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block, "content-first s3 judging must not require glob match or file existence")

    def test_artifact_glob_and_file_existence_path_alone(self) -> None:  # deep: isolates the s3_path branch
        self.write_registry()
        # "**/prompts/**/*.md" needs a segment nested under prompts/ — mirrors
        # the production registry's own glob shape (meetings/**/...).
        artifact = self.root / "prompts" / "drafts" / "output.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("saved", encoding="utf-8")  # content alone does NOT satisfy s3_content
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text(FULL_BLOCK),  # s1/s2 satisfied via plain text, not the Write
            self.assistant_write(str(artifact), "saved"),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block, "glob match + real non-empty file must satisfy s3 on its own")

    def test_partial_violation_names_only_role_pattern(self) -> None:  # deep: loose s3, strict s2
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_write("/tmp/scratch/partial.md", PARTIAL_BLOCK),
        ])
        block, reason = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertTrue(block)
        self.assertIn("role_pattern", reason)
        self.assertNotIn("code_block", reason)
        self.assertNotIn("artifact_saved", reason)

    def test_interactive_escape_with_no_exec_after_passes(self) -> None:  # deep: no false-positive on waiting
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Options: research, image, or copy — which option would you like?"),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block)

    def test_interactive_escape_then_execution_is_judged(self) -> None:  # deep: escape does not blanket-exempt
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Options: research, image, or copy — which option would you like?"),
            self.assistant_write("/tmp/scratch/after-escape.md", "not a contract-shaped output"),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertTrue(block, "a tool call after the escape phrase means execution resumed and must be judged")

    def test_last_invoke_window_rearms_after_a_bad_first_attempt(self) -> None:  # deep: R3
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("first attempt, nothing produced"),
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_write("/tmp/scratch/second.md", FULL_BLOCK),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block, "verification window must be the segment after the LAST invoke")

    def test_bounce_capped_once_per_session_per_skill(self) -> None:  # deep: fail-open under a stuck loop
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("still nothing"),
        ])
        p = self.payload(t)
        first_block, _ = blocked(run_hook(GATE, p, self.env))
        self.assertTrue(first_block)
        second_block, _ = blocked(run_hook(GATE, p, self.env))
        self.assertFalse(second_block, "a second bounce for the same (session, skill) must not fire")

    def test_observe_mode_never_blocks(self) -> None:  # deep: staged rollout
        contracts = json.loads(json.dumps(CONTRACTS))
        contracts["mode"] = "observe"
        self.write_registry(contracts)
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Sure, proceeding now."),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block, "observe mode must measure, never block")

    # -- boundary -------------------------------------------------------------

    def test_unregistered_skill_ignored(self) -> None:  # boundary: registry scope
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("some-other-skill"),
            self.assistant_text("done, no contract for this one"),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block)

    def test_corrupt_registry_fails_open(self) -> None:  # boundary
        (self.root / "skill-contracts.json").write_text("{not valid json", encoding="utf-8")
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Sure, proceeding now."),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block)

    def test_corrupt_transcript_fails_open(self) -> None:  # boundary
        self.write_registry()
        t = self.tmp / "broken.jsonl"
        t.write_text("not valid json {{{ broken line\n", encoding="utf-8")
        block, _ = blocked(run_hook(GATE, self.payload(t), self.env))
        self.assertFalse(block)

    def test_missing_transcript_path_fails_open(self) -> None:  # boundary
        self.write_registry()
        payload = self.payload(self.tmp / "does-not-exist.jsonl")
        block, _ = blocked(run_hook(GATE, payload, self.env))
        self.assertFalse(block)

    def test_stop_hook_active_loop_guard(self) -> None:  # boundary
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Sure, proceeding now."),
        ])
        block, _ = blocked(run_hook(GATE, self.payload(t, stop_hook_active=True), self.env))
        self.assertFalse(block)

    def test_gate_off_kill_switch(self) -> None:  # boundary
        self.write_registry()
        t = self.write_transcript([
            self.assistant_skill_invoke("prompt-generator"),
            self.assistant_text("Sure, proceeding now."),
        ])
        env = dict(self.env)
        env["FABLE_GATE_OFF"] = "1"
        block, _ = blocked(run_hook(GATE, self.payload(t), env))
        self.assertFalse(block)


class SkillStepInjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "project"
        self.root.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_registry(self, contracts: dict = CONTRACTS) -> None:
        (self.root / "skill-contracts.json").write_text(json.dumps(contracts), encoding="utf-8")

    def payload(self, skill: str, tool_name: str = "Skill") -> dict:
        return {"cwd": str(self.root), "tool_name": tool_name, "tool_input": {"skill": skill}}

    def test_registered_skill_emits_checklist(self) -> None:  # nominal
        self.write_registry()
        ctx = injected(run_hook(INJECT, self.payload("prompt-generator")))
        self.assertIn("skill-step contract", ctx)

    def test_namespaced_skill_key_resolves(self) -> None:  # nominal: "plugin:skill" -> "skill"
        self.write_registry()
        ctx = injected(run_hook(INJECT, self.payload("some-plugin:prompt-generator")))
        self.assertIn("skill-step contract", ctx)

    def test_unregistered_skill_silent(self) -> None:  # boundary
        self.write_registry()
        ctx = injected(run_hook(INJECT, self.payload("brainstorming")))
        self.assertEqual(ctx, "")

    def test_no_registry_file_silent(self) -> None:  # boundary
        ctx = injected(run_hook(INJECT, self.payload("prompt-generator")))
        self.assertEqual(ctx, "")

    def test_corrupt_registry_silent(self) -> None:  # boundary
        (self.root / "skill-contracts.json").write_text("{not valid", encoding="utf-8")
        ctx = injected(run_hook(INJECT, self.payload("prompt-generator")))
        self.assertEqual(ctx, "")

    def test_non_skill_tool_silent(self) -> None:  # boundary
        self.write_registry()
        ctx = injected(run_hook(INJECT, self.payload("prompt-generator", tool_name="Write")))
        self.assertEqual(ctx, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
