#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Micro combat utilities with anti-splash awareness.
"""

from __future__ import annotations

import asyncio
from typing import Iterable, List, Optional, Set, Tuple

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None
    AbilityId = None
    UpgradeId = None
    Point2 = None

try:
    from combat.terrain_analysis import ChokePointDetector
except ImportError:
    ChokePointDetector = None


class AntiSplashAwareness:
    """Detects splash threats and provides repulsion/separation boosts."""

    def __init__(self) -> None:
        self.avoid_radius = 10.0
        self.min_multiplier = 5.0
        self.max_multiplier = 15.0  # Increased for better panic response
        self.air_multiplier = 12.0  # Increased for air units
        self.ground_multiplier = 8.0  # Increased for ground units
        self.extreme_threat_multiplier = 20.0  # For critical threats
        self.threat_types = set()
        self.extreme_threats = set()  # High-priority splash threats

        if UnitTypeId:
            # Regular splash threats - use getattr for compatibility
            threat_type_names = [
                "SIEGETANK",
                "SIEGETANKSIEGED",
                "HIGHTEMPLAR",
                "BANELING",
                "BANELINGBURROWED",
                "DISRUPTOR",
                "COLOSSUS",
                "HELLION",
                "HELLBAT",
                "HELLIONTANK",
                "LIBERATORAG",
                "LURKERMP",
                "LURKERMPBURROWED",
                "RAVEN",
                "WIDOWMINE",
                "WIDOWMINEBURROWED",
            ]
            for name in threat_type_names:
                unit_type = getattr(UnitTypeId, name, None)
                if unit_type is not None:
                    self.threat_types.add(unit_type)

            # Extreme threats requiring immediate panic split
            extreme_names = ["SIEGETANKSIEGED", "HIGHTEMPLAR", "DISRUPTOR", "BANELING"]
            for name in extreme_names:
                unit_type = getattr(UnitTypeId, name, None)
                if unit_type is not None:
                    self.extreme_threats.add(unit_type)

    def get_threats(self, enemy_units: Iterable) -> List:
        """Get splash threat units. Phase 22: Uses set lookup for O(1) type check."""
        if not self.threat_types or not enemy_units:
            return []
        return [enemy for enemy in enemy_units if enemy.type_id in self.threat_types]

    def separation_multiplier(self, unit, enemy_units: Iterable) -> float:
        threats = self.get_threats(enemy_units)
        if not threats:
            return 1.0

        # Check for extreme threats first (panic mode)
        extreme_nearby = self._has_extreme_threat_nearby(unit, threats)
        if extreme_nearby:
            nearest = extreme_nearby
            if nearest <= self.avoid_radius * 1.2:  # Extended range for extreme threats
                ratio = max(0.0, 1.0 - (nearest / (self.avoid_radius * 1.2)))
                return min(
                    self.extreme_threat_multiplier,
                    self.max_multiplier
                    + ratio * (self.extreme_threat_multiplier - self.max_multiplier),
                )

        # Regular threat handling
        nearest = self._closest_threat_distance(unit, threats)
        if nearest is None or nearest > self.avoid_radius:
            return 1.0

        ratio = max(0.0, 1.0 - (nearest / self.avoid_radius))
        return min(
            self.max_multiplier,
            self.min_multiplier + ratio * (self.max_multiplier - self.min_multiplier),
        )

    def repulsion_vector(self, unit, enemy_units: Iterable) -> Tuple[float, float]:
        threats = self.get_threats(enemy_units)
        if not threats:
            return 0.0, 0.0

        repulsion_x = 0.0
        repulsion_y = 0.0
        weight = (
            self.air_multiplier
            if getattr(unit, "is_flying", False)
            else self.ground_multiplier
        )

        for threat in threats:
            try:
                dist = unit.distance_to(threat)
            except Exception:
                continue
            if dist <= 0 or dist > self.avoid_radius:
                continue
            strength = (self.avoid_radius - dist) / self.avoid_radius
            dx = unit.position.x - threat.position.x
            dy = unit.position.y - threat.position.y
            repulsion_x += (dx / (dist + 0.1)) * strength * weight
            repulsion_y += (dy / (dist + 0.1)) * strength * weight

        return repulsion_x, repulsion_y

    def _has_extreme_threat_nearby(self, unit, threats: Iterable) -> Optional[float]:
        """Check for extreme threats and return nearest distance, or None if no extreme threat."""
        if not self.extreme_threats:
            return None

        extreme_distances = []
        for threat in threats:
            if threat.type_id not in self.extreme_threats:
                continue
            try:
                dist = unit.distance_to(threat)
                extreme_distances.append(dist)
            except Exception:
                continue

        if not extreme_distances:
            return None
        return min(extreme_distances)

    @staticmethod
    def _closest_threat_distance(unit, threats: Iterable) -> Optional[float]:
        distances = []
        for threat in threats:
            try:
                distances.append(unit.distance_to(threat))
            except Exception:
                continue
        if not distances:
            return None
        return min(distances)


class ChokePointManager:
    """Detects chokepoints and adjusts unit behavior to prevent congestion."""

    def __init__(self, bot):
        self.bot = bot
        self.chokepoints = []
        self.chokepoint_cache_frame = -1
        self.chokepoint_radius = 5.0  # Detection radius for chokepoints

    def update_chokepoints(self, iteration: int) -> None:
        """Update chokepoint cache every 100 frames."""
        if iteration - self.chokepoint_cache_frame < 100:
            return

        self.chokepoint_cache_frame = iteration
        self.chokepoints = []

        # Get chokepoints from game_info if available
        if hasattr(self.bot, "game_info") and hasattr(self.bot.game_info, "map_ramps"):
            for ramp in self.bot.game_info.map_ramps:
                if hasattr(ramp, "top_center"):
                    self.chokepoints.append(ramp.top_center)
                if hasattr(ramp, "bottom_center"):
                    self.chokepoints.append(ramp.bottom_center)

    def is_in_chokepoint(self, position) -> bool:
        """Check if position is near a chokepoint."""
        if not self.chokepoints or not position:
            return False

        for choke in self.chokepoints:
            try:
                if position.distance_to(choke) < self.chokepoint_radius:
                    return True
            except Exception:
                continue
        return False

    def get_cohesion_modifier(self, position) -> float:
        """
        Return cohesion weight modifier for position.
        Lower cohesion in chokepoints to prevent clustering.
        """
        if self.is_in_chokepoint(position):
            return 0.3  # Reduce cohesion to 30% in chokepoints
        return 1.0  # Normal cohesion elsewhere


class ZvTMicroAdjustments:
    """Terran-specific micro from STRATEGY_PLAN Phase 1."""

    def __init__(self, bot):
        self.bot = bot

    def apply(self, own_units: Iterable, enemy_units: Iterable) -> Set[int]:
        if not self._is_terran_matchup():
            return set()

        own_list = list(own_units) if own_units else []
        enemy_list = list(enemy_units) if enemy_units else []
        handled: Set[int] = set()
        handled.update(self.handle_siege_tanks(own_list, enemy_list, handled))
        handled.update(self.handle_marine_ball(own_list, enemy_list, handled))
        handled.update(self.handle_medivac_drop(enemy_list, handled))
        handled.update(self.handle_widow_mines(own_list, enemy_list, handled))
        return handled

    def handle_siege_tanks(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        handled: Set[int] = set()
        tanks = self._units_of_type(enemy_units, {"SIEGETANKSIEGED"})
        if not tanks:
            return handled

        actions = []
        bile = getattr(AbilityId, "EFFECT_CORROSIVEBILE", None)
        zerglings = self._units_of_type(own_units, {"ZERGLING"})
        ravagers = self._units_of_type(own_units, {"RAVAGER"})
        for tank in tanks:
            for ling in self._within(zerglings, tank, 15.0):
                if getattr(ling, "tag", None) in reserved or ling.tag in handled:
                    continue
                target = tank.position.towards(ling.position, 1.5)
                actions.append(ling.move(target))
                handled.add(ling.tag)

            if bile:
                for ravager in self._within(ravagers, tank, 9.0):
                    if (
                        getattr(ravager, "tag", None) in reserved
                        or ravager.tag in handled
                    ):
                        continue
                    actions.append(ravager(bile, tank.position))
                    handled.add(ravager.tag)

        self._issue_actions(actions)
        return handled

    def handle_marine_ball(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        handled: Set[int] = set()
        marines = self._units_of_type(enemy_units, {"MARINE"})
        if len(marines) < 6:
            return handled

        actions = []
        banelings = self._units_of_type(own_units, {"BANELING"})
        for center in self._find_unit_clumps(marines, radius=3.0, min_count=6):
            candidates = [
                b
                for b in banelings
                if getattr(b, "tag", None) not in reserved
                and getattr(b, "tag", None) not in handled
            ]
            for bane in self._closest_n_units(candidates, center, 4):
                actions.append(bane.attack(center))
                handled.add(bane.tag)

        self._issue_actions(actions)
        return handled

    def handle_medivac_drop(self, enemy_units: List, reserved: Set[int]) -> Set[int]:
        handled: Set[int] = set()
        medivacs = self._units_of_type(enemy_units, {"MEDIVAC"})
        if not medivacs:
            return handled

        bases = list(getattr(self.bot, "townhalls", []) or [])
        if not bases:
            return handled

        actions = []
        queens = self._units_of_type(getattr(self.bot, "units", []) or [], {"QUEEN"})
        hydras = self._units_of_type(
            getattr(self.bot, "units", []) or [], {"HYDRALISK"}
        )
        for base in bases:
            nearby_medivacs = self._within(medivacs, base, 22.0)
            if not nearby_medivacs:
                continue
            for queen in self._within(queens, base, 20.0):
                if getattr(queen, "tag", None) in reserved or queen.tag in handled:
                    continue
                target = self._closest_to(nearby_medivacs, queen)
                if target:
                    actions.append(queen.attack(target))
                    handled.add(queen.tag)
            for hydra in self._within(hydras, base, 25.0):
                if getattr(hydra, "tag", None) in reserved or hydra.tag in handled:
                    continue
                target = self._closest_to(nearby_medivacs, hydra)
                if target:
                    actions.append(hydra.attack(target))
                    handled.add(hydra.tag)

        self._issue_actions(actions)
        return handled

    def handle_widow_mines(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        mines = self._units_of_type(enemy_units, {"WIDOWMINE", "WIDOWMINEBURROWED"})
        if not mines:
            return set()

        handled: Set[int] = set()
        actions = []
        zerglings = self._units_of_type(own_units, {"ZERGLING"})
        for mine in mines:
            candidates = [
                ling
                for ling in zerglings
                if getattr(ling, "tag", None) not in reserved
                and getattr(ling, "tag", None) not in handled
            ]
            expendable = self._closest_to(candidates, mine)
            if not expendable:
                continue
            actions.append(expendable.attack(mine.position))
            handled.add(expendable.tag)

        self._issue_actions(actions)
        return handled

    def _is_terran_matchup(self) -> bool:
        race = getattr(self.bot, "enemy_race", None)
        return race is not None and "terran" in str(race).lower()

    @staticmethod
    def _unit_name(unit) -> str:
        return getattr(getattr(unit, "type_id", None), "name", str(getattr(unit, "type_id", ""))).upper()

    def _units_of_type(self, units: Iterable, names: Set[str]) -> List:
        wanted = {getattr(UnitTypeId, name, None) for name in names if UnitTypeId}
        result = []
        for unit in units:
            unit_type = getattr(unit, "type_id", None)
            if self._unit_name(unit) in names:
                result.append(unit)
                continue
            try:
                type_matches = unit_type in wanted
            except TypeError:
                type_matches = False
            if type_matches:
                result.append(unit)
        return result

    @staticmethod
    def _within(units: Iterable, target, distance: float) -> List:
        result = []
        for unit in units:
            try:
                if unit.distance_to(target) <= distance:
                    result.append(unit)
            except Exception:
                continue
        return result

    @staticmethod
    def _closest_to(units: Iterable, target):
        closest = None
        closest_dist = None
        for unit in units:
            try:
                dist = unit.distance_to(target)
            except Exception:
                continue
            if closest_dist is None or dist < closest_dist:
                closest = unit
                closest_dist = dist
        return closest

    def _closest_n_units(self, units: Iterable, target, count: int) -> List:
        sortable = []
        for unit in units:
            try:
                sortable.append((unit.distance_to(target), unit))
            except Exception:
                continue
        sortable.sort(key=lambda item: item[0])
        return [unit for _, unit in sortable[:count]]

    def _find_unit_clumps(self, units: List, radius: float, min_count: int) -> List:
        centers = []
        seen = set()
        for unit in units:
            nearby = []
            for other in units:
                try:
                    if unit.distance_to(other) <= radius:
                        nearby.append(other)
                except Exception:
                    continue
            if len(nearby) < min_count:
                continue
            tags = frozenset(getattr(u, "tag", id(u)) for u in nearby)
            if tags in seen:
                continue
            seen.add(tags)
            center = self._center_of_units(nearby)
            if center:
                centers.append(center)
        return centers

    @staticmethod
    def _center_of_units(units: List):
        if not units:
            return None
        if not Point2:
            return units[0].position
        x = sum(unit.position.x for unit in units) / len(units)
        y = sum(unit.position.y for unit in units) / len(units)
        return Point2((x, y))

    def _issue_actions(self, actions: List) -> None:
        for action in actions:
            try:
                result = self.bot.do(action)
                if asyncio.iscoroutine(result):
                    try:
                        asyncio.create_task(result)
                    except RuntimeError:
                        pass
            except Exception:
                continue


class ZvPMicroAdjustments(ZvTMicroAdjustments):
    """Protoss-specific micro from STRATEGY_PLAN Phase 2."""

    def apply(self, own_units: Iterable, enemy_units: Iterable) -> Set[int]:
        if not self._is_protoss_matchup():
            return set()

        own_list = list(own_units) if own_units else []
        enemy_list = list(enemy_units) if enemy_units else []
        handled: Set[int] = set()
        handled.update(self.handle_psionic_storm(own_list, handled))
        handled.update(self.handle_force_fields(own_list, enemy_list, handled))
        handled.update(self.handle_colossus(own_list, enemy_list, handled))
        handled.update(self.handle_oracles(own_list, enemy_list, handled))
        return handled

    def handle_force_fields(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        handled: Set[int] = set()
        force_positions = self._effect_positions({"FORCEFIELD"})
        sentries = self._units_of_type(enemy_units, {"SENTRY"})
        for sentry in sentries:
            position = getattr(sentry, "position", None)
            if position is not None:
                force_positions.append(position)
        if not force_positions:
            return handled

        actions = []
        bile = getattr(AbilityId, "EFFECT_CORROSIVEBILE", None)
        ravagers = self._units_of_type(own_units, {"RAVAGER"})
        for position in force_positions:
            if bile:
                for ravager in self._within_positions(ravagers, position, 9.0):
                    tag = getattr(ravager, "tag", None)
                    if tag in reserved or tag in handled:
                        continue
                    actions.append(ravager(bile, position))
                    handled.add(tag)
            for unit in self._within_positions(own_units, position, 4.5):
                tag = getattr(unit, "tag", None)
                if tag in reserved or tag in handled:
                    continue
                try:
                    actions.append(unit.move(unit.position.towards(position, -3)))
                    handled.add(tag)
                except Exception:
                    continue

        self._set("zvp_force_field_detected", True)
        self._issue_actions(actions)
        return handled

    def handle_psionic_storm(self, own_units: List, reserved: Set[int]) -> Set[int]:
        handled: Set[int] = set()
        storm_positions = self._effect_positions({"PSISTORM", "PSYCHICSTORM", "STORM"})
        if not storm_positions:
            return handled

        actions = []
        for position in storm_positions:
            for unit in self._within_positions(own_units, position, 4.0):
                tag = getattr(unit, "tag", None)
                if tag in reserved or tag in handled:
                    continue
                try:
                    actions.append(unit.move(unit.position.towards(position, -3)))
                    handled.add(tag)
                except Exception:
                    continue

        self._set("zvp_storm_split_active", True)
        self._issue_actions(actions)
        return handled

    def handle_colossus(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        colossi = self._units_of_type(enemy_units, {"COLOSSUS"})
        if not colossi:
            return set()

        handled: Set[int] = set()
        actions = []
        for corruptor in self._units_of_type(own_units, {"CORRUPTOR"}):
            tag = getattr(corruptor, "tag", None)
            if tag in reserved or tag in handled:
                continue
            target = self._closest_to(colossi, corruptor)
            if target:
                actions.append(corruptor.attack(target))
                handled.add(tag)

        for unit in own_units:
            tag = getattr(unit, "tag", None)
            if tag in reserved or tag in handled:
                continue
            if not self._is_ground_unit(unit):
                continue
            closest = self._closest_to(colossi, unit)
            if not closest:
                continue
            try:
                if unit.distance_to(closest) < 7.0:
                    actions.append(unit.move(unit.position.towards(closest.position, -2)))
                    handled.add(tag)
            except Exception:
                continue

        self._issue_actions(actions)
        return handled

    def handle_oracles(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        oracles = self._units_of_type(enemy_units, {"ORACLE"})
        if not oracles:
            return set()

        handled: Set[int] = set()
        actions = []
        bases = list(getattr(self.bot, "townhalls", []) or [])
        defenders = self._units_of_type(own_units + self._bot_units_list(), {"QUEEN", "HYDRALISK"})
        for base in bases:
            nearby_oracles = self._within(oracles, base, 18.0)
            if not nearby_oracles:
                continue
            for defender in self._within(defenders, base, 22.0):
                tag = getattr(defender, "tag", None)
                if tag in reserved or tag in handled:
                    continue
                target = self._closest_to(nearby_oracles, defender)
                if target:
                    actions.append(defender.attack(target))
                    handled.add(tag)
            if not self._has_spore_near(base):
                self._set("need_spore_at", getattr(base, "position", base))
                self._set("AIR_THREAT_ACTIVE", True)

        self._issue_actions(actions)
        return handled

    def _is_protoss_matchup(self) -> bool:
        race = getattr(self.bot, "enemy_race", None)
        return race is not None and "protoss" in str(race).lower()

    def _effect_positions(self, names: Set[str]) -> List:
        state = getattr(self.bot, "state", None)
        effects = getattr(state, "effects", []) if state is not None else []
        try:
            effects = list(effects or [])
        except TypeError:
            return []

        positions = []
        for effect in effects:
            effect_id = getattr(effect, "id", None)
            effect_name = getattr(effect_id, "name", str(effect_id)).upper()
            if not any(name in effect_name for name in names):
                continue
            try:
                positions.extend(list(getattr(effect, "positions", []) or []))
            except TypeError:
                continue
        return positions

    @staticmethod
    def _within_positions(units: Iterable, position, distance: float) -> List:
        result = []
        for unit in units:
            try:
                if unit.distance_to(position) <= distance:
                    result.append(unit)
            except Exception:
                continue
        return result

    @staticmethod
    def _is_ground_unit(unit) -> bool:
        if hasattr(unit, "is_ground"):
            return bool(unit.is_ground)
        return not bool(getattr(unit, "is_flying", False))

    def _bot_units_list(self) -> List:
        units = getattr(self.bot, "units", [])
        try:
            return list(units or [])
        except TypeError:
            return []

    def _has_spore_near(self, base) -> bool:
        structures = getattr(self.bot, "structures", None)
        if callable(structures):
            try:
                spores = structures(UnitTypeId.SPORECRAWLER)
                if hasattr(spores, "closer_than"):
                    nearby = spores.closer_than(10, base)
                    return bool(nearby) or getattr(nearby, "amount", 0) > 0
                return bool(spores)
            except Exception:
                return False
        try:
            candidates = list(structures or [])
        except TypeError:
            return False
        for structure in candidates:
            if self._unit_name(structure) != "SPORECRAWLER":
                continue
            try:
                if structure.distance_to(base) <= 10:
                    return True
            except Exception:
                continue
        return False

    def _set(self, key: str, value) -> None:
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard and hasattr(blackboard, "set"):
            blackboard.set(key, value)


class ZvZMicroAdjustments(ZvTMicroAdjustments):
    """Zerg mirror micro for early ling/bane and roach mirrors."""

    def apply(self, own_units: Iterable, enemy_units: Iterable) -> Set[int]:
        if not self._is_zerg_matchup():
            return set()

        own_list = list(own_units) if own_units else []
        enemy_list = list(enemy_units) if enemy_units else []
        handled: Set[int] = set()
        handled.update(self.ling_bane_micro(own_list, enemy_list, handled))
        handled.update(self.roach_vs_roach_micro(own_list, enemy_list, handled))
        return handled

    def ling_bane_micro(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        handled: Set[int] = set()
        own_lings = self._units_of_type(own_units, {"ZERGLING"})
        own_banes = self._units_of_type(own_units, {"BANELING"})
        enemy_lings = self._units_of_type(enemy_units, {"ZERGLING"})
        enemy_banes = self._units_of_type(enemy_units, {"BANELING", "BANELINGBURROWED"})
        if not (own_lings or own_banes):
            return handled

        actions = []
        for ling in own_lings:
            tag = getattr(ling, "tag", None)
            if tag in reserved or tag in handled:
                continue
            closest_bane = self._closest_to(enemy_banes, ling)
            try:
                if closest_bane and ling.distance_to(closest_bane) < 4.0:
                    actions.append(ling.move(ling.position.towards(closest_bane.position, -4)))
                    handled.add(tag)
                    continue
            except Exception:
                pass
            target = self._closest_to(enemy_lings, ling)
            if target:
                actions.append(ling.attack(target))
                handled.add(tag)

        if len(enemy_lings) >= 4:
            densest = self._find_densest_point(enemy_lings, radius=2.0)
            for bane in own_banes:
                tag = getattr(bane, "tag", None)
                if tag in reserved or tag in handled:
                    continue
                actions.append(bane.attack(densest))
                handled.add(tag)
        elif enemy_banes:
            for bane in own_banes:
                tag = getattr(bane, "tag", None)
                if tag in reserved or tag in handled:
                    continue
                target = self._closest_to(enemy_banes, bane)
                if target:
                    actions.append(bane.attack(target))
                    handled.add(tag)

        self._issue_actions(actions)
        return handled

    def roach_vs_roach_micro(
        self, own_units: List, enemy_units: List, reserved: Set[int]
    ) -> Set[int]:
        own_roaches = self._units_of_type(own_units, {"ROACH"})
        enemy_roaches = self._units_of_type(enemy_units, {"ROACH", "RAVAGER"})
        if not own_roaches or not enemy_roaches:
            return set()

        handled: Set[int] = set()
        actions = []
        burrow_down = getattr(AbilityId, "BURROWDOWN_ROACH", None)
        burrow_available = self._burrow_available()
        for roach in own_roaches:
            tag = getattr(roach, "tag", None)
            if tag in reserved or tag in handled:
                continue
            if getattr(roach, "health_percentage", 1.0) < 0.30:
                if burrow_available and burrow_down:
                    actions.append(roach(burrow_down))
                else:
                    start = getattr(self.bot, "start_location", None)
                    if start is not None:
                        actions.append(roach.move(roach.position.towards(start, 5)))
                handled.add(tag)
                continue
            weakest = min(enemy_roaches, key=lambda enemy: getattr(enemy, "health", 0))
            actions.append(roach.attack(weakest))
            handled.add(tag)

        self._issue_actions(actions)
        return handled

    def _is_zerg_matchup(self) -> bool:
        race = getattr(self.bot, "enemy_race", None)
        return race is not None and "zerg" in str(race).lower()

    def _burrow_available(self) -> bool:
        burrow = getattr(UpgradeId, "BURROW", None)
        state = getattr(self.bot, "state", None)
        upgrades = getattr(state, "upgrades", set()) if state is not None else set()
        if burrow and burrow in upgrades:
            return True
        already_pending_upgrade = getattr(self.bot, "already_pending_upgrade", None)
        if callable(already_pending_upgrade) and burrow:
            try:
                return bool(already_pending_upgrade(burrow))
            except Exception:
                return False
        return False

    def _find_densest_point(self, units: List, radius: float = 2.0):
        best_pos = getattr(units[0], "position", None) if units else None
        best_count = -1
        for unit in units:
            count = 0
            for other in units:
                try:
                    if unit.distance_to(other) <= radius:
                        count += 1
                except Exception:
                    continue
            if count > best_count:
                best_count = count
                best_pos = getattr(unit, "position", best_pos)
        return best_pos


class MicroCombat:
    """Lightweight micro helpers with anti-splash reactions."""

    def __init__(self, bot):
        self.bot = bot
        self.anti_splash = AntiSplashAwareness()
        self.chokepoint_manager = ChokePointManager(bot)
        self.lurker_choke_detector = (
            ChokePointDetector(bot) if ChokePointDetector else None
        )
        self.zvt = ZvTMicroAdjustments(bot)
        self.zvp = ZvPMicroAdjustments(bot)
        self.zvz = ZvZMicroAdjustments(bot)

    def manage_lurker_positioning(self, iteration: int = 0) -> Set[int]:
        """Position Lurkers on nearby chokes and burrow with LURKERMP ids."""
        if not UnitTypeId:
            return set()

        if self.lurker_choke_detector:
            self.lurker_choke_detector.update_chokepoints(iteration)
            chokepoints = list(getattr(self.lurker_choke_detector, "chokepoints", []))
        else:
            self.chokepoint_manager.update_chokepoints(iteration)
            chokepoints = list(getattr(self.chokepoint_manager, "chokepoints", []))
        if not chokepoints:
            return set()

        lurkers = self._get_lurkers()
        if not lurkers:
            return set()

        enemies = list(getattr(self.bot, "enemy_units", []) or [])
        burrow_down = getattr(AbilityId, "BURROWDOWN_LURKER", None) or getattr(
            AbilityId, "BURROWDOWN_LURKERMP", None
        )
        burrow_up = getattr(AbilityId, "BURROWUP_LURKER", None) or getattr(
            AbilityId, "BURROWUP_LURKERMP", None
        )

        actions = []
        handled: Set[int] = set()
        for lurker in lurkers:
            tag = getattr(lurker, "tag", None)
            if tag is None:
                continue
            choke = self._nearest_choke(getattr(lurker, "position", None), chokepoints)
            if choke is None:
                continue

            is_burrowed = getattr(lurker, "is_burrowed", False) or self._unit_name(
                lurker
            ) == "LURKERMPBURROWED"
            try:
                if not is_burrowed:
                    if lurker.distance_to(choke) < 3.0 and burrow_down:
                        actions.append(lurker(burrow_down))
                    else:
                        actions.append(lurker.move(choke))
                    handled.add(tag)
                    continue

                enemies_nearby = [
                    enemy for enemy in enemies if enemy.distance_to(lurker) <= 9.0
                ]
                if not enemies_nearby and burrow_up:
                    enemies_far = [
                        enemy for enemy in enemies if enemy.distance_to(lurker) <= 20.0
                    ]
                    if enemies_far:
                        actions.append(lurker(burrow_up))
                        handled.add(tag)
            except Exception:
                continue

        self._issue_actions(actions)
        return handled

    def _get_lurkers(self) -> List:
        units = getattr(self.bot, "units", [])
        lurker_types = {
            getattr(UnitTypeId, "LURKERMP", None),
            getattr(UnitTypeId, "LURKERMPBURROWED", None),
        }
        lurker_types.discard(None)
        if callable(units):
            result = []
            for unit_type in lurker_types:
                try:
                    result.extend(list(units(unit_type) or []))
                except Exception:
                    continue
            return result
        try:
            iterable = list(units or [])
        except TypeError:
            return []
        result = []
        for unit in iterable:
            if self._unit_name(unit) in {"LURKERMP", "LURKERMPBURROWED"}:
                result.append(unit)
                continue
            try:
                type_matches = getattr(unit, "type_id", None) in lurker_types
            except TypeError:
                type_matches = False
            if type_matches:
                result.append(unit)
        return result

    @staticmethod
    def _unit_name(unit) -> str:
        return getattr(
            getattr(unit, "type_id", None), "name", str(getattr(unit, "type_id", ""))
        ).upper()

    @staticmethod
    def _nearest_choke(position, chokepoints: List):
        if position is None or not chokepoints:
            return None
        nearest = None
        nearest_dist = None
        for choke in chokepoints:
            try:
                dist = position.distance_to(choke)
            except Exception:
                continue
            if nearest_dist is None or dist < nearest_dist:
                nearest = choke
                nearest_dist = dist
        return nearest

    def focus_fire(self, units: Iterable, target) -> None:
        """
        * Phase 15-2: 포커스 파이어 개선 *
        - anti-splash는 극심한 위협(거리 4 이내)에만 적용
        - 나머지 유닛은 타겟 집중 공격
        - 사거리 안에 있으면 무조건 공격 우선
        """
        unit_list = list(units) if units else []
        actions = []
        enemy_units = getattr(self.bot, "enemy_units", [])
        handled_tags = set()
        handled_tags.update(self.zvt.apply(unit_list, enemy_units))
        handled_tags.update(self.zvp.apply(unit_list, enemy_units))
        handled_tags.update(self.zvz.apply(unit_list, enemy_units))
        for unit in unit_list:
            if getattr(unit, "tag", None) in handled_tags:
                continue
            # anti-splash: 극심한 위협(거리 4 이내)에만 회피
            rep_x, rep_y = self.anti_splash.repulsion_vector(unit, enemy_units)
            if rep_x or rep_y:
                # * Phase 15: 스플래시 위협이 매우 가까울 때만 회피 *
                splash_threats_close = False
                for threat_type in self.anti_splash.extreme_threats:
                    for e in enemy_units:
                        if (
                            hasattr(e, "type_id")
                            and e.type_id == threat_type
                            and hasattr(e, "distance_to")
                            and e.distance_to(unit) < 4
                        ):
                            splash_threats_close = True
                            break
                    if splash_threats_close:
                        break

                if splash_threats_close:
                    move_target = self._offset_position(unit, rep_x, rep_y)
                    if move_target:
                        actions.append(unit.move(move_target))
                        continue
            # 타겟이 사거리 안이면 무조건 공격
            actions.append(unit.attack(target))

        self._issue_actions(actions)

    def kiting(self, units: Iterable, enemy_units: Iterable) -> None:
        """
        Improved kiting logic: only kite when weapon is on cooldown.
        * Phase 15: 저체력 후퇴 + 원거리 카이팅 강화 *
        """
        unit_list = list(units) if units else []
        actions = []
        threats = list(enemy_units) if enemy_units else []
        handled_tags = set()
        handled_tags.update(self.zvt.apply(unit_list, threats))
        handled_tags.update(self.zvp.apply(unit_list, threats))
        handled_tags.update(self.zvz.apply(unit_list, threats))
        for unit in unit_list:
            if getattr(unit, "tag", None) in handled_tags:
                continue
            # * Phase 15-1: 저체력 유닛 자동 후퇴 (베인링/저글링 제외) *
            if unit.health_percentage < 0.3 and unit.type_id not in (
                getattr(UnitTypeId, "BANELING", None),
                getattr(UnitTypeId, "ZERGLING", None),
            ):
                closest = self._closest_enemy(unit, threats)
                if closest:
                    retreat_pos = unit.position.towards(closest.position, -5)
                    actions.append(unit.move(retreat_pos))
                    continue

            # 1. Queen Micro (Transfuse)
            if unit.type_id == getattr(UnitTypeId, "QUEEN", None):
                if self._micro_queen(unit, unit_list, actions):
                    continue

            # 2. Zergling Micro (Surround)
            if unit.type_id == getattr(UnitTypeId, "ZERGLING", None):
                if self._micro_zergling(unit, threats, actions):
                    continue

            # 3. Baneling Micro (Crash into clumps)
            if unit.type_id == getattr(UnitTypeId, "BANELING", None):
                if self._micro_baneling(unit, threats, actions):
                    continue

            # 3.1 Roach Micro (Burrow Heal)
            if unit.type_id == getattr(UnitTypeId, "ROACH", None):
                if self._micro_roach(unit, actions):
                    continue

            # 3.2 Roach Burrowed (Unburrow logic)
            if unit.type_id == getattr(UnitTypeId, "ROACHBURROWED", None):
                if self._micro_roach_burrowed(unit, actions):
                    continue

            # 4. Anti-Splash Repulsion
            rep_x, rep_y = self.anti_splash.repulsion_vector(unit, threats)
            if rep_x or rep_y:
                move_target = self._offset_position(unit, rep_x, rep_y)
                if move_target:
                    actions.append(unit.move(move_target))
                    continue

            # 5. * Phase 15-3: 원거리 유닛 카이팅 강화 *
            target = self._closest_enemy(unit, threats)
            if target:
                weapon_cooldown = unit.weapon_cooldown
                ground_range = unit.ground_range
                distance = unit.distance_to(target)

                # 원거리 유닛 (사거리 5+): 사거리 경계에서 카이팅
                if ground_range >= 5:
                    if weapon_cooldown > 0 and distance < ground_range + 1:
                        # 쿨다운 중 -> 사거리 유지하며 후퇴
                        move_target = unit.position.towards(target.position, -3)
                        actions.append(unit.move(move_target))
                    elif distance > ground_range + 2:
                        # 사거리 밖 -> 접근
                        actions.append(unit.attack(target))
                    else:
                        # 사거리 안 + 공격 가능 -> 공격
                        actions.append(unit.attack(target))
                else:
                    # 근접/단거리 유닛: 기존 로직
                    if weapon_cooldown > 0 and distance < ground_range:
                        move_target = unit.position.towards(target.position, -2)
                        actions.append(unit.move(move_target))
                    else:
                        actions.append(unit.attack(target))

        self._issue_actions(actions)

    def _micro_queen(self, queen, friendly_units: Iterable, actions: List) -> bool:
        """Queen Transfuse logic."""
        if not hasattr(self.bot, "abilities"):
            return False

        transfuse_id = getattr(self.bot.abilities, "TRANSFUSION_TRANSFUSION", None)
        if not transfuse_id:
            return False

        if queen.energy < 50:
            return False

        # Find injured biological unit/structure nearby
        low_hp_units = [
            u
            for u in friendly_units
            if u.is_biological
            and u.health_percentage < 0.4
            and u.distance_to(queen) < 7
        ]

        if low_hp_units:
            # Heal the most injured one
            target = min(low_hp_units, key=lambda u: u.health)
            actions.append(queen(transfuse_id, target))
            return True

        return False

    def _micro_zergling(self, zergling, enemy_units: Iterable, actions: List) -> bool:
        """
        Zergling Surround Logic - maximize attack surface by surrounding enemies.

        Enhanced Strategy (LOGIC_AUDIT_REPORT v2):
        - Front zerglings attack directly
        - Rear zerglings move to enemy's back/sides in circular pattern
        - Creates 360-degree surround for maximum DPS
        - Prevents wasted DPS from zerglings stuck behind
        """
        if not enemy_units:
            return False

        # Find closest enemy
        target = self._closest_enemy(zergling, enemy_units)
        if not target:
            return False

        distance = zergling.distance_to(target)

        # If close enough to engage (within 3 range)
        if distance < 3.0:
            # * Phase 22: Use closer_than() instead of manual loop *
            all_units = getattr(self.bot, "units", [])
            if hasattr(all_units, "closer_than"):
                nearby_allies = all_units.of_type(UnitTypeId.ZERGLING).closer_than(
                    2.0, target.position
                )
                nearby_allies = [u for u in nearby_allies if u.tag != zergling.tag]
            else:
                nearby_allies = [
                    u
                    for u in all_units
                    if u.type_id == UnitTypeId.ZERGLING
                    and u.distance_to(target) < 2.0
                    and u.tag != zergling.tag
                ]

            # If 2+ allies already engaging, create circular surround instead of stacking
            # OPTIMIZED: 4 -> 2 (more aggressive surround)
            if len(nearby_allies) >= 2:
                # * Enhanced Surround: Calculate optimal surround position *
                import math

                # Calculate angle based on zergling's position relative to target
                dx = zergling.position.x - target.position.x
                dy = zergling.position.y - target.position.y
                current_angle = math.atan2(dy, dx)

                # Distribute units evenly around target (360 degrees)
                # Add offset to create spiral surround pattern
                angle_offset = (zergling.tag % 8) * (
                    math.pi / 4
                )  # 8 positions around circle
                optimal_angle = current_angle + angle_offset

                # Calculate surround position (1.5 units from target center)
                surround_radius = 1.5
                surround_x = target.position.x + surround_radius * math.cos(
                    optimal_angle
                )
                surround_y = target.position.y + surround_radius * math.sin(
                    optimal_angle
                )

                try:
                    from sc2.position import Point2

                    surround_pos = Point2((surround_x, surround_y))
                    actions.append(zergling.move(surround_pos))
                    return True
                except (ImportError, AttributeError):
                    # Fallback: simple surround
                    surround_pos = target.position.towards(zergling.position, -2.0)
                    actions.append(zergling.move(surround_pos))
                    return True

        # Default: attack normally if not in surround scenario
        return False

    def _micro_baneling(self, baneling, enemy_units: Iterable, actions: List) -> bool:
        """
        * Phase 27: 바네링 자폭 최적화 *
        - 경장갑/밀집 타겟에 attack() (이전: move()로 이동만)
        - 클러스터 없으면 가장 가까운 적에 돌진
        """
        if not enemy_units:
            return False

        if hasattr(enemy_units, "closer_than"):
            nearby_enemies = enemy_units.closer_than(10, baneling.position)
        else:
            nearby_enemies = [e for e in enemy_units if e.distance_to(baneling) < 10]
        if not nearby_enemies:
            return False

        # 1. 경장갑(light) 우선 타겟 - 마린/저글링/일꾼 등
        light_targets = [e for e in nearby_enemies if getattr(e, "is_light", False)]

        if light_targets:
            # 밀집된 경장갑 클러스터 중심으로 돌진
            center = self._find_center_of_mass(light_targets)
            if center:
                actions.append(baneling.attack(center))
                return True
            # 클러스터 실패 시 가장 가까운 경장갑 직접 공격
            closest = min(light_targets, key=lambda e: e.distance_to(baneling))
            actions.append(baneling.attack(closest))
            return True

        # 2. 경장갑 없으면 가장 가까운 적 돌진 (낭비 방지: 3유닛 이상일 때만)
        if len(nearby_enemies) >= 3:
            center = self._find_center_of_mass(
                list(nearby_enemies)
                if not isinstance(nearby_enemies, list)
                else nearby_enemies
            )
            if center:
                actions.append(baneling.attack(center))
                return True

        # 3. 최후 수단: 가장 가까운 적 공격
        if hasattr(nearby_enemies, "closest_to"):
            closest = nearby_enemies.closest_to(baneling)
        else:
            closest = min(nearby_enemies, key=lambda e: e.distance_to(baneling))
        actions.append(baneling.attack(closest))
        return True

    def _micro_roach(self, roach, actions: List) -> bool:
        """
        Roach Burrow Heal Logic.
        If HP < 30% and Burrow researched, burrow to heal/de-aggro.
        """
        # Check if Burrow is researched
        if not self.bot.state.upgrades:
            return False

        burrow_upgrade = getattr(UpgradeId, "BURROW", None)
        if not burrow_upgrade or burrow_upgrade not in self.bot.state.upgrades:
            return False

        # If low HP, burrow
        if roach.health_percentage < 0.35:
            burrow_down = getattr(AbilityId, "BURROWDOWN_ROACH", None)
            if burrow_down:
                actions.append(roach(burrow_down))
                return True

        return False

    def _micro_roach_burrowed(self, roach, actions: List) -> bool:
        """
        Handle burrowed Roaches.
        If HP > 80%, unburrow to fight again.
        """
        # If high HP, unburrow
        if roach.health_percentage > 0.85:
            burrow_up = getattr(AbilityId, "BURROWUP_ROACH", None)
            if burrow_up:
                actions.append(roach(burrow_up))
                return True

        # Otherwise stay burrowed (healing)
        return True

    def harass_workers(self, units: Iterable, nearby_enemies: Iterable) -> None:
        """
        Smart Harassment Logic:
        1. Target workers specifically.
        2. Ignore combat units unless cornered.
        3. Retreat if health is low.
        """
        actions = []
        if not nearby_enemies:
            # No enemies nearby? Attack closest base or worker
            # This part is usually handled by the caller (finding a target position),
            # but if we are here, we just look for targets in vision.
            return

        enemy_workers = [
            e
            for e in nearby_enemies
            if getattr(e.type_id, "name", "") in ["SCV", "PROBE", "DRONE", "MULE"]
        ]

        enemy_combat = [
            e
            for e in nearby_enemies
            if getattr(e.type_id, "name", "")
            not in ["SCV", "PROBE", "DRONE", "MULE", "LARVA", "EGG"]
        ]

        for unit in units:
            # 1. Survival Check: Low HP -> Run away from combat units
            if unit.health_percentage < 0.3:
                threats = enemy_combat if enemy_combat else enemy_workers
                rep_x, rep_y = self.anti_splash.repulsion_vector(unit, threats)

                # If no specific repulsion, just run away from closest threat
                if not rep_x and not rep_y and threats:
                    closest_threat = self._closest_enemy(unit, threats)
                    if closest_threat:
                        move_target = unit.position.towards(closest_threat.position, -4)
                        actions.append(unit.move(move_target))
                        continue

                if rep_x or rep_y:
                    move_target = self._offset_position(unit, rep_x, rep_y)
                    if move_target:
                        actions.append(unit.move(move_target))
                        continue

            # 2. Worker Hunting
            if enemy_workers:
                target = self._closest_enemy(unit, enemy_workers)
                if target:
                    actions.append(unit.attack(target))
                    continue

            # 3. If no workers, fight back or run (Kiting logic)
            if enemy_combat:
                target = self._closest_enemy(unit, enemy_combat)
                if target:
                    # Simple optimization: Attack if close, otherwise maybe run?
                    # For now, just attack to clear way
                    actions.append(unit.attack(target))
            else:
                # No workers, no combat units... attack buildings?
                pass

        self._issue_actions(actions)

    def _find_center_of_mass(self, units) -> Optional[Point2]:
        if not units or not Point2:
            return None
        total_x = sum(u.position.x for u in units)
        total_y = sum(u.position.y for u in units)
        return Point2((total_x / len(units), total_y / len(units)))

    @staticmethod
    def _closest_enemy(unit, enemies: Iterable):
        closest = None
        closest_dist = None
        for enemy in enemies:
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                continue
            if closest_dist is None or dist < closest_dist:
                closest = enemy
                closest_dist = dist
        return closest

    @staticmethod
    def _offset_position(unit, dx: float, dy: float):
        if not Point2:
            return None
        try:
            return unit.position + Point2((dx, dy))
        except Exception:
            return None

    def _issue_actions(self, actions: List) -> None:
        if not actions:
            return
        for action in actions:
            try:
                result = self.bot.do(action)
                if asyncio.iscoroutine(result):
                    try:
                        asyncio.create_task(result)
                    except RuntimeError:
                        pass
            except Exception:
                continue
