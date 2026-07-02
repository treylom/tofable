#!/usr/bin/env python3
"""due_soon tests — reproduces the bug report. Run with: python3 test_due_soon.py"""
from __future__ import annotations

import unittest
from datetime import date

from due_soon import due_soon


class T(unittest.TestCase):
    today = date(2026, 7, 2)

    def tasks(self):
        return [
            {"name": "today", "due": date(2026, 7, 2)},
            {"name": "d3", "due": date(2026, 7, 5)},
            {"name": "d5", "due": date(2026, 7, 7)},   # due in exactly 5 days — should be included
            {"name": "d6", "due": date(2026, 7, 8)},   # due in 6 days — should be excluded
            {"name": "past", "due": date(2026, 7, 1)},
            {"name": "none", "due": None},
        ]

    def test_nth_day_included(self):
        names = [t["name"] for t in due_soon(self.tasks(), self.today)]
        self.assertIn("d5", names, "task due in exactly window_days should be included — bug reproduction")

    def test_day_after_window_excluded(self):
        names = [t["name"] for t in due_soon(self.tasks(), self.today)]
        self.assertNotIn("d6", names)

    def test_today_included_past_excluded(self):
        names = [t["name"] for t in due_soon(self.tasks(), self.today)]
        self.assertIn("today", names)
        self.assertNotIn("past", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
