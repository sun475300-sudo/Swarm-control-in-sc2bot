"""
공용 sc2 stub — 테스트 환경에서 burnysc2 미설치 시 ``sys.modules`` 에 주입한다.

테스트 컬렉션이 다음 두 패턴에서 모두 통과해야 한다.

1. ``from sc2.ids.unit_typeid import UnitTypeId`` 같은 직접 임포트
2. ``unit_type: UnitTypeId = UnitTypeId.OVERLORD`` 같은 임포트 타임 속성 접근

이 스텁은 게임 로직을 시뮬레이트하지 않는다. 단지 임포트 그래프가 안전하게
탐색될 수 있도록 ``UnitTypeId.<ANY>`` 가 항상 sentinel 값을 돌려주게 한다.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


class _IdLike:
    """Enum 흉내 — ``UnitTypeId.OVERLORD`` 같은 어떤 속성도 동일한 sentinel.

    실제 sc2 의 enum 값은 ``.name`` / ``.value`` 속성을 노출하므로 동등하게 지원한다.
    """

    _instances: dict[tuple[str, str], "_IdLike"] = {}

    def __new__(cls, namespace: str, name: str) -> "_IdLike":
        key = (namespace, name)
        if key not in cls._instances:
            obj = object.__new__(cls)
            obj._namespace = namespace
            obj._name = name
            cls._instances[key] = obj
        return cls._instances[key]

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"<{self._namespace}.{self._name}>"

    def __str__(self) -> str:
        return f"{self._namespace}.{self._name}"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _IdLike) and (self._namespace, self._name) == (
            other._namespace,
            other._name,
        )

    def __hash__(self) -> int:
        return hash((self._namespace, self._name))


class _IdCatalog(type):
    """``__getattr__`` 로 모든 속성에 sentinel 을 돌려주는 metaclass.

    또한 ``Race["Zerg"]`` 같은 indexed access (실제 Enum API) 도 지원한다.
    """

    def __getattr__(cls, name: str) -> _IdLike:  # noqa: D401
        if name.startswith("__"):
            raise AttributeError(name)
        return _IdLike(cls.__name__, name)

    def __getitem__(cls, name: str) -> _IdLike:  # ``Race["Zerg"]``
        return _IdLike(cls.__name__, name)

    def __iter__(cls):  # 일부 코드가 list(UnitTypeId) 를 호출
        return iter(())

    def __instancecheck__(cls, obj) -> bool:
        # 실제 sc2.Enum 처럼 ``isinstance(Race.Terran, Race)`` 가 True 가 되도록.
        return isinstance(obj, _IdLike) and obj._namespace == cls.__name__


class UnitTypeId(metaclass=_IdCatalog):
    pass


class UpgradeId(metaclass=_IdCatalog):
    pass


class AbilityId(metaclass=_IdCatalog):
    pass


class BuffId(metaclass=_IdCatalog):
    pass


class EffectId(metaclass=_IdCatalog):
    pass


class Race(metaclass=_IdCatalog):
    Zerg = _IdLike("Race", "Zerg")
    Terran = _IdLike("Race", "Terran")
    Protoss = _IdLike("Race", "Protoss")
    Random = _IdLike("Race", "Random")
    NoRace = _IdLike("Race", "NoRace")


class Difficulty(metaclass=_IdCatalog):
    VeryEasy = _IdLike("Difficulty", "VeryEasy")
    Easy = _IdLike("Difficulty", "Easy")
    Medium = _IdLike("Difficulty", "Medium")
    MediumHard = _IdLike("Difficulty", "MediumHard")
    Hard = _IdLike("Difficulty", "Hard")
    Harder = _IdLike("Difficulty", "Harder")
    VeryHard = _IdLike("Difficulty", "VeryHard")
    CheatVision = _IdLike("Difficulty", "CheatVision")
    CheatMoney = _IdLike("Difficulty", "CheatMoney")
    CheatInsane = _IdLike("Difficulty", "CheatInsane")


class Point2:
    __slots__ = ("x", "y")

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], (tuple, list)):
            self.x, self.y = float(args[0][0]), float(args[0][1])
        elif len(args) >= 2:
            self.x, self.y = float(args[0]), float(args[1])
        else:
            self.x = float(kwargs.get("x", 0.0))
            self.y = float(kwargs.get("y", 0.0))

    def distance_to(self, other) -> float:
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None and hasattr(other, "position"):
            ox = other.position.x
            oy = other.position.y
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    def towards(self, other, distance: float) -> "Point2":
        dx = getattr(other, "x", other[0] if hasattr(other, "__getitem__") else 0) - self.x
        dy = getattr(other, "y", other[1] if hasattr(other, "__getitem__") else 0) - self.y
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        return Point2(self.x + dx / length * distance, self.y + dy / length * distance)

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, idx):
        return (self.x, self.y)[idx]

    def __eq__(self, other):
        return getattr(other, "x", None) == self.x and getattr(other, "y", None) == self.y

    def __hash__(self):
        return hash((self.x, self.y))


class Point3(Point2):
    __slots__ = ("z",)

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], (tuple, list)) and len(args[0]) >= 3:
            super().__init__(args[0][0], args[0][1])
            self.z = float(args[0][2])
        elif len(args) >= 3:
            super().__init__(args[0], args[1])
            self.z = float(args[2])
        else:
            super().__init__(*args, **kwargs)
            self.z = float(kwargs.get("z", 0.0))


class Unit:
    """런타임 어트리뷰트 접근을 허용하는 매우 느슨한 스텁."""

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class Units(list):
    """``sc2.units.Units`` 흉내."""

    def __init__(self, iterable=(), bot_object=None):
        super().__init__(iterable)
        self.bot_object = bot_object

    def __call__(self, *args, **kwargs):  # ``bot.units(...)`` 패턴 호환
        return Units(self)

    def of_type(self, *_args, **_kwargs):
        return Units(self)

    def filter(self, fn):
        return Units([u for u in self if fn(u)])

    def closer_than(self, *_args, **_kwargs):
        return Units(self)

    def further_than(self, *_args, **_kwargs):
        return Units(self)

    def tags_in(self, *_args, **_kwargs):
        return Units(self)

    @property
    def ready(self):
        return Units(self)

    @property
    def not_ready(self):
        return Units(())

    @property
    def idle(self):
        return Units(self)

    @property
    def amount(self):
        return len(self)


class BotAI:
    """``BotAI`` 자리 표시자."""

    def __init__(self, *args, **kwargs):
        pass


class Bot:
    def __init__(self, *args, **kwargs):
        self.race = kwargs.get("race")
        self.ai = kwargs.get("ai")


class Computer:
    def __init__(self, *args, **kwargs):
        self.race = kwargs.get("race")
        self.difficulty = kwargs.get("difficulty")


def run_game(*_args, **_kwargs):  # placeholder
    return None


def maps_get(*_args, **_kwargs):  # placeholder
    return None


def install_sc2_stub() -> None:
    """``sys.modules`` 에 sc2 트리를 주입한다 (이미 설치된 경우 no-op)."""

    if "sc2" in sys.modules and getattr(sys.modules["sc2"], "__real__", True):
        # 진짜 sc2 가 이미 로드되어 있으면 건드리지 않는다.
        try:
            import sc2  # type: ignore  # noqa: F401

            return
        except Exception:
            pass

    # 루트 패키지
    sc2_pkg = types.ModuleType("sc2")
    sc2_pkg.__path__ = []  # type: ignore[attr-defined]
    sc2_pkg.__real__ = False  # type: ignore[attr-defined]
    sys.modules["sc2"] = sc2_pkg

    # sc2.bot_ai
    bot_ai_mod = types.ModuleType("sc2.bot_ai")
    bot_ai_mod.BotAI = BotAI
    sys.modules["sc2.bot_ai"] = bot_ai_mod
    sc2_pkg.bot_ai = bot_ai_mod  # type: ignore[attr-defined]

    # sc2.ids 패키지
    ids_pkg = types.ModuleType("sc2.ids")
    ids_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["sc2.ids"] = ids_pkg
    sc2_pkg.ids = ids_pkg  # type: ignore[attr-defined]

    for sub, cls in (
        ("unit_typeid", UnitTypeId),
        ("upgrade_id", UpgradeId),
        ("ability_id", AbilityId),
        ("buff_id", BuffId),
        ("effect_id", EffectId),
    ):
        mod = types.ModuleType(f"sc2.ids.{sub}")
        # 멤버를 클래스명 + 패스칼/스네이크 두 가지로 노출
        setattr(mod, cls.__name__, cls)
        sys.modules[f"sc2.ids.{sub}"] = mod
        setattr(ids_pkg, sub, mod)

    # sc2.position
    pos_mod = types.ModuleType("sc2.position")
    pos_mod.Point2 = Point2
    pos_mod.Point3 = Point3
    sys.modules["sc2.position"] = pos_mod
    sc2_pkg.position = pos_mod  # type: ignore[attr-defined]

    # sc2.unit / sc2.units
    unit_mod = types.ModuleType("sc2.unit")
    unit_mod.Unit = Unit
    sys.modules["sc2.unit"] = unit_mod
    sc2_pkg.unit = unit_mod  # type: ignore[attr-defined]

    units_mod = types.ModuleType("sc2.units")
    units_mod.Units = Units
    sys.modules["sc2.units"] = units_mod
    sc2_pkg.units = units_mod  # type: ignore[attr-defined]

    # sc2.player
    player_mod = types.ModuleType("sc2.player")
    player_mod.Bot = Bot
    player_mod.Computer = Computer
    player_mod.Human = MagicMock
    player_mod.Observer = MagicMock
    sys.modules["sc2.player"] = player_mod
    sc2_pkg.player = player_mod  # type: ignore[attr-defined]

    # sc2.data
    data_mod = types.ModuleType("sc2.data")
    data_mod.Race = Race
    data_mod.Difficulty = Difficulty
    data_mod.Result = type("Result", (), {"Victory": "Victory", "Defeat": "Defeat", "Tie": "Tie"})
    data_mod.AIBuild = type("AIBuild", (), {"RandomBuild": "RandomBuild"})
    sys.modules["sc2.data"] = data_mod
    sc2_pkg.data = data_mod  # type: ignore[attr-defined]

    # sc2.race
    race_mod = types.ModuleType("sc2.race")
    race_mod.Race = Race
    sys.modules["sc2.race"] = race_mod
    sc2_pkg.race = race_mod  # type: ignore[attr-defined]

    # sc2.difficulty
    diff_mod = types.ModuleType("sc2.difficulty")
    diff_mod.Difficulty = Difficulty
    sys.modules["sc2.difficulty"] = diff_mod
    sc2_pkg.difficulty = diff_mod  # type: ignore[attr-defined]

    # sc2.main / sc2.maps / sc2.game
    main_mod = types.ModuleType("sc2.main")
    main_mod.run_game = run_game
    sys.modules["sc2.main"] = main_mod
    sc2_pkg.main = main_mod  # type: ignore[attr-defined]

    maps_mod = types.ModuleType("sc2.maps")
    maps_mod.get = maps_get
    sys.modules["sc2.maps"] = maps_mod
    sc2_pkg.maps = maps_mod  # type: ignore[attr-defined]

    game_mod = types.ModuleType("sc2.game")
    sys.modules["sc2.game"] = game_mod
    sc2_pkg.game = game_mod  # type: ignore[attr-defined]

    # sc2.game_info, sc2.game_state, sc2.game_data — 다양한 봇 코드 임포트 대응
    for sub in ("game_info", "game_state", "game_data", "constants", "pixel_map"):
        m = types.ModuleType(f"sc2.{sub}")
        sys.modules[f"sc2.{sub}"] = m
        setattr(sc2_pkg, sub, m)


__all__ = [
    "install_sc2_stub",
    "UnitTypeId",
    "UpgradeId",
    "AbilityId",
    "BuffId",
    "EffectId",
    "Point2",
    "Point3",
    "Race",
    "Difficulty",
    "Unit",
    "Units",
    "BotAI",
    "Bot",
    "Computer",
]
