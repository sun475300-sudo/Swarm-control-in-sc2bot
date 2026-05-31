"""
Lightweight SC2 stub modules.

The real `burnysc2` package requires native dependencies (mpyq) that aren't
available in CI/dev sandboxes. Tests that only need the enum identifiers
(UnitTypeId / UpgradeId / AbilityId / Race / Difficulty) can use these stubs
instead of pulling in the full library.

Call `install()` from a conftest before test collection. It registers fake
`sc2`, `sc2.ids.*`, `sc2.data`, `sc2.position`, `sc2.bot_ai`, and `sc2.unit`
modules in `sys.modules` so that `from sc2.ids.unit_typeid import UnitTypeId`
succeeds without the real library.
"""
from __future__ import annotations

import sys
import types


class _EnumMember:
    """Behaves like a real ``Enum`` member: ``.name``, ``.value``, hashable.

    Compares equal to other ``_EnumMember`` instances with the same name and
    to plain strings carrying the same name — that mirrors how real sc2 enums
    behave in most call sites without making ``isinstance(x, str)`` True
    (which would break code branches that test for string upgrade ids).
    """

    __slots__ = ("_name",)

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._name

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name}>"

    def __str__(self):
        return self._name

    def __hash__(self):
        return hash(("_EnumMember", self._name))

    def __eq__(self, other):
        if isinstance(other, _EnumMember):
            return self._name == other._name
        if isinstance(other, str):
            return self._name == other
        return NotImplemented

    def __ne__(self, other):
        eq = self.__eq__(other)
        return eq if eq is NotImplemented else not eq


class _AutoEnumMeta(type):
    """Class-level attribute access returns an ``_EnumMember`` cached per name.

    Lets test code reference `UnitTypeId.ANY_NAME` without enumerating every
    unit. Equality is name-based so tests can compare against string fixtures,
    and ``Cls[name]`` / ``Cls("name")`` lookups also work like real enums.
    """

    def __getattr__(cls, name):  # pragma: no cover - dynamic
        if name.startswith("_"):
            raise AttributeError(name)
        cache = cls.__dict__.get("_members_")
        if cache is None:
            cache = {}
            type.__setattr__(cls, "_members_", cache)
        if name not in cache:
            cache[name] = _EnumMember(name)
        return cache[name]

    def __getitem__(cls, name):
        return getattr(cls, name)

    def __call__(cls, name):
        return getattr(cls, name)

    def __iter__(cls):
        cache = cls.__dict__.get("_members_") or {}
        return iter(cache.values())


class _AutoEnum(metaclass=_AutoEnumMeta):
    pass


class UnitTypeId(_AutoEnum):
    pass


class UpgradeId(_AutoEnum):
    pass


class AbilityId(_AutoEnum):
    pass


class Race(_AutoEnum):
    pass


class Difficulty(_AutoEnum):
    pass


# Pre-populate well-known race/difficulty members so identity comparisons work.
for _name in ("Zerg", "Terran", "Protoss", "Random", "NoRace"):
    getattr(Race, _name)
for _name in ("VeryEasy", "Easy", "Medium", "MediumHard", "Hard", "Harder",
              "VeryHard", "CheatVision", "CheatMoney", "CheatInsane"):
    getattr(Difficulty, _name)


class Units(list):
    """sc2 ``Units`` is constructed as ``Units(iterable, bot_object)``.

    Real implementation stores ``bot_object`` for unit-method dispatch; tests
    don't need that, but we must accept the 2-arg signature.
    """

    def __init__(self, iterable=(), bot_object=None):
        super().__init__(iterable)
        self._bot_object = bot_object

    def __or__(self, other):
        return Units(list(self) + list(other), self._bot_object)

    def filter(self, predicate):
        return Units([u for u in self if predicate(u)], self._bot_object)

    def closer_than(self, distance, target):
        try:
            tx, ty = target.position.x, target.position.y
        except AttributeError:
            tx, ty = target[0], target[1]
        out = []
        for u in self:
            try:
                ux, uy = u.position.x, u.position.y
            except AttributeError:
                ux, uy = u[0], u[1]
            if ((ux - tx) ** 2 + (uy - ty) ** 2) ** 0.5 < distance:
                out.append(u)
        return Units(out, self._bot_object)

    @property
    def amount(self):
        return len(self)

    @property
    def exists(self):
        return len(self) > 0


class Point2(tuple):
    def __new__(cls, xy=(0.0, 0.0)):
        x, y = xy
        return super().__new__(cls, (float(x), float(y)))

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    def distance_to(self, other):
        ox, oy = other[0], other[1]
        return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5


class BotAI:
    pass


class Unit:
    pass


_INSTALLED = False


def install() -> None:
    """Register stub sc2 modules in `sys.modules`. Idempotent."""
    global _INSTALLED
    if _INSTALLED or "sc2" in sys.modules:
        return

    def _mk(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
        return mod

    sc2 = _mk("sc2")
    ids = _mk("sc2.ids")
    sc2.ids = ids
    _mk("sc2.ids.unit_typeid", UnitTypeId=UnitTypeId)
    _mk("sc2.ids.upgrade_id", UpgradeId=UpgradeId)
    _mk("sc2.ids.ability_id", AbilityId=AbilityId)
    _mk("sc2.ids.buff_id", BuffId=_AutoEnum)
    _mk("sc2.ids.effect_id", EffectId=_AutoEnum)
    _mk("sc2.data", Race=Race, Difficulty=Difficulty, Result=_AutoEnum,
        Alliance=_AutoEnum, CloakState=_AutoEnum, DisplayType=_AutoEnum,
        Attribute=_AutoEnum, race_townhalls={}, race_worker={}, race_gas={})
    _mk("sc2.position", Point2=Point2, Point3=Point2)
    _mk("sc2.bot_ai", BotAI=BotAI)
    _mk("sc2.unit", Unit=Unit)
    _mk("sc2.units", Units=Units)
    _mk("sc2.constants", IS_STRUCTURE=set(), TARGET_AIR=set(), TARGET_GROUND=set())

    class _Maps:
        @staticmethod
        def get(name):
            return name

    _mk("sc2.maps", get=_Maps.get)
    sc2.maps = sys.modules["sc2.maps"]
    _mk("sc2.player", Bot=type("Bot", (), {}), Computer=type("Computer", (), {}),
        Human=type("Human", (), {}))
    _mk("sc2.main", run_game=lambda *a, **kw: None,
        _play_game=lambda *a, **kw: None)
    _mk("sc2.client", Client=type("Client", (), {}))
    _mk("sc2.portconfig", Portconfig=type("Portconfig", (), {}))
    _mk("sc2.protocol", ConnectionAlreadyClosed=type("ConnectionAlreadyClosed",
                                                     (Exception,), {}))

    _INSTALLED = True
