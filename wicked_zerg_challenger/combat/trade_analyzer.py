"""
Trade Efficiency Analyzer - 전투 효율성 실시간 분석

전투에서의 리소스 교환을 분석하여 최적의 판단을 내립니다:
- 킬/데스 미네랄 가치 계산
- 불리한 교환 시 자동 후퇴 권고
- 전투 승률 예측
- 전투 통계 추적

Features:
- Real-time resource trade calculation
- Automatic retreat recommendation
- Battle outcome prediction
- Statistics tracking
"""

from collections import defaultdict
from typing import Dict

from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.unit import Unit
except ImportError:

    class BotAI:
        pass

    class _SC2StubSymbol:
        """Sentinel value used in place of real SC2 enum members.

        Hashable, comparable, and stringifies to the symbol name, but is
        explicitly not a ``str`` so callers can distinguish it from real
        upgrade-name strings used elsewhere in build orders."""

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
        _cache = {}

        def __getattr__(cls, name):
            key = (cls.__name__, name)
            sym = cls._cache.get(key)
            if sym is None:
                sym = _SC2StubSymbol(name)
                cls._cache[key] = sym
            return sym

    class UnitTypeId(metaclass=_SC2StubMeta):
        pass

    Unit = None


class TradeAnalyzer:
    """전투 효율성 분석기"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("TradeAnalyzer")

        # Unit costs (minerals + gas * 1.5)
        self.UNIT_COSTS = {
            "ZERGLING": 25,
            "BANELING": 75,
            "ROACH": 100,
            "RAVAGER": 175,
            "HYDRALISK": 125,
            "LURKER": 275,
            "MUTALISK": 175,
            "CORRUPTOR": 225,
            "ULTRALISK": 450,
            "BROODLORD": 400,
            "MARINE": 50,
            "ZEALOT": 150,
        }

        # Battle tracking
        self.friendly_losses: Dict[str, int] = defaultdict(int)
        self.enemy_losses: Dict[str, int] = defaultdict(int)
        self.last_unit_count: Dict[str, int] = {}
        self.last_enemy_count: Dict[str, int] = {}

        # Trade efficiency
        self.current_trade_ratio = 1.0  # resources lost / resources killed
        self.battle_active = False

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration % 22 == 0:  # ~1초마다
                self._update_unit_counts()
                self._calculate_trade_efficiency()

                # 불리한 교환 경고
                if self.current_trade_ratio > 2.0 and self.battle_active:
                    self.logger.warning(
                        f"[{int(self.bot.time)}s] * UNFAVORABLE TRADE! "
                        f"Ratio: {self.current_trade_ratio:.2f}:1 - Consider retreating *"
                    )

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[TRADE_ANALYZER] Error: {e}")

    def _update_unit_counts(self):
        """유닛 수 업데이트 및 손실 추적"""
        if not hasattr(self.bot, "units"):
            return

        current_counts = self._get_army_counts()

        # 손실 계산
        for unit_type, count in self.last_unit_count.items():
            if count > current_counts.get(unit_type, 0):
                losses = count - current_counts.get(unit_type, 0)
                self.friendly_losses[unit_type] += losses

        # Enemy losses (estimated)
        if hasattr(self.bot, "enemy_units"):
            enemy_counts = self._get_enemy_counts()

            for unit_type, count in self.last_enemy_count.items():
                if count > enemy_counts.get(unit_type, 0):
                    losses = count - enemy_counts.get(unit_type, 0)
                    self.enemy_losses[unit_type] += losses

            self.last_enemy_count = enemy_counts

        self.last_unit_count = current_counts

    def _get_army_counts(self) -> Dict[str, int]:
        """아군 병력 수 집계"""
        counts = {}
        for unit in self.bot.units:
            unit_type = str(unit.type_id).upper()
            counts[unit_type] = counts.get(unit_type, 0) + 1
        return counts

    def _get_enemy_counts(self) -> Dict[str, int]:
        """적 병력 수 집계"""
        counts = {}
        for unit in self.bot.enemy_units:
            unit_type = str(unit.type_id).upper()
            counts[unit_type] = counts.get(unit_type, 0) + 1
        return counts

    def _calculate_trade_efficiency(self):
        """교환 효율성 계산"""
        friendly_value_lost = sum(
            self.UNIT_COSTS.get(unit_type, 100) * count
            for unit_type, count in self.friendly_losses.items()
        )

        enemy_value_lost = sum(
            self.UNIT_COSTS.get(unit_type, 100) * count
            for unit_type, count in self.enemy_losses.items()
        )

        if enemy_value_lost > 0:
            self.current_trade_ratio = friendly_value_lost / enemy_value_lost
        else:
            self.current_trade_ratio = 1.0

    def get_trade_stats(self) -> Dict:
        """교환 통계 반환"""
        return {
            "trade_ratio": self.current_trade_ratio,
            "friendly_losses": dict(self.friendly_losses),
            "enemy_losses": dict(self.enemy_losses),
        }
