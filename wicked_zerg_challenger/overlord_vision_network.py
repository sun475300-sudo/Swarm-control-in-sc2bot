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
            if iteration % 220 == 0:  # ~10초마다
                self._update_vision_positions()
                await self._deploy_vision_network()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[VISION_NETWORK] Error: {e}")

    def _update_vision_positions(self):
        """시야 위치 업데이트"""
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        self.vision_positions = []

        # 1. Watchtowers (if any)
        # 2. Expansion paths
        for exp_pos in self.bot.expansion_locations_list[:5]:
            self.vision_positions.append(exp_pos.towards(self.bot.game_info.map_center, 5))

        # 3. Map center
        self.vision_positions.append(self.bot.game_info.map_center)

    async def _deploy_vision_network(self):
        """시야 네트워크 배치"""
        if not hasattr(self.bot, "units"):
            return

        overlords = self.bot.units(UnitTypeId.OVERLORD).idle

        for pos in self.vision_positions:
            if pos in self.assigned_overlords:
                # Already assigned
                continue

            if overlords:
                overlord = overlords.first
                self.bot.do(overlord.move(pos))
                self.assigned_overlords[pos] = overlord.tag
                overlords = overlords.exclude_type(UnitTypeId.OVERLORD)

                self.logger.info(f"[{int(self.bot.time)}s] ★ Overlord deployed to vision position {pos} ★")
