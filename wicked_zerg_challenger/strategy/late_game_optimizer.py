"""
Late Game Composition Optimizer - 후반 조합 최적화

적 조합에 따라 최적의 유닛 조합으로 전환:
- vs Mech: Brood Lord + Viper
- vs Bio: Ultralisk + Banelings
- vs Air: Corruptor + Viper
- vs Carrier: Mass Corruptor

Features:
- 적 조합 실시간 분석
- 자동 테크 전환
- 업그레이드 우선순위 조정
- 가스 집약 유닛 비율 관리
"""

from typing import Dict, Set
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        ULTRALISK = "ULTRALISK"
        BROODLORD = "BROODLORD"
        VIPER = "VIPER"
        CORRUPTOR = "CORRUPTOR"
    class UpgradeId:
        pass


class LateGameOptimizer:
    """후반 조합 최적화"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("LateGameOpt")

        # Composition analysis
        self.enemy_composition = {
            "mech_count": 0,
            "bio_count": 0,
            "air_count": 0,
            "massive_count": 0,
        }

        # Recommended composition
        self.recommended_comp = "standard"  # "brood_lord", "ultralisk", "corruptor"

        # Tech transitions
        self.tech_targets: Set[UnitTypeId] = set()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # Late game starts at 10 minutes
            if self.bot.time < 600:
                return

            if iteration % 220 == 0:  # ~10초마다
                self._analyze_enemy_composition()
                self._determine_optimal_composition()
                self._plan_tech_transitions()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[LATE_GAME_OPT] Error: {e}")

    def _analyze_enemy_composition(self):
        """적 조합 분석"""
        if not hasattr(self.bot, "enemy_units"):
            return

        mech_units = {"SIEGETANK", "THOR", "HELLION", "CYCLONE", "COLOSSUS", "IMMORTAL"}
        bio_units = {"MARINE", "MARAUDER", "ZEALOT", "STALKER"}
        air_units = {"VIKING", "BATTLECRUISER", "CARRIER", "TEMPEST", "VOIDRAY"}
        massive_units = {"THOR", "BATTLECRUISER", "CARRIER", "COLOSSUS"}

        self.enemy_composition = {
            "mech_count": 0,
            "bio_count": 0,
            "air_count": 0,
            "massive_count": 0,
        }

        for unit in self.bot.enemy_units:
            unit_type = str(unit.type_id).upper()

            if unit_type in mech_units:
                self.enemy_composition["mech_count"] += 1
            if unit_type in bio_units:
                self.enemy_composition["bio_count"] += 1
            if unit_type in air_units:
                self.enemy_composition["air_count"] += 1
            if unit_type in massive_units:
                self.enemy_composition["massive_count"] += 1

    def _determine_optimal_composition(self):
        """최적 조합 결정"""
        mech = self.enemy_composition["mech_count"]
        bio = self.enemy_composition["bio_count"]
        air = self.enemy_composition["air_count"]

        if air > 10:
            self.recommended_comp = "corruptor"
            self.logger.info(f"[{int(self.bot.time)}s] ★ RECOMMENDED: Mass Corruptor vs Air ★")
        elif mech > bio:
            self.recommended_comp = "brood_lord"
            self.logger.info(f"[{int(self.bot.time)}s] ★ RECOMMENDED: Brood Lord + Viper vs Mech ★")
        elif bio > 15:
            self.recommended_comp = "ultralisk"
            self.logger.info(f"[{int(self.bot.time)}s] ★ RECOMMENDED: Ultralisk + Banelings vs Bio ★")

    def _plan_tech_transitions(self):
        """테크 전환 계획"""
        if self.recommended_comp == "brood_lord":
            self.tech_targets = {UnitTypeId.BROODLORD, UnitTypeId.VIPER}
        elif self.recommended_comp == "ultralisk":
            self.tech_targets = {UnitTypeId.ULTRALISK}
        elif self.recommended_comp == "corruptor":
            self.tech_targets = {UnitTypeId.CORRUPTOR, UnitTypeId.VIPER}

    def get_recommended_composition(self) -> str:
        """추천 조합 반환"""
        return self.recommended_comp
