# -*- coding: utf-8 -*-
"""Smoke tests for ``wicked_zerg_challenger/tools/check_missing_logic.py``.

The previous version of the script had a fatal bug: it tried to unpack each
``Path`` returned by ``rglob`` as if it were ``os.walk``'s
``(root, dirs, files)`` triple, which raises ``TypeError`` on the very first
iteration. These tests pin the corrected behaviour: the scanner must walk a
small temporary tree without raising and must surface obvious findings
(missing-implementation, bare ``pass``, ``TODO``).
"""

import os
import sys
from pathlib import Path

import pytest

# Add the wicked_zerg_challenger root to sys.path so ``tools.*`` imports resolve.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import check_missing_logic  # noqa: E402
from tools.check_missing_logic import MissingLogicChecker  # noqa: E402


@pytest.fixture()
def fake_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a tiny project tree and point the checker at it."""
    src = tmp_path / "pkg"
    src.mkdir()

    (src / "good.py").write_text(
        "class A:\n"
        "    def _ok(self):\n"
        "        return self._helper()\n"
        "    def _helper(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )

    (src / "missing.py").write_text(
        "class B:\n"
        "    def go(self):\n"
        "        return self._not_defined_anywhere()\n",
        encoding="utf-8",
    )

    (src / "todos.py").write_text(
        "def stub():\n"
        "    # TODO: implement\n"
        "    pass\n",
        encoding="utf-8",
    )

    # Excluded directory must be skipped.
    cache = src / "__pycache__"
    cache.mkdir()
    (cache / "should_skip.py").write_text("def boom(): raise Exception()\n", encoding="utf-8")

    monkeypatch.setattr(check_missing_logic, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_scan_all_does_not_raise(fake_project: Path) -> None:
    """Regression test: ``scan_all`` used to crash with ``TypeError`` immediately."""
    checker = MissingLogicChecker()
    results = checker.scan_all()  # must not raise
    assert isinstance(results, dict)
    assert {"missing_implementations", "pass_statements", "todo_comments"} <= results.keys()


def test_scan_all_finds_missing_method(fake_project: Path) -> None:
    checker = MissingLogicChecker()
    results = checker.scan_all()
    methods = {item["method"] for item in results["missing_implementations"]}
    assert "_not_defined_anywhere" in methods


def test_scan_all_finds_pass_and_todo(fake_project: Path) -> None:
    checker = MissingLogicChecker()
    results = checker.scan_all()
    todo_files = {Path(p).name for p in results["todo_comments"]}
    assert "todos.py" in todo_files
    pass_files = {Path(p).name for p in results["pass_statements"]}
    assert "todos.py" in pass_files


def test_excluded_dirs_are_skipped(fake_project: Path) -> None:
    checker = MissingLogicChecker()
    results = checker.scan_all()
    all_files = (
        list(results["pass_statements"])
        + list(results["todo_comments"])
        + [item["file"] for item in results["missing_implementations"]]
    )
    assert not any("__pycache__" in p for p in all_files)
