#!/usr/bin/env python3
"""Convert Codex exec JSONL transcripts into judge-readable dialogue text.

The Claude bench judge consumes a plain behavioural transcript. Codex gives us
two useful streams: stdout from `codex exec --json` and persisted session
JSONL/rollout files. This adapter accepts either a run directory or one or more
JSONL files, extracts user/assistant/tool/result content where the schema is
known, and falls back to compact JSON for unfamiliar event shapes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("input")
                if text:
                    parts.append(_as_text(text))
                elif item.get("type") == "tool_use":
                    parts.append(
                        f"tool_use {item.get('name', '<tool>')} "
                        f"{json.dumps(item.get('input', {}), ensure_ascii=False, sort_keys=True)}"
                    )
                elif item.get("type") == "tool_result":
                    parts.append(_as_text(item.get("content")))
            else:
                parts.append(_as_text(item))
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        if "text" in value:
            return _as_text(value["text"])
        if "content" in value:
            return _as_text(value["content"])
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _label_event(event: dict[str, Any]) -> tuple[str, str]:
    kind = str(event.get("type") or event.get("event") or event.get("msg") or "event")

    if kind in {"item.started", "item.completed"}:
        item = event.get("item")
        if isinstance(item, dict):
            item_type = str(item.get("type") or "item")
            status = item.get("status") or ("completed" if kind == "item.completed" else "started")
            if item_type == "agent_message":
                return "ASSISTANT", _as_text(item.get("text") or item.get("content"))
            if item_type == "command_execution":
                output = _as_text(item.get("aggregated_output"))
                command = item.get("command") or "<command>"
                exit_code = item.get("exit_code")
                text = f"{command}\nstatus={status} exit_code={exit_code}"
                if output:
                    text += f"\n{output}"
                return "COMMAND", text
            if item_type == "file_change":
                return "FILE_CHANGE", json.dumps(
                    {"status": status, "changes": item.get("changes") or []},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            if item_type == "error":
                return "ERROR", _as_text(item.get("message"))
            return item_type.upper(), json.dumps(item, ensure_ascii=False, sort_keys=True)

    if kind in {"user", "input"}:
        return "USER", _as_text(event.get("message") or event.get("content") or event.get("prompt"))

    if kind == "assistant":
        message = event.get("message")
        if isinstance(message, dict):
            return "ASSISTANT", _as_text(message.get("content"))
        return "ASSISTANT", _as_text(event.get("content") or message)

    if kind in {"agent_message", "message"}:
        role = str(event.get("role") or event.get("source") or "assistant").upper()
        return role, _as_text(event.get("content") or event.get("message"))

    if kind in {"tool_call", "tool_use"}:
        name = event.get("name") or event.get("tool") or event.get("recipient") or "tool"
        payload = event.get("input") if "input" in event else event.get("arguments")
        return "TOOL", f"{name} {json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)}"

    if kind in {"tool_result", "tool_output"}:
        name = event.get("name") or event.get("tool") or "tool"
        return "TOOL_RESULT", f"{name}: {_as_text(event.get('content') or event.get('output'))}"

    if kind == "result":
        return "RESULT", _as_text(event.get("result") or event.get("output") or event.get("message"))

    if "message" in event or "content" in event:
        return kind.upper(), _as_text(event.get("message") or event.get("content"))

    return kind.upper(), json.dumps(event, ensure_ascii=False, sort_keys=True)


def _jsonl_files(paths: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            candidates = [path / "transcript.jsonl"]
            rollouts = path / "rollouts"
            if rollouts.exists():
                candidates.extend(sorted(rollouts.glob("*.jsonl")))
            out.extend(p for p in candidates if p.exists())
        elif path.exists():
            out.append(path)
    return out


def convert(paths: list[Path]) -> str:
    blocks: list[str] = []
    seen: set[Path] = set()
    for file in _jsonl_files(paths):
        real = file.resolve()
        if real in seen:
            continue
        seen.add(real)
        events: list[str] = []
        for line in file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                events.append(f"RAW: {line}")
                continue
            if not isinstance(event, dict):
                events.append(f"RAW: {json.dumps(event, ensure_ascii=False)}")
                continue
            label, text = _label_event(event)
            if text.strip():
                events.append(f"{label}: {text.strip()}")
        if events:
            blocks.append(f"### {file.name}\n" + "\n\n".join(events))
    return "\n\n".join(blocks).strip() + ("\n" if blocks else "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path, help="Codex run directory or JSONL file")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    text = convert(args.paths)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
