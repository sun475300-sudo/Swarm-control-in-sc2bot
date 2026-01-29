"""
Enhanced Scouting System - 통합 정찰 시스템

다층 정찰 체계로 적의 전략을 조기에 파악합니다:
1. Worker Scout (13 supply) - 적 자연 확장과 본진 정찰
2. Overlord Scout - 맵 외곽 및 프록시 탐지
3. Zergling Patrol - 확장 감시 및 프록시 탐지
4. Scout Data Analysis - 치즈, 타이밍 러시, 테크 경로 식별

Features:
- 13 supply 드론 정찰 (적 자연 확장 및 본진 체크)
- Overlord 안전 경로 정찰 (맵 코너, 프록시 위치)
- Zergling 순찰 (확장 위치, 적 이동 경로)
- 적 빌드 분석 (Gas 타이밍, Pool 타이밍, 확장 타이밍)
"""

from typing import Optional, List, Set, Dict, Tuple
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        DRONE = "DRONE"
        ZERGLING = "ZERGLING"
        OVERLORD = "OVERLORD"
    Point2 = tuple
    Unit = None


class EnhancedScoutSystem:
    """
    통합 정찰 시스템 - Worker, Overlord, Zergling 정찰 통합
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("EnhancedScout")

        # ★ Worker Scout (13 supply) ★
        self.worker_scout_tag: Optional[int] = None
        self.worker_scout_sent = False
        self.worker_scout_threshold = 13  # 13 supply에 출발
        self.worker_scout_waypoints: List[Point2] = []
        self.worker_current_wp = 0

        # ★ Overlord Scout ★
        self.overlord_scout_tag: Optional[int] = None
        self.overlord_scout_sent = False
        self.overlord_waypoints: List[Point2] = []
        self.overlord_current_wp = 0

        # ★ Zergling Patrol ★
        self.zergling_patrol_tags: List[int] = []
        self.zergling_patrol_assigned = False
        self.zergling_patrol_count = 2  # 2마리의 Zergling 순찰
        self.zergling_waypoints: Dict[int, List[Point2]] = {}
        self.zergling_current_wp: Dict[int, int] = {}

        # ★ Scout Data ★
        self.enemy_pool_timing: Optional[float] = None
        self.enemy_gas_timing: Optional[float] = None
        self.enemy_natural_timing: Optional[float] = None
        self.enemy_third_timing: Optional[float] = None
        self.enemy_tech_buildings: Dict[str, float] = {}
        self.enemy_army_units: Dict[str, int] = {}

        # ★ Analysis Results ★
        self.is_cheese: bool = False
        self.is_timing_attack: bool = False
        self.is_fast_expand: bool = False
        self.tech_path: str = "UNKNOWN"  # "RUSH", "TECH", "MACRO", "UNKNOWN"

        # ★ Scouted Locations ★
        self.main_base_scouted = False
        self.natural_scouted = False
        self.proxy_locations_scouted: Set[Tuple[float, float]] = set()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 1. Worker Scout (13 supply)
            if not self.worker_scout_sent and self.bot.supply_used >= self.worker_scout_threshold:
                await self._send_worker_scout()

            # 2. Overlord Scout (2분부터)
            if not self.overlord_scout_sent and self.bot.time >= 120:
                await self._send_overlord_scout()

            # 3. Zergling Patrol (Spawning Pool 완성 후)
            if not self.zergling_patrol_assigned and self._has_spawning_pool():
                await self._assign_zergling_patrol()

            # 4. Update Scout Commands
            if iteration % 22 == 0:  # ~1초마다
                await self._update_worker_scout()
                await self._update_overlord_scout()
                await self._update_zergling_patrol()

            # 5. Collect Scout Information
            if iteration % 44 == 0:  # ~2초마다
                await self._collect_scout_data()

            # 6. Analyze Scout Data
            if iteration % 220 == 0:  # ~10초마다
                self._analyze_scout_data()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[ENHANCED_SCOUT] Error: {e}")

    # ========================================
    # Worker Scout (13 Supply)
    # ========================================

    async def _send_worker_scout(self):
        """13 supply에 드론 정찰 파견"""
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "townhalls"):
            return

        workers = self.bot.units(UnitTypeId.DRONE).filter(lambda w: w.is_gathering)
        if not workers:
            return

        # 미네랄 채취 중인 드론 선택
        worker = workers.first
        self.worker_scout_tag = worker.tag
        self.worker_scout_sent = True

        # ★ Worker Scout 경로 설정 ★
        self._plan_worker_scout_path()

        if self.worker_scout_waypoints:
            first_target = self.worker_scout_waypoints[0]
            self.bot.do(worker.move(first_target))

            self.logger.info(
                f"[{int(self.bot.time)}s] ★ WORKER SCOUT SENT (13 supply) → {first_target} ★"
            )

    def _plan_worker_scout_path(self):
        """Worker Scout 경로 계획"""
        if not hasattr(self.bot, "enemy_start_locations"):
            return

        enemy_start = self.bot.enemy_start_locations[0]

        # ★ 경로: 적 자연 확장 → 적 본진 → 귀환 ★
        waypoints = []

        # 1. 적 자연 확장 위치
        if hasattr(self.bot, "expansion_locations_list"):
            natural_pos = min(
                self.bot.expansion_locations_list,
                key=lambda pos: pos.distance_to(enemy_start)
            )
            waypoints.append(natural_pos)

        # 2. 적 본진
        waypoints.append(enemy_start)

        # 3. 적 본진 뒤쪽 (프록시 체크)
        map_center = self.bot.game_info.map_center
        behind_main = enemy_start.towards(map_center, -5)
        waypoints.append(behind_main)

        self.worker_scout_waypoints = waypoints

    async def _update_worker_scout(self):
        """Worker Scout 업데이트"""
        if not self.worker_scout_tag:
            return

        worker = self.bot.units.find_by_tag(self.worker_scout_tag)
        if not worker:
            # Scout died or lost
            self.worker_scout_tag = None
            return

        # Check if reached current waypoint
        if self.worker_current_wp < len(self.worker_scout_waypoints):
            target = self.worker_scout_waypoints[self.worker_current_wp]

            if worker.position.distance_to(target) < 3:
                # Reached waypoint
                self.worker_current_wp += 1
                self.logger.info(
                    f"[{int(self.bot.time)}s] ★ WORKER SCOUT reached waypoint {self.worker_current_wp}/{len(self.worker_scout_waypoints)} ★"
                )

                # Move to next waypoint
                if self.worker_current_wp < len(self.worker_scout_waypoints):
                    next_target = self.worker_scout_waypoints[self.worker_current_wp]
                    self.bot.do(worker.move(next_target))
                else:
                    # Scout complete, return to mining
                    if self.bot.townhalls.exists:
                        main_base = self.bot.townhalls.first
                        minerals = self.bot.mineral_field.closer_than(10, main_base)
                        if minerals:
                            self.bot.do(worker.gather(minerals.first))

                        self.logger.info(
                            f"[{int(self.bot.time)}s] ★ WORKER SCOUT returning to mining ★"
                        )

    # ========================================
    # Overlord Scout
    # ========================================

    async def _send_overlord_scout(self):
        """Overlord 정찰 파견 (2분부터)"""
        if not hasattr(self.bot, "units"):
            return

        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords:
            return

        # Idle Overlord 선택
        overlord = overlords.first
        self.overlord_scout_tag = overlord.tag
        self.overlord_scout_sent = True

        # ★ Overlord Scout 경로 설정 ★
        self._plan_overlord_scout_path()

        if self.overlord_waypoints:
            first_target = self.overlord_waypoints[0]
            self.bot.do(overlord.move(first_target))

            self.logger.info(
                f"[{int(self.bot.time)}s] ★ OVERLORD SCOUT SENT → {first_target} ★"
            )

    def _plan_overlord_scout_path(self):
        """Overlord Scout 경로 계획 (맵 외곽 및 프록시 위치)"""
        if not hasattr(self.bot, "game_info"):
            return

        map_center = self.bot.game_info.map_center
        playable_area = self.bot.game_info.playable_area

        # ★ 맵 4개 코너 정찰 (프록시 탐지) ★
        waypoints = [
            Point2((playable_area.x, playable_area.y)),  # Top-left
            Point2((playable_area.x + playable_area.width, playable_area.y)),  # Top-right
            Point2((playable_area.x + playable_area.width, playable_area.y + playable_area.height)),  # Bottom-right
            Point2((playable_area.x, playable_area.y + playable_area.height)),  # Bottom-left
            map_center,  # Map center
        ]

        self.overlord_waypoints = waypoints

    async def _update_overlord_scout(self):
        """Overlord Scout 업데이트"""
        if not self.overlord_scout_tag:
            return

        overlord = self.bot.units.find_by_tag(self.overlord_scout_tag)
        if not overlord:
            self.overlord_scout_tag = None
            return

        # Check if reached current waypoint
        if self.overlord_current_wp < len(self.overlord_waypoints):
            target = self.overlord_waypoints[self.overlord_current_wp]

            if overlord.position.distance_to(target) < 5:
                # Reached waypoint
                self.overlord_current_wp += 1

                # Move to next waypoint
                if self.overlord_current_wp < len(self.overlord_waypoints):
                    next_target = self.overlord_waypoints[self.overlord_current_wp]
                    self.bot.do(overlord.move(next_target))

    # ========================================
    # Zergling Patrol
    # ========================================

    def _has_spawning_pool(self) -> bool:
        """Spawning Pool 존재 확인"""
        if not hasattr(self.bot, "structures"):
            return False

        try:
            pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL)
            return pools.ready.exists
        except (ImportError, AttributeError, NameError):
            # Failed to access spawning pool structures
            return False

    async def _assign_zergling_patrol(self):
        """Zergling 순찰 할당"""
        if not hasattr(self.bot, "units"):
            return

        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if len(zerglings) < self.zergling_patrol_count:
            return

        # ★ 2마리의 Zergling을 순찰에 배치 ★
        for i in range(self.zergling_patrol_count):
            zergling = zerglings[i]
            self.zergling_patrol_tags.append(zergling.tag)

        self.zergling_patrol_assigned = True

        # ★ 각 Zergling의 순찰 경로 설정 ★
        self._plan_zergling_patrol_paths()

        self.logger.info(
            f"[{int(self.bot.time)}s] ★ ZERGLING PATROL ASSIGNED ({self.zergling_patrol_count} units) ★"
        )

    def _plan_zergling_patrol_paths(self):
        """Zergling 순찰 경로 계획"""
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        # ★ 확장 위치들을 순찰 경로로 설정 ★
        expansion_locs = list(self.bot.expansion_locations_list)

        for i, tag in enumerate(self.zergling_patrol_tags):
            # 각 Zergling마다 다른 경로 할당
            if i == 0:
                # Zergling 1: 맵 왼쪽 확장들
                patrol_path = expansion_locs[::2]  # 짝수 인덱스
            else:
                # Zergling 2: 맵 오른쪽 확장들
                patrol_path = expansion_locs[1::2]  # 홀수 인덱스

            self.zergling_waypoints[tag] = patrol_path
            self.zergling_current_wp[tag] = 0

            # 첫 웨이포인트로 이동
            if patrol_path:
                zergling = self.bot.units.find_by_tag(tag)
                if zergling:
                    self.bot.do(zergling.move(patrol_path[0]))

    async def _update_zergling_patrol(self):
        """Zergling 순찰 업데이트"""
        for tag in self.zergling_patrol_tags:
            zergling = self.bot.units.find_by_tag(tag)
            if not zergling:
                continue

            if tag not in self.zergling_waypoints:
                continue

            waypoints = self.zergling_waypoints[tag]
            current_wp_idx = self.zergling_current_wp.get(tag, 0)

            if current_wp_idx >= len(waypoints):
                # Reset to beginning (loop patrol)
                current_wp_idx = 0
                self.zergling_current_wp[tag] = 0

            target = waypoints[current_wp_idx]

            # Check if reached waypoint
            if zergling.position.distance_to(target) < 5:
                # Move to next waypoint
                current_wp_idx = (current_wp_idx + 1) % len(waypoints)
                self.zergling_current_wp[tag] = current_wp_idx

                next_target = waypoints[current_wp_idx]
                self.bot.do(zergling.move(next_target))

    # ========================================
    # Scout Data Collection
    # ========================================

    async def _collect_scout_data(self):
        """정찰 정보 수집"""
        if not hasattr(self.bot, "enemy_structures"):
            return

        game_time = self.bot.time

        # ★ 1. Gas Timing ★
        if self.enemy_gas_timing is None:
            gas_buildings = self.bot.enemy_structures.filter(
                lambda s: getattr(s.type_id, "name", "").upper() in {
                    "EXTRACTOR", "ASSIMILATOR", "REFINERY"
                }
            )
            if gas_buildings:
                self.enemy_gas_timing = game_time
                self.logger.info(f"[{int(game_time)}s] ★ ENEMY GAS detected! ★")

        # ★ 2. Pool/Barracks/Gateway Timing ★
        if self.enemy_pool_timing is None:
            production = self.bot.enemy_structures.filter(
                lambda s: getattr(s.type_id, "name", "").upper() in {
                    "SPAWNINGPOOL", "BARRACKS", "GATEWAY"
                }
            )
            if production:
                self.enemy_pool_timing = game_time
                building_type = getattr(production.first.type_id, "name", "PRODUCTION")
                self.logger.info(f"[{int(game_time)}s] ★ ENEMY {building_type} detected! ★")

        # ★ 3. Natural Expansion Timing ★
        if self.enemy_natural_timing is None and hasattr(self.bot, "enemy_start_locations"):
            enemy_start = self.bot.enemy_start_locations[0]

            # Find natural expansion near enemy start
            natural_pos = None
            if hasattr(self.bot, "expansion_locations_list"):
                expansions = [
                    pos for pos in self.bot.expansion_locations_list
                    if 5 < pos.distance_to(enemy_start) < 30
                ]
                if expansions:
                    natural_pos = min(expansions, key=lambda p: p.distance_to(enemy_start))

            if natural_pos:
                enemy_natural_bases = self.bot.enemy_structures.closer_than(10, natural_pos).filter(
                    lambda s: getattr(s.type_id, "name", "").upper() in {
                        "COMMANDCENTER", "NEXUS", "HATCHERY"
                    }
                )
                if enemy_natural_bases:
                    self.enemy_natural_timing = game_time
                    self.logger.info(f"[{int(game_time)}s] ★ ENEMY NATURAL EXPANSION detected! ★")

        # ★ 4. Tech Buildings ★
        tech_buildings = {
            "FACTORY", "STARPORT", "TWILIGHTCOUNCIL", "STARGATE",
            "ROBOTICSFACILITY", "SPIRE", "HYDRALISKDEN", "ROACHWARREN"
        }

        for building in self.bot.enemy_structures:
            building_type = getattr(building.type_id, "name", "").upper()
            if building_type in tech_buildings and building_type not in self.enemy_tech_buildings:
                self.enemy_tech_buildings[building_type] = game_time
                self.logger.info(f"[{int(game_time)}s] ★ ENEMY TECH: {building_type} ★")

        # ★ 5. Army Composition ★
        if hasattr(self.bot, "enemy_units"):
            for unit in self.bot.enemy_units:
                unit_type = getattr(unit.type_id, "name", "").upper()
                self.enemy_army_units[unit_type] = self.enemy_army_units.get(unit_type, 0) + 1

    # ========================================
    # Scout Data Analysis
    # ========================================

    def _analyze_scout_data(self):
        """정찰 데이터 분석"""
        game_time = self.bot.time

        # ★ 1. Cheese Detection ★
        # 빠른 Gas (1:30 전) + 늦은 Natural (2:30 이후) = Cheese
        if self.enemy_gas_timing and self.enemy_gas_timing < 90:
            if self.enemy_natural_timing is None or self.enemy_natural_timing > 150:
                self.is_cheese = True
                self.logger.warning(f"[{int(game_time)}s] ★★★ CHEESE SUSPECTED! ★★★")

        # ★ 2. Fast Expand Detection ★
        # Natural이 1:30 전에 있음 = Fast Expand
        if self.enemy_natural_timing and self.enemy_natural_timing < 90:
            self.is_fast_expand = True
            self.logger.info(f"[{int(game_time)}s] ★ FAST EXPAND detected ★")

        # ★ 3. Tech Path Analysis ★
        if self.enemy_tech_buildings:
            tech_count = len(self.enemy_tech_buildings)

            if tech_count >= 2:
                self.tech_path = "TECH"
            elif self.is_fast_expand:
                self.tech_path = "MACRO"
            elif self.is_cheese:
                self.tech_path = "RUSH"
            else:
                self.tech_path = "UNKNOWN"

        # ★ 4. Blackboard Update ★
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard:
            blackboard.set("enemy_is_cheese", self.is_cheese)
            blackboard.set("enemy_is_fast_expand", self.is_fast_expand)
            blackboard.set("enemy_tech_path", self.tech_path)
            blackboard.set("enemy_gas_timing", self.enemy_gas_timing)
            blackboard.set("enemy_natural_timing", self.enemy_natural_timing)

    def get_scout_report(self) -> Dict:
        """정찰 리포트 반환"""
        return {
            "worker_scout_sent": self.worker_scout_sent,
            "overlord_scout_sent": self.overlord_scout_sent,
            "zergling_patrol_assigned": self.zergling_patrol_assigned,
            "main_base_scouted": self.main_base_scouted,
            "natural_scouted": self.natural_scouted,
            "enemy_gas_timing": self.enemy_gas_timing,
            "enemy_pool_timing": self.enemy_pool_timing,
            "enemy_natural_timing": self.enemy_natural_timing,
            "enemy_tech_buildings": self.enemy_tech_buildings,
            "is_cheese": self.is_cheese,
            "is_fast_expand": self.is_fast_expand,
            "tech_path": self.tech_path,
        }
