#!/usr/bin/env python3
"""PostToolUse (matcher: Skill) — skill-step contract preview (opt-in).

Companion to `skill-step-gate.py` (Stop). That gate catches a missing
output contract *after the fact*, at turn-end — useful, but a bounce is a
whole extra round-trip. This hook fires the moment a registered skill is
invoked and immediately surfaces its checklist into context, before the
model has decided how to respond. The pairing is the same
prevent-then-catch shape as the rest of `hooks/`: cheap prevention first,
a capped catch as the backstop.

Contract: reads the same opt-in `skill-contracts.json` at the project root
that `skill-step-gate.py` reads. If the invoked skill has a `checklist`
string registered, emit it as `additionalContext` on the PostToolUse
response. No file, no matching contract, or no `checklist` field -> silent
no-op (zero cost) — this must never fire for a skill nobody registered.

The checklist text is read straight from the registry (single source of
truth shared with the Stop gate) rather than hard-coded here, so editing
one contract entry updates both the preview and what the gate checks for.

Fail-open on any exception, any missing/corrupt input, any non-`Skill`
tool call.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CONTRACTS_FILE = "skill-contracts.json"


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        input_data = json.loads(raw)
        if not isinstance(input_data, dict):
            return 0
        if str(input_data.get("tool_name") or "") != "Skill":
            return 0

        skill_val = str((input_data.get("tool_input") or {}).get("skill") or "")
        if not skill_val:
            return 0
        key = skill_val.split(":")[-1]

        root = Path(str(input_data.get("cwd") or "."))
        contracts_path = root / CONTRACTS_FILE
        if not contracts_path.is_file():
            return 0
        try:
            data = json.loads(contracts_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0  # corrupt registry = fail-open

        contracts = data.get("contracts") if isinstance(data, dict) else None
        if not isinstance(contracts, dict):
            return 0
        contract = contracts.get(key)
        if not isinstance(contract, dict):
            return 0  # unregistered skill — zero cost

        checklist = str(contract.get("checklist") or "").strip()
        if not checklist:
            return 0

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": checklist,
            }
        }, ensure_ascii=False))
        return 0
    except Exception:
        return 0  # fail-open, always


if __name__ == "__main__":
    sys.exit(main())
