"""
sc2_stubs - sc2 모듈 미설치 환경용 공용 stub

burnysc2(python-sc2)가 설치되지 않은 환경(CI·로컬 유닛테스트 등)에서
`from sc2.xxx import Yyy` 가 실패해도 import-time 오류가 나지 않도록
필요한 식별자를 하나의 자리에서 제공한다.

사용법:
    from utils.sc2_stubs import (
        UnitTypeId, AbilityId, UpgradeId, Race, BotAI,
        Unit, Units, Point2,
    )

- `UnitTypeId`/`AbilityId`/`UpgradeId`/`Race`는 `__getattr__`로
  임의 속성을 문자열로 반환하므로, 코드가 `UnitTypeId.OVERLORD` 등
  어떤 이름을 참조해도 AttributeError가 발생하지 않는다.
- `Units`는 `list` 서브클래스이므로 `Units([], None)` 호출과 `len()` 모두 동작.
- `Point2`는 2-tuple 대체, `Unit`/`BotAI`는 빈 클래스.

실제 sc2 설치 환경에서는 직접 `sc2.*` 를 써야 하며, 본 모듈은 폴백 전용.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional


class _StubMember(str):
    """
    enum 멤버를 흉내내는 stub 값.

    str 서브클래스이므로 문자열 비교/사전 키 등에서 그대로 동작하고,
    동시에 `.name`/`.value` 속성으로 python-sc2 enum 멤버와 호환된다.
    """

    __slots__ = ()

    @property
    def name(self) -> str:
        return str(self)

    @property
    def value(self) -> str:
        return str(self)


class _StringEnumMeta(type):
    """
    임의 속성 접근을 `_StubMember` 값으로 반환하는 metaclass.

    `UnitTypeId.OVERLORD` → `_StubMember("OVERLORD")` 처럼 동작해
    어떤 속성 이름도 AttributeError 없이 처리되며, `.name` 접근도 가능하다.

    동일 이름은 캐싱되어 매번 같은 객체가 반환된다.
    """

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._stub_cache: dict = {}

    def __getattr__(cls, name: str) -> _StubMember:  # type: ignore[override]
        if name.startswith("_"):
            raise AttributeError(name)
        cache = cls.__dict__.get("_stub_cache")
        if cache is None:
            cache = {}
            type.__setattr__(cls, "_stub_cache", cache)
        if name not in cache:
            cache[name] = _StubMember(name)
        return cache[name]

    def __getitem__(cls, name: str) -> _StubMember:
        # Enum-style `Race["Zerg"]` lookup. Fails KeyError on non-str
        # so `isinstance(x, Race)` round-trip code paths are preserved.
        if not isinstance(name, str):
            raise KeyError(name)
        return cls.__getattr__(name)

    def __contains__(cls, item) -> bool:
        return isinstance(item, _StubMember)

    def __iter__(cls):
        cache = cls.__dict__.get("_stub_cache", {})
        return iter(cache.values())


class UnitTypeId(metaclass=_StringEnumMeta):
    """UnitTypeId stub - 모든 속성 접근을 이름 문자열로 반환."""


class AbilityId(metaclass=_StringEnumMeta):
    """AbilityId stub."""


class UpgradeId(metaclass=_StringEnumMeta):
    """UpgradeId stub."""


class BuffId(metaclass=_StringEnumMeta):
    """BuffId stub."""


class EffectId(metaclass=_StringEnumMeta):
    """EffectId stub."""


class Race(metaclass=_StringEnumMeta):
    """Race stub."""


class Difficulty(metaclass=_StringEnumMeta):
    """Difficulty stub."""


class Attribute(metaclass=_StringEnumMeta):
    """Attribute stub."""


class Point2(tuple):
    """2-D 좌표 stub. (x, y) 2-tuple 호환."""

    def __new__(cls, iterable: Iterable[float] = (0.0, 0.0)):
        seq = tuple(iterable) if not isinstance(iterable, tuple) else iterable
        if len(seq) < 2:
            seq = (0.0, 0.0)
        return super().__new__(cls, seq[:2])

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    def distance_to(self, other: "Point2 | tuple") -> float:
        ox, oy = other[0], other[1]
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5


class Point3(Point2):
    """3-D 좌표 stub."""

    def __new__(cls, iterable: Iterable[float] = (0.0, 0.0, 0.0)):
        seq = tuple(iterable) if not isinstance(iterable, tuple) else iterable
        if len(seq) < 3:
            seq = (seq + (0.0, 0.0, 0.0))[:3]
        return tuple.__new__(cls, seq[:3])

    @property
    def z(self) -> float:
        return self[2]


class Unit:
    """Unit stub - 실제 속성은 mock 등이 제공한다고 가정."""


class Units(list):
    """
    Units stub - list 서브클래스.

    `Units([], None)`, `len(units)`, 반복 등이 모두 가능하다.
    bot_object 인자는 무시된다.
    """

    def __init__(self, items: Optional[Iterable[Any]] = None, bot_object: Any = None):
        super().__init__(items or [])
        self._bot_object = bot_object

    def filter(self, predicate):
        return Units([u for u in self if predicate(u)], self._bot_object)

    def closer_than(self, distance: float, position: Any) -> "Units":
        def _dist(u):
            try:
                return u.distance_to(position)
            except Exception:
                return float("inf")
        return Units([u for u in self if _dist(u) < distance], self._bot_object)

    def amount(self) -> int:  # python-sc2 has `units.amount`
        return len(self)


class BotAI:
    """BotAI stub."""


__all__ = [
    "UnitTypeId",
    "AbilityId",
    "UpgradeId",
    "BuffId",
    "EffectId",
    "Race",
    "Difficulty",
    "Attribute",
    "Point2",
    "Point3",
    "Unit",
    "Units",
    "BotAI",
]
