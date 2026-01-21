# -*- coding: utf-8 -*-
"""
Queen Manager - 여왕 관리 로직
"""

from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.buff_id import BuffId
else:
    try:
        from sc2.unit import Unit
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.ids.ability_id import AbilityId
        from sc2.ids.buff_id import BuffId
    except ImportError:
        Unit = object
        UnitTypeId = object
        AbilityId = object
        BuffId = object


class QueenManager:
    """여왕 생산, 인젝트, 수혈 및 방어 관리."""

    def __init__(self, bot):
        self.bot = bot
        self.queen_hatchery_assignments: Dict[int, int] = {}
        self.max_assign_distance = 10.0
        self.inject_range = 4.0

    async def manage_queens(self):
        b = self.bot
        hatcheries = b.townhalls.ready if hasattr(b, "townhalls") else []
        if not hatcheries:
            return

        queens = b.units(UnitTypeId.QUEEN) if hasattr(b, "units") else []
        queens_list = list(queens) if hasattr(queens, "__iter__") else []

        if not queens_list:
            await self._produce_first_queen(hatcheries)
            return

        alive_queen_tags = {q.tag for q in queens_list}
        for q_tag in list(self.queen_hatchery_assignments.keys()):
            if q_tag not in alive_queen_tags:
                self.queen_hatchery_assignments.pop(q_tag, None)

        await self._inject_larva(hatcheries, queens_list)
        await self._transfuse_critical_buildings(queens_list)

    async def _produce_first_queen(self, hatcheries):
        b = self.bot
        if not b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return
        if b.minerals < 150:
            return
        if b.workers.amount < 8:
            return

        idle_hatcheries = [
            h for h in hatcheries
            if h.is_ready and h.is_idle and (not hasattr(h, "orders") or len(h.orders) == 0)
        ]
        if not idle_hatcheries:
            return

        hatch = idle_hatcheries[0]
        try:
            await b.do(hatch.train(UnitTypeId.QUEEN))
        except Exception:
            return

    async def _inject_larva(self, hatcheries, queens_list):
        b = self.bot
        ready_queens = [q for q in queens_list if q.is_ready and q.energy >= 25]
        if not ready_queens:
            return

        for hatch in hatcheries:
            inject_buff = getattr(BuffId, "QUEENSPAWNLARVA", None)
            if inject_buff and hasattr(hatch, "has_buff") and hatch.has_buff(inject_buff):
                continue

            assigned_tag = None
            for q_tag, h_tag in self.queen_hatchery_assignments.items():
                if h_tag == hatch.tag:
                    assigned_tag = q_tag
                    break

            assigned_queen = None
            if assigned_tag:
                assigned_queen = next((q for q in ready_queens if q.tag == assigned_tag), None)

            if assigned_queen and assigned_queen.distance_to(hatch) > self.max_assign_distance:
                assigned_queen = None

            if not assigned_queen:
                nearby = [q for q in ready_queens if q.distance_to(hatch) <= self.max_assign_distance]
                if not nearby:
                    continue
                assigned_queen = min(nearby, key=lambda q: q.distance_to(hatch))
                self.queen_hatchery_assignments[assigned_queen.tag] = hatch.tag

            if assigned_queen.distance_to(hatch) <= self.inject_range:
                try:
                    await b.do(assigned_queen(AbilityId.EFFECT_INJECTLARVA, hatch))
                except Exception:
                    continue

    async def _transfuse_critical_buildings(self, queens_list):
        b = self.bot
        ready_queens = [q for q in queens_list if q.is_ready and q.energy >= 50]
        if not ready_queens or not hasattr(b, "structures"):
            return

        critical_types = [
            UnitTypeId.SPINECRAWLER,
            UnitTypeId.SPORECRAWLER,
            UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.LURKERDEN,
            UnitTypeId.HYDRALISKDEN,
            UnitTypeId.LAIR,
            UnitTypeId.HIVE,
        ]

        critical_buildings = b.structures.filter(
            lambda s: s.type_id in critical_types and getattr(s, "health_percentage", 1.0) < 0.6
        )
        if not critical_buildings.exists:
            return

        for queen in ready_queens:
            # 가장 체력이 낮은 핵심 건물 우선
            target = min(critical_buildings, key=lambda s: s.health_percentage)
            try:
                await b.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, target))
                break
            except Exception:
                continue
