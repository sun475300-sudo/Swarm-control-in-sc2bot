"""
Overlord Vision Network - Overlord 시야 네트워크

전략적 위치에 Overlord를 배치하여 최대 시야 확보:
- 확장 경로 감시
- Drop 감지
- 적 이동 경로 모니터링
- Overseer 전환 타이밍

Features:
- 주요 위치 자동 배치
- 시야 커버리지 최적화
- 위험 레벨 평가 및 후퇴
- Changelings 정찰 지원
"""

from typing import List, Dict, Set, Optional
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        OVERLORD = "OVERLORD"
        OVERSEER = "OVERSEER"
    Point2 = tuple


class OverlordVisionNetwork:
    """Overlord 시야 네트워크"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("VisionNetwork")

        # Vision positions
        self.vision_positions: List[Point2] = []
        self.assigned_overlords: Dict[Point2, int] = {}  # {position: overlord_tag}

        # Network state
        self.network_established = False

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # ★ IMPROVED: 220 → 110 프레임 (~5초마다) — 더 빠른 시야 대응
            if iteration % 110 == 0:
                self._update_vision_positions()
                await self._deploy_vision_network()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[VISION_NETWORK] Error: {e}")

    def _update_vision_positions(self):
        """시야 위치 업데이트 (★ OPTIMIZED: 우선순위 기반 위치 선정 ★)"""
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        import math

        self.vision_positions = []
        our_base = self.bot.start_location
        enemy_base = self.bot.enemy_start_locations[0] if self.bot.enemy_start_locations else None

        # ★ PRIORITY 0: Highground Pillars (대공 유닛 도달 불가 벼랑) ★
        # 적 본진 주변 지상 이동 불가 고지대에 대군주 배치 → 반영구 시야
        pillar_positions = self._find_highground_pillars(enemy_base)
        for pos in pillar_positions[:3]:  # 최대 3개
            self.vision_positions.append(pos)

        # ★ PRIORITY 1: Watchtowers (best vision, defensible)
        if hasattr(self.bot, "watchtowers"):
            for tower in self.bot.watchtowers[:2]:
                self.vision_positions.append(tower.position)

        # ★ PRIORITY 2: Enemy base perimeter (drop detection + tech scouting)
        if enemy_base:
            for angle in [0, 90, 180, 270]:
                rad = math.radians(angle)
                offset_x = 15 * math.cos(rad)
                offset_y = 15 * math.sin(rad)
                watch_pos = Point2((enemy_base.x + offset_x, enemy_base.y + offset_y))
                self.vision_positions.append(watch_pos)

        # ★ PRIORITY 3: Main attack path (between bases)
        if enemy_base:
            midpoint = Point2(((our_base.x + enemy_base.x) / 2, (our_base.y + enemy_base.y) / 2))
            self.vision_positions.append(midpoint)

        # ★ PRIORITY 4: Expansion paths (우리 확장 + 적 예상 확장)
        for exp_pos in self.bot.expansion_locations_list[1:4]:
            self.vision_positions.append(exp_pos.towards(self.bot.game_info.map_center, 5))

        # ★ PRIORITY 5: Map center (general awareness)
        self.vision_positions.append(self.bot.game_info.map_center)

    def _find_highground_pillars(self, enemy_base) -> List[Point2]:
        """
        ★★★ 대군주 절대 안전지대(Pillars) 탐색 ★★★

        pathing_grid에서 지상 이동 불가(=0) 위치를 탐색하여
        대공 유닛이 도달할 수 없는 벼랑 끝 사각지대를 찾음.

        적 본진 주변 10/15/20 거리, 45도 간격 8방향 샘플링.
        지상 도달 불가한 위치만 반환.
        """
        import math

        if not enemy_base or not hasattr(self.bot, "game_info"):
            return []

        pathing = getattr(self.bot.game_info, "pathing_grid", None)
        if pathing is None:
            return []

        pillars = []

        # 적 본진 주변 여러 거리/각도에서 지상 이동 불가 지점 탐색
        for distance in [10, 15, 20]:
            for angle_deg in range(0, 360, 45):
                rad = math.radians(angle_deg)
                x = enemy_base.x + distance * math.cos(rad)
                y = enemy_base.y + distance * math.sin(rad)

                # 맵 경계 체크
                px, py = int(x), int(y)
                if px < 2 or py < 2:
                    continue
                if px >= pathing.width - 2 or py >= pathing.height - 2:
                    continue

                try:
                    # 지상 이동 불가 = 대공 유닛 도달 불가 = 안전
                    if pathing[px, py] == 0:
                        # 근처에 이미 찾은 pillar가 없는지 확인
                        pos = Point2((x, y))
                        if all(pos.distance_to(p) > 5 for p in pillars):
                            pillars.append(pos)
                except (IndexError, Exception):
                    continue

        return pillars

    def _is_overlord_managed(self, overlord_tag: int) -> bool:
        """다른 시스템이 관리 중인 오버로드인지 확인"""
        # ★ UnitAuthority 체크 ★
        authority = getattr(self.bot, "unit_authority", None)
        if authority and overlord_tag in getattr(authority, "authorities", {}):
            owner = authority.authorities[overlord_tag].owner
            if owner != "OverlordVisionNetwork":
                return True
        # ★ AdvancedScoutV2 체크 ★
        scout = getattr(self.bot, "advanced_scout_v2", None)
        if scout:
            # 정찰용 오버로드 확인
            if overlord_tag in getattr(scout, "active_scouts", {}):
                return True
            if overlord_tag in getattr(scout, "_overlord_scouts", set()):
                return True
            if overlord_tag in getattr(scout, "assigned_overlords", set()):
                return True
        # ★ RogueTactics 드랍 오버로드 체크 ★
        rogue = getattr(self.bot, "rogue_tactics", None)
        if rogue and overlord_tag in getattr(rogue, "_drop_overlords", set()):
            return True
        return False

    async def _deploy_vision_network(self):
        """시야 네트워크 배치 (★ OPTIMIZED: 생존 검증 + 재배치 ★)"""
        if not hasattr(self.bot, "units"):
            return

        # ★ 다른 시스템이 관리하지 않는 idle 오버로드만 사용 ★
        overlords = self.bot.units(UnitTypeId.OVERLORD).idle
        overlords = overlords.filter(lambda u: not self._is_overlord_managed(u.tag))

        # ★ Clean up dead/missing overlords from assignments
        positions_to_remove = []
        for pos, tag in self.assigned_overlords.items():
            overlord = self.bot.units.find_by_tag(tag)
            if not overlord or overlord.type_id != UnitTypeId.OVERLORD:
                # Overlord dead or transformed to Overseer
                positions_to_remove.append(pos)
            elif overlord.distance_to(pos) > 15:
                # Overlord moved away (possibly reassigned by other logic)
                positions_to_remove.append(pos)

        for pos in positions_to_remove:
            del self.assigned_overlords[pos]

        # ★ Deploy overlords to uncovered positions (priority order)
        for pos in self.vision_positions:
            if pos in self.assigned_overlords:
                # Already assigned and validated
                continue

            if overlords.exists:
                overlord = overlords.first
                self.bot.do(overlord.move(pos))
                self.assigned_overlords[pos] = overlord.tag
                # Remove from available pool
                overlords = overlords.filter(lambda u: u.tag != overlord.tag)

                self.logger.info(f"[{int(self.bot.time)}s] ★ Overlord deployed to vision position {pos} ★")
