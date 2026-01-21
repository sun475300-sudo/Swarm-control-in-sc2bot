#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic Upgrade Manager
"""

from typing import List

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    class UnitTypeId:
        ZERGLING = "ZERGLING"
        BANELING = "BANELING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        MUTALISK = "MUTALISK"
        EVOLUTIONCHAMBER = "EVOLUTIONCHAMBER"
        LAIR = "LAIR"
        HIVE = "HIVE"
        VOIDRAY = "VOIDRAY"
        CARRIER = "CARRIER"
        LIBERATOR = "LIBERATOR"
        BATTLECRUISER = "BATTLECRUISER"
        PHOENIX = "PHOENIX"
        SIEGETANK = "SIEGETANK"
        THOR = "THOR"
        HELLION = "HELLION"
        CYCLONE = "CYCLONE"
        COLOSSUS = "COLOSSUS"
        IMMORTAL = "IMMORTAL"

    class UpgradeId:
        ZERGMELEEWEAPONSLEVEL1 = "ZERGMELEEWEAPONSLEVEL1"
        ZERGMELEEWEAPONSLEVEL2 = "ZERGMELEEWEAPONSLEVEL2"
        ZERGMELEEWEAPONSLEVEL3 = "ZERGMELEEWEAPONSLEVEL3"
        ZERGMISSILEWEAPONSLEVEL1 = "ZERGMISSILEWEAPONSLEVEL1"
        ZERGMISSILEWEAPONSLEVEL2 = "ZERGMISSILEWEAPONSLEVEL2"
        ZERGMISSILEWEAPONSLEVEL3 = "ZERGMISSILEWEAPONSLEVEL3"
        ZERGGROUNDARMORSLEVEL1 = "ZERGGROUNDARMORSLEVEL1"
        ZERGGROUNDARMORSLEVEL2 = "ZERGGROUNDARMORSLEVEL2"
        ZERGGROUNDARMORSLEVEL3 = "ZERGGROUNDARMORSLEVEL3"


class UpgradeManager:
    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 66  # ~3s

    async def on_step(self, iteration: int):
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration
        await self._apply_dynamic_upgrades()

    async def _apply_dynamic_upgrades(self):
        if not hasattr(self.bot, "structures"):
            return
        evo = self.bot.structures(UnitTypeId.EVOLUTIONCHAMBER).ready
        if not evo.exists:
            return

        priorities = self._compute_upgrade_priorities()
        for chamber in evo.idle:
            for upgrade in priorities:
                if self._can_research_upgrade(upgrade):
                    try:
                        await self.bot.do(chamber.research(upgrade))
                        break
                    except Exception:
                        continue

    def _compute_upgrade_priorities(self) -> List[UpgradeId]:
        # Composition based
        units = self.bot.units
        ling_bane = units(UnitTypeId.ZERGLING).amount + units(UnitTypeId.BANELING).amount
        roach = units(UnitTypeId.ROACH).amount
        hydra = units(UnitTypeId.HYDRALISK).amount
        muta = units(UnitTypeId.MUTALISK).amount

        comp_total = max(1, ling_bane + roach + hydra + muta)
        ling_ratio = ling_bane / comp_total
        ranged_ratio = (roach + hydra) / comp_total

        # Enemy matchup hints
        enemy_race = getattr(self.bot, "enemy_race", None)
        prefer_armor = enemy_race in {"Terran", "Protoss"}
        prefer_missile = False

        intel = getattr(self.bot, "intel", None)
        inferred_tech = set()
        inferred_strategy = None
        if intel and hasattr(intel, "get_inferred_tech"):
            inferred_tech = set(intel.get_inferred_tech())
        if intel and hasattr(intel, "get_inferred_strategy"):
            inferred_strategy = intel.get_inferred_strategy()

        if inferred_strategy == "air":
            prefer_missile = True
        if inferred_strategy in {"early_marine_rush", "12_pool_rush"}:
            prefer_armor = True

        air_tech = {
            UnitTypeId.VOIDRAY,
            UnitTypeId.CARRIER,
            UnitTypeId.LIBERATOR,
            UnitTypeId.BATTLECRUISER,
            UnitTypeId.PHOENIX,
        }
        mech_tech = {
            UnitTypeId.SIEGETANK,
            UnitTypeId.THOR,
            UnitTypeId.HELLION,
            UnitTypeId.CYCLONE,
            UnitTypeId.COLOSSUS,
            UnitTypeId.IMMORTAL,
        }
        if inferred_tech & air_tech:
            prefer_missile = True
        if inferred_tech & mech_tech:
            prefer_armor = True

        melee = [
            UpgradeId.ZERGMELEEWEAPONSLEVEL1,
            UpgradeId.ZERGMELEEWEAPONSLEVEL2,
            UpgradeId.ZERGMELEEWEAPONSLEVEL3,
        ]
        missile = [
            UpgradeId.ZERGMISSILEWEAPONSLEVEL1,
            UpgradeId.ZERGMISSILEWEAPONSLEVEL2,
            UpgradeId.ZERGMISSILEWEAPONSLEVEL3,
        ]
        armor = [
            UpgradeId.ZERGGROUNDARMORSLEVEL1,
            UpgradeId.ZERGGROUNDARMORSLEVEL2,
            UpgradeId.ZERGGROUNDARMORSLEVEL3,
        ]

        if prefer_missile:
            return missile + (armor if prefer_armor else melee)
        if ling_ratio >= 0.45:
            return melee + (armor if prefer_armor else missile)
        if ranged_ratio >= 0.45:
            return missile + (armor if prefer_armor else melee)
        # Balanced
        return (armor if prefer_armor else melee) + missile

    def _can_research_upgrade(self, upgrade: UpgradeId) -> bool:
        if hasattr(self.bot, "already_pending_upgrade"):
            if self.bot.already_pending_upgrade(upgrade) > 0:
                return False
        if hasattr(self.bot, "upgrades") and upgrade in self.bot.upgrades:
            return False
        if not self.bot.can_afford(upgrade):
            return False
        return True
