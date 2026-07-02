#!/usr/bin/env python3
"""Due-soon filter — returns tasks due within N days of today (today
included, the Nth day included)."""
from __future__ import annotations

from datetime import date


def due_soon(tasks: list[dict], today: date, window_days: int = 5) -> list[dict]:
    """Return tasks due within window_days (today included, the Nth day
    included), sorted by due date ascending."""
    out = []
    for task in tasks:
        due = task.get("due")
        if due is None:
            continue
        delta = (due - today).days
        if 0 <= delta < window_days:
            out.append(task)
    return sorted(out, key=lambda x: x["due"])
