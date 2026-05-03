# -*- coding: utf-8 -*-
"""
Closure Capture Lint Guard
==========================

이 테스트는 `for x in items: ... lambda: ...x...` 형태의 루프 변수
지연-바인딩 버그(B023)를 ruff가 잡는지 회귀 검증합니다.

배경: 2026-05-03 27건의 B023 버그를 수정 (전투/경제/정찰 전반).
같은 패턴이 다시 들어오면 CI에서 차단되도록 가드를 추가합니다.

이 테스트는 wicked_zerg_challenger 디렉토리 전체를 ruff로 검사합니다.
ruff가 설치되어 있지 않으면 skip합니다.
"""

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _has_ruff() -> bool:
    return shutil.which("ruff") is not None


@pytest.mark.skipif(not _has_ruff(), reason="ruff not installed")
def test_no_b023_loop_closure_bugs():
    """루프 안 lambda가 루프 변수를 지연 바인딩하는 패턴 금지."""
    result = subprocess.run(
        ["ruff", "check", "--select=B023", "--no-fix", str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"B023 (function-uses-loop-variable) 위반 발견:\n{result.stdout}\n{result.stderr}\n"
        "수정법: `lambda x: ... var ...` → `lambda x, v=var: ... v ...`"
    )


@pytest.mark.skipif(not _has_ruff(), reason="ruff not installed")
def test_no_b004_unreliable_callable_check():
    """`hasattr(x, "__call__")` 금지 — `callable(x)` 사용."""
    result = subprocess.run(
        ["ruff", "check", "--select=B004", "--no-fix", str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"B004 (unreliable-callable-check) 위반 발견:\n{result.stdout}\n{result.stderr}"
    )


@pytest.mark.skipif(not _has_ruff(), reason="ruff not installed")
def test_no_f823_undefined_local():
    """함수내 `import foo` 재선언으로 모듈 임포트가 가려지는 경우 차단."""
    result = subprocess.run(
        ["ruff", "check", "--select=F823", "--no-fix", str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"F823 (undefined-local) 위반 발견:\n{result.stdout}\n{result.stderr}"
    )


@pytest.mark.skipif(not _has_ruff(), reason="ruff not installed")
def test_no_f811_redefined_unused():
    """동일 메서드/함수 재정의로 첫 정의가 가려지는 경우 차단.

    opponent_modeling.py의 on_step 처럼 두 번째 정의가
    (의도치 않게) 첫 번째의 모든 로직을 덮어쓰는 사례 방지.
    """
    result = subprocess.run(
        ["ruff", "check", "--select=F811", "--no-fix", str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"F811 (redefined-while-unused) 위반 발견:\n{result.stdout}\n{result.stderr}"
    )


@pytest.mark.skipif(not _has_ruff(), reason="ruff not installed")
def test_no_b905_zip_without_strict():
    """`zip(...)` 호출 시 `strict=` 키워드 명시 강제 (Python 3.10+).

    길이가 다른 iterable을 silently 절단하는 버그를 차단.
    """
    result = subprocess.run(
        ["ruff", "check", "--select=B905", "--no-fix", str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"B905 (zip-without-explicit-strict) 위반 발견:\n{result.stdout}\n{result.stderr}\n"
        "수정법: `zip(a, b)` → `zip(a, b, strict=False)` 또는 `strict=True`"
    )
