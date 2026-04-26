# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

이 파일이 하는 일:
1. protobuf python 구현 강제 (s2clientprotocol 호환).
2. burnysc2가 설치되지 않은 환경에서, `wicked_zerg_challenger/_sc2_compat.py`의
   스텁 클래스들을 가짜 `sc2`/`sc2.ids.*`/`sc2.position`/`sc2.unit` 모듈로
   sys.modules에 주입한다. 그래야 테스트 파일 상단의

       from sc2.ids.unit_typeid import UnitTypeId

   같은 직접 임포트가 collection 단계에서 폭발하지 않는다.

진짜 sc2가 설치되어 있으면 _sc2_compat이 진짜 클래스를 그대로 노출하므로
이 conftest는 본질적으로 no-op이 된다.
"""
import os
import sys
import types
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# wicked_zerg_challenger를 import path에 추가 (기존 conftest에 없던 부분)
_PKG_ROOT = Path(__file__).resolve().parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))


def _install_sc2_stub_modules() -> None:
    """sc2 미설치 환경에서 가짜 sc2 모듈 트리를 sys.modules에 주입."""
    try:
        import sc2  # noqa: F401
        return  # 진짜 sc2 사용
    except Exception:
        pass

    from _sc2_compat import (  # type: ignore
        BotAI,
        UnitTypeId,
        AbilityId,
        UpgradeId,
        Race,
        Difficulty,
        Result,
        Bot,
        Computer,
        Point2,
        Unit,
        Units,
        maps,
        run_game,
    )

    def _mod(name: str, **attrs) -> types.ModuleType:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    sc2_pkg = _mod("sc2", maps=maps)
    sc2_pkg.__path__ = []  # 패키지로 인식되게

    sc2_ids = _mod("sc2.ids")
    sc2_ids.__path__ = []

    _mod("sc2.bot_ai", BotAI=BotAI)
    _mod("sc2.ids.unit_typeid", UnitTypeId=UnitTypeId)
    _mod("sc2.ids.ability_id", AbilityId=AbilityId)
    _mod("sc2.ids.upgrade_id", UpgradeId=UpgradeId)
    _mod("sc2.data", Race=Race, Difficulty=Difficulty, Result=Result)
    _mod("sc2.player", Bot=Bot, Computer=Computer)
    _mod("sc2.position", Point2=Point2)
    _mod("sc2.unit", Unit=Unit)
    _mod("sc2.units", Units=Units)
    _mod("sc2.main", run_game=run_game)
    _mod("sc2.maps")  # sc2.maps는 함수도 있으므로 별도 처리
    sys.modules["sc2.maps"] = maps if hasattr(maps, "__name__") else types.ModuleType("sc2.maps")
    sys.modules["sc2.maps"].get = maps.get  # type: ignore[attr-defined]


_install_sc2_stub_modules()
