"""Small date-parsing helper used by analyze.py."""
from __future__ import annotations

from datetime import date


def parse_iso(value: str) -> date:
    y, m, d = (int(x) for x in value.split("-"))
    return date(y, m, d)
