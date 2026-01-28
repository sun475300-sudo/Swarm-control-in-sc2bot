# -*- coding: utf-8 -*-
"""
Map Memory System - 맵 기억 시스템

유닛 시야에만 의존하지 않고 맵 정보를 활용:
1. 한 번 발견된 적 건물 위치 영구 기억
2. 확장 위치 기반 적 기지 예측
3. 파괴된 건물 추적
4. 맵 전체 탐색 진행도
"""

from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass, field
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger
import json
import os


@dataclass
class DiscoveredStructure:
    """발견된 건물 정보"""
    unit_type: UnitTypeId
    position: Point2
    first_seen_time: float
    last_seen_time: float
    is_destroyed: bool = False
    destroyed_time: Optional[float] = None
    race: Optional[str] = None


@dataclass
class PredictedBase:
    """예측된 적 기지"""
    position: Point2
    confidence: float  # 0.0 ~ 1.0
    reason: str  # "expansion_location", "scouted", "mineral_patch"
    predicted_time: float


class MapMemorySystem:
    """
    맵 기억 시스템

    유닛 시야에 의존하지 않고 게임 전체 맵 정보를 활용하여
    적 건물과 기지 위치를 추적합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("MapMemory")

        # 발견된 적 건물 (영구 기록)
        self.discovered_structures: Dict[int, DiscoveredStructure] = {}

        # 예측된 적 기지
        self.predicted_bases: List[PredictedBase] = []

        # 맵 탐색 진행도
        self.explored_positions: Set[Tuple[int, int]] = set()
        self.exploration_progress = 0.0  # 0% ~ 100%

        # 확장 위치별 상태
        self.expansion_status: Dict[Point2, str] = {}  # "unknown", "enemy", "ally", "neutral"

        # 통계
        self.total_structures_discovered = 0
        self.total_structures_destroyed = 0

        # 설정
        self.MEMORY_FILE = "map_memory.json"
        self.GRID_SIZE = 10  # 탐색 그리드 크기

    async def on_start(self):
        """게임 시작 시 실행"""
        # 확장 위치 초기화
        for exp_pos in self.bot.expansion_locations_list:
            self.expansion_status[exp_pos] = "unknown"

        # 아군 시작 위치는 "ally"로 설정
        self.expansion_status[self.bot.start_location] = "ally"

        # 적 시작 위치는 "enemy"로 예측
        if self.bot.enemy_start_locations:
            enemy_start = self.bot.enemy_start_locations[0]
            self.expansion_status[enemy_start] = "enemy"

            # 적 본진 예측 기지 추가
            self.predicted_bases.append(PredictedBase(
                position=enemy_start,
                confidence=1.0,
                reason="enemy_start_location",
                predicted_time=0.0
            ))

        self.logger.info(f"[INIT] Tracking {len(self.bot.expansion_locations_list)} expansion locations")

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 1. 적 건물 발견 및 기록 (매 프레임)
            await self._discover_enemy_structures(game_time)

            # 2. 확장 위치 상태 업데이트 (5초마다)
            if iteration % 110 == 0:
                await self._update_expansion_status(game_time)

            # 3. 적 기지 예측 (10초마다)
            if iteration % 220 == 0:
                await self._predict_enemy_bases(game_time)

            # 4. 맵 탐색 진행도 업데이트 (10초마다)
            if iteration % 220 == 0:
                self._update_exploration_progress()

            # 5. 파괴된 건물 확인 (5초마다)
            if iteration % 110 == 0:
                await self._check_destroyed_structures(game_time)

            # 6. 디버그 출력 (20초마다)
            if iteration % 440 == 0:
                self._print_status(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[MAP_MEMORY] Error: {e}")

    async def _discover_enemy_structures(self, game_time: float):
        """적 건물 발견 및 기록"""
        if not hasattr(self.bot, "enemy_structures"):
            return

        for structure in self.bot.enemy_structures:
            tag = structure.tag

            if tag not in self.discovered_structures:
                # 새로운 건물 발견
                self.discovered_structures[tag] = DiscoveredStructure(
                    unit_type=structure.type_id,
                    position=structure.position,
                    first_seen_time=game_time,
                    last_seen_time=game_time,
                    race=str(self.bot.enemy_race)
                )
                self.total_structures_discovered += 1

                self.logger.info(
                    f"[DISCOVERY] New enemy structure: {structure.type_id.name} "
                    f"at {structure.position} [{int(game_time)}s]"
                )

                # 타운홀 발견 시 확장 위치 업데이트
                if self._is_townhall(structure.type_id):
                    self._update_expansion_near_position(structure.position, "enemy")
            else:
                # 기존 건물 업데이트
                self.discovered_structures[tag].last_seen_time = game_time

    def _is_townhall(self, unit_type: UnitTypeId) -> bool:
        """타운홀 건물인지 확인"""
        townhalls = {
            UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
            UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS,
            UnitTypeId.NEXUS
        }
        return unit_type in townhalls

    def _update_expansion_near_position(self, position: Point2, status: str):
        """위치 근처의 확장 지점 상태 업데이트"""
        for exp_pos in self.bot.expansion_locations_list:
            if position.distance_to(exp_pos) < 10:
                self.expansion_status[exp_pos] = status
                break

    async def _update_expansion_status(self, game_time: float):
        """확장 위치 상태 업데이트"""
        for exp_pos, current_status in list(self.expansion_status.items()):
            if current_status != "unknown":
                continue

            # 아군 건물 확인
            if self.bot.townhalls.exists:
                for townhall in self.bot.townhalls:
                    if townhall.position.distance_to(exp_pos) < 10:
                        self.expansion_status[exp_pos] = "ally"
                        break

            # 적 건물 확인 (기억된 건물 포함)
            for structure in self.discovered_structures.values():
                if structure.is_destroyed:
                    continue

                if self._is_townhall(structure.unit_type):
                    if structure.position.distance_to(exp_pos) < 10:
                        self.expansion_status[exp_pos] = "enemy"
                        break

    async def _predict_enemy_bases(self, game_time: float):
        """적 기지 위치 예측"""
        # 1. 확장 위치 기반 예측
        for exp_pos, status in self.expansion_status.items():
            if status == "unknown":
                # 거리 기반 예측
                distance_to_enemy = exp_pos.distance_to(self.bot.enemy_start_locations[0]) if self.bot.enemy_start_locations else 999

                # 적 본진에 가까울수록 높은 확률
                if distance_to_enemy < 30:
                    confidence = 0.8
                elif distance_to_enemy < 50:
                    confidence = 0.5
                else:
                    confidence = 0.3

                # 이미 예측된 위치인지 확인
                already_predicted = any(
                    pred.position.distance_to(exp_pos) < 5
                    for pred in self.predicted_bases
                )

                if not already_predicted and confidence >= 0.5:
                    self.predicted_bases.append(PredictedBase(
                        position=exp_pos,
                        confidence=confidence,
                        reason="expansion_location",
                        predicted_time=game_time
                    ))

        # 2. 미네랄 패치 기반 예측
        if hasattr(self.bot, "mineral_field"):
            for mineral in self.bot.mineral_field:
                # 미네랄 그룹 찾기
                nearby_minerals = self.bot.mineral_field.closer_than(8, mineral)

                if nearby_minerals.amount >= 6:  # 미네랄 패치가 6개 이상 = 기지 후보
                    mineral_center = nearby_minerals.center

                    # 이미 발견되었거나 예측된 위치인지 확인
                    already_known = any(
                        struct.position.distance_to(mineral_center) < 15
                        for struct in self.discovered_structures.values()
                        if self._is_townhall(struct.unit_type)
                    )

                    already_predicted = any(
                        pred.position.distance_to(mineral_center) < 15
                        for pred in self.predicted_bases
                    )

                    if not already_known and not already_predicted:
                        # 확장 위치와 가까운지 확인
                        near_expansion = any(
                            exp_pos.distance_to(mineral_center) < 10
                            for exp_pos in self.bot.expansion_locations_list
                        )

                        if near_expansion:
                            self.predicted_bases.append(PredictedBase(
                                position=mineral_center,
                                confidence=0.6,
                                reason="mineral_patch",
                                predicted_time=game_time
                            ))

    def _update_exploration_progress(self):
        """맵 탐색 진행도 업데이트"""
        if not hasattr(self.bot, "state") or not hasattr(self.bot.state, "visibility"):
            return

        # 맵을 그리드로 나누어 탐색 진행도 계산
        playable = self.bot.game_info.playable_area

        total_cells = 0
        explored_cells = 0

        for x in range(int(playable.x), int(playable.x + playable.width), self.GRID_SIZE):
            for y in range(int(playable.y), int(playable.y + playable.height), self.GRID_SIZE):
                total_cells += 1

                pos = Point2((x, y))
                # Visibility: 0 = Hidden, 1 = Fogged, 2 = Visible
                visibility = self.bot.state.visibility.data_numpy[int(pos.y), int(pos.x)]

                if visibility > 0:  # Fogged or Visible
                    explored_cells += 1

        self.exploration_progress = (explored_cells / total_cells * 100) if total_cells > 0 else 0

    async def _check_destroyed_structures(self, game_time: float):
        """파괴된 건물 확인"""
        # 현재 존재하는 적 건물 태그 집합
        current_enemy_tags = {structure.tag for structure in self.bot.enemy_structures}

        # 기억된 건물 중 현재 존재하지 않는 건물 찾기
        for tag, structure in self.discovered_structures.items():
            if structure.is_destroyed:
                continue

            # 마지막으로 본 지 10초 이상 지났고, 현재 보이지 않으면 파괴된 것으로 간주
            if tag not in current_enemy_tags:
                time_since_last_seen = game_time - structure.last_seen_time

                if time_since_last_seen > 10.0:
                    structure.is_destroyed = True
                    structure.destroyed_time = game_time
                    self.total_structures_destroyed += 1

                    self.logger.info(
                        f"[DESTROYED] {structure.unit_type.name} at {structure.position} "
                        f"(not seen for {int(time_since_last_seen)}s)"
                    )

    def get_all_known_enemy_structures(self) -> List[DiscoveredStructure]:
        """모든 기억된 적 건물 반환 (파괴되지 않은 것만)"""
        return [
            structure for structure in self.discovered_structures.values()
            if not structure.is_destroyed
        ]

    def get_enemy_bases(self) -> List[Point2]:
        """
        모든 적 기지 위치 반환 (발견된 + 예측된)

        우선순위:
        1. 발견된 타운홀 (확실)
        2. 확장 위치에서 "enemy" 상태
        3. 예측된 기지 (신뢰도 0.5+)
        """
        bases = []

        # 1. 발견된 타운홀
        for structure in self.discovered_structures.values():
            if not structure.is_destroyed and self._is_townhall(structure.unit_type):
                bases.append(structure.position)

        # 2. 확장 위치에서 "enemy" 상태
        for exp_pos, status in self.expansion_status.items():
            if status == "enemy":
                # 중복 체크
                if not any(base.distance_to(exp_pos) < 5 for base in bases):
                    bases.append(exp_pos)

        # 3. 예측된 기지 (신뢰도 0.5+)
        for predicted in self.predicted_bases:
            if predicted.confidence >= 0.5:
                # 중복 체크
                if not any(base.distance_to(predicted.position) < 5 for base in bases):
                    bases.append(predicted.position)

        return bases

    def get_next_target_base(self) -> Optional[Point2]:
        """
        다음 공격 목표 기지 반환

        우선순위:
        1. 가장 약한 확인된 기지
        2. 가장 가까운 예측 기지
        """
        all_bases = self.get_enemy_bases()

        if not all_bases:
            return None

        # 우리 본진에서 가장 가까운 기지
        if self.bot.townhalls.exists:
            our_base = self.bot.townhalls.first.position
            return min(all_bases, key=lambda pos: pos.distance_to(our_base))

        return all_bases[0]

    def _print_status(self, game_time: float):
        """상태 출력"""
        known_bases = len(self.get_enemy_bases())
        predicted_count = sum(1 for p in self.predicted_bases if p.confidence >= 0.5)

        self.logger.info(
            f"[MAP_MEMORY] [{int(game_time)}s] "
            f"Structures: {len(self.discovered_structures)} "
            f"(Destroyed: {self.total_structures_destroyed}), "
            f"Known Bases: {known_bases} (Predicted: {predicted_count}), "
            f"Exploration: {self.exploration_progress:.1f}%"
        )

    def get_statistics(self) -> Dict:
        """통계 반환"""
        return {
            "total_structures_discovered": self.total_structures_discovered,
            "total_structures_destroyed": self.total_structures_destroyed,
            "active_structures": len([s for s in self.discovered_structures.values() if not s.is_destroyed]),
            "known_enemy_bases": len(self.get_enemy_bases()),
            "predicted_bases": len([p for p in self.predicted_bases if p.confidence >= 0.5]),
            "exploration_progress": f"{self.exploration_progress:.1f}%",
            "expansion_status": {
                "enemy": sum(1 for s in self.expansion_status.values() if s == "enemy"),
                "ally": sum(1 for s in self.expansion_status.values() if s == "ally"),
                "unknown": sum(1 for s in self.expansion_status.values() if s == "unknown")
            }
        }
