# -*- coding: utf-8 -*-
"""
Base Defense System - 기지 방어 시스템

필수 기지 방어 로직:
1. 기지 위협 평가
2. 군대 유닛 자동 귀환
3. 일꾼 방어 참여
4. 퀸 우선 방어
5. 스파인 크롤러 타겟팅
6. 우선순위 타겟 집중 공격
"""

from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2
else:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
    except ImportError:
        Units = object
        Unit = object
        Point2 = tuple

from utils.logger import get_logger


class BaseDefenseSystem:
    """
    기지 방어 시스템

    책임:
    - 기지 위협 감지 및 평가
    - 방어 유닛 자동 배치
    - 일꾼 방어 참여 관리
    - 우선순위 타겟팅
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("BaseDefense")

        # Defense state
        self._base_defense_active = False
        self._defense_rally_point = None
        self._last_defense_check = 0
        self._defense_check_interval = 3  # 3 frames between checks

        # Thresholds
        self._worker_defense_threshold = 1  # 적 1기라도 일꾼 방어
        self._critical_defense_threshold = 8  # 적 8기 이상 심각

        # High threat unit types
        self.high_threat_units = {
            "SIEGETANK", "SIEGETANKSIEGED", "THOR", "BATTLECRUISER",
            "COLOSSUS", "DISRUPTOR", "IMMORTAL", "ARCHON",
            "ULTRALISK", "BROODLORD", "RAVAGER", "LURKER"
        }

        # High priority target types (for focus fire)
        self.high_priority_targets = {
            "SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "DISRUPTOR",
            "HIGHTEMPLAR", "WIDOWMINE", "LIBERATOR", "LIBERATORAG",
            "IMMORTAL", "THOR", "MEDIVAC"
        }

    @property
    def is_active(self) -> bool:
        """기지 방어가 활성화되었는지 확인"""
        return self._base_defense_active

    @property
    def defense_position(self) -> Optional['Point2']:
        """현재 방어 위치 반환"""
        return self._defense_rally_point

    def evaluate_base_threat(self, enemy_units) -> Optional['Point2']:
        """
        기지 위협 평가

        Returns:
            위협 위치 (Point2) 또는 None
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return None

        game_time = getattr(self.bot, "time", 0)

        # 위협 수준 추적
        highest_threat = None
        highest_threat_count = 0
        highest_threat_score = 0
        has_high_threat = False

        for th in self.bot.townhalls:
            # 중후반에는 더 넓은 감지 거리
            detection_range = 25 if game_time < 300 else 40

            # 근처 적 감지
            if hasattr(enemy_units, "closer_than"):
                nearby_enemies = enemy_units.closer_than(detection_range, th.position)
            else:
                nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < detection_range]

            if not nearby_enemies:
                continue

            # 위협 점수 계산
            threat_score = 0
            local_high_threat = False
            for enemy in nearby_enemies:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                if enemy_type in self.high_threat_units:
                    threat_score += 5
                    local_high_threat = True
                else:
                    threat_score += 1

            # 가장 높은 위협 선택
            if threat_score > highest_threat_score:
                highest_threat_score = threat_score
                highest_threat_count = len(nearby_enemies)
                highest_threat = self._get_enemy_center(nearby_enemies)
                has_high_threat = local_high_threat

        # 위협이 있으면 디버그 출력
        if highest_threat and self.bot.iteration % 50 == 0:
            if has_high_threat:
                threat_level = "CRITICAL"
            elif highest_threat_count >= 6:
                threat_level = "heavy"
            elif highest_threat_count >= 3:
                threat_level = "medium"
            else:
                threat_level = "light"
            self.logger.info(f"[{int(game_time)}s] Base threat: {highest_threat_count} enemies ({threat_level}, score={highest_threat_score})")

        return highest_threat

    def get_units_near_base(self, units, range_distance: float = 30) -> List:
        """기지 근처 유닛 가져오기 (최적화)"""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return []

        # Optimization: Use global spatial query first
        nearby_tags = set()
        for th in self.bot.townhalls:
            nearby = self.bot.units.closer_than(range_distance, th.position)
            for u in nearby:
                nearby_tags.add(u.tag)

        # Filter the input list against the nearby set
        return [u for u in units if u.tag in nearby_tags]

    async def execute_defense_task(self, units, threat_position):
        """
        기지 방어 실행

        개선사항:
        - 퀸 우선 방어
        - 스파인 크롤러 자동 타겟팅
        - 고위협 유닛 집중 공격
        """
        if not threat_position:
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            # Fallback to simple attack
            for unit in units:
                try:
                    self.bot.do(unit.attack(threat_position))
                except Exception:
                    continue
            return

        # 우선순위 타겟 찾기
        priority_target = None
        enemy_units = getattr(self.bot, "enemy_units", [])
        if enemy_units:
            for enemy in enemy_units:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                if enemy_type in self.high_priority_targets and enemy.distance_to(threat_position) < 15:
                    priority_target = enemy
                    break

        # 퀸을 먼저 보내기
        queens = [u for u in units if hasattr(u, 'type_id') and u.type_id == UnitTypeId.QUEEN]
        other_units = [u for u in units if u not in queens]

        # 퀸 방어 우선
        for queen in queens:
            try:
                if queen.distance_to(threat_position) < 8:
                    target = priority_target if priority_target else threat_position
                    self.bot.do(queen.attack(target))
                else:
                    self.bot.do(queen.move(threat_position))
            except (AttributeError, TypeError) as e:
                self.logger.debug(f"Queen defense command failed: {e}")
            except Exception as e:
                self.logger.warning(f"Unexpected error in queen defense: {e}")

        # 스파인 크롤러 타겟팅
        if hasattr(self.bot, "structures"):
            spines = self.bot.structures(UnitTypeId.SPINECRAWLER).ready
            spines_in_range = spines.closer_than(20, threat_position) if hasattr(spines, "closer_than") else \
                             [s for s in spines if s.distance_to(threat_position) < 20]

            for spine in spines_in_range:
                try:
                    if hasattr(enemy_units, "closer_than"):
                        enemies_near = enemy_units.closer_than(12, spine)
                    else:
                        enemies_near = [e for e in enemy_units if e.distance_to(spine) < 12]

                    if enemies_near:
                        # 우선순위 타겟 먼저
                        priority_enemies = [
                            e for e in enemies_near
                            if getattr(e.type_id, "name", "").upper() in self.high_priority_targets
                        ]
                        if priority_enemies:
                            target = spine.position.closest(priority_enemies)
                        else:
                            target = spine.position.closest(enemies_near)
                        self.bot.do(spine.attack(target))
                except (AttributeError, TypeError) as e:
                    self.logger.debug(f"Spine crawler targeting failed: {e}")
                except Exception as e:
                    self.logger.warning(f"Unexpected error in spine targeting: {e}")

        # 다른 유닛들 방어
        for unit in other_units:
            try:
                if priority_target and unit.distance_to(priority_target) < 10:
                    self.bot.do(unit.attack(priority_target))
                else:
                    self.bot.do(unit.attack(threat_position))
            except Exception:
                continue

    async def check_mandatory_base_defense(self, iteration: int) -> Optional['Point2']:
        """
        필수 기지 방어 체크

        Returns:
            위협 위치 또는 None
        """
        # 체크 간격
        if iteration - self._last_defense_check < self._defense_check_interval:
            return self._defense_rally_point if self._base_defense_active else None
        self._last_defense_check = iteration

        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "enemy_units"):
            self._base_defense_active = False
            return None

        if not self.bot.townhalls.exists:
            self._base_defense_active = False
            return None

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            self._base_defense_active = False
            self._defense_rally_point = None
            return None

        game_time = getattr(self.bot, "time", 0)

        # 기지별 위협 평가
        max_threat_score = 0
        threat_position = None
        threat_enemies = []

        for th in self.bot.townhalls:
            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < 30]

            if not nearby_enemies:
                continue

            # 위협 점수 계산
            threat_score = 0
            for enemy in nearby_enemies:
                if hasattr(enemy, "can_attack") and enemy.can_attack:
                    threat_score += 2
                else:
                    threat_score += 1
                if getattr(enemy, "is_flying", False):
                    threat_score += 1

            if threat_score > max_threat_score:
                max_threat_score = threat_score
                threat_enemies = nearby_enemies
                threat_position = self._get_enemy_center(nearby_enemies)

        # 위협이 없으면 방어 모드 해제
        if max_threat_score == 0:
            if self._base_defense_active and iteration % 100 == 0:
                print(f"[BASE DEFENSE] [{int(game_time)}s] Threat cleared - returning to normal")
            self._base_defense_active = False
            self._defense_rally_point = None
            return None

        # 위협 감지 - 방어 모드 활성화
        self._base_defense_active = True
        self._defense_rally_point = threat_position

        enemy_count = len(threat_enemies)

        # 로그 출력
        if iteration % 110 == 0:
            print(f"[BASE DEFENSE] [{int(game_time)}s] ★ MANDATORY DEFENSE ★ "
                  f"Enemies: {enemy_count}, Threat score: {max_threat_score}")

        # 모든 군대 즉시 방어
        await self.execute_mandatory_defense(threat_position, threat_enemies, iteration)

        # 위험 상황: 일꾼도 방어 참여
        if enemy_count >= self._worker_defense_threshold:
            await self.worker_defense(threat_position, threat_enemies, iteration)

        return threat_position

    async def execute_mandatory_defense(self, threat_position, threat_enemies, iteration: int):
        """모든 군대 귀환 및 방어"""
        if not hasattr(self.bot, "units"):
            return

        game_time = getattr(self.bot, "time", 0)

        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        # 패배 직감 시스템 연동
        defeat_level = 0
        last_stand_mode = False
        if hasattr(self.bot, "defeat_detection") and self.bot.defeat_detection:
            defeat_status = self.bot.defeat_detection._get_current_status()
            defeat_level = defeat_status.get("defeat_level", 0)
            last_stand_mode = defeat_status.get("last_stand_required", False)

        # 모든 군대 유닛 수집
        army_types = {
            UnitTypeId.ZERGLING, UnitTypeId.BANELING, UnitTypeId.ROACH,
            UnitTypeId.RAVAGER, UnitTypeId.HYDRALISK, UnitTypeId.LURKER,
            UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR, UnitTypeId.ULTRALISK,
            UnitTypeId.BROODLORD, UnitTypeId.INFESTOR, UnitTypeId.VIPER
        }

        army_units = [u for u in self.bot.units if u.type_id in army_types]

        if not army_units:
            return

        # 타겟 우선순위 분류
        high_priority_targets = []
        medium_priority_targets = []
        low_priority_targets = []

        for enemy in threat_enemies:
            enemy_type = getattr(enemy.type_id, "name", "").upper()

            if enemy_type in ["SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "DISRUPTOR",
                             "THOR", "BATTLECRUISER", "TEMPEST", "CARRIER"]:
                high_priority_targets.append(enemy)
            elif enemy_type in ["MEDIVAC", "HIGHTEMPLAR", "IMMORTAL", "RAVAGER",
                               "INFESTOR", "VIPER", "ORACLE", "WARPPRISM"]:
                medium_priority_targets.append(enemy)
            else:
                low_priority_targets.append(enemy)

        priority_targets = high_priority_targets or medium_priority_targets or low_priority_targets

        # 마지막 방어 모드: 더 공격적인 전략
        if last_stand_mode:
            if high_priority_targets:
                main_target = min(high_priority_targets,
                                key=lambda e: e.distance_to(threat_position))

                for unit in army_units:
                    try:
                        if unit.type_id == UnitTypeId.BANELING:
                            densest_enemy = self.find_densest_enemy_position(threat_enemies)
                            if densest_enemy:
                                self.bot.do(unit.attack(densest_enemy.position))
                            else:
                                self.bot.do(unit.attack(main_target))
                        else:
                            self.bot.do(unit.attack(main_target))
                    except Exception:
                        continue

                if iteration % 220 == 0:
                    print(f"[LAST STAND] [{int(game_time)}s] {len(army_units)} units - FOCUS FIRE on {getattr(main_target.type_id, 'name', 'enemy')}")
                return

        # 일반 방어 모드
        for unit in army_units:
            try:
                if unit.type_id == UnitTypeId.BANELING:
                    densest_enemy = self.find_densest_enemy_position(threat_enemies)
                    if densest_enemy:
                        self.bot.do(unit.attack(densest_enemy.position))
                    elif threat_enemies:
                        self.bot.do(unit.attack(threat_enemies[0]))
                    else:
                        self.bot.do(unit.attack(threat_position))
                    continue

                if unit.type_id == UnitTypeId.MUTALISK:
                    medivacs = [e for e in threat_enemies
                               if getattr(e.type_id, "name", "").upper() == "MEDIVAC"]
                    if medivacs:
                        self.bot.do(unit.attack(medivacs[0]))
                        continue

                if unit.distance_to(threat_position) < 15:
                    if priority_targets:
                        closest_priority = min(priority_targets,
                                             key=lambda e: e.distance_to(unit))
                        self.bot.do(unit.attack(closest_priority))
                    elif threat_enemies:
                        closest = min(threat_enemies,
                                    key=lambda e: e.distance_to(unit))
                        self.bot.do(unit.attack(closest))
                    else:
                        self.bot.do(unit.attack(threat_position))
                else:
                    self.bot.do(unit.attack(threat_position))
            except Exception:
                continue

        if iteration % 220 == 0:
            defeat_msg = f" [위기도: {defeat_level}]" if defeat_level >= 2 else ""
            print(f"[BASE DEFENSE] [{int(game_time)}s] {len(army_units)} units defending{defeat_msg}")

    async def worker_defense(self, threat_position, threat_enemies, iteration: int):
        """일꾼 방어 참여"""
        if not hasattr(self.bot, "workers"):
            return

        game_time = getattr(self.bot, "time", 0)
        workers = self.bot.workers

        if not workers:
            return

        # 패배 직감 시스템 연동
        defeat_level = 0
        last_stand_mode = False
        if hasattr(self.bot, "defeat_detection") and self.bot.defeat_detection:
            defeat_status = self.bot.defeat_detection._get_current_status()
            defeat_level = defeat_status.get("defeat_level", 0)
            last_stand_mode = defeat_status.get("last_stand_required", False)

        # 위협 근처 일꾼만 방어
        nearby_workers = [w for w in workers if w.distance_to(threat_position) < 15]

        if not nearby_workers:
            return

        # 위기 수준에 따라 일꾼 수 조절
        if last_stand_mode or defeat_level >= 3:
            defense_workers = nearby_workers  # 모든 일꾼
            if iteration % 220 == 0:
                print(f"[WORKER DEFENSE] ★ 패배 직전! 모든 일꾼({len(defense_workers)}) 방어 참여! ★")
        elif defeat_level >= 2:
            defense_workers = nearby_workers[:12]
            if iteration % 220 == 0:
                print(f"[WORKER DEFENSE] 위기 상황 - {len(defense_workers)} 일꾼 방어")
        else:
            defense_workers = nearby_workers[:6]

        # 가장 가까운 타운홀 찾기
        closest_townhall = None
        if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
            closest_townhall = self.bot.townhalls.closest_to(threat_position)

        for worker in defense_workers:
            try:
                # 일꾼이 기지에서 12거리 이상 벗어나면 즉시 복귀
                if closest_townhall and worker.distance_to(closest_townhall) > 12:
                    self.bot.do(worker.gather(self.bot.mineral_field.closest_to(closest_townhall)))
                    continue

                if threat_enemies:
                    base_close_threats = [e for e in threat_enemies
                                         if closest_townhall and e.distance_to(closest_townhall) < 12]
                    if base_close_threats:
                        closest = min(base_close_threats, key=lambda e: e.distance_to(worker))
                        self.bot.do(worker.attack(closest))
                    else:
                        self.bot.do(worker.gather(self.bot.mineral_field.closest_to(closest_townhall)))
                else:
                    if closest_townhall and threat_position.distance_to(closest_townhall) < 12:
                        self.bot.do(worker.attack(threat_position))
                    else:
                        self.bot.do(worker.gather(self.bot.mineral_field.closest_to(closest_townhall)))
            except Exception:
                continue

        if iteration % 220 == 0:
            print(f"[BASE DEFENSE] [{int(game_time)}s] ★ {len(defense_workers)} WORKERS DEFENDING ★")

    def find_densest_enemy_position(self, enemies):
        """가장 밀집된 적 위치 찾기 (맹독충용)"""
        if not enemies:
            return None

        max_density = 0
        densest_enemy = None

        for enemy in enemies:
            nearby_count = sum(1 for e in enemies if e.distance_to(enemy) < 5)
            if nearby_count > max_density:
                max_density = nearby_count
                densest_enemy = enemy

        return densest_enemy

    def _get_enemy_center(self, enemy_units):
        """적 유닛들의 중심 위치 계산"""
        if not enemy_units:
            return None

        x_sum = sum(e.position.x for e in enemy_units)
        y_sum = sum(e.position.y for e in enemy_units)
        count = len(enemy_units)

        try:
            from sc2.position import Point2
            return Point2((x_sum / count, y_sum / count))
        except ImportError:
            return enemy_units[0].position
