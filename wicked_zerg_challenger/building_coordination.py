# -*- coding: utf-8 -*-
"""
Building Coordination - 건물 중복 방지 시스템

모든 건물 건설을 중앙에서 조정하여 중복 방지:
1. 단일 진입점 (Single Entry Point)
2. already_pending() 중앙 관리
3. 건물 요청 대기열

**문제 해결**:
- 산란못, 추출장 등 여러 곳에서 중복 건설 방지
- 건물 건설 상태 추적
"""

from typing import Dict, Set, Optional
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger


class BuildingCoordination:
    """건물 중복 방지 코디네이터"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("BuildingCoord")

        # 건설 요청 추적
        self.building_requests: Dict[UnitTypeId, float] = {}  # {building_type: request_time}
        self.request_cooldown = 10.0  # 같은 건물 10초 쿨다운

        # 1개만 필요한 건물
        self.UNIQUE_BUILDINGS = {
            UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.ROACHWARREN,
            UnitTypeId.BANELINGNEST,
            UnitTypeId.HYDRALISKDEN,
            UnitTypeId.SPIRE,
            UnitTypeId.GREATERSPIRE,
            UnitTypeId.INFESTATIONPIT,
            UnitTypeId.ULTRALISKCAVERN,
            UnitTypeId.NYDUSNETWORK,
            UnitTypeId.EVOLUTIONCHAMBER,
            UnitTypeId.LURKERDENMP
        }

    def can_build(self, building_type: UnitTypeId) -> bool:
        """건물을 건설할 수 있는지 확인"""
        game_time = self.bot.time

        # 1. 이미 존재하는지 확인
        if self.bot.structures(building_type).exists:
            # 1개만 필요한 건물이면 거부
            if building_type in self.UNIQUE_BUILDINGS:
                return False

        # 2. 건설 중인지 확인
        pending = self.bot.already_pending(building_type)
        if pending > 0:
            # 1개만 필요한 건물이면 거부
            if building_type in self.UNIQUE_BUILDINGS:
                self.logger.debug(f"[BLOCKED] {building_type.name} already pending ({pending})")
                return False

        # 3. 최근 요청 확인 (쿨다운)
        if building_type in self.building_requests:
            last_request = self.building_requests[building_type]
            if game_time - last_request < self.request_cooldown:
                return False

        return True

    def request_building(self, building_type: UnitTypeId, requester: str = "Unknown") -> bool:
        """건물 건설 요청"""
        if self.can_build(building_type):
            self.building_requests[building_type] = self.bot.time
            self.logger.info(f"[REQUEST] {requester} requested {building_type.name}")
            return True
        else:
            self.logger.debug(f"[DENIED] {requester} request for {building_type.name} denied")
            return False

    def get_building_count(self, building_type: UnitTypeId) -> Dict[str, int]:
        """건물 개수 정보"""
        return {
            "existing": self.bot.structures(building_type).amount,
            "pending": self.bot.already_pending(building_type),
            "total": self.bot.structures(building_type).amount + self.bot.already_pending(building_type)
        }
