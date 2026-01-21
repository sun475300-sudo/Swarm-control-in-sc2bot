# -*- coding: utf-8 -*-
"""
Queen Manager Improvements - ���� ���� ���� ����

CRITICAL IMPROVEMENTS:
1. ���� �Ӱ谪 ���� ���� ���� (���� ���� �� ���� ���� ����)
2. STYLE �ּ� ���� �� �ڵ� ����
3. ��� ���� ȿ���� ����
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.position import Point2
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
else:
    try:
        from sc2.unit import Unit
        from sc2.position import Point2
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.ids.ability_id import AbilityId
    except ImportError:
        Unit = None
        Point2 = None
        UnitTypeId = None
        AbilityId = None


class QueenManagerImproved:
    """
    ������ ���� ������
    
    �ֿ� ���� ����:
    1. ���� ���� �� ���� ���� ���� (������ ������ �Ҹ����� ����)
    2. ��� ���� ȿ���� ���� (�Ÿ� üũ ��ȭ)
    3. �ڵ� ���� (STYLE �ּ� ����)
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.queen_assignments = {}  # {hatchery_tag: queen_tag}
        self.last_inject_time = {}  # {hatchery_tag: time}
        self.inject_cooldown = 29.0  # Inject ��Ÿ�� (��)
        self.max_inject_distance = 4.0  # Inject �ִ� �Ÿ�
        self.max_queen_travel_distance = 10.0  # ���� �̵� �ִ� �Ÿ�
    
    async def produce_queen(self, hatchery: Unit) -> bool:
        """
        ���� ����
        
        CRITICAL FIX: ���� ���� ���� - ������ ������ �Ҹ����� �����Ƿ� ���� üũ ���ʿ�
        
        Args:
            hatchery: ��ȭ�� ����
            
        Returns:
            ���� ���� ����
        """
        try:
            # �ʼ� �ǹ� Ȯ��
            if not self.bot.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
                return False
            
            # �̳׶� Ȯ�� (������ �̳׶� 150�� �Ҹ�)
            if self.bot.minerals < 150:
                return False
            
            # CRITICAL FIX: ���� ���� ���� (������ ������ �Ҹ����� ����)
            # ���� �ڵ�: if self.bot.vespene < 100: return False  <- �� �κ� ����
            
            # ����ǰ Ȯ��
            if self.bot.supply_left < 2:
                return False
            
            # ��ȭ�� ���� Ȯ��
            if not hatchery.is_ready or not hatchery.is_idle:
                return False
            
            # �̹� �Ҵ�� ������ �ִ��� Ȯ��
            if hatchery.tag in self.queen_assignments:
                assigned_queen = self.bot.units.find_by_tag(self.queen_assignments[hatchery.tag])
                if assigned_queen and assigned_queen.is_alive:
                    return False  # �̹� �Ҵ�� ������ ����
            
            # ���� ����
            if await self._safe_train(hatchery, UnitTypeId.QUEEN):
                # �Ҵ� ���� ������Ʈ�� ������ ������ �Ŀ� ����
                return True
            
            return False
        
        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[WARNING] Queen production error: {e}")
            return False
    
    async def manage_larva_inject(self, queens, hatcheries):
        """
        ��� ���� ����
        
        CRITICAL IMPROVEMENT: ��� ���� ȿ���� ����
        
        Args:
            queens: ���� ���ֵ�
            hatcheries: ��ȭ�� ���ֵ�
        """
        try:
            for hatch in hatcheries:
                hatch_tag = hatch.tag
                
                # Inject ��Ÿ�� Ȯ��
                last_inject = self.last_inject_time.get(hatch_tag, 0.0)
                if self.bot.time - last_inject < self.inject_cooldown:
                    continue
                
                # �Ҵ�� ���� Ȯ��
                assigned_queen_tag = self.queen_assignments.get(hatch_tag)
                assigned_queen = None
                
                if assigned_queen_tag:
                    assigned_queen = self.bot.units.find_by_tag(assigned_queen_tag)
                    if not assigned_queen or not assigned_queen.is_alive:
                        # �Ҵ�� ������ �׾����� �Ҵ� ����
                        del self.queen_assignments[hatch_tag]
                        assigned_queen = None
                
                # �Ҵ�� ������ �ְ� ������ ���
                if assigned_queen:
                    distance = assigned_queen.distance_to(hatch.position)
                    if distance <= self.max_inject_distance:
                        if assigned_queen.energy >= 25:
                            try:
                                await self.bot.do(assigned_queen(AbilityId.EFFECT_INJECTLARVA, hatch))
                                self.last_inject_time[hatch_tag] = self.bot.time
                                continue
                            except Exception:
                                pass
                    # CRITICAL IMPROVEMENT: ������ �ʹ� �ָ� ���Ҵ� ����
                    elif distance > self.max_queen_travel_distance:
                        # �ʹ� �ָ� �ٸ� ���� ã��
                        assigned_queen = None
                
                # �Ҵ�� ������ ���ų� �ָ� ���� ����� ���� ã��
                if not assigned_queen:
                    # CRITICAL IMPROVEMENT: �Ÿ� ���� ��ȭ (20 -> 10)
                    nearby_queens = queens.filter(
                        lambda q: q.distance_to(hatch.position) < 10.0
                        and q.energy >= 25
                        and q.is_idle
                    )
                    
                    if nearby_queens.exists:
                        closest_queen = nearby_queens.closest_to(hatch.position)
                        distance = closest_queen.distance_to(hatch.position)
                        
                        # CRITICAL IMPROVEMENT: Inject �Ÿ� ���� ������ ��� ���
                        if distance <= self.max_inject_distance:
                            try:
                                await self.bot.do(closest_queen(AbilityId.EFFECT_INJECTLARVA, hatch))
                                self.last_inject_time[hatch_tag] = self.bot.time
                                self.queen_assignments[hatch_tag] = closest_queen.tag
                            except Exception:
                                pass
                        # CRITICAL IMPROVEMENT: �ʹ� �ָ� ���� ���� ��ȯ�ϰų� �ٸ� ���� �Ҵ�
                        elif distance > self.max_queen_travel_distance:
                            # �ٸ� ��ȭ�忡 �Ҵ���� ���� ���� ã��
                            unassigned_queens = queens.filter(
                                lambda q: q.tag not in self.queen_assignments.values()
                                and q.energy >= 25
                            )
                            if unassigned_queens.exists:
                                new_queen = unassigned_queens.closest_to(hatch.position)
                                self.queen_assignments[hatch_tag] = new_queen.tag
        
        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[WARNING] Larva inject management error: {e}")
    
    async def _safe_train(self, unit: Unit, unit_type: UnitTypeId) -> bool:
        """������ ���� ����"""
        try:
            result = unit.train(unit_type)
            if hasattr(result, '__await__'):
                await result
            return True
        except Exception:
            return False
