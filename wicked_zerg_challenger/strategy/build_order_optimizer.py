"""
Build Order Optimizer - 빌드 오더 최적화

초반 게임 빌드 순서를 최적화하여 효율성을 극대화합니다:
1. 17 Hatchery, 18 Gas, 17 Pool 표준 오프너
2. Overlord 타이밍 최적화 (인구수 막힘 방지)
3. Queen 생산 우선순위 (첫 100 가스는 항상 Queen)
4. Drone 포화 마일스톤 (기지당 미네랄 16/16, 가스 3/3)

Features:
- Supply block 방지 시스템
- Gas 우선순위 관리 (Queen > Metabolic Boost > 유닛)
- Drone 포화도 자동 관리
- 빌드 순서 검증 및 교정
"""

from typing import Dict, Set

from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:

    class BotAI:
        pass

    class _SC2StubSymbol:
        """Sentinel sc2 enum member used when python-sc2 is unavailable.

        Hashable, comparable, stringifies to its name, but is *not* a
        Python ``str`` so build-order classifiers can distinguish stub
        enum members from upgrade-name strings."""

        __slots__ = ("_name",)

        def __init__(self, name):
            self._name = name

        def __eq__(self, other):
            if isinstance(other, _SC2StubSymbol):
                return other._name == self._name
            return NotImplemented

        def __hash__(self):
            return hash(("_SC2StubSymbol", self._name))

        def __repr__(self):
            return self._name

        def __str__(self):
            return self._name

    class _SC2StubMeta(type):
        _cache: dict = {}

        def __getattr__(cls, name):
            key = (cls.__name__, name)
            sym = cls._cache.get(key)
            if sym is None:
                sym = _SC2StubSymbol(name)
                cls._cache[key] = sym
            return sym
    class UnitTypeId(metaclass=_SC2StubMeta):
        pass

    class UpgradeId(metaclass=_SC2StubMeta):
        pass

    Point2 = tuple


