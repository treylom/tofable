#!/usr/bin/env python3
"""Stop — skill-step contract gate (opt-in).

Failure class this catches: **skill invoked, steps skipped.** A skill can
carry a fully-specified output contract — "generate this structured block,
name a role, save the result to a file" — and inject the entire spec into
context on invoke, and a model will still skim past it and execute anyway.
This was mined from a live incident where a prompt-crystallization skill's
full instruction body (70k+ characters) was present verbatim in context at
invoke time, and the three required output steps were skipped regardless.
Same root finding as the rest of `hooks/` ("a written rule is not
enforcement" — see `docs/method.md`), applied to a *skill's own declared
output*, not to code/harness changes.

Design:
- **Opt-in, zero cost by default.** No `skill-contracts.json` at the project
  root -> no-op. This mirrors `requirements-lock.py`'s opt-in convention:
  the mechanism ships here, but nothing is enforced until you register a
  contract.
- **Contract registry.** Each entry maps a skill name to a small output
  contract with three checkable surfaces:
    - `code_block`   — a literal marker (e.g. "```") that must appear in the
                        output.
    - `role_pattern` — a regex a named-role declaration must match (e.g.
                        `<role>\\s*You are .{2,80}?\\.`).
    - `artifact_glob` — glob patterns; a `Write` after the invoke whose
                        `file_path` matches one of them AND is a real,
                        non-empty file counts as the artifact surface.
  The artifact surface is judged **content-first**: a `Write` whose content
  already satisfies the role pattern (or carries the marker this contract
  cares about) counts even when its path doesn't match any glob and even
  when the write never lands on disk during a dry-run transcript replay —
  the same content is also folded into the code-block/role-pattern checks.
  The glob+file-existence path is the fallback for contracts whose artifact
  lives somewhere the content check can't see.
- **Last-invoke window.** If the registered skill was invoked more than
  once in the session, only the segment *after the last invoke* is judged —
  a model that got it wrong once and re-ran the skill gets a fresh chance
  rather than being judged on a stale attempt.
- **Interactive escape.** A contract can declare an `interactive_escape`
  phrase (e.g. "which option would you like"). If that phrase appears and
  no tool call follows it, the transcript is read as "options presented,
  waiting on the user" rather than "skipped the contract" — this must not
  false-positive on ordinary interactive skill flows.
- **observe vs. block.** A contract (or the registry's top-level default)
  can set `"mode": "observe"` to log-shaped behavior without ever blocking
  — useful for piloting a new contract before trusting it to bounce a Stop.
  Default when unset: `"observe"` (a stranger copying this file for the
  first time should not get a silent hard-block they didn't ask for; the
  authoring project can flip its own `skill-contracts.json` to `"block"`
  once it trusts the contract — see `docs/gate-audit-playbook.md`).
- **Capped, fail-open.** At most one bounce per (session, skill) — a stuck
  loop must not wedge the session. Bookkeeping lives in its own small state
  file under `fable_lib.data_root()`, kept separate from the shared
  evidence ledger the other gates use (`fable_lib.py`'s `DEFAULT_LEDGER`
  schema is untouched by this file). Any parse failure, missing transcript,
  missing registry, or internal exception passes the Stop through
  unmodified.

This gate only verifies that the three surfaces *exist* — it does not judge
prompt/output quality. That's a human/reviewer job (see
`rules/verification.md`); this gate exists to catch the step being skipped
entirely, not to grade it.
"""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from fable_lib import data_root, gate_enabled, ledger_key, read_stdin_json
except Exception:
    sys.exit(0)

CONTRACTS_FILE = "skill-contracts.json"
DEFAULT_MODE = "observe"


def _load_contracts(root: Path) -> dict[str, Any] | None:
    path = root / CONTRACTS_FILE
    if not path.is_file():
        return None  # opt-in: no registry, no opinion
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None  # corrupt registry = fail-open
    return data if isinstance(data, dict) else None


def _state_path(input_data: dict[str, Any]) -> Path:
    return data_root() / "skill-step" / f"{ledger_key(input_data)}.json"


