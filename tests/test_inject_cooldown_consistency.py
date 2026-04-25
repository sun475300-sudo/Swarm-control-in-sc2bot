# -*- coding: utf-8 -*-
"""
Inject 쿨다운 단일 진실 공급원 회귀 테스트.

Spawn Larva 쿨다운 값(29초 = 28.57초 + 0.43초 버퍼)이 여러 곳에서
하드코딩되면 한 곳을 고쳐도 다른 매니저가 옛 값을 그대로 사용하는
치명적 버그가 생길 수 있다. 이 테스트는 모든 매니저가
``UpgradeConstants.INJECT_COOLDOWN_WITH_BUFFER`` 단일 출처를 따르는지
확인한다.

주의: 프로젝트 루트에도 ``utils/`` 디렉터리가 존재하므로
``wicked_zerg_challenger/utils``는 importlib로 직접 로드한다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"


def _load(module_relpath: str, alias: str):
    """Load a module from wicked_zerg_challenger by relative file path."""
    file_path = WZC_ROOT / module_relpath
    spec = importlib.util.spec_from_file_location(alias, file_path)
    if spec is None or spec.loader is None:
        pytest.skip(f"Cannot load {module_relpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def upgrade_constants():
    module = _load("utils/game_constants.py", "_wzc_game_constants")
    return module.UpgradeConstants


def test_upgrade_constants_defines_buffered_cooldown(upgrade_constants):
    assert upgrade_constants.INJECT_COOLDOWN == pytest.approx(28.57, rel=1e-3)
    assert upgrade_constants.INJECT_COOLDOWN_WITH_BUFFER == 29.0
    assert upgrade_constants.INJECT_COOLDOWN_WITH_BUFFER > upgrade_constants.INJECT_COOLDOWN


def test_macro_cycle_class_uses_buffered_value(upgrade_constants):
    """MacroCycleManager.INJECT_COOLDOWN은 import 시점 클래스 attr이므로
    text 비교가 가장 안정적이다."""
    src = (WZC_ROOT / "macro_cycle.py").read_text(encoding="utf-8")
    assert "INJECT_COOLDOWN = _DEFAULT_INJECT_COOLDOWN" in src
    assert "_DEFAULT_INJECT_COOLDOWN = UpgradeConstants.INJECT_COOLDOWN_WITH_BUFFER" in src


def test_queen_inject_optimizer_uses_buffered_value():
    src = (WZC_ROOT / "economy" / "queen_inject_optimizer.py").read_text(encoding="utf-8")
    assert "_DEFAULT_INJECT_COOLDOWN = UpgradeConstants.INJECT_COOLDOWN_WITH_BUFFER" in src
    assert "self.INJECT_COOLDOWN = _DEFAULT_INJECT_COOLDOWN" in src


def test_queen_specialization_uses_buffered_value():
    src = (WZC_ROOT / "economy" / "queen_specialization.py").read_text(encoding="utf-8")
    assert "_DEFAULT_INJECT_COOLDOWN = UpgradeConstants.INJECT_COOLDOWN_WITH_BUFFER" in src
    assert "self.inject_cooldown = _DEFAULT_INJECT_COOLDOWN" in src


def test_queen_manager_uses_buffered_value():
    src = (WZC_ROOT / "queen_manager.py").read_text(encoding="utf-8")
    assert "_DEFAULT_INJECT_COOLDOWN = UpgradeConstants.INJECT_COOLDOWN_WITH_BUFFER" in src
    assert "self.inject_cooldown = _DEFAULT_INJECT_COOLDOWN" in src


def test_no_other_files_hardcode_29_inject_cooldown():
    """29.0 하드코딩이 inject 쿨다운 의도로 다시 들어오는 것을 방지."""
    offending = []
    expected_marker_files = {
        WZC_ROOT / "macro_cycle.py",
        WZC_ROOT / "queen_manager.py",
        WZC_ROOT / "economy" / "queen_inject_optimizer.py",
        WZC_ROOT / "economy" / "queen_specialization.py",
        WZC_ROOT / "utils" / "game_constants.py",
    }
    for path in WZC_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path in expected_marker_files:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if "inject" in stripped.lower() and "29.0" in stripped and "cooldown" in stripped.lower():
                # Comments referencing the value are allowed
                if stripped.startswith("#"):
                    continue
                # Test files / training scripts are noise
                if "test" in path.name.lower() or "trainer" in path.name.lower():
                    continue
                offending.append(f"{path.relative_to(PROJECT_ROOT)}:{n}: {stripped}")

    assert not offending, "Inject 쿨다운 29.0이 하드코딩된 파일:\n" + "\n".join(offending)
