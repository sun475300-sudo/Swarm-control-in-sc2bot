# -*- coding: utf-8 -*-
"""
Opponent Modeling System - 적 행동 패턴 학습 및 예측

Features:
1. Historical Data Collection - 과거 게임에서 적 패턴 저장
2. Strategy Prediction - 초반 지표로 전략 예측
3. Adaptive Response - 예측에 기반한 선제적 대응
4. Pattern Recognition - 적 성향 분류 (공격형, 확장형, 치즈)
5. Integration - IntelManager, DynamicCounter, StrategyV2 연동
"""

from __future__ import annotations
import json
import os
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.position import Point2
except ImportError:
    pass


class OpponentStyle(Enum):
    """적 플레이 스타일 분류"""
    UNKNOWN = "unknown"
    AGGRESSIVE = "aggressive"      # 초반 압박형 (러쉬, 올인)
    MACRO = "macro"                # 확장 중심 (후반 지향)
    CHEESE = "cheese"              # 치즈 (프록시, 올인)
    TIMING = "timing"              # 타이밍 공격 중심
    DEFENSIVE = "defensive"        # 방어 중심
    MIXED = "mixed"                # 혼합형


class StrategySignal(Enum):
    """전략 시그널 (초반 지표)"""
    # Build patterns
    EARLY_POOL = "early_pool"                  # 12 Pool (Zerg)
    FAST_EXPAND = "fast_expand"                # 빠른 확장
    PROXY_DETECTED = "proxy_detected"          # 프록시 건물
    TECH_RUSH = "tech_rush"                    # 빠른 테크 (Stargate, Factory)
    NO_NATURAL = "no_natural"                  # 멀티 없음 (올인 징조)
    EARLY_GAS = "early_gas"                    # 빠른 가스 (테크 or 올인)

    # Army composition
    MASS_WORKERS = "mass_workers"              # 일꾼 다수 (매크로)
    EARLY_ARMY = "early_army"                  # 초반 병력 집결
    AIR_UNITS_EARLY = "air_units_early"        # 초반 공중 유닛

    # Behavior
    SCOUTING_AGGRESSIVE = "scouting_aggressive"  # 공격적 정찰
    BASE_HIDDEN = "base_hidden"                # 본진 숨김 (치즈)
    EARLY_AGGRESSION = "early_aggression"      # 초반 압박


@dataclass
class GameHistory:
    """한 게임의 기록"""
    game_id: str
    opponent_race: str
    opponent_style: str
    detected_strategy: str
    build_order_observed: List[str]  # ["spawningpool", "roachwarren", ...]
    timing_attacks: List[float]      # [180.0, 360.0, ...] (seconds)
    final_composition: Dict[str, int]  # {"zergling": 30, "roach": 15, ...}
    game_result: str  # "win" or "loss"
    game_duration: float
    early_signals: List[str]  # StrategySignal names
    tech_progression: List[Tuple[float, str]]  # [(120.0, "lair"), ...]


