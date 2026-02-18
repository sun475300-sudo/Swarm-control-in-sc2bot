



# -*- coding: utf-8 -*-
"""
WickedZergBotPro Implementation - on_step implementation

This file implements the on_step method for WickedZergBotPro.
It can be integrated into the existing wicked_zerg_bot_pro.py file,
or imported and used separately.
"""

try:
    from sc2.bot_ai import BotAI
except ImportError:
    class BotAI:
        pass

from bot_step_integration import BotStepIntegrator
from utils.logger import setup_logger
from typing import Optional, List, Dict, Any
from pathlib import Path
from blackboard import Blackboard
from difficulty_progression import DifficultyProgression
from personality_module import PersonalityModule, PersonalityMode
import traceback
import json
import time
import os
import shutil
import glob as glob_mod

class WickedZergBotProImpl(BotAI):
    """
    WickedZergBotPro on_step implementation.

    This class extends the existing WickedZergBotPro or
    can be integrated into the existing class.
    """

    def __init__(self, train_mode: bool = False, instance_id: int = 0,
                 personality: str = "serral", opponent_race=None,
                 game_count: int = 0, learning_rate: Optional[float] = None):
        """Initialize WickedZergBotPro."""
        super().__init__()
        self.train_mode = train_mode
        self.instance_id = instance_id
        self.personality_type = personality  # Store the requested personality type (string)
        self.personality = None              # Will be the actual module instance
        self.opponent_race = opponent_race
        self.game_count = game_count
        self.learning_rate = learning_rate

        # Initialize managers (lazy loading)
        self.blackboard = Blackboard()     # ★ Blackboard (Single Source of Truth) ★
        self.defense_coordinator = None    # ★ DefenseCoordinator (Unified Defense) ★
        self.early_defense = None          # ★ EarlyDefenseSystem (0-3 min rush defense) ★
        self.production_controller = None  # ★ ProductionController (Dynamic Authority) ★
        self.intel = None
        self.economy = None
        self.production = None
        self.combat = None
        self.scout = None
        self.micro = None
        self.idle_units = None  # ★ IdleUnitManager (Idle unit harassment) ★

        # Difficulty Progression System
        self.difficulty_progression = DifficultyProgression()
        self.current_difficulty = None  # Will be set in on_start()
        self.queen_manager = None

        # Advanced managers (initialized in on_start)
        self.strategy_manager = None       # Race-specific strategies + Emergency Mode
        self.performance_optimizer = None  # Distance caching + spatial indexing
        self.formation_controller = None   # PID-based smooth movement
        self.rogue_tactics = None          # Baneling drop + larva saving
        self.transformer_model = None      # Transformer decision model
        self.hierarchical_rl = None        # Hierarchical RL agent
        self.aggressive_strategies = None  # Early game aggressive strategies

        # Step integrator initialization
        self._step_integrator = None

        # ★ Feature 85: Build Order Timing Log ★
        self._build_order_log: List[Dict[str, Any]] = []
        self._tracked_structure_tags: set = set()

        # ★ Feature 86: Unit Lost Tracking ★
        self._units_lost: List[Dict[str, Any]] = []
        self._workers_created: int = 0
        self._expansions_built: int = 0

    async def on_start(self):
        """
        Called when the bot starts.

        Initializes all managers:
        - Strategy Manager: Race-specific strategies, Emergency Mode
        - Performance Optimizer: Distance caching, spatial indexing
        - PID Controller: Smooth unit movement
        - Rogue Tactics: Baneling drop, larva saving
        - Transformer Model: Decision making (training mode)
        - ProductionResilience: Safe unit production with retry logic
        """
        await super().on_start()

        print("[BOT] on_start: Initializing all managers...")
        self.logger = setup_logger("WickedZergBot")
        self.logger.info("Bot started. Initializing managers...")

        # === 0. Blackboard (Central State) ===
        # Already initialized in __init__, but logging here
        if self.blackboard:
             print("[BOT] ★ Blackboard active")

        # === 0.1 Resource Manager (Thread-safe resource reservation) ===
        try:
            from core.resource_manager import ResourceManager
            self.resource_manager = ResourceManager(self)
            print("[BOT] ★ ResourceManager initialized (thread-safe reservation system)")
        except ImportError as e:
            print(f"[BOT_WARN] ResourceManager not available: {e}")
            self.resource_manager = None

        # === 0.05 Difficulty Progression ===
        try:
            map_name = self.game_info.map_name if hasattr(self, 'game_info') else "Unknown"
            opponent_race = self.enemy_race if hasattr(self, 'enemy_race') else None

            if opponent_race and self.difficulty_progression:
                self.current_difficulty = self.difficulty_progression.get_recommended_difficulty(
                    map_name, opponent_race
                )
                print(f"[DIFFICULTY] Map: {map_name}, Opponent: {opponent_race.name}")
                print(f"[DIFFICULTY] Recommended Difficulty: {self.current_difficulty.name}")

                # Print stats summary if available
                stats_summary = self.difficulty_progression.get_stats_summary(map_name, opponent_race)
                if "No stats" not in stats_summary:
                    print(stats_summary)
            else:
                # Fallback
                try:
                    from sc2.data import Difficulty
                    self.current_difficulty = Difficulty.Easy
                    print("[DIFFICULTY] Using fallback difficulty: Easy")
                except ImportError:
                    self.current_difficulty = None
        except Exception as e:
            print(f"[DIFFICULTY] Error getting recommended difficulty: {e}")
            try:
                from sc2.data import Difficulty
                self.current_difficulty = Difficulty.Easy
            except ImportError:
                self.current_difficulty = None

        # ========== MANAGER INITIALIZATION (Factory Pattern) ==========
        # 기존 650줄의 중복 코드를 간결한 factory pattern으로 대체
        try:
            from core.manager_factory import ManagerFactory
            from core.manager_registry import get_all_manager_configs

            # Factory 생성 및 매니저 등록
            factory = ManagerFactory(self)
            factory.register_managers(get_all_manager_configs())

            # 모든 매니저 초기화 (의존성 순서 자동 관리)
            stats = factory.initialize_all(verbose=True)

            # Factory를 bot에 저장 (나중에 매니저 조회용)
            self.manager_factory = factory

            print(f"\n[BOT] ★ Manager initialization complete: {stats['succeeded']}/{stats['total']} succeeded ★\n")

        except ImportError as e:
            print(f"[BOT_ERROR] ManagerFactory not available: {e}")
            print("[BOT_ERROR] ManagerFactory is required! Cannot continue without it.")
            raise ImportError("ManagerFactory is required for bot initialization") from e

        # === Map Memory System 시작 ===
        if hasattr(self, "map_memory") and self.map_memory:
            try:
                await self.map_memory.on_start()
                print("[BOT] MapMemorySystem started - Enemy tracking active")
            except Exception as e:
                print(f"[BOT_WARN] MapMemorySystem on_start failed: {e}")
                traceback.print_exc()

        # === Personality Module (Jarvis) ===
        try:
            mode = PersonalityMode.NEUTRAL
            if self.personality_type:
                p_type = self.personality_type.lower()
                if "serral" in p_type or "cocky" in p_type:
                    mode = PersonalityMode.COCKY
                elif "maru" in p_type or "polite" in p_type:
                    mode = PersonalityMode.POLITE
                elif "dark" in p_type:
                    mode = PersonalityMode.COCKY
                elif "silent" in p_type:
                    mode = PersonalityMode.SILENT
            
            self.personality = PersonalityModule(self, mode=mode,
                                               knowledge_manager=getattr(self, 'knowledge_manager', None),
                                               opponent_modeling=getattr(self, 'opponent_modeling', None))
            print(f"[BOT] ★ PersonalityModule initialized (Jarvis active, Mode: {mode.value})")
        except Exception as e:
            print(f"[BOT_WARN] Failed to initialize PersonalityModule: {e}")
            traceback.print_exc()

        # === RL Agent initialization (train_mode only) ===
        self.rl_agent = None
        if self.train_mode:
            try:
                from local_training.rl_agent import RLAgent
                import os as _os
                initial_lr = self.learning_rate if self.learning_rate else 0.001
                model_path = str(Path(__file__).parent / "local_training" / "models" / "rl_agent_model.npz")
                self.rl_agent = RLAgent(learning_rate=initial_lr, model_path=model_path)
                if _os.path.exists(model_path):
                    print(f"[RL_AGENT] Loaded existing model from {model_path}")
                print(f"[RL_AGENT] Initialized (lr={initial_lr}, train_mode=True)")
            except ImportError as e:
                print(f"[RL_AGENT] Not available: {e}")
            except Exception as e:
                print(f"[RL_AGENT] Initialization failed: {e}")
                traceback.print_exc()

        # === Hierarchical RL System initialization ===
        self.hierarchical_rl = None
        try:
            from local_training.hierarchical_rl.improved_hierarchical_rl import HierarchicalRLSystem
            self.hierarchical_rl = HierarchicalRLSystem()
            print(f"[HIERARCHICAL_RL] Initialized (Shadow Mode Active)")
        except ImportError as e:
            print(f"[HIERARCHICAL_RL] Not available: {e}")
        except Exception as e:
            print(f"[HIERARCHICAL_RL] Initialization failed: {e}")
            traceback.print_exc()

        # === Situational Awareness Module Integration (Stage 5) ===
        self.situational_awareness = None
        try:
            from core.situational_awareness import SituationalAwareness
            self.situational_awareness = SituationalAwareness(self)
            print(f"[SITUATIONAL_AWARENESS] Initialized (SITREP Generation Active)")
        except ImportError as e:
            print(f"[SITUATIONAL_AWARENESS] Not available: {e}")
        except Exception as e:
            print(f"[SITUATIONAL_AWARENESS] Initialization failed: {e}")
            traceback.print_exc()

        # === Step integrator initialization ===
        self._step_integrator = BotStepIntegrator(self)

        # ★★★ 학습된 데이터 적용 (모든 매니저 초기화 완료 후) ★★★
        try:
            if hasattr(self, 'economy') and hasattr(self.economy, 'balancer'):
                self.economy.balancer.apply_learned_economy_weights()
                print("[BOT] [OK] Applied learned economy fundamentals to EconomyCombatBalancer")
        except Exception as e:
            print(f"[BOT] [WARNING] Failed to apply learned economy weights: {e}")
            traceback.print_exc()

        # ★★★ Opponent Modeling - Load previous data and start tracking ★★★
        if hasattr(self, 'opponent_modeling') and self.opponent_modeling:
            try:
                # Detect opponent ID (player name or ID)
                opponent_id = None
                if hasattr(self, 'opponent_id'):
                    opponent_id = self.opponent_id
                elif hasattr(self, 'enemy_name'):
                    opponent_id = self.enemy_name
                else:
                    # Fallback: use enemy race as identifier
                    opponent_id = f"AI_{self.enemy_race.name if hasattr(self, 'enemy_race') else 'Unknown'}"

                # Start tracking
                self.opponent_modeling.on_game_start(opponent_id, self.enemy_race if hasattr(self, 'enemy_race') else None)
                print(f"[OPPONENT_MODELING] Started tracking opponent: {opponent_id}")

                # Get strategy prediction
                predicted_strategy, confidence = self.opponent_modeling.get_predicted_strategy()
                if predicted_strategy:
                    print(f"[OPPONENT_MODELING] Predicted strategy: {predicted_strategy} (confidence: {confidence:.2%})")
                    counter_units = self.opponent_modeling.get_counter_recommendations()
                    print(f"[OPPONENT_MODELING] Recommended counters: {counter_units}")
            except Exception as e:
                print(f"[BOT_WARN] OpponentModeling on_start error: {e}")
                traceback.print_exc()

        print(f"[BOT] on_start complete. Enemy race: {self.opponent_race}")

    async def on_step(self, iteration: int):
        """
        Called every game step.

        This method executes actual game logic and training logic.

        NOTE: 모든 매니저 호출은 BotStepIntegrator에서 처리됨
        - StrategyManager: 종족별 전략 + Emergency Mode
        - RogueTacticsManager: 맹독충 드랍 + 라바 세이빙
        - AggressiveStrategies: 초반 공격 전략 (12풀, 맹독충 올인 등)
        중복 호출 방지를 위해 여기서는 호출하지 않음
        """
        # ★★★ 시간 제한: 30분(1800초) 강제 종료 (충분한 학습 시간 확보) - train_mode일 때만 ★★★
        if self.train_mode and self.time > 1800:
            if not hasattr(self, '_game_ended'):
                self._game_ended = True
                print(f"[GAME] Time limit reached ({int(self.time)}s). Surrendering for fast training.")
                await self.client.leave()
            return

        # Store iteration as attribute for other modules to access
        self.iteration = iteration

        # ★ Feature 86: Cache our unit tags for unit lost tracking ★
        if iteration % 22 == 0:
            if not hasattr(self, '_known_unit_tags'):
                self._known_unit_tags = {}
            if hasattr(self, 'units'):
                for unit in self.units:
                    self._known_unit_tags[unit.tag] = {
                        "type": unit.type_id.name,
                        "position": {"x": round(unit.position.x, 1), "y": round(unit.position.y, 1)},
                    }
                    # Track workers created
                    if unit.type_id.name == "DRONE" and unit.tag not in self._known_unit_tags:
                        self._workers_created = getattr(self, '_workers_created', 0) + 1

        # 전략 선택 (한 번만 실행)
        if self.aggressive_strategies and not self.aggressive_strategies._strategy_decided:
            enemy_race = str(getattr(self, "enemy_race", "Unknown"))
            self.aggressive_strategies.select_strategy(enemy_race)

        if self._step_integrator is None:
            self._step_integrator = BotStepIntegrator(self)

        # ★ Feature 85: Track key building/upgrade completions ★
        if iteration % 22 == 0:
            self._track_build_order()

        # Execute integrated on_step (모든 핵심 매니저 포함)
        await self._step_integrator.on_step(iteration)

        # Personality module is called in bot_step_integration.py; do not call here.

    async def on_end(self, game_result):
        """
        Called when the game ends.
        Handles result logging, reward calculation, and curriculum updates.
        """
        print(f"[BOT] Game ended with result: {game_result}")

        # ★ NEW: Personality Module - Send GG message
        if hasattr(self, "personality") and self.personality:
            result_str = str(game_result).upper()
            if "VICTORY" in result_str or "WIN" in result_str:
                await self.personality.on_victory()
            elif "DEFEAT" in result_str or "LOSS" in result_str:
                await self.personality.on_defeat()

        # ★ NEW: Save intel data for next game
        if self.intel:
             self.intel.save_data()

        # ★★★ Opponent Modeling - Save game data for learning ★★★
        if hasattr(self, 'opponent_modeling') and self.opponent_modeling:
            try:
                result_str = str(game_result).upper()
                won = "VICTORY" in result_str or "WIN" in result_str
                lost = "DEFEAT" in result_str or "LOSS" in result_str

                # Record game outcome
                self.opponent_modeling.on_game_end(won, lost)
                print(f"[OPPONENT_MODELING] Game data saved. Opponent model updated.")

                # Print learning summary every 5 games
                if self.opponent_modeling.current_opponent:
                    model = self.opponent_modeling.models.get(self.opponent_modeling.current_opponent)
                    if model and model.games_played % 5 == 0:
                        print(f"[OPPONENT_MODELING] Opponent: {self.opponent_modeling.current_opponent}")
                        print(f"  Games: {model.games_played}, Wins: {model.games_won}, Losses: {model.games_lost}")
                        print(f"  Win rate: {model.games_won / model.games_played * 100:.1f}%")
            except Exception as e:
                print(f"[BOT_WARN] OpponentModeling on_end error: {e}")
                traceback.print_exc()

        # Performance Optimizer cleanup
        # if self.performance_optimizer:
        #     self.performance_optimizer.on_end(game_result)  # Method doesn't exist

        await super().on_end(game_result)

        # Training mode: Calculate final reward and save model
        if self.train_mode:
            try:
                # ★★★ NEW: Analyze victory/defeat conditions for detailed reward ★★★
                result_str = str(game_result).upper()
                game_won = "VICTORY" in result_str or "WIN" in result_str
                game_lost = "DEFEAT" in result_str or "LOSS" in result_str

                # Default rewards
                game_outcome_reward = 0.0

                # Use VictoryConditionsLearner for detailed analysis
                if hasattr(self, '_victory_learner') and self._victory_learner:
                    if game_won:
                        conditions, reward = self._victory_learner.analyze_game_result(self, "Victory")
                        game_outcome_reward = reward
                        print(f"\n[VICTORY] Conditions met: {', '.join(conditions)}")
                        print(f"[VICTORY] Total reward: {reward:.1f}")
                    elif game_lost:
                        conditions, penalty = self._victory_learner.analyze_game_result(self, "Defeat")
                        game_outcome_reward = penalty
                        print(f"\n[DEFEAT] Conditions: {', '.join(conditions)}")
                        print(f"[DEFEAT] Total penalty: {penalty:.1f}")

                    # 통계 출력 (10게임마다)
                    total_games = len(self._victory_learner.victory_patterns) + len(self._victory_learner.defeat_patterns)
                    if total_games % 10 == 0 and total_games > 0:
                        self._victory_learner.print_analysis()
                else:
                    # Fallback: Simple reward
                    if game_won:
                        game_outcome_reward = 10.0
                    elif game_lost:
                        game_outcome_reward = -5.0

                # CRITICAL FIX: Initialize parameters_updated counter
                self.parameters_updated = 0

                # ★★★ Adaptive Learning Rate Update (최우선) ★★★
                if hasattr(self, 'adaptive_lr') and self.adaptive_lr:
                    new_lr = self.adaptive_lr.update(game_won)

                    # 학습률이 조정되었으면 RL Agent에 적용
                    if new_lr and hasattr(self, 'rl_agent') and self.rl_agent:
                        self.rl_agent.learning_rate = new_lr
                        print(f"[ADAPTIVE_LR] [OK] RL Agent 학습률 업데이트: {new_lr:.6f}")

                    # 10게임마다 통계 출력
                    if self.adaptive_lr.total_games % 10 == 0:
                        print(self.adaptive_lr.get_summary())

                # RL agent: end episode and perform learning (CRITICAL!)
                if hasattr(self, 'rl_agent') and self.rl_agent:
                    # End episode triggers backpropagation and weight update
                    # (경험 데이터는 end_episode 내부에서 자동 저장)
                    training_stats = self.rl_agent.end_episode(final_reward=game_outcome_reward, save_experience=True)

                    # Check if learning occurred (steps > 0 means rewards were collected)
                    if training_stats.get('steps', 0) > 0:
                        self.parameters_updated = 1  # Mark that learning occurred
                        print(f"[TRAINING] [OK] Neural network updated!")
                        print(f"  Loss: {training_stats.get('loss', 0):.4f}, Avg Reward: {training_stats.get('avg_reward', 0):.3f}")
                        print(f"  Steps: {training_stats.get('steps', 0)}, ε={training_stats.get('epsilon', 0):.3f}, LR={training_stats.get('learning_rate', 0):.6f}")
                    else:
                        print(f"[TRAINING] No learning this episode (no rewards collected)")

                    # 모델 검증 (게임 결과 기록)
                    game_time = getattr(self, 'time', 0)
                    self.rl_agent.validate(game_won, game_time)

                    # 배포 가능 여부 확인 (10 게임마다)
                    if self.rl_agent.episode_count % 10 == 0:
                        ready, reason = self.rl_agent.is_ready_for_deployment()
                        if ready:
                            print(f"[RL_AGENT] ★ MODEL READY FOR DEPLOYMENT ★")
                        else:
                            print(f"[RL_AGENT] Training progress: {reason}")

                    # Save model
                    if hasattr(self.rl_agent, 'save_model'):
                        model_path = "local_training/models/rl_agent_model.npz"
                        self.rl_agent.save_model(model_path)

                # Reset reward system
                if hasattr(self, '_reward_system'):
                    self._reward_system.reset()

            except Exception as e:
                print(f"[WARNING] Training end logic error: {e}")
                import traceback
                traceback.print_exc()

        # ★★★ 게임 간 매니저 상태 초기화 (훈련 에피소드 안정성) ★★★
        self._reset_all_managers()

        # ★★★ 커리큘럼 매니저: 승리/패배 기록 (종족별 추적 포함) ★★★
        try:
            from local_training.curriculum_manager import CurriculumManager

            curriculum = CurriculumManager()
            result_str = str(game_result).upper()

            # ★ 상대 종족 감지 ★
            opponent_race = None
            try:
                if hasattr(self, 'enemy_race') and self.enemy_race:
                    opponent_race = str(self.enemy_race).replace("Race.", "")
                elif hasattr(self, '_enemy_race'):
                    opponent_race = str(self._enemy_race).replace("Race.", "")
                # 적 유닛/건물에서 종족 추론
                elif hasattr(self, 'enemy_units') and self.enemy_units:
                    enemy_unit = self.enemy_units.first
                    if hasattr(enemy_unit, 'race'):
                        opponent_race = str(enemy_unit.race).replace("Race.", "")
                elif hasattr(self, 'enemy_structures') and self.enemy_structures:
                    enemy_struct = self.enemy_structures.first
                    if hasattr(enemy_struct, 'race'):
                        opponent_race = str(enemy_struct.race).replace("Race.", "")
            except Exception:
                pass

            if opponent_race:
                print(f"[RACE] 상대 종족: {opponent_race}")

            if "VICTORY" in result_str or "WIN" in result_str:
                promoted = curriculum.record_win(opponent_race)
                if promoted:
                    print("[CURRICULUM] ★★★ 다음 단계로 승격! ★★★")
            elif "DEFEAT" in result_str or "LOSS" in result_str:
                demoted = curriculum.record_loss(opponent_race)
                if demoted:
                    print("[CURRICULUM] 난이도 하향 - 연습 더 필요")

            # 현재 진행 상황 출력
            progress = curriculum.get_progress_info()
            print(f"[CURRICULUM] 현재 단계: {progress['level_name']} "
                  f"({progress['wins_at_current_level']}/{progress['wins_required']}승)")
            print(f"[CURRICULUM] 최종 목표: CheatInsane AI 격파!")

            # ★ 종족별 승률 출력 ★
            curriculum.print_race_stats()

        except Exception as e:
            print(f"[WARNING] Curriculum manager error: {e}")

        # ★★★ Game Analytics - 게임 결과 상세 분석 ★★★
        if hasattr(self, 'game_analytics') and self.game_analytics and self.train_mode:
            try:
                # 추가 통계 수집
                additional_stats = {
                    "worker_count": self.workers.amount if hasattr(self, 'workers') else 0,
                    "army_count": self.units.amount if hasattr(self, 'units') else 0,
                    "base_count": self.townhalls.amount if hasattr(self, 'townhalls') else 0,
                    "pool_timing": getattr(self, 'pool_timing', 0),
                    "first_expand_timing": getattr(self, 'first_expand_timing', 0),
                    "minerals": self.minerals if hasattr(self, 'minerals') else 0,
                    "vespene": self.vespene if hasattr(self, 'vespene') else 0,
                }

                # 실제 난이도 가져오기
                difficulty_str = 'Easy'  # 기본값
                if hasattr(self, 'current_difficulty') and self.current_difficulty:
                    difficulty_str = self.current_difficulty.name

                # 게임 분석 기록
                self.game_analytics.record_game(
                    game_id=getattr(self, 'game_count', 0),
                    map_name=str(getattr(self, 'game_info', {}).get('map_name', 'Unknown')) if hasattr(self, 'game_info') else 'Unknown',
                    opponent_race=str(getattr(self, 'enemy_race', 'Unknown')).replace('Race.', ''),
                    difficulty=difficulty_str,
                    result=str(game_result),
                    game_time=getattr(self, 'time', 0.0) if hasattr(self, 'time') else 0.0,
                    additional_stats=additional_stats
                )

                # 난이도 진행도 시스템에도 기록
                if hasattr(self, 'difficulty_progression') and self.difficulty_progression:
                    try:
                        map_name = str(getattr(self, 'game_info', {}).get('map_name', 'Unknown')) if hasattr(self, 'game_info') else 'Unknown'
                        opponent_race = getattr(self, 'enemy_race', None)
                        won = (str(game_result) == "Victory")

                        if opponent_race and hasattr(self, 'current_difficulty') and self.current_difficulty:
                            self.difficulty_progression.record_game(
                                map_name=map_name,
                                opponent_race=opponent_race,
                                difficulty=self.current_difficulty,
                                won=won
                            )
                            print(f"[DIFFICULTY] Recorded: {map_name} vs {opponent_race.name} ({self.current_difficulty.name}): {'WIN' if won else 'LOSS'}")
                    except Exception as e:
                        print(f"[DIFFICULTY] Error recording to progression system: {e}")

                # 10게임마다 통계 요약 출력
                if self.game_analytics.total_games % 10 == 0:
                    print(self.game_analytics.get_summary())

                # 종족별 조언 (20게임마다)
                if self.game_analytics.total_games % 20 == 0:
                    opponent_race = str(getattr(self, 'enemy_race', 'Unknown')).replace('Race.', '')
                    advice = self.game_analytics.get_race_specific_advice(opponent_race)
                    if advice:
                        print(advice)

            except Exception as e:
                print(f"[WARNING] Game analytics error: {e}")

        # ★★★ Phase 22: Game Result Reporter - 경기 결과 자동 보고서 ★★★
        try:
            # GameDataLogger 종료 처리
            if hasattr(self, 'game_data_logger') and self.game_data_logger:
                result_str = str(game_result)
                self.game_data_logger.finalize_game(result_str)

                # GameResultReporter로 보고서 생성
                if hasattr(self, 'game_result_reporter') and self.game_result_reporter:
                    report_text = self.game_result_reporter.generate_report(
                        self.game_data_logger.game_data
                    )
                    print("\n" + report_text)

                    # Discord용 한줄 요약도 생성
                    quick_summary = self.game_result_reporter.generate_quick_summary(
                        self.game_data_logger.game_data
                    )
                    print(f"\n[QUICK SUMMARY] {quick_summary}")

                    # 봇에 요약 저장 (JARVIS Discord 전송용)
                    self._game_quick_summary = quick_summary
                    self._game_report_text = report_text
        except Exception as e:
            print(f"[WARNING] Game result reporter error: {e}")

        # ★ Feature 81: Structured Game Result Logging ★
        try:
            self._save_structured_game_result(game_result)
        except Exception as e:
            print(f"[WARNING] Structured game result logging error: {e}")

        # ★ Feature 84: Replay Auto-Organization ★
        try:
            self._organize_replay(game_result)
        except Exception as e:
            print(f"[WARNING] Replay organization error: {e}")

        # ★ Feature 85: Save Build Order Timing Log ★
        try:
            self._save_build_order_log()
        except Exception as e:
            print(f"[WARNING] Build order log save error: {e}")

        # Store training result for run_with_training.py
        self._training_result = {
            "game_result": str(game_result),
            "game_time": getattr(self, 'time', 0.0) if hasattr(self, 'time') else 0.0,
            "build_order_score": getattr(self, 'build_order_score', None),
            "loss_reason": getattr(self, 'loss_reason', None),
            "parameters_updated": getattr(self, 'parameters_updated', 0)
        }

    # =========================================================================
    # Feature 81: Structured Game Result Logging
    # =========================================================================
    def _save_structured_game_result(self, game_result) -> None:
        """Save a structured game result dict to logs/game_results.json."""
        result_str = str(game_result).upper()
        if "VICTORY" in result_str or "WIN" in result_str:
            result_label = "win"
        elif "DEFEAT" in result_str or "LOSS" in result_str:
            result_label = "loss"
        else:
            result_label = "unknown"

        # Gather opponent race
        opp_race = "Unknown"
        try:
            if hasattr(self, 'enemy_race') and self.enemy_race:
                opp_race = str(self.enemy_race).replace("Race.", "")
        except Exception:
            pass

        # Gather stats
        game_duration = getattr(self, 'time', 0.0) if hasattr(self, 'time') else 0.0
        final_supply = getattr(self, 'supply_used', 0) if hasattr(self, 'supply_used') else 0
        final_minerals = getattr(self, 'minerals', 0) if hasattr(self, 'minerals') else 0
        final_vespene = getattr(self, 'vespene', 0) if hasattr(self, 'vespene') else 0
        workers_created = getattr(self, '_workers_created', 0)
        expansions_built = getattr(self, '_expansions_built', 0)

        # Units killed / lost counts
        units_killed = 0
        units_lost_count = len(getattr(self, '_units_lost', []))
        try:
            if hasattr(self, 'state') and hasattr(self.state, 'score'):
                score = self.state.score
                units_killed = getattr(score, 'killed_value_units', 0)
        except Exception:
            pass

        game_result_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "result": result_label,
            "opponent_race": opp_race,
            "game_duration_seconds": round(game_duration, 1),
            "final_supply": final_supply,
            "final_minerals": final_minerals,
            "final_vespene": final_vespene,
            "units_killed": units_killed,
            "units_lost": units_lost_count,
            "workers_created": workers_created,
            "expansions_built": expansions_built,
            "units_lost_details": getattr(self, '_units_lost', []),
        }

        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        results_file = logs_dir / "game_results.json"

        # Load existing or create new list
        existing = []
        if results_file.exists():
            try:
                with open(results_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
            except (json.JSONDecodeError, IOError):
                existing = []

        existing.append(game_result_entry)

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        print(f"[GAME_RESULT] Saved structured result: {result_label} vs {opp_race} ({game_duration:.0f}s)")

    # =========================================================================
    # Feature 84: Replay Auto-Organization
    # =========================================================================
    def _organize_replay(self, game_result) -> None:
        """Find the most recent .SC2Replay and copy it to an organized directory."""
        try:
            # Common replay directories
            replay_dirs = [
                Path.home() / "Documents" / "StarCraft II" / "Replays",
                Path.home() / "Documents" / "StarCraft II" / "Accounts",
                Path("replays"),
                Path("."),
            ]

            recent_replay = None
            recent_time = 0

            for replay_dir in replay_dirs:
                if not replay_dir.exists():
                    continue
                # Search recursively for .SC2Replay files
                for replay_path in replay_dir.rglob("*.SC2Replay"):
                    try:
                        mtime = replay_path.stat().st_mtime
                        # Only consider replays modified in the last 5 minutes
                        if mtime > time.time() - 300 and mtime > recent_time:
                            recent_time = mtime
                            recent_replay = replay_path
                    except OSError:
                        continue

            if not recent_replay:
                return

            # Build destination path
            result_str = str(game_result).upper()
            result_label = "win" if ("VICTORY" in result_str or "WIN" in result_str) else "loss"

            opp_race = "Unknown"
            try:
                if hasattr(self, 'enemy_race') and self.enemy_race:
                    opp_race = str(self.enemy_race).replace("Race.", "")
            except Exception:
                pass

            date_str = time.strftime("%Y-%m-%d")
            timestamp_str = time.strftime("%H%M%S")

            dest_dir = Path(__file__).parent / "logs" / "replays" / date_str
            dest_dir.mkdir(parents=True, exist_ok=True)

            dest_name = f"{opp_race}_{result_label}_{timestamp_str}.SC2Replay"
            dest_path = dest_dir / dest_name

            shutil.copy2(str(recent_replay), str(dest_path))
            print(f"[REPLAY] Organized replay: {dest_path}")

        except Exception as e:
            # Never crash the bot
            print(f"[REPLAY_WARN] Replay organization failed (non-critical): {e}")

    # =========================================================================
    # Feature 85: Build Order Timing Log
    # =========================================================================
    def _track_build_order(self) -> None:
        """Track key building/upgrade completions with game time."""
        if not hasattr(self, 'structures'):
            return

        # Key structures to track
        key_structures = {
            "SPAWNINGPOOL", "LAIR", "HIVE", "ROACHWARREN", "BANELINGNEST",
            "HYDRALISKDEN", "SPIRE", "GREATERSPIRE", "INFESTATIONPIT",
            "ULTRALISKCAVERN", "LURKERDENMP", "EVOLUTIONCHAMBER",
            "NYDUSNETWORK", "EXTRACTOR", "HATCHERY",
        }

        game_time = getattr(self, 'time', 0.0)

        for structure in self.structures:
            try:
                if structure.tag in self._tracked_structure_tags:
                    continue
                if not structure.is_ready:
                    continue

                struct_name = structure.type_id.name.upper()

                if struct_name in key_structures:
                    self._tracked_structure_tags.add(structure.tag)
                    self._build_order_log.append({
                        "structure": struct_name,
                        "game_time_seconds": round(game_time, 1),
                        "game_time_formatted": f"{int(game_time // 60)}:{int(game_time % 60):02d}",
                        "position": {"x": round(structure.position.x, 1), "y": round(structure.position.y, 1)},
                    })

                    # Track expansions
                    if struct_name == "HATCHERY":
                        self._expansions_built = getattr(self, '_expansions_built', 0) + 1

            except Exception:
                continue

    def _save_build_order_log(self) -> None:
        """Save build order log to JSON at game end."""
        if not self._build_order_log:
            return

        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        game_id = getattr(self, 'game_count', 0)
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filepath = logs_dir / f"build_order_{game_id}_{timestamp_str}.json"

        build_data = {
            "game_id": game_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "build_order": self._build_order_log,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(build_data, f, indent=2, ensure_ascii=False)

        print(f"[BUILD_ORDER] Saved {len(self._build_order_log)} entries to {filepath.name}")

    # =========================================================================
    # Feature 86: Unit Lost Tracking
    # =========================================================================
    async def on_unit_destroyed(self, unit_tag: int):
        """Track which of our units died, what type, and when."""
        try:
            # Check if the destroyed unit was one of ours by checking known tags
            # The bot framework calls this for ALL destroyed units, so we need to
            # filter for our own units only.
            game_time = getattr(self, 'time', 0.0)

            # Try to find unit info from our cached data
            unit_info = None
            if hasattr(self, '_known_unit_tags') and unit_tag in self._known_unit_tags:
                unit_info = self._known_unit_tags[unit_tag]

            # If we don't have cached info, try to identify if it was ours
            # by checking if the tag was in our previous units
            if unit_info is None:
                # Fallback: we can't determine unit type without caching
                # but we still record the tag loss
                return

            self._units_lost.append({
                "unit_type": unit_info.get("type", "UNKNOWN"),
                "game_time_seconds": round(game_time, 1),
                "game_time_formatted": f"{int(game_time // 60)}:{int(game_time % 60):02d}",
                "position": unit_info.get("position", None),
            })
        except Exception:
            pass

    def _reset_all_managers(self):
        """★ 게임 간 전체 매니저 상태 초기화 (훈련 에피소드 안정성 확보) ★"""
        reset_targets = [
            ("unit_authority", "UnitAuthority"),
            ("combat", "CombatManager"),
            ("strategy_manager", "StrategyManager"),
            ("economy", "EconomyManager"),
            ("personality", "Personality"),
            ("defeat_detection", "DefeatDetection"),
            ("defense_coordinator", "DefenseCoordinator"),
            ("overlord_safety", "OverlordSafety"),
            ("micro_v3", "MicroController"),
        ]
        for attr, name in reset_targets:
            mgr = getattr(self, attr, None)
            if mgr and hasattr(mgr, "reset"):
                try:
                    mgr.reset()
                except Exception as e:
                    print(f"[RESET_WARN] {name}.reset() failed: {e}")

        # ★ 누적 가능한 dict/set/list 직접 초기화
        for attr in ["_step_integrator"]:
            if hasattr(self, attr):
                setattr(self, attr, None)

        # DataCacheManager 초기화
        if hasattr(self, "data_cache") and self.data_cache:
            if hasattr(self.data_cache, "cache"):
                self.data_cache.cache.clear()

        # ★ 로거 핸들러 누적 방지
        try:
            from utils.logger import reset_all_loggers
            reset_all_loggers()
        except Exception:
            pass

        print("[RESET] All managers reset for next episode")


# How to integrate into existing WickedZergBotPro class:
#
# 1. Integrate into existing class:
#    from bot_step_integration import BotStepIntegrator
#
#    class WickedZergBotPro(BotAI):
#        def __init__(self, ...):
#            ...
#            self._step_integrator = None
#
#        async def on_step(self, iteration: int):
#            if self._step_integrator is None:
#                self._step_integrator = BotStepIntegrator(self)
#            await self._step_integrator.on_step(iteration)
#
# 2. Or inherit this class:
#    class WickedZergBotPro(WickedZergBotProImpl):
#        # Additional methods...
