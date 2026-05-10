"""
Multi-Prong Attack Coordinator - 다방향 동시 공격 시스템

적의 병력을 분산시키고 멀티태스킹을 강요합니다:
- Main Army: 정면 압박
- Mutalisk: 미네랄 라인 견제
- Zergling: 확장 타격
- Nydus/Drop: 후방 교란

Features:
- 3방향 이상 동시 공격
- 타겟 우선순위 자동 할당
- 공격 타이밍 동기화
- 실시간 위협 레벨 평가
"""

from typing import Dict, Optional, Set

from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.units import Units
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

    Point2 = tuple
    Units = list


class MultiProngCoordinator:
    """다방향 동시 공격 조율"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("MultiProng")

        # Attack prongs
        self.prong_assignments: Dict[str, Set[int]] = {
            "main_army": set(),
            "mutalisk_harass": set(),
            "zergling_runby": set(),
            "drop_squad": set(),
        }

        # Target assignments
        self.prong_targets: Dict[str, Optional[Point2]] = {
            "main_army": None,
            "mutalisk_harass": None,
            "zergling_runby": None,
            "drop_squad": None,
        }

        # Attack state
        self.attack_active = False
        self.attack_start_time = 0

        # * Performance Optimization: 캐싱 변수 *
        self._cached_army_count = 0
        self._cached_muta_count = 0
        self._last_count_update = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration % 44 == 0:
                # Check if we should initiate multi-prong
                if self._should_initiate_attack():
                    await self._plan_multi_prong_attack()

                # Execute multi-prong
                if self.attack_active:
                    await self._execute_multi_prong()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[MULTI_PRONG] Error: {e}")

    def _should_initiate_attack(self) -> bool:
        """
        다방향 공격을 시작할지 결정

        성능 최적화:
        - 병력 수 계산을 2초마다만 수행 (캐시 활용)
        """
        if not hasattr(self.bot, "units"):
            return False

        # * Harassment가 활성화되어 있으면 Multi-Prong 중단 (충돌 방지) *
        if hasattr(self.bot, "harassment_coord") and self.bot.harassment_coord:
            # Harassment가 Zergling을 사용 중인지 확인
            if hasattr(self.bot.harassment_coord, "zergling_runby_active"):
                if self.bot.harassment_coord.zergling_runby_active:
                    return False  # Harassment 우선

        # * 캐싱: 2초마다만 병력 수 재계산 *
        current_time = self.bot.time
        if current_time - self._last_count_update >= 2.0:
            self._cached_army_count = (
                self.bot.units(UnitTypeId.ZERGLING).amount
                + self.bot.units(UnitTypeId.ROACH).amount * 2
            )
            self._cached_muta_count = self.bot.units(UnitTypeId.MUTALISK).amount
            self._last_count_update = current_time

        # 최소 요구사항: 20 army supply + 4 mutalisk
        return self._cached_army_count >= 20 and self._cached_muta_count >= 4

    async def _plan_multi_prong_attack(self):
        """다방향 공격 계획"""
        self.logger.info(
            f"[{int(self.bot.time)}s] [*] MULTI-PRONG ATTACK INITIATED [*]"
        )

        # Assign units to prongs
        self._assign_units_to_prongs()

        # Assign targets to prongs
        self._assign_targets_to_prongs()

        self.attack_active = True
        self.attack_start_time = self.bot.time

    def _assign_units_to_prongs(self):
        """유닛을 각 공격조에 할당"""
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        mutalisks = self.bot.units(UnitTypeId.MUTALISK)
        roaches = self.bot.units(UnitTypeId.ROACH)

        # Main Army: 70% of ground units
        main_army_size = int(len(zerglings) * 0.7)
        for ling in zerglings[:main_army_size]:
            self.prong_assignments["main_army"].add(ling.tag)

        for roach in roaches:
            self.prong_assignments["main_army"].add(roach.tag)

        # Zergling Runby: 30% of zerglings
        for ling in zerglings[main_army_size:]:
            self.prong_assignments["zergling_runby"].add(ling.tag)

        # Mutalisk Harass: All mutalisks
        for muta in mutalisks:
            self.prong_assignments["mutalisk_harass"].add(muta.tag)

    def _assign_targets_to_prongs(self):
        """각 공격조에 타겟 할당"""
        if not hasattr(self.bot, "enemy_structures"):
            return

        enemy_bases = list(
            self.bot.enemy_structures.filter(
                lambda s: s.type_id
                in {UnitTypeId.HATCHERY, UnitTypeId.COMMANDCENTER, UnitTypeId.NEXUS}
            )
        )

        if not enemy_bases:
            return

        # Main Army: Enemy main base
        self.prong_targets["main_army"] = enemy_bases[0].position

        # Mutalisk: Enemy mineral line
        self.prong_targets["mutalisk_harass"] = enemy_bases[0].position

        # Zergling: Enemy natural expansion
        if len(enemy_bases) > 1:
            self.prong_targets["zergling_runby"] = enemy_bases[1].position

    async def _execute_multi_prong(self):
        """다방향 공격 실행"""
        # Execute each prong
        for prong_name, unit_tags in self.prong_assignments.items():
            target = self.prong_targets.get(prong_name)
            if not target:
                continue

            for tag in unit_tags:
                unit = self.bot.units.find_by_tag(tag)
                if unit and target:  # target이 유효한지도 체크
                    self.bot.do(unit.attack(target))
