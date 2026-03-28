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
        CREEPTUMORBURROWED = "CREEPTUMORBURROWED"
    class AbilityId:
        BUILD_CREEPTUMOR_QUEEN = "BUILD_CREEPTUMOR_QUEEN"
        BUILD_CREEPTUMOR_TUMOR = "BUILD_CREEPTUMOR_TUMOR"
    Point2 = tuple


class CreepAutomationV2:
    """고급 크립 자동화 V2"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("CreepV2")

        # Creep targets
        self.creep_targets: List[Point2] = []
        self.tumor_positions: Set[Tuple[float, float]] = set()

        # ★ Phase 18: 종양 릴레이 쿨다운 추적 ★
        self._tumor_cooldowns: dict = {}

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
        """크립 타겟 업데이트 — ★ Phase 18: 공격적 적진 방향 크립 확장 ★"""
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        self.creep_targets = []
        game_time = getattr(self.bot, "time", 0)

        # 1. 확장 위치들
        for exp_pos in self.bot.expansion_locations_list:
            self.creep_targets.append(exp_pos)

        # 2. 맵 중앙
        map_center = self.bot.game_info.map_center
        self.creep_targets.append(map_center)

        # 3. ★ Phase 18: 적진 방향 공격적 크립 — 다단계 웨이포인트 ★
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_start = self.bot.enemy_start_locations[0]
            our_base = self.bot.start_location
            total_dist = our_base.distance_to(enemy_start)

            if total_dist > 1:
                # 5분 전: 30%까지만 (안전 범위)
                # 5분 후: 60%까지 (맵 센터 넘어)
                # 8분 후: 75%까지 (적진 근처)
                if game_time >= 480:
                    max_ratio = 0.75
                elif game_time >= 300:
                    max_ratio = 0.60
                else:
                    max_ratio = 0.30

                # 10% 간격으로 웨이포인트 생성
                for pct in range(10, int(max_ratio * 100) + 1, 10):
                    ratio = pct / 100.0
                    wp = Point2((
                        our_base.x + (enemy_start.x - our_base.x) * ratio,
                        our_base.y + (enemy_start.y - our_base.y) * ratio
                    ))
                    self.creep_targets.append(wp)

                # ★ Phase 18: 측면 크립도 추가 (8분+, 적진 방향 좌우 15도 오프셋) ★
                if game_time >= 480:
                    import math
                    dx = enemy_start.x - our_base.x
                    dy = enemy_start.y - our_base.y
                    angle = math.atan2(dy, dx)
                    for offset_deg in [-15, 15]:
                        offset_rad = math.radians(offset_deg)
                        new_angle = angle + offset_rad
                        for dist_ratio in [0.4, 0.55]:
                            dist = total_dist * dist_ratio
                            wp = Point2((
                                our_base.x + math.cos(new_angle) * dist,
                                our_base.y + math.sin(new_angle) * dist
                            ))
                            self.creep_targets.append(wp)

    async def _spread_creep(self):
        """크립 확장 (Inject 우선순위 고려) — ★ Phase 18: 종양 릴레이 + 공격적 확장 ★"""
        if not hasattr(self.bot, "units"):
            return

        # ★ Phase 18: 종양 릴레이 — 매립된 종양이 적 방향으로 자동 확산 ★
        await self._tumor_relay_toward_enemy()

        # ★ Inject 우선순위 고려: 25+ 에너지가 있는 Queen만 사용 ★
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
                # ★ Phase 18: 크립이 없는 타겟 우선 (프론티어 확장) ★
                uncovered_targets = [t for t in self.creep_targets if not self.bot.has_creep(t)]
                if uncovered_targets:
                    target = min(uncovered_targets, key=lambda pos: pos.distance_to(queen.position))
                else:
                    target = min(self.creep_targets, key=lambda pos: pos.distance_to(queen.position))

                # Tumor 배치 가능한 위치 찾기
                placement = queen.position.towards(target, 5)

                if self.bot.has_creep(placement):
                    self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, placement))
                    self.tumor_positions.add((placement.x, placement.y))

    async def _tumor_relay_toward_enemy(self):
        """
        ★ Phase 18: 종양 릴레이 — 매립된 종양이 적 방향으로 자동 확산 ★

        매립된 종양(CREEPTUMORBURROWED)이 쿨다운 완료 시
        적 방향으로 새 종양을 생성하여 크립 프론티어를 전진시킴.
        """
        if not hasattr(self.bot, "enemy_start_locations") or not self.bot.enemy_start_locations:
            return

        enemy_start = self.bot.enemy_start_locations[0]

        # 매립된 종양 찾기
        tumors = self.bot.structures.of_type({
            UnitTypeId.CREEPTUMORBURROWED
        })

        if not tumors.exists:
            return

        # 적에 가장 가까운 종양부터 처리 (프론티어 우선)
        sorted_tumors = tumors.sorted(lambda t: t.distance_to(enemy_start))

        spread_count = 0
        max_spreads = 3  # 한 번에 최대 3개

        for tumor in sorted_tumors:
            if spread_count >= max_spreads:
                break

            # 쿨다운 체크 (50프레임 최소 간격)
            tag = tumor.tag
            last_spread = self._tumor_cooldowns.get(tag, 0)
            current_iter = getattr(self.bot, "_game_loop", 0)
            if current_iter and current_iter - last_spread < 50:
                continue

            # 적 방향으로 10거리 위치에 종양 생성 시도
            spread_pos = tumor.position.towards(enemy_start, 10)

            # 크립 위여야 함
            if not self.bot.has_creep(spread_pos):
                # 더 가까운 위치 시도
                spread_pos = tumor.position.towards(enemy_start, 7)
                if not self.bot.has_creep(spread_pos):
                    continue

            # 이미 종양이 있는 위치면 스킵
            pos_key = (round(spread_pos.x, 0), round(spread_pos.y, 0))
            if pos_key in self.tumor_positions:
                continue

            try:
                abilities = await self.bot.get_available_abilities(tumor)
                if AbilityId.BUILD_CREEPTUMOR_TUMOR in abilities:
                    self.bot.do(tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, spread_pos))
                    self.tumor_positions.add(pos_key)
                    self._tumor_cooldowns[tag] = current_iter if current_iter else 0
                    spread_count += 1
            except Exception:
                continue
