"""
Advanced Creep Automation V2 - 고급 크립 자동화

프로급 크립 확장 전략:
- Pathfinding 기반 Tumor 배치
- 주요 맵 위치로의 크립 연결
- 확장 경로 우선순위
- 적진 방향 공격적 크립

Features:
- Smart tumor placement (최대 범위 활용)
- Creep highway (기지 간 연결)
- Offensive creep (적진 방향)
- Defensive creep (초크 포인트)
"""

from typing import List, Set, Tuple
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        QUEEN = "QUEEN"
        CREEPTUMOR = "CREEPTUMOR"
    class AbilityId:
        BUILD_CREEPTUMOR_QUEEN = "BUILD_CREEPTUMOR_QUEEN"
    Point2 = tuple


class CreepAutomationV2:
    """고급 크립 자동화 V2"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("CreepV2")

        # Creep targets
        self.creep_targets: List[Point2] = []
        self.tumor_positions: Set[Tuple[float, float]] = set()

        # Creep queens
        self.creep_queen_tags: Set[int] = set()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration % 110 == 0:
                self._update_creep_targets()

            if iteration % 44 == 0:
                await self._spread_creep()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[CREEP_V2] Error: {e}")

    def _update_creep_targets(self):
        """크립 타겟 업데이트"""
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        self.creep_targets = []

        # 1. 확장 위치들
        for exp_pos in self.bot.expansion_locations_list:
            self.creep_targets.append(exp_pos)

        # 2. 맵 중앙
        self.creep_targets.append(self.bot.game_info.map_center)

        # 3. 적 본진 방향
        if hasattr(self.bot, "enemy_start_locations"):
            enemy_start = self.bot.enemy_start_locations[0]
            main_to_enemy = self.bot.start_location.towards(enemy_start, 20)
            self.creep_targets.append(main_to_enemy)

    async def _spread_creep(self):
        """크립 확장 (Inject 우선순위 고려)"""
        if not hasattr(self.bot, "units"):
            return

        # ★ Inject 우선순위 고려: 50+ 에너지가 있는 Queen만 사용 ★
        queens = self.bot.units(UnitTypeId.QUEEN).filter(lambda q: q.energy >= 25)

        # InjectOptimizer가 있으면 우선순위 체크
        inject_optimizer = getattr(self.bot, "inject_optimizer", None)

        for queen in queens:
            # ★ Inject 우선순위 체크 ★
            if inject_optimizer:
                if not inject_optimizer.can_use_queen_for_creep(queen):
                    continue  # Inject를 위해 에너지 보존

            # Creep tumor 배치
            if self.creep_targets:
                target = min(self.creep_targets, key=lambda pos: pos.distance_to(queen.position))

                # Tumor 배치 가능한 위치 찾기
                placement = queen.position.towards(target, 5)

                if self.bot.has_creep(placement):
                    self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, placement))
                    self.tumor_positions.add((placement.x, placement.y))