def _load_state(input_data: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(_state_path(input_data).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(input_data: dict[str, Any], state: dict[str, Any]) -> None:
    path = _state_path(input_data)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(path)  # atomic swap


def _read_transcript_entries(path_str: str) -> list[Any]:
    try:
        raw_lines = Path(path_str).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    entries: list[Any] = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue  # a corrupt individual line is skipped, not fatal
    return entries


def _skill_key(value: str) -> str:
    return value.split(":")[-1] if value else ""


def _find_last_invoke(entries: list[Any], contracts: dict[str, Any]) -> tuple[int, str] | None:
    """Index + key of the LAST registered-skill invoke (no early break —
    a later invoke re-arms the verification window over an earlier one)."""
    invoke_idx: int | None = None
    invoke_key: str | None = None
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                skill_val = str((block.get("input") or {}).get("skill") or "")
                key = _skill_key(skill_val)
                if key in contracts:
                    invoke_idx, invoke_key = i, key
    if invoke_idx is None or invoke_key is None:
        return None
    return invoke_idx, invoke_key


def _collect_after(
    entries: list[Any], start_idx: int, escape_phrase: str | None
) -> tuple[bool, str, list[str], list[str]]:
    """Body text + Write contents/paths for the segment after start_idx.

    Returns (skip, body, write_contents, write_paths). `skip` is True only
    when an interactive-escape phrase appeared with no tool call after it —
    the session is waiting on the user, not skipping the contract, and the
    caller must treat that as a pass regardless of how empty everything
    else looks. When nothing at all follows the invoke (no text, no tool
    calls), `skip` is False and every surface is judged missing — silence
    after an invoke is the violation this gate exists to catch, not a
    reason to wave it through.
    """
    body_parts: list[str] = []
    write_contents: list[str] = []
    write_paths: list[str] = []
    escape_idx: int | None = None
    exec_after_escape = False

    for i in range(start_idx + 1, len(entries)):
        entry = entries[i]
        if not isinstance(entry, dict):
            continue
        message = entry.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        has_tool_use_here = False
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                text = str(block.get("text") or "")
                body_parts.append(text)
                if escape_phrase and escape_phrase in text:
                    escape_idx = i
            elif btype == "tool_use":
                has_tool_use_here = True
                if block.get("name") == "Write":
                    tool_input = block.get("input") or {}
                    c = str(tool_input.get("content") or "")
                    body_parts.append(c)
                    write_contents.append(c)
                    fp = tool_input.get("file_path")
                    if fp:
                        write_paths.append(str(fp))
        if escape_idx is not None and i > escape_idx and has_tool_use_here:
            exec_after_escape = True

    if escape_idx is not None and not exec_after_escape:
        return True, "", [], []  # waiting on the user — not a violation

    return False, "\n".join(body_parts), write_contents, write_paths


def _surfaces_missing(
    contract: dict[str, Any], body: str, write_contents: list[str], write_paths: list[str]
) -> list[str]:
    surfaces = contract.get("surfaces") or {}
    code_marker = surfaces.get("code_block")
    role_pattern = surfaces.get("role_pattern")
    artifact_globs = surfaces.get("artifact_glob") or []
    role_re = re.compile(role_pattern, re.DOTALL) if role_pattern else None

    s1 = bool(code_marker) and (code_marker in body) and (("<objective" in body) or ("<role" in body))
    s2 = bool(role_re) and role_re.search(body) is not None

    s3_content = any(
        (role_re and role_re.search(c)) or ("<objective" in c) for c in write_contents
    )
    s3_path = False
    for fp in write_paths:
        if any(fnmatch.fnmatch(fp, g) for g in artifact_globs):
            try:
                p = Path(fp)
                if p.is_file() and p.stat().st_size > 0:
                    s3_path = True
                    break
            except OSError:
                continue
    s3 = s3_content or s3_path

    missing = []
    if not s1:
        missing.append("code_block")
    if not s2:
        missing.append("role_pattern")
    if not s3:
        missing.append("artifact_saved")
    return missing


def main() -> int:
    try:
        input_data = read_stdin_json()
        if not input_data:
            return 0
        if input_data.get("stop_hook_active") is True:
            return 0  # loop guard
        if not gate_enabled():
            return 0

        root = Path(str(input_data.get("cwd") or "."))
        contracts_data = _load_contracts(root)
        if not contracts_data:
            return 0

        contracts = contracts_data.get("contracts")
        if not isinstance(contracts, dict) or not contracts:
            return 0
        registry_mode = str(contracts_data.get("mode") or DEFAULT_MODE)

        transcript_path = str(input_data.get("transcript_path") or "")
        if not transcript_path:
            return 0
        entries = _read_transcript_entries(transcript_path)
        if not entries:
            return 0

        found = _find_last_invoke(entries, contracts)
        if found is None:
            return 0  # no registered skill invoked this session — scope is per-skill opt-in
        invoke_idx, invoke_key = found
        contract = contracts.get(invoke_key) or {}

        state = _load_state(input_data)
        bounced = state.get("bounced")
        if not isinstance(bounced, dict):
            bounced = {}
        if bounced.get(invoke_key):
            return 0  # one bounce per (session, skill) already spent

        escape_phrase = contract.get("interactive_escape")
        skip, body, write_contents, write_paths = _collect_after(entries, invoke_idx, escape_phrase)
        if skip:
            return 0  # options presented, waiting on the user — not a violation

        missing = _surfaces_missing(contract, body, write_contents, write_paths)
        if not missing:
            return 0

        mode = str(contract.get("mode") or registry_mode)
        if mode != "block":
            return 0  # observe: measure only, never block

        bounced[invoke_key] = True
        state["bounced"] = bounced
        _save_state(input_data, state)
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"skill-step-gate: '{invoke_key}' was invoked and its registered output "
                f"contract is missing: {', '.join(missing)}. A written skill spec is not "
                "enforcement — finish the missing surface(s) before ending the turn. If this "
                "is a false positive, the identical stop passes next time (one bounce per "
                "skill per session)."
            ),
        }, ensure_ascii=False))
        return 0
    except Exception:
        return 0  # fail-open, always


if __name__ == "__main__":
    sys.exit(main())
