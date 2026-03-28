#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intel Manager - lightweight information manager with update/on_step bridge.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class IntelManager:
    """Collects intel and bridges update() to on_step()."""

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 8
        self.enemy_race_name: Optional[str] = None
        self.enemy_main_base_location = None  # 추가

        # Enemy composition tracking
        self.enemy_army_supply = 0
        self.enemy_worker_count = 0
        self.enemy_base_count = 0
        self.enemy_tech_buildings = set()
        self.scouted_locations = set()

        # Threat tracking
        self._under_attack = False
        self._attack_position = None
        self._last_attack_time = 0.0
        self._threat_level = "none"  # none, light, medium, heavy, critical
        self._high_threat_units_detected = False

        # Enemy unit type counts
        self.enemy_unit_counts = {}

        # High threat unit types
        self._high_threat_types = {
            "SIEGETANK", "SIEGETANKSIEGED", "THOR", "BATTLECRUISER",
            "COLOSSUS", "DISRUPTOR", "IMMORTAL", "ARCHON",
            "ULTRALISK", "BROODLORD", "RAVAGER", "LURKER", "LURKERMP",
            "LIBERATOR", "LIBERATORAG", "WIDOWMINE", "HIGHTEMPLAR"
        }

        # ★ NEW: Hidden tech tracking (정찰로 확인해야 하는 위험 테크)
        self._hidden_tech_alerts = {
            "DARKSHRINE": "DT_INCOMING",
            "STARGATE": "AIR_INCOMING",
            "FUSIONCORE": "BC_INCOMING",
            "TEMPLARARCHIVE": "HT_INCOMING",
            "NYDUSNETWORK": "NYDUS_INCOMING",
            "FLEETBEACON": "CARRIER_INCOMING",
        }
        self._detected_tech_alerts: set = set()  # 이미 경고한 테크

        # Build pattern confidence tracking
        self._build_pattern_confidence = 0.0  # 0.0 ~ 1.0
        self._build_pattern_status = "unknown"  # "unknown", "suspected", "confirmed"
        self._enemy_build_pattern = "unknown"
        self._recommended_response = []

        # ★ NEW: Destructible structures tracking
        self.destructible_rocks = []  # 파괴 가능한 중립 구조물
        self.all_enemy_structures = []  # 모든 적 구조물 (승리 조건용)
        self._last_structure_update = 0.0

    async def on_step(self, iteration: int) -> None:
        if iteration - self.last_update < self.update_interval:
            return
        self.last_update = iteration

        try:
            result = self.update(iteration)
            if asyncio.iscoroutine(result):
                await result
        except (AttributeError, TypeError) as e:
            logger.warning(f"[IntelManager] on_step suppressed: {e}")
            return
        except Exception as e:
            # Log unexpected errors
            if iteration % 50 == 0:
                print(f"[INTEL] Unexpected error in on_step: {type(e).__name__} - {e}")
            return

    def update(self, iteration: int) -> None:
        # Update enemy race
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race is None:
            self.enemy_race_name = None
        elif hasattr(enemy_race, "name"):
            self.enemy_race_name = str(enemy_race.name)
        else:
            self.enemy_race_name = str(enemy_race)

        # Update enemy unit composition
        self._update_enemy_composition()

        # Update threat status
        self._update_threat_status()

        # ★ NEW: Update destructible structures
        self._update_destructible_structures()

        # ★ NEW: Update all enemy structures
        self._update_all_enemy_structures()

    def _update_enemy_composition(self) -> None:
        """Track enemy army composition."""
        enemy_units = getattr(self.bot, "enemy_units", [])
        enemy_structures = getattr(self.bot, "enemy_structures", [])

        # ★ Update enemy main base location ★
        self._update_enemy_main_base(enemy_structures)

        # Count enemy units by type
        self.enemy_unit_counts = {}
        self.enemy_army_supply = 0
        self.enemy_worker_count = 0

        # ★ Phase 42: supply_cost 속성 없음 — 정확한 룩업 테이블 사용
        _ENEMY_SUPPLY = {
            'ZERGLING': 0.5, 'BANELING': 0.5, 'ROACH': 2, 'RAVAGER': 3,
            'HYDRALISK': 2, 'LURKERMP': 3, 'MUTALISK': 2, 'CORRUPTOR': 2,
            'ULTRALISK': 6, 'BROODLORD': 4, 'INFESTOR': 2, 'VIPER': 3,
            'MARINE': 1, 'MARAUDER': 2, 'REAPER': 1, 'GHOST': 2,
            'HELLION': 2, 'HELLIONTANK': 2, 'SIEGETANK': 3, 'SIEGETANKSIEGED': 3,
            'THOR': 6, 'BATTLECRUISER': 6, 'VIKING': 2, 'MEDIVAC': 2,
            'BANSHEE': 3, 'RAVEN': 2, 'LIBERATOR': 3, 'CYCLONE': 3,
            'ZEALOT': 2, 'STALKER': 2, 'ADEPT': 2, 'IMMORTAL': 4,
            'COLOSSUS': 6, 'DISRUPTOR': 3, 'ARCHON': 4, 'HIGHTEMPLAR': 2,
            'DARKTEMPLAR': 2, 'PHOENIX': 2, 'VOIDRAY': 4, 'CARRIER': 6,
            'ORACLE': 3, 'TEMPEST': 4,
        }
        worker_names = {'SCV', 'PROBE', 'DRONE'}
        for unit in enemy_units:
            type_name = getattr(unit.type_id, "name", str(unit.type_id))
            self.enemy_unit_counts[type_name] = self.enemy_unit_counts.get(type_name, 0) + 1

            # ★ Phase 42: 룩업 테이블 우선, 없으면 1
            supply = _ENEMY_SUPPLY.get(type_name.upper(), 1)
            if type_name.upper() in worker_names:
                self.enemy_worker_count += 1
            else:
                self.enemy_army_supply += supply

        # Count enemy bases
        base_types = {'COMMANDCENTER', 'COMMANDCENTERFLYING', 'ORBITALCOMMAND',
                     'ORBITALCOMMANDFLYING', 'PLANETARYFORTRESS',
                     'NEXUS', 'HATCHERY', 'LAIR', 'HIVE'}
        self.enemy_base_count = sum(
            1 for s in enemy_structures
            if getattr(s.type_id, "name", "").upper() in base_types
        )

        # Track tech buildings with detailed categorization
        tech_buildings = {'FACTORY', 'STARPORT', 'ARMORY', 'FUSIONCORE',
                         'ROBOTICSFACILITY', 'STARGATE', 'DARKSHRINE',
                         'TEMPLARARCHIVE', 'FLEETBEACON', 'TWILIGHTCOUNCIL',
                         'SPIRE', 'GREATERSPIRE', 'INFESTATIONPIT',
                         'BANELINGNEST', 'ROACHWARREN', 'HYDRALISKDEN',
                         'NYDUSNETWORK', 'NYDUSCANAL'}
        self.enemy_tech_buildings = {
            getattr(s.type_id, "name", "").upper()
            for s in enemy_structures
            if getattr(s.type_id, "name", "").upper() in tech_buildings
        }

        # ★ NEW: Hidden tech alert system
        self._check_hidden_tech_alerts()

        # Detect enemy build pattern
        self._detect_enemy_build_pattern(enemy_structures, enemy_units)

        # ★ Phase 20: 적 확장/테크 상태 → Blackboard 전파 (공격 타이밍용) ★
        self._detect_enemy_vulnerability(enemy_structures)

        # ★ Phase 42: 적 공격 타이밍 예측 → Blackboard 전파 ★
        self._predict_enemy_attack_timing()

    def _update_enemy_main_base(self, enemy_structures) -> None:
        """
        Update enemy main base location from visible structures or start locations.

        Priority:
        1. Visible enemy townhalls (closest to known start location)
        2. bot.enemy_start_locations[0] as fallback
        """
        base_types = {'COMMANDCENTER', 'COMMANDCENTERFLYING', 'ORBITALCOMMAND',
                      'ORBITALCOMMANDFLYING', 'PLANETARYFORTRESS',
                      'NEXUS', 'HATCHERY', 'LAIR', 'HIVE'}

        # Try to find from visible enemy structures
        enemy_bases = []
        for s in enemy_structures:
            try:
                type_name = getattr(s.type_id, "name", "").upper()
                if type_name in base_types:
                    enemy_bases.append(s)
            except (AttributeError, TypeError) as e:
                logger.warning(f"[IntelManager] Enemy base detection suppressed: {e}")
                continue

        if enemy_bases:
            # Use the enemy base closest to their start location
            start_locs = getattr(self.bot, "enemy_start_locations", [])
            if start_locs:
                ref = start_locs[0]
                closest = min(enemy_bases, key=lambda b: b.distance_to(ref))
                self.enemy_main_base_location = closest.position
            else:
                self.enemy_main_base_location = enemy_bases[0].position
        elif self.enemy_main_base_location is None:
            # Fallback: use enemy start location
            start_locs = getattr(self.bot, "enemy_start_locations", [])
            if start_locs:
                self.enemy_main_base_location = start_locs[0]

    def _update_threat_status(self) -> None:
        """Check if we're under attack with improved detection."""
        enemy_units = getattr(self.bot, "enemy_units", [])
        townhalls = getattr(self.bot, "townhalls", [])

        if not townhalls:
            self._under_attack = False
            return

        current_time = getattr(self.bot, "time", 0.0)

        # ★ 캐시 사용 (1초 TTL) ★
        if hasattr(self.bot, "data_cache") and self.bot.data_cache:
            cached_threat = self.bot.data_cache.get_threat_level()
            if cached_threat:
                self._threat_level = cached_threat.lower()

        # High-threat unit types (detect earlier)
        high_threat_units = {
            'ZERGLING', 'MARINE', 'ZEALOT', 'REAPER', 'ADEPT',
            'BANELING', 'ROACH', 'STALKER', 'MARAUDER',
            'SIEGETANK', 'SIEGETANKSIEGED', 'LIBERATOR', 'WIDOWMINE'
        }

        # ★ O(n) 최적화: 적 유닛 1회 순회, 타운홀 위치 캐시 ★
        th_positions = [th.position for th in townhalls]
        base_detection_range = 40 if current_time < 180 else 30
        found_critical = False

        for enemy in enemy_units:
            try:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                detection_range = base_detection_range if current_time < 180 else (
                    35 if enemy_type in high_threat_units else 30
                )

                near_base = any(
                    enemy.distance_to(pos) < detection_range for pos in th_positions
                )
                if not near_base:
                    continue

                self._under_attack = True
                self._attack_position = enemy.position
                self._last_attack_time = current_time

                if enemy_type in self._high_threat_types:
                    self._high_threat_units_detected = True
                    self._threat_level = "critical"
                    found_critical = True
                elif not found_critical and self._threat_level not in ["critical", "heavy"]:
                    self._threat_level = "medium"

                if current_time < 180 and self.bot.iteration % 100 == 0:
                    print(f"[INTEL] [{int(current_time)}s] EARLY ATTACK: {enemy_type} detected!")

            except (AttributeError, TypeError) as e:
                logger.warning(f"[IntelManager] Threat detection suppressed: {e}")
                continue

        # Clear attack flag after 10 seconds of no enemies
        if current_time - self._last_attack_time > 10:
            self._under_attack = False
            self._attack_position = None
            self._threat_level = "none"
            self._high_threat_units_detected = False

    def is_under_attack(self) -> bool:
        """Check if any base is under attack."""
        return self._under_attack

    def get_attack_position(self):
        """Get position where attack is happening."""
        return self._attack_position

    def get_enemy_army_supply(self) -> int:
        """Get estimated enemy army supply."""
        return self.enemy_army_supply

    def get_enemy_composition(self) -> dict:
        """Get enemy unit type counts."""
        return self.enemy_unit_counts.copy()

    def has_enemy_tech(self, tech_name: str) -> bool:
        """Check if enemy has specific tech building."""
        return tech_name.upper() in self.enemy_tech_buildings

    def get_threat_level(self) -> str:
        """Get current threat level: none, light, medium, heavy, critical."""
        return self._threat_level

    def has_high_threat_units(self) -> bool:
        """Check if high-threat units (Siege Tanks, Colossi, etc.) are detected."""
        return self._high_threat_units_detected

    def is_major_attack(self) -> bool:
        """Check if this is a major attack (critical threat level or high-threat units)."""
        return self._threat_level == "critical" or self._high_threat_units_detected

    def _predict_enemy_attack_timing(self) -> None:
        """
        ★ Phase 42: 적 테크 건물 기반 공격 타이밍 예측 ★

        관측된 테크 건물 → 예상 공격 시점(초) 추정 → Blackboard 전파
        전략 매니저가 이를 읽어 방어 준비 타이밍 조정.

        예측 규칙 (보수적 하한 추정):
          FACTORY / BARRACKS 기반 → 3:30 공격 가능
          STARGATE / STARPORT   → 4:00 공격 가능
          ROBOTICSFACILITY      → 5:00 공격 가능 (Immortal/Colossus)
          DARKSHRINE            → 4:30 공격 가능 (DT)
          적 supply > 20        → 현재 ~ +60초 내 공격 가능
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard or not hasattr(blackboard, "set"):
            return

        game_time = getattr(self.bot, "time", 0)
        tech = self.enemy_tech_buildings  # already computed set of string names

        predicted_attack_time: float = 999.0  # 기본: 매우 늦음 (예측 불가)

        # 테크 건물 기반 하한 추정
        if 'DARKSHRINE' in tech:
            predicted_attack_time = min(predicted_attack_time, 270.0)  # 4:30
        if 'STARGATE' in tech or 'STARPORT' in tech:
            predicted_attack_time = min(predicted_attack_time, 240.0)  # 4:00
        if 'FACTORY' in tech:
            predicted_attack_time = min(predicted_attack_time, 210.0)  # 3:30
        if 'ROBOTICSFACILITY' in tech:
            predicted_attack_time = min(predicted_attack_time, 300.0)  # 5:00

        # 적 병력 규모 기반: supply > 20이면 60초 내 공격 가능
        if self.enemy_army_supply > 20:
            predicted_attack_time = min(predicted_attack_time, game_time + 60.0)

        # 적 병력 규모 기반: supply > 40이면 30초 내 공격 가능
        if self.enemy_army_supply > 40:
            predicted_attack_time = min(predicted_attack_time, game_time + 30.0)

        # 이미 예측 시점이 지났으면 임박
        imminent = predicted_attack_time <= game_time + 30.0

        blackboard.set("enemy_attack_predicted_time", predicted_attack_time)
        blackboard.set("enemy_attack_imminent", imminent)

        if imminent and game_time % 30 < 1:  # 30초마다 로그
            logger.info(
                f"[INTEL] [{int(game_time)}s] ★ ENEMY ATTACK IMMINENT "
                f"(predicted: {int(predicted_attack_time)}s, supply: {self.enemy_army_supply:.0f})"
            )

    def _detect_enemy_vulnerability(self, enemy_structures) -> None:
        """
        ★ Phase 20: 적 확장/테크 취약 시점 감지 ★

        적이 확장 중이거나 고비용 테크를 올리는 중이면
        Blackboard에 플래그를 세워 공격 타이밍으로 활용.
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard or not hasattr(blackboard, "set"):
            return

        # 적 건설 중인 건물 확인
        expanding = False
        teching = False

        base_types = {'COMMANDCENTER', 'NEXUS', 'HATCHERY'}
        expensive_tech = {'STARPORT', 'ROBOTICSFACILITY', 'STARGATE',
                         'DARKSHRINE', 'FLEETBEACON', 'FUSIONCORE',
                         'GREATERSPIRE', 'NYDUSNETWORK'}

        for struct in enemy_structures:
            type_name = getattr(struct.type_id, "name", "").upper()
            build_progress = getattr(struct, "build_progress", 1.0)

            if build_progress < 1.0:  # 건설 중
                if type_name in base_types:
                    expanding = True
                if type_name in expensive_tech:
                    teching = True

        blackboard.set("enemy_expanding", expanding)
        blackboard.set("enemy_teching", teching)

    def _detect_enemy_build_pattern(self, enemy_structures, enemy_units) -> None:
        """
        Detect enemy build pattern based on tech buildings and units.

        Patterns:
        - Terran: Bio (Barracks), Mech (Factory), Air (Starport)
        - Protoss: Gateway, Robo, Stargate
        - Zerg: Pool first, Hatch first, Ling/Bane, Roach/Hydra
        """
        game_time = getattr(self.bot, "time", 0)

        # Count structures by type
        structure_counts = {}
        for s in enemy_structures:
            name = getattr(s.type_id, "name", "").upper()
            structure_counts[name] = structure_counts.get(name, 0) + 1

        # Detect pattern
        detected_pattern = "unknown"
        recommended_response = []

        # === TERRAN DETECTION ===
        if "BARRACKS" in structure_counts:
            barracks_count = structure_counts.get("BARRACKS", 0)
            factory_count = structure_counts.get("FACTORY", 0)
            starport_count = structure_counts.get("STARPORT", 0)

            if starport_count >= 1 and factory_count >= 1:
                # Mech or BC rush
                detected_pattern = "terran_mech"
                recommended_response = ["hydralisk", "corruptor", "viper"]
            elif barracks_count >= 3:
                # Bio (Marine/Marauder/Medivac)
                detected_pattern = "terran_bio"
                recommended_response = ["baneling", "zergling", "ultralisk"]
            elif factory_count >= 2:
                # Tank/Hellion
                detected_pattern = "terran_factory"
                recommended_response = ["mutalisk", "ravager", "swarmhost"]

            # Early aggression detection
            if barracks_count >= 2 and game_time < 180:
                detected_pattern = "terran_rush"
                recommended_response = ["zergling", "spine_crawler", "queen"]

        # === PROTOSS DETECTION ===
        elif "GATEWAY" in structure_counts or "NEXUS" in structure_counts:
            gateway_count = structure_counts.get("GATEWAY", 0)
            robo_count = structure_counts.get("ROBOTICSFACILITY", 0)
            stargate_count = structure_counts.get("STARGATE", 0)
            twilight = "TWILIGHTCOUNCIL" in structure_counts

            if stargate_count >= 1:
                # Stargate (Oracle, Void Ray, Carrier)
                detected_pattern = "protoss_stargate"
                recommended_response = ["hydralisk", "corruptor", "spore_crawler"]
            elif robo_count >= 1:
                # Robo (Immortal, Colossus)
                detected_pattern = "protoss_robo"
                recommended_response = ["hydralisk", "roach", "corruptor"]
            elif twilight:
                # Twilight (Blink Stalker, Charge Zealot)
                detected_pattern = "protoss_twilight"
                recommended_response = ["roach", "hydralisk", "lurker"]
            elif gateway_count >= 3:
                # Gateway all-in
                detected_pattern = "protoss_gateway"
                recommended_response = ["roach", "zergling", "spine_crawler"]

            # Proxy detection
            if gateway_count >= 1 and game_time < 150:
                detected_pattern = "protoss_proxy"
                recommended_response = ["zergling", "spine_crawler", "queen"]

        # === ZERG DETECTION ===
        elif "SPAWNINGPOOL" in structure_counts or "HATCHERY" in structure_counts:
            baneling_nest = "BANELINGNEST" in structure_counts
            roach_warren = "ROACHWARREN" in structure_counts
            spire = "SPIRE" in structure_counts or "GREATERSPIRE" in structure_counts

            if spire:
                detected_pattern = "zerg_muta"
                recommended_response = ["hydralisk", "spore_crawler", "queen"]
            elif roach_warren and not baneling_nest:
                detected_pattern = "zerg_roach"
                recommended_response = ["roach", "ravager", "hydralisk"]
            elif baneling_nest:
                detected_pattern = "zerg_ling_bane"
                recommended_response = ["baneling", "zergling", "roach"]

            # 12 pool detection
            pool_count = structure_counts.get("SPAWNINGPOOL", 0)
            hatch_count = structure_counts.get("HATCHERY", 0) + structure_counts.get("LAIR", 0) + structure_counts.get("HIVE", 0)
            if pool_count >= 1 and hatch_count <= 1 and game_time < 120:
                detected_pattern = "zerg_12pool"
                recommended_response = ["zergling", "spine_crawler", "queen"]

        # Store detected pattern
        self._enemy_build_pattern = detected_pattern
        self._recommended_response = recommended_response

        # ★ Calculate confidence score ★
        self._build_pattern_confidence = self._calculate_build_confidence(
            detected_pattern, structure_counts, enemy_units, game_time
        )

        # ★ Determine confidence status ★
        if self._build_pattern_confidence >= 0.7:
            self._build_pattern_status = "confirmed"
        elif self._build_pattern_confidence >= 0.3:
            self._build_pattern_status = "suspected"
        else:
            self._build_pattern_status = "unknown"

        # ★ Push to Blackboard ★
        self._push_intel_to_blackboard(detected_pattern)

        # Log detection (every 30 seconds)
        if game_time > 0 and int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
            if detected_pattern != "unknown":
                confidence_pct = int(self._build_pattern_confidence * 100)
                print(f"[INTEL] [{int(game_time)}s] Enemy build: {detected_pattern} ({self._build_pattern_status}, {confidence_pct}%)")
                print(f"[INTEL] Recommended counter: {recommended_response}")

    def _calculate_build_confidence(self, pattern: str, structure_counts: dict,
                                    enemy_units, game_time: float) -> float:
        """
        Calculate confidence score for detected build pattern.

        Factors:
        - Number of tech buildings (more = higher confidence)
        - Number of related units (more = higher confidence)
        - Game time (later = higher confidence)
        - Pattern specificity (specific patterns = higher confidence)

        Returns:
            float: Confidence score (0.0 ~ 1.0)
        """
        if pattern == "unknown":
            return 0.0

        confidence = 0.0

        # Factor 1: Tech building count (0 ~ 0.4)
        tech_building_count = sum(
            1 for name in structure_counts.keys()
            if name in self.enemy_tech_buildings
        )
        confidence += min(tech_building_count * 0.15, 0.4)

        # Factor 2: Related unit count (0 ~ 0.3)
        related_unit_patterns = {
            "terran_bio": ["MARINE", "MARAUDER", "MEDIVAC"],
            "terran_mech": ["SIEGETANK", "HELLION", "THOR", "CYCLONE"],
            "terran_factory": ["SIEGETANK", "HELLION"],
            "protoss_stargate": ["PHOENIX", "VOIDRAY", "ORACLE", "CARRIER"],
            "protoss_robo": ["IMMORTAL", "COLOSSUS", "OBSERVER"],
            "protoss_gateway": ["ZEALOT", "STALKER", "ADEPT"],
            "zerg_muta": ["MUTALISK", "CORRUPTOR"],
            "zerg_roach": ["ROACH", "RAVAGER"],
            "zerg_ling_bane": ["ZERGLING", "BANELING"],
        }

        pattern_units = related_unit_patterns.get(pattern, [])
        related_unit_count = sum(
            self.enemy_unit_counts.get(unit_type, 0)
            for unit_type in pattern_units
        )
        confidence += min(related_unit_count * 0.03, 0.3)

        # Factor 3: Game time progression (0 ~ 0.2)
        # More time = more confidence (up to 5 minutes)
        time_factor = min(game_time / 300.0, 1.0) * 0.2
        confidence += time_factor

        # Factor 4: Rush pattern bonus (early aggression = high confidence)
        if "rush" in pattern or "proxy" in pattern or "12pool" in pattern:
            if game_time < 180:  # First 3 minutes
                confidence += 0.2  # High confidence for early aggression

        # Cap at 1.0
        return min(confidence, 1.0)

    def get_enemy_build_pattern(self) -> str:
        """Get detected enemy build pattern."""
        return getattr(self, "_enemy_build_pattern", "unknown")

    def get_recommended_response(self) -> list:
        """Get recommended unit composition to counter enemy build."""
        return getattr(self, "_recommended_response", [])

    def get_build_pattern_confidence(self) -> float:
        """
        Get confidence score for detected build pattern.

        Returns:
            float: Confidence score (0.0 ~ 1.0)
        """
        return self._build_pattern_confidence

    def get_build_pattern_status(self) -> str:
        """
        Get build pattern detection status.

        Returns:
            str: "unknown", "suspected", or "confirmed"
        """
        return self._build_pattern_status

    def is_build_pattern_confirmed(self) -> bool:
        """
        Check if build pattern is confirmed (confidence >= 0.7).

        Returns:
            bool: True if confirmed
        """
        return self._build_pattern_status == "confirmed"

    def _push_intel_to_blackboard(self, detected_pattern: str) -> None:
        """
        Push intelligence data to Blackboard for other systems to use.

        Args:
            detected_pattern: Detected enemy build pattern
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard:
            return

        try:
            # Push build pattern info
            blackboard.set("enemy_build_pattern", detected_pattern)
            blackboard.set("enemy_build_confidence", self._build_pattern_confidence)
            blackboard.set("enemy_build_status", self._build_pattern_status)

            # Push recommended response
            blackboard.set("recommended_counter_units", self._recommended_response)

            # Push threat info
            blackboard.set("under_attack", self._under_attack)
            blackboard.set("threat_level", self._threat_level)
            blackboard.set("has_high_threat_units", self._high_threat_units_detected)

            # Push composition info
            blackboard.set("enemy_army_supply", self.enemy_army_supply)
            blackboard.set("enemy_base_count", self.enemy_base_count)
            blackboard.set("enemy_worker_count", self.enemy_worker_count)

        except (AttributeError, TypeError) as e:
            logger.warning(f"[IntelManager] Blackboard update suppressed: {e}")

    def _check_hidden_tech_alerts(self) -> None:
        """
        ★ NEW: 위험 테크 건물 발견 시 즉시 경고 + Blackboard 알림

        DarkShrine → 스포어 크롤러 + 오버시어 필요
        Stargate → 스포어 크롤러 + 퀸/히드라 필요
        FusionCore → BC 대비 코럽터/히드라 필요
        """
        game_time = getattr(self.bot, "time", 0.0)

        for tech_name, alert_type in self._hidden_tech_alerts.items():
            if tech_name in self.enemy_tech_buildings and alert_type not in self._detected_tech_alerts:
                self._detected_tech_alerts.add(alert_type)
                print(f"[INTEL] [{int(game_time)}s] ★★★ ALERT: {tech_name} detected! → {alert_type} ★★★")

                # Push to Blackboard
                blackboard = getattr(self.bot, "blackboard", None)
                if blackboard:
                    blackboard.set(f"alert_{alert_type.lower()}", True)
                    blackboard.set("latest_tech_alert", alert_type)
                    blackboard.set("latest_tech_alert_time", game_time)

                    # ★ Phase 17: 위협 테크 감지 시 즉시 방어 플래그 설정 ★
                    if alert_type in ("DT_INCOMING", "AIR_INCOMING", "BC_INCOMING", "CARRIER_INCOMING"):
                        blackboard.set("urgent_spore_all_bases", True)
                    if alert_type == "NYDUS_INCOMING":
                        blackboard.set("urgent_spine_all_bases", True)

    def get_tech_alerts(self) -> set:
        """현재까지 감지된 테크 경고 목록 반환."""
        return self._detected_tech_alerts.copy()

    def has_tech_alert(self, alert_type: str) -> bool:
        """특정 테크 경고가 발생했는지 확인."""
        return alert_type in self._detected_tech_alerts

    def record_scouted_location(self, location) -> None:
        """Record a location that has been scouted."""
        self.scouted_locations.add(location)

    def _update_destructible_structures(self) -> None:
        """
        ★ NEW: 파괴 가능한 중립 구조물 감지

        Destructible Rocks, Debris 등 확장 경로를 막는 구조물 추적
        """
        try:
            current_time = getattr(self.bot, "time", 0.0)

            # 5초마다 업데이트
            if current_time - self._last_structure_update < 5.0:
                return

            self._last_structure_update = current_time

            # 파괴 가능한 구조물 타입
            destructible_types = {
                "DESTRUCTIBLEROCK6X6", "DESTRUCTIBLEROCKSVERTICAL",
                "DESTRUCTIBLEROCKSHORIZONTAL", "DESTRUCTIBLEDEBRIS6X6",
                "DESTRUCTIBLEDEBRISRAMPLEFT", "DESTRUCTIBLEDEBRISRAMPRIGHT"
            }

            # 모든 중립 유닛에서 파괴 가능한 구조물 찾기
            destructible_list = []
            all_units = getattr(self.bot, "all_units", [])

            for unit in all_units:
                try:
                    # 적군도 아니고 아군도 아닌 유닛 = 중립
                    if not hasattr(unit, "is_mine") or unit.is_mine:
                        continue
                    if not hasattr(unit, "is_enemy") or unit.is_enemy:
                        continue

                    type_name = getattr(unit.type_id, "name", "").upper()

                    # 파괴 가능한 구조물인지 확인
                    if any(dest_type in type_name for dest_type in destructible_types):
                        destructible_list.append(unit)
                except (AttributeError, TypeError) as e:
                    logger.warning(f"[IntelManager] Destructible unit check suppressed: {e}")
                    continue

            self.destructible_rocks = destructible_list

            # 로그 (처음 발견 시만)
            if destructible_list and current_time < 60 and self.bot.iteration % 100 == 0:
                print(f"[INTEL] [{int(current_time)}s] ★ {len(destructible_list)} destructible rocks detected!")

        except (AttributeError, TypeError) as e:
            logger.warning(f"[IntelManager] Destructible structure scan suppressed: {e}")

    def _update_all_enemy_structures(self) -> None:
        """
        ★ NEW: 모든 적 구조물 추적 (승리 조건용)

        모든 적 건물을 파괴해야 승리할 수 있음
        """
        try:
            enemy_structures = getattr(self.bot, "enemy_structures", [])
            self.all_enemy_structures = list(enemy_structures)

            current_time = getattr(self.bot, "time", 0.0)

            # 10초마다 적 구조물 수 로그
            if int(current_time) % 30 == 0 and self.bot.iteration % 22 == 0:
                if len(self.all_enemy_structures) > 0:
                    print(f"[INTEL] [{int(current_time)}s] Enemy structures remaining: {len(self.all_enemy_structures)}")
        except (AttributeError, TypeError) as e:
            logger.warning(f"[IntelManager] Enemy structure tracking suppressed: {e}")

    def get_destructible_rocks(self) -> list:
        """파괴 가능한 중립 구조물 목록 반환."""
        return self.destructible_rocks.copy()

    def get_closest_destructible_rock(self, position):
        """주어진 위치에서 가장 가까운 파괴 가능한 구조물 반환."""
        if not self.destructible_rocks:
            return None

        try:
            return min(self.destructible_rocks, key=lambda rock: rock.distance_to(position))
        except Exception as e:
            logger.warning(f"[IntelManager] Closest destructible rock suppressed: {e}")
            return None

    def get_all_enemy_structures(self) -> list:
        """모든 적 구조물 목록 반환 (승리 조건용)."""
        return self.all_enemy_structures.copy()

    def get_enemy_structure_count(self) -> int:
        """남은 적 구조물 수 반환."""
        return len(self.all_enemy_structures)

    # ==========================================================
    # ★ NEW: Data Backup System (데이터 백업 및 복구) ★
    # ==========================================================

    def save_data(self, file_path: str = "data/intel_data.json") -> bool:
        """
        현재 수집된 인텔 데이터를 JSON 파일로 저장합니다.

        Args:
            file_path: 저장할 파일 경로

        Returns:
            bool: 성공 여부
        """
        import json
        import os

        try:
            # 디렉토리 생성
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # 데이터 직렬화
            data = {
                "enemy_race_name": self.enemy_race_name,
                "enemy_unit_counts": self.enemy_unit_counts,
                "enemy_tech_buildings": list(self.enemy_tech_buildings),  # set -> list
                "scouted_locations": [
                    (loc.x, loc.y) for loc in self.scouted_locations
                ],  # Point2 -> tuple
                "enemy_build_pattern": getattr(self, "_enemy_build_pattern", "unknown"),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            print(f"[INTEL] Data saved to {file_path}")
            return True

        except (IOError, OSError) as e:
            print(f"[INTEL] Failed to save data (I/O error): {e}")
            return False
        except (TypeError, ValueError) as e:
            print(f"[INTEL] Failed to save data (serialization error): {e}")
            return False

    def load_data(self, file_path: str = "data/intel_data.json") -> bool:
        """
        JSON 파일에서 인텔 데이터를 불러와 복구합니다.

        Args:
            file_path: 불러올 파일 경로

        Returns:
            bool: 성공 여부
        """
        import json
        import os
        from sc2.position import Point2

        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 데이터 복원
            self.enemy_race_name = data.get("enemy_race_name")
            self.enemy_unit_counts = data.get("enemy_unit_counts", {})
            self.enemy_tech_buildings = set(data.get("enemy_tech_buildings", []))
            self._enemy_build_pattern = data.get("enemy_build_pattern", "unknown")

            # Scouted Locations 복원 (tuple -> Point2)
            scouted = data.get("scouted_locations", [])
            self.scouted_locations = {Point2(loc) for loc in scouted}
            
            print(f"[INTEL] Data loaded from {file_path}")
            print(f"  - Enemy Race: {self.enemy_race_name}")
            print(f"  - Build Pattern: {self._enemy_build_pattern}")
            print(f"  - Scouted Locations: {len(self.scouted_locations)}")
            
            return True

        except (IOError, OSError) as e:
            print(f"[INTEL] Failed to load data (I/O error): {e}")
            return False
        except (TypeError, ValueError, KeyError) as e:
            print(f"[INTEL] Failed to load data (parsing error): {e}")
            return False
