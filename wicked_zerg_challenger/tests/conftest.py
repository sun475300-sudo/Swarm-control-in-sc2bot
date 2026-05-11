# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _install_sc2_stub() -> None:
    """Install a minimal sc2 stub so test modules can be imported without the
    real `burnysc2` package. Tests mock the actual behaviour, so we only need
    importable symbols.
    """
    try:  # pragma: no cover — real lib available
        import sc2  # type: ignore  # noqa: F401

        return
    except ImportError:
        pass

    class _IdMember:
        """Hashable, comparable stand-in for sc2 enum members."""

        __slots__ = ("name", "value")

        def __init__(self, name: str):
            self.name = name
            self.value = hash(name) & 0x7FFFFFFF

        def __repr__(self):
            return f"<_IdMember {self.name}>"

        def __hash__(self):
            return hash(("_IdMember", self.name))

        def __eq__(self, other):
            return isinstance(other, _IdMember) and self.name == other.name

        def __ne__(self, other):
            return not self.__eq__(other)

    class _AutoId:
        """Enum-like that returns a unique hashable sentinel per attribute."""

        def __init__(self):
            self._members: dict = {}

        def __getattr__(self, name):  # type: ignore[override]
            if name.startswith("_"):
                raise AttributeError(name)
            members = self.__dict__.setdefault("_members", {})
            if name not in members:
                members[name] = _IdMember(name)
            return members[name]

        def __iter__(self):
            return iter(self.__dict__.get("_members", {}).values())

        def __contains__(self, item):
            members = self.__dict__.get("_members", {})
            if isinstance(item, _IdMember):
                return item.name in members
            return item in members

    def _make_module(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        sys.modules[name] = mod
        return mod

    class _Point2(tuple):
        def __new__(cls, xy=(0, 0)):
            return tuple.__new__(cls, (float(xy[0]), float(xy[1])))

        @property
        def x(self):
            return self[0]

        @property
        def y(self):
            return self[1]

        def distance_to(self, other):
            ox = getattr(other, "x", other[0] if hasattr(other, "__getitem__") else 0)
            oy = getattr(other, "y", other[1] if hasattr(other, "__getitem__") else 0)
            return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5

    class _Unit:  # minimal placeholder
        pass

    class _Units(list):
        def __init__(self, iterable=(), bot_object=None):  # type: ignore[override]
            super().__init__(iterable)
            self._bot_object = bot_object

        @property
        def ready(self):
            return self

        @property
        def amount(self):
            return len(self)

    class _BotAI:
        pass

    class _NamedMeta(type):
        """Metaclass that lazily produces hashable members and supports
        ``isinstance`` checks against instances of the class itself."""

        def __getattr__(cls, name):
            cache = cls.__dict__.get("_cache")
            if cache is None:
                cache = {}
                setattr(cls, "_cache", cache)
            if name not in cache:
                cache[name] = cls(name)
            return cache[name]

        def __getitem__(cls, name):
            return getattr(cls, name)

        def __iter__(cls):
            return iter(cls.__dict__.get("_cache", {}).values())

    class _NamedBase(metaclass=_NamedMeta):
        __slots__ = ("name",)

        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<{type(self).__name__} {self.name}>"

        def __hash__(self):
            return hash((type(self).__name__, self.name))

        def __eq__(self, other):
            return type(other) is type(self) and self.name == other.name

    class _Race(_NamedBase):
        pass

    class _Difficulty(_NamedBase):
        pass

    class _Result:
        Victory = "Victory"
        Defeat = "Defeat"
        Tie = "Tie"
        Undecided = "Undecided"

    class _Bot:
        def __init__(self, race=None, ai=None, name=None):
            self.race = race
            self.ai = ai
            self.name = name

    class _Computer:
        def __init__(self, race=None, difficulty=None, ai_build=None):
            self.race = race
            self.difficulty = difficulty
            self.ai_build = ai_build

    def _run_game(*args, **kwargs):  # pragma: no cover
        raise RuntimeError("sc2 stub: run_game is not callable in tests")

    _make_module("sc2")
    _make_module("sc2.ids")
    _make_module("sc2.ids.unit_typeid", UnitTypeId=_AutoId())
    _make_module("sc2.ids.upgrade_id", UpgradeId=_AutoId())
    _make_module("sc2.ids.ability_id", AbilityId=_AutoId())
    _make_module("sc2.ids.buff_id", BuffId=_AutoId())
    _make_module("sc2.ids.effect_id", EffectId=_AutoId())
    _make_module("sc2.position", Point2=_Point2, Point3=_Point2)
    _make_module("sc2.unit", Unit=_Unit)
    _make_module("sc2.units", Units=_Units)
    _make_module("sc2.bot_ai", BotAI=_BotAI)
    _make_module(
        "sc2.data",
        Race=_Race,
        Difficulty=_Difficulty,
        Result=_Result,
        Alliance=_AutoId(),
        Attribute=_AutoId(),
        race_townhalls={},
        race_worker={},
    )
    _make_module("sc2.player", Bot=_Bot, Computer=_Computer, Human=_Bot)
    _make_module("sc2.main", run_game=_run_game)
    _make_module("sc2.maps", get=lambda name: name)
    _make_module("sc2.game_state")
    _make_module("sc2.game_info")
    _make_module("sc2.constants")
    _make_module("sc2.dicts")
    _make_module("sc2.dicts.unit_trained_from")
    _make_module("sc2.dicts.unit_research_abilities")


_install_sc2_stub()
