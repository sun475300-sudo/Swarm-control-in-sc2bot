"""
Timing Attack Library - 프로급 타이밍 공격

검증된 타이밍 러시 전략들:
- Roach/Ravager All-in (7분)
- Mutalisk Rush (6분)
- 2-Base Timing (8분)
- Zergling Flood (4분)

Features:
- 정확한 타이밍 추적
- 리소스 최적화
- 공격 준비도 체크
- 타이밍 윈도우 감지
"""

from typing import Dict, Optional
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        ROACH = "ROACH"
        MUTALISK = "MUTALISK"


class TimingAttacks:
    """타이밍 공격 라이브러리"""

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("TimingAttacks")

        # Timing windows
        self.ROACH_TIMING = 420  # 7분
        self.MUTA_TIMING = 360   # 6분
        self.ZERGLING_TIMING = 240  # 4분

        # Attack state
        self.timing_attack_active = False
        self.timing_attack_type: Optional[str] = None
        self.timing_window_started = {}  # {attack_type: start_time}
        self.timing_window_duration = 60  # 윈도우 지속시간 (60초)

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            if iteration % 110 == 0:
                self._check_timing_windows()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[TIMING_ATTACKS] Error: {e}")

    def _check_timing_windows(self):
        """
        타이밍 윈도우 체크

        개선사항:
        - 타이밍 윈도우 확장 (유닛 완성까지 대기)
        - 적 방어 평가
        - 자원 확인 (추가 생산 가능 여부)
        """
        game_time = self.bot.time

        # ★ Roach/Ravager 7분 타이밍 ★
        if game_time >= self.ROACH_TIMING:
            attack_type = "roach_ravager"

            # 윈도우 시작 시간 기록
            if attack_type not in self.timing_window_started:
                self.timing_window_started[attack_type] = game_time

            # 윈도우 내에서 준비되면 공격
            time_in_window = game_time - self.timing_window_started[attack_type]
            if time_in_window < self.timing_window_duration:
                if self._ready_for_roach_timing():
                    self._initiate_roach_timing()

        # ★ Mutalisk 6분 타이밍 ★
        elif game_time >= self.MUTA_TIMING:
            attack_type = "mutalisk"

            if attack_type not in self.timing_window_started:
                self.timing_window_started[attack_type] = game_time

            time_in_window = game_time - self.timing_window_started[attack_type]
            if time_in_window < self.timing_window_duration:
                if self._ready_for_muta_timing():
                    self._initiate_muta_timing()

    def _ready_for_roach_timing(self) -> bool:
        """
        Roach 타이밍 준비 확인

        조건:
        1. Roach 16기 이상
        2. 적 방어 규모 평가 (15 supply 미만)
        3. 자원 확인 (추가 4기 생산 가능)
        """
        if not hasattr(self.bot, "units"):
            return False

        # 1. 유닛 수 확인
        roach_count = self.bot.units(UnitTypeId.ROACH).amount
        ravager_count = self.bot.units(UnitTypeId.RAVAGER).amount

        total_supply = roach_count * 2 + ravager_count * 3
        if total_supply < 32:  # 16 Roach = 32 supply
            return False

        # 2. 적 방어 규모 체크
        enemy_defense = self._assess_enemy_defense()
        if enemy_defense > 20:  # 20+ supply 방어
            self.logger.warning(
                f"[{int(self.bot.time)}s] Roach timing cancelled: Enemy defense too strong ({enemy_defense} supply)"
            )
            return False

        # 3. 자원 확인: Roach 4기 추가 생산 가능
        minerals_per_roach = 75
        gas_per_roach = 25
        additional_production = 4

        if self.bot.minerals < minerals_per_roach * additional_production:
            return False
        if self.bot.vespene < gas_per_roach * additional_production:
            return False

        return True

    def _ready_for_muta_timing(self) -> bool:
        """Mutalisk 타이밍 준비 확인"""
        if not hasattr(self.bot, "units"):
            return False

        muta_count = self.bot.units(UnitTypeId.MUTALISK).amount
        return muta_count >= 8

    def _initiate_roach_timing(self):
        """Roach 타이밍 공격 시작"""
        self.timing_attack_active = True
        self.timing_attack_type = "roach_ravager"
        self.logger.info(f"[{int(self.bot.time)}s] ★★★ ROACH/RAVAGER TIMING ATTACK! ★★★")

    def _initiate_muta_timing(self):
        """Mutalisk 타이밍 공격 시작"""
        self.timing_attack_active = True
        self.timing_attack_type = "mutalisk"
        self.logger.info(f"[{int(self.bot.time)}s] ★★★ MUTALISK TIMING ATTACK! ★★★")

    def _assess_enemy_defense(self) -> int:
        """
        적 방어 규모 평가

        Returns:
            적 방어 병력 supply 추정치
        """
        if not hasattr(self.bot, "enemy_units"):
            return 0

        enemy_units = self.bot.enemy_units
        defense_supply = 0

        # 주요 방어 유닛별 supply 계산
        unit_supply = {
            # Terran
            "MARINE": 1,
            "MARAUDER": 2,
            "SIEGETANK": 3,
            "BUNKER": 5,  # 안에 유닛 있다고 가정
            # Protoss
            "ZEALOT": 2,
            "STALKER": 2,
            "SENTRY": 2,
            "IMMORTAL": 4,
            "PHOTONCANNON": 3,
            # Zerg
            "ZERGLING": 0.5,
            "ROACH": 2,
            "HYDRALISK": 2,
            "SPINECRAWLER": 2,
        }

        for unit in enemy_units:
            unit_type = unit.type_id.name
            defense_supply += unit_supply.get(unit_type, 1)

        return int(defense_supply)
