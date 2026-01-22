# -*- coding: utf-8 -*-
"""
Strategy Manager - Race-specific and Emergency Mode Controller

Features:
1. Race-specific unit composition adjustments
2. Rush/Cheese detection and Emergency Mode
3. Dynamic strategy switching
4. Rogue Tactics integration

프로게이머 참고:
- 대 테란: 뮤탈리스크 + 바퀴 + 맹독충
- 대 프로토스: 히드라리스크 + 바퀴 + 점막 확장
- 대 저그: 저글링 + 맹독충 + 뮤탈리스크
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class GamePhase(Enum):
    """게임 페이즈"""
    EARLY = "early"      # 0-4분
    MID = "mid"          # 4-10분
    LATE = "late"        # 10분+


class StrategyMode(Enum):
    """전략 모드"""
    NORMAL = "normal"
    EMERGENCY = "emergency"
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    ALL_IN = "all_in"


class EnemyRace(Enum):
    """상대 종족"""
    TERRAN = "Terran"
    PROTOSS = "Protoss"
    ZERG = "Zerg"
    RANDOM = "Random"
    UNKNOWN = "Unknown"


class StrategyManager:
    """
    종족별 전략 및 Emergency Mode 관리자

    Features:
    - 상대 종족에 따른 유닛 비율 조정
    - 러시/치즈 감지 및 긴급 대응
    - Rogue Tactics 연동
    """

    def __init__(self, bot):
        self.bot = bot

        # 전략 상태
        self.current_mode = StrategyMode.NORMAL
        self.detected_enemy_race = EnemyRace.UNKNOWN
        self.game_phase = GamePhase.EARLY

        # Emergency Mode 설정
        self.emergency_active = False
        self.emergency_start_time = 0.0
        self.emergency_duration = 120.0  # 2분 지속

        # 러시 감지 설정
        self.rush_detection_threshold = 150.0  # 2:30 이전 공격 = 러시
        self.cheese_detection_threshold = 120.0  # 2분 이전 공격 = 치즈

        # 종족별 유닛 비율 (ZERGLING, ROACH, HYDRA, MUTALISK, BANELING)
        self.race_unit_ratios = {
            EnemyRace.TERRAN: {
                GamePhase.EARLY: {"zergling": 0.3, "roach": 0.4, "baneling": 0.3},
                GamePhase.MID: {"zergling": 0.2, "roach": 0.3, "hydra": 0.2, "mutalisk": 0.3},
                GamePhase.LATE: {"zergling": 0.1, "roach": 0.2, "hydra": 0.3, "mutalisk": 0.4},
            },
            EnemyRace.PROTOSS: {
                GamePhase.EARLY: {"zergling": 0.4, "roach": 0.4, "baneling": 0.2},
                GamePhase.MID: {"zergling": 0.1, "roach": 0.3, "hydra": 0.5, "mutalisk": 0.1},
                GamePhase.LATE: {"zergling": 0.1, "roach": 0.2, "hydra": 0.5, "mutalisk": 0.2},
            },
            EnemyRace.ZERG: {
                GamePhase.EARLY: {"zergling": 0.5, "baneling": 0.5},
                GamePhase.MID: {"zergling": 0.3, "roach": 0.2, "baneling": 0.3, "mutalisk": 0.2},
                GamePhase.LATE: {"zergling": 0.2, "roach": 0.2, "hydra": 0.2, "mutalisk": 0.4},
            },
            EnemyRace.UNKNOWN: {
                GamePhase.EARLY: {"zergling": 0.5, "roach": 0.3, "baneling": 0.2},
                GamePhase.MID: {"zergling": 0.2, "roach": 0.3, "hydra": 0.3, "mutalisk": 0.2},
                GamePhase.LATE: {"zergling": 0.1, "roach": 0.2, "hydra": 0.3, "mutalisk": 0.4},
            },
        }

        # Emergency Mode 비율 (방어 우선)
        self.emergency_ratios = {
            "zergling": 0.6,
            "roach": 0.3,
            "queen": 0.1,  # 퀸 추가 생산
        }

        # Rogue Tactics 연동
        self.rogue_tactics_active = False
        self.larva_saving_mode = False

    def update(self) -> None:
        """매 스텝마다 호출하여 전략 업데이트"""
        self._detect_enemy_race()
        self._update_game_phase()
        self._check_rush_detection()
        self._check_rogue_tactics()
        self._update_strategy_mode()

    def _detect_enemy_race(self) -> None:
        """상대 종족 감지"""
        if self.detected_enemy_race != EnemyRace.UNKNOWN:
            return

        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race is None:
            return

        race_name = str(enemy_race)
        if "Terran" in race_name:
            self.detected_enemy_race = EnemyRace.TERRAN
        elif "Protoss" in race_name:
            self.detected_enemy_race = EnemyRace.PROTOSS
        elif "Zerg" in race_name:
            self.detected_enemy_race = EnemyRace.ZERG
        elif "Random" in race_name:
            self.detected_enemy_race = EnemyRace.RANDOM

    def _update_game_phase(self) -> None:
        """게임 페이즈 업데이트"""
        game_time = getattr(self.bot, "time", 0.0)

        if game_time < 240:  # 4분
            self.game_phase = GamePhase.EARLY
        elif game_time < 600:  # 10분
            self.game_phase = GamePhase.MID
        else:
            self.game_phase = GamePhase.LATE

    def _check_rush_detection(self) -> None:
        """러시/치즈 감지"""
        game_time = getattr(self.bot, "time", 0.0)

        # 이미 Emergency Mode면 스킵
        if self.emergency_active:
            # Emergency 종료 체크
            if game_time - self.emergency_start_time > self.emergency_duration:
                self._end_emergency_mode()
            return

        # 러시 감지 조건
        is_rush = self._detect_early_aggression(game_time)
        if is_rush:
            self._activate_emergency_mode(game_time)

    def _detect_early_aggression(self, game_time: float) -> bool:
        """초반 공격 감지"""
        # 게임 초반이 아니면 러시가 아님
        if game_time > self.rush_detection_threshold:
            return False

        # Intel Manager 활용
        intel = getattr(self.bot, "intel", None)
        if intel:
            if hasattr(intel, "is_under_attack") and intel.is_under_attack():
                return True
            if hasattr(intel, "detected_rush") and intel.detected_rush:
                return True

        # 직접 적 유닛 체크
        if hasattr(self.bot, "enemy_units") and self.bot.enemy_units:
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                main_base = self.bot.townhalls.first
                for enemy in self.bot.enemy_units:
                    # 적 전투 유닛이 기지 근처에 있으면 러시
                    if enemy.can_attack and enemy.distance_to(main_base) < 30:
                        return True

        return False

    def _activate_emergency_mode(self, game_time: float) -> None:
        """Emergency Mode 활성화"""
        self.emergency_active = True
        self.emergency_start_time = game_time
        self.current_mode = StrategyMode.EMERGENCY

        print(f"[STRATEGY] EMERGENCY MODE ACTIVATED at {int(game_time)}s - Rush detected!")

        # Economy Manager에 알림
        if hasattr(self.bot, "economy"):
            self.bot.economy._emergency_mode = True

    def _end_emergency_mode(self) -> None:
        """Emergency Mode 종료"""
        self.emergency_active = False
        self.current_mode = StrategyMode.NORMAL

        print("[STRATEGY] Emergency mode ended - Returning to normal operations")

        # Economy Manager 복구
        if hasattr(self.bot, "economy"):
            self.bot.economy._emergency_mode = False

    def _check_rogue_tactics(self) -> None:
        """Rogue Tactics 상태 확인"""
        rogue = getattr(self.bot, "rogue_tactics", None)
        if rogue:
            self.rogue_tactics_active = True
            self.larva_saving_mode = getattr(rogue, "larva_saving_active", False)
        else:
            self.rogue_tactics_active = False
            self.larva_saving_mode = False

    def _update_strategy_mode(self) -> None:
        """전략 모드 업데이트"""
        if self.emergency_active:
            return  # Emergency 유지

        # 군대 우위 계산
        our_army = 0
        enemy_army = 0

        if hasattr(self.bot, "units"):
            for unit in self.bot.units:
                if unit.can_attack and unit.type_id.name != "DRONE":
                    our_army += 1

        if hasattr(self.bot, "enemy_units"):
            for unit in self.bot.enemy_units:
                if unit.can_attack:
                    enemy_army += 1

        # 전략 결정
        if our_army > enemy_army * 1.5:
            self.current_mode = StrategyMode.AGGRESSIVE
        elif our_army < enemy_army * 0.5 and enemy_army > 5:
            self.current_mode = StrategyMode.DEFENSIVE
        else:
            self.current_mode = StrategyMode.NORMAL

    def get_unit_ratios(self) -> Dict[str, float]:
        """
        현재 상황에 맞는 유닛 비율 반환

        Returns:
            유닛 종류별 비율 딕셔너리
        """
        if self.emergency_active:
            return self.emergency_ratios

        race = self.detected_enemy_race
        if race == EnemyRace.RANDOM or race == EnemyRace.UNKNOWN:
            race = EnemyRace.UNKNOWN

        phase_ratios = self.race_unit_ratios.get(race, self.race_unit_ratios[EnemyRace.UNKNOWN])
        return phase_ratios.get(self.game_phase, phase_ratios[GamePhase.EARLY])

    def should_produce_drone(self) -> bool:
        """
        드론 생산 여부 결정

        Returns:
            드론을 생산해야 하면 True
        """
        # Emergency Mode에서는 드론 생산 최소화
        if self.emergency_active:
            drone_count = 0
            if hasattr(self.bot, "units"):
                drones = self.bot.units.filter(lambda u: u.type_id.name == "DRONE")
                drone_count = drones.amount if hasattr(drones, "amount") else len(drones)
            return drone_count < 12  # 최소 12기만 유지

        return True

    def should_save_larva(self) -> bool:
        """
        Rogue Tactics의 라바 세이빙 모드 확인

        Returns:
            라바를 아껴야 하면 True
        """
        return self.larva_saving_mode

    def get_priority_unit(self) -> Optional[str]:
        """
        현재 우선 생산해야 할 유닛 반환

        Returns:
            우선 유닛 이름 또는 None
        """
        if self.emergency_active:
            return "zergling"  # 긴급 시 저글링 우선

        ratios = self.get_unit_ratios()
        if ratios:
            # 가장 비율이 높은 유닛 반환
            return max(ratios.keys(), key=lambda k: ratios[k])
        return None

    def get_status_report(self) -> Dict[str, Any]:
        """
        전략 상태 리포트 반환

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "mode": self.current_mode.value,
            "enemy_race": self.detected_enemy_race.value,
            "game_phase": self.game_phase.value,
            "emergency_active": self.emergency_active,
            "rogue_tactics_active": self.rogue_tactics_active,
            "larva_saving": self.larva_saving_mode,
            "unit_ratios": self.get_unit_ratios(),
        }
