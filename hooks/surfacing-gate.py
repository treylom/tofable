#!/usr/bin/env python3
"""PreToolUse (Bash) — destructive-op surfacing gate.

The mechanical half of the "surface destructive ops" discipline: when a Bash
command carries a destructive token (recursive/forced rm, force-push, hard
reset, `git clean -f`, `find ... -delete`, mass wipes), the gate bounces the
call ONCE and asks the agent to surface the op in its visible reply — what is
being destroyed, which paths, and why it is safe — then re-run the same
command. The identical command (by hash) passes on the retry, so this never
blocks work; it only makes silent destruction impossible.

Mined from live incidents: an `rm` buried inside a dispatch prompt that the
user had to interrupt by hand; a 10k-file wipe of the user's notes store
from a mis-scoped sync; a blind `git add -A` across a repo boundary that
lost files. In each case the operation itself was arguably routine — the
silence around it was the failure.

Fail-open on any exception; same kill switch / pilot scoping as the other
gates (FABLE_GATE_OFF / FABLE_GATE_PILOT). Per-command bounce is capped by
hash; a session-wide cap (MAX_SURFACING_BLOCKS) bounds worst-case friction
from false positives.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from fable_lib import gate_enabled, load_ledger, read_stdin_json, save_ledger
except Exception:
    sys.exit(0)

MAX_SURFACING_BLOCKS = 5  # session-wide cap — bounds false-positive friction

# Anchored at a command position (start of line, or after ;, &&, ||, |, $( )
# so destructive words inside grep patterns / echoed prose don't match.
CMD_ANCHOR = r"(?:^|[;&|]\s*|\$\(\s*|`\s*)"
DESTRUCTIVE_PATTERNS = [
    CMD_ANCHOR + r"rm\s+(?:-[a-zA-Z]*\s+)*-[a-zA-Z]*[rfRF][a-zA-Z]*\b",  # rm -r / -f / -rf ...
    CMD_ANCHOR + r"git\s+push\b[^\n;|&]*(?:--force(?:-with-lease)?|\s-f\b)",
    CMD_ANCHOR + r"git\s+reset\s+--hard\b",
    CMD_ANCHOR + r"git\s+clean\b[^\n;|&]*-[a-zA-Z]*f",
    CMD_ANCHOR + r"git\s+branch\s+(?:-D|--delete\s+--force)\b",
    CMD_ANCHOR + r"find\b[^\n;|&]*\s-delete\b",
    CMD_ANCHOR + r"(?:rmdir|shred|mkfs\.[a-z0-9]+)\b",
    CMD_ANCHOR + r"truncate\s+-s\s*0\b",
    CMD_ANCHOR + r"rsync\b[^\n]*--delete\b",
]
# Content patterns live inside quoted program text (`python3 -c "...
# shutil.rmtree(...)"`, SQL handed to a client), so they cannot be
# command-anchored. Instead, a pure read-only search/filter pipeline that
# merely MENTIONS them is exempted (2026-07-13 rereview C9a) — it cannot
# execute them, and bouncing a grep for dangerous code punished exactly the
# kind of careful auditing the gates exist to encourage.
DESTRUCTIVE_CONTENT_PATTERNS = [
    r"\bshutil\.rmtree\s*\(",
    r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b",
]
DESTRUCTIVE_RE = re.compile("|".join(DESTRUCTIVE_PATTERNS), re.IGNORECASE)
DESTRUCTIVE_CONTENT_RE = re.compile("|".join(DESTRUCTIVE_CONTENT_PATTERNS), re.IGNORECASE)
READONLY_SEGMENT_RE = re.compile(
    r"^(?:grep|rg|ag|ack|egrep|fgrep|head|tail|wc|sort|uniq|cut|awk|sed|cat|echo|less|find|ls|git\s+(?:grep|log|show|diff))\b",
    re.IGNORECASE,
)


def readonly_search_pipeline(command: str) -> bool:
    segments = [s.strip() for s in re.split(r"[;&|]+|\$\(|`", command) if s.strip()]
    return bool(segments) and all(READONLY_SEGMENT_RE.match(s) for s in segments)


def destructive_match(command: str):
    match = DESTRUCTIVE_RE.search(command)
    if match:
        return match
    match = DESTRUCTIVE_CONTENT_RE.search(command)
    if match and not readonly_search_pipeline(command):
        return match
    return None

REASON = (
    "surfacing-gate: this command contains a destructive operation ({token}). "
    "Not blocked — but surface it first: state in your visible reply (1) the "
    "exact operation, (2) the paths/targets it destroys, (3) why that is safe "
    "or intended (backup, user instruction, disposable artifact). Then re-run "
    "the same command — the identical command passes on retry."
)


def command_of(input_data: dict[str, Any]) -> str:
    tool_input = input_data.get("tool_input")
    if isinstance(tool_input, dict):
        return str(tool_input.get("command") or "")
    return ""


def cmd_hash(command: str) -> str:
    return hashlib.sha256(command.strip().encode("utf-8", "replace")).hexdigest()[:16]


def main() -> int:
    try:
        input_data: dict[str, Any] = read_stdin_json()
        if not input_data:
            return 0
        if str(input_data.get("tool_name") or "") != "Bash":
            return 0
        if not gate_enabled():
            return 0
        command = command_of(input_data)
        if not command:
            return 0
        match = destructive_match(command)
        if not match:
            return 0
        ledger = load_ledger(input_data)
        surfaced = ledger.get("surfaced_ops")
        if not isinstance(surfaced, list):
            surfaced = []
        digest = cmd_hash(command)
        if digest in surfaced:
            return 0  # same command re-issued after the bounce — intent confirmed
        if int(ledger.get("surfacing_blocks") or 0) >= MAX_SURFACING_BLOCKS:
            return 0  # session cap reached — stop adding friction
        surfaced.append(digest)
        ledger["surfaced_ops"] = surfaced[-40:]
        ledger["surfacing_blocks"] = int(ledger.get("surfacing_blocks") or 0) + 1
        save_ledger(input_data, ledger)
        token = match.group(0).strip()[:60]
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": REASON.format(token=token),
                    }
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception:
        return 0  # fail-open


if __name__ == "__main__":
    raise SystemExit(main())
