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


class _AutoEnumMeta(type):
    """Class-level attribute access returns the name itself.

    Lets test code reference `UnitTypeId.ANY_NAME` without enumerating every
    unit. Equality is name-based so tests can compare against string fixtures.
    """

    def __getattr__(cls, name):  # pragma: no cover - dynamic
        if name.startswith("_"):
            raise AttributeError(name)
        return name


class _AutoEnum(metaclass=_AutoEnumMeta):
    pass


class UnitTypeId(_AutoEnum):
    pass


class UpgradeId(_AutoEnum):
    pass


class AbilityId(_AutoEnum):
    pass


class Race(_AutoEnum):
    Zerg = "Zerg"
    Terran = "Terran"
    Protoss = "Protoss"
    Random = "Random"


class Difficulty(_AutoEnum):
    VeryEasy = "VeryEasy"
    Easy = "Easy"
    Medium = "Medium"
    Hard = "Hard"
    Harder = "Harder"
    VeryHard = "VeryHard"


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
    _mk("sc2.units", Units=list)
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
