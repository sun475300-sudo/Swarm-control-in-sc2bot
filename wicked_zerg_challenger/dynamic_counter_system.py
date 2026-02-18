# -*- coding: utf-8 -*-
"""
Dynamic Counter System - 적 고급 유닛 감지 시 즉시 카운터 유닛 생산

IntelManager가 전투순양함, 거신 등을 발견하면
StrategyManager가 즉시 반응하여 카운터 유닛(타락귀, 히드라) 생산을 강제합니다.
"""

from typing import Dict, Set, List, Tuple
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        # Terran Threats
        BATTLECRUISER = "BATTLECRUISER"
        THOR = "THOR"
        SIEGETANK = "SIEGETANK"
        SIEGETANKSIEGED = "SIEGETANKSIEGED"
        LIBERATOR = "LIBERATOR"
        WIDOWMINE = "WIDOWMINE"

        # Protoss Threats
        CARRIER = "CARRIER"
        TEMPEST = "TEMPEST"
        VOIDRAY = "VOIDRAY"
        COLOSSUS = "COLOSSUS"
        DISRUPTOR = "DISRUPTOR"
        IMMORTAL = "IMMORTAL"
        ARCHON = "ARCHON"
        HIGHTEMPLAR = "HIGHTEMPLAR"

        # Zerg Threats
        BROODLORD = "BROODLORD"
        ULTRALISK = "ULTRALISK"
        LURKER = "LURKER"
        LURKERMP = "LURKERMP"

        # Counter Units
        CORRUPTOR = "CORRUPTOR"
        HYDRALISK = "HYDRALISK"
        ROACH = "ROACH"
        RAVAGER = "RAVAGER"
        QUEEN = "QUEEN"


