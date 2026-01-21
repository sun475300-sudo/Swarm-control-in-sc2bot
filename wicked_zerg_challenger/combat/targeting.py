# -*- coding: utf-8 -*-
"""
Targeting Manager - Advanced Target Selection Logic

구현된 기능:
1. 체력 우선 타겟팅: 체력이 낮아 한두 방에 잡을 수 있는 유닛 우선 공격
2. 위협도 우선 타겟팅: 아군에게 큰 피해를 주는 유닛 우선순위 부여
3. 사거리 고려: 현재 공격 가능 범위 내에 있는 타겟을 우선시
"""

from typing import Dict, List, Optional, Tuple, Set, Any, Union, cast, TYPE_CHECKING
from pathlib import Path
from datetime import datetime, timezone
import csv
if TYPE_CHECKING:
    from sc2.unit import Unit  # type: ignore[import-not-found]
    from sc2.units import Units  # type: ignore[import-not-found]
    from sc2.ids.unit_typeid import UnitTypeId  # type: ignore[import-not-found]
    from sc2.ids.ability_id import AbilityId  # type: ignore[import-not-found]
else:
    try:
        from sc2.unit import Unit
        from sc2.units import Units
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.ids.ability_id import AbilityId
    except Exception:
        Unit = Any
        Units = Any
        UnitTypeId = Any
        AbilityId = Any


