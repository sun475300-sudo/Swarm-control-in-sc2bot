# -*- coding: utf-8 -*-
"""
Intel Manager - Advanced Intelligence Analysis

������ ���:
1. ��ũ Ʈ�� �߷�: �ǹ�, ���� ä�뷮, ���� ���� Ÿ�̹��� ���� �� �ǵ� ����
2. ���� �Ȱ� ����: �뱺��/���۸��� ���� �ǽð� �� ���� ����
3. ������ ��: ���� ���� �ǵ� �� ���� ����
"""

from typing import Dict, List, Optional, Tuple, Set, Any
from collections import defaultdict
from sc2.unit import Unit
from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.game_info import GameInfo


class IntelManager:
    """���� �м� �� ���� ���� ������"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # ������ �� �ǹ�/���� ���
        self.observed_buildings: Dict[UnitTypeId, List[float]] = defaultdict(list)  # unit_type -> [game_times]
        self.observed_units: Dict[UnitTypeId, List[float]] = defaultdict(list)
        
        # ���� ä�뷮 ����
        self.enemy_gas_timings: List[Tuple[float, int]] = []  # (game_time, gas_count)
        
        # ��ũ Ʈ�� �߷�
        self.inferred_tech: Set[UnitTypeId] = set()
        self.inferred_strategy: Optional[str] = None
        
        # ���� �Ȱ� ����
        self.fog_of_war_positions: Dict[Point2, float] = {}  # position -> last_seen_time
        self.scout_units: List[int] = []  # unit tags for scout units
        
        # ������ ��
        self.threat_level: float = 0.0  # 0.0 ~ 1.0
        self.attack_intent: bool = False
        
    def update(self, iteration: int):
        """�� ������ ������Ʈ"""
        try:
            self._update_observations()
            self._infer_tech_tree()
            self._evaluate_threat()
            self._manage_fog_of_war()
        except Exception as e:
            if iteration % 200 == 0:
                print(f"[WARNING] IntelManager.update() error: {e}")
    
    def _update_observations(self):
        """������ �� �ǹ�/���� ��� ������Ʈ"""
        current_time = self.bot.time
        
        # �� �ǹ� ����
        for enemy_building in self.bot.enemy_structures:
            building_type = enemy_building.type_id
            if current_time not in self.observed_buildings[building_type]:
                self.observed_buildings[building_type].append(current_time)
        
        # �� ���� ����
        for enemy_unit in self.bot.enemy_units:
            unit_type = enemy_unit.type_id
            if current_time not in self.observed_units[unit_type]:
                self.observed_units[unit_type].append(current_time)
        
        # ���� ����� ���� ����
        gas_count = len(self.bot.enemy_structures.filter(
            lambda s: s.type_id in [UnitTypeId.REFINERY, UnitTypeId.ASSIMILATOR, UnitTypeId.EXTRACTOR]
        ))
        if gas_count > 0:
            self.enemy_gas_timings.append((current_time, gas_count))
    
    def _infer_tech_tree(self):
        """��ũ Ʈ�� �߷� - ������ �ʴ� ���� �ǵ� ����"""
        self.inferred_tech.clear()
        
        # 1. �ǹ� ��� �߷�
        if UnitTypeId.STARGATE in self.observed_buildings:
            self.inferred_tech.add(UnitTypeId.VOIDRAY)
            self.inferred_tech.add(UnitTypeId.CARRIER)
            self.inferred_strategy = "air"
        
        if UnitTypeId.DARKSHRINE in self.observed_buildings:
            self.inferred_tech.add(UnitTypeId.DARKTEMPLAR)
            self.inferred_strategy = "dt_drop"  # ���� ��� ��� ����
        
        if UnitTypeId.FACTORY in self.observed_buildings:
            self.inferred_tech.add(UnitTypeId.SIEGETANK)
            self.inferred_tech.add(UnitTypeId.HELLION)
        
        # 2. ���� ä�뷮 ��� �߷�
        # ������ ���� ä���ϸ� ���� ���� ���� ����
        recent_gas = [g for g in self.enemy_gas_timings if self.bot.time - g[0] < 60.0]
        if recent_gas:
            avg_gas = sum(g[1] for g in recent_gas) / len(recent_gas)
            if avg_gas >= 2:
                # ���� 2�� �̻� = ���� ���� ���� ����
                if UnitTypeId.GATEWAY in self.observed_buildings:
                    self.inferred_tech.add(UnitTypeId.HIGHTEMPLAR)
                    self.inferred_tech.add(UnitTypeId.ARCHON)
        
        # 3. ���� ���� Ÿ�̹� ��� �߷�
        # 12�� (12 Pool) ����: �ſ� ���� ���۸� ����
        if UnitTypeId.SPAWNINGPOOL in self.observed_buildings:
            pool_time = min(self.observed_buildings[UnitTypeId.SPAWNINGPOOL])
            if pool_time < 60.0:  # 1�� �̳� Ǯ �Ǽ�
                self.inferred_strategy = "12_pool_rush"
                self.threat_level = 0.9  # �ſ� ����
        
        # 4. �׶� ���� �߷�
        if UnitTypeId.BARRACKS in self.observed_buildings:
            barracks_time = min(self.observed_buildings[UnitTypeId.BARRACKS])
            if barracks_time < 90.0:  # ���� �跰
                self.inferred_strategy = "early_marine_rush"
                self.threat_level = 0.7
    
    def _evaluate_threat(self):
        """������ ��"""
        threat = 0.0
        
        # 1. �� ���� ũ��
        enemy_army_supply = sum(
            getattr(u, 'supply_cost', 0) or 0
            for u in self.bot.enemy_units
            if u.type_id not in [UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE]
        )
        our_army_supply = getattr(self.bot, 'supply_army', 0) or 0
        
        if enemy_army_supply > 0:
            supply_ratio = enemy_army_supply / max(our_army_supply, 1)
            threat += min(supply_ratio * 0.3, 0.3)
        
        # 2. ���� �츮 ���� ��ó�� �ִ���
        if self.bot.enemy_units:
            our_bases = self.bot.townhalls
            if our_bases.exists:
                main_base = our_bases.first
                nearby_enemies = [
                    e for e in self.bot.enemy_units
                    if e.distance_to(main_base) < 20.0
                ]
                if nearby_enemies:
                    threat += 0.4
                    self.attack_intent = True
        
        # 3. ������ ���� ����
        high_threat_units = [
            UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED,
            UnitTypeId.HIGHTEMPLAR, UnitTypeId.ARCHON,
            UnitTypeId.COLOSSUS, UnitTypeId.CARRIER
        ]
        for unit_type in high_threat_units:
            if unit_type in self.observed_units:
                threat += 0.2
        
        self.threat_level = min(threat, 1.0)
    
    def _manage_fog_of_war(self):
        """���� �Ȱ� ���� - �뱺��/���۸��� ���� �� ���� ����"""
        current_time = self.bot.time
        
        # �뱺�ָ� �ֿ� �̵� ��ο� ��ġ
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if overlords.exists:
            # �� ������ ���� ��ο� �뱺�� ��ġ
            enemy_start = self.bot.enemy_start_locations[0] if self.bot.enemy_start_locations else None
            if enemy_start:
                for overlord in overlords.idle[:3]:  # �ִ� 3���� ��ī��Ʈ
                    # �� ������ �츮 ���� ������ �߰� ������ ��ġ
                    if self.bot.townhalls.exists:
                        our_base = self.bot.townhalls.first
                        scout_position = our_base.position.towards(enemy_start, 30.0)
                        overlord.move(scout_position)
        
        # ���۸� �� �⸦ �ֿ� ��ο� ��ġ
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings.exists and len(self.scout_units) < 2:
            # ���� ��ī��Ʈ�� �������� ���� ���۸� ����
            available_lings = [z for z in zerglings if z.tag not in self.scout_units]
            if available_lings:
                scout_ling = available_lings[0]
                self.scout_units.append(scout_ling.tag)
                # �� ���� �������� �̵�
                if self.bot.enemy_start_locations:
                    enemy_start = self.bot.enemy_start_locations[0]
                    scout_ling.move(enemy_start)
    
    def get_inferred_strategy(self) -> Optional[str]:
        """�߷е� �� ���� ��ȯ"""
        return self.inferred_strategy
    
    def get_threat_level(self) -> float:
        """������ ��ȯ (0.0 ~ 1.0)"""
        return self.threat_level
    
    def is_under_attack(self) -> bool:
        """���� �ް� �ִ��� ����"""
        return self.attack_intent
    
    def get_inferred_tech(self) -> Set[UnitTypeId]:
        """�߷е� �� ��ũ ��ȯ"""
        return self.inferred_tech.copy()
