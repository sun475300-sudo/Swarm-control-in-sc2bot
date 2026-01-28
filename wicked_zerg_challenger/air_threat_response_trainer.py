# -*- coding: utf-8 -*-
"""
Air Threat Response Trainer - 공중 위협 대응 학습 시스템

공중 유닛 대응 전략:
1. 상대 공중유닛 < 5 & 아군 지상유닛 > 20: 공중유닛 무시, 기지 파괴
2. 상대 공중유닛 >= 5 & 아군 대공유닛 < 10: 긴급 대공 유닛 생산
3. 상대 공중유닛 위협도 분석 (Mutalisk, Phoenix, Void Ray 등)
4. 동적 카운터: 히드라, 퀸, 감염충, 타락귀
"""

from typing import Dict, Set, List, Optional
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger


class ThreatLevel:
    """위협 수준"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AirThreatResponseTrainer:
    """
    공중 위협 대응 학습 시스템

    상황에 따라 공중유닛을 무시하거나 적극 대응
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("AirThreatResponse")

        # 공중 유닛 분류
        self.LIGHT_AIR = {
            UnitTypeId.MUTALISK, UnitTypeId.PHOENIX,
            UnitTypeId.ORACLE, UnitTypeId.MEDIVAC
        }

        self.HEAVY_AIR = {
            UnitTypeId.VOIDRAY, UnitTypeId.CARRIER,
            UnitTypeId.BATTLECRUISER, UnitTypeId.TEMPEST,
            UnitTypeId.BROODLORD
        }

        # 대공 유닛
        self.OUR_ANTI_AIR = {
            UnitTypeId.QUEEN, UnitTypeId.HYDRALISK,
            UnitTypeId.CORRUPTOR, UnitTypeId.INFESTOR,
            UnitTypeId.SPORECRAWLER
        }

        # 위협 임계값
        self.IGNORE_AIR_THRESHOLD = 5  # 5기 이하면 무시 가능
        self.CRITICAL_AIR_THRESHOLD = 10  # 10기 이상이면 위험
        self.MIN_GROUND_ARMY = 20  # 지상군 최소 20

        # 대응 전략
        self.current_strategy = "BALANCED"  # BALANCED, IGNORE_AIR, COUNTER_AIR

        # 통계
        self.air_threats_detected = 0
        self.counter_units_produced = 0
        self.air_units_killed = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 1. 공중 위협 분석 (1초마다)
            if iteration % 22 == 0:
                threat_level = self._analyze_air_threat()

                # 2. 전략 결정
                self._decide_strategy(threat_level)

                # 3. 전략 실행
                if iteration % 44 == 0:  # 2초마다
                    await self._execute_strategy(threat_level)

            # 4. 긴급 대공 생산 (0.5초마다)
            if iteration % 11 == 0:
                await self._emergency_anti_air_production()

            # 5. 통계 출력 (30초마다)
            if iteration % 660 == 0:
                self._print_statistics(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[AIR_THREAT] Error: {e}")

    def _analyze_air_threat(self) -> int:
        """
        공중 위협 분석

        Returns:
            ThreatLevel (0-4)
        """
        if not self.bot.enemy_units:
            return ThreatLevel.NONE

        # 적 공중 유닛 집계
        light_air = self.bot.enemy_units.filter(
            lambda u: u.type_id in self.LIGHT_AIR
        )
        heavy_air = self.bot.enemy_units.filter(
            lambda u: u.type_id in self.HEAVY_AIR
        )

        light_count = light_air.amount
        heavy_count = heavy_air.amount
        total_air = light_count + heavy_count

        # 위협 가중치 (중형 공중은 2배)
        threat_score = light_count + (heavy_count * 2)

        # 위협 수준 결정
        if threat_score == 0:
            return ThreatLevel.NONE
        elif threat_score < 3:
            return ThreatLevel.LOW
        elif threat_score < 7:
            return ThreatLevel.MEDIUM
        elif threat_score < 12:
            return ThreatLevel.HIGH
        else:
            return ThreatLevel.CRITICAL

    def _decide_strategy(self, threat_level: int):
        """
        전략 결정

        Args:
            threat_level: 공중 위협 수준
        """
        # 아군 병력 확인
        ground_army = self.bot.units.filter(
            lambda u: u.type_id in {
                UnitTypeId.ZERGLING, UnitTypeId.ROACH,
                UnitTypeId.RAVAGER, UnitTypeId.ULTRALISK
            }
        )

        anti_air = self.bot.units.filter(
            lambda u: u.type_id in self.OUR_ANTI_AIR
        )

        ground_count = ground_army.amount
        anti_air_count = anti_air.amount

        # 전략 1: 공중유닛 무시 (공격 집중)
        if (threat_level <= ThreatLevel.LOW and
            ground_count >= self.MIN_GROUND_ARMY):

            if self.current_strategy != "IGNORE_AIR":
                self.current_strategy = "IGNORE_AIR"
                self.logger.info(
                    f"[STRATEGY] IGNORE_AIR - "
                    f"Ground: {ground_count}, Enemy Air: Low threat"
                )

        # 전략 2: 공중유닛 적극 대응
        elif threat_level >= ThreatLevel.MEDIUM:
            if self.current_strategy != "COUNTER_AIR":
                self.current_strategy = "COUNTER_AIR"
                self.logger.info(
                    f"[STRATEGY] COUNTER_AIR - "
                    f"Enemy Air: {threat_level}, Anti-air: {anti_air_count}"
                )

        # 전략 3: 균형
        else:
            if self.current_strategy != "BALANCED":
                self.current_strategy = "BALANCED"
                self.logger.info("[STRATEGY] BALANCED")

    async def _execute_strategy(self, threat_level: int):
        """전략 실행"""
        if self.current_strategy == "IGNORE_AIR":
            # Complete Destruction에 신호 보내기
            if hasattr(self.bot, "complete_destruction"):
                # 모든 병력을 건물 파괴에 집중
                pass  # Complete Destruction이 자동으로 처리

        elif self.current_strategy == "COUNTER_AIR":
            # 대공 유닛 생산 요청
            await self._request_anti_air_production()

    async def _emergency_anti_air_production(self):
        """긴급 대공 유닛 생산"""
        threat_level = self._analyze_air_threat()

        # 위협이 높고 대공 유닛이 부족하면
        if threat_level >= ThreatLevel.HIGH:
            anti_air = self.bot.units.filter(
                lambda u: u.type_id in self.OUR_ANTI_AIR
            )

            if anti_air.amount < 10:
                # Unit Factory에 긴급 생산 요청
                if hasattr(self.bot, "unit_factory"):
                    # 히드라 긴급 생산
                    self.bot.unit_factory.request_priority = "HYDRALISK"

    async def _request_anti_air_production(self):
        """대공 유닛 생산 요청"""
        # 히드라리스크 생산 요청
        if hasattr(self.bot, "unit_factory"):
            try:
                # 히드라 덴 확인
                hydra_den = self.bot.structures(UnitTypeId.HYDRALISKDEN).ready

                if hydra_den.exists:
                    # 히드라 생산 우선순위 상향
                    self.logger.info("[PRODUCTION] Requesting Hydralisk production")
                else:
                    # 히드라 덴 건설 요청
                    self.logger.info("[PRODUCTION] Requesting Hydralisk Den")

                # 퀸도 대공 가능
                queens = self.bot.units(UnitTypeId.QUEEN)
                if queens.amount < 5:
                    self.logger.info("[PRODUCTION] Requesting more Queens")

            except Exception:
                pass

    def get_current_strategy(self) -> str:
        """현재 전략 반환"""
        return self.current_strategy

    def should_ignore_air(self) -> bool:
        """공중유닛을 무시해야 하는지"""
        return self.current_strategy == "IGNORE_AIR"

    def get_statistics(self) -> Dict:
        """통계 반환"""
        threat_level = self._analyze_air_threat()

        return {
            "current_strategy": self.current_strategy,
            "threat_level": threat_level,
            "threats_detected": self.air_threats_detected,
            "counter_units": self.counter_units_produced,
            "air_kills": self.air_units_killed
        }

    def _print_statistics(self, game_time: float):
        """통계 출력"""
        stats = self.get_statistics()

        self.logger.info(
            f"[AIR_THREAT] [{int(game_time)}s] "
            f"Strategy: {stats['current_strategy']}, "
            f"Threat: {stats['threat_level']}"
        )
