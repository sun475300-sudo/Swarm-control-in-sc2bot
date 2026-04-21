# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

sc2(burnysc2) 라이브러리가 설치되지 않은 환경(예: CI 기본 파이썬)에서
테스트가 수집 단계에서 ModuleNotFoundError로 실패하는 문제를 방지한다.

실제 sc2 임포트가 성공하면 그대로 사용하고, 실패 시에만 최소한의 스텁을
sys.modules에 등록해 테스트 코드가 `from sc2... import ...` 문으로
UnitTypeId, Point2 등을 불러올 수 있게 한다.
"""
import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _install_sc2_stubs() -> None:
    """sc2가 없을 때만 최소 스텁을 sys.modules에 등록."""
    try:
        import sc2  # noqa: F401
        return  # real library present → nothing to do
    except ImportError:
        pass

    from enum import Enum

    class _DynamicIdMeta(type):
        """모든 속성 접근에 대해 동일 이름의 스텁 인스턴스를 캐시-반환."""

        _cache = {}

        def __getattr__(cls, name):
            if name.startswith("_"):
                raise AttributeError(name)
            key = (cls.__name__, name)
            if key not in _DynamicIdMeta._cache:
                instance = cls.__new__(cls)
                instance._name = name
                _DynamicIdMeta._cache[key] = instance
            return _DynamicIdMeta._cache[key]

    class _DynamicIdBase(metaclass=_DynamicIdMeta):
        """sc2의 UnitTypeId/AbilityId/UpgradeId/BuffId 폴백.

        어떤 이름을 요구해도 해시 가능한 싱글턴 스텁을 반환하므로
        테스트 시 값 비교/집합 멤버십 체크가 모두 동작한다.
        """

        def __init__(self, name: str = "UNKNOWN"):
            self._name = name

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._name

        def __repr__(self):
            return f"{type(self).__name__}.{self._name}"

        def __str__(self):
            return self._name

        def __eq__(self, other):
            if isinstance(other, _DynamicIdBase):
                return type(self) is type(other) and self._name == other._name
            if isinstance(other, str):
                return self._name == other
            return NotImplemented

        def __hash__(self):
            return hash((type(self).__name__, self._name))

    class _UnitTypeIdStub(_DynamicIdBase):
        pass

    class _AbilityIdStub(_DynamicIdBase):
        pass

    class _UpgradeIdStub(_DynamicIdBase):
        pass

    class _BuffIdStub(_DynamicIdBase):
        pass

    class _DifficultyStub(Enum):
        VeryEasy = 1
        Easy = 2
        Medium = 3
        MediumHard = 4
        Hard = 5
        Harder = 6
        VeryHard = 7
        CheatVision = 8
        CheatMoney = 9
        CheatInsane = 10

    class _RaceStub(Enum):
        Zerg = 1
        Protoss = 2
        Terran = 3
        Random = 4

    class _Point2Stub(tuple):
        def __new__(cls, value=(0.0, 0.0)):
            if isinstance(value, (tuple, list)) and len(value) >= 2:
                x, y = value[0], value[1]
            else:
                x, y = 0.0, 0.0
            obj = super().__new__(cls, (x, y))
            return obj

        @property
        def x(self):
            return self[0]

        @property
        def y(self):
            return self[1]

        def distance_to(self, other):
            ox, oy = other[0], other[1]
            return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5

    class _BotAIStub:
        pass

    class _UnitStub:
        pass

    class _UnitsStub(list):
        def __init__(self, units=None, bot_object=None):
            super().__init__(units or [])

        def closer_than(self, distance, point):
            return _UnitsStub([u for u in self if hasattr(u, "distance_to") and u.distance_to(point) < distance])

        def filter(self, func):
            return _UnitsStub([u for u in self if func(u)])

        @property
        def amount(self):
            return len(self)

    def _register(name: str, **attrs) -> types.ModuleType:
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module
        return module

    _register("sc2")
    _register("sc2.ids")
    _register("sc2.ids.unit_typeid", UnitTypeId=_UnitTypeIdStub)
    _register("sc2.ids.ability_id", AbilityId=_AbilityIdStub)
    _register("sc2.ids.upgrade_id", UpgradeId=_UpgradeIdStub)
    _register("sc2.ids.buff_id", BuffId=_BuffIdStub)
    _register("sc2.data", Difficulty=_DifficultyStub, Race=_RaceStub)
    _register("sc2.position", Point2=_Point2Stub, Point3=_Point2Stub)
    _register("sc2.bot_ai", BotAI=_BotAIStub)
    _register("sc2.unit", Unit=_UnitStub)
    _register("sc2.units", Units=_UnitsStub)


_install_sc2_stubs()
