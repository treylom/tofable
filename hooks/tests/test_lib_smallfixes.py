#!/usr/bin/env python3
"""Regressions from the 2026-07-13 rereview LOW batch.

Run: python3 hooks/tests/test_lib_smallfixes.py

- C9b: the code-surface heuristic covers the common languages a public
  reference implementation will meet (PHP/Kotlin/Dart/C#/Elixir/Haskell/
  Scala/Terraform/proto/HTML), and lockfiles count as config (codex parity).
- C9c: ledger files accumulate one-per-(session,cwd) forever without a
  prune — first touch of a new ledger sweeps siblings older than the TTL.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))
import fable_lib  # noqa: E402


class CodeExtsCoverageTests(unittest.TestCase):
    def test_more_languages_classify_as_code(self) -> None:
        for name in (
            "handler.php",
            "App.kt",
            "build.kts",
            "main.dart",
            "Service.cs",
            "task.ex",
            "query.exs",
            "Main.hs",
            "Build.scala",
            "network.tf",
            "schema.proto",
            "index.html",
        ):
            self.assertEqual(fable_lib.classify_path_kind(f"/workspace/proj/src/{name}"), "code", name)

    def test_lockfile_classifies_as_config(self) -> None:
        self.assertEqual(fable_lib.classify_path_kind("/workspace/proj/Cargo.lock"), "config")

    def test_markdown_still_docs(self) -> None:
        self.assertEqual(fable_lib.classify_path_kind("/workspace/proj/notes/plan.md"), "docs")


class LedgerPruneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="tofable-prune-")
        self._old_env = os.environ.get("FABLE_STATE_DIR")
        os.environ["FABLE_STATE_DIR"] = self.tmp.name

    def tearDown(self) -> None:
        if self._old_env is None:
            os.environ.pop("FABLE_STATE_DIR", None)
        else:
            os.environ["FABLE_STATE_DIR"] = self._old_env
        self.tmp.cleanup()

    def test_stale_ledger_pruned_on_first_touch(self) -> None:
        stale = fable_lib.save_ledger({"session_id": "stale-sess", "cwd": "/w"}, fable_lib.default_ledger())
        stale_lock = Path(f"{stale}.lock")
        stale_lock.touch()
        old = time.time() - 40 * 86400
        os.utime(stale, (old, old))

        fresh = fable_lib.save_ledger({"session_id": "fresh-sess", "cwd": "/w"}, fable_lib.default_ledger())

        # a brand-new session's first load triggers the sweep
        fable_lib.load_ledger({"session_id": "new-sess", "cwd": "/w"})

        self.assertFalse(stale.exists(), "stale ledger should be pruned")
        self.assertFalse(stale_lock.exists(), "stale ledger's lock should be pruned with it")
        self.assertTrue(fresh.exists(), "recent sibling must survive")


if __name__ == "__main__":
    unittest.main(verbosity=1)
