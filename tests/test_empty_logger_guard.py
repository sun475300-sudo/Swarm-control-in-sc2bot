"""Unit tests for scripts/check_no_empty_logger_calls.py.

Why: the empty-logger CI workflow (.github/workflows/empty-logger-guard.yml)
is the only thing protecting us from a repeat of the bug fixed in commit
2e03d2f (131 empty logger.<level>() calls left behind by the print->logger
migration). If the script silently breaks — wrong regex, missing import,
exit-code change — CI keeps reporting green and the regression slips
through. These tests pin the contract.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_no_empty_logger_calls.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_check_no_empty_logger_calls", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard():
    return _load_module()


class TestEmptyCallRegex:
    def test_matches_empty_info(self, guard):
        assert guard.EMPTY_CALL_RE.search("    logger.info()")

    def test_matches_empty_debug(self, guard):
        assert guard.EMPTY_CALL_RE.search("logger.debug()")

    def test_matches_empty_with_whitespace(self, guard):
        assert guard.EMPTY_CALL_RE.search("logger.warning(   )")

    def test_matches_each_known_level(self, guard):
        for level in ("debug", "info", "warning", "warn",
                      "error", "critical", "exception"):
            assert guard.EMPTY_CALL_RE.search(f"logger.{level}()"), level

    def test_does_not_match_non_empty(self, guard):
        assert not guard.EMPTY_CALL_RE.search('logger.info("hello")')

    def test_does_not_match_partial_name(self, guard):
        # `mylogger.info()` is not the bug class — only `logger.<level>()`.
        assert not guard.EMPTY_CALL_RE.search("mylogger.info()")

    def test_does_not_match_unknown_level(self, guard):
        assert not guard.EMPTY_CALL_RE.search("logger.trace()")


class TestFindOffenders:
    def test_clean_dir_returns_empty(self, guard, tmp_path):
        (tmp_path / "ok.py").write_text(
            'logger.info("kept")\nlogger.debug("also kept")\n',
            encoding="utf-8",
        )
        assert guard.find_offenders([tmp_path]) == []

    def test_dirty_dir_lists_each_offender(self, guard, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_text(
            "logger.info()\n"
            'logger.warning("kept")\n'
            "logger.debug(   )\n",
            encoding="utf-8",
        )
        offenders = guard.find_offenders([tmp_path])
        # 2 empty calls (lines 1 and 3), the warning("kept") line is fine.
        assert len(offenders) == 2
        assert {ln for _, ln, _ in offenders} == {1, 3}

    def test_skips_pycache(self, guard, tmp_path):
        cache = tmp_path / "pkg" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "stale.py").write_text("logger.info()\n", encoding="utf-8")
        assert guard.find_offenders([tmp_path]) == []

    def test_missing_root_is_silent(self, guard, tmp_path):
        # Don't crash if a caller passes a path that hasn't been created yet.
        assert guard.find_offenders([tmp_path / "nope"]) == []


class TestMainExitCode:
    def test_exit_zero_on_clean_tree(self, guard, tmp_path, capsys):
        (tmp_path / "ok.py").write_text(
            'logger.info("kept")\n', encoding="utf-8"
        )
        assert guard.main([str(tmp_path)]) == 0
        assert "OK" in capsys.readouterr().out

    def test_exit_one_on_offender(self, guard, tmp_path, capsys):
        (tmp_path / "bad.py").write_text("logger.info()\n", encoding="utf-8")
        assert guard.main([str(tmp_path)]) == 1
        assert "FAIL" in capsys.readouterr().out


class TestRepoIsClean:
    """Smoke test: the live repo has no empty logger calls right now."""

    def test_wicked_zerg_challenger_clean(self, guard):
        offenders = guard.find_offenders(
            [REPO_ROOT / "wicked_zerg_challenger"]
        )
        # If this fails, run the full file:line list it produces — each
        # entry is a logger.<level>() that must be filled in or removed.
        assert offenders == [], f"{len(offenders)} empty logger call(s)"
