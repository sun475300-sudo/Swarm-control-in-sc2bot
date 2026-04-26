"""
sc2 호환 스텁 (Test/Lint 환경용)

burnysc2가 설치되지 않은 환경 (CI 단위 테스트, 정적 분석 등)에서
`from sc2.ids.unit_typeid import UnitTypeId` 같은 임포트가 실패하면
모듈 전체 로드가 무너진다. 기존 코드는 each module에서

    try:
        from sc2.ids.unit_typeid import UnitTypeId
    except ImportError:
        class UnitTypeId:
            pass

같은 빈 스텁을 둔다. 그러나 빈 스텁은 `UnitTypeId.OVERLORD`를 함수의
기본 인자로 쓰는 즉시 `AttributeError: type object 'UnitTypeId' has no
attribute 'OVERLORD'`로 모듈 import가 실패한다 (예: P0-4).

본 모듈은 메타클래스 기반의 *Auto-Stub*을 제공한다:
- 미정의 attribute에 접근하면 같은 이름의 sentinel 인스턴스를 lazy로 생성·캐시.
- 동일성/해시가 안정적이라 dict key·set 멤버로도 안전.
- `==` 비교, `is` 비교, `bool()` 모두 안전한 기본 동작.

이 스텁은 *오로지* 임포트 안전을 보장할 뿐, 실제 게임 로직을 시뮬레이션하지
않는다. 진짜 sc2가 설치되어 있으면 본 모듈은 진짜 클래스를 그대로 재노출한다.
"""

from __future__ import annotations

__all__ = [
    "SC2_AVAILABLE",
    "BotAI",
    "UnitTypeId",
    "AbilityId",
    "UpgradeId",
    "Race",
    "Difficulty",
    "Result",
    "Bot",
    "Computer",
    "Point2",
    "Unit",
    "Units",
    "maps",
    "run_game",
]

try:
    from sc2 import maps as _real_maps  # type: ignore
    from sc2.bot_ai import BotAI as _RealBotAI  # type: ignore
    from sc2.ids.unit_typeid import UnitTypeId as _RealUnitTypeId  # type: ignore
    from sc2.ids.ability_id import AbilityId as _RealAbilityId  # type: ignore
    from sc2.ids.upgrade_id import UpgradeId as _RealUpgradeId  # type: ignore
    from sc2.data import Race as _RealRace  # type: ignore
    from sc2.data import Difficulty as _RealDifficulty  # type: ignore
    from sc2.data import Result as _RealResult  # type: ignore
    from sc2.player import Bot as _RealBot  # type: ignore
    from sc2.player import Computer as _RealComputer  # type: ignore
    from sc2.position import Point2 as _RealPoint2  # type: ignore
    from sc2.unit import Unit as _RealUnit  # type: ignore
    from sc2.units import Units as _RealUnits  # type: ignore
    from sc2.main import run_game as _real_run_game  # type: ignore

    SC2_AVAILABLE = True
    BotAI = _RealBotAI
    UnitTypeId = _RealUnitTypeId
    AbilityId = _RealAbilityId
    UpgradeId = _RealUpgradeId
    Race = _RealRace
    Difficulty = _RealDifficulty
    Result = _RealResult
    Bot = _RealBot
    Computer = _RealComputer
    Point2 = _RealPoint2
    Unit = _RealUnit
    Units = _RealUnits
    maps = _real_maps
    run_game = _real_run_game
