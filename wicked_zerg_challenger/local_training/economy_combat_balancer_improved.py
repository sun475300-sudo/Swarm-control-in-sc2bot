# -*- coding: utf-8 -*-
"""
Economy-Combat Balancer Improved - ����-���� ���� ���� ����

CRITICAL IMPROVEMENTS:
1. �������� ���� ���� (Ȯ�� ��� ��� ���� ���� üũ)
2. ��� ��ǥ ��ġ ���� ���� (60-80��)
3. ���� Ÿ�� �ϵ��ڵ� ���� (���� ���� Ÿ�� ����)
"""

from typing import Dict, List, Optional
from collections import defaultdict

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        DRONE = "DRONE"
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        MUTALISK = "MUTALISK"


class EconomyCombatBalancerImproved:
    """
    ������ ����-���� ���� �����
    
    �ֿ� ���� ����:
    1. �������� ���� ����: Ȯ�� ��� ���� ���� ���� üũ
    2. ��� ��ǥ ����: �Ĺݺ� 60-80�� ��ǥ
    3. ���� ���� Ÿ�� ����: �ϵ��ڵ� ����
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # ���� ���� ���� (�������� ���� ����)
        self.production_history = {
            'drones': 0,
            'army_units': 0,
            'total': 0
        }
        
        # ��� ��ǥ ��ġ (���� ����)
        self.drone_targets = {
            'early': 30,      # �ʹ� (0-6��)
            'mid': 60,        # �߹� (6-12��)
            'late': 80,       # �Ĺ� (12�� ����)
        }
        
        # ��Ƽ ������ ��� ��ǥ
        self.drones_per_base = 16
    
    def should_make_drone(self, current_drone_count: int, army_count: int) -> bool:
        """
        ��� ���� ���� ����
        
        CRITICAL IMPROVEMENT: �������� ���� ���� (Ȯ�� ��� ���)
        
        Args:
            current_drone_count: ���� ��� ��
            army_count: ���� ���� ���� ��
            
        Returns:
            ��� ���� ����
        """
        try:
            # ��ǥ ��� �� ���
            target_drones = self._calculate_target_drones()
            
            # ��ǥ �޼� ���� Ȯ��
            if current_drone_count >= target_drones:
                return False
            
            # CRITICAL IMPROVEMENT: �������� ���� ����
            # Ȯ�� ��� ���� ���� ������ üũ�Ͽ� �ұ��� ����
            total_produced = self.production_history['total']
            
            if total_produced == 0:
                # ù ������ ��� �켱
                return True
            
            # ���� ���� ���� ���
            drone_ratio = self.production_history['drones'] / total_produced if total_produced > 0 else 0.0
            army_ratio = self.production_history['army_units'] / total_produced if total_produced > 0 else 0.0
            
            # ��ǥ ���� ��� (���� ��Ȳ�� ����)
            target_drone_ratio = self._calculate_target_drone_ratio()
            
            # ��ǥ �������� ũ�� ����� ���� ����
            if drone_ratio < target_drone_ratio - 0.1:  # ��ǥ���� 10% �̻� ������
                return True  # ��� ���� ����
            
            if drone_ratio > target_drone_ratio + 0.1:  # ��ǥ���� 10% �̻� ������
                return False  # ���� ���� ����
            
            # ��ǥ ��� �� �̴� �� ��� ����
            if current_drone_count < target_drones:
                return True
            
            return False
        
        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[WARNING] Should make drone decision error: {e}")
            return False
    
    def _calculate_target_drones(self) -> int:
        """
        ��ǥ ��� �� ���
        
        CRITICAL IMPROVEMENT: ��� ��ǥ ���� ���� (60-80��)
        """
        try:
            game_time_minutes = self.bot.time / 60.0
            base_count = self.bot.townhalls.amount
            
            # ���� �ð��� ���� �⺻ ��ǥ
            if game_time_minutes < 6:
                base_target = self.drone_targets['early']
            elif game_time_minutes < 12:
                base_target = self.drone_targets['mid']
            else:
                base_target = self.drone_targets['late']
            
            # ��Ƽ ���� ���� ���� ����
            multi_target = base_count * self.drones_per_base
            
            # �� �� ���� �� ����
            target = max(base_target, multi_target)
            
            return int(target)
        
        except Exception:
            return 30  # �⺻��
    
    def _calculate_target_drone_ratio(self) -> float:
        """��ǥ ��� ���� ���"""
        try:
            game_time_minutes = self.bot.time / 60.0
            
            # ���� �ð��� ���� ��ǥ ����
            if game_time_minutes < 6:
                return 0.7  # �ʹ�: 70% ���
            elif game_time_minutes < 12:
                return 0.5  # �߹�: 50% ���
            else:
                return 0.3  # �Ĺ�: 30% ���
        
        except Exception:
            return 0.5  # �⺻��
    
    def record_production(self, unit_type: UnitTypeId):
        """
        ���� ��� ������Ʈ
        
        Args:
            unit_type: ����� ���� Ÿ��
        """
        self.production_history['total'] += 1
        
        if unit_type == UnitTypeId.DRONE:
            self.production_history['drones'] += 1
        else:
            self.production_history['army_units'] += 1
    
    def count_army_units(self) -> int:
        """
        ���� ���� �� ���
        
        CRITICAL IMPROVEMENT: ���� ���� Ÿ�� ���� (�ϵ��ڵ� ����)
        """
        try:
            army_count = 0
            
            # CRITICAL IMPROVEMENT: �ϵ��ڵ� ����
            # unit.is_army �Ӽ� ��� �Ǵ� ���� ����
            all_units = self.bot.units
            
            for unit in all_units:
                # �ϲ� ����
                if unit.type_id == UnitTypeId.DRONE:
                    continue
                
                # �ǹ� ����
                if unit.is_structure:
                    continue
                
                # ���� ���� (���� ����)
                if unit.type_id == UnitTypeId.QUEEN:
                    continue
                
                # �뱺�� ���� (���� ����)
                if unit.type_id == UnitTypeId.OVERLORD:
                    continue
                
                # �������� ��� ���� �������� ����
                army_count += 1
            
            return army_count
        
        except Exception as e:
            if self.bot.iteration % 200 == 0:
                print(f"[WARNING] Count army units error: {e}")
            return 0
    
    def get_balance_mode(self) -> str:
        """
        ���� ��� ��ȯ
        
        Returns:
            ���� ��� ('FULL_ECONOMY', 'ECONOMY_FOCUS', 'BALANCED', 'COMBAT_FOCUS', 'FULL_COMBAT')
        """
        try:
            drone_count = self.bot.units(UnitTypeId.DRONE).amount
            army_count = self.count_army_units()
            target_drones = self._calculate_target_drones()
            
            # ��� ���� ���
            if drone_count + army_count == 0:
                return 'BALANCED'
            
            drone_ratio = drone_count / (drone_count + army_count)
            target_ratio = target_drones / (target_drones + max(army_count, 10))
            
            # ��ǥ ��� ���� ����
            ratio_diff = drone_ratio - target_ratio
            
            if ratio_diff > 0.2:
                return 'FULL_COMBAT'  # ����� �ʹ� ����
            elif ratio_diff > 0.1:
                return 'COMBAT_FOCUS'
            elif ratio_diff > -0.1:
                return 'BALANCED'
            elif ratio_diff > -0.2:
                return 'ECONOMY_FOCUS'
            else:
                return 'FULL_ECONOMY'  # ����� �ʹ� ����
        
        except Exception:
            return 'BALANCED'
