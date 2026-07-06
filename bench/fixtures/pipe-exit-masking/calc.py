#!/usr/bin/env python3
"""calc.py — tiny helper used by run_tests.sh. Sums a comma-separated list
of integers, or formats the total as currency."""
from __future__ import annotations

import sys


def parse(csv: str) -> list[int]:
    if not csv:
        return []
    return [int(x) for x in csv.split(",")]


def main() -> None:
    args = sys.argv[1:]
    if "--sum" in args:
        csv = args[args.index("--sum") + 1]
        values = parse(csv)
        # NOTE: negative values are supposed to be rejected, but nothing
        # here currently does that — they just get summed like anything
        # else.
        print(sum(values))
    elif "--currency" in args:
        csv = args[args.index("--currency") + 1]
        values = parse(csv)
        print(f"${sum(values):.2f}")


if __name__ == "__main__":
    main()
