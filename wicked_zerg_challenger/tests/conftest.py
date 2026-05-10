# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Provides lightweight stubs for the optional ``sc2`` (burnysc2) and
``numpy`` packages so that unit tests written against pure-python logic
can be collected and executed without the heavy game/ML dependencies
present on the developer machine.

If the real packages are installed they take precedence — the stubs only
register themselves when the real modules cannot be imported.
"""

import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol).
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _install_sc2_stub() -> None:
    """Register a tiny in-memory ``sc2`` package when burnysc2 is missing."""
    try:
        import sc2  # noqa: F401  (real package present — no stub needed)

        return
    except ImportError:
        pass

    sc2_pkg = types.ModuleType("sc2")
    sc2_pkg.__path__ = []  # mark as package so submodule lookup works

    # sc2.position.Point2 — minimal 2-tuple compatible class.
    position_mod = types.ModuleType("sc2.position")

    class Point2(tuple):
        def __new__(cls, iterable=(0.0, 0.0)):
            x, y = iterable
            return super().__new__(cls, (float(x), float(y)))

        @property
        def x(self) -> float:
            return self[0]

        @property
        def y(self) -> float:
            return self[1]

        def distance_to(self, other) -> float:
            ox, oy = other[0], other[1]
            return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    position_mod.Point2 = Point2

    class Point3(tuple):
        def __new__(cls, iterable=(0.0, 0.0, 0.0)):
            return super().__new__(cls, tuple(float(c) for c in iterable))

    position_mod.Point3 = Point3

    # sc2.ids.* enums — stub with auto-incrementing integer members.
    ids_pkg = types.ModuleType("sc2.ids")
    ids_pkg.__path__ = []

    def _make_enum_module(name: str, *, exported_class: str, members):
        mod = types.ModuleType(name)

        class _AutoIntEnum(int):
            def __new__(cls, value, *, member_name=""):
                obj = int.__new__(cls, value)
                obj._name = member_name
                return obj

            @property
            def name(self) -> str:
                return self._name

            @property
            def value(self) -> int:
                return int(self)

            def __repr__(self):
                return f"<{exported_class}.{self._name or int(self)}>"

            def __str__(self):
                return self._name or super().__str__()

        class _AutoEnumProxy:
            def __init__(self):
                self._members: dict = {}
                self._instances: dict = {}
                for i, m in enumerate(members, start=1):
                    self._members[m] = i
                    self._instances[m] = _AutoIntEnum(i, member_name=m)

            def __getattr__(self, item):
                if item.startswith("_"):
                    raise AttributeError(item)
                # Auto-allocate IDs for unknown members so tests can
                # reference any unit/upgrade name without errors.
                if item not in self._members:
                    self._members[item] = len(self._members) + 1
                    self._instances[item] = _AutoIntEnum(
                        self._members[item], member_name=item
                    )
                return self._instances[item]

            def __getitem__(self, item):
                return self.__getattr__(item)

            def __iter__(self):
                return iter(self._instances.values())

        proxy = _AutoEnumProxy()
        setattr(mod, exported_class, proxy)
        return mod

    unit_typeid_mod = _make_enum_module(
        "sc2.ids.unit_typeid",
        exported_class="UnitTypeId",
        members=(
            "DRONE",
            "OVERLORD",
            "ZERGLING",
            "ROACH",
            "QUEEN",
            "HATCHERY",
            "LAIR",
            "HIVE",
            "EXTRACTOR",
            "SPAWNINGPOOL",
            "EVOLUTIONCHAMBER",
            "BANELING",
            "MUTALISK",
            "HYDRALISK",
            "LURKER",
            "ULTRALISK",
            "BROODLORD",
            "CORRUPTOR",
            "INFESTOR",
            "SWARMHOSTMP",
            "VIPER",
            "SPINECRAWLER",
            "SPORECRAWLER",
            "CREEPTUMOR",
            "CREEPTUMORQUEEN",
            "CREEPTUMORBURROWED",
        ),
    )
    upgrade_id_mod = _make_enum_module(
        "sc2.ids.upgrade_id",
        exported_class="UpgradeId",
        members=(
            "ZERGMELEEWEAPONSLEVEL1",
            "ZERGMELEEWEAPONSLEVEL2",
            "ZERGMELEEWEAPONSLEVEL3",
            "ZERGMISSILEWEAPONSLEVEL1",
            "ZERGGROUNDARMORSLEVEL1",
            "ZERGFLYERWEAPONSLEVEL1",
            "ZERGFLYERARMORSLEVEL1",
            "GLIALRECONSTITUTION",
            "TUNNELINGCLAWS",
            "CENTRIFICALHOOKS",
            "ZERGLINGMOVEMENTSPEED",
            "ZERGLINGATTACKSPEED",
        ),
    )

    ability_id_mod = _make_enum_module(
        "sc2.ids.ability_id",
        exported_class="AbilityId",
        members=(
            "BUILD_HATCHERY",
            "BUILD_EXTRACTOR",
            "BUILD_SPAWNINGPOOL",
            "BUILD_SPINECRAWLER",
            "BUILD_SPORECRAWLER",
            "RESEARCH_BURROW",
            "EFFECT_INJECTLARVA",
            "EFFECT_TRANSFUSION",
            "BUILD_CREEPTUMOR_QUEEN",
            "BUILD_CREEPTUMOR_TUMOR",
            "BUILD_CREEPTUMOR",
            "MORPH_LURKER",
            "MORPH_LAIR",
            "MORPH_HIVE",
        ),
    )
    buff_id_mod = _make_enum_module(
        "sc2.ids.buff_id",
        exported_class="BuffId",
        members=("QUEENSPAWNLARVATIMER", "BLINDINGCLOUD", "FUNGALGROWTH"),
    )

    # sc2.bot_ai.BotAI placeholder
    bot_ai_mod = types.ModuleType("sc2.bot_ai")

    class BotAI:
        pass

    bot_ai_mod.BotAI = BotAI

    # sc2.unit.Unit placeholder
    unit_mod = types.ModuleType("sc2.unit")

    class Unit:
        pass

    unit_mod.Unit = Unit

    # sc2.units.Units placeholder (list-like collection)
    units_mod = types.ModuleType("sc2.units")

    class Units(list):
        def __init__(self, units=(), bot_object=None):
            super().__init__(units)
            self._bot_object = bot_object

    units_mod.Units = Units

    # sc2.data.Race / Result placeholders
    data_mod = types.ModuleType("sc2.data")

    class _SimpleEnum:
        @classmethod
        def __getattr__(cls, item):
            return item

    class _NamedString(str):
        @property
        def name(self) -> str:
            return str(self)

        @property
        def value(self) -> str:
            return str(self)

    class _StringEnumMeta(type):
        def __getitem__(cls, item):
            members = cls.__dict__.get("_members", {})
            if item not in members:
                ns = _NamedString(item)
                members[item] = ns
                setattr(cls, item, ns)
            return members[item]

        def __iter__(cls):
            return iter(cls.__dict__.get("_members", {}).values())

    def _make_string_enum(name: str, members):
        d = {"_members": {m: _NamedString(m) for m in members}}
        d.update(d["_members"])
        return _StringEnumMeta(name, (), d)

    Race = _make_string_enum("Race", ("Zerg", "Terran", "Protoss", "Random"))
    Result = _make_string_enum("Result", ("Victory", "Defeat", "Tie"))
    Difficulty = _make_string_enum(
        "Difficulty",
        (
            "VeryEasy",
            "Easy",
            "Medium",
            "MediumHard",
            "Hard",
            "Harder",
            "VeryHard",
            "CheatVision",
            "CheatMoney",
            "CheatInsane",
        ),
    )
    data_mod.Race = Race
    data_mod.Result = Result
    data_mod.Difficulty = Difficulty

    # sc2.maps with a no-op get() so calls don't crash during collection.
    maps_mod = types.ModuleType("sc2.maps")

    def _maps_get(name):
        return name

    maps_mod.get = _maps_get
    sc2_pkg.maps = maps_mod

    # sc2.constants placeholder (commonly referenced sets are populated lazily)
    constants_mod = types.ModuleType("sc2.constants")
    constants_mod.IS_STRUCTURE = set()
    constants_mod.UNIT_TRAINED_FROM = {}

    sys.modules.setdefault("sc2", sc2_pkg)
    sys.modules.setdefault("sc2.position", position_mod)
    sys.modules.setdefault("sc2.ids", ids_pkg)
    sys.modules.setdefault("sc2.ids.unit_typeid", unit_typeid_mod)
    sys.modules.setdefault("sc2.ids.upgrade_id", upgrade_id_mod)
    sys.modules.setdefault("sc2.ids.ability_id", ability_id_mod)
    sys.modules.setdefault("sc2.ids.buff_id", buff_id_mod)
    sys.modules.setdefault("sc2.bot_ai", bot_ai_mod)
    sys.modules.setdefault("sc2.unit", unit_mod)
    sys.modules.setdefault("sc2.units", units_mod)
    sys.modules.setdefault("sc2.data", data_mod)
    sys.modules.setdefault("sc2.constants", constants_mod)
    sys.modules.setdefault("sc2.maps", maps_mod)

    # sc2.main / sc2.player / sc2.client / sc2.protocol — stubbed callables
    main_mod = types.ModuleType("sc2.main")

    async def _async_noop(*args, **kwargs):
        return None

    main_mod.run_game = _async_noop
    main_mod._play_game = _async_noop
    sys.modules.setdefault("sc2.main", main_mod)

    player_mod = types.ModuleType("sc2.player")
    player_mod.Bot = type("Bot", (), {"__init__": lambda self, *a, **k: None})
    player_mod.Computer = type("Computer", (), {"__init__": lambda self, *a, **k: None})
    player_mod.Human = type("Human", (), {"__init__": lambda self, *a, **k: None})
    sys.modules.setdefault("sc2.player", player_mod)

    client_mod = types.ModuleType("sc2.client")
    client_mod.Client = type("Client", (), {})
    sys.modules.setdefault("sc2.client", client_mod)

    protocol_mod = types.ModuleType("sc2.protocol")
    protocol_mod.ConnectionAlreadyClosed = type(
        "ConnectionAlreadyClosed", (Exception,), {}
    )
    sys.modules.setdefault("sc2.protocol", protocol_mod)

    portconfig_mod = types.ModuleType("sc2.portconfig")
    portconfig_mod.Portconfig = type("Portconfig", (), {})
    sys.modules.setdefault("sc2.portconfig", portconfig_mod)


_install_sc2_stub()
