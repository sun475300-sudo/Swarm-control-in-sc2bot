# -*- coding: utf-8 -*-
"""
Early Scout System - 초반 정찰 시스템 (Zergling 정찰)

목적: 빠르고 효과적인 Zergling 정찰
- 첫 Zergling 2마리를 적 기지로 자동 정찰
- 적의 초반 빌드 감지 (6풀, 치즈, 프록시 등)
- 확장 기지 및 맵 전체 정찰
- Overlord 보조 정찰
"""

from typing import Optional, List, Set, Dict
try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        ZERGLING = "ZERGLING"
        OVERLORD = "OVERLORD"
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        ASSIMILATOR = "ASSIMILATOR"
        REFINERY = "REFINERY"
    class Point2:
        pass
    class Unit:
        pass


# O(n^2) -> O(1) 변환: 가스 건물 type_id 집합 (set 멤버십은 O(1))
GAS_BUILDING_TYPES: Set[object] = {
    UnitTypeId.EXTRACTOR,
    UnitTypeId.ASSIMILATOR,
    UnitTypeId.REFINERY,
}


class EarlyScoutSystem:
    """
    초반 정찰 시스템 (Zergling + Overlord)

    핵심 기능:
    1. Zergling 2마리 자동 정찰 배치
    2. 적 기지, 자연 확장, 프록시 위치 정찰
    3. 치즈/러시 조기 감지
    4. Overlord 보조 정찰 (맵 센터)
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.early_game_threshold = 300.0  # 5분

        # === Zergling 정찰 ===
        self.scout_ling_tags: List[int] = []  # 정찰 Zergling 태그 리스트
        self.max_scout_lings = 3  # ★ 최대 3마리로 증가 (더 적극적 정찰)
        self.ling_scouts_assigned = False  # Zergling 배치 완료 플래그

        # === Overlord 정찰 ===
        self.scout_overlord_tag: Optional[int] = None  # 정찰 Overlord 태그
        self.overlord_scout_sent = False  # Overlord 출발 플래그

        # === 정찰 경로 ===
        self.ling_waypoints: Dict[int, List[Point2]] = {}  # 각 Zergling의 경로
        self.ling_current_wp: Dict[int, int] = {}  # 각 Zergling의 현재 웨이포인트 인덱스
        self.overlord_waypoints: List[Point2] = []  # Overlord 경로
        self.overlord_current_wp = 0  # Overlord 현재 웨이포인트

        # === 정찰 정보 ===
        self.enemy_pool_timing: Optional[float] = None
        self.enemy_gas_timing: Optional[float] = None
        self.enemy_natural_timing: Optional[float] = None
        self.enemy_early_units: Set[int] = set()  # 발견한 적 유닛 태그
        self.proxy_detected = False
        self.cheese_suspected = False

        # === 정찰 체크포인트 ===
        self.main_base_scouted = False
        self.natural_scouted = False
        self.third_scouted = False

        # === 성능 최적화 (캐싱) ===
        self._last_update = 0.0
        self._update_interval = 0.5  # 0.5초마다 업데이트

    async def execute(self, iteration: int) -> None:
        """
        메인 실행 루프 (매 프레임 호출)

        ★ IMPROVED: 5분 이후에도 정찰 결과 분석은 계속 + 재정찰 지원
        """
        # 성능 최적화: 0.5초마다만 업데이트
        if self.bot.time - self._last_update < self._update_interval:
            return
        self._last_update = self.bot.time

        # 적 정보 수집은 항상 실행 (5분 이후에도)
        await self._analyze_enemy_info()

        # 5분 이후에는 저글링 정찰만 중단 (오버로드는 계속)
        if self.bot.time <= self.early_game_threshold:
            # 1. Zergling 정찰 할당 (Pool 완성 후)
            if not self.ling_scouts_assigned:
                await self._assign_zergling_scouts()

            # 2. Zergling 정찰 관리
            if self.scout_ling_tags:
                await self._manage_zergling_scouts()

        # 3. Overlord 정찰 (게임 시작 즉시 - 5초부터) — 시간 제한 없음
        if not self.overlord_scout_sent and self.bot.time > 5:
            await self._send_overlord_scout()

        # 4. Overlord 정찰 관리 — 시간 제한 없음
        if self.scout_overlord_tag:
            await self._manage_overlord_scout()

        # ★ NEW: 5분 이후 재정찰 (enemy build 미확인 시 30초마다 저글링 재파견)
        if self.bot.time > self.early_game_threshold:
            await self._mid_game_rescouting()

    async def _assign_zergling_scouts(self) -> None:
        """
        Zergling 2마리를 정찰 임무에 배치
        """
        # Pool이 완성되어야 함
        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not pools:
            return

        # Zergling 확인
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if zerglings.amount < 2:
            return

        # 적 시작 위치 확인
        if not self.bot.enemy_start_locations:
            return

        # 이미 배치했으면 스킵
        if self.ling_scouts_assigned:
            return

        enemy_start = self.bot.enemy_start_locations[0]
        our_base = self.bot.start_location
        map_center = self.bot.game_info.map_center

        # 첫 2마리 선택
        scout_lings = zerglings.take(self.max_scout_lings)

        for i, ling in enumerate(scout_lings):
            self.scout_ling_tags.append(ling.tag)

            # 경로 생성
            if i == 0:
                # 첫 번째: 적 기지 → 자연 확장 → 3번째 확장
                waypoints = [
                    enemy_start,
                    enemy_start.towards(map_center, 8),
                    map_center
                ]
            else:
                # 두 번째: 맵 주변 → 프록시 체크
                waypoints = [
                    our_base.towards(enemy_start, 20),
                    map_center,
                    enemy_start.towards(our_base, 15)
                ]

            self.ling_waypoints[ling.tag] = waypoints
            self.ling_current_wp[ling.tag] = 0

            # 첫 웨이포인트로 이동
            self.bot.do(ling.move(waypoints[0]))

        self.ling_scouts_assigned = True
        print(f"[EARLY_SCOUT] >>> Zergling {len(scout_lings)}마리 정찰 출발! (게임 시간: {int(self.bot.time)}초)")

    async def _manage_zergling_scouts(self) -> None:
        """
        Zergling 정찰 경로 관리
        """
        # 살아있는 정찰 Zergling만 확인
        alive_scouts = self.bot.units(UnitTypeId.ZERGLING).tags_in(self.scout_ling_tags)

        for ling in alive_scouts:
            if ling.tag not in self.ling_waypoints:
                continue

            waypoints = self.ling_waypoints[ling.tag]
            current_wp_idx = self.ling_current_wp.get(ling.tag, 0)

            # 모든 웨이포인트 완료
            if current_wp_idx >= len(waypoints):
                continue

            target = waypoints[current_wp_idx]

            # 목표 지점 도착 확인
            if ling.distance_to(target) < 3:
                # 다음 웨이포인트로
                self.ling_current_wp[ling.tag] = current_wp_idx + 1

                # 정찰 체크포인트 기록
                if current_wp_idx == 0:
                    self.main_base_scouted = True
                    print(f"[EARLY_SCOUT] [OK] 적 기지 정찰 완료 (게임 시간: {int(self.bot.time)}초)")
                elif current_wp_idx == 1:
                    self.natural_scouted = True

                # 다음 목표로 이동
                if self.ling_current_wp[ling.tag] < len(waypoints):
                    self.bot.do(ling.move(waypoints[self.ling_current_wp[ling.tag]]))

    async def _send_overlord_scout(self) -> None:
        """
        Overlord를 맵 센터로 보내기 (보조 정찰)
        """
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords:
            return

        # 이미 보냈으면 스킵
        if self.overlord_scout_sent:
            return

        # 첫 번째 Overlord 선택
        scout_ol = overlords.first
        self.scout_overlord_tag = scout_ol.tag

        # ★ Phase 17: 오버로드 정찰 경로 개선 — 적 자연확장 정찰 ★
        map_center = self.bot.game_info.map_center
        enemy_start = self.bot.enemy_start_locations[0] if self.bot.enemy_start_locations else map_center

        # 적 자연 확장 추정 위치 (적 본진에서 가장 가까운 확장)
        enemy_natural = map_center.towards(enemy_start, map_center.distance_to(enemy_start) * 0.65)
        if hasattr(self.bot, "expansion_locations_list") and self.bot.expansion_locations_list:
            # 적 본진에서 가장 가까운 확장 = 적 자연
            sorted_exps = sorted(
                self.bot.expansion_locations_list,
                key=lambda p: p.distance_to(enemy_start)
            )
            if len(sorted_exps) >= 2:
                enemy_natural = sorted_exps[1]  # [0]은 적 본진, [1]이 자연

        self.overlord_waypoints = [
            map_center,
            enemy_natural,  # ★ Phase 17: 적 자연확장 정찰 (확장 여부 확인)
            map_center.towards(enemy_start, 15)  # 적 본진 근처 (안전거리)
        ]
        self.overlord_current_wp = 0

        # 이동 명령
        self.bot.do(scout_ol.move(self.overlord_waypoints[0]))

        self.overlord_scout_sent = True
        print(f"[EARLY_SCOUT] <<< Overlord 정찰 출발! (게임 시간: {int(self.bot.time)}초)")

    async def _manage_overlord_scout(self) -> None:
        """
        Overlord 정찰 경로 관리
        """
        overlords = self.bot.units(UnitTypeId.OVERLORD).tags_in([self.scout_overlord_tag])
        if not overlords:
            self.scout_overlord_tag = None
            # ★ Phase 33: 정찰 오버로드 사망 시 재파견 허용 (이전: overlord_scout_sent=True 유지 → 영구 재정찰 없음)
            self.overlord_scout_sent = False
            return

        scout_ol = overlords.first

        # 모든 웨이포인트 완료
        if self.overlord_current_wp >= len(self.overlord_waypoints):
            return

        target = self.overlord_waypoints[self.overlord_current_wp]

        # 목표 도착
        if scout_ol.distance_to(target) < 5:
            self.overlord_current_wp += 1

            # 다음 목표로 이동
            if self.overlord_current_wp < len(self.overlord_waypoints):
                self.bot.do(scout_ol.move(self.overlord_waypoints[self.overlord_current_wp]))

    async def _analyze_enemy_info(self) -> None:
        """
        적 정보 수집 및 분석 (캐싱된 데이터 사용)
        """
        # 적 건물 확인 (한 번만 검사)
        if not self.enemy_pool_timing and self.bot.enemy_structures:
            for structure in self.bot.enemy_structures:
                # Spawning Pool 발견
                if structure.type_id == UnitTypeId.SPAWNINGPOOL:
                    self.enemy_pool_timing = self.bot.time
                    print(f"[EARLY_SCOUT] 🏗️ 적 Pool 발견! (타이밍: {int(self.bot.time)}초)")

                    # 6풀 의심 (90초 이전)
                    if self.bot.time < 90:
                        self.cheese_suspected = True
                        print(f"[EARLY_SCOUT] [!] 조기 러시 의심! (치즈 가능성)")

                # Gas 발견
                if structure.type_id in GAS_BUILDING_TYPES:
                    if not self.enemy_gas_timing:
                        self.enemy_gas_timing = self.bot.time
                        print(f"[EARLY_SCOUT] [GAS] 적 가스 발견! (타이밍: {int(self.bot.time)}초)")

        # 적 유닛 카운트 (새로운 유닛만 추가)
        if self.bot.enemy_units:
            for unit in self.bot.enemy_units:
                if unit.tag not in self.enemy_early_units:
                    self.enemy_early_units.add(unit.tag)

    async def _mid_game_rescouting(self) -> None:
        """
        ★ NEW: 중반 재정찰 시스템

        5분 이후 30초마다 idle 저글링 1마리를 적 기지로 정찰 파견.
        적 테크 변화를 지속적으로 추적.
        """
        # 30초마다만 실행
        last_rescout = getattr(self, "_last_rescout_time", 0.0)
        if self.bot.time - last_rescout < 30.0:
            return
        self._last_rescout_time = self.bot.time

        # idle 저글링 찾기
        zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
        # ★ Phase 33: 최소 2마리로 하향 (이전: 4 — 중반에 idle 저글링 4마리가 없어 미발동)
        if not zerglings.exists or zerglings.amount < 2:
            return  # 최소 2마리 이상 idle 상태여야 1마리 파견

        # 적 기지 위치
        if not self.bot.enemy_start_locations:
            return

        enemy_start = self.bot.enemy_start_locations[0]

        # 가장 가까운 idle 저글링 1마리 파견
        scout_ling = zerglings.closest_to(enemy_start)
        # ★ Phase 33: move() → attack() — 적 만나도 도망 안 하고 정찰 유지
        self.bot.do(scout_ling.attack(enemy_start))

        if int(self.bot.time) % 60 < 5:
            print(f"[EARLY_SCOUT] [{int(self.bot.time)}s] Mid-game rescout: Zergling sent to enemy base")

    def is_cheese_detected(self) -> bool:
        """치즈/러시 감지 여부"""
        return self.cheese_suspected

    def get_scout_status(self) -> str:
        """정찰 상태 반환"""
        status_parts = []

        # Zergling 정찰
        if self.ling_scouts_assigned:
            zergling_tags: Set[int] = {u.tag for u in self.bot.units(UnitTypeId.ZERGLING)}
            alive_scouts = len([tag for tag in self.scout_ling_tags if tag in zergling_tags])
            status_parts.append(f"Lings: {alive_scouts}/{self.max_scout_lings}")
        else:
            status_parts.append("Lings: 대기")

        # Overlord 정찰
        if self.overlord_scout_sent:
            status_parts.append("OL: 정찰 중")
        else:
            status_parts.append("OL: 대기")

        # 정찰 진행도
        checkpoints = []
        if self.main_base_scouted:
            checkpoints.append("메인")
        if self.natural_scouted:
            checkpoints.append("자연")

        if checkpoints:
            status_parts.append(f"체크: {','.join(checkpoints)}")

        # 치즈 감지
        if self.cheese_suspected:
            status_parts.append("[!]치즈!")

        return " | ".join(status_parts) if status_parts else "정찰 준비 중"