class BuildOrderOptimizer:
    """
    빌드 오더 최적화 시스템
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("BuildOrder")

        # * Build Order Configuration *
        self.HATCHERY_SUPPLY = 17  # 17 supply에 Hatchery
        self.GAS_SUPPLY = 18  # 18 supply에 Gas
        self.POOL_SUPPLY = 17  # 17 supply에 Pool

        # * Supply Block Prevention *
        self.overlord_buffer = 2  # 인구수 여유분
        self.overlord_requested = False

        # * Gas Priority System *
        self.gas_reserved_for_queen = False
        self.first_queen_made = False
        self.metabolic_boost_requested = False
        self.queens_per_base = 1  # 기지당 Queen 수
        self.first_queen_made = False

        # * Drone Saturation *
        self.MINERALS_PER_BASE = 16  # 기지당 미네랄 드론
        self.GAS_PER_EXTRACTOR = 3  # 가스당 드론

        # * Build Order State *
        self.expansion_placed = False
        self.pool_placed = False
        self.gas_placed = False
        self.first_overlord_made = False

        # * Milestones *
        self.milestones_completed: Set[str] = set()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 1. Early game build order (5분까지)
            if self.bot.time < 300:
                await self._execute_early_build_order()

            # 2. Supply block prevention (always active)
            if iteration % 22 == 0:  # ~1초마다
                await self._prevent_supply_block()

            # 3. Gas priority management
            if iteration % 33 == 0:  # ~1.5초마다
                self._manage_gas_priority()

            # 4. Drone saturation management
            if iteration % 44 == 0:  # ~2초마다
                await self._manage_drone_saturation()

            # 5. Build milestones tracking
            if iteration % 110 == 0:  # ~5초마다
                self._track_milestones()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[BUILD_ORDER] Error: {e}")

    # ========================================
    # Early Game Build Order (17/18/17)
    # ========================================

    async def _execute_early_build_order(self):
        """
        초반 빌드 오더 실행

        17 Hatchery, 18 Gas, 17 Pool
        """
        supply = self.bot.supply_used

        # * 1. First Overlord (14 supply) *
        if supply >= 14 and not self.first_overlord_made:
            await self._build_overlord()
            self.first_overlord_made = True

        # * 2. Hatchery at 17 supply *
        if supply >= self.HATCHERY_SUPPLY and not self.expansion_placed:
            await self._build_expansion()
        if not self._has_expansion_started() and self.bot.time < 120:
            return

        # * 3. Spawning Pool at 17 supply *
        if supply >= self.POOL_SUPPLY and not self.pool_placed:
            await self._build_spawning_pool()

        # * 4. Extractor at 18 supply *
        if supply >= self.GAS_SUPPLY and not self.gas_placed:
            await self._build_extractor()

        # * 5. Queen from first 100 gas *
        if not self.first_queen_made and self._can_build_queen():
            await self._build_queen()

    async def _build_overlord(self):
        """Overlord 생산"""
        if not hasattr(self.bot, "units"):
            return

        larvae = self.bot.units(UnitTypeId.LARVA)
        if not larvae or self.bot.minerals < 100:
            return

        # Train Overlord
        if larvae.idle:
            self.bot.do(larvae.first.train(UnitTypeId.OVERLORD))
            self.logger.info(
                f"[{int(self.bot.time)}s] [*] Overlord trained (Supply: {self.bot.supply_used}) [*]"
            )

    async def _build_expansion(self):
        """자연 확장 Hatchery 건설"""
        if self._has_expansion_started():
            self.expansion_placed = True
            return

        if self.bot.minerals < 300:
            return

        if not hasattr(self.bot, "expand_now"):
            return

        # * 자연 확장 위치 찾기 *
        await self.bot.expand_now()
        if not self._has_expansion_started():
            return
        self.expansion_placed = True

        self.logger.info(
            f"[{int(self.bot.time)}s] [*] EXPANSION HATCHERY placed (Supply: {self.bot.supply_used}) [*]"
        )

    def _has_expansion_started(self) -> bool:
        townhalls = getattr(self.bot, "townhalls", None)
        if townhalls is not None and getattr(townhalls, "amount", 1) >= 2:
            return True

        already_pending = getattr(self.bot, "already_pending", None)
        if already_pending and already_pending(UnitTypeId.HATCHERY) > 0:
            return True

        return False

    async def _build_spawning_pool(self):
        """Spawning Pool 건설"""
        if self.bot.minerals < 200:
            return

        if not hasattr(self.bot, "structures") or not hasattr(self.bot, "can_place"):
            return

        # Check if already exists
        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL)
        if pools.exists or self.bot.already_pending(UnitTypeId.SPAWNINGPOOL) > 0:
            self.pool_placed = True
            return

        # * Pool 위치 선택 (본진 근처) *
        if self.bot.townhalls.exists:
            main_base = self.bot.townhalls.first
            position = await self.bot.find_placement(
                UnitTypeId.SPAWNINGPOOL,
                main_base.position.towards(self.bot.game_info.map_center, 5),
            )

            if position:
                workers = self.bot.units(UnitTypeId.DRONE)
                if workers:
                    self.bot.do(workers.first.build(UnitTypeId.SPAWNINGPOOL, position))
                    self.pool_placed = True

                    self.logger.info(
                        f"[{int(self.bot.time)}s] [*] SPAWNING POOL placed (Supply: {self.bot.supply_used}) [*]"
                    )

    async def _build_extractor(self):
        """Extractor 건설"""
        if self.bot.minerals < 25:
            return

        if not hasattr(self.bot, "vespene_geyser"):
            return

        if self._should_delay_extractor():
            return

        # Check if already exists
        extractors = self.bot.structures(UnitTypeId.EXTRACTOR)
        if extractors.exists or self.bot.already_pending(UnitTypeId.EXTRACTOR) > 0:
            self.gas_placed = True
            return

        # * Geyser 찾기 (본진) *
        if self.bot.townhalls.exists:
            main_base = self.bot.townhalls.first
            geysers = self.bot.vespene_geyser.closer_than(10, main_base)

            if geysers:
                workers = self.bot.units(UnitTypeId.DRONE)
                if workers:
                    self.bot.do(
                        workers.first.build(UnitTypeId.EXTRACTOR, geysers.first)
                    )
                    self.gas_placed = True

                    self.logger.info(
                        f"[{int(self.bot.time)}s] [*] EXTRACTOR placed (Supply: {self.bot.supply_used}) [*]"
                    )

    def _should_delay_extractor(self) -> bool:
        """Keep gas behind real expansion progress."""
        townhalls = getattr(self.bot, "townhalls", None)
        try:
            base_count = int(getattr(townhalls, "amount", 1) or 1)
        except (TypeError, ValueError):
            base_count = 1

        already_pending = getattr(self.bot, "already_pending", lambda _: 0)
        pending_hatch = int(already_pending(UnitTypeId.HATCHERY) or 0)
        pending_gas = int(already_pending(UnitTypeId.EXTRACTOR) or 0)

        extractors = self.bot.structures(UnitTypeId.EXTRACTOR)
        try:
            extractor_count = int(getattr(extractors, "amount", 0) or 0)
        except (TypeError, ValueError):
            extractor_count = 0

        if base_count < 2 and pending_hatch == 0:
            return True
        if base_count < 3 and extractor_count + pending_gas >= 1:
            return True
        return False

    def _can_build_queen(self) -> bool:
        """Queen을 생산할 수 있는지 확인"""
        if self._should_reserve_third_base():
            return False

        if not hasattr(self.bot, "structures"):
            return False

        # Spawning Pool이 완성되었는지 확인
        pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not pools:
            return False

        # 가스가 충분한지 확인
        if (
            self.bot.vespene < 100
        ):  # Actually Queen costs 0 gas, but this is for general use
            return False

        # Hatchery가 있는지 확인
        if not self.bot.townhalls.ready.idle:
            return False

        return True

    async def _build_queen(self):
        """Queen 생산"""
        if not self._can_build_queen():
            return

        hatcheries = self.bot.townhalls.ready.idle
        if not hatcheries:
            return

        # * Queen 생산 *
        self.bot.do(hatcheries.first.train(UnitTypeId.QUEEN))
        self.first_queen_made = True

        self.logger.info(
            f"[{int(self.bot.time)}s] [*] QUEEN trained (first 100 gas priority) [*]"
        )

    # ========================================
    # Supply Block Prevention
    # ========================================

    async def _prevent_supply_block(self):
        """인구수 막힘 방지"""
        # * Supply check *
        supply_left = self.bot.supply_cap - self.bot.supply_used
        if self._should_reserve_third_base() and supply_left > 0:
            return

        if supply_left <= self.overlord_buffer and self.bot.supply_cap < 200:
            # Need Overlord
            if self.bot.minerals >= 100:
                larvae = self.bot.units(UnitTypeId.LARVA).idle
                if larvae:
                    self.bot.do(larvae.first.train(UnitTypeId.OVERLORD))
                    self.logger.info(
                        f"[{int(self.bot.time)}s] * OVERLORD trained (Supply: {self.bot.supply_used}/{self.bot.supply_cap}) *"
                    )

    # ========================================
    # Gas Priority Management
    # ========================================

    def _manage_gas_priority(self):
        """
        가스 우선순위 관리

        1순위: Queen
        2순위: Metabolic Boost (Zergling 속업)
        3순위: 유닛 생산
        """
        # * Queen 우선순위 *
        if not self.first_queen_made:
            self.gas_reserved_for_queen = True
            return

        if self._should_reserve_third_base():
            return

        # * Metabolic Boost 우선순위 *
        if hasattr(self.bot, "structures"):
            pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready

            if pools and self.bot.vespene >= 100:
                # Metabolic Boost 연구 (아직 안 했으면)
                speed_upgrade = UpgradeId.ZERGLINGMOVEMENTSPEED
                if speed_upgrade in self.bot.state.upgrades:
                    self.metabolic_boost_requested = True
                    return
                if self.metabolic_boost_requested:
                    return
                pending_upgrade = getattr(self.bot, "already_pending_upgrade", None)
                if callable(pending_upgrade) and pending_upgrade(speed_upgrade) > 0:
                    self.metabolic_boost_requested = True
                    return
                if self.bot.minerals < 100:
                    return

                idle_pools = getattr(pools, "idle", None)
                pool = idle_pools.first if idle_pools else pools.first
                self.bot.do(pool.research(speed_upgrade))
                self.metabolic_boost_requested = True
                self.logger.info(
                    f"[{int(self.bot.time)}s] [*] METABOLIC BOOST started [*]"
                )

    # ========================================
    # Drone Saturation Management
    # ========================================

    async def _manage_drone_saturation(self):
        """
        Drone 포화도 관리

        - 미네랄: 기지당 16 드론
        - 가스: Extractor당 3 드론
        """
        if not hasattr(self.bot, "townhalls") or not hasattr(self.bot, "units"):
            return

        total_bases = self.bot.townhalls.ready.amount
        total_extractors = self.bot.structures(UnitTypeId.EXTRACTOR).ready.amount

        # * 목표 드론 수 계산 *
        target_mineral_drones = total_bases * self.MINERALS_PER_BASE
        target_gas_drones = total_extractors * self.GAS_PER_EXTRACTOR
        target_total_drones = target_mineral_drones + target_gas_drones

        # * 현재 드론 수 *
        current_drones = self.bot.units(UnitTypeId.DRONE).amount
        if self._should_reserve_third_base():
            return

        # * 드론 생산 필요 여부 *
        if current_drones < target_total_drones:
            # Larvae로 드론 생산
            larvae = self.bot.units(UnitTypeId.LARVA).idle
            if larvae and self.bot.minerals >= 50:
                drones_to_make = min(
                    larvae.amount, target_total_drones - current_drones
                )

                for i in range(drones_to_make):
                    if self.bot.minerals >= 50:
                        self.bot.do(larvae[i].train(UnitTypeId.DRONE))

    def _should_reserve_third_base(self) -> bool:
        """Pause non-essential larva spending until the third Hatchery starts."""
        game_time = getattr(self.bot, "time", 0.0)
        if game_time < 150:
            return False

        townhalls = getattr(self.bot, "townhalls", None)
        ready = getattr(townhalls, "ready", None) if townhalls else None
        base_count = 0
        for source in (ready, townhalls):
            if not source:
                continue
            amount = getattr(source, "amount", None)
            if isinstance(amount, (int, float)):
                base_count = int(amount)
                break
            if amount is not None:
                continue
            try:
                base_count = len(list(source))
                break
            except TypeError:
                pass

        already_pending = getattr(self.bot, "already_pending", lambda _: 0)
        try:
            pending_hatch = int(already_pending(UnitTypeId.HATCHERY) or 0)
        except (TypeError, ValueError):
            pending_hatch = 0

        if base_count >= 3:
            if game_time >= 360 and base_count < 4 and pending_hatch == 0:
                return not self._has_active_base_threat()
            return False
        if base_count < 2:
            return pending_hatch > 0 and not self._has_active_base_threat()
        if pending_hatch > 0:
            return False

        return not self._has_active_base_threat()

    def _has_active_base_threat(self) -> bool:
        enemy_units = getattr(self.bot, "enemy_units", None)
        townhalls = getattr(self.bot, "townhalls", None)
        if enemy_units is None or townhalls is None:
            return False

        try:
            bases = list(townhalls)
        except TypeError:
            first_base = getattr(townhalls, "first", None)
            bases = [first_base] if first_base else []

        for base in bases:
            if not base:
                continue
            try:
                nearby = enemy_units.closer_than(12, base)
            except Exception:
                continue

            amount = getattr(nearby, "amount", 0)
            if isinstance(amount, (int, float)) and amount > 0:
                return True
            try:
                if len(nearby) > 0:
                    return True
            except TypeError:
                pass

        return False

    # ========================================
    # Milestone Tracking
    # ========================================

    def _track_milestones(self):
        """빌드 마일스톤 추적"""
        game_time = self.bot.time

        # * Milestone 1: 1분 멀티 *
        if game_time >= 60 and "1min_multi" not in self.milestones_completed:
            if self.bot.townhalls.amount >= 2:
                self.milestones_completed.add("1min_multi")
                self.logger.info(f"[{int(game_time)}s] [*] MILESTONE: 1-Min Multi [*]")

        # * Milestone 2: Queen 생산 *
        if "first_queen" not in self.milestones_completed:
            queens = self.bot.units(UnitTypeId.QUEEN)
            if queens.amount >= 1:
                self.milestones_completed.add("first_queen")
                self.logger.info(f"[{int(game_time)}s] [*] MILESTONE: First Queen [*]")

        # * Milestone 3: Metabolic Boost *
        if "metabolic_boost" not in self.milestones_completed:
            if UpgradeId.ZERGLINGMOVEMENTSPEED in self.bot.state.upgrades:
                self.milestones_completed.add("metabolic_boost")
                self.logger.info(
                    f"[{int(game_time)}s] [*] MILESTONE: Metabolic Boost [*]"
                )

        # * Milestone 4: 16 Drones on minerals *
        if "16_mineral_drones" not in self.milestones_completed:
            # Simplified check
            if self.bot.units(UnitTypeId.DRONE).amount >= 16:
                self.milestones_completed.add("16_mineral_drones")
                self.logger.info(
                    f"[{int(game_time)}s] [*] MILESTONE: 16 Mineral Drones [*]"
                )

    def get_build_order_status(self) -> Dict:
        """빌드 오더 상태 반환"""
        return {
            "expansion_placed": self.expansion_placed,
            "pool_placed": self.pool_placed,
            "gas_placed": self.gas_placed,
            "first_queen_made": self.first_queen_made,
            "milestones_completed": list(self.milestones_completed),
            "current_supply": self.bot.supply_used,
            "supply_cap": self.bot.supply_cap,
            "drones": (
                self.bot.units(UnitTypeId.DRONE).amount
                if hasattr(self.bot, "units")
                else 0
            ),
        }