class Targeting:
    """타겟팅 관리 - 체력 우선, 위협도 우선, 사거리 고려"""

    def __init__(self, bot):
        self.bot = bot
        
        # 위협도가 높은 유닛 타입 (우선 공격 대상)
        self.high_threat_units = {
            # 테란
            UnitTypeId.SIEGETANK,
            UnitTypeId.SIEGETANKSIEGED,
            UnitTypeId.THOR,
            UnitTypeId.BATTLECRUISER,
            UnitTypeId.LIBERATOR,
            UnitTypeId.LIBERATORAG,
            UnitTypeId.GHOST,
            # 프로토스
            UnitTypeId.HIGHTEMPLAR,
            UnitTypeId.ARCHON,
            UnitTypeId.COLOSSUS,
            UnitTypeId.IMMORTAL,
            UnitTypeId.DISRUPTOR,
            UnitTypeId.CARRIER,
            # 저그
            UnitTypeId.BROODLORD,
            UnitTypeId.ULTRALISK,
            UnitTypeId.LURKER,
            UnitTypeId.LURKERBURROWED,
        }
        
        # 중간 위협도 유닛
        self.medium_threat_units = {
            UnitTypeId.MARINE,
            UnitTypeId.MARAUDER,
            UnitTypeId.STALKER,
            UnitTypeId.ROACH,
            UnitTypeId.HYDRALISK,
        }

        # Tunable params (can be overridden via bot.targeting_params dict)
        self.params = {
            "threat_high": 1000.0,
            "threat_medium": 500.0,
            "health_thresholds": (0.3, 0.5, 0.7),
            "health_scores": (800.0, 400.0, 200.0),
            "supply_weight": 10.0,
            "siegetank_bonus": 500.0,
            "hightemplar_bonus": 600.0,
            "distance_bonus_max": 10.0,
            "distance_bonus_weight": 10.0,
            "overkill_ratio": 1.1,
            "default_damage": 5.0,
            "stats_enabled": True,
            "stats_interval": 200,
            "missing_confirm_seconds": 5.0,
            "stats_csv_mode": "combat",  # combat or game
            "stats_csv_dir": "logs",
        }
        override = getattr(self.bot, "targeting_params", None)
        if isinstance(override, dict):
            self.params.update(override)

        # Overkill distribution stats
        self._distribution_rates: List[float] = []
        self._target_first_assigned: Dict[int, float] = {}
        self._target_last_seen: Dict[int, float] = {}
        self._target_lifetimes: List[float] = []

        # Combat/game tracking for CSV split
        self._combat_active = False
        self._combat_id = 0
        self._game_id = self._resolve_game_id()

        # Unit damage table (approximate, can be overridden)
        self.damage_table = {
            UnitTypeId.ZERGLING: 5.0,
            UnitTypeId.BANELING: 20.0,
            UnitTypeId.ROACH: 16.0,
            UnitTypeId.RAVAGER: 16.0,
            UnitTypeId.HYDRALISK: 12.0,
            UnitTypeId.MUTALISK: 9.0,
            UnitTypeId.ULTRALISK: 35.0,
            UnitTypeId.CORRUPTOR: 10.0,
            UnitTypeId.BROODLORD: 20.0,
        }
        override_table = self.params.get("damage_table")
        if isinstance(override_table, dict):
            self.damage_table.update(override_table)

    def select_target(self, unit: Unit, enemies: Units) -> Optional[Unit]:
        """
        단일 유닛을 위한 타겟 선택
        
        Args:
            unit: 공격할 아군 유닛
            enemies: 적 유닛 목록
            
        Returns:
            최적 타겟 유닛 또는 None
        """
        if not enemies.exists:
            return None
        
        # 사거리 내 적 유닛 필터링
        attack_range = self._get_attack_range(unit)
        enemies_in_range = [e for e in enemies if unit.distance_to(e) <= attack_range]
        
        if not enemies_in_range:
            # 사거리 밖이면 가장 가까운 적 반환 (이동 후 공격)
            return enemies.closest_to(unit)
        
        # 사거리 내 적들 중 최적 타겟 선택
        return self._select_best_target(unit, enemies_in_range)

    def prioritize_targets(self, enemies: Units) -> List[Unit]:
        """
        타겟 우선순위 결정 (전체 적 유닛 정렬)
        
        Args:
            enemies: 적 유닛 목록
            
        Returns:
            우선순위가 높은 순서로 정렬된 적 유닛 리스트
        """
        if not enemies.exists:
            return []
        
        # 각 적 유닛의 우선순위 점수 계산
        scored_targets = []
        for enemy in enemies:
            score = self.calculate_target_value(enemy)
            scored_targets.append((score, enemy))
        
        # 점수 높은 순으로 정렬
        scored_targets.sort(key=lambda x: x[0], reverse=True)
        
        return [target for _, target in scored_targets]

    def calculate_target_value(self, target: Unit) -> float:
        """
        타겟 가치 계산 (우선순위 점수)
        
        계산 요소:
        1. 위협도 (높을수록 높은 점수)
        2. 체력 비율 (낮을수록 높은 점수 - 한두 방에 잡을 수 있는 유닛 우선)
        3. 가치 (비용/보급품)
        
        Args:
            target: 타겟 유닛
            
        Returns:
            우선순위 점수 (높을수록 우선 공격)
        """
        score = 0.0
        
        # 1. 위협도 점수
        if target.type_id in self.high_threat_units:
            score += self.params["threat_high"]
        elif target.type_id in self.medium_threat_units:
            score += self.params["threat_medium"]
        
        # 2. 체력 비율 점수 (체력이 낮을수록 높은 점수)
        if hasattr(target, 'health') and hasattr(target, 'health_max'):
            if target.health_max > 0:
                health_ratio = target.health / target.health_max
                t1, t2, t3 = self.params["health_thresholds"]
                s1, s2, s3 = self.params["health_scores"]
                if health_ratio <= t1:
                    score += s1
                elif health_ratio <= t2:
                    score += s2
                elif health_ratio <= t3:
                    score += s3
        
        # 3. 가치 점수 (비용이 높은 유닛 우선)
        # 보급품을 기준으로 가치 계산
        supply_cost = getattr(target, 'supply_cost', 0) or 0
        if supply_cost > 0:
            score += supply_cost * self.params["supply_weight"]
        
        # 4. 특수 유닛 보너스
        # 공성 전차, 고위 기사 등 특수 유닛 추가 점수
        if target.type_id == UnitTypeId.SIEGETANKSIEGED:
            score += self.params["siegetank_bonus"]
        elif target.type_id == UnitTypeId.HIGHTEMPLAR:
            score += self.params["hightemplar_bonus"]
        
        return score

    def find_best_target(self, units: Units, enemies: Units) -> Optional[Unit]:
        """
        최적 타겟 찾기 (여러 아군 유닛을 위한 공통 타겟)
        
        Args:
            units: 아군 유닛 목록
            enemies: 적 유닛 목록
            
        Returns:
            최적 타겟 유닛 또는 None
        """
        if not enemies.exists or not units.exists:
            return None
        
        # 우선순위가 높은 적 유닛 선택
        prioritized = self.prioritize_targets(enemies)
        
        if not prioritized:
            return None
        
        # 가장 우선순위가 높은 적 유닛 반환
        return prioritized[0]

    def assign_targets(self, units: Units, enemies: Units) -> Dict[int, Unit]:
        """
        오버킬 방지 타겟 할당

        각 적 유닛의 남은 체력 대비 예상 데미지를 고려해
        동일 타겟 과집중을 줄입니다.
        """
        assignments: Dict[int, Unit] = {}
        if not enemies.exists or not units.exists:
            return assignments

        # 예상 피해 누적치 (enemy.tag -> damage)
        expected_damage: Dict[int, float] = {}
        prioritized = self.prioritize_targets(enemies)

        for unit in units:
            target = self._select_overkill_aware_target(unit, prioritized, expected_damage)
            if target is None:
                continue
            assignments[unit.tag] = target
            expected_damage[target.tag] = expected_damage.get(target.tag, 0.0) + self._estimate_unit_damage(unit, target)

        self._update_target_stats(enemies, assignments)
        return assignments

    def _select_overkill_aware_target(
        self,
        unit: Unit,
        prioritized_targets: List[Unit],
        expected_damage: Dict[int, float]
    ) -> Optional[Unit]:
        """
        오버킬을 피하는 타겟 선택
        """
        for enemy in prioritized_targets:
            remaining = getattr(enemy, "health", 0) + getattr(enemy, "shield", 0)
            projected = expected_damage.get(enemy.tag, 0.0) + self._estimate_unit_damage(unit, enemy)
            # 이미 충분한 화력이 예약된 타겟이면 다음 타겟 선택
            if remaining > 0 and projected >= remaining * self.params["overkill_ratio"]:
                continue
            # 사거리 고려
            if unit.distance_to(enemy) <= self._get_attack_range(unit):
                return enemy

        # fallback: 가장 가까운 적
        return prioritized_targets[0] if prioritized_targets else None

    def _estimate_unit_damage(self, unit: Unit, target: Optional[Unit] = None) -> float:
        """
        간단한 유닛 데미지 추정치 (overkill 계산용)
        """
        if unit.type_id in self.damage_table:
            return float(self.damage_table[unit.type_id])
        if target is not None and getattr(target, "is_flying", False):
            base_damage = getattr(unit, "air_damage", 0) or 0
        else:
            base_damage = getattr(unit, "ground_damage", 0) or 0
        if base_damage <= 0:
            base_damage = self.params["default_damage"]
        return float(base_damage)

    def _select_best_target(self, unit: Unit, enemies_in_range: List[Unit]) -> Optional[Unit]:
        """
        사거리 내 적들 중 최적 타겟 선택
        
        Args:
            unit: 아군 유닛
            enemies_in_range: 사거리 내 적 유닛 리스트
            
        Returns:
            최적 타겟 유닛
        """
        if not enemies_in_range:
            return None
        
        # 각 적의 우선순위 점수 계산
        scored = []
        for enemy in enemies_in_range:
            score = self.calculate_target_value(enemy)
            # 거리 보정 (가까울수록 약간의 보너스)
            distance = unit.distance_to(enemy)
            distance_bonus = max(0, self.params["distance_bonus_max"] - distance) * self.params["distance_bonus_weight"]
            score += distance_bonus
            scored.append((score, enemy))
        
        # 점수 높은 순으로 정렬
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored[0][1] if scored else None

    def _get_attack_range(self, unit: Unit) -> float:
        """
        유닛의 공격 사거리 반환
        
        Args:
            unit: 유닛
            
        Returns:
            공격 사거리
        """
        # 기본 사거리 (유닛 타입별)
        base_ranges = {
            UnitTypeId.ZERGLING: 0.1,  # 근접
            UnitTypeId.ROACH: 4.0,
            UnitTypeId.HYDRALISK: 6.0,
            UnitTypeId.MUTALISK: 3.0,
            UnitTypeId.CORRUPTOR: 6.0,
            UnitTypeId.BROODLORD: 10.0,
            UnitTypeId.ULTRALISK: 1.0,  # 근접
        }
        
        # 업그레이드 보너스 (간단한 추정)
        range_bonus = 0.0
        if hasattr(self.bot, 'upgrades'):
            if unit.type_id == UnitTypeId.HYDRALISK:
                # 히드라 사거리 업그레이드
                if hasattr(self.bot.upgrades, 'HYDRALISKRANGE') and self.bot.upgrades.HYDRALISKRANGE:
                    range_bonus = 1.0
        
        base_range = base_ranges.get(unit.type_id, 5.0)
        return base_range + range_bonus

    def _update_target_stats(self, enemies: Units, assignments: Dict[int, Unit]) -> None:
        if not self.params.get("stats_enabled", True):
            return
        current_time = getattr(self.bot, "time", 0.0)
        current_iteration = getattr(self.bot, "iteration", 0)

        # Update combat state
        self._update_combat_state(enemies, assignments, current_time)

        # Update last seen times
        for enemy in enemies:
            self._target_last_seen[enemy.tag] = current_time

        # Track first assignment time
        for target in assignments.values():
            if target.tag not in self._target_first_assigned:
                self._target_first_assigned[target.tag] = current_time

        # Distribution rate
        total_assigned = len(assignments)
        if total_assigned > 0:
            unique_targets = len({t.tag for t in assignments.values()})
            self._distribution_rates.append(unique_targets / float(total_assigned))

        # Detect target removal (missing for some time)
        missing_confirm = self.params.get("missing_confirm_seconds", 5.0)
        for tag, last_seen in list(self._target_last_seen.items()):
            if current_time - last_seen < missing_confirm:
                continue
            first_assigned = self._target_first_assigned.pop(tag, None)
            if first_assigned is not None:
                self._target_lifetimes.append(max(0.0, last_seen - first_assigned))
            self._target_last_seen.pop(tag, None)

        # Periodic logging
        interval = int(self.params.get("stats_interval", 200))
        if interval > 0 and current_iteration % interval == 0:
            avg_dist = (
                sum(self._distribution_rates[-20:]) / max(1, len(self._distribution_rates[-20:]))
            )
            avg_life = (
                sum(self._target_lifetimes[-20:]) / max(1, len(self._target_lifetimes[-20:]))
            )
            print(
                f"[TARGET_STATS] dist_rate={avg_dist:.2f} avg_life={avg_life:.2f}s "
                f"samples={len(self._target_lifetimes)}"
            )
            self._append_stats_csv(current_time, current_iteration, avg_dist, avg_life, len(self._target_lifetimes))

    def _append_stats_csv(
        self, current_time: float, iteration: int, dist_rate: float, avg_life: float, samples: int
    ) -> None:
        path = self._get_stats_csv_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            write_header = not path.exists()
            with path.open("a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["time", "iteration", "game_id", "combat_id", "dist_rate", "avg_life_sec", "samples"])
                writer.writerow([
                    f"{current_time:.2f}",
                    iteration,
                    self._game_id,
                    self._combat_id,
                    f"{dist_rate:.4f}",
                    f"{avg_life:.4f}",
                    samples,
                ])
        except Exception:
            return

    def _update_combat_state(self, enemies: Units, assignments: Dict[int, Unit], current_time: float) -> None:
        in_combat = bool(assignments) and enemies.exists
        if in_combat and not self._combat_active:
            self._combat_active = True
            self._combat_id += 1
            # Reset per-combat stats
            self._distribution_rates = []
            self._target_first_assigned = {}
            self._target_last_seen = {}
            self._target_lifetimes = []
        elif not in_combat and self._combat_active:
            # End combat
            self._combat_active = False

    def _get_stats_csv_path(self) -> Path:
        base_dir = Path(str(self.params.get("stats_csv_dir", "logs")))
        mode = self.params.get("stats_csv_mode", "combat")
        if mode == "game":
            return base_dir / f"target_stats_{self._game_id}.csv"
        return base_dir / f"target_stats_{self._game_id}_combat{self._combat_id}.csv"

    def _resolve_game_id(self) -> str:
        for attr in ("game_id", "match_id", "game_identifier"):
            value = getattr(self.bot, attr, None)
            if value:
                return str(value)
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def get_focus_fire_target(self, units: Units, enemies: Units) -> Optional[Unit]:
        """
        집중 사격 타겟 선택 (모든 아군이 같은 적을 공격)
        
        Args:
            units: 아군 유닛 목록
            enemies: 적 유닛 목록
            
        Returns:
            집중 사격할 타겟 유닛
        """
        if not enemies.exists:
            return None
        
        # 체력이 낮은 적 우선 (한두 방에 잡을 수 있는 유닛)
        enemy_list: List[Unit] = cast(List[Unit], list(enemies))
        low_health_enemies: List[Unit] = [
            e for e in enemy_list
            if hasattr(e, 'health') and hasattr(e, 'health_max')
            and e.health_max > 0
            and (e.health / e.health_max) <= 0.3
        ]
        
        if low_health_enemies:
            # 체력이 가장 낮은 적 선택
            return min(low_health_enemies, key=lambda e: e.health)
        
        # 체력이 낮은 적이 없으면 위협도가 높은 적 선택
        return self.find_best_target(units, enemies)
