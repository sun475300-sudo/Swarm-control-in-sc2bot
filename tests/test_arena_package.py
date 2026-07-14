"""Regression tests for create_arena_package.py's ROADMAP Task 8.2 size gate.

Task 8.2 requires the generated Arena ZIP stay under 10MB. Previously the
script only printed the size with no automated pass/fail signal, so an
oversized package would silently upload-fail on aiarena.net. These tests
verify create_arena_zip() reports whether the budget was met.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from create_arena_package import create_arena_zip


def test_real_package_is_within_default_budget(tmp_path):
    zip_path, zip_size_mb, within_budget = create_arena_zip(tmp_path, "arena_test.zip")

    assert Path(zip_path).exists()
    assert within_budget is True
    assert zip_size_mb < 10


def test_within_budget_is_false_when_max_size_is_forced_too_small(tmp_path):
    zip_path, zip_size_mb, within_budget = create_arena_zip(
        tmp_path, "arena_test_tiny_budget.zip", max_size_mb=0.001
    )

    assert Path(zip_path).exists()
    assert within_budget is False
    assert zip_size_mb > 0.001
