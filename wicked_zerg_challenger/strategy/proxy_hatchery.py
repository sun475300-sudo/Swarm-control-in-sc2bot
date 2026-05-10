"""
Proxy Hatchery Tactics - 프록시 해처리 전술

적진 근처에 공격용 해처리를 건설:
- Hidden expansions
- Forward production base
- Nydus network hub
- Spine crawler rush base

Features:
- 은폐된 위치 선택
- 적 정찰 회피
- Spine crawler 방어
- 공격적 유닛 생산
"""

from typing import Optional

from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
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

    Point2 = tuple


class ProxyHatchery:
    """프록시 해처리 전술"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("ProxyHatch")

        # Proxy state
        self.proxy_attempted = False
        self.proxy_location: Optional[Point2] = None
        self.proxy_hatchery_tag: Optional[int] = None

        # Timing
        self.PROXY_TIMING = 180  # 3분

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # Proxy timing (3분)
            if game_time >= self.PROXY_TIMING and not self.proxy_attempted:
                await self._attempt_proxy_hatchery()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[PROXY_HATCH] Error: {e}")

    async def _attempt_proxy_hatchery(self):
        """프록시 해처리 시도"""
        if not hasattr(self.bot, "enemy_start_locations"):
            return

        if self._ready_base_count() < 4:
            return

        if self._pending_hatchery_count() > 0:
            return

        if self.bot.minerals < 300:
            return

        # 적진 근처 은폐 위치 찾기
        enemy_start = self.bot.enemy_start_locations[0]
        proxy_location = enemy_start.towards(self.bot.game_info.map_center, 15)

        # 드론 파견
        drones = self.bot.units(UnitTypeId.DRONE)
        if self._units_amount(drones) > 0:
            drone = drones.first
            self.bot.do(drone.build(UnitTypeId.HATCHERY, proxy_location))

            self.proxy_attempted = True
            self.proxy_location = proxy_location

            self.logger.info(
                f"[{int(self.bot.time)}s] *** PROXY HATCHERY ATTEMPTED! Location: {proxy_location} ***"
            )

    def _ready_base_count(self) -> int:
        townhalls = getattr(self.bot, "townhalls", None)
        if not townhalls:
            return 0

        ready = getattr(townhalls, "ready", None)
        for source in (ready, townhalls):
            amount = getattr(source, "amount", None)
            if isinstance(amount, (int, float)):
                return int(amount)
            try:
                return len(list(source))
            except TypeError:
                continue
        return 0

    def _pending_hatchery_count(self) -> int:
        already_pending = getattr(self.bot, "already_pending", None)
        if not callable(already_pending):
            return 0
        try:
            return int(already_pending(UnitTypeId.HATCHERY) or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _units_amount(units) -> int:
        amount = getattr(units, "amount", None)
        if isinstance(amount, (int, float)):
            return int(amount)
        try:
            return len(list(units))
        except TypeError:
            return 0
