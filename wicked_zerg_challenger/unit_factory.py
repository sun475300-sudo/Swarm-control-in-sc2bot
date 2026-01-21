# -*- coding: utf-8 -*-
"""
Unit Factory - 생산 로직 (정상화 버전)

목표:
1. 프레임당 다중 생산 (return 병목 제거)
2. 여왕 생산 가스 조건 제거
3. 간결하고 안전한 생산 흐름 유지
"""

from typing import Optional, List

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        LARVA = "LARVA"
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        MUTALISK = "MUTALISK"
        ULTRALISK = "ULTRALISK"
        OVERLORD = "OVERLORD"
        QUEEN = "QUEEN"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        ROACHWARREN = "ROACHWARREN"
        HYDRALISKDEN = "HYDRALISKDEN"
        SPIRE = "SPIRE"
        ULTRALISKCAVERN = "ULTRALISKCAVERN"


class UnitFactory:
    """Unit Production Specialist."""

    def __init__(self, production_manager):
        self.pm = production_manager
        self.bot = production_manager.bot
        self.config = getattr(production_manager, "config", None)
        self.priority_table = self._build_priority_table()

    async def _produce_army(self, game_phase, build_plan: Optional[dict] = None):
        b = self.bot

        larvae = list(b.units(UnitTypeId.LARVA))
        if not larvae:
            return

        if b.supply_left < 2:
            return

        # Flush mode: use all larvae when minerals >= 1000
        if b.minerals < 1000:
            # Reserve a small portion if needed
            reserve_count = max(1, int(len(larvae) * 0.2))
            if len(larvae) > reserve_count:
                larvae = larvae[:-reserve_count]
            else:
                return

        # Counter priority
        counter_priority = []
        if hasattr(b, "counter_punch") and b.counter_punch and hasattr(b.counter_punch, "get_train_priority"):
            counter_priority = b.counter_punch.get_train_priority()

        # Tech-based units
        tech_based_units = await self._get_tech_based_unit_composition()

        # Default units with resource-aware ordering
        units_to_produce = self._select_units_by_resources(game_phase)

        produced_count = 0

        # Production loop: consume as many larvae as possible
        for larva in list(larvae):
            if not hasattr(larva, "is_ready") or not larva.is_ready:
                continue

            if b.supply_left < 1:
                if b.can_afford(UnitTypeId.OVERLORD):
                    await self._safe_train(larva, UnitTypeId.OVERLORD)
                continue

            produced = False

            for unit_type in counter_priority:
                if await self._try_produce_unit(unit_type, [larva]):
                    produced = True
                    produced_count += 1
                    break

            if produced:
                continue

            for unit_type in tech_based_units:
                if await self._try_produce_unit(unit_type, [larva]):
                    produced = True
                    produced_count += 1
                    break

            if produced:
                continue

            for unit_type in units_to_produce:
                if await self._try_produce_unit(unit_type, [larva]):
                    produced_count += 1
                    break

        if produced_count > 0 and getattr(b, "iteration", 0) % 50 == 0:
            print(f"[PRODUCTION] [{int(b.time)}s] Produced {produced_count} units this frame")

    async def _produce_queen(self):
        """Queen production (gas 조건 제거)."""
        b = self.bot

        if not b.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            return

        # 여왕은 미네랄만 사용
        if b.minerals < 150:
            return

        townhalls = list(b.townhalls) if hasattr(b, "townhalls") else []
        if not townhalls:
            return

        queens_count = b.units(UnitTypeId.QUEEN).amount + b.already_pending(UnitTypeId.QUEEN)
        if queens_count >= len(townhalls):
            return

        # Worker / supply sanity
        if b.workers.amount < len(townhalls) * 8:
            return
        if b.supply_cap - b.supply_used < 4:
            return

        idle_hatcheries = [
            th for th in townhalls
            if th.is_ready and th.is_idle and (not hasattr(th, "orders") or len(th.orders) == 0)
        ]
        if not idle_hatcheries:
            return

        hatch = idle_hatcheries[0]
        await self._safe_train(hatch, UnitTypeId.QUEEN)

    async def _try_produce_unit(self, unit_type, larvae: List):
        b = self.bot

        if unit_type == UnitTypeId.ROACH and not b.structures(UnitTypeId.ROACHWARREN).ready.exists:
            return False
        if unit_type == UnitTypeId.HYDRALISK and not b.structures(UnitTypeId.HYDRALISKDEN).ready.exists:
            return False
        if unit_type == UnitTypeId.MUTALISK and not b.structures(UnitTypeId.SPIRE).ready.exists:
            return False
        if unit_type == UnitTypeId.ULTRALISK and not b.structures(UnitTypeId.ULTRALISKCAVERN).ready.exists:
            return False
        if unit_type != UnitTypeId.ZERGLING and not b.can_afford(unit_type):
            return False

        for larva in larvae:
            if hasattr(larva, "is_ready") and not larva.is_ready:
                continue
            if b.supply_left < 1:
                return False
            if await self._safe_train(larva, unit_type):
                return True
        return False

    async def _safe_train(self, unit, unit_type) -> bool:
        try:
            result = unit.train(unit_type)
            if hasattr(result, "__await__"):
                await result
            return True
        except Exception:
            return False

    def _should_use_basic_units(self) -> bool:
        # Early game or fallback
        supply_used = getattr(self.bot, "supply_used", 0)
        return supply_used < 40

    async def _get_tech_based_unit_composition(self) -> List:
        b = self.bot
        scout = getattr(b, "scout", None)
        if scout and getattr(scout, "enemy_has_air", False):
            if b.structures(UnitTypeId.HYDRALISKDEN).ready.exists:
                return [UnitTypeId.HYDRALISK]
        return []

    def _get_counter_units(self, game_phase) -> List:
        # Simplified fallback counter composition
        return [UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.HYDRALISK]

    def _build_priority_table(self) -> dict:
        """Build a mineral/gas-aware priority table."""
        table = {
            "low_gas": [
                UnitTypeId.ZERGLING,
                UnitTypeId.ROACH,
                UnitTypeId.HYDRALISK,
            ],
            "balanced": [
                UnitTypeId.ROACH,
                UnitTypeId.HYDRALISK,
                UnitTypeId.ZERGLING,
                UnitTypeId.MUTALISK,
            ],
            "high_gas": [
                UnitTypeId.HYDRALISK,
                UnitTypeId.MUTALISK,
                UnitTypeId.ROACH,
                UnitTypeId.ZERGLING,
                UnitTypeId.ULTRALISK,
            ],
        }
        override = getattr(self.config, "production_priority_table", None)
        if isinstance(override, dict):
            table.update(override)
        return table

    def _select_units_by_resources(self, game_phase) -> List:
        """Select unit order based on mineral/gas competition."""
        b = self.bot
        minerals = getattr(b, "minerals", 0)
        gas = getattr(b, "vespene", 0)
        gas_ratio = gas / max(minerals, 1)

        if self._should_use_basic_units():
            base_units = [UnitTypeId.ZERGLING, UnitTypeId.ROACH]
        else:
            base_units = self._get_counter_units(game_phase)

        if gas < 50 or gas_ratio < 0.15:
            order = self.priority_table.get("low_gas", base_units)
        elif gas > 150 and gas_ratio > 0.6:
            order = self.priority_table.get("high_gas", base_units)
        else:
            order = self.priority_table.get("balanced", base_units)

        # Preserve any base units not included in the table
        for u in base_units:
            if u not in order:
                order.append(u)
        return order
