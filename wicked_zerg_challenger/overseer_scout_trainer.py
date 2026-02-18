# -*- coding: utf-8 -*-
"""
Overseer Scout Trainer - 감시군주 정찰 학습 시스템

감시군주의 특수 능력을 활용한 고급 정찰:
1. 투명 유닛 감지 (Detector)
2. 변신체 생성으로 안전한 정찰
3. 오염으로 적 건물 무력화
4. 대군주보다 빠른 이동 속도
"""

from typing import Dict, Set, List, Optional
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from utils.logger import get_logger


class OverseerScout:
    """감시군주 정찰 정보"""

    def __init__(self, tag: int):
        self.tag = tag
        self.assigned_zone: Optional[Point2] = None
        self.last_scout_time = 0.0
        self.zones_scouted = 0
        self.changelings_spawned = 0
        self.contaminations_used = 0


class OverseerScoutTrainer:
    """
    감시군주 정찰 학습 시스템

    감시군주를 활용한 안전하고 효과적인 정찰
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("OverseerScout")

        # 감시군주 추적
        self.overseers: Dict[int, OverseerScout] = {}  # tag -> OverseerScout

        # 정찰 설정
        self.MIN_OVERSEERS_FOR_SCOUT = 2  # 정찰에 필요한 최소 감시군주
        self.SCOUT_INTERVAL = 30.0  # 정찰 간격 (초)

        # 정찰 존 (맵을 여러 구역으로 나눔)
        self.scout_zones: List[Point2] = []
        self.scouted_zones: Set[int] = set()  # 정찰 완료된 존 인덱스

        # 변신체 설정
        self.CHANGELING_COOLDOWN = 60.0  # 변신체 쿨다운
        self.last_changeling_time = 0.0

        # 오염 설정
        self.CONTAMINATE_TARGETS = {
            UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
            UnitTypeId.NEXUS, UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
            UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT,
            UnitTypeId.GATEWAY, UnitTypeId.ROBOTICSFACILITY, UnitTypeId.STARGATE
        }

        # 통계
        self.total_zones_scouted = 0
        self.total_changelings = 0
        self.total_contaminations = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 감시군주 확인
            overseers = self.bot.units(UnitTypeId.OVERSEER)
            if overseers.amount < self.MIN_OVERSEERS_FOR_SCOUT:
                return

            # 정찰 존 초기화 (최초 1회)
            if not self.scout_zones and iteration == 100:
                self._initialize_scout_zones()

            # 1. 감시군주 추적 업데이트
            self._update_overseer_tracking(overseers, game_time)

            # 2. 정찰 존 할당 (10초마다)
            if iteration % 220 == 0:
                await self._assign_scout_zones(overseers, game_time)

            # 3. 변신체 생성 (1초마다 확인)
            if iteration % 22 == 0:
                await self._spawn_changelings(overseers, game_time)

            # 4. 오염 사용 (2초마다)
            if iteration % 44 == 0:
                await self._use_contaminate(overseers, game_time)

            # 5. 통계 출력 (60초마다)
            if iteration % 1320 == 0 and self.total_zones_scouted > 0:
                self._print_statistics(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[OVERSEER_SCOUT] Error: {e}")

    def _initialize_scout_zones(self):
        """정찰 존 초기화"""
        try:
            # 맵 크기 확인
            if not hasattr(self.bot, "game_info"):
                return

            playable_area = self.bot.game_info.playable_area
            map_width = playable_area.width
            map_height = playable_area.height

            # 맵을 3x3 = 9개 구역으로 분할
            zone_width = map_width / 3
            zone_height = map_height / 3

            for x in range(3):
                for y in range(3):
                    center_x = playable_area.x + (x + 0.5) * zone_width
                    center_y = playable_area.y + (y + 0.5) * zone_height
                    self.scout_zones.append(Point2((center_x, center_y)))

            self.logger.info(f"[INIT] {len(self.scout_zones)} scout zones initialized")

        except Exception as e:
            self.logger.error(f"[INIT] Error initializing scout zones: {e}")

    def _update_overseer_tracking(self, overseers, game_time: float):
        """감시군주 추적 업데이트"""
        current_tags = {o.tag for o in overseers}

        # 새로운 감시군주 추가
        for overseer in overseers:
            if overseer.tag not in self.overseers:
                # ★ Unit Authority Check ★
                if hasattr(self.bot, "unit_authority") and self.bot.unit_authority:
                    from unit_authority_manager import AuthorityLevel
                    # IDLE 권한 요청 (정찰은 전투보다 낮음)
                    granted = self.bot.unit_authority.request_authority(
                        {overseer.tag}, AuthorityLevel.SCOUTING, "OverseerScout", self.bot.state.game_loop
                    )
                    if overseer.tag not in granted:
                        continue
                
                self.overseers[overseer.tag] = OverseerScout(overseer.tag)
                self.logger.info(f"[NEW] Overseer {overseer.tag} registered for scouting")

        # 죽은 감시군주 제거
        dead_tags = set(self.overseers.keys()) - current_tags
        for tag in dead_tags:
            del self.overseers[tag]

    async def _assign_scout_zones(self, overseers, game_time: float):
        """
        정찰 존 할당

        감시군주를 미정찰 구역에 배치
        """
        if not self.scout_zones:
            return

        # 미정찰 존 찾기
        unscouted_zones = [
            (i, zone) for i, zone in enumerate(self.scout_zones)
            if i not in self.scouted_zones
        ]

        if not unscouted_zones:
            # 모든 존 정찰 완료 → 리셋
            self.scouted_zones.clear()
            return

        # 할당되지 않은 감시군주 찾기
        for overseer in overseers:
            scout_info = self.overseers.get(overseer.tag)
            if not scout_info:
                continue

            # 쿨다운 확인
            time_since_last = game_time - scout_info.last_scout_time
            if time_since_last < self.SCOUT_INTERVAL:
                continue

            # 할당 없거나 이미 도착한 경우
            if scout_info.assigned_zone is None or overseer.position.distance_to(scout_info.assigned_zone) < 5:
                if unscouted_zones:
                    # 가장 가까운 미정찰 존 할당
                    zone_index, zone_pos = min(
                        unscouted_zones,
                        key=lambda x: overseer.position.distance_to(x[1])
                    )

                    scout_info.assigned_zone = zone_pos
                    scout_info.last_scout_time = game_time
                    self.scouted_zones.add(zone_index)
                    self.total_zones_scouted += 1
                    scout_info.zones_scouted += 1

                    # 정찰 명령
                    self.bot.do(overseer.move(zone_pos))

                    self.logger.info(
                        f"[SCOUT] Overseer {overseer.tag} assigned to zone {zone_index} at {zone_pos}"
                    )

                    # 리스트에서 제거
                    unscouted_zones.remove((zone_index, zone_pos))

    async def _spawn_changelings(self, overseers, game_time: float):
        """
        변신체 생성

        적 기지 근처에서 안전한 정찰을 위해 변신체 생성
        """
        # 쿨다운 확인
        if game_time - self.last_changeling_time < self.CHANGELING_COOLDOWN:
            return

        # 적 건물 근처 감시군주 찾기
        if not self.bot.enemy_structures:
            return

        for overseer in overseers:
            # 적 건물과의 거리 확인
            closest_enemy = self.bot.enemy_structures.closest_to(overseer.position)
            distance = overseer.position.distance_to(closest_enemy.position)

            # 15~25 거리에 있으면 변신체 생성
            if 15 < distance < 25:
                # 변신체 생성 가능 여부 확인
                abilities = await self.bot.get_available_abilities(overseer)
                if AbilityId.SPAWNCHANGELING_SPAWNCHANGELING in abilities:
                    self.bot.do(overseer(AbilityId.SPAWNCHANGELING_SPAWNCHANGELING))

                    scout_info = self.overseers.get(overseer.tag)
                    if scout_info:
                        scout_info.changelings_spawned += 1

                    self.last_changeling_time = game_time
                    self.total_changelings += 1

                    self.logger.info(
                        f"[CHANGELING] Spawned at {overseer.position} "
                        f"(near {closest_enemy.type_id.name})"
                    )
                    break

    async def _use_contaminate(self, overseers, game_time: float):
        """
        오염 사용

        적 생산 건물에 오염을 사용하여 생산 중단
        """
        if not self.bot.enemy_structures:
            return

        # 오염 가능한 적 건물 찾기
        contaminate_targets = self.bot.enemy_structures.filter(
            lambda s: s.type_id in self.CONTAMINATE_TARGETS
        )

        if not contaminate_targets:
            return

        for overseer in overseers:
            # 가장 가까운 타겟 찾기
            closest_target = contaminate_targets.closest_to(overseer.position)
            distance = overseer.position.distance_to(closest_target.position)

            # 10 거리 이내면 오염 사용
            if distance < 10:
                abilities = await self.bot.get_available_abilities(overseer)
                if AbilityId.CONTAMINATE_CONTAMINATE in abilities:
                    self.bot.do(overseer(AbilityId.CONTAMINATE_CONTAMINATE, closest_target))

                    scout_info = self.overseers.get(overseer.tag)
                    if scout_info:
                        scout_info.contaminations_used += 1

                    self.total_contaminations += 1

                    self.logger.info(
                        f"[CONTAMINATE] Used on {closest_target.type_id.name} "
                        f"at {closest_target.position}"
                    )
                    break

    def get_scout_statistics(self) -> Dict:
        """정찰 통계 반환"""
        active_overseers = len(self.overseers)

        return {
            "active_overseers": active_overseers,
            "total_zones_scouted": self.total_zones_scouted,
            "total_changelings": self.total_changelings,
            "total_contaminations": self.total_contaminations,
            "scout_zones": len(self.scout_zones),
            "scouted_zones": len(self.scouted_zones)
        }

    def _print_statistics(self, game_time: float):
        """통계 출력"""
        stats = self.get_scout_statistics()

        self.logger.info(
            f"[SCOUT_STATS] [{int(game_time)}s] "
            f"Overseers: {stats['active_overseers']}, "
            f"Zones: {stats['scouted_zones']}/{stats['scout_zones']}, "
            f"Changelings: {stats['total_changelings']}, "
            f"Contaminations: {stats['total_contaminations']}"
        )
