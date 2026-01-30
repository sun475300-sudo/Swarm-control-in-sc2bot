# -*- coding: utf-8 -*-
"""
Attack Controller - 공격 제어 시스템

기능:
1. 선제 공격 로직
2. 공격 타겟 우선순위 결정
3. 타이밍 어택 관리
4. 맵 수색
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


class AttackController:
    """
    공격 제어 시스템

    책임:
    - 선제 공격 실행
    - 공격 타겟 우선순위 결정
    - 타이밍 어택 관리
    - 맵 수색
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("AttackController")

        # Roach rush timing
        self._roach_rush_active = False
        self._roach_rush_timing = 360  # 6:00
        self._roach_rush_min_count = 12
        self._roach_rush_sent = False

        # Map search state
        self._search_index = 0
        self._last_search_time = 0

    async def offensive_attack(self, army_units, iteration: int):
        """
        선제 공격 로직

        특징:
        - 즉시 공격 (집결 대기 없음)
        - 여러 타겟 동시 공격
        - 타겟 우선순위: 생산 건물 > 기지 > 기타

        Args:
            army_units: 아군 유닛들
            iteration: 현재 반복 횟수
        """
        try:
            game_time = getattr(self.bot, "time", 0)

            # 최소 병력 확인
            army_supply = sum(getattr(u, "supply_cost", 1) for u in army_units)

            # 초반에는 더 낮은 임계값
            min_attack_threshold = 3 if game_time < 240 else 6

            if army_supply < min_attack_threshold:
                return

            # 공격 타겟 찾기
            attack_targets = self.find_multiple_attack_targets()

            if not attack_targets:
                # 적 시작 위치로 공격 (fallback)
                if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                    attack_targets = [self.bot.enemy_start_locations[0]]

            if not attack_targets:
                return

            # 10프레임마다 공격 명령 갱신
            if iteration % 10 != 0:
                return

            # 디버그 로그
            if iteration % 100 == 0:
                self.logger.info(f"[{int(game_time)}s] OFFENSIVE ATTACK: {len(army_units)} units, {army_supply} supply, {len(attack_targets)} targets")

            # 병력 분할 공격 (여러 타겟)
            if len(attack_targets) > 1 and army_supply >= 20:
                num_groups = min(len(attack_targets), 3)
                group_size = len(army_units) // num_groups

                for group_idx in range(num_groups):
                    start_idx = group_idx * group_size
                    end_idx = start_idx + group_size if group_idx < num_groups - 1 else len(army_units)
                    group_units = army_units[start_idx:end_idx]
                    target = attack_targets[group_idx]

                    for unit in group_units:
                        try:
                            self.bot.do(unit.attack(target))
                        except Exception:
                            continue

                if iteration % 200 == 0:
                    self.logger.info(f"[{int(game_time)}s] ★ MULTI-ATTACK: {num_groups} groups attacking {len(attack_targets)} targets")
            else:
                # 단일 타겟 공격
                attack_target = attack_targets[0]
                attack_count = 0
                for unit in list(army_units):
                    try:
                        self.bot.do(unit.attack(attack_target))
                        attack_count += 1
                    except Exception:
                        continue

                if iteration % 200 == 0:
                    target_name = getattr(attack_target, "name", str(attack_target)[:30])
                    self.logger.info(f"[{int(game_time)}s] Attacking {target_name} with {army_supply} supply army ({attack_count} units ordered)")

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.warning(f"Offensive attack error: {e}")

    def find_multiple_attack_targets(self) -> List:
        """
        여러 공격 타겟 찾기

        우선순위:
        1. 적 생산 건물 (병력 차단)
        2. 적 기지 (경제 차단)
        3. 기타 건물

        Returns:
            공격 타겟 리스트 (최대 3개)
        """
        targets = []
        enemy_structures = getattr(self.bot, "enemy_structures", None)

        if not enemy_structures or not enemy_structures.exists:
            single_target = self.find_priority_attack_target()
            return [single_target] if single_target else []

        # 생산 건물 타입
        production_types = {
            "BARRACKS", "BARRACKSFLYING", "FACTORY", "FACTORYFLYING",
            "STARPORT", "STARPORTFLYING",
            "GATEWAY", "WARPGATE", "ROBOTICSFACILITY", "STARGATE",
            "SPAWNINGPOOL", "ROACHWARREN", "HYDRALISKDEN"
        }

        # 기지 타입
        townhall_types = {
            "NEXUS", "COMMANDCENTER", "COMMANDCENTERFLYING",
            "ORBITALCOMMAND", "ORBITALCOMMANDFLYING", "PLANETARYFORTRESS",
            "HATCHERY", "LAIR", "HIVE"
        }

        # 타겟 분류
        production_buildings = []
        enemy_bases = []

        for struct in enemy_structures:
            struct_type = getattr(struct.type_id, "name", "").upper()
            if struct_type in production_types:
                production_buildings.append(struct)
            elif struct_type in townhall_types:
                enemy_bases.append(struct)

        if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
            our_base = self.bot.townhalls.first.position

            # 우선순위 1: 생산 건물
            if production_buildings:
                sorted_production = sorted(production_buildings, key=lambda b: b.distance_to(our_base))
                targets.extend([p.position for p in sorted_production[:2]])

            # 우선순위 2: 적 기지
            if enemy_bases:
                sorted_bases = sorted(enemy_bases, key=lambda b: b.distance_to(our_base))
                targets.extend([base.position for base in sorted_bases[:3]])

            return targets if targets else [self.find_priority_attack_target()]

        single_target = self.find_priority_attack_target()
        return [single_target] if single_target else []

    def find_priority_attack_target(self):
        """
        우선 공격 타겟 찾기

        우선순위:
        1. 적 기지 (타운홀)
        2. 적 생산 건물
        3. 적 테크 건물
        4. 기타 적 건물
        5. 맵 수색 위치
        6. 적 시작 위치 (fallback)

        Returns:
            공격 타겟 위치 또는 유닛
        """
        game_time = getattr(self.bot, "time", 0)
        enemy_structures = getattr(self.bot, "enemy_structures", None)

        # 적 건물이 있으면 우선 공격
        if enemy_structures and enemy_structures.exists:
            # 가장 가까운 적 건물
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                our_base = self.bot.townhalls.first.position
                closest_structure = min(enemy_structures, key=lambda s: s.distance_to(our_base))
                return closest_structure.position

        # 적 건물이 없으면 맵 수색
        search_target = self.get_map_search_target()
        if search_target:
            return search_target

        # Fallback: 적 시작 위치
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        return None

    def get_map_search_target(self):
        """
        맵 수색 타겟

        확장 위치들을 순회하며 적 기지 찾기

        Returns:
            수색 위치
        """
        game_time = getattr(self.bot, "time", 0)

        # 수색 위치 목록 생성
        search_locations = []

        # 1. 적 시작 위치
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            search_locations.append(self.bot.enemy_start_locations[0])

        # 2. 확장 위치들
        exp_list = []
        if hasattr(self.bot, "expansion_locations_list"):
            exp_list = list(self.bot.expansion_locations_list)
        elif hasattr(self.bot, "expansion_locations"):
            exp_list = list(self.bot.expansion_locations.keys())

        if exp_list:
            # 적 시작 위치에서 가까운 순으로 정렬
            if search_locations:
                enemy_start = search_locations[0]
                exp_list.sort(key=lambda pos: pos.distance_to(enemy_start))

            # 이미 점령한 위치 제외
            our_bases = set()
            if hasattr(self.bot, "townhalls"):
                for th in self.bot.townhalls:
                    our_bases.add(th.position)

            for exp_pos in exp_list:
                if any(exp_pos.distance_to(base) < 5 for base in our_bases):
                    continue
                search_locations.append(exp_pos)

        # 3. 맵 코너
        if hasattr(self.bot, "game_info"):
            w = self.bot.game_info.map_size.width
            h = self.bot.game_info.map_size.height
            corners = [
                (10, 10), (w-10, 10), (10, h-10), (w-10, h-10)
            ]

            try:
                from sc2.position import Point2
                for x, y in corners:
                    search_locations.append(Point2((x, y)))
            except ImportError:
                pass

        # 4. 맵 중앙
        if hasattr(self.bot, "game_info"):
            search_locations.append(self.bot.game_info.map_center)

        if not search_locations:
            return None

        # 30초마다 다음 수색 위치로 이동
        if game_time - self._last_search_time > 30:
            self._search_index = (self._search_index + 1) % len(search_locations)
            self._last_search_time = game_time

            if self.bot.iteration % 100 == 0:
                print(f"[SEARCH] [{int(game_time)}s] Searching map location {self._search_index + 1}/{len(search_locations)}")

        return search_locations[self._search_index]

    async def check_roach_rush_timing(self, iteration: int):
        """
        바퀴 러쉬 타이밍 체크

        조건:
        - 게임 시간 6분
        - 바퀴 12마리 이상
        """
        game_time = getattr(self.bot, "time", 0)

        if game_time < self._roach_rush_timing:
            return

        if self._roach_rush_sent:
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        # 바퀴 수 확인
        roaches = [u for u in self.bot.units if hasattr(u, 'type_id') and u.type_id == UnitTypeId.ROACH]

        if len(roaches) >= self._roach_rush_min_count:
            self._roach_rush_active = True
            self._roach_rush_sent = True

            # 적 본진으로 공격
            if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
                target = self.bot.enemy_start_locations[0]

                for roach in roaches:
                    try:
                        self.bot.do(roach.attack(target))
                    except Exception:
                        continue

                if iteration % 22 == 0:
                    print(f"[ROACH RUSH] [{int(game_time)}s] ★★★ {len(roaches)} ROACHES ATTACKING! ★★★")
