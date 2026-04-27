# -*- coding: utf-8 -*-
"""
Aggressive Tech Builder - Build tech more aggressively when resources overflow.

When construction logic prevents duplicates well but resources overflow,
we need more aggression to build tech faster.

This module does when resources overflow:
1. Increase tech construction priority
2. Relax Supply conditions to build tech faster
3. Allow building multiple techs simultaneously
"""

from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger("AggressiveTechBuilder")
try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:

    class UnitTypeId:
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        ROACHWARREN = "ROACHWARREN"
        HYDRALISKDEN = "HYDRALISKDEN"
        LAIR = "LAIR"
        HATCHERY = "HATCHERY"
        BANELINGNEST = "BANELINGNEST"
        EVOLUTIONCHAMBER = "EVOLUTIONCHAMBER"
        SPIRE = "SPIRE"


class AggressiveTechBuilder:
    """
    �ڿ��� ��ĥ �� ��ũ�� �� ���������� �ø��� ����

    �ڿ��� ��ĥ �� (�̳׶� 800+, ���� 200+):
    - Supply ������ ��ȭ�Ͽ� �� ������ ��ũ�� �ø�
    - ���� ��ũ�� ���ÿ� �ø� �� �ֵ��� ��
    - ��ũ �Ǽ� �켱������ ����
    """

    def __init__(self, bot):
        self.bot = bot
        # �ڿ��� ��ġ�� ���ذ�
        self.excess_mineral_threshold = 800  # �̳׶� 800 �̻�
        self.excess_gas_threshold = 200  # ���� 200 �̻�
        # Supply ��ȭ ���� (�ڿ��� ��ĥ �� supply ������ �̸�ŭ ��ȭ)
        self.supply_reduction_factor = 0.7  # 30% ��ȭ (��: 17 -> 12)

    def has_excess_resources(self) -> Tuple[bool, float, float]:
        """
        �ڿ��� ��ġ���� Ȯ��

        Returns:
            (has_excess, mineral_excess, gas_excess):
            - has_excess: �ڿ��� ��ġ���� ����
            - mineral_excess: �̳׶� �ʰ���
            - gas_excess: ���� �ʰ���
        """
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)

        mineral_excess = max(0, minerals - self.excess_mineral_threshold)
        gas_excess = max(0, gas - self.excess_gas_threshold)

        has_excess = (
            minerals >= self.excess_mineral_threshold
            or gas >= self.excess_gas_threshold
        )

        return has_excess, mineral_excess, gas_excess

    def get_adjusted_supply_threshold(self, base_supply: float) -> float:
        """
        �ڿ��� ��ĥ �� supply ������ ��ȭ

        Args:
            base_supply: �⺻ supply ����

        Returns:
            ��ȭ�� supply ����
        """
        has_excess, _, _ = self.has_excess_resources()
        if has_excess:
            return base_supply * self.supply_reduction_factor
        return base_supply

    async def should_build_tech_aggressively(
        self, tech_type: UnitTypeId, base_supply: float, check_existing: bool = True
    ) -> bool:
        """
        �ڿ��� ��ĥ �� ��ũ�� �� ���������� �ø��� ����

        Args:
            tech_type: �Ǽ��� ��ũ Ÿ��
            base_supply: �⺻ supply ����
            check_existing: ���� �ǹ� ���� ���� Ȯ��

        Returns:
            �Ǽ��ؾ� �ϴ��� ����
        """
        has_excess, mineral_excess, gas_excess = self.has_excess_resources()
        supply_used = getattr(self.bot, "supply_used", 0)

        # ���� �ǹ� Ȯ��
        if check_existing:
            if hasattr(self.bot, "structures"):
                existing = self.bot.structures(tech_type)
                if existing.exists or self.bot.already_pending(tech_type) > 0:
                    return False

        # �ڿ��� ��ĥ ��: supply ���� ��ȭ
        if has_excess:
            adjusted_supply = self.get_adjusted_supply_threshold(base_supply)
            if supply_used >= adjusted_supply:
                return True
        else:
            # �ڿ��� ��ġ�� ���� ��: �⺻ ����
            if supply_used >= base_supply:
                return True

        return False

    async def build_tech_aggressively(
        self,
        tech_type: UnitTypeId,
        build_func,
        base_supply: float = 17.0,
        priority: int = 1,
    ) -> bool:
        """
        �ڿ��� ��ĥ �� ��ũ�� �� ���������� �ø�

        Args:
            tech_type: �Ǽ��� ��ũ Ÿ��
            build_func: �Ǽ� �Լ� (async function)
            base_supply: �⺻ supply ����
            priority: �켱���� (1=�ֿ켱, 2=������)

        Returns:
            �Ǽ� ���� ����
        """
        has_excess, mineral_excess, gas_excess = self.has_excess_resources()

        # �ڿ��� ��ġ�� ������ �⺻ ���� ���
        if not has_excess:
            return False

        # �Ǽ� ���� ���� Ȯ��
        if not self.bot.can_afford(tech_type):
            return False

        # Supply ���� Ȯ�� (��ȭ�� ����)
        should_build = await self.should_build_tech_aggressively(
            tech_type, base_supply, check_existing=True
        )

        if not should_build:
            return False

        # �Ǽ� ����
        try:
            result = await build_func()
            if result:
                excess_info = (
                    f"M:{int(mineral_excess)}+ G:{int(gas_excess)}+"
                    if has_excess
                    else ""
                )
                logger.info(
                    f"[{int(self.bot.time)}s] Building {tech_type} "
                    f"at supply {self.bot.supply_used:.1f} (excess resources: {excess_info})"
                )
                return True
        except Exception as e:
            if self.bot.iteration % 100 == 0:
                logger.error(f"Failed to build {tech_type}: {e}")

        return False

    async def build_multiple_techs_aggressively(
        self, tech_priorities: List[Tuple[UnitTypeId, callable, float]]
    ) -> Dict[UnitTypeId, bool]:
        """
        �ڿ��� ��ĥ �� ���� ��ũ�� ���ÿ� �ø�

        Args:
            tech_priorities: [(tech_type, build_func, base_supply), ...] ����Ʈ

        Returns:
            {tech_type: success} ��ųʸ�
        """
        has_excess, _, _ = self.has_excess_resources()
        if not has_excess:
            return {}

        results = {}

        # �켱���� ������ �Ǽ�
        sorted_techs = sorted(tech_priorities, key=lambda x: x[3] if len(x) > 3 else 1)

        for tech_info in sorted_techs:
            tech_type = tech_info[0]
            build_func = tech_info[1]
            base_supply = tech_info[2] if len(tech_info) > 2 else 17.0

            # �ڿ��� ������� Ȯ��
            if not self.bot.can_afford(tech_type):
                results[tech_type] = False
                continue

            # �Ǽ� ����
            success = await self.build_tech_aggressively(
                tech_type, build_func, base_supply
            )
            results[tech_type] = success

            # �� ���� �ϳ����� �Ǽ� (�ߺ� ����)
            if success:
                break

        return results

    def get_tech_build_priority(self, tech_type: UnitTypeId) -> int:
        """
        ��ũ �Ǽ� �켱���� ��ȯ

        Args:
            tech_type: ��ũ Ÿ��

        Returns:
            �켱���� (1=�ֿ켱, ���ڰ� Ŭ���� ���� �켱����)
        """
        priority_map = {
            UnitTypeId.SPAWNINGPOOL: 1,  # �ֿ켱
            UnitTypeId.SPAWNINGPOOL: 1,  # ֿ켱
            UnitTypeId.EXTRACTOR: 2,  #
            UnitTypeId.ROACHWARREN: 3,  # 3
            UnitTypeId.HYDRALISKDEN: 4,  # 4
            UnitTypeId.BANELINGNEST: 5,  # 5
            UnitTypeId.EVOLUTIONCHAMBER: 6,  # 6
            UnitTypeId.LAIR: 7,  # 7
            UnitTypeId.SPIRE: 8,  # 8
        }
        return priority_map.get(tech_type, 10)

    async def recommend_tech_builds(self) -> List[Tuple[UnitTypeId, float, int]]:
        """

        Returns:
            [(tech_type, base_supply, priority), ...] ����Ʈ
        """
        has_excess, mineral_excess, gas_excess = self.has_excess_resources()
        if not has_excess:
            return []

        recommendations = []

        # Spawning Pool (�⺻ ��ũ)
        if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).exists:
            recommendations.append((UnitTypeId.SPAWNINGPOOL, 12.0, 1))

        # Extractor (������ ������ ��)
        if gas_excess < 100 and not self.bot.structures(UnitTypeId.EXTRACTOR).exists:
            recommendations.append((UnitTypeId.EXTRACTOR, 14.0, 2))

        # Roach Warren (�̳׶��� ���� ��ĥ ��)
        if (
            mineral_excess > 300
            and not self.bot.structures(UnitTypeId.ROACHWARREN).exists
        ):
            recommendations.append((UnitTypeId.ROACHWARREN, 20.0, 3))

        # Hydralisk Den (������ ���� ��ĥ ��)
        if gas_excess > 100 and not self.bot.structures(UnitTypeId.HYDRALISKDEN).exists:
            recommendations.append((UnitTypeId.HYDRALISKDEN, 25.0, 4))

        # Lair (�̳׶��� ������ ��� ���� ��ĥ ��) - ��ȭ�� ����
        if (
            mineral_excess > 500
            and gas_excess > 150
            and self.bot.structures(UnitTypeId.LAIR).amount == 0
            and self.bot.structures(UnitTypeId.HATCHERY).ready.exists
        ):
            # Spawning Pool Ȯ�� (�ʼ� �䱸����)
            if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                # Extractor Ȯ�� (���� ���� Ȯ��)
                if self.bot.structures(UnitTypeId.EXTRACTOR).ready.exists:
                    recommendations.append((UnitTypeId.LAIR, 30.0, 5))

        return recommendations
