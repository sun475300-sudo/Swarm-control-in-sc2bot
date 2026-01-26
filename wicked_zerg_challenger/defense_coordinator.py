# -*- coding: utf-8 -*-
"""
Defense Coordinator - 통합 방어 시스템

여러 방어 시스템을 하나로 통합:
- EarlyDefenseSystem (초반 러시 대응)
- MultiBaseDefense (멀티 기지 방어)
- EmergencyMode (긴급 상황 대응)

Blackboard 기반 아키텍처:
- GameStateBlackboard를 통해 위협 정보 공유
- Dynamic Authority로 긴급 시 생산 권한 획득

참고: LOGIC_IMPROVEMENT_REPORT.md - Section 4 (Defense Consolidation)
"""

from typing import Optional, Set, List
import math

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    BotAI = None
    UnitTypeId = None
    AbilityId = None
    Point2 = None

try:
    from game_state_blackboard import GameStateBlackboard, ThreatLevel, AuthorityMode
except ImportError:
    GameStateBlackboard = None
    ThreatLevel = None
    AuthorityMode = None


class DefenseCoordinator:
    """
    통합 방어 시스템

    책임:
    1. 위협 감지 및 평가
    2. 긴급 방어 병력 생산 요청
    3. 방어 건물 배치 (가시 촉수, 포자 촉수)
    4. 병력 배치 및 방어선 형성
    5. 일꾼 대피 및 보호
    """

    def __init__(self, bot: BotAI, blackboard: Optional[GameStateBlackboard] = None):
        self.bot = bot
        self.blackboard = blackboard

        # === 방어 상태 ===
        self.detected_threats: Set[int] = set()  # 감지된 적 태그
        self.defending_units: Set[int] = set()   # 방어 중인 유닛 태그

        # === 초반 방어 (0-3분) ===
        self.early_game_threshold = 180.0
        self.pool_requested = False
        self.first_queen_requested = False

        # === 방어 건물 ===
        self.spine_crawler_positions: List[Point2] = []
        self.spore_crawler_positions: List[Point2] = []

        # === 성능 최적화 ===
        self.last_threat_check = 0.0
        self.threat_check_interval = 0.5  # 0.5초마다 체크

    async def execute(self, iteration: int) -> None:
        """방어 로직 실행"""
        if not self.bot or not self.blackboard:
            return

        game_time = self.bot.time

        # 1. 위협 감지 및 평가 (주기적으로)
        if game_time - self.last_threat_check >= self.threat_check_interval:
            await self._detect_and_evaluate_threats()
            self.last_threat_check = game_time

        # 2. Blackboard 위협 정보 업데이트
        self._update_blackboard_threat()

        # 3. 초반 방어 (0-3분)
        if game_time < self.early_game_threshold:
            await self._early_game_defense()

        # 4. 긴급 방어 (위협 HIGH 이상)
        if self.blackboard.threat.level >= ThreatLevel.HIGH:
            await self._emergency_defense()

        # 5. 방어 건물 배치
        if iteration % 50 == 0:  # 2초마다
            await self._build_defense_structures()

        # 6. 병력 방어 배치
        await self._position_defense_units()

    # ========== 위협 감지 및 평가 ==========

    async def _detect_and_evaluate_threats(self) -> None:
        """
        적 유닛 감지 및 위협 수준 평가

        위협 수준 기준:
        - NONE: 적 없음
        - LOW: 정찰 유닛만
        - MEDIUM: 소규모 병력 (본진 근처)
        - HIGH: 중규모 병력 또는 초반 러시
        - CRITICAL: 대규모 공격 또는 올인
        """
        if not self.bot.enemy_units:
            # 적이 없으면 안전
            self.detected_threats.clear()
            return

        # 우리 기지 위치
        bases = list(self.bot.townhalls)
        if not bases:
            return

        # 각 기지 근처 적 확인
        total_enemy_supply = 0.0
        max_enemy_near_base = 0
        is_rushing = False
        is_air_threat = False
        threat_position = None

        for base in bases:
            # 기지 25 거리 내 적
            nearby_enemies = self.bot.enemy_units.closer_than(25, base.position)

            if nearby_enemies:
                # 적 태그 저장
                for enemy in nearby_enemies:
                    self.detected_threats.add(enemy.tag)

                # 적 병력 카운트
                enemy_count = len(nearby_enemies)
                if enemy_count > max_enemy_near_base:
                    max_enemy_near_base = enemy_count
                    threat_position = base.position

                # 공중 위협 확인
                if any(getattr(e, "is_flying", False) for e in nearby_enemies):
                    is_air_threat = True

                # 보급 계산 (근사치)
                for enemy in nearby_enemies:
                    if enemy.type_id in [UnitTypeId.ZERGLING, UnitTypeId.MARINE]:
                        total_enemy_supply += 0.5
                    elif enemy.type_id in [UnitTypeId.REAPER, UnitTypeId.BANELING]:
                        total_enemy_supply += 1
                    elif enemy.type_id in [UnitTypeId.ROACH, UnitTypeId.STALKER]:
                        total_enemy_supply += 2
                    elif enemy.type_id in [UnitTypeId.IMMORTAL, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED]:
                        total_enemy_supply += 4
                    else:
                        total_enemy_supply += 2  # 기본값

        # 게임 시간 고려한 러시 판정
        game_time = self.bot.time
        if game_time < 180:  # 3분 이내
            # 초반 러시: 적 병력 4+ 또는 보급 4+
            if max_enemy_near_base >= 4 or total_enemy_supply >= 4:
                is_rushing = True
        elif game_time < 300:  # 5분 이내
            # 중반 러시: 적 병력 8+ 또는 보급 8+
            if max_enemy_near_base >= 8 or total_enemy_supply >= 8:
                is_rushing = True

        # 위협 레벨 결정
        threat_level = ThreatLevel.NONE

        if is_rushing or total_enemy_supply >= 20:
            threat_level = ThreatLevel.CRITICAL
        elif total_enemy_supply >= 10 or max_enemy_near_base >= 6:
            threat_level = ThreatLevel.HIGH
        elif max_enemy_near_base >= 3 or total_enemy_supply >= 4:
            threat_level = ThreatLevel.MEDIUM
        elif max_enemy_near_base >= 1:
            threat_level = ThreatLevel.LOW

        # Blackboard 업데이트
        if self.blackboard:
            self.blackboard.update_threat(
                level=threat_level,
                enemy_army_supply=total_enemy_supply,
                enemy_units_near_base=max_enemy_near_base,
                is_rushing=is_rushing,
                is_air_threat=is_air_threat,
                threat_position=threat_position
            )

    def _update_blackboard_threat(self) -> None:
        """Blackboard 위협 상태 업데이트"""
        if not self.blackboard:
            return

        # 공격받고 있는지 확인
        is_under_attack = len(self.detected_threats) > 0

        self.blackboard.is_under_attack = is_under_attack

        # 공격받은 기지 태그 업데이트
        if is_under_attack:
            for base in self.bot.townhalls:
                nearby_enemies = self.bot.enemy_units.closer_than(15, base.position)
                if nearby_enemies:
                    self.blackboard.attacked_bases.add(base.tag)

    # ========== 초반 방어 (0-3분) ==========

    async def _early_game_defense(self) -> None:
        """
        초반 방어 (0-3분)

        목표:
        - 12풀 Spawning Pool
        - 첫 Queen 생산
        - 초기 Zergling 4-6마리
        """
        supply_used = self.bot.supply_used
        game_time = self.bot.time

        # 1. Spawning Pool 우선 건설 (12 드론 이후)
        if not self.pool_requested and supply_used >= 12:
            if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).exists:
                if not self.bot.already_pending(UnitTypeId.SPAWNINGPOOL):
                    # Blackboard 통해 건설 예약
                    if self.blackboard.reserve_building(UnitTypeId.SPAWNINGPOOL, "DefenseCoordinator"):
                        print(f"[DEFENSE] Requesting Spawning Pool at {game_time:.1f}s")
                        self.pool_requested = True

        # 2. 첫 Queen 생산 요청
        pools_ready = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if pools_ready and not self.first_queen_requested:
            queen_count = self.blackboard.get_unit_count(UnitTypeId.QUEEN)
            if queen_count.total == 0:
                # 긴급 우선순위로 Queen 요청
                self.blackboard.request_production(
                    UnitTypeId.QUEEN, 1, "DefenseCoordinator", priority=0
                )
                self.first_queen_requested = True
                print(f"[DEFENSE] Requesting first Queen at {game_time:.1f}s")

        # 3. 초기 Zergling 생산 요청 (러시 감지 시)
        if pools_ready and self.blackboard.threat.is_rushing:
            zergling_count = self.blackboard.get_unit_count(UnitTypeId.ZERGLING)
            target_zerglings = 6  # 초반 목표: 6마리

            if zergling_count.total < target_zerglings:
                needed = target_zerglings - zergling_count.total
                self.blackboard.request_production(
                    UnitTypeId.ZERGLING, needed, "DefenseCoordinator", priority=0
                )

    # ========== 긴급 방어 ==========

    async def _emergency_defense(self) -> None:
        """
        긴급 방어 모드

        위협 HIGH 이상일 때:
        - 드론 생산 중단
        - 전투 유닛 최대 생산
        - 일꾼 대피
        """
        if not self.blackboard:
            return

        threat_level = self.blackboard.threat.level

        # 1. Authority 모드를 EMERGENCY로 전환
        if threat_level == ThreatLevel.CRITICAL:
            self.blackboard.set_authority_mode(
                AuthorityMode.EMERGENCY,
                f"Critical threat: {self.blackboard.threat.enemy_units_near_base} enemies"
            )

        # 2. 긴급 병력 생산 요청
        await self._request_emergency_units()

        # 3. 일꾼 대피
        await self._evacuate_workers()

    async def _request_emergency_units(self) -> None:
        """긴급 병력 생산 요청"""
        if not self.blackboard:
            return

        game_time = self.bot.time
        pools_ready = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready

        if not pools_ready:
            return

        # 현재 병력 확인
        zergling_count = self.blackboard.get_unit_count(UnitTypeId.ZERGLING)
        queen_count = self.blackboard.get_unit_count(UnitTypeId.QUEEN)

        # 긴급 목표 병력
        if game_time < 180:  # 3분 이내
            target_zerglings = 12
            target_queens = 2
        elif game_time < 300:  # 5분 이내
            target_zerglings = 20
            target_queens = 3
        else:
            target_zerglings = 30
            target_queens = 4

        # Zergling 요청
        if zergling_count.total < target_zerglings:
            needed = target_zerglings - zergling_count.total
            self.blackboard.request_production(
                UnitTypeId.ZERGLING, needed, "DefenseCoordinator", priority=0
            )

        # Queen 요청
        if queen_count.total < target_queens:
            needed = target_queens - queen_count.total
            self.blackboard.request_production(
                UnitTypeId.QUEEN, needed, "DefenseCoordinator", priority=0
            )

    async def _evacuate_workers(self) -> None:
        """일꾼 대피 (위험 지역에서)"""
        if not self.bot.workers:
            return

        # 위험 위치 확인
        threat_pos = self.blackboard.threat.threat_position
        if not threat_pos:
            return

        # 위험 근처 일꾼 찾기
        workers_in_danger = self.bot.workers.closer_than(10, threat_pos)

        if workers_in_danger:
            # 가장 가까운 안전한 기지로 대피
            safe_bases = [
                base for base in self.bot.townhalls
                if base.position.distance_to(threat_pos) > 20
            ]

            if safe_bases:
                safe_base = safe_bases[0]
                for worker in workers_in_danger:
                    worker.move(safe_base.position)

    # ========== 방어 건물 배치 ==========

    async def _build_defense_structures(self) -> None:
        """방어 건물 배치 (가시 촉수, 포자 촉수)"""
        if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            return

        # 각 기지마다 방어 건물 확인
        for base in self.bot.townhalls:
            await self._build_base_defense(base)

    async def _build_base_defense(self, base) -> None:
        """기지별 방어 건물 배치"""
        # 기지 근처 가시 촉수 개수
        spines_nearby = self.bot.structures(UnitTypeId.SPINECRAWLER).closer_than(15, base.position)

        # 위협 수준에 따라 목표 개수 결정
        threat_level = self.blackboard.threat.level if self.blackboard else ThreatLevel.NONE

        if threat_level >= ThreatLevel.HIGH:
            target_spines = 3
        elif threat_level >= ThreatLevel.MEDIUM:
            target_spines = 2
        else:
            target_spines = 1

        # 부족하면 건설 요청
        if len(spines_nearby) < target_spines:
            if self.bot.can_afford(UnitTypeId.SPINECRAWLER):
                # 건설 위치: 기지 앞쪽
                build_pos = base.position.towards(self.bot.game_info.map_center, 8)

                # 건설 (점막 체크 필요)
                if self.bot.workers.exists:
                    worker = self.bot.workers.closest_to(build_pos)
                    worker.build(UnitTypeId.SPINECRAWLER, build_pos)
                    print(f"[DEFENSE] Building Spine Crawler at base")

        # 공중 위협 시 포자 촉수
        if self.blackboard and self.blackboard.threat.is_air_threat:
            spores_nearby = self.bot.structures(UnitTypeId.SPORECRAWLER).closer_than(15, base.position)

            if len(spores_nearby) == 0:
                if self.bot.can_afford(UnitTypeId.SPORECRAWLER):
                    build_pos = base.position.towards(self.bot.game_info.map_center, 6)

                    if self.bot.workers.exists:
                        worker = self.bot.workers.closest_to(build_pos)
                        worker.build(UnitTypeId.SPORECRAWLER, build_pos)
                        print(f"[DEFENSE] Building Spore Crawler (air threat)")

    # ========== 병력 방어 배치 ==========

    async def _position_defense_units(self) -> None:
        """병력을 방어 위치에 배치"""
        if not self.blackboard or not self.blackboard.should_defend():
            return

        # 방어할 기지 선택 (공격받은 기지 우선)
        target_base = None

        if self.blackboard.attacked_bases:
            for base in self.bot.townhalls:
                if base.tag in self.blackboard.attacked_bases:
                    target_base = base
                    break

        if not target_base and self.bot.townhalls:
            target_base = self.bot.townhalls.first

        if not target_base:
            return

        # 방어 병력 모집
        defense_units = []

        # Zergling
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings:
            defense_units.extend(zerglings)

        # Queen
        queens = self.bot.units(UnitTypeId.QUEEN).idle
        if queens:
            defense_units.extend(queens)

        # 방어 위치: 기지 앞쪽
        defense_pos = target_base.position.towards(self.bot.game_info.map_center, 5)

        # 병력 이동
        for unit in defense_units:
            if unit.distance_to(defense_pos) > 10:
                unit.move(defense_pos)
                self.defending_units.add(unit.tag)

    # ========== 상태 조회 ==========

    def get_status(self) -> dict:
        """방어 시스템 상태 반환"""
        threat_level = self.blackboard.threat.level.name if self.blackboard else "UNKNOWN"

        return {
            "threat_level": threat_level,
            "detected_threats": len(self.detected_threats),
            "defending_units": len(self.defending_units),
            "pool_requested": self.pool_requested,
            "first_queen_requested": self.first_queen_requested,
        }