class OpponentModel:
    """단일 적에 대한 모델"""

    def __init__(self, opponent_id: str):
        self.opponent_id = opponent_id
        self.games_played = 0
        self.games_won = 0
        self.games_lost = 0

        # Style distribution
        self.style_counts: Dict[str, int] = defaultdict(int)
        self.dominant_style = OpponentStyle.UNKNOWN

        # Strategy patterns
        self.strategy_frequency: Dict[str, int] = defaultdict(int)
        self.build_order_patterns: List[List[str]] = []
        self.timing_attack_history: List[float] = []

        # Predictive indicators
        self.early_signal_correlations: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # {signal: {strategy: count}}

        # Composition preferences
        self.unit_preferences: Dict[str, float] = defaultdict(float)

    def update_from_game(self, game_history: GameHistory):
        """
        게임 결과로 모델 업데이트

        Note: game_result is from OUR perspective
        - "win" = we won, opponent lost
        - "loss" = we lost, opponent won
        """
        self.games_played += 1

        if game_history.game_result == "loss":
            self.games_won += 1  # We lost, opponent won
        elif game_history.game_result == "win":
            self.games_lost += 1  # We won, opponent lost

        # Update style
        self.style_counts[game_history.opponent_style] += 1
        self.dominant_style = OpponentStyle(max(self.style_counts.items(), key=lambda x: x[1])[0])

        # Update strategy frequency
        self.strategy_frequency[game_history.detected_strategy] += 1

        # Build order patterns
        self.build_order_patterns.append(game_history.build_order_observed)
        if len(self.build_order_patterns) > 20:
            self.build_order_patterns.pop(0)

        # Timing attacks
        self.timing_attack_history.extend(game_history.timing_attacks)
        if len(self.timing_attack_history) > 50:
            self.timing_attack_history = self.timing_attack_history[-50:]

        # Signal correlations
        for signal in game_history.early_signals:
            self.early_signal_correlations[signal][game_history.detected_strategy] += 1

        # Unit preferences
        for unit_type, count in game_history.final_composition.items():
            self.unit_preferences[unit_type] += count

    def predict_strategy(self, observed_signals: List[str]) -> Tuple[str, float]:
        """
        초반 시그널로 전략 예측

        Args:
            observed_signals: 관찰된 초반 시그널 목록

        Returns:
            (predicted_strategy, confidence)
        """
        if not observed_signals or not self.early_signal_correlations:
            return ("unknown", 0.0)

        # 시그널별 전략 점수 계산
        strategy_scores: Dict[str, float] = defaultdict(float)

        for signal in observed_signals:
            if signal in self.early_signal_correlations:
                total_signal_count = sum(self.early_signal_correlations[signal].values())
                for strategy, count in self.early_signal_correlations[signal].items():
                    # Normalized score
                    strategy_scores[strategy] += count / total_signal_count

        if not strategy_scores:
            # Fallback to most frequent strategy
            if self.strategy_frequency:
                most_common = max(self.strategy_frequency.items(), key=lambda x: x[1])
                confidence = most_common[1] / self.games_played
                return (most_common[0], confidence)
            return ("unknown", 0.0)

        # Get highest scoring strategy
        predicted = max(strategy_scores.items(), key=lambda x: x[1])
        confidence = min(predicted[1] / len(observed_signals), 1.0)

        return (predicted[0], confidence)

    def get_expected_timing_attacks(self) -> List[float]:
        """예상 타이밍 공격 시간대 반환"""
        if not self.timing_attack_history:
            return []

        # Cluster timing attacks
        from collections import Counter

        # Round to nearest 30 seconds
        rounded_times = [round(t / 30) * 30 for t in self.timing_attack_history]
        time_counts = Counter(rounded_times)

        # Return times that occurred >= 30% of games
        threshold = max(1, self.games_played * 0.3)
        expected = [time for time, count in time_counts.items() if count >= threshold]

        return sorted(expected)

    def to_dict(self) -> dict:
        """모델 직렬화"""
        return {
            "opponent_id": self.opponent_id,
            "games_played": self.games_played,
            "games_won": self.games_won,
            "games_lost": self.games_lost,
            "style_counts": dict(self.style_counts),
            "dominant_style": self.dominant_style.value,
            "strategy_frequency": dict(self.strategy_frequency),
            "build_order_patterns": self.build_order_patterns,
            "timing_attack_history": self.timing_attack_history,
            "early_signal_correlations": {
                k: dict(v) for k, v in self.early_signal_correlations.items()
            },
            "unit_preferences": dict(self.unit_preferences)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'OpponentModel':
        """모델 역직렬화"""
        model = cls(data["opponent_id"])
        model.games_played = data.get("games_played", 0)
        model.games_won = data.get("games_won", 0)
        model.games_lost = data.get("games_lost", 0)
        model.style_counts = defaultdict(int, data.get("style_counts", {}))
        model.dominant_style = OpponentStyle(data.get("dominant_style", "unknown"))
        model.strategy_frequency = defaultdict(int, data.get("strategy_frequency", {}))
        model.build_order_patterns = data.get("build_order_patterns", [])
        model.timing_attack_history = data.get("timing_attack_history", [])

        signal_corr = data.get("early_signal_correlations", {})
        model.early_signal_correlations = defaultdict(
            lambda: defaultdict(int),
            {k: defaultdict(int, v) for k, v in signal_corr.items()}
        )

        model.unit_preferences = defaultdict(float, data.get("unit_preferences", {}))

        return model


class OpponentModeling:
    """
    Opponent Modeling System - 적 패턴 학습 및 전략 예측

    Architecture:
    1. IntelManager로부터 실시간 데이터 수집
    2. 게임 중 초반 시그널 감지 (0-3분)
    3. 역사적 데이터 기반 전략 예측
    4. StrategyManagerV2에 대응 전략 제안
    5. 게임 종료 시 데이터 저장
    """

    def __init__(self, bot: BotAI, intel_manager=None, data_file: str = "data/opponent_models.json"):
        self.bot = bot
        self.intel = intel_manager or getattr(bot, "intel", None)
        self.logger = get_logger("OpponentModeling")
        self.data_file = data_file

        # Opponent models
        self.opponent_models: Dict[str, OpponentModel] = {}
        self.current_opponent_id: Optional[str] = None
        self.current_game_history: Optional[GameHistory] = None

        # Current game tracking
        self.observed_signals: Set[str] = set()
        self.build_order_observed: List[str] = []
        self.tech_progression: List[Tuple[float, str]] = []
        self.timing_attacks_detected: List[float] = []

        # Prediction
        self.predicted_strategy: Optional[str] = None
        self.prediction_confidence: float = 0.0
        self.prediction_made_at: float = 0.0

        # State
        self.last_update = 0
        self.update_interval = 22  # ~1 second
        self.early_game_phase = True  # 0-180s, signal detection phase

        # Load historical data
        self.load_models()

        self.logger.info("[OPPONENT_MODELING] System initialized")

    async def on_start(self):
        """게임 시작 시 호출"""
        # Identify opponent
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race:
            race_name = getattr(enemy_race, "name", str(enemy_race))
            # In real games, opponent_id would be player name/ID
            # For now, use race as identifier
            self.current_opponent_id = f"opponent_{race_name}"

            # Load or create model
            if self.current_opponent_id not in self.opponent_models:
                self.opponent_models[self.current_opponent_id] = OpponentModel(self.current_opponent_id)
                self.logger.info(f"[OPPONENT_MODELING] New opponent: {self.current_opponent_id}")
            else:
                model = self.opponent_models[self.current_opponent_id]
                self.logger.info(
                    f"[OPPONENT_MODELING] Known opponent: {self.current_opponent_id}\n"
                    f"  Games: {model.games_played} (W: {model.games_won}, L: {model.games_lost})\n"
                    f"  Dominant Style: {model.dominant_style.value}\n"
                    f"  Expected Timings: {model.get_expected_timing_attacks()}"
                )

        # Initialize game history
        game_id = f"game_{int(self.bot.time * 1000)}"
        self.current_game_history = GameHistory(
            game_id=game_id,
            opponent_race=race_name if enemy_race else "Unknown",
            opponent_style="unknown",
            detected_strategy="unknown",
            build_order_observed=[],
            timing_attacks=[],
            final_composition={},
            game_result="unknown",
            game_duration=0.0,
            early_signals=[],
            tech_progression=[]
        )

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        if iteration - self.last_update < self.update_interval:
            return

        self.last_update = iteration
        game_time = self.bot.time

        # Early game signal detection (0-180s)
        if game_time < 180.0:
            self.early_game_phase = True
            await self._detect_early_signals(game_time)
        elif self.early_game_phase:
            # Transition out of early game
            self.early_game_phase = False
            await self._make_strategy_prediction(game_time)

        # Continuous tracking
        await self._track_build_order(game_time)
        await self._detect_timing_attacks(game_time)
        await self._track_tech_progression(game_time)

        # Update blackboard
        if hasattr(self.bot, "blackboard") and self.bot.blackboard:
            self.bot.blackboard.set("predicted_strategy", self.predicted_strategy)
            self.bot.blackboard.set("prediction_confidence", self.prediction_confidence)
            self.bot.blackboard.set("observed_signals", list(self.observed_signals))

    async def _detect_early_signals(self, game_time: float):
        """초반 시그널 감지 (0-180s)"""
        if not self.intel:
            return

        enemy_structures = getattr(self.bot, "enemy_structures", [])
        enemy_units = getattr(self.bot, "enemy_units", [])

        # Build pattern signals
        structure_names = {getattr(s.type_id, "name", "").upper() for s in enemy_structures}

        # Fast expand detection
        if game_time < 120 and any(base in structure_names for base in ["HATCHERY", "NEXUS", "COMMANDCENTER"]):
            if len([s for s in enemy_structures if getattr(s.type_id, "name", "").upper() in ["HATCHERY", "NEXUS", "COMMANDCENTER"]]) >= 2:
                self._add_signal(StrategySignal.FAST_EXPAND)

        # Early pool detection (Zerg)
        if game_time < 100 and "SPAWNINGPOOL" in structure_names:
            self._add_signal(StrategySignal.EARLY_POOL)

        # Early gas detection
        gas_structures = {"EXTRACTOR", "ASSIMILATOR", "REFINERY"}
        if game_time < 90 and any(gas in structure_names for gas in gas_structures):
            self._add_signal(StrategySignal.EARLY_GAS)

        # Tech rush detection
        tech_structures = {"STARGATE", "FACTORY", "ROBOTICSFACILITY", "SPIRE"}
        if game_time < 150 and any(tech in structure_names for tech in tech_structures):
            self._add_signal(StrategySignal.TECH_RUSH)

        # No natural expansion
        if game_time > 120:
            base_count = len([s for s in enemy_structures if getattr(s.type_id, "name", "").upper() in ["HATCHERY", "NEXUS", "COMMANDCENTER", "LAIR", "HIVE", "ORBITALCOMMAND"]])
            if base_count <= 1:
                self._add_signal(StrategySignal.NO_NATURAL)

        # Early army detection
        army_supply = sum(getattr(u, "supply_cost", 1) for u in enemy_units if not u.is_worker)
        if game_time < 150 and army_supply >= 15:
            self._add_signal(StrategySignal.EARLY_ARMY)

        # Air units early
        air_units = [u for u in enemy_units if getattr(u, "is_flying", False) and not u.is_worker]
        if game_time < 180 and len(air_units) >= 2:
            self._add_signal(StrategySignal.AIR_UNITS_EARLY)

    def _add_signal(self, signal: StrategySignal):
        """시그널 추가 (중복 방지)"""
        signal_name = signal.value
        if signal_name not in self.observed_signals:
            self.observed_signals.add(signal_name)
            self.logger.info(f"[{int(self.bot.time)}s] ★ SIGNAL DETECTED: {signal_name}")

    async def _make_strategy_prediction(self, game_time: float):
        """전략 예측 수행 (초반 종료 시)"""
        if not self.current_opponent_id or self.current_opponent_id not in self.opponent_models:
            self.logger.info(f"[{int(game_time)}s] No opponent model available for prediction")
            return

        model = self.opponent_models[self.current_opponent_id]

        # Make prediction
        predicted, confidence = model.predict_strategy(list(self.observed_signals))

        self.predicted_strategy = predicted
        self.prediction_confidence = confidence
        self.prediction_made_at = game_time

        self.logger.info(
            f"[{int(game_time)}s] ★★★ STRATEGY PREDICTION ★★★\n"
            f"  Predicted: {predicted}\n"
            f"  Confidence: {confidence*100:.1f}%\n"
            f"  Signals: {list(self.observed_signals)}\n"
            f"  Expected Timings: {model.get_expected_timing_attacks()}"
        )

        # Notify StrategyManagerV2
        await self._send_prediction_to_strategy_manager(predicted, confidence)

    async def _send_prediction_to_strategy_manager(self, strategy: str, confidence: float):
        """예측을 StrategyManagerV2에 전달"""
        if not hasattr(self.bot, "strategy_manager"):
            return

        strategy_manager = self.bot.strategy_manager

        # Set blackboard recommendations
        if hasattr(self.bot, "blackboard") and self.bot.blackboard:
            # Recommend counter strategy
            counter_strategies = self._get_counter_strategy(strategy)
            self.bot.blackboard.set("recommended_strategy", counter_strategies)
            self.bot.blackboard.set("opponent_prediction", {
                "strategy": strategy,
                "confidence": confidence,
                "counter": counter_strategies
            })

            self.logger.info(f"[OPPONENT_MODELING] Recommended counter: {counter_strategies}")

    def _get_counter_strategy(self, opponent_strategy: str) -> List[str]:
        """적 전략에 대한 카운터 전략 반환"""
        counter_map = {
            "terran_bio": ["baneling", "zergling", "spine_crawler"],
            "terran_mech": ["hydralisk", "corruptor", "viper"],
            "terran_rush": ["zergling", "spine_crawler", "queen"],
            "protoss_stargate": ["hydralisk", "corruptor", "spore_crawler"],
            "protoss_robo": ["hydralisk", "roach", "corruptor"],
            "protoss_gateway": ["roach", "zergling", "spine_crawler"],
            "protoss_proxy": ["zergling", "spine_crawler", "queen"],
            "zerg_muta": ["hydralisk", "spore_crawler", "queen"],
            "zerg_roach": ["roach", "ravager", "hydralisk"],
            "zerg_ling_bane": ["baneling", "roach", "zergling"],
            "zerg_12pool": ["zergling", "spine_crawler", "queen"],
        }

        return counter_map.get(opponent_strategy, ["roach", "hydralisk", "zergling"])

    async def _track_build_order(self, game_time: float):
        """빌드 오더 추적"""
        if not self.intel:
            return

        enemy_structures = getattr(self.bot, "enemy_structures", [])

        for structure in enemy_structures:
            structure_name = getattr(structure.type_id, "name", "").lower()
            if structure_name and structure_name not in self.build_order_observed:
                self.build_order_observed.append(structure_name)

    async def _detect_timing_attacks(self, game_time: float):
        """타이밍 공격 감지"""
        if not self.intel:
            return

        # Check if under attack
        if self.intel.is_under_attack():
            # Check if this is a new attack (not within 30s of previous)
            if not self.timing_attacks_detected or game_time - self.timing_attacks_detected[-1] > 30:
                self.timing_attacks_detected.append(game_time)
                self.logger.info(f"[{int(game_time)}s] ★ TIMING ATTACK DETECTED")

    async def _track_tech_progression(self, game_time: float):
        """기술 진행 추적"""
        if not self.intel:
            return

        tech_buildings = self.intel.enemy_tech_buildings

        for tech in tech_buildings:
            tech_lower = tech.lower()
            if not any(t[1] == tech_lower for t in self.tech_progression):
                self.tech_progression.append((game_time, tech_lower))

    async def on_end(self, game_result: str):
        """
        게임 종료 시 호출

        Args:
            game_result: "Victory" or "Defeat"
        """
        if not self.current_game_history or not self.current_opponent_id:
            return

        game_time = self.bot.time

        # Finalize game history
        self.current_game_history.opponent_style = self._classify_opponent_style()
        self.current_game_history.detected_strategy = self.predicted_strategy or "unknown"
        self.current_game_history.build_order_observed = self.build_order_observed
        self.current_game_history.timing_attacks = self.timing_attacks_detected
        self.current_game_history.final_composition = self._get_final_enemy_composition()
        self.current_game_history.game_result = "win" if game_result == "Defeat" else "loss"
        self.current_game_history.game_duration = game_time
        self.current_game_history.early_signals = list(self.observed_signals)
        self.current_game_history.tech_progression = self.tech_progression

        # Update opponent model
        model = self.opponent_models[self.current_opponent_id]
        model.update_from_game(self.current_game_history)

        # Save to disk
        self.save_models()

        self.logger.info(
            f"[GAME_END] Opponent model updated:\n"
            f"  Opponent: {self.current_opponent_id}\n"
            f"  Style: {self.current_game_history.opponent_style}\n"
            f"  Strategy: {self.current_game_history.detected_strategy}\n"
            f"  Result: {self.current_game_history.game_result}\n"
            f"  Total Games: {model.games_played}"
        )

    def _classify_opponent_style(self) -> str:
        """적 플레이 스타일 분류"""
        game_time = self.bot.time

        # Cheese detection
        if StrategySignal.PROXY_DETECTED.value in self.observed_signals:
            return OpponentStyle.CHEESE.value

        if StrategySignal.NO_NATURAL.value in self.observed_signals and game_time < 180:
            return OpponentStyle.CHEESE.value

        # Aggressive detection
        if len(self.timing_attacks_detected) >= 2 and game_time < 480:
            return OpponentStyle.AGGRESSIVE.value

        if StrategySignal.EARLY_ARMY.value in self.observed_signals:
            return OpponentStyle.AGGRESSIVE.value

        # Macro detection
        if StrategySignal.FAST_EXPAND.value in self.observed_signals:
            if len(self.timing_attacks_detected) == 0 or (self.timing_attacks_detected and self.timing_attacks_detected[0] > 300):
                return OpponentStyle.MACRO.value

        # Timing attack detection
        if len(self.timing_attacks_detected) == 1 and 180 < game_time < 600:
            return OpponentStyle.TIMING.value

        # Default
        return OpponentStyle.MIXED.value

    def _get_final_enemy_composition(self) -> Dict[str, int]:
        """게임 종료 시점 적 조합"""
        if not self.intel:
            return {}

        return self.intel.get_enemy_composition()

    def save_models(self) -> bool:
        """모델을 파일에 저장"""
        try:
            directory = os.path.dirname(self.data_file)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            data = {
                opponent_id: model.to_dict()
                for opponent_id, model in self.opponent_models.items()
            }

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"[OPPONENT_MODELING] Models saved: {len(data)} opponents")
            return True

        except Exception as e:
            self.logger.error(f"[OPPONENT_MODELING] Failed to save models: {e}")
            return False

    def load_models(self) -> bool:
        """파일에서 모델 로드"""
        if not os.path.exists(self.data_file):
            self.logger.info(f"[OPPONENT_MODELING] No existing models file: {self.data_file}")
            return False

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.opponent_models = {
                opponent_id: OpponentModel.from_dict(model_data)
                for opponent_id, model_data in data.items()
            }

            self.logger.info(
                f"[OPPONENT_MODELING] Models loaded: {len(self.opponent_models)} opponents\n"
                f"  Total games: {sum(m.games_played for m in self.opponent_models.values())}"
            )
            return True

        except Exception as e:
            self.logger.error(f"[OPPONENT_MODELING] Failed to load models: {e}")
            return False

    def get_opponent_stats(self, opponent_id: str) -> Optional[Dict]:
        """특정 적의 통계 반환"""
        if opponent_id not in self.opponent_models:
            return None

        model = self.opponent_models[opponent_id]

        return {
            "games_played": model.games_played,
            "win_rate": model.games_won / model.games_played if model.games_played > 0 else 0.0,
            "dominant_style": model.dominant_style.value,
            "most_common_strategy": max(model.strategy_frequency.items(), key=lambda x: x[1])[0] if model.strategy_frequency else "unknown",
            "expected_timings": model.get_expected_timing_attacks(),
            "favorite_units": sorted(model.unit_preferences.items(), key=lambda x: x[1], reverse=True)[:5]
        }

    # ============================================================
    # Integration Methods (for main bot lifecycle)
    # ============================================================

    def on_game_start(self, opponent_id: str, opponent_race=None):
        """게임 시작 시 호출 - 적 추적 시작"""
        self.current_opponent = opponent_id
        self.current_game_history = GameHistory(opponent_id=opponent_id)
        self.observed_signals.clear()

        # Load opponent model if exists
        if opponent_id not in self.opponent_models:
            self.opponent_models[opponent_id] = OpponentModel(opponent_id)
            self.logger.info(f"[OPPONENT_MODELING] New opponent: {opponent_id}")
        else:
            self.logger.info(f"[OPPONENT_MODELING] Known opponent: {opponent_id} ({self.opponent_models[opponent_id].games_played} games)")

    async def on_step(self, iteration: int):
        """매 프레임 호출 - 신호 감지"""
        if not self.current_opponent or not self.bot:
            return

        game_time = self.bot.time

        # Only detect signals in early game (0-180s)
        if game_time <= 180.0:
            await self._detect_early_signals(game_time)

    def on_game_end(self, won: bool, lost: bool):
        """게임 종료 시 호출 - 데이터 저장"""
        if not self.current_opponent or not self.current_game_history:
            return

        # Update game history
        self.current_game_history.game_won = won
        self.current_game_history.game_lost = lost
        self.current_game_history.early_signals = [s.value for s in self.observed_signals]

        # Detect strategy (placeholder - would need more logic)
        if self.intel:
            # Try to detect strategy from intel data
            pass

        # Update opponent model
        model = self.opponent_models[self.current_opponent]
        model.update_from_game(self.current_game_history)

        # Save to disk
        self.save_models()

        self.logger.info(f"[OPPONENT_MODELING] Game data saved for {self.current_opponent}")

    def get_predicted_strategy(self) -> Tuple[Optional[str], float]:
        """현재 적의 전략 예측"""
        if not self.current_opponent or self.current_opponent not in self.opponent_models:
            return (None, 0.0)

        model = self.opponent_models[self.current_opponent]

        # If we have observed signals, use them for prediction
        if self.observed_signals:
            signal_strings = [s.value for s in self.observed_signals]
            return model.predict_strategy(signal_strings)

        # Otherwise, return most common strategy
        if model.strategy_frequency:
            most_common = max(model.strategy_frequency.items(), key=lambda x: x[1])
            total_games = sum(model.strategy_frequency.values())
            confidence = most_common[1] / total_games if total_games > 0 else 0.0
            return (most_common[0], confidence)

        return (None, 0.0)

    def get_counter_recommendations(self) -> List[str]:
        """예측된 전략에 대한 카운터 유닛 추천"""
        predicted_strategy, confidence = self.get_predicted_strategy()

        if not predicted_strategy or confidence < 0.3:
            # Default counters
            return ["roach", "hydralisk", "zergling"]

        return self._get_counter_strategy(predicted_strategy)
