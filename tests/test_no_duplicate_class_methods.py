# -*- coding: utf-8 -*-
"""
회귀 테스트: 클래스 내부의 중복(섀도잉) 함수 정의 방지.

라운드 1에서 다음과 같은 중복 정의를 제거했다 (두 번째 정의가 첫 번째를
조용히 덮어쓰며 의도된 로직이 사라지는 사고를 막기 위함):

  * combat_manager.CombatManager._find_harass_target
  * economy_manager.EconomyManager._prevent_resource_banking
  * economy_manager.EconomyManager._reduce_gas_workers
  * local_training/production_resilience.ProductionResilience.build_terran_counters
  * opponent_modeling.OpponentModeling.on_step

이 테스트는 같은 클래스 안에서 동일 이름의 메서드가 두 번 이상 정의되면
실패한다. AST 기반이라 SC2 런타임 의존성 없이 동작한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PKG_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"


def _find_duplicate_methods(source_path: Path) -> list[tuple[str, str, int, int]]:
    """파일 안의 각 클래스에 대해 (class, method, first_line, dup_line)을 반환."""
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
    except SyntaxError:
        # 별도 E9 검사에서 잡힘 — 여기서는 패스
        return []

    duplicates: list[tuple[str, str, int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        seen: dict[str, int] = {}
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name in seen:
                    duplicates.append(
                        (node.name, child.name, seen[child.name], child.lineno)
                    )
                else:
                    seen[child.name] = child.lineno
    return duplicates


# 라운드 1에서 정리한 파일들. 여기에는 새로 추가될 일이 없어야 한다.
GUARDED_FILES = [
    PKG_ROOT / "combat_manager.py",
    PKG_ROOT / "economy_manager.py",
    PKG_ROOT / "opponent_modeling.py",
    PKG_ROOT / "local_training" / "production_resilience.py",
    PKG_ROOT / "game_analytics_system.py",
]


@pytest.mark.parametrize(
    "source_path",
    [pytest.param(p, id=p.name) for p in GUARDED_FILES],
)
def test_no_duplicate_methods_in_guarded_files(source_path: Path) -> None:
    assert source_path.exists(), f"감시 대상 파일이 사라졌다: {source_path}"
    dups = _find_duplicate_methods(source_path)
    assert not dups, (
        f"{source_path.relative_to(PROJECT_ROOT)} 안에서 같은 클래스의 메서드가 "
        f"두 번 이상 정의됐다. 첫 정의가 조용히 덮어써질 수 있다:\n"
        + "\n".join(
            f"  - class {cls}.{method}: line {first} → 재정의 line {dup}"
            for cls, method, first, dup in dups
        )
    )


def test_all_package_files_have_no_class_level_method_dupes() -> None:
    """패키지 전체에 대해서도 같은 검사를 수행 (예방적 광역 가드)."""
    offenders: list[tuple[Path, str, str, int, int]] = []
    for src in PKG_ROOT.rglob("*.py"):
        # 학습용/실험 코드 제외 (의도된 패턴이 있을 수 있음)
        rel = src.relative_to(PKG_ROOT).as_posix()
        if rel.startswith(("tests/", "tools/", "visuals/")):
            continue
        for cls, method, first, dup in _find_duplicate_methods(src):
            offenders.append((src, cls, method, first, dup))

    if offenders:
        details = "\n".join(
            f"  - {p.relative_to(PROJECT_ROOT)}: {cls}.{method} (first {f}, dup {d})"
            for p, cls, method, f, d in offenders
        )
        pytest.fail(
            "패키지에 동일 클래스의 메서드가 두 번 이상 정의된 곳이 있다:\n"
            + details
        )
