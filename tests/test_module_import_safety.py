# -*- coding: utf-8 -*-
"""
모듈 import 안전성 회귀 테스트.

`sc2` 라이브러리(Burnysc2)가 설치돼 있지 않은 환경에서도, ImportError fallback 을
선언한 봇 코어 모듈이 module-level / class-level 에서 폭주하지 않도록 보장한다.

배경:
    `wicked_zerg_challenger/scouting/advanced_scout_system_v2.py` 에서
    함수 시그니처 default 값이 `UnitTypeId.OVERLORD` 로 선언돼 있어,
    sc2 미설치 시 fallback `class UnitTypeId: pass` 를 사용했을 때 클래스 정의
    자체가 `AttributeError: type object 'UnitTypeId' has no attribute 'OVERLORD'`
    로 실패했다. 이 테스트는 동일 회귀를 잡는다.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

WICKED_DIR = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


@pytest.fixture(autouse=True)
def _ensure_wicked_on_syspath():
    p = str(WICKED_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)
    yield


@pytest.mark.skipif(
    importlib.util.find_spec("sc2") is not None,
    reason="sc2 가 설치된 환경에서는 fallback 경로를 검증할 수 없음",
)
def test_advanced_scout_system_v2_imports_without_sc2():
    """sc2 미설치 환경에서도 모듈 import 가 성공해야 한다."""
    # 캐시 제거 후 재 import
    for mod in list(sys.modules):
        if mod.startswith("scouting") or mod == "scouting":
            sys.modules.pop(mod, None)

    mod = importlib.import_module("scouting.advanced_scout_system_v2")
    assert hasattr(mod, "AdvancedScoutingSystemV2")
    cls = mod.AdvancedScoutingSystemV2
    # 시그니처 default 가 None 으로 lazily 처리되는지 검증
    import inspect

    sig = inspect.signature(cls._assign_patrol)
    assert sig.parameters["unit_type"].default is None


def test_check_proxy_import_does_not_exit():
    """check_proxy 는 윈도우 전용 경로 검사 스크립트지만, 단순 import 만으로
    sys.exit() 를 호출해선 안 된다 (다른 환경에서 모듈 스캔/로딩 시 크래시 방지)."""
    sys.modules.pop("check_proxy", None)
    mod = importlib.import_module("check_proxy")
    assert hasattr(mod, "check_proxy"), "check_proxy() 함수가 export 되어야 함"
    # 함수가 호출 가능하고 부재 시 비-zero 를 반환하는지만 검증 (sys.exit 금지)
    rc = mod.check_proxy(proxy_path="/nonexistent/path/cli-proxy-api.exe")
    assert rc != 0