class DynamicCounterSystem:
    """
    ★ Dynamic Counter System ★

    IntelManager의 적 유닛 정보를 실시간 분석하여
    위협 유닛 발견 시 즉시 카운터 유닛 생산을 강제합니다.
    """

    def __init__(self, bot, intel_manager=None):
        self.bot = bot
        self.intel = intel_manager or getattr(bot, "intel", None)
        self.logger = get_logger("DynamicCounter")

        # ★ 체크 주기 ★
        self.last_check = 0
        self.check_interval = 33  # 약 1.5초마다

        # ★ 감지된 위협 ★
        self.detected_threats: Set[str] = set()
        self.threat_first_seen: Dict[str, float] = {}
        self.active_counters: Dict[str, Dict] = {}  # {threat: counter_info}

        # ★ 카운터 룰 ★
        self.counter_rules = {
            # ===== Terran Threats =====
            "BATTLECRUISER": {
                "threat_value": 100,
                "counter_units": ["corruptor", "queen"],
                "counter_ratios": [0.70, 0.30],
                "min_count": 8,  # 최소 8 타락귀
                "urgency": "CRITICAL",
                "production_boost": 0.5,  # 생산량 50% 증가
            },
            "THOR": {
                "threat_value": 50,
                "counter_units": ["roach", "ravager"],
                "counter_ratios": [0.60, 0.40],
                "min_count": 8,
                "urgency": "HIGH",
                "production_boost": 0.3,
            },
            "SIEGETANK": {
                "threat_value": 40,
                "counter_units": ["roach", "ravager", "mutalisk"],
                "counter_ratios": [0.40, 0.30, 0.30],
                "min_count": 6,
                "urgency": "HIGH",
                "production_boost": 0.3,
            },
            "LIBERATOR": {
                "threat_value": 35,
                "counter_units": ["corruptor", "hydralisk"],
                "counter_ratios": [0.70, 0.30],
                "min_count": 6,
                "urgency": "MEDIUM",
                "production_boost": 0.2,
            },

            # ===== Protoss Threats =====
            "CARRIER": {
                "threat_value": 100,
                "counter_units": ["corruptor", "hydralisk"],
                "counter_ratios": [0.80, 0.20],
                "min_count": 10,
                "urgency": "CRITICAL",
                "production_boost": 0.6,
            },
            "VOIDRAY": {
                "threat_value": 40,
                "counter_units": ["corruptor", "hydralisk"],
                "counter_ratios": [0.60, 0.40],
                "min_count": 6,
                "urgency": "HIGH",
                "production_boost": 0.3,
            },
            "COLOSSUS": {
                "threat_value": 60,
                "counter_units": ["corruptor", "roach"],
                "counter_ratios": [0.70, 0.30],
                "min_count": 6,
                "urgency": "HIGH",
                "production_boost": 0.4,
            },
            "DISRUPTOR": {
                "threat_value": 50,
                "counter_units": ["roach", "hydralisk"],
                "counter_ratios": [0.50, 0.50],
                "min_count": 8,
                "urgency": "HIGH",
                "production_boost": 0.3,
            },
            "IMMORTAL": {
                "threat_value": 45,
                "counter_units": ["hydralisk", "zergling"],
                "counter_ratios": [0.70, 0.30],
                "min_count": 8,
                "urgency": "MEDIUM",
                "production_boost": 0.2,
            },
            "ARCHON": {
                "threat_value": 50,
                "counter_units": ["roach", "hydralisk"],
                "counter_ratios": [0.60, 0.40],
                "min_count": 8,
                "urgency": "HIGH",
                "production_boost": 0.3,
            },

            # ===== Zerg Threats =====
            "BROODLORD": {
                "threat_value": 80,
                "counter_units": ["corruptor", "hydralisk"],
                "counter_ratios": [0.80, 0.20],
                "min_count": 8,
                "urgency": "CRITICAL",
                "production_boost": 0.5,
            },
            "ULTRALISK": {
                "threat_value": 70,
                "counter_units": ["roach", "queen"],
                "counter_ratios": [0.80, 0.20],
                "min_count": 10,
                "urgency": "HIGH",
                "production_boost": 0.4,
            },
            "LURKER": {
                "threat_value": 55,
                "counter_units": ["roach", "hydralisk", "overseer"],
                "counter_ratios": [0.50, 0.40, 0.10],
                "min_count": 8,
                "urgency": "HIGH",
                "production_boost": 0.3,
            },
        }

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration - self.last_check < self.check_interval:
                return

            self.last_check = iteration

            if not self.intel:
                return

            # ★ 1. 적 고급 유닛 스캔 ★
            new_threats = await self._scan_enemy_threats()

            # ★ 2. 새 위협 감지 시 대응 ★
            if new_threats:
                await self._activate_counters(new_threats)

            # ★ 3. 활성 카운터 업데이트 ★
            await self._update_active_counters(iteration)

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[DYNAMIC_COUNTER] Error: {e}")

    async def _scan_enemy_threats(self) -> Set[str]:
        """
        적 고급 유닛 스캔

        Returns:
            새로 발견된 위협 유닛 집합
        """
        if not hasattr(self.bot, "enemy_units"):
            return set()

        enemy_units = getattr(self.bot, "enemy_units", [])
        current_threats = set()

        for enemy in enemy_units:
            type_name = getattr(enemy.type_id, "name", "").upper()

            # 위협 유닛 감지
            if type_name in self.counter_rules:
                current_threats.add(type_name)

                # 처음 발견된 위협
                if type_name not in self.detected_threats:
                    game_time = getattr(self.bot, "time", 0)
                    self.threat_first_seen[type_name] = game_time
                    self.detected_threats.add(type_name)

                    self.logger.warning(
                        f"[{int(game_time)}s] ★★★ HIGH THREAT DETECTED: {type_name} ★★★"
                    )

        # 새로 발견된 위협만 반환
        new_threats = current_threats - set(self.active_counters.keys())
        return new_threats

    async def _activate_counters(self, threats: Set[str]):
        """
        위협 유닛에 대한 카운터 활성화

        Args:
            threats: 새로 발견된 위협 유닛들
        """
        game_time = getattr(self.bot, "time", 0)

        for threat in threats:
            counter_rule = self.counter_rules.get(threat)
            if not counter_rule:
                continue

            # 카운터 활성화
            self.active_counters[threat] = {
                "rule": counter_rule,
                "activated_time": game_time,
                "units_produced": 0,
                "target_met": False,
            }

            self.logger.info(
                f"[{int(game_time)}s] ★ COUNTER ACTIVATED: {threat} ★\n"
                f"  Counter Units: {counter_rule['counter_units']}\n"
                f"  Min Count: {counter_rule['min_count']}\n"
                f"  Urgency: {counter_rule['urgency']}\n"
                f"  Production Boost: +{counter_rule['production_boost']*100:.0f}%"
            )

            # Blackboard에 카운터 명령 등록
            await self._register_counter_to_blackboard(threat, counter_rule)

    async def _register_counter_to_blackboard(self, threat: str, counter_rule: Dict):
        """
        Blackboard에 카운터 생산 명령 등록
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard:
            return

        # ★ 유닛 구성 오버라이드 ★
        current_override = blackboard.get("unit_composition_override", {})

        for unit_name, ratio in zip(counter_rule["counter_units"], counter_rule["counter_ratios"]):
            # 기존 비율에 boost 추가
            boost = ratio * counter_rule["production_boost"]
            current_override[unit_name] = current_override.get(unit_name, 0) + boost

        blackboard.set("unit_composition_override", current_override)
        blackboard.set("dynamic_counter_active", True)
        blackboard.set("active_counter_threat", threat)

        self.logger.info(f"[DYNAMIC_COUNTER] Registered to Blackboard: {current_override}")

    async def _update_active_counters(self, iteration: int):
        """
        활성 카운터 상태 업데이트
        """
        if not hasattr(self.bot, "units"):
            return

        game_time = getattr(self.bot, "time", 0)

        for threat, counter_info in list(self.active_counters.items()):
            rule = counter_info["rule"]
            counter_units = rule["counter_units"]

            # 카운터 유닛 수 확인
            total_count = 0
            for unit_name in counter_units:
                try:
                    unit_type = getattr(UnitTypeId, unit_name.upper(), None)
                    if unit_type:
                        count = self.bot.units(unit_type).amount
                        total_count += count
                except (AttributeError, TypeError) as e:
                    # Invalid unit type or units API not available
                    self.logger.debug(f"Counter unit check failed for {unit_name}: {e}")
                    continue

            # 목표 달성 확인
            if total_count >= rule["min_count"] and not counter_info["target_met"]:
                counter_info["target_met"] = True
                self.logger.info(
                    f"[{int(game_time)}s] ★ COUNTER TARGET MET: {threat} ★\n"
                    f"  Counter Units: {total_count}/{rule['min_count']}"
                )

                # Blackboard 오버라이드 해제 (목표 달성)
                blackboard = getattr(self.bot, "blackboard", None)
                if blackboard:
                    blackboard.set("dynamic_counter_active", False)

    def get_active_threats(self) -> List[Tuple[str, Dict]]:
        """
        현재 활성화된 위협 목록 반환

        Returns:
            [(threat_name, counter_info), ...]
        """
        return [(threat, info) for threat, info in self.active_counters.items()]

    def get_highest_threat(self) -> Tuple[str, int]:
        """
        가장 위험한 위협 반환

        Returns:
            (threat_name, threat_value)
        """
        if not self.detected_threats:
            return ("NONE", 0)

        highest = ("NONE", 0)
        for threat in self.detected_threats:
            rule = self.counter_rules.get(threat)
            if rule:
                value = rule["threat_value"]
                if value > highest[1]:
                    highest = (threat, value)

        return highest
