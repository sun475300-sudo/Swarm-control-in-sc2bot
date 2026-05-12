# -*- coding: utf-8 -*-
"""
회귀 테스트: wicked_zerg_challenger 패키지의 모든 모듈이 파싱되어야 한다.

라운드 1에서 game_analytics_system.py 안의 중복된 except/log 블록 때문에
IndentationError(E999)가 생겨 일부 임포트 경로가 깨졌었다.
같은 종류의 문법 사고가 다시 들어오는 것을 막기 위한 광역 가드.

SC2 런타임이 없어도 ast.parse만 수행하므로 환경에 종속되지 않는다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PKG_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"

# 일부 자동 생성 / 외부 의존 영역은 명시적으로 제외 가능
EXCLUDED_PREFIXES: tuple[str, ...] = ()


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for p in PKG_ROOT.rglob("*.py"):
        rel = p.relative_to(PKG_ROOT).as_posix()
        if any(rel.startswith(pref) for pref in EXCLUDED_PREFIXES):
            continue
        files.append(p)
    return files


@pytest.mark.parametrize(
    "source_path",
    [pytest.param(p, id=p.relative_to(PKG_ROOT).as_posix()) for p in _iter_python_files()],
)
def test_module_parses_cleanly(source_path: Path) -> None:
    """각 모듈이 SyntaxError 없이 AST 파싱되어야 한다."""
    src = source_path.read_text(encoding="utf-8")
    try:
        ast.parse(src, filename=str(source_path))
    except SyntaxError as exc:
        pytest.fail(
            f"{source_path.relative_to(PROJECT_ROOT)} parse failed at "
            f"line {exc.lineno}, col {exc.offset}: {exc.msg}"
        )
