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
import json
from pathlib import Path
from utils.logger import get_logger
from config.config_loader import ConfigLoader
from racial_counter_manager import RacialCounterManager

try:
    from knowledge_manager import KnowledgeManager
except ImportError:
    class KnowledgeManager:
        """Fallback stub when knowledge_manager module is unavailable."""
        def __init__(self):
            self.knowledge = {}
        def get(self, key, default=None):
            return default

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
    종족별 전략 및 Emergency Mode 관리자 (Data-Driven)
    
    Features:
    - 상대 종족에 따른 유닛 비율 조정 (Json Load)
    - 러시/치즈 감지 및 긴급 대응
    - Rogue Tactics 연동
    """

    def __init__(self, bot, blackboard=None): # Added blackboard
        self.bot = bot
        self.blackboard = blackboard # Store blackboard
        self.logger = get_logger("StrategyManager")
        self.knowledge_manager = KnowledgeManager() # Initialize

        # 전략 상태
        self.current_mode = StrategyMode.NORMAL
        self.detected_enemy_race = EnemyRace.UNKNOWN
        self.game_phase = GamePhase.EARLY

        # Emergency Mode 설정 (config-driven)
        rush_cfg = ConfigLoader.get_rush_detection_config()
        self.emergency_active = False
        self.emergency_start_time = 0.0
        self.emergency_duration = rush_cfg.get("emergency_duration_seconds", 120.0)

        # 러시 감지 설정 (config-driven)
        self.rush_detection_threshold = rush_cfg.get("rush_threshold_seconds", 150.0)
        self.cheese_detection_threshold = rush_cfg.get("cheese_threshold_seconds", 120.0)

        # 로그 스팸 방지
        self.last_air_threat_log = 0
        self.last_major_attack_log = 0
        self.last_high_templar_log = 0
        self.last_disruptor_log = 0
        self.log_cooldown = 5.0

        # 4분 이전 견제 시스템
        self.early_harassment_active = False
        self.last_harassment_time = 0
        self.harassment_interval = 15.0  # ★ 30s → 15s: more aggressive harassment

        # ★ Load Unit Ratios from KnowledgeManager ★
        self.race_unit_ratios = {
            EnemyRace.TERRAN: self._load_ratios("Terran"),
            EnemyRace.PROTOSS: self._load_ratios("Protoss"),
            EnemyRace.ZERG: self._load_ratios("Zerg"),
            EnemyRace.UNKNOWN: self._load_ratios("Terran"), # Default to Terran ratios
        }
        
        self.logger.info(f"[STRATEGY] Loaded unit ratios for {len(self.race_unit_ratios)} races from Knowledge Base")

        # Emergency Mode 비율 (config-driven)
        emergency_cfg = ConfigLoader.get_emergency_config()
        self.emergency_ratios = emergency_cfg.get("default_ratios", {
            "zergling": 0.5,
            "roach": 0.25,
            "baneling": 0.15,
            "queen": 0.1,
        })
        self.emergency_air_ratios = emergency_cfg.get("air_threat_ratios", {
            "zergling": 0.30,
            "hydralisk": 0.40,
            "roach": 0.20,
            "queen": 0.10,
        })

        # Racial Counter Manager (extracted from this class)
        self.counter_manager = RacialCounterManager(bot, blackboard, self.logger)

        # 방어 건물 긴급 건설 플래그
        self.emergency_spine_requested = False
        self.emergency_spore_requested = False

        # Defense mode tracking (auto-exit after no attack for 120s)
        self.defense_mode_start_time = 0.0
        self.last_major_attack_time = 0.0
        self.defense_mode_timeout = 120.0  # seconds with no attack before exiting

        # Rogue Tactics 연동
        self.rogue_tactics_active = False
        self.larva_saving_mode = False
        
        # Rush Persistence Counter
        self.rush_persistence_count = 0

        # 학습된 데이터 저장소
        self.learned_priorities = {}
        self.learned_expansion_timings = {}
        self.learned_army_ratios = {}

        # ★ Feature 83: Extended JARVIS command fields ★
        self.target_priority: str = "military"  # "economy" | "military" | "tech"
        self.expansion_timing: str = "normal"   # "fast" | "normal" | "slow"
        self.preferred_comp: str = "balanced"    # "zergling_heavy" | "roach_heavy" | "muta_heavy" | "balanced"

        # ★ Feature 89: Custom unit weights from JARVIS ★
        self.custom_unit_weights: Optional[Dict[str, float]] = None
        self.early_scout_pressure_active = False
        self.early_scout_greed_suppressed = False
        self.early_scout_fast_gas = False
        self.early_scout_cheese_active = False

    def _load_ratios(self, race_name: str) -> Dict[GamePhase, Dict[str, float]]:
        """KnowledgeManager에서 유닛 비율 로드"""
        ratios = {}
        race_data = self.knowledge_manager.knowledge.get("unit_ratios", {}).get(race_name, {})
        
        # Convert string keys to GamePhase enum
        for phase_str, unit_data in race_data.items():
            try:
                normalized_data = {k.lower(): v for k, v in unit_data.items()}

                if phase_str == "early":
                    ratios[GamePhase.EARLY] = normalized_data
                elif phase_str == "mid":
                    ratios[GamePhase.MID] = normalized_data
                elif phase_str == "late":
                    ratios[GamePhase.LATE] = normalized_data
            except Exception as e:
                self.logger.warning(f"Failed to load ratios for {race_name}/{phase_str}: {e}")
        
        # Fill missing phases with defaults if empty (Safe Fallback)
        if not ratios:
            self.logger.warning(f"No ratios found for {race_name}, using fallback.")
            return {
                GamePhase.EARLY: {"zergling": 0.6, "queen": 0.2, "roach": 0.2},
                GamePhase.MID: {"roach": 0.25, "hydralisk": 0.2, "zergling": 0.2,
                                "ravager": 0.1, "baneling": 0.1, "queen": 0.1, "lurker": 0.05},
                GamePhase.LATE: {"ultralisk": 0.20, "hydralisk": 0.20, "corruptor": 0.15,
                                 "broodlord": 0.10, "viper": 0.10, "zergling": 0.10,
                                 "lurker": 0.10, "ravager": 0.05},
            }
            
        return ratios

    def update(self) -> None:
        """매 스텝마다 호출하여 전략 업데이트"""
        # ★ 적 유닛 정보 1회 캐시 (매 프레임 반복 조회 방지) ★
        self._cached_enemy_composition = self._cache_enemy_composition()

        self._check_jarvis_commands()
        self._detect_enemy_race()
        self._update_game_phase()
        self._check_rush_detection()
        self._check_defense_mode_timeout()
        self._check_early_harassment()
        self._check_rogue_tactics()
        self._apply_early_scout_signals()
        self._update_strategy_mode()
        self._update_counter_build()
        self._detect_direct_air_threat()
        # Delegated to RacialCounterManager
        self._apply_racial_counters()

        # ★ Write State to Blackboard ★
        if self.blackboard:
            self.blackboard.set("strategy_mode", self.current_mode.name)
            self.blackboard.set("game_phase", self.game_phase.name)
            self.blackboard.set("enemy_race", self.detected_enemy_race.name)
            self.blackboard.set(
                "is_rush_detected",
                self.emergency_active or self.early_scout_pressure_active,
            )

    def _cache_enemy_composition(self) -> Dict[str, int]:
        """적 유닛 구성을 1회 캐시 (매 프레임 반복 조회 방지)"""
        composition: Dict[str, int] = {}
        if not hasattr(self.bot, "enemy_units"):
            return composition
        for enemy in self.bot.enemy_units:
            try:
                etype = getattr(enemy.type_id, "name", "").upper()
                if etype:
                    composition[etype] = composition.get(etype, 0) + 1
            except (AttributeError, TypeError):
                continue
        return composition

    def _get_early_scout_signal_state(self) -> Dict[str, Any]:
        if self.early_scout_pressure_active:
            self.current_mode = StrategyMode.DEFENSIVE
            return {
                "fresh": False,
                "gas_time": None,
                "natural_confirmed": False,
                "cheese_suspected": False,
                "cheese_active": False,
                "fast_gas": False,
                "greed_suppressed": False,
                "pressure_active": True,
                "drone_floor": 16,
            }

        game_time = getattr(self.bot, "time", 0.0)
        state: Dict[str, Any] = {
            "fresh": False,
            "gas_time": None,
            "natural_confirmed": False,
            "cheese_suspected": False,
            "cheese_active": False,
            "fast_gas": False,
            "greed_suppressed": False,
            "pressure_active": False,
            "drone_floor": 20,
        }
        if not self.blackboard:
            return state

        last_report = self.blackboard.get("early_scout_last_report_time", 0.0) or 0.0
        try:
            last_report = float(last_report)
        except (TypeError, ValueError):
            last_report = 0.0

        gas_time = self.blackboard.get("early_scout_gas_time", None)
        try:
            gas_time = float(gas_time) if gas_time is not None else None
        except (TypeError, ValueError):
            gas_time = None

        natural_confirmed = bool(
            self.blackboard.get("early_scout_natural_confirmed", False)
        )
        cheese_suspected = bool(
            self.blackboard.get("early_scout_cheese_suspected", False)
        )
        fresh = last_report > 0 and (game_time - last_report) <= 75.0
        early_window = game_time <= 240.0
        cheese_active = fresh and cheese_suspected
        fast_gas = fresh and gas_time is not None and gas_time < 90.0
        greed_suppressed = fresh and early_window and not natural_confirmed

        state.update(
            {
                "fresh": fresh,
                "gas_time": gas_time,
                "natural_confirmed": natural_confirmed,
                "cheese_suspected": cheese_suspected,
                "cheese_active": cheese_active,
                "fast_gas": fast_gas,
                "greed_suppressed": greed_suppressed,
                "pressure_active": cheese_active or greed_suppressed or fast_gas,
                "drone_floor": 16 if cheese_active else 20,
            }
        )
        return state

    def _apply_early_scout_signals(self) -> None:
        state = self._get_early_scout_signal_state()
        self.early_scout_pressure_active = bool(state["pressure_active"])
        self.early_scout_greed_suppressed = bool(state["greed_suppressed"])
        self.early_scout_fast_gas = bool(state["fast_gas"])
        self.early_scout_cheese_active = bool(state["cheese_active"])

        if not self.early_scout_pressure_active:
            return

        game_time = getattr(self.bot, "time", 0.0)
        if self.current_mode != StrategyMode.DEFENSIVE:
            self.defense_mode_start_time = game_time
        self.current_mode = StrategyMode.DEFENSIVE
        self._request_defensive_building(spine=True)

        self._adjust_unit_ratio("queen", 0.20)
        self._adjust_unit_ratio("zergling", 0.35)
        self._adjust_unit_ratio("roach", 0.15)

        if self.blackboard and self.early_scout_cheese_active:
            self.blackboard.set("is_rush_detected", True)

        if self.early_scout_fast_gas:
            self._request_defensive_building(spore=True)

    def _check_jarvis_commands(self) -> None:
        """자비스로부터 받은 외부 명령어 체크 (aggression_level, target_priority, etc.)"""
        if self.bot.iteration % 22 != 0: # 1초마다만 체크
            return

        cmd_path = Path("jarvis_command.json")
        if cmd_path.exists():
            try:
                with open(cmd_path, "r", encoding="utf-8") as f:
                    cmd_data = json.load(f)

                    # --- Aggression Level (existing) ---
                    level = cmd_data.get("aggression_level")
                    if level:
                        if level == "passive":
                            self.current_mode = StrategyMode.DEFENSIVE
                        elif level == "balanced":
                            self.current_mode = StrategyMode.NORMAL
                        elif level == "aggressive":
                            self.current_mode = StrategyMode.AGGRESSIVE
                        elif level == "all_in":
                            self.current_mode = StrategyMode.ALL_IN
                        self.logger.info(f"[JARVIS] Aggression level updated to: {level}")

                    # ★ Feature 83: target_priority ★
                    tp = cmd_data.get("target_priority")
                    if tp and tp in ("economy", "military", "tech"):
                        self.target_priority = tp
                        self.logger.info(f"[JARVIS] Target priority set to: {tp}")

                    # ★ Feature 83: expansion_timing ★
                    et = cmd_data.get("expansion_timing")
                    if et and et in ("fast", "normal", "slow"):
                        self.expansion_timing = et
                        self.logger.info(f"[JARVIS] Expansion timing set to: {et}")

                    # ★ Feature 83: unit_composition ★
                    uc = cmd_data.get("unit_composition")
                    if uc and uc in ("zergling_heavy", "roach_heavy", "muta_heavy", "balanced"):
                        self.preferred_comp = uc
                        self.logger.info(f"[JARVIS] Preferred composition set to: {uc}")

                    # ★ Feature 89: unit_weights ★
                    uw = cmd_data.get("unit_weights")
                    if uw and isinstance(uw, dict):
                        # Validate all values are numeric
                        valid = all(isinstance(v, (int, float)) for v in uw.values())
                        if valid:
                            self.custom_unit_weights = {k.lower(): float(v) for k, v in uw.items()}
                            self.logger.info(f"[JARVIS] Custom unit weights set: {self.custom_unit_weights}")
                        else:
                            self.logger.warning("[JARVIS] Invalid unit_weights (values must be numeric)")

                cmd_path.unlink(missing_ok=True)
            except Exception as e:
                self.logger.warning(f"Failed to read jarvis command: {e}")



    def get_learned_economy_weight(self) -> float:
        """
        학습된 경제 우선순위 반환 (0.0 ~ 1.0)

        Returns:
            Drone 우선순위 (높을수록 economy 중시)
        """
        return self.learned_priorities.get("Drone", 0.0)

    def get_learned_supply_weight(self) -> float:
        """
        학습된 보급 우선순위 반환 (0.0 ~ 1.0)

        Returns:
            Overlord 우선순위 (높을수록 supply 여유 중시)
        """
        return self.learned_priorities.get("Overlord", 0.0)

    def get_learned_queen_weight(self) -> float:
        """
        학습된 퀸 우선순위 반환 (0.0 ~ 1.0)

        Returns:
            Queen 우선순위 (높을수록 macro/defense 중시)
        """
        return self.learned_priorities.get("Queen", 0.0)

    def get_learned_expansion_timing(self, base_number: str) -> float:
        """
        학습된 확장 타이밍 반환

        Args:
            base_number: "second_base", "third_base", "fourth_base"

        Returns:
            확장 타이밍 (초 단위), 없으면 0.0
        """
        return self.learned_expansion_timings.get(base_number, 0.0)

    def _detect_enemy_race(self) -> None:
        """상대 종족 감지"""
        # Re-check if still UNKNOWN or RANDOM (actual race may have been revealed)
        if self.detected_enemy_race not in (EnemyRace.UNKNOWN, EnemyRace.RANDOM):
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
            # Only set RANDOM if not already RANDOM (avoid redundant logging)
            if self.detected_enemy_race != EnemyRace.RANDOM:
                self.detected_enemy_race = EnemyRace.RANDOM

    def _update_game_phase(self) -> None:
        """
        게임 페이즈 업데이트 (forward-only with hysteresis)

        Phase transitions only move forward: EARLY -> MID -> LATE.
        This prevents flicker at time boundaries (e.g., lag spikes causing
        game_time to appear to jump back briefly).
        """
        game_time = getattr(self.bot, "time", 0.0)

        if self.game_phase == GamePhase.EARLY and game_time >= 240:
            self.game_phase = GamePhase.MID
            self.logger.info(f"[{int(game_time)}s] Game phase: EARLY -> MID")
        elif self.game_phase == GamePhase.MID and game_time >= 600:
            self.game_phase = GamePhase.LATE
            self.logger.info(f"[{int(game_time)}s] Game phase: MID -> LATE")

    def _check_rush_detection(self) -> None:
        """러시/치즈 감지 (초반 + 중후반)"""
        game_time = getattr(self.bot, "time", 0.0)

        # 이미 Emergency Mode면 스킵
        if self.emergency_active:
            # Emergency 종료 체크
            if game_time - self.emergency_start_time > self.emergency_duration:
                self._end_emergency_mode()
            return

        # 초반 러시 감지 (3분 이전)
        if game_time < self.rush_detection_threshold:
            is_rush = self._detect_early_aggression(game_time)
            if is_rush:
                self._activate_emergency_mode(game_time)
                return

        # 중후반 대규모 공격 감지 (4분 이후)
        if game_time >= 240:
            is_major_attack = self._detect_major_attack(game_time)
            if is_major_attack:
                self._activate_defense_mode(game_time)

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
                # ★ CRITICAL: 비상 모드 조건 완화 (30 → 15) - 확장 차단 방지 ★
                nearby_enemies = [e for e in self.bot.enemy_units
                                 if e.can_attack and e.distance_to(main_base) < 15]
                # 적 3마리 이상일 때만 러시로 판정 (정찰 유닛 무시)
                if len(nearby_enemies) >= 3:
                    self.rush_persistence_count += 1
                    # 3회 연속 감지 시 True 반환 (약 3프레임/스텝) - Glitch 방지
                    if self.rush_persistence_count >= 3:
                        return True
                    return False
                
        self.rush_persistence_count = 0
        return False

    def _check_early_harassment(self) -> None:
        """
        1-4분 견제 시스템

        1분부터 시작하여 15초마다 적 본진을 견제
        저글링, 뮤탈리스크 등 빠른 유닛으로 적 일꾼 견제 및 정보 수집
        """
        game_time = getattr(self.bot, "time", 0.0)

        # 1분부터 4분까지만 활성화
        if game_time < 60 or game_time >= 240:
            self.early_harassment_active = False
            return

        # 15초마다 견제 (more aggressive)
        if game_time - self.last_harassment_time < self.harassment_interval:
            return

        self.last_harassment_time = game_time
        self.early_harassment_active = True
        
        # Log only - Control is delegated to CombatManager
        self.logger.info(f"[{int(game_time)}s] EARLY HARASSMENT: Signal sent to CombatManager")

    def _detect_major_attack(self, game_time: float) -> bool:
        """
        중후반 대규모 공격 감지

        조건:
        1. 적 군대가 우리 기지 근처에 있음
        2. 적 군대 규모가 일정 수준 이상
        3. 고위협 유닛 (시즈탱크, 콜로서스 등) 포함
        """
        if not hasattr(self.bot, "enemy_units") or not hasattr(self.bot, "townhalls"):
            return False

        if not self.bot.townhalls.exists:
            return False

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            return False

        # 고위협 유닛 목록 (중후반 푸쉬의 핵심)
        high_threat_units = {
            # 테란
            "SIEGETANK", "SIEGETANKSIEGED", "THOR", "BATTLECRUISER",
            "LIBERATOR", "LIBERATORAG", "CYCLONE", "WIDOWMINE",
            # 프로토스
            "COLOSSUS", "DISRUPTOR", "IMMORTAL", "ARCHON",
            "CARRIER", "TEMPEST", "VOIDRAY", "HIGHTEMPLAR",
            # 저그
            "ULTRALISK", "BROODLORD", "RAVAGER", "LURKER", "LURKERMP"
        }

        total_threat_score = 0
        high_threat_count = 0
        enemies_near_base = []
        counted_tags = set()

        # ★ O(n) 최적화: 적 유닛 1회 순회, 각 타운홀 거리 체크 ★
        th_positions = [th.position for th in self.bot.townhalls]
        for enemy in enemy_units:
            try:
                if enemy.tag in counted_tags:
                    continue
                for th_pos in th_positions:
                    if enemy.distance_to(th_pos) < 25:
                        counted_tags.add(enemy.tag)
                        enemies_near_base.append(enemy)

                        enemy_type = getattr(enemy.type_id, "name", "").upper()
                        if enemy_type in high_threat_units:
                            high_threat_count += 1
                            total_threat_score += 10
                        elif enemy.can_attack:
                            total_threat_score += 2
                        break  # 이미 카운트됨, 다음 적으로
            except (AttributeError, TypeError):
                continue

        # 대규모 공격 판정
        # 조건: 위협 점수 30 이상 또는 고위협 유닛 3개 이상 (과민 감지 완화)
        if total_threat_score >= 30 or high_threat_count >= 3:
            # ★★★ 로그 스팸 방지: 5초마다만 출력 ★★★
            if game_time - self.last_major_attack_log > self.log_cooldown:
                self.logger.warning(f"[{int(game_time)}s] MAJOR ATTACK DETECTED! "
                                    f"Threat score: {total_threat_score}, High-threat units: {high_threat_count}")
                self.last_major_attack_log = game_time
            return True

        return False

    def _activate_defense_mode(self, game_time: float) -> None:
        """
        중후반 방어 모드 활성화

        Emergency Mode와 다르게:
        1. 드론 생산은 계속 (경제 유지)
        2. 로그 스팸 방지: 최소 10초 쿨다운
        2. 군대 집결 우선
        3. 방어 건물 추가 건설
        """
        # 이미 방어 모드면 타이머만 갱신
        if self.current_mode == StrategyMode.DEFENSIVE:
            self.last_major_attack_time = game_time
            return

        # ★ 로그 스팸 방지: 10초 쿨다운 ★
        last_log = getattr(self, "_last_defense_log_time", 0.0)
        should_log = (game_time - last_log) >= 10.0

        self.current_mode = StrategyMode.DEFENSIVE
        self.defense_mode_start_time = game_time
        self.last_major_attack_time = game_time

        if should_log:
            self._last_defense_log_time = game_time
            self.logger.warning(f"[{int(game_time)}s] DEFENSE MODE ACTIVATED - Major attack incoming!")

        # 군대 집결 신호
        self._request_army_rally()

        # 확장 기지 방어 건물 추가 요청 (BuildingCoordination에 위임)
        self._request_defensive_building(spine=True)

        # 적 공중 유닛 체크 → 스포어 요청도 위임
        if hasattr(self.bot, "enemy_units"):
            air_threats = {"MUTALISK", "VOIDRAY", "ORACLE", "PHOENIX",
                         "BATTLECRUISER", "CARRIER", "LIBERATOR", "BROODLORD"}
            for enemy in self.bot.enemy_units:
                enemy_type = getattr(enemy.type_id, "name", "").upper()
                if enemy_type in air_threats:
                    self._request_defensive_building(spore=True)
                    break

    def _check_defense_mode_timeout(self) -> None:
        """
        Defense mode auto-exit: if no major attack detected for 120 seconds,
        return to NORMAL mode. This prevents the bot from staying stuck in
        DEFENSIVE mode indefinitely after a threat has passed.
        """
        if self.current_mode != StrategyMode.DEFENSIVE:
            return

        game_time = getattr(self.bot, "time", 0.0)

        # Check if a major attack is currently happening
        if self._detect_major_attack(game_time):
            # Attack still ongoing - reset the timer
            self.last_major_attack_time = game_time
            return

        # No major attack right now - check if timeout has elapsed
        if game_time - self.last_major_attack_time >= self.defense_mode_timeout:
            self.current_mode = StrategyMode.NORMAL
            self._reset_min_army_for_attack()
            self.emergency_spine_requested = False
            self.logger.info(
                f"[{int(game_time)}s] DEFENSE MODE AUTO-EXIT: "
                f"No major attack for {int(self.defense_mode_timeout)}s, returning to NORMAL"
            )

    def _request_army_rally(self) -> None:
        """군대 집결 요청"""
        # Combat Manager에 집결 신호 전송
        combat = getattr(self.bot, "combat_manager", None)
        if combat:
            # 집결 포인트를 위협받는 기지 근처로 설정
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                rally_pos = self.bot.townhalls.first.position
                combat._rally_point = rally_pos
                combat._min_army_for_attack = 999  # 공격 중지, 방어 우선
                self.logger.info("Army rallying to defend base!")

    def _reset_min_army_for_attack(self) -> None:
        """방어 모드 종료 시 공격 임계값 복원"""
        combat = getattr(self.bot, "combat_manager", None)
        if combat and getattr(combat, "_min_army_for_attack", 0) >= 999:
            combat._min_army_for_attack = 20
            self.logger.info("Attack threshold reset to 20 (defense mode ended)")

    def _update_counter_build(self) -> None:
        """
        ★ Phase 17: 적 빌드에 따른 실시간 대응 빌드 업데이트 ★

        IntelManager에서 감지한 적 빌드 패턴에 따라 아군 유닛 비율을 즉각 조정합니다.
        - 정찰 정보의 신뢰도(confidence)를 고려한 대응 강도 조절
        - 확인된(confirmed) 패턴에는 강력한 대응
        - 의심(suspected) 패턴에는 부분적 대응
        """
        intel = getattr(self.bot, "intel", None)
        if not intel:
            return

        # ★ Phase 17: 적 빌드 패턴 및 신뢰도 확인 ★
        enemy_pattern = ""
        build_confidence = 0.0
        build_status = "unknown"

        if hasattr(intel, "get_enemy_build_pattern"):
            enemy_pattern = intel.get_enemy_build_pattern()

        if hasattr(intel, "get_build_pattern_confidence"):
            build_confidence = intel.get_build_pattern_confidence()

        if hasattr(intel, "get_build_pattern_status"):
            build_status = intel.get_build_pattern_status()

        # ★ Phase 17: 카운터빌드 반응속도 개선 — 폴백 타이밍 + 임계값 하향 ★
        game_time = getattr(self.bot, "time", 0)
        if (enemy_pattern == "unknown" or build_confidence < 0.1) and game_time > 150:
            # ★ Phase 17: 2분30초 이후 정찰 실패 → 즉시 폴백 (기존 3분)
            self._apply_safe_fallback_ratios()
            return
        if enemy_pattern == "unknown" or build_confidence < 0.1:
            # ★ Phase 17: 0.2→0.1 (더 낮은 confidence에서도 대응 시작)
            return

        # === 적 빌드별 대응 유닛 비율 설정 ===

        # === Dynamic Counter Logic from Knowledge Base (Commander Learning) ===
        # 1. Reset to base ratios for this race/phase
        enemy_race_name = self.detected_enemy_race.name.capitalize() # e.g. "Terran"
        base_ratios = self.knowledge_manager.get_unit_ratios(enemy_race_name, self.game_phase.value)
        
        if not base_ratios:
             # Keep existing if loading failed
             return
        
        current_ratios = base_ratios.copy()
        
        # 2. ★ Phase 17: Apply Build Pattern Counters with Confidence-Based Scaling ★
        recommended = intel.get_recommended_response()
        if recommended:
            # IntelManager recommends a list of units (e.g. ['hydralisk', 'corruptor'])
            # Boost ratio based on confidence level:
            # - confirmed (0.7+): 0.4 boost (strong counter)
            # - suspected (0.3-0.7): 0.2 boost (moderate counter)
            # - unknown (<0.3): 0.1 boost (weak counter)

            if build_status == "confirmed":
                boost_multiplier = 1.3  # 30% stronger
            elif build_status == "suspected":
                boost_multiplier = 0.7  # 30% weaker
            else:
                boost_multiplier = 0.3  # 70% weaker

            for unit_name in recommended:
                u_key = unit_name.lower().replace(" ", "")
                if u_key == "hydralisk": u_key = "hydra"
                if u_key == "lurkermp": u_key = "lurker"

                base_boost = 0.3
                adjusted_boost = base_boost * boost_multiplier

                current_ratios[u_key] = current_ratios.get(u_key, 0) + adjusted_boost

                # ★ 로그 출력 (10초마다만) ★
                if int(game_time) % 10 == 0 and self.bot.iteration % 22 == 0:
                    self.logger.info(
                        f"[{int(game_time)}s] Counter boost: {u_key} +{adjusted_boost:.2f} "
                        f"({build_status}, confidence={build_confidence:.0%})"
                    )
        
        # 3. Scan enemy units and adjust ratios (Reactive)
        if hasattr(self.bot, "enemy_units"):
            detected_types = set(u.type_id.name.upper() for u in self.bot.enemy_units)
            
            for e_type in detected_types:
                counter_rule = self.knowledge_manager.get_counter_unit(e_type)
                if counter_rule:
                    c_unit = counter_rule["unit"].lower()
                    # Normalize common names to match UnitFactory keys
                    if c_unit == "hydralisk": c_unit = "hydra"
                    if c_unit == "lurkermp": c_unit = "lurker"
                    
                    ratio_boost = counter_rule["ratio"]
                    
                    # Add/Boost counter unit (Adding weight)
                    current_ratios[c_unit] = current_ratios.get(c_unit, 0) + ratio_boost

        # 4. Normalize
        total = sum(current_ratios.values())
        if total > 0:
            for k in current_ratios:
                current_ratios[k] /= total
        
        # 5. Apply to current state
        if self.detected_enemy_race in self.race_unit_ratios:
            self.race_unit_ratios[self.detected_enemy_race][self.game_phase] = current_ratios
        self._request_defensive_building(spine=True)

        # 로그 출력 (30초마다)
        if int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
            self.logger.info(f"[{int(game_time)}s] Counter build for {enemy_pattern}")

    def _handle_air_threat(self) -> None:
        """
        공중 위협 대응 강화

        스포어/카운터 유닛 요청은 RacialCounterManager에서 처리.
        여기서는 스파이어 건설 + 대공 비율 강제만 담당.
        """
        game_time = getattr(self.bot, "time", 0)

        # 기지 수만큼 스포어 필요 (스포어 건설 자체는 racial_counter_manager에서 요청)
        if not hasattr(self, "_spore_count_needed"):
            self._spore_count_needed = 0
        if hasattr(self.bot, "townhalls"):
            self._spore_count_needed = max(2, self.bot.townhalls.amount)

        # 스파이어 건설 요청 -> BuildingCoordination에 위임
        self._request_spire_via_coordinator(game_time)

        # 대공 유닛 비율 강제 조정
        self._force_anti_air_ratios()

        # 로그 쿨다운 (10초마다만 출력)
        if not hasattr(self, "_last_air_log_time"):
            self._last_air_log_time = 0
        if game_time - self._last_air_log_time >= 10:
            self.logger.warning(f"[{int(game_time)}s] AIR THREAT ACTIVE - Anti-air priority")
            self._last_air_log_time = game_time

    def _force_anti_air_ratios(self) -> None:
        """★ 대공 유닛 비율 강제 조정 ★"""
        # 모든 페이즈에 대공 유닛 비율 높이기
        anti_air_ratios = {
            GamePhase.EARLY: {"zergling": 0.2, "queen": 0.3, "hydra": 0.5},
            GamePhase.MID: {"hydra": 0.5, "corruptor": 0.3, "queen": 0.2},
            GamePhase.LATE: {"hydra": 0.4, "corruptor": 0.4, "viper": 0.2},
        }

        # 현재 적 종족의 비율 덮어쓰기
        self.race_unit_ratios[self.detected_enemy_race] = anti_air_ratios

    def get_spore_count_needed(self) -> int:
        """필요한 스포어 크롤러 수 반환"""
        return getattr(self, "_spore_count_needed", 2)

    # ========== Delegation Helpers ==========

    def _request_defensive_building(self, spine: bool = False, spore: bool = False) -> None:
        """
        방어 건물 건설 요청을 중앙화하는 헬퍼.

        BuildingCoordination이 있으면 위임하고, 없으면 기존 플래그 방식 사용.
        Blackboard에도 긴급 상태를 전파합니다.

        Args:
            spine: 스파인 크롤러 요청
            spore: 스포어 크롤러 요청
        """
        if spine:
            self.emergency_spine_requested = True
        if spore:
            self.emergency_spore_requested = True
            if self.blackboard:
                self.blackboard.set("urgent_spore_all_bases", True)

        # BuildingCoordination이 있으면 요청 등록
        building_coord = getattr(self.bot, "building_coord", None)
        if building_coord:
            try:
                from sc2.ids.unit_typeid import UnitTypeId
                if spine:
                    building_coord.request_building(UnitTypeId.SPINECRAWLER, "StrategyManager")
                if spore:
                    building_coord.request_building(UnitTypeId.SPORECRAWLER, "StrategyManager")
            except Exception as e:
                self.logger.debug(f"[STRATEGY] defensive building request failed: {e}")

    def _request_spire_via_coordinator(self, game_time: float) -> None:
        """
        스파이어 건설 요청을 BuildingCoordination에 위임합니다.

        직접 구조물을 조회하는 대신, BuildingCoordination의 can_build/request_building을 사용합니다.
        BuildingCoordination이 없으면 로그만 남깁니다.
        """
        building_coord = getattr(self.bot, "building_coord", None)
        if building_coord:
            try:
                from sc2.ids.unit_typeid import UnitTypeId
                if building_coord.can_build(UnitTypeId.SPIRE):
                    building_coord.request_building(UnitTypeId.SPIRE, "StrategyManager-AirThreat")
                    self.logger.info(f"[{int(game_time)}s] Spire build requested via BuildingCoordination")
            except Exception as e:
                self.logger.debug(f"[STRATEGY] spire build request failed: {e}")
        else:
            # Fallback: 로그만 남기고, BotStepIntegrator/AggressiveTechBuilder가 처리
            if int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
                self.logger.info(f"[{int(game_time)}s] Spire needed for anti-air (no BuildingCoord)")

    def _get_drone_count(self) -> int:
        """
        현재 드론 수를 반환합니다.

        EconomyManager가 있으면 위임하고, 없으면 직접 조회합니다.

        Returns:
            현재 드론 수
        """
        # EconomyManager 위임
        economy = getattr(self.bot, "economy", None)
        if economy and hasattr(economy, "bot") and hasattr(economy.bot, "workers"):
            try:
                return economy.bot.workers.amount
            except Exception:
                pass

        # Fallback: 직접 조회
        if hasattr(self.bot, "workers"):
            try:
                return self.bot.workers.amount
            except Exception:
                pass

        if hasattr(self.bot, "units"):
            try:
                drones = self.bot.units.filter(lambda u: u.type_id.name == "DRONE")
                return drones.amount if hasattr(drones, "amount") else len(drones)
            except Exception:
                pass

        return 0

    def _detect_direct_air_threat(self) -> None:
        """
        ★ 직접 공중 유닛 감지 및 대응 ★

        빌드 패턴이 아닌 실제 공중 유닛이 보이면 즉시 대응
        """
        if not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)

        # 공중 위협 유닛 목록
        air_threat_units = {
            # 테란
            "BANSHEE", "BATTLECRUISER", "LIBERATOR", "LIBERATORAG",
            "VIKINGFIGHTER", "RAVEN", "MEDIVAC",
            # 프로토스
            "VOIDRAY", "ORACLE", "PHOENIX", "CARRIER", "TEMPEST",
            "MOTHERSHIP", "INTERCEPTOR",
            # 저그
            "MUTALISK", "CORRUPTOR", "BROODLORD", "VIPER"
        }

        # ★ 캐시된 적 구성 사용 ★
        comp = self._cached_enemy_composition
        air_unit_count = 0
        detected_air_types = set()
        for etype, count in comp.items():
            if etype in air_threat_units:
                air_unit_count += count
                detected_air_types.add(etype)

        # ★★★ IMPROVED: 공중 유닛 1기만 감지해도 즉시 대응 (기존: 2기) ★★★
        if air_unit_count >= 1:
            self._air_threat_active = True
            self._request_defensive_building(spore=True)

            # 30초마다 로그
            if int(game_time) % 30 == 0 and self.bot.iteration % 22 == 0:
                self.logger.warning(f"[{int(game_time)}s] [*][*][*] AIR THREAT ACTIVE: {air_unit_count} air units detected! [*][*][*]")
                self.logger.info(f"Air types: {detected_air_types}")

            # 히드라 우선 생산 설정
            self._force_hydra_production = True

            # ★★★ IMPROVED: 공중 유닛 수에 따라 히드라 비율 동적 조정 ★★★
            current_ratios = self.get_unit_ratios()

            # 공중 유닛이 많을수록 히드라 비율 증가
            if air_unit_count >= 10:
                hydra_ratio = 0.70  # 대규모 공중 병력 → 70% 히드라
            elif air_unit_count >= 5:
                hydra_ratio = 0.55  # 중간 규모 → 55% 히드라
            else:
                hydra_ratio = 0.45  # 소규모 → 45% 히드라 (기존 40%에서 증가)

            if "hydra" in current_ratios:
                current_ratios["hydra"] = max(current_ratios.get("hydra", 0), hydra_ratio)
            else:
                current_ratios["hydra"] = hydra_ratio

            # 조정된 비율을 race_unit_ratios에 반영 (이전에는 반영 없이 버려졌음)
            if self.detected_enemy_race in self.race_unit_ratios:
                self.race_unit_ratios[self.detected_enemy_race][self.game_phase] = current_ratios

            # 공중 위협 대응 호출
            self._handle_air_threat()

        elif air_unit_count == 0:
            # 공중 위협 해제 (일정 시간 유지)
            if hasattr(self, "_air_threat_active") and self._air_threat_active:
                if not hasattr(self, "_air_threat_clear_time"):
                    self._air_threat_clear_time = game_time
                elif game_time - self._air_threat_clear_time > 60:  # 60초 후 해제
                    self._air_threat_active = False
                    self._force_hydra_production = False
                    self.logger.info(f"[{int(game_time)}s] Air threat cleared")

    def is_air_threat_detected(self) -> bool:
        """공중 위협 감지 여부"""
        # ★ 직접 감지 우선 체크 ★
        if getattr(self, "_air_threat_active", False):
            return True

        intel = getattr(self.bot, "intel", None)
        if not intel:
            return False

        enemy_pattern = ""
        if hasattr(intel, "get_enemy_build_pattern"):
            enemy_pattern = intel.get_enemy_build_pattern()

        return enemy_pattern in ["protoss_stargate", "zerg_muta", "terran_mech"]

    def _apply_racial_counters(self) -> None:
        """Delegate counter logic to RacialCounterManager."""
        if not hasattr(self.bot, "enemy_units"):
            return

        race_map = {
            EnemyRace.TERRAN: "Terran",
            EnemyRace.PROTOSS: "Protoss",
            EnemyRace.ZERG: "Zerg",
        }
        race_str = race_map.get(self.detected_enemy_race)
        if not race_str:
            return

        current_ratios = self.race_unit_ratios.get(
            self.detected_enemy_race, {}
        ).get(self.game_phase, {})

        updated = self.counter_manager.update(
            enemy_race=race_str,
            game_phase=self.game_phase.name if hasattr(self.game_phase, 'name') else str(self.game_phase),
            game_time=getattr(self.bot, "time", 0),
            enemy_composition=self._cached_enemy_composition,
            current_ratios=current_ratios,
            request_building_fn=self._request_defensive_building,
        )

        # Write back updated ratios
        if self.detected_enemy_race in self.race_unit_ratios:
            self.race_unit_ratios[self.detected_enemy_race][self.game_phase] = updated

    def _counter_terran_units(self) -> None:
        """
        ★ Phase 21: 테란 유닛별 카운터 로직 ★

        - 바이오 (마린/마라우더/메딕): 바네링 돌진 + 저글링 포위
        - 메카닉 (탱크/토르): 레바저 담즙 + 뮤탈 견제
        - 공중 (바이킹/밴시/배틀크루저): 히드라 + 코럽터
        - 헬리온 러시: 퀸 + 바퀴 즉시
        """
        if self.detected_enemy_race != EnemyRace.TERRAN:
            return

        if not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)
        comp = self._cached_enemy_composition

        marine_count = comp.get("MARINE", 0)
        marauder_count = comp.get("MARAUDER", 0)
        medivac_count = comp.get("MEDIVAC", 0)
        tank_count = comp.get("SIEGETANK", 0) + comp.get("SIEGETANKSIEGED", 0)
        thor_count = comp.get("THOR", 0) + comp.get("THORAP", 0)
        hellion_count = comp.get("HELLION", 0) + comp.get("HELLIONTANK", 0)
        banshee_count = comp.get("BANSHEE", 0)
        battlecruiser_count = comp.get("BATTLECRUISER", 0)
        liberator_count = comp.get("LIBERATOR", 0) + comp.get("LIBERATORAG", 0)

        bio_count = marine_count + marauder_count

        # 바이오 (마린 6+ 또는 마라우더 3+): 바네링 + 저글링 돌진
        if bio_count >= 6 or (medivac_count >= 2 and bio_count >= 4):
            self._adjust_unit_ratio("baneling", 0.25)
            self._adjust_unit_ratio("zergling", 0.30)
            self._adjust_unit_ratio("roach", 0.20)
            self._adjust_unit_ratio("hydralisk", 0.15)
            self._adjust_unit_ratio("ravager", 0.10)
            if game_time > 300 and not getattr(self, "_zvt_bio_logged", False):
                self._zvt_bio_logged = True
                self.logger.info(f"[{int(game_time)}s] [*] ZvT BIO DETECTED -> Baneling+Ling priority [*]")

        # 메카닉 (탱크 2+ 또는 토르 1+): 레바저 담즙 + 우회 기동
        if tank_count >= 2 or thor_count >= 1:
            self._adjust_unit_ratio("ravager", 0.30)  # 담즙으로 탱크 파괴
            self._adjust_unit_ratio("roach", 0.25)
            self._adjust_unit_ratio("hydralisk", 0.20)
            self._adjust_unit_ratio("zergling", 0.15)
            self._adjust_unit_ratio("corruptor", 0.10)  # 토르+메디 대응
            if game_time > 300 and not getattr(self, "_zvt_mech_logged", False):
                self._zvt_mech_logged = True
                self.logger.info(f"[{int(game_time)}s] [*] ZvT MECH DETECTED -> Ravager bile + Roach [*]")

        # 공중 (밴시/배틀크루저/리버레이터): 히드라 + 코럽터
        if banshee_count >= 1 or battlecruiser_count >= 1 or liberator_count >= 2:
            self._adjust_unit_ratio("hydralisk", 0.35)
            self._adjust_unit_ratio("corruptor", 0.25)
            self._adjust_unit_ratio("roach", 0.20)
            self._adjust_unit_ratio("queen", 0.10)
            self._adjust_unit_ratio("zergling", 0.10)
            self._request_defensive_building(spore=True)
            if game_time > 300 and not getattr(self, "_zvt_air_logged", False):
                self._zvt_air_logged = True
                self.logger.info(f"[{int(game_time)}s] [*] ZvT AIR DETECTED -> Hydra+Corruptor+Spore [*]")

        # 헬리온 러시 (초반): 퀸 + 바퀴
        # ★ Phase 34: 4분→5분으로 확장 (4:30~5분 헬리온 러시 대응)
        if hellion_count >= 3 and game_time < 300:
            self._adjust_unit_ratio("queen", 0.20)
            self._adjust_unit_ratio("roach", 0.40)
            self._adjust_unit_ratio("zergling", 0.30)
            self._adjust_unit_ratio("ravager", 0.10)

    def _counter_protoss_units(self) -> None:
        """
        ★★★ 프로토스 유닛별 카운터 로직 ★★★

        감지된 프로토스 유닛에 따라 유닛 비율 동적 조정:
        - 불멸자(Immortal): 레이바저 담즙, 저글링 포위
        - 콜로서스(Colossus): 커럽터 필수, 레이바저 담즙
        - 공허 포격기(VoidRay): 히드라, 퀸
        - 아둔의 창(Adept): 바퀴, 저글링 수비
        - 고위 기사(HighTemplar): 분산, 링/바퀴 돌진
        - 추적자(Stalker): 저글링 포위, 바퀴
        """
        if self.detected_enemy_race != EnemyRace.PROTOSS:
            return

        if not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)

        # 프로토스 핵심 유닛 카운트
        immortal_count = 0
        # ★ 캐시된 적 구성 사용 (별도 루프 불필요) ★
        comp = self._cached_enemy_composition
        immortal_count = comp.get("IMMORTAL", 0)
        colossus_count = comp.get("COLOSSUS", 0)
        voidray_count = comp.get("VOIDRAY", 0)
        disruptor_count = comp.get("DISRUPTOR", 0)
        high_templar_count = comp.get("HIGHTEMPLAR", 0)
        archon_count = comp.get("ARCHON", 0)
        carrier_count = comp.get("CARRIER", 0)
        stalker_count = comp.get("STALKER", 0)

        # ★ NEW: DarkShrine/Oracle 테크 경고 대응 (IntelManager 연동)
        intel = getattr(self.bot, "intel", None)
        if intel and hasattr(intel, "has_tech_alert"):
            # DT 대응: 스포어 크롤러 + 오버시어 긴급 생산
            if intel.has_tech_alert("DT_INCOMING"):
                if not getattr(self, "_dt_response_active", False):
                    self._dt_response_active = True
                    self._request_defensive_building(spore=True)
                    self.logger.warning(f"[{int(game_time)}s] [*][*][*] DT INCOMING! Spore + Overseer PRIORITY [*][*][*]")
                    # Blackboard에 오버시어 긴급 요청
                    if self.blackboard:
                        self.blackboard.set("urgent_overseer", True)

            # Oracle 대응: 스포어 크롤러 + 퀸 집중
            if intel.has_tech_alert("AIR_INCOMING"):
                if not getattr(self, "_air_response_active", False):
                    self._air_response_active = True
                    self._request_defensive_building(spore=True)
                    self.logger.warning(f"[{int(game_time)}s] [*][*][*] STARGATE TECH! Spore + Queen PRIORITY [*][*][*]")

        # ★ 유닛별 대응 전략 ★

        # 불멸자 2기 이상 → 레이바저 담즙 강화
        if immortal_count >= 2:
            if not hasattr(self, "_immortal_counter_active"):
                self._immortal_counter_active = False

            if not self._immortal_counter_active:
                self._immortal_counter_active = True
                self.logger.info(f"[{int(game_time)}s] [*] IMMORTAL DETECTED ({immortal_count}) - Ravager bile priority [*]")

            # 레이바저 비율 증가
            self._adjust_unit_ratio("ravager", 0.35)
            self._adjust_unit_ratio("zergling", 0.35)  # 포위용
            self._adjust_unit_ratio("roach", 0.1)  # 바퀴 감소 (불멸자 약점)

        # 콜로서스 1기 이상 → 커럽터 필수
        if colossus_count >= 1:
            if not hasattr(self, "_colossus_counter_active"):
                self._colossus_counter_active = False

            if not self._colossus_counter_active:
                self._colossus_counter_active = True
                self.logger.info(f"[{int(game_time)}s] [*][*][*] COLOSSUS DETECTED ({colossus_count}) - Corruptor PRIORITY [*][*][*]")

            # 커럽터 + 레이바저 담즙
            self._adjust_unit_ratio("corruptor", 0.4)
            self._adjust_unit_ratio("ravager", 0.2)
            self._adjust_unit_ratio("hydra", 0.3)

            # 스파이어 긴급 건설 - AggressiveTechBuilder로 통합됨

        # 공허 포격기/캐리어 → 대공 강화 + ★ Phase 21: 바이퍼 추가 ★
        if voidray_count >= 2 or carrier_count >= 1:
            if not getattr(self, "_zvp_air_logged", False):
                self._zvp_air_logged = True
                self.logger.warning(f"[{int(game_time)}s] [*] AIR THREAT - VoidRay/Carrier detected [*]")
            self._handle_air_threat()
            self._adjust_unit_ratio("hydralisk", 0.35)
            self._adjust_unit_ratio("corruptor", 0.30)
            # ★ Phase 21: 캐리어 3+ 시 바이퍼 추가 (어둠 집어삼키기로 캐리어 잡기)
            if carrier_count >= 3:
                self._adjust_unit_ratio("viper", 0.10)
                self._adjust_unit_ratio("corruptor", 0.25)
                self._adjust_unit_ratio("hydralisk", 0.30)

        # 디스럽터 → 분산 필요, 빠른 공격
        if disruptor_count >= 1:
            # 로그 스팸 방지
            if game_time - self.last_disruptor_log > self.log_cooldown:
                self.logger.warning(f"[{int(game_time)}s] DISRUPTOR DETECTED - Split micro needed")
                self.last_disruptor_log = game_time
            # 빠른 유닛으로 우회 공격
            self._adjust_unit_ratio("zergling", 0.3)
            self._adjust_unit_ratio("mutalisk", 0.3)

        # 고위 기사/아콘 → 분산, 빠른 돌진
        if high_templar_count >= 1 or archon_count >= 2:
            # 로그 스팸 방지
            if game_time - self.last_high_templar_log > self.log_cooldown:
                self.logger.warning(f"[{int(game_time)}s] HIGH TEMPLAR/ARCHON - Rush them!")
                self.last_high_templar_log = game_time
            self._adjust_unit_ratio("zergling", 0.4)
            self._adjust_unit_ratio("ravager", 0.3)  # 담즙으로 폭풍 지역 회피

        # ★ Phase 34: 추적자(Stalker) 4+ → 저글링 포위 + 바퀴 돌진 (이전: stalker_count 수집만 하고 미사용)
        if stalker_count >= 4:
            if not getattr(self, "_zvp_stalker_logged", False):
                self._zvp_stalker_logged = True
                self.logger.info(f"[{int(game_time)}s] [*] ZvP STALKER ARMY -- Zergling surround + Roach [*]")
            self._adjust_unit_ratio("zergling", 0.35)  # 포위
            self._adjust_unit_ratio("roach", 0.30)     # 정면 탱킹
            self._adjust_unit_ratio("ravager", 0.20)   # 담즙으로 추격 저지
            self._adjust_unit_ratio("baneling", 0.15)  # 집결 시 광역

    def _apply_safe_fallback_ratios(self) -> None:
        """
        ★ Phase 12: 정찰 실패 시 종족별 안전 폴백 빌드 ★

        정찰 정보가 없을 때 가장 범용적인 유닛 조합을 생산합니다.
        - vs Terran: 바퀴 + 히드라 (바이오/메카닉 모두 대응)
        - vs Protoss: 바퀴 + 히드라 (게이트웨이/로보 모두 대응) + 포자 (오라클/공허 대비)
        - vs Zerg: 바퀴 + 바네링 (범용)
        - Unknown: 바퀴 + 히드라 (가장 안전)
        """
        race = self.detected_enemy_race
        fallback_ratios = {
            "zergling": 0.20,
            "roach": 0.40,
            "hydralisk": 0.25,
            "ravager": 0.10,
            "corruptor": 0.05,
        }

        if race == EnemyRace.TERRAN:
            fallback_ratios = {
                "zergling": 0.15,
                "baneling": 0.15,
                "roach": 0.30,
                "hydralisk": 0.30,
                "ravager": 0.10,
            }
        elif race == EnemyRace.PROTOSS:
            fallback_ratios = {
                "zergling": 0.10,
                "roach": 0.35,
                "hydralisk": 0.30,
                "ravager": 0.15,
                "corruptor": 0.10,
            }
            # 포자 건설 요청 (DT/Oracle 대비)
            self._request_defensive_building(spore=True)
        elif race == EnemyRace.ZERG:
            fallback_ratios = {
                "zergling": 0.15,
                "baneling": 0.15,
                "roach": 0.40,
                "hydralisk": 0.20,
                "ravager": 0.10,
            }

        # 현재 비율에 적용
        if self.detected_enemy_race in self.race_unit_ratios:
            self.race_unit_ratios[self.detected_enemy_race][self.game_phase] = fallback_ratios
        if self.blackboard:
            self.blackboard.set("unit_ratios", fallback_ratios)

    def _counter_zerg_units(self) -> None:
        """
        ★ NEW: ZvZ 유닛별 카운터 로직 ★

        - 저글링 다수 → 맹독충 + 바퀴 전환
        - 맹독충 → 바퀴 (맹독충에 강함)
        - 뮤탈리스크 → 히드라 + 스포어
        - 바퀴/히드라 → 레이바저 담즙
        - 12풀 러시 → 스파인 + 퀸 방어
        """
        if self.detected_enemy_race != EnemyRace.ZERG:
            return

        if not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)
        comp = self._cached_enemy_composition

        zergling_count = comp.get("ZERGLING", 0)
        baneling_count = comp.get("BANELING", 0)
        roach_count = comp.get("ROACH", 0)
        mutalisk_count = comp.get("MUTALISK", 0)
        hydra_count = comp.get("HYDRALISK", 0)
        ravager_count = comp.get("RAVAGER", 0)

        # 저글링 10+ → 바퀴 + 맹독충으로 전환 (저글링 미러는 불리)
        # ★ Phase 34: game_time < 300 제한 제거 — 5분 이후에도 저글링 러시 대응
        if zergling_count >= 10:
            self._adjust_unit_ratio("roach", 0.4)
            self._adjust_unit_ratio("baneling", 0.3)
            self._adjust_unit_ratio("zergling", 0.2)

        # 맹독충 4+ → 바퀴 전환 (바퀴가 맹독충에 강함)
        if baneling_count >= 4:
            self._adjust_unit_ratio("roach", 0.5)
            self._adjust_unit_ratio("ravager", 0.2)

        # 바퀴 5+ → 레이바저 + 히드라
        if roach_count >= 5:
            self._adjust_unit_ratio("ravager", 0.3)
            self._adjust_unit_ratio("hydra", 0.3)
            self._adjust_unit_ratio("roach", 0.3)

        # 뮤탈리스크 → 히드라 + 스포어
        if mutalisk_count >= 3:
            # ★ Phase 34: "hydralisk" 오타 수정 → "hydra" (내부 키 통일)
            self._adjust_unit_ratio("hydra", 0.5)
            self._request_defensive_building(spore=True)
            if game_time - getattr(self, "_last_zvz_muta_log", 0) > 10:
                self._last_zvz_muta_log = game_time
                self.logger.warning(f"[{int(game_time)}s] ZvZ: Mutalisk detected! Hydra + Spore priority")

        # ★ Phase 21: ZvZ 중반 안정화 — 로치→히드라→럴커 전환 ★
        if game_time >= 360:  # 6분+
            if roach_count >= 5 or hydra_count >= 5:
                # 로치/히드라 미러 → 럴커가 결정적
                self._adjust_unit_ratio("lurker", 0.20)
                # ★ Phase 34: "hydralisk" 오타 수정 → "hydra"
                self._adjust_unit_ratio("hydra", 0.30)
                self._adjust_unit_ratio("roach", 0.25)
                self._adjust_unit_ratio("ravager", 0.15)
                self._adjust_unit_ratio("zergling", 0.10)
                if not getattr(self, "_zvz_lurker_logged", False):
                    self._zvz_lurker_logged = True
                    self.logger.info(f"[{int(game_time)}s] [*] ZvZ MID: Lurker transition for positional advantage [*]")

    def _adjust_unit_ratio(self, unit_type: str, target_ratio: float) -> None:
        """유닛 비율 동적 조정"""
        current_ratios = self.race_unit_ratios[self.detected_enemy_race].get(
            self.game_phase, {}
        )

        if unit_type in current_ratios:
            # 기존 비율보다 높으면 업데이트
            if target_ratio > current_ratios[unit_type]:
                current_ratios[unit_type] = target_ratio
        else:
            current_ratios[unit_type] = target_ratio

        # Normalize so ratios sum to 1.0
        total = sum(current_ratios.values())
        if total > 0:
            for k in current_ratios:
                current_ratios[k] /= total

    def _request_spire_build(self) -> None:
        """스파이어 긴급 건설 요청 - 제거됨 (AggressiveTechBuilder로 통합)"""
        pass

    def should_force_hydra(self) -> bool:
        """히드라 강제 생산 여부"""
        return getattr(self, "_force_hydra_production", False)

    def _activate_emergency_mode(self, game_time: float) -> None:
        """
        Emergency Mode 활성화
        ★ Phase 17: Blackboard 연동 + 즉시 저글링 생산 요청 ★
        """
        self.emergency_active = True
        self.emergency_start_time = game_time
        self.current_mode = StrategyMode.EMERGENCY

        self.logger.warning(f"EMERGENCY MODE ACTIVATED at {int(game_time)}s - Rush detected!")

        # Economy Manager에 알림
        if hasattr(self.bot, "economy") and self.bot.economy:
            self.bot.economy.set_emergency_mode(True)

        # 긴급 방어 건물 건설 요청 (BuildingCoordination에 위임)
        self._request_defensive_building(spine=True)
        self.emergency_spore_requested = False

        # 적 공중 유닛이 있으면 스포어도 요청
        has_air_enemy = False
        if hasattr(self.bot, "enemy_units"):
            for enemy in self.bot.enemy_units:
                if getattr(enemy, "is_flying", False):
                    has_air_enemy = True
                    break
        if has_air_enemy:
            self._request_defensive_building(spore=True)

        # ★ Phase 17: Blackboard에 긴급 상태 전파 — 모든 시스템에 즉시 알림 ★
        if self.blackboard:
            self.blackboard.set("is_rush_detected", True)
            self.blackboard.set("emergency_mode", True)
            self.blackboard.set("emergency_start_time", game_time)
            # 저글링 우선 생산 비율 즉시 적용 (config-driven)
            if self.emergency_spore_requested:
                emergency_ratios = dict(self.emergency_air_ratios)
            else:
                emergency_ratios = dict(self.emergency_ratios)
            self.blackboard.set("unit_ratios", emergency_ratios)

        self.logger.info(f"Emergency defense requested: Spine={self.emergency_spine_requested}, Spore={self.emergency_spore_requested}")

    def _end_emergency_mode(self) -> None:
        """Emergency Mode 종료"""
        self.emergency_active = False
        self.current_mode = StrategyMode.NORMAL

        self.logger.info("Emergency mode ended - Returning to normal operations")

        # Reset attack threshold that was set to 999 during defense
        self._reset_min_army_for_attack()

        # Economy Manager 복구
        if hasattr(self.bot, "economy") and self.bot.economy:
            self.bot.economy.set_emergency_mode(False)

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

        # ★ 방어 모드가 활성화된 직후에는 덮어쓰지 않음 (oscillation 방지) ★
        game_time = getattr(self.bot, "time", 0.0)
        if (self.current_mode == StrategyMode.DEFENSIVE
                and game_time - self.defense_mode_start_time < 15.0):
            return  # 방어 모드 전환 후 15초간 유지

        # 군대 우위 계산 (supply-weighted)
        our_army = 0
        enemy_army = 0

        if hasattr(self.bot, "units"):
            for unit in self.bot.units:
                if unit.can_attack and unit.type_id.name != "DRONE":
                    our_army += getattr(unit, "supply_cost", 1)

        if hasattr(self.bot, "enemy_units"):
            for unit in self.bot.enemy_units:
                if unit.can_attack:
                    enemy_army += getattr(unit, "supply_cost", 1)

        # 공급량 기반 공격 (적 정보가 없어도 공격)
        army_supply = getattr(self.bot, "supply_army", 0)

        # 전략 결정
        if self.current_mode != StrategyMode.EMERGENCY:
            prev_mode = self.current_mode
            # 1. 압도적 물량이면 공격 (적 유닛 수와 무관하게)
            if army_supply >= 100:
                self.current_mode = StrategyMode.ALL_IN
            # 2. 적당한 물량이면 공격적 운영
            elif army_supply >= 40:
                self.current_mode = StrategyMode.AGGRESSIVE
            # 3. 상대적 우위 계산 (기존 로직)
            elif our_army > enemy_army * 1.5 and our_army >= 10:
                self.current_mode = StrategyMode.AGGRESSIVE
            elif our_army < enemy_army * 0.5 and enemy_army > 5:
                self.current_mode = StrategyMode.DEFENSIVE
            else:
                self.current_mode = StrategyMode.NORMAL

            # Reset attack threshold when leaving DEFENSIVE mode
            if prev_mode == StrategyMode.DEFENSIVE and self.current_mode != StrategyMode.DEFENSIVE:
                self._reset_min_army_for_attack()

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
        base_ratios = phase_ratios.get(self.game_phase, phase_ratios[GamePhase.EARLY])

        # ★ Feature 89: Apply custom unit weights from JARVIS when set ★
        if self.custom_unit_weights:
            merged = dict(base_ratios)
            for unit, weight in self.custom_unit_weights.items():
                merged[unit] = weight
            # Normalize
            total = sum(merged.values())
            if total > 0:
                for k in merged:
                    merged[k] /= total
            return merged

        return base_ratios

    def should_produce_drone(self) -> bool:
        """
        드론 생산 여부 결정

        Returns:
            드론을 생산해야 하면 True
        """
        # Emergency Mode에서는 드론 생산 최소화
        if self.emergency_active:
            drone_count = self._get_drone_count()
            return drone_count < 12  # 최소 12기만 유지

        if self.early_scout_greed_suppressed:
            drone_count = self._get_drone_count()
            drone_floor = 16 if self.early_scout_cheese_active else 20
            return drone_count < drone_floor

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

    # ========== #110: 게임 페이즈 관리 ==========

    def get_game_phase_details(self) -> Dict[str, Any]:
        """
        게임 페이즈 상세 정보 반환 (#110)

        초반/중반/후반 전환을 감지하고 페이즈별 전략 정보를 제공합니다.

        Returns:
            페이즈 상세 정보 딕셔너리
        """
        game_time = getattr(self.bot, "time", 0.0)
        supply_used = getattr(self.bot, "supply_used", 0)
        base_count = 0
        if hasattr(self.bot, "townhalls"):
            base_count = self.bot.townhalls.amount

        # 페이즈별 특성
        phase_config = {
            GamePhase.EARLY: {
                "name": "초반 (Early Game)",
                "time_range": "0~4분",
                "priority": "경제 확장, 정찰, 기본 방어",
                "drone_target": min(22, base_count * 16),
                "army_focus": "저글링 소수 (정찰/방어)",
                "expansion_goal": 2,
                "tech_goal": "스포닝풀 + 가스",
            },
            GamePhase.MID: {
                "name": "중반 (Mid Game)",
                "time_range": "4~10분",
                "priority": "군대 확충, 테크업, 타이밍 공격",
                "drone_target": min(55, base_count * 16),
                "army_focus": "주력 유닛 생산 (바퀴/히드라)",
                "expansion_goal": 3,
                "tech_goal": "레어 + 진화실 + 유닛 업그레이드",
            },
            GamePhase.LATE: {
                "name": "후반 (Late Game)",
                "time_range": "10분+",
                "priority": "맥스아웃, 고급 유닛, 멀티 전선",
                "drone_target": min(80, base_count * 16),
                "army_focus": "고급 유닛 (울트라/바이퍼/커럽터)",
                "expansion_goal": 5,
                "tech_goal": "하이브 + 3/3 업그레이드",
            },
        }

        current_config = phase_config.get(self.game_phase, phase_config[GamePhase.EARLY])

        return {
            "phase": self.game_phase.value,
            "game_time": game_time,
            "supply_used": supply_used,
            "base_count": base_count,
            **current_config,
        }

    def detect_phase_transition(self) -> Optional[str]:
        """
        페이즈 전환 감지 (#110)

        시간 기반뿐만 아니라 상황 기반 전환도 감지합니다.

        Returns:
            전환 설명 문자열 (전환 없으면 None)
        """
        game_time = getattr(self.bot, "time", 0.0)
        supply_used = getattr(self.bot, "supply_used", 0)

        # 강제 전환 조건 (시간보다 상황 우선)

        # 서플라이 100 이상이면 후반으로 강제 전환
        if self.game_phase == GamePhase.MID and supply_used >= 100:
            self.game_phase = GamePhase.LATE
            return f"서플라이 {supply_used} 도달 -> 후반 전환"

        # 3기지 이상이고 40서플라이 이상이면 중반으로 강제 전환
        base_count = 0
        if hasattr(self.bot, "townhalls"):
            base_count = self.bot.townhalls.amount

        if self.game_phase == GamePhase.EARLY and base_count >= 3 and supply_used >= 40:
            self.game_phase = GamePhase.MID
            return f"3기지 + 서플라이 {supply_used} -> 중반 전환"

        return None

    def get_phase_strategy_recommendation(self) -> Dict[str, Any]:
        """
        현재 페이즈에 맞는 전략 추천 (#110)

        Returns:
            전략 추천 딕셔너리
        """
        if self.game_phase == GamePhase.EARLY:
            return {
                "economy_weight": 0.7,
                "army_weight": 0.2,
                "tech_weight": 0.1,
                "should_expand": True,
                "should_attack": False,
                "recommended_action": "드론 생산 우선, 2기지 확장",
            }
        elif self.game_phase == GamePhase.MID:
            return {
                "economy_weight": 0.3,
                "army_weight": 0.5,
                "tech_weight": 0.2,
                "should_expand": True,
                "should_attack": True,
                "recommended_action": "군대 확충 + 타이밍 공격 준비",
            }
        else:  # LATE
            return {
                "economy_weight": 0.2,
                "army_weight": 0.6,
                "tech_weight": 0.2,
                "should_expand": True,
                "should_attack": True,
                "recommended_action": "맥스아웃 후 총공격",
            }

    def check_surrender(self, game_time: float) -> bool:
        """
        ★ Smart Surrender Logic ★
        
        Check if the game is hopelessly lost to save time.
        
        Conditions:
        1. Time > 5 minutes
        2. No bases left OR
        3. Massive army disadvantage (5x) with low population OR
        4. Critical supply drop (< 10) after 5 mins
        """
        if game_time < 300:  # Don't surrender in first 5 mins
            return False
            
        # 1. No bases left
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            # Check if we have enough minerals to rebuild (300+) AND a drone
            can_rebuild = False
            if self.bot.minerals >= 300:
                if hasattr(self.bot, "workers") and self.bot.workers.exists:
                    can_rebuild = True
            
            if not can_rebuild:
                self.logger.warning(f"[{int(game_time)}s] SURRENDER: No bases and cannot rebuild.")
                return True

        # 2. Critical Supply Drop (Wiped out)
        if hasattr(self.bot, "supply_used"):
            if self.bot.supply_used < 10 and game_time > 600: # 10분 이후 인구 10 미만
                self.logger.warning(f"[{int(game_time)}s] SURRENDER: Critical supply drop ({self.bot.supply_used}) late game.")
                return True
                
        # 3. Massive Disadvantage
        # (Requires reliable army value calculation, so keep it simple for now)
        # If opponent has 5+ bases and we have 1 base after 15 mins?
        if game_time > 900: # 15분
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.amount < 2:
                 if hasattr(self.bot, "enemy_structures"):
                     enemy_bases = len([s for s in self.bot.enemy_structures if s.name.lower() in ["nexus", "commandcenter", "orbitalcommand", "planetaryfortress", "hatchery", "lair", "hive"]])
                     if enemy_bases >= 4:
                        self.logger.warning(f"[{int(game_time)}s] SURRENDER: Economic collapse (1 vs {enemy_bases} bases).")
                        return True

        return False

    # =========================================================================
    # Feature #100: 테크 전환 감지
    # =========================================================================

    def detect_tech_switch(self) -> Optional[Dict[str, Any]]:
        """
        Feature #100: 적 테크 경로 변경 감지

        적의 건물 및 유닛 조합 변화를 추적하여 테크 전환을 감지합니다.

        감지 패턴:
        - 테란: 바이오 -> 메카 (배럭 중심 -> 팩토리/스타포트)
        - 테란: 메카 -> 바이오 (팩토리 -> 배럭 추가)
        - 프로토스: 게이트웨이 -> 로보틱스 (콜로서스/불멸자)
        - 프로토스: 지상 -> 공중 (스타게이트 추가)
        - 저그: 저글링 -> 로치/히드라 (워렌/덴 건설)
        - 저그: 지상 -> 공중 (스파이어 건설)

        Returns:
            테크 전환 정보 딕셔너리 또는 None
            {
                "detected": True/False,
                "from_tech": str,
                "to_tech": str,
                "confidence": float (0.0~1.0),
                "recommended_comp": str
            }
        """
        if not hasattr(self.bot, "enemy_structures"):
            return None

        enemy_structures = self.bot.enemy_structures
        if not enemy_structures.exists:
            return None

        race = self.detected_enemy_race

        if race == EnemyRace.TERRAN:
            return self._detect_terran_tech_switch(enemy_structures)
        elif race == EnemyRace.PROTOSS:
            return self._detect_protoss_tech_switch(enemy_structures)
        elif race == EnemyRace.ZERG:
            return self._detect_zerg_tech_switch(enemy_structures)

        return None

    def _detect_terran_tech_switch(self, enemy_structures) -> Optional[Dict[str, Any]]:
        """
        테란 테크 전환 감지: 바이오/메카/공중 전환 패턴 분석
        """
        barracks_count = 0
        factory_count = 0
        starport_count = 0
        armory_count = 0

        for s in enemy_structures:
            name = s.name.lower() if hasattr(s, "name") else ""
            if "barracks" in name:
                barracks_count += 1
            elif "factory" in name:
                factory_count += 1
            elif "starport" in name:
                starport_count += 1
            elif "armory" in name:
                armory_count += 1

        enemy_units = getattr(self.bot, "enemy_units", None)
        bio_count = 0
        mech_count = 0
        air_count = 0

        if enemy_units:
            for u in enemy_units:
                name = u.name.lower() if hasattr(u, "name") else ""
                if any(n in name for n in ["marine", "marauder", "ghost", "reaper"]):
                    bio_count += 1
                elif any(n in name for n in ["hellion", "hellbat", "siegetank", "cyclone", "thor"]):
                    mech_count += 1
                elif any(n in name for n in ["viking", "liberator", "banshee", "raven", "battlecruiser", "medivac"]):
                    air_count += 1

        result = {
            "detected": False,
            "from_tech": "unknown",
            "to_tech": "unknown",
            "confidence": 0.0,
            "recommended_comp": "balanced",
        }

        # 바이오 -> 메카 전환 감지
        if barracks_count >= 2 and factory_count >= 2 and armory_count >= 1:
            if mech_count > bio_count:
                result["detected"] = True
                result["from_tech"] = "bio"
                result["to_tech"] = "mech"
                result["confidence"] = min(1.0, mech_count / max(bio_count + mech_count, 1))
                result["recommended_comp"] = "roach_ravager_heavy"
                self.logger.info(
                    f"[{int(self.bot.time)}s] [TECH_SWITCH] 테란 바이오->메카 전환 감지! "
                    f"신뢰도: {result['confidence']:.1%}"
                )

        # 공중 전환 감지
        elif starport_count >= 2 and air_count > bio_count + mech_count:
            result["detected"] = True
            result["from_tech"] = "ground"
            result["to_tech"] = "air"
            result["confidence"] = min(1.0, air_count / max(bio_count + mech_count + air_count, 1))
            result["recommended_comp"] = "hydra_corruptor"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 테란 공중 전환 감지! "
                f"신뢰도: {result['confidence']:.1%}"
            )

        # 메카 -> 바이오 전환 감지
        elif factory_count >= 1 and barracks_count >= 3 and bio_count > mech_count * 2:
            result["detected"] = True
            result["from_tech"] = "mech"
            result["to_tech"] = "bio"
            result["confidence"] = min(1.0, bio_count / max(bio_count + mech_count, 1))
            result["recommended_comp"] = "baneling_zergling_heavy"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 테란 메카->바이오 전환 감지! "
                f"신뢰도: {result['confidence']:.1%}"
            )

        return result if result["detected"] else None

    def _detect_protoss_tech_switch(self, enemy_structures) -> Optional[Dict[str, Any]]:
        """
        프로토스 테크 전환 감지: 게이트웨이/로보틱스/공중 전환 패턴 분석
        """
        gateway_count = 0
        robo_count = 0
        stargate_count = 0
        templar_archives = False
        fleet_beacon = False

        for s in enemy_structures:
            name = s.name.lower() if hasattr(s, "name") else ""
            if "gateway" in name or "warpgate" in name:
                gateway_count += 1
            elif "robotics" in name and "bay" not in name:
                robo_count += 1
            elif "stargate" in name:
                stargate_count += 1
            elif "templar" in name:
                templar_archives = True
            elif "fleet" in name:
                fleet_beacon = True

        result = {
            "detected": False,
            "from_tech": "unknown",
            "to_tech": "unknown",
            "confidence": 0.0,
            "recommended_comp": "balanced",
        }

        # 게이트웨이 -> 로보틱스 전환 (콜로서스/불멸자)
        if robo_count >= 2:
            result["detected"] = True
            result["from_tech"] = "gateway"
            result["to_tech"] = "robotics"
            result["confidence"] = 0.8
            result["recommended_comp"] = "corruptor_roach"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 프로토스 로보틱스 집중 감지!"
            )

        # 공중 전환 (캐리어/보이드레이)
        elif stargate_count >= 2 or fleet_beacon:
            result["detected"] = True
            result["from_tech"] = "ground"
            result["to_tech"] = "air"
            result["confidence"] = 0.9 if fleet_beacon else 0.7
            result["recommended_comp"] = "hydra_corruptor"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 프로토스 공중 전환 감지!"
            )

        # 하이템플러 전환
        elif templar_archives:
            result["detected"] = True
            result["from_tech"] = "gateway"
            result["to_tech"] = "templar"
            result["confidence"] = 0.85
            result["recommended_comp"] = "zergling_ultra_surround"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 프로토스 하이템플러 감지!"
            )

        return result if result["detected"] else None

    def _detect_zerg_tech_switch(self, enemy_structures) -> Optional[Dict[str, Any]]:
        """
        저그 테크 전환 감지: 지상/공중 전환 패턴 분석
        """
        spire = False
        greater_spire = False
        lurker_den = False
        ultra_cavern = False

        for s in enemy_structures:
            name = s.name.lower() if hasattr(s, "name") else ""
            if "greaterspire" in name:
                greater_spire = True
            elif "spire" in name:
                spire = True
            elif "lurker" in name:
                lurker_den = True
            elif "ultralisk" in name:
                ultra_cavern = True

        result = {
            "detected": False,
            "from_tech": "unknown",
            "to_tech": "unknown",
            "confidence": 0.0,
            "recommended_comp": "balanced",
        }

        # 공중 전환 (뮤탈/브루드로드)
        if greater_spire:
            result["detected"] = True
            result["from_tech"] = "ground"
            result["to_tech"] = "broodlord"
            result["confidence"] = 0.9
            result["recommended_comp"] = "corruptor_hydra"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 저그 그레이터 스파이어 감지!"
            )
        elif spire:
            result["detected"] = True
            result["from_tech"] = "ground"
            result["to_tech"] = "mutalisk"
            result["confidence"] = 0.75
            result["recommended_comp"] = "hydra_spore"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 저그 스파이어 감지!"
            )

        # 울트라 전환
        elif ultra_cavern:
            result["detected"] = True
            result["from_tech"] = "ground"
            result["to_tech"] = "ultralisk"
            result["confidence"] = 0.85
            result["recommended_comp"] = "roach_ravager_bile"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 저그 울트라리스크 전환 감지!"
            )

        # 럴커 전환
        elif lurker_den:
            result["detected"] = True
            result["from_tech"] = "hydra"
            result["to_tech"] = "lurker"
            result["confidence"] = 0.8
            result["recommended_comp"] = "roach_ravager_bile"
            self.logger.info(
                f"[{int(self.bot.time)}s] [TECH_SWITCH] 저그 럴커 전환 감지!"
            )

        return result if result["detected"] else None

    def get_tech_switch_status(self) -> Dict[str, Any]:
        """
        Feature #100: 적 테크 전환 상태 조회

        Returns:
            테크 전환 현황 딕셔너리
        """
        tech_info = self.detect_tech_switch()
        if tech_info:
            return tech_info
        return {
            "detected": False,
            "from_tech": "unknown",
            "to_tech": "unknown",
            "confidence": 0.0,
            "recommended_comp": "balanced",
        }
