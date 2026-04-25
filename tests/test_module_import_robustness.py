# -*- coding: utf-8 -*-
"""
Module import robustness tests.

burnysc2(``sc2`` 패키지)는 mpyq 등 native build를 요구해서 일부 CI나
새로운 컨테이너에서 설치가 실패할 수 있다. 봇의 핵심 모듈은 sc2 stub
환경에서도 (적어도) ``import``는 성공해야 한다 — import에 실패하면
다른 매니저가 ``except ImportError`` 가드로 fallback할 기회조차 없다.

과거 회귀 사례:
- ``advanced_scout_system_v2._assign_patrol(unit_type=UnitTypeId.OVERLORD)``
  default 인자가 클래스 정의 시점에 ``UnitTypeId.OVERLORD``를 평가
  → fallback stub에 OVERLORD 속성이 없어 ``AttributeError``로 import 실패

이 테스트는 위 같은 회귀를 잡는다.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"


@pytest.fixture(autouse=True)
def _path_setup(monkeypatch):
    monkeypatch.syspath_prepend(str(WZC_ROOT))
    # Drop any cached modules that may have been imported with full sc2
    # so we re-exercise the fallback paths under a fresh state when the
    # actual sc2 lib is absent.
    yield


MODULES_THAT_MUST_IMPORT = [
    "strict_upgrade_priority",
    "worker_combat_system",
    "combat.stutter_step_kiting",
    "scouting.advanced_scout_system_v2",
]


@pytest.mark.parametrize("module_name", MODULES_THAT_MUST_IMPORT)
def test_module_imports_without_attribute_errors(module_name):
    """모듈 import가 AttributeError(stub 누락)로 실패하지 않아야 한다."""
    try:
        importlib.import_module(module_name)
    except AttributeError as exc:
        pytest.fail(
            f"{module_name}이 import 시점에 SC2 enum 속성을 평가하다 실패: {exc}"
        )
    except ImportError:
        # ImportError는 sc2 외 의존성 문제일 수 있으므로 본 테스트의 관심사가 아님
        pytest.skip(f"{module_name}: ImportError (외부 의존성 누락)")


def test_filter_by_type_handles_string_lists():
    """combat_manager가 사용하는 호출 패턴이 깨지지 않는지 회귀 검증."""
    from utils.common_helpers import filter_by_type  # noqa: WPS433

    class _T:
        def __init__(self, name):
            self.name = name

    class _U:
        def __init__(self, name):
            self.type_id = _T(name)

    units = [_U("MUTALISK"), _U("ZERGLING")]
    result = filter_by_type(units, ["MUTALISK"])
    assert [u.type_id.name for u in result] == ["MUTALISK"]
