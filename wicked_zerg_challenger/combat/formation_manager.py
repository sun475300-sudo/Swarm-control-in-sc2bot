# -*- coding: utf-8 -*-
"""
Formation Manager - Terrain Utilization and Formation Control

������ ���:
1. ������ ����(Concave): ���Ÿ� ������ ���� ���δ� �ݿ� ���� ����
2. ��� ����(Choke Point): ���� ��񿡼��� ������ ��ġ ����
3. �������� Ȱ��: ���, ��ֹ� ���� Ȱ���� ����
"""

from typing import Dict, List, Optional, Tuple, Set
from sc2.unit import Unit
from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.game_info import GameInfo


class FormationManager:
    """���� ������ - ������ ����, ��� ����, ���� Ȱ��"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # ���Ÿ� ���� Ÿ��
        self.ranged_units = {
            UnitTypeId.HYDRALISK,
            UnitTypeId.ROACH,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.MUTALISK,
        }
        
        # ���� ���� Ÿ��
        self.melee_units = {
            UnitTypeId.ZERGLING,
            UnitTypeId.ULTRALISK,
            UnitTypeId.BANELING,
        }
    
    def form_concave(self, units: Units, enemy_center: Point2) -> List[Tuple[Unit, Point2]]:
        """
        ������ ����(Concave) ����
        
        ���Ÿ� ������ ���� ���δ� �ݿ� ���·� ��ġ�Ͽ� ȭ���� ���߽�Ŵ
        
        Args:
            units: �Ʊ� ���� ���
            enemy_center: ���� �߽� ��ġ
            
        Returns:
            (����, ��ǥ ��ġ) Ʃ�� ����Ʈ
        """
        if not units.exists:
            return []
        
        # ���Ÿ� ���ְ� ���� ���� �и�
        ranged = [u for u in units if u.type_id in self.ranged_units]
        melee = [u for u in units if u.type_id in self.melee_units]
        
        assignments = []
        
        # ���Ÿ� ����: �ݿ� ���·� ��ġ
        if ranged and enemy_center:
            # �ݿ��� ������ (������ �Ÿ�)
            radius = 8.0  # ���Ÿ� ������ ��Ÿ� ����
            
            # �ݿ��� �߽��� (���� ����)
            if self.bot.townhalls.exists:
                our_base = self.bot.townhalls.first
                direction = (enemy_center - our_base.position).normalized()
            else:
                direction = Point2((1, 0))  # �⺻ ����
            
            # �ݿ� ���·� ��ġ
            angle_step = 180.0 / max(len(ranged), 1)  # 180�� �ݿ�
            
            for i, unit in enumerate(ranged):
                angle = (i * angle_step - 90.0) * 3.14159 / 180.0  # ���� ��ȯ
                
                # �ݿ� ��ġ ���
                offset_x = radius * direction.x * abs(angle) / 1.57
                offset_y = radius * direction.y * abs(angle) / 1.57
                
                target_pos = enemy_center + Point2((offset_x, offset_y))
                assignments.append((unit, target_pos))
        
        # ���� ����: ���� ���ʿ� ��ġ
        if melee and enemy_center:
            for i, unit in enumerate(melee):
                # ���� ���ʿ� ��ġ
                if self.bot.townhalls.exists:
                    our_base = self.bot.townhalls.first
                    direction = (enemy_center - our_base.position).normalized()
                else:
                    direction = Point2((1, 0))
                
                target_pos = enemy_center - direction * 3.0  # �� �� 3 �Ÿ�
                assignments.append((unit, target_pos))
        
        return assignments
    
    def find_choke_points(self, map_info: GameInfo) -> List[Point2]:
        """
        ���(Choke Point) ã��
        
        ���� ��γ� �Ա��� ã�� ������ ��ġ�� Ȱ��
        
        Args:
            map_info: ���� �� ����
            
        Returns:
            ��� ��ġ ����Ʈ
        """
        choke_points = []
        
        # ������ ����: �츮 ������ �� ���� ������ �ֿ� ���
        if self.bot.townhalls.exists and self.bot.enemy_start_locations:
            our_base = self.bot.townhalls.first
            enemy_start = self.bot.enemy_start_locations[0]
            
            # �߰� �������� ��� �ĺ��� ����
            mid_point = our_base.position.towards(enemy_start, 20.0)
            choke_points.append(mid_point)
        
        return choke_points
    
    def should_avoid_choke(self, units: Units, enemy_units: Units) -> bool:
        """
        ��񿡼� �ο��� ���ƾ� �ϴ��� �Ǵ�
        
        ���� ��񿡼� �ټ��� ���� �ο�� �Ҹ��ϹǷ� ���� ������ ����
        
        Args:
            units: �Ʊ� ����
            enemy_units: �� ����
            
        Returns:
            ����� ���ؾ� �ϸ� True
        """
        if not units.exists or not enemy_units.exists:
            return False
        
        # �Ʊ��� ������ ���� Ȯ��
        our_count = len(units)
        enemy_count = len(enemy_units)
        
        # ���� ���� ���� ������ ������ ���ؾ� ��
        if enemy_count > our_count * 1.5:
            # ������ �����ִ��� Ȯ��
            if enemy_units.exists:
                enemy_positions = [e.position for e in enemy_units]
                avg_enemy_pos = Point2((
                    sum(p.x for p in enemy_positions) / len(enemy_positions),
                    sum(p.y for p in enemy_positions) / len(enemy_positions)
                ))
                
                # ������ �����ִ� ���� (ǥ������)
                distances = [p.distance_to(avg_enemy_pos) for p in enemy_positions]
                avg_distance = sum(distances) / len(distances) if distances else 0
                
                # ������ �ſ� ���������� (���� ����) ���ؾ� ��
                if avg_distance < 5.0:
                    return True
        
        return False
    
    def get_optimal_position(self, unit: Unit, enemy_center: Point2, formation_type: str = "concave") -> Point2:
        """
        ���� ��ġ ���
        
        Args:
            unit: ����
            enemy_center: ���� �߽� ��ġ
            formation_type: ���� Ÿ�� ("concave", "line", "surround")
            
        Returns:
            ���� ��ġ
        """
        if formation_type == "concave":
            # ������ ����
            if unit.type_id in self.ranged_units:
                # ���Ÿ� ����: ���� ���δ� ��ġ
                if self.bot.townhalls.exists:
                    our_base = self.bot.townhalls.first
                    direction = (enemy_center - our_base.position).normalized()
                else:
                    direction = Point2((1, 0))
                
                # ���� ����/���� ��ġ
                radius = 8.0
                perpendicular = Point2((-direction.y, direction.x))  # ���� ����
                target_pos = enemy_center + perpendicular * radius
                return target_pos
            else:
                # ���� ����: ���� ����
                if self.bot.townhalls.exists:
                    our_base = self.bot.townhalls.first
                    direction = (enemy_center - our_base.position).normalized()
                else:
                    direction = Point2((1, 0))
                
                return enemy_center - direction * 3.0
        
        # �⺻: ������ ����� ��ġ
        return enemy_center
