"""Reads the working dataset and prints basic stats.

Usage: python3 analyze.py
"""
from __future__ import annotations

import csv
from pathlib import Path

from utils import parse_iso

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "dataset.csv.bak"


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows = load_rows(DATA_PATH)
    dates = sorted(parse_iso(r["date"]) for r in rows)
    total = sum(float(r["amount"]) for r in rows)
    print(f"loaded {len(rows)} rows from {DATA_PATH.name}")
    print(f"date range: {dates[0]} .. {dates[-1]}")
    print(f"total amount: {total:.2f}")


if __name__ == "__main__":
    main()
