"""
Proxy Hatchery Tactics - 프록시 해처리 전술

적진 근처에 공격용 해처리를 건설:
- Hidden expansions
- Forward production base
- Nydus network hub
- Spine crawler rush base

Features:
- 은폐된 위치 선택
- 적 정찰 회피
- Spine crawler 방어
- 공격적 유닛 생산
"""

from typing import Optional, List
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        HATCHERY = "HATCHERY"
        DRONE = "DRONE"
    Point2 = tuple


class ProxyHatchery:
    """프록시 해처리 전술"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("ProxyHatch")

        # Proxy state
        self.proxy_attempted = False
        self.proxy_location: Optional[Point2] = None
        self.proxy_hatchery_tag: Optional[int] = None

        # Timing
        self.PROXY_TIMING = 180  # 3분

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # Proxy timing (3분)
            if game_time >= self.PROXY_TIMING and not self.proxy_attempted:
                await self._attempt_proxy_hatchery()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[PROXY_HATCH] Error: {e}")

    async def _attempt_proxy_hatchery(self):
        """프록시 해처리 시도"""
        if not hasattr(self.bot, "enemy_start_locations"):
            return

        if self.bot.minerals < 300:
            return

        # 적진 근처 은폐 위치 찾기
        enemy_start = self.bot.enemy_start_locations[0]
        proxy_location = enemy_start.towards(self.bot.game_info.map_center, 15)

        # 드론 파견
        drones = self.bot.units(UnitTypeId.DRONE)
        if drones:
            drone = drones.first
            self.bot.do(drone.build(UnitTypeId.HATCHERY, proxy_location))

            self.proxy_attempted = True
            self.proxy_location = proxy_location

            self.logger.info(
                f"[{int(self.bot.time)}s] ★★★ PROXY HATCHERY ATTEMPTED! Location: {proxy_location} ★★★"
            )
