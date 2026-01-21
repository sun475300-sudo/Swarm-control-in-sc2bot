# -*- coding: utf-8 -*-
"""
Micro Combat Manager

CombatManager에서 분리된 마이크로 전투 기능
Boids 알고리즘 기반 군집 제어 통합
"""

from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
    except ImportError:
        # Fallback for type checking without SC2
        Units = object
        Unit = object
        Point2 = object
else:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
        from sc2.ids.unit_typeid import UnitTypeId
    except ImportError:
        Units = object
        Unit = object
        Point2 = object
        UnitTypeId = object

try:
    from combat.boids_swarm_control import BoidsSwarmController
    BOIDS_AVAILABLE = True
except ImportError:
    BOIDS_AVAILABLE = False
    BoidsSwarmController = None


class MicroCombat:
    """마이크로 전투 관리 (Boids 알고리즘 통합)"""

    def __init__(self, bot):
        self.bot = bot
        self._base_weights = None
        # Boids 알고리즘 컨트롤러 초기화
        if BOIDS_AVAILABLE:
            self.boids_controller = BoidsSwarmController(
                separation_weight=1.5,
                alignment_weight=1.0,
                cohesion_weight=1.0,
                separation_radius=2.0,
                neighbor_radius=5.0,
                max_speed=3.0,
                max_force=0.5
            )
        else:
            self.boids_controller = None

    async def micro_units(self, units: "Units", target: "Unit") -> bool:
        """
        유닛 마이크로 관리 (Boids 알고리즘 적용)
        
        Boids 알고리즘을 사용하여 유닛들이 서로 겹치지 않으면서
        적을 부드럽게 감싸는 형태의 무빙을 구현합니다.
        """
        if not units or not target:
            return False
        
        if not self.boids_controller:
            # Boids가 없으면 기본 동작
            for unit in units:
                if unit.is_idle:
                    await self.bot.do(unit.attack(target))
            return True
        
        try:
            # Boids 알고리즘으로 목표 위치 계산
            target_pos = target.position
            enemy_units = self.bot.enemy_units if hasattr(self.bot, 'enemy_units') else None
            self._apply_splash_avoidance(units, enemy_units)
            self._apply_flow_control(units, target_pos)
            
            # 각 유닛에 대해 Boids 적용
            unit_targets = self.boids_controller.apply_boids_to_units(
                units=units,
                target=target_pos,
                enemy_units=enemy_units
            )
            
            # 계산된 목표 위치로 이동
            for unit, target_position in unit_targets:
                if unit.is_idle or unit.is_moving:
                    # 목표 위치로 이동 (적과 가까우면 공격)
                    distance_to_enemy = unit.distance_to(target)
                    if distance_to_enemy <= unit.attack_range:
                        await self.bot.do(unit.attack(target))
                    else:
                        await self.bot.do(unit.move(target_position))
            
            return True
        except Exception as e:
            # 에러 발생 시 기본 동작
            for unit in units:
                if unit.is_idle:
                    await self.bot.do(unit.attack(target))
            return False
        finally:
            self._restore_weights()

    async def kiting(self, units: "Units", enemy: "Units") -> bool:
        """
        키팅 (공격 후 후퇴) - Boids 알고리즘 통합
        
        유닛들이 적을 공격한 후 Boids 알고리즘으로 자연스럽게 후퇴합니다.
        """
        if not units or not enemy:
            return False
        
        if not self.boids_controller:
            # 기본 키팅 로직
            for unit in units:
                closest_enemy = enemy.closest_to(unit.position)
                if closest_enemy:
                    if unit.weapon_cooldown == 0:
                        await self.bot.do(unit.attack(closest_enemy))
                    else:
                        # 공격 쿨타임 중이면 후퇴
                        retreat_pos = unit.position.towards(closest_enemy.position, -3.0)
                        await self.bot.do(unit.move(retreat_pos))
            return True
        
        try:
            self._apply_splash_avoidance(units, enemy)
            # Boids 알고리즘으로 적 회피 + 공격
            for unit in units:
                closest_enemy = enemy.closest_to(unit.position)
                if not closest_enemy:
                    continue
                
                # 이웃 유닛들
                neighbors = units.closer_than(5.0, unit.position)
                
                # 적 회피 힘 계산
                avoidance_force = self.boids_controller._calculate_enemy_avoidance(
                    unit, enemy
                )
                
                # 공격 가능한지 확인
                if unit.weapon_cooldown == 0 and unit.distance_to(closest_enemy) <= unit.attack_range:
                    await self.bot.do(unit.attack(closest_enemy))
                else:
                    # 후퇴 (적 회피 방향으로)
                    retreat_pos = Point2((
                        unit.position.x + avoidance_force[0] * 3.0,
                        unit.position.y + avoidance_force[1] * 3.0
                    ))
                    await self.bot.do(unit.move(retreat_pos))
            
            return True
        except Exception:
            return False
        finally:
            self._restore_weights()

    async def stutter_step(self, units: "Units", target: "Unit") -> bool:
        """
        스터터 스텝 (이동-공격 반복) - Boids 알고리즘 통합
        """
        if not units or not target:
            return False
        
        if not self.boids_controller:
            # 기본 스터터 스텝
            for unit in units:
                if unit.weapon_cooldown == 0:
                    await self.bot.do(unit.attack(target))
                else:
                    # 공격 쿨타임 중이면 이동
                    move_pos = unit.position.towards(target.position, 2.0)
                    await self.bot.do(unit.move(move_pos))
            return True
        
        try:
            self._apply_splash_avoidance(units, self.bot.enemy_units if hasattr(self.bot, "enemy_units") else None)
            self._apply_flow_control(units, target.position)
            # Boids 알고리즘으로 이동하면서 공격
            for unit in units:
                if unit.weapon_cooldown == 0:
                    await self.bot.do(unit.attack(target))
                else:
                    # Boids로 계산된 위치로 이동
                    neighbors = units.closer_than(5.0, unit.position)
                    velocity_x, velocity_y = self.boids_controller.calculate_swarm_velocity(
                        unit=unit,
                        neighbors=neighbors,
                        target=target.position
                    )
                    move_pos = Point2((
                        unit.position.x + velocity_x,
                        unit.position.y + velocity_y
                    ))
                    await self.bot.do(unit.move(move_pos))
            return True
        except Exception:
            return False
        finally:
            self._restore_weights()

    async def focus_fire(self, units: "Units", target: "Unit") -> bool:
        """
        집중 공격 - Boids 알고리즘으로 적을 포위하면서 집중 공격
        """
        if not units or not target:
            return False
        
        try:
            self._apply_splash_avoidance(units, self.bot.enemy_units if hasattr(self.bot, "enemy_units") else None)
            self._apply_flow_control(units, target.position)
            # 모든 유닛이 같은 타겟을 공격
            for unit in units:
                if unit.distance_to(target) <= unit.attack_range:
                    await self.bot.do(unit.attack(target))
                else:
                    # Boids 알고리즘으로 적을 포위하면서 접근
                    if self.boids_controller:
                        neighbors = units.closer_than(5.0, unit.position)
                        enemy_units = self.bot.enemy_units if hasattr(self.bot, 'enemy_units') else None
                        
                        velocity_x, velocity_y = self.boids_controller.calculate_swarm_velocity(
                            unit=unit,
                            neighbors=neighbors,
                            target=target.position,
                            enemy_units=enemy_units
                        )
                        move_pos = Point2((
                            unit.position.x + velocity_x,
                            unit.position.y + velocity_y
                        ))
                        await self.bot.do(unit.move(move_pos))
                    else:
                        # 기본 이동
                        await self.bot.do(unit.move(target.position))
            return True
        except Exception:
            return False
        finally:
            self._restore_weights()

    async def attack_assigned_targets(self, units: "Units", assignments: dict) -> bool:
        """
        오버킬 분산 타겟 할당 기반 공격
        """
        if not units or not assignments:
            return False
        try:
            self._apply_splash_avoidance(units, self.bot.enemy_units if hasattr(self.bot, "enemy_units") else None)
            for unit in units:
                target = assignments.get(unit.tag)
                if not target:
                    continue
                if unit.distance_to(target) <= unit.attack_range:
                    await self.bot.do(unit.attack(target))
                else:
                    await self.bot.do(unit.move(target.position))
            return True
        except Exception:
            return False
        finally:
            self._restore_weights()

    async def split_units(self, units: "Units", enemy: "Units") -> bool:
        """
        유닛 분산 (스플릿) - Boids 알고리즘의 Separation 강화
        """
        if not units or not enemy:
            return False
        
        if not self.boids_controller:
            # 기본 분산 로직
            for unit in units:
                closest_enemy = enemy.closest_to(unit.position)
                if closest_enemy:
                    # 적으로부터 멀어지는 방향으로 이동
                    retreat_pos = unit.position.towards(closest_enemy.position, -5.0)
                    await self.bot.do(unit.move(retreat_pos))
            return True
        
        try:
            self._apply_splash_avoidance(units, enemy, force_split=True)
            # Boids 알고리즘의 분리 힘을 강화하여 분산
            # Separation 가중치를 높여서 유닛들이 더 멀어지도록
            original_separation = self.boids_controller.separation_weight
            self.boids_controller.separation_weight = 3.0  # 분리 강화
            
            for unit in units:
                neighbors = units.closer_than(5.0, unit.position)
                velocity_x, velocity_y = self.boids_controller.calculate_swarm_velocity(
                    unit=unit,
                    neighbors=neighbors,
                    enemy_units=enemy
                )
                move_pos = Point2((
                    unit.position.x + velocity_x,
                    unit.position.y + velocity_y
                ))
                await self.bot.do(unit.move(move_pos))
            
            # 원래 가중치로 복원
            self.boids_controller.separation_weight = original_separation
            return True
        except Exception:
            return False
        finally:
            self._restore_weights()

    def _apply_splash_avoidance(self, units: "Units", enemy_units, force_split: bool = False) -> None:
        if not self.boids_controller or not enemy_units or not units:
            return
        if self._base_weights is None:
            self._base_weights = {
                "separation_weight": self.boids_controller.separation_weight,
                "alignment_weight": self.boids_controller.alignment_weight,
                "cohesion_weight": self.boids_controller.cohesion_weight,
                "separation_radius": self.boids_controller.separation_radius,
                "neighbor_radius": self.boids_controller.neighbor_radius,
            }

        splash_types = {
            UnitTypeId.BANELING,
            UnitTypeId.SIEGETANK,
            UnitTypeId.SIEGETANKSIEGED,
            UnitTypeId.HIGHTEMPLAR,
            UnitTypeId.DISRUPTOR,
            UnitTypeId.COLOSSUS,
            UnitTypeId.THOR,
            UnitTypeId.LURKER,
            UnitTypeId.LURKERBURROWED,
        }
        enemy_has_splash = any(getattr(e, "type_id", None) in splash_types for e in enemy_units)

        if enemy_has_splash or force_split:
            muta_count = sum(1 for u in units if u.type_id == UnitTypeId.MUTALISK)
            multiplier = 8.0 if muta_count > 0 else 5.0
            self.boids_controller.separation_weight = self._base_weights["separation_weight"] * multiplier
            self.boids_controller.cohesion_weight = self._base_weights["cohesion_weight"] * 0.6
            self.boids_controller.separation_radius = max(
                self._base_weights["separation_radius"], 3.5 if muta_count > 0 else 2.5
            )
            self.boids_controller.neighbor_radius = max(
                self._base_weights["neighbor_radius"], 7.0 if muta_count > 0 else 5.5
            )

    def _apply_flow_control(self, units: "Units", target_pos: "Point2") -> None:
        if not self.boids_controller or not units:
            return
        if units.amount < 4:
            return
        center_x = sum(u.position.x for u in units) / units.amount
        center_y = sum(u.position.y for u in units) / units.amount
        avg_dist = sum(u.distance_to(Point2((center_x, center_y))) for u in units) / units.amount
        if avg_dist < 2.0:
            if self._base_weights is None:
                self._base_weights = {
                    "separation_weight": self.boids_controller.separation_weight,
                    "alignment_weight": self.boids_controller.alignment_weight,
                    "cohesion_weight": self.boids_controller.cohesion_weight,
                    "separation_radius": self.boids_controller.separation_radius,
                    "neighbor_radius": self.boids_controller.neighbor_radius,
                }
            self.boids_controller.cohesion_weight = self._base_weights["cohesion_weight"] * 0.4
            self.boids_controller.alignment_weight = self._base_weights["alignment_weight"] * 0.7

    def _restore_weights(self) -> None:
        if not self.boids_controller or not self._base_weights:
            return
        self.boids_controller.separation_weight = self._base_weights["separation_weight"]
        self.boids_controller.alignment_weight = self._base_weights["alignment_weight"]
        self.boids_controller.cohesion_weight = self._base_weights["cohesion_weight"]
        self.boids_controller.separation_radius = self._base_weights["separation_radius"]
        self.boids_controller.neighbor_radius = self._base_weights["neighbor_radius"]
        self._base_weights = None
