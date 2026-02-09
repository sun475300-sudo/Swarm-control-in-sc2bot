"""
Adaptive Build Order AI - 적응형 빌드 오더

적의 전략과 종족에 따라 빌드를 동적으로 조정:
- vs Terran: Anti-reaper defense → Roach push
- vs Protoss: Fast expand → Roach/Ravager timing
- vs Zerg: Pool first → Zergling pressure
- Cheese detection → All-in defense

Features:
- 적 종족 감지
- 적 빌드 분석 (Gas timing, Pool timing)
- 동적 빌드 전환
- 타이밍 공격 최적화
"""

from typing import Dict, Optional
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.race import Race
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        pass
    class Race:
        Terran = "Terran"
        Protoss = "Protoss"
        Zerg = "Zerg"


class AdaptiveBuildOrder:
    """적응형 빌드 오더 AI"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("AdaptiveBuild")

        # Enemy analysis
        self.enemy_race: Optional[Race] = None
        self.enemy_cheese_detected = False
        self.enemy_fast_expand = False

        # Build plan
        self.current_build = "standard"  # "anti_cheese", "timing_attack", "macro"

        # ★ Race-specific timing attacks ★
        self.timing_attack_details: Dict[str, any] = {}
        self.attack_supply_requirement = 0
        self.attack_target_time = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration % 220 == 0:
                self._detect_enemy_race()
                self._analyze_enemy_strategy()
                self._adapt_build_order()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[ADAPTIVE_BUILD] Error: {e}")

    def _detect_enemy_race(self):
        """적 종족 감지"""
        if hasattr(self.bot, "enemy_race"):
            self.enemy_race = self.bot.enemy_race

    def _analyze_enemy_strategy(self):
        """적 전략 분석"""
        # Cheese detection (from scout data)
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard:
            self.enemy_cheese_detected = blackboard.get("enemy_is_cheese", False)
            self.enemy_fast_expand = blackboard.get("enemy_is_fast_expand", False)

    def _adapt_build_order(self):
        """
        빌드 오더 조정

        종족별 전략:
        - vs Terran: Roach/Ravager 타이밍 (6:30)
        - vs Protoss: Roach 압박 + Ravager bile (7:00)
        - vs Zerg: Zergling/Baneling 올인 (5:30)
        """
        # ★ StrategyManager가 Emergency 모드이면 AdaptiveBuild 판단 스킵 ★
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard:
            strategy_mode = blackboard.get("strategy_mode", "NORMAL")
            if strategy_mode == "EMERGENCY":
                self.current_build = "anti_cheese"
                self._setup_anti_cheese_build()
                self._sync_to_blackboard(blackboard)
                return

        if self.enemy_cheese_detected:
            self.current_build = "anti_cheese"
            self._setup_anti_cheese_build()
            self.logger.info(f"[{int(self.bot.time)}s] ★ BUILD: Anti-Cheese Defense ★")

        elif self.enemy_fast_expand:
            self.current_build = "timing_attack"
            self._setup_timing_attack()
            self.logger.info(
                f"[{int(self.bot.time)}s] ★ BUILD: Timing Attack ({self.enemy_race.name}) ★"
            )

        else:
            self.current_build = "macro"
            self._setup_macro_build()

        # ★ Blackboard에 빌드 결정 동기화 ★
        if blackboard:
            self._sync_to_blackboard(blackboard)

    def _sync_to_blackboard(self, blackboard):
        """Blackboard에 빌드 결정 사항 기록 (다른 시스템이 참조 가능)"""
        blackboard.set("adaptive_build_plan", self.current_build)
        blackboard.set("adaptive_attack_supply", self.attack_supply_requirement)
        blackboard.set("adaptive_attack_time", self.attack_target_time)
        if self.timing_attack_details:
            blackboard.set("adaptive_build_details", self.timing_attack_details)

    def _setup_anti_cheese_build(self):
        """
        치즈 방어 빌드

        - 즉시 Roach Warren 건설
        - Queen 대량 생산 (방어)
        - Spine Crawler 추가
        """
        self.timing_attack_details = {
            "priority": "defense",
            "unit_comp": {
                UnitTypeId.QUEEN: 4,
                UnitTypeId.ROACH: 8,
            },
            "tech_buildings": [
                UnitTypeId.ROACHWARREN,
                UnitTypeId.SPINECRAWLER,
            ]
        }

    def _setup_timing_attack(self):
        """
        타이밍 공격 빌드 (종족별)

        - vs Terran: Roach/Ravager (6:30, 30 supply)
        - vs Protoss: Roach 압박 (7:00, 35 supply)
        - vs Zerg: Zergling/Baneling (5:30, 40 supply)
        """
        if self.enemy_race == Race.Terran:
            # Terran: Roach/Ravager 타이밍
            self.attack_supply_requirement = 30
            self.attack_target_time = 390  # 6:30
            self.timing_attack_details = {
                "priority": "timing",
                "unit_comp": {
                    UnitTypeId.ROACH: 12,
                    UnitTypeId.RAVAGER: 4,
                },
                "tech_buildings": [
                    UnitTypeId.ROACHWARREN,
                ],
                "upgrades": [
                    "GLIALRECONSTITUTION",  # Roach speed
                ]
            }

        elif self.enemy_race == Race.Protoss:
            # Protoss: Roach 압박
            self.attack_supply_requirement = 35
            self.attack_target_time = 420  # 7:00
            self.timing_attack_details = {
                "priority": "timing",
                "unit_comp": {
                    UnitTypeId.ROACH: 16,
                    UnitTypeId.RAVAGER: 2,
                },
                "tech_buildings": [
                    UnitTypeId.ROACHWARREN,
                ],
                "upgrades": [
                    "GLIALRECONSTITUTION",
                ]
            }

        elif self.enemy_race == Race.Zerg:
            # Zerg: Zergling/Baneling 올인
            self.attack_supply_requirement = 40
            self.attack_target_time = 330  # 5:30
            self.timing_attack_details = {
                "priority": "all_in",
                "unit_comp": {
                    UnitTypeId.ZERGLING: 24,
                    UnitTypeId.BANELING: 8,
                },
                "tech_buildings": [
                    UnitTypeId.BANELINGNEST,
                ],
                "upgrades": [
                    "ZERGLINGMOVEMENTSPEED",  # Metabolic Boost
                ]
            }

        else:
            # Unknown race: 기본 Roach 타이밍
            self.attack_supply_requirement = 30
            self.attack_target_time = 390
            self.timing_attack_details = {
                "priority": "timing",
                "unit_comp": {
                    UnitTypeId.ROACH: 15,
                },
                "tech_buildings": [
                    UnitTypeId.ROACHWARREN,
                ]
            }

    def _setup_macro_build(self):
        """
        매크로 빌드 (기본)

        - 3 기지 빠른 확장
        - Dronedrilling
        - Lair tech 준비
        """
        self.timing_attack_details = {
            "priority": "macro",
            "expansion_count": 3,
            "drone_target": 66,  # 3-base saturation
            "tech_buildings": [
                UnitTypeId.LAIR,
                UnitTypeId.HYDRALISKDEN,
            ]
        }

    def get_current_build(self) -> str:
        """현재 빌드 반환"""
        return self.current_build

    def get_build_details(self) -> Dict:
        """빌드 세부사항 반환"""
        return self.timing_attack_details

    def should_attack_now(self) -> bool:
        """
        타이밍 공격 실행 여부

        조건:
        1. 타이밍 공격 빌드
        2. 공격 시간 도달
        3. 병력 요구사항 충족
        """
        if self.current_build != "timing_attack":
            return False

        game_time = self.bot.time
        if game_time < self.attack_target_time:
            return False

        # 병력 확인
        if not hasattr(self.bot, "supply_used"):
            return False

        if self.bot.supply_used < self.attack_supply_requirement:
            return False

        return True