except Exception:  # ImportError 또는 transitive 실패
    SC2_AVAILABLE = False

    class _StubMeta(type):
        """미정의 attribute 접근과 subscript를 sentinel로 lazy 채움.

        burnysc2의 Race/Difficulty 같은 Enum은 ``Race.Zerg`` 와 ``Race["Zerg"]``
        둘 다 동일 멤버를 반환한다. 우리 스텁도 같은 의미를 가지도록
        ``__getattr__`` 과 ``__getitem__`` 양쪽을 채운다.
        """

        _stub_cache: dict

        def _ensure_cache(cls) -> dict:
            cache = cls.__dict__.get("_stub_cache")
            if cache is None:
                cache = {}
                type.__setattr__(cls, "_stub_cache", cache)
            return cache

        def _get_member(cls, name: str):
            cache = cls._ensure_cache()
            cached = cache.get(name)
            if cached is not None:
                return cached
            sentinel = cls(name)  # type: ignore[call-arg]
            cache[name] = sentinel
            return sentinel

        def __getattr__(cls, name):  # noqa: D401 - dunder
            if name.startswith("__"):
                raise AttributeError(name)
            return cls._get_member(name)

        def __getitem__(cls, name):  # noqa: D401 - dunder
            if not isinstance(name, str):
                raise KeyError(name)
            return cls._get_member(name)

    class _StubEnumLike(metaclass=_StubMeta):
        """UnitTypeId/AbilityId/UpgradeId/Race용 sentinel."""

        def __init__(self, name: str = "<stub>"):
            self.name = name
            self.value = -1

        def __repr__(self) -> str:
            return f"<{type(self).__name__}.{self.name} (stub)>"

        def __eq__(self, other) -> bool:
            return isinstance(other, type(self)) and other.name == self.name

        def __hash__(self) -> int:
            return hash((type(self).__name__, self.name))

        # Production code uses patterns like `next_diff if next_diff else fallback`
        # to test "did we find a next item?". Sentinel members must therefore be
        # truthy — they represent existing values, not absence-of-value.
        def __bool__(self) -> bool:
            return True

    class UnitTypeId(_StubEnumLike):  # type: ignore[no-redef]
        pass

    class AbilityId(_StubEnumLike):  # type: ignore[no-redef]
        pass

    class UpgradeId(_StubEnumLike):  # type: ignore[no-redef]
        pass

    class Race(_StubEnumLike):  # type: ignore[no-redef]
        pass

    class Difficulty(_StubEnumLike):  # type: ignore[no-redef]
        pass

    class Result(_StubEnumLike):  # type: ignore[no-redef]
        pass

    class Bot:  # type: ignore[no-redef]
        """sc2.player.Bot 최소 스텁."""

        def __init__(self, race=None, ai=None, name=None):
            self.race = race
            self.ai = ai
            self.name = name

    class Computer:  # type: ignore[no-redef]
        """sc2.player.Computer 최소 스텁."""

        def __init__(self, race=None, difficulty=None, ai_build=None):
            self.race = race
            self.difficulty = difficulty
            self.ai_build = ai_build

    def run_game(*_args, **_kwargs):  # type: ignore[no-redef]
        """sc2.main.run_game 스텁 — 테스트 환경에서 호출되면 NotImplemented."""
        raise NotImplementedError("sc2.main.run_game stub: install burnysc2 to run.")

    class _MapsStub:
        """sc2.maps 모듈 스텁 — get/Map 메서드만 흉내."""

        def get(self, name):  # noqa: D401
            return name

    maps = _MapsStub()  # type: ignore[no-redef]

    class BotAI:  # type: ignore[no-redef]
        """sc2.bot_ai.BotAI 최소 스텁."""

    class Point2(tuple):  # type: ignore[no-redef]
        """sc2.position.Point2 최소 스텁 (tuple 기반)."""

        def __new__(cls, xy=(0.0, 0.0)):
            return super().__new__(cls, tuple(xy))

        @property
        def x(self):
            return self[0]

        @property
        def y(self):
            return self[1]

        def distance_to(self, other) -> float:
            ox = getattr(other, "x", other[0] if hasattr(other, "__getitem__") else 0)
            oy = getattr(other, "y", other[1] if hasattr(other, "__getitem__") else 0)
            return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5

        def distance_to_point2(self, other) -> float:
            return self.distance_to(other)

        def offset(self, other) -> "Point2":
            return Point2((self[0] + other[0], self[1] + other[1]))

    class Unit:  # type: ignore[no-redef]
        """sc2.unit.Unit 최소 스텁."""

    class Units(list):  # type: ignore[no-redef]
        """sc2.units.Units 최소 스텁 (list 기반).

        burnysc2의 Units는 ``Units(iterable, bot_object)`` 시그니처를 가진다.
        list 기본 생성자는 1-arg만 받으므로 명시적으로 2-arg를 받아 둔다.
        """

        def __init__(self, iterable=(), bot_object=None):
            super().__init__(iterable)
            self._bot = bot_object

        def filter(self, pred):
            return Units([u for u in self if pred(u)], self._bot)

        @property
        def amount(self) -> int:
            return len(self)

        @property
        def exists(self) -> bool:
            return bool(self)
