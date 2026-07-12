#!/usr/bin/env python3
"""Codex UserPromptSubmit hook: lightweight ledger seeding for tofable gates."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from lib import default_ledger, gate_enabled, ledger_path, read_stdin_json, save_ledger
except Exception:
    raise SystemExit(0)


def main() -> int:
    try:
        input_data = read_stdin_json()
        if input_data and gate_enabled():
            # Seed only on first touch (2026-07-13 rereview C4). UserPromptSubmit
            # fires on every user TURN — wiping here erased pending verification
            # obligations and reset every bounce budget each turn. The ledger is
            # already per-session (its key hashes session_id), so a new session
            # gets a fresh file without any explicit reset.
            if not ledger_path(input_data).exists():
                save_ledger(input_data, default_ledger())
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
