# -*- coding: utf-8 -*-
"""
Run bot with neural network training enabled.

This script starts a game and trains the neural network model in real-time.
Model will be saved to: local_training/models/zerg_net_model.pt
"""

import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from sc2 import maps  # type: ignore
from sc2.data import Difficulty, Race  # type: ignore
from sc2.main import run_game  # type: ignore
from sc2.player import Bot, Computer  # type: ignore
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro

logger = logging.getLogger(__name__)

# SC2 path auto-setup function


def _ensure_sc2_path():
    """
    Set SC2PATH environment variable - search via Windows Registry or common paths
    """
    # Skip Windows-specific discovery on non-Windows hosts (AI Arena runs on
    # Linux)
    if sys.platform != "win32":
        return

    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        versions_dir = os.path.join(sc2_path, "Versions")
        if os.path.exists(versions_dir):
            return

    # 1. Find StarCraft II installation path via Windows Registry
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Blizzard Entertainment\StarCraft II"
        )
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)

        if os.path.exists(install_path):
            os.environ["SC2PATH"] = install_path
            logger.info(f"[SC2] Found via Registry: {install_path}")
            return
    except Exception as e:
        logger.warning(f"[WARNING] Failed to read SC2 path from registry: {e}")

    # 2. Search common installation paths
    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]

    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            logger.info(f"[SC2] Found at common path: {path}")
            return

    logger.warning("[WARNING] SC2 installation not found automatically")


# Setup SC2 path before sc2 import
_ensure_sc2_path()

# Bot class import
sys.path.append(str(Path(__file__).parent))


def create_bot_with_training(
    learning_rate: Optional[float] = None, personality: str = "serral"
):
    """
    Create bot instance with neural network training enabled.
    Model will be saved to: local_training/models/zerg_net_model.pt
    """
    # CRITICAL: Set train_mode = True to enable neural network training
    bot_instance = WickedZergBotPro(
        train_mode=True, learning_rate=learning_rate, personality=personality
    )
    return Bot(Race.Zerg, bot_instance)


def main():
    """
    Main entry point for bot execution with training enabled.
    IMPROVED: Continuous training mode - games will run continuously without stopping.
    """
    logger.info("\n" + "=" * 70)
    logger.info("? NEURAL NETWORK TRAINING MODE (CONTINUOUS)")
    logger.info("=" * 70)
    logger.info("? Training Configuration:")
    logger.info("   ? 15-dimensional state vector (Self 5 + Enemy 10)")
    logger.info("   ? REINFORCE algorithm for policy learning")
    logger.info("   ? Model auto-saves after each game")
    logger.info("   ? Continuous training: Games run continuously without stopping")
    logger.info("   ? Build order comparison with pro gamer baseline")
    logger.info("   ? Auto-update learned parameters on victory")
    logger.info("? Model save location: local_training/models/zerg_net_model.pt")
    logger.info("? Build order data: local_training/scripts/learned_build_orders.json")
    logger.info("??  Press Ctrl+C to stop training")
    logger.info("=" * 70)
    # 1. Run on AI Arena server (when --LadderServer flag is present)
    if "--LadderServer" in sys.argv:
        from sc2.main import run_ladder_game  # type: ignore

        # Start Arena Monitoring Server
        arena_server_manager = None
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from monitoring.server_manager import start_arena_monitoring

            arena_server_manager = start_arena_monitoring(background=True)
            if arena_server_manager:
                logger.info("[OK] Arena monitoring server started")
                logger.info(f"     Server URL: {arena_server_manager.get_server_url()}")
                logger.info("     Mobile/Web Access: Available")
            else:
                logger.warning("[WARNING] Failed to start arena monitoring server")
        except Exception as e:
            logger.warning(f"[WARNING] Arena monitoring server not available: {e}")
            logger.info("[INFO] Continuing without monitoring server...")

        logger.info("\n[STEP 2] ? Connecting to AI Arena Server...")
        logger.info("=" * 70)
        bot = create_bot_with_training(
            personality="serral"
        )  # Ladder server doesn't support custom LR yet
        logger.info("[OK] Bot created with training enabled")
        logger.info("[INFO] Joining Ladder Game...")
        try:
            run_ladder_game(bot)
        finally:
            # Stop arena server when done
            if arena_server_manager:
                arena_server_manager.stop_server()
        return

    # 2. Check for checkpoint and auto-resume
    checkpoint_manager = None
    try:
        from utils.checkpoint_manager import CheckpointManager

        checkpoint_dir = Path(__file__).parent / "local_training" / "checkpoints"
        checkpoint_manager = CheckpointManager(checkpoint_dir)

        # Try to load latest checkpoint
        latest_checkpoint = checkpoint_manager.load_latest_checkpoint()
        if latest_checkpoint:
            logger.info("\n[CHECKPOINT] Found previous training checkpoint")
            logger.info(f"  Iteration: {latest_checkpoint['iteration']}")
            logger.info(f"  Timestamp: {latest_checkpoint['timestamp']}")
            logger.info("[INFO] Auto-resuming from checkpoint...")
            # Checkpoint data will be used when creating bot
    except Exception as e:
        logger.warning(f"[WARNING] Checkpoint manager not available: {e}")
        checkpoint_manager = None

    # 2. Run on local machine for continuous training
    logger.info("\n[STEP 2] ? Initializing Continuous Training Loop...")
    logger.info("=" * 70)

    # Start Local Monitoring Server
    local_server_manager = None
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from monitoring.server_manager import start_local_monitoring

        local_server_manager = start_local_monitoring(background=True)
        if local_server_manager:
            logger.info("[OK] Local monitoring server started")
            logger.info(f"     Server URL: {local_server_manager.get_server_url()}")
            logger.info("     Mobile/Web Access: Available")
            logger.info(f"     Web UI: {local_server_manager.get_server_url()}/ui")
            logger.info(f"     API Docs: {local_server_manager.get_server_url()}/docs")
        else:
            logger.warning("[WARNING] Failed to start local monitoring server")
    except Exception as e:
        logger.warning(f"[WARNING] Monitoring server not available: {e}")
        logger.info("[INFO] Continuing without monitoring server...")

    # Initialize Training Session Manager
    try:
        from tools.training_session_manager import TrainingSessionManager

        session_manager = TrainingSessionManager()
        logger.info("[OK] Training session manager initialized")
    except ImportError as e:
        logger.warning(f"[WARNING] Training session manager not available: {e}")
        session_manager = None

    # Initialize Background Parallel Learner (NEW: Experience Replay System)
    background_learner = None
    try:
        from tools.background_parallel_learner import BackgroundParallelLearner

        background_learner = BackgroundParallelLearner(
            max_workers=1,  # 단일 모델 업데이트이므로 1개면 충분
            enable_replay_analysis=False,  # sc2reader 리플레이 분석 비활성화
            enable_model_training=True,  # 경험 데이터 기반 학습 활성화
        )
        background_learner.start()
        logger.info("[OK] Background parallel learner initialized and started")
        logger.info("[INFO] Experience replay training will run in background")
        logger.info(f"[INFO] Monitoring directory: {background_learner.data_dir}")
    except ImportError as e:
        logger.warning(f"[WARNING] Background parallel learner not available: {e}")
    except Exception as e:
        logger.warning(f"[WARNING] Failed to start background learner: {e}")

    # Initialize Auto Replay Learner (NEW: Learn from pro replays)
    auto_replay_learner = None
    try:
        from tools.auto_replay_learner import AutoReplayLearner

        auto_replay_learner = AutoReplayLearner()
        logger.info("[OK] Auto replay learner initialized")
        logger.info("[INFO] Will automatically download and learn from pro replays")
        logger.info("[INFO] Replay learning every 10 games")
    except ImportError as e:
        logger.warning(f"[WARNING] Auto replay learner not available: {e}")
    except Exception as e:
        logger.warning(f"[WARNING] Failed to initialize auto replay learner: {e}")

    game_count = 0
    max_consecutive_failures = 5
    consecutive_failures = 0

    # Available maps
    available_maps = [
        "AbyssalReefLE",
        "BelShirVestigeLE",
        "CactusValleyLE",
        "HonorgroundsLE",
        "ProximaStationLE",
    ]
    opponent_races = [Race.Terran, Race.Protoss, Race.Zerg]
    # IMPROVED: Start with easier difficulties to improve win rate
    # Current win rate: 0.00% (0/221 games) - need easier difficulty
    # Progression: Easy -> Medium -> Hard -> VeryHard (gradual increase)
    difficulties = [Difficulty.Easy, Difficulty.Medium]  # Changed from Hard/VeryHard

    logger.info(f"[INFO] Available maps: {len(available_maps)} maps")
    logger.info(f"[INFO] Available opponent races: {len(opponent_races)} races")
    logger.info(f"[INFO] Available difficulties: {len(difficulties)} levels")
    logger.info("[OK] Continuous training loop initialized")
    logger.info("[INFO] Game windows will open - you can watch the games in real-time!")
    logger.info("[INFO] Neural network is learning from your gameplay...")
    logger.info("=" * 70)
    # Parse max games from arguments
    max_games = float("inf")
    for i, arg in enumerate(sys.argv):
        if arg == "--max_games":
            try:
                max_games = int(sys.argv[i + 1])
                logger.info(f"[CONFIG] Max games set to: {max_games}")
            except (IndexError, ValueError) as e:
                logger.warning(f"[WARNING] Invalid --max_games argument: {e}")

    # Parse learning rate from arguments
    learning_rate = None
    for i, arg in enumerate(sys.argv):
        if arg == "--learning_rate" or arg == "--lr":
            try:
                learning_rate = float(sys.argv[i + 1])
                logger.info(f"[CONFIG] Learning Rate manually set to: {learning_rate}")
            except (IndexError, ValueError) as e:
                logger.warning(f"[WARNING] Invalid --learning_rate argument: {e}")

    # Parse opponent race filter (--race zerg/protoss/terran/all)
    opponent_race_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--race" or arg == "--opponent_race":
            try:
                race_str = sys.argv[i + 1].lower()
                if race_str == "zerg":
                    opponent_race_filter = [Race.Zerg]
                    logger.info("[CONFIG] Opponent race filter: Zerg only (ZvZ)")
                elif race_str == "protoss":
                    opponent_race_filter = [Race.Protoss]
                    logger.info("[CONFIG] Opponent race filter: Protoss only (ZvP)")
                elif race_str == "terran":
                    opponent_race_filter = [Race.Terran]
                    logger.info("[CONFIG] Opponent race filter: Terran only (ZvT)")
                elif race_str == "all":
                    opponent_race_filter = None
                    logger.info("[CONFIG] Opponent race filter: All races")
                else:
                    logger.warning(
                        f"[WARNING] Unknown race '{race_str}'. Using all races."
                    )
            except (IndexError, ValueError) as e:
                logger.warning(f"[WARNING] Invalid --race argument: {e}")

    # Parse personality (--personality serral/maru/dark/silent)
    personality_setting = "serral"  # Default
    for i, arg in enumerate(sys.argv):
        if arg == "--personality":
            try:
                personality_setting = sys.argv[i + 1].lower()
                logger.info(f"[CONFIG] Bot Personality set to: {personality_setting}")
            except IndexError:
                logger.warning("[WARNING] Missing value for --personality")

    while True:
        try:
            if game_count >= max_games:
                logger.info(
                    f"\n[INFO] Reached maximum number of games ({max_games}). Stopping training."
                )
                break

            game_count += 1

            if consecutive_failures > 0:
                logger.info(
                    f"\n??  [RETRY] Current consecutive failures: {consecutive_failures}/{max_consecutive_failures}"
                )
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(
                        f"? [ERROR] Too many consecutive failures ({consecutive_failures}). Stopping training."
                    )
                    break

            # [STEP 3] Select random map, opponent race, and adaptive difficulty
            logger.info(f"\n{'='*70}")
            logger.info(f"? [STEP 3] GAME #{game_count} - Random Selection")
            logger.info("=" * 70)

            # IMPROVED: Random Map Selection with Retry
            # Try up to 3 times to find a valid map
            map_name = "AbyssalReefLE"  # Default fallback

            # Expanded map pool (including newer and standard maps)
            extended_maps = [
                "AbyssalReefLE",
                "BelShirVestigeLE",
                "CactusValleyLE",
                "ProximaStationLE",
                "NewRepugnancyLE",
                "AcropolisLE",
                "DiscoBloodbathLE",
                "EphemeronLE",
                "TritonLE",
                "WintersGateLE",
                "WorldofSleepersLE",
                "ThunderbirdLE",
                "AutomatonLE",
                "PortAleksanderLE",
                "CyberForestLE",
                "KairosJunctionLE",
                "KingsCoveLE",
                "YearZeroLE",
            ]

            # Combine ensuring uniqueness
            all_maps = list(set(available_maps + extended_maps))

            # Try to pick a map that exists
            for _ in range(3):
                candidate = random.choice(all_maps)
                try:
                    if maps.get(candidate) is not None:
                        map_name = candidate
                        break
                except Exception:
                    continue

            # IMPROVED: Bag of Races (Ensure variety) with --race filter support
            if opponent_race_filter is not None:
                # Filtered mode: only use specified races
                if not hasattr(main, "race_bag") or not main.race_bag:
                    main.race_bag = list(opponent_race_filter)
                    random.shuffle(main.race_bag)
                    logger.info(
                        f"[RACE_LOGIC] Filtered race bag: {[r.name for r in main.race_bag]}"
                    )
            else:
                # Default: all races
                if not hasattr(main, "race_bag") or not main.race_bag:
                    main.race_bag = [Race.Terran, Race.Protoss, Race.Zerg]
                    random.shuffle(main.race_bag)
                    logger.info(
                        f"[RACE_LOGIC] Refilled race bag: {[r.name for r in main.race_bag]}"
                    )

            # Pick from bag
            opponent_race = main.race_bag.pop()

            # IMPROVED: Use adaptive difficulty from session manager
            if session_manager:
                recommended_difficulty_str = session_manager.get_adaptive_difficulty()
                # Convert string to Difficulty enum
                if recommended_difficulty_str == "VeryHard":
                    difficulty = Difficulty.VeryHard
                elif recommended_difficulty_str == "Hard":
                    difficulty = Difficulty.Hard
                elif recommended_difficulty_str == "Medium":
                    difficulty = Difficulty.Medium
                elif recommended_difficulty_str == "Easy":
                    difficulty = Difficulty.Easy
                else:
                    # Fallback to random choice from difficulties list
                    difficulty = random.choice(difficulties)
                logger.info(
                    f"[ADAPTIVE] Recommended difficulty: {recommended_difficulty_str} "
                    f"(based on {session_manager.session_stats.win_rate:.1f}% win rate)"
                )
            else:
                # No session manager: use random choice from difficulties list (Easy/Medium)
                difficulty = random.choice(difficulties)

            logger.info(f"[SELECTED] Map: {map_name}")
            logger.info(f"[SELECTED] Opponent Race: {opponent_race.name}")
            logger.info(f"[SELECTED] Difficulty: {difficulty.name}")
            logger.info("[INFO] Starting game...")
            logger.info("=" * 70)
            # Create new bot instance for each game
            bot = create_bot_with_training(
                learning_rate=learning_rate, personality=personality_setting
            )
            # bot is already a Bot instance, so we can set attributes on the
            # underlying AI
            if hasattr(bot, "ai") and bot.ai:
                bot.ai.game_count = game_count  # Track game count

            # Run game with error handling
            try:
                map_instance = maps.get(map_name)
                if map_instance is None:
                    logger.info(
                        f"[WARNING] Map '{map_name}' not found, using default: AbyssalReefLE"
                    )
                    map_name = "AbyssalReefLE"
                    map_instance = maps.get(map_name)

                if map_instance is None:
                    logger.error("[ERROR] Default map not found. Skipping this game.")
                    consecutive_failures += 1
                    time.sleep(5)
                    continue

                # CRITICAL: bot is already a Bot instance from create_bot_with_training()
                # DO NOT wrap it again with Bot() - it will cause AssertionError
                # bot = Bot(Race.Zerg, bot) # WRONG - causes error
                # bot is already a Bot instance, use it directly
                run_game(
                    map_instance,
                    [
                        bot,
                        # CORRECT: Use bot directly (already a Bot instance)
                        Computer(opponent_race, difficulty),
                    ],
                    realtime=False,  # False = faster speed (no visible game window)
                )

                # Game completed successfully
                consecutive_failures = 0
                if session_manager:
                    session_manager.reset_error_count()

                # IMPROVED: Get game result from bot (wait for on_end to complete)
                # Wait a moment for on_end() to complete and store
                # _training_result
                import time as time_module

                # Small delay to ensure on_end() completes
                time_module.sleep(0.5)

                game_result_str = "Unknown"
                game_time = 0.0
                build_order_score = None
                loss_reason = None
                parameters_updated = 0

                if hasattr(bot, "ai") and bot.ai:
                    # CRITICAL: Get training result from on_end() if available
                    if hasattr(bot.ai, "_training_result"):
                        result = bot.ai._training_result
                        game_result_str = result.get("game_result", "Unknown")
                        game_time = result.get("game_time", 0.0)
                        build_order_score = result.get("build_order_score")
                        loss_reason = result.get("loss_reason")
                        parameters_updated = result.get("parameters_updated", 0)
                        logger.info(
                            f"[INFO] Retrieved training result: {game_result_str}, "
                            f"Time: {game_time:.1f}s, Score: {build_order_score}, "
                            f"Params: {parameters_updated}"
                        )
                    else:
                        # Fallback: Try to get from bot attributes
                        if hasattr(bot.ai, "last_result"):
                            game_result_str = str(bot.ai.last_result)
                        if hasattr(bot.ai, "time"):
                            game_time = float(bot.ai.time)
                        logger.info(
                            "[WARNING] _training_result not found, using fallback values"
                        )

                # Record game result in session manager
                if session_manager:
                    try:
                        logger.info(
                            f"[TRAINING] Recording game result: Game #{game_count}, Result: {game_result_str}, Time: {game_time:.1f}s"
                        )
                        session_manager.record_game_result(
                            game_id=game_count,
                            map_name=map_name,
                            opponent_race=opponent_race.name,
                            difficulty=difficulty.name,
                            result=game_result_str,
                            game_time=game_time,
                            build_order_score=build_order_score,
                            loss_reason=loss_reason,
                            parameters_updated=parameters_updated,
                        )
                        logger.info("[TRAINING] Game result recorded successfully")
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to record game result: {e}")
                        import traceback

                        traceback.print_exc()

                logger.info(f"\n{'='*70}")
                logger.info(f"? [GAME #{game_count}] COMPLETED SUCCESSFULLY")
                logger.info("=" * 70)
                logger.info("[INFO] Neural network model saved")
                logger.info(
                    "[INFO] Build order comparison analysis will be displayed above"
                )
                # IMPROVED: Longer wait time between games to ensure SC2 client
                # fully closes
                wait_between_games = 10  # Increased from 3 to 10 seconds
                logger.info(
                    f"[NEXT] Automatically starting next game in {wait_between_games} seconds..."
                )
                logger.info(
                    "[INFO] Waiting for SC2 client to fully close before next game"
                )
                logger.info("=" * 70)

                # IMPROVED: Check if SC2 processes are still running before
                # next game
                try:
                    import psutil

                    for _ in range(wait_between_games):
                        sc2_running = False
                        for proc in psutil.process_iter(["pid", "name"]):
                            try:
                                proc_name = proc.info["name"].lower()
                                if "sc2" in proc_name or "starcraft" in proc_name:
                                    sc2_running = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                        if not sc2_running:
                            # SC2 processes closed, can proceed
                            break

                        time.sleep(1)
                        # Force kill if still running (Windows only)
                        logger.warning(
                            "[WARNING] SC2 process stuck. Forcing termination..."
                        )
                        try:
                            import subprocess

                            if sys.platform == "win32":
                                subprocess.call(
                                    ["taskkill", "/F", "/IM", "SC2_x64.exe"],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                                subprocess.call(
                                    ["taskkill", "/F", "/IM", "StarCraft II.exe"],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                            else:
                                subprocess.call(
                                    ["pkill", "-f", "SC2_x64"],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                        except Exception:
                            pass
                except (ImportError, Exception):
                    # Fallback: try to kill SC2, then sleep
                    try:
                        import subprocess

                        if sys.platform == "win32":
                            subprocess.call(
                                ["taskkill", "/F", "/IM", "SC2_x64.exe"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                        else:
                            subprocess.call(
                                ["pkill", "-f", "SC2_x64"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                    except Exception:
                        pass
                    time.sleep(wait_between_games)

                # IMPROVED: Print background learning stats periodically
                if background_learner and game_count % 5 == 0:
                    stats = background_learner.get_stats()
                    logger.info(f"\n{'='*70}")
                    logger.info("? [BACKGROUND LEARNING] STATISTICS")
                    logger.info("=" * 70)
                    logger.info(
                        f"Experience Files Processed: {stats['files_processed']}"
                    )
                    logger.info(f"Batch Training Runs: {stats['batches_trained']}")
                    logger.info(f"Total Training Samples: {stats['total_samples']}")
                    logger.info(f"Average Loss: {stats['avg_loss']:.4f}")
                    logger.info(
                        f"Total Processing Time: {stats['total_processing_time']:.2f}s"
                    )
                    logger.info(
                        f"Active Workers: {stats['active_workers']}/{stats['max_workers']}"
                    )
                    logger.info(f"Errors: {stats['errors']}")
                    logger.info("=" * 70)
                # ★ NEW: Auto Replay Learning (every 10 games) ★
                if auto_replay_learner and game_count % 10 == 0:
                    logger.info(f"\n{'='*70}")
                    logger.info(
                        "🎮 [AUTO REPLAY LEARNING] Downloading and learning from pro replays..."
                    )
                    logger.info("=" * 70)
                    try:
                        # 3개 리플레이 다운로드, 각 5회 학습
                        auto_replay_learner.run_auto_learning_cycle(
                            num_replays=3, learning_iterations=5, min_mmr=4000
                        )
                        logger.info(
                            "[AUTO_REPLAY] [OK] Replay learning cycle completed"
                        )
                    except Exception as replay_error:
                        logger.info(
                            f"[AUTO_REPLAY] [FAILED] Replay learning failed: {replay_error}"
                        )
                        import traceback

                        traceback.print_exc()
                    logger.info("=" * 70)
            except Exception as game_error:
                consecutive_failures += 1

                # ★ CRITICAL FIX: Save experience data even when game fails ★
                logger.info(
                    "\n[RECOVERY] Attempting to save experience data from failed game..."
                )
                try:
                    if (
                        hasattr(bot, "ai")
                        and bot.ai
                        and hasattr(bot.ai, "rl_agent")
                        and bot.ai.rl_agent
                    ):
                        # Try to save whatever experience data was collected before failure
                        bot.ai.rl_agent.end_episode(
                            final_reward=-10.0, save_experience=True
                        )
                        logger.info(
                            f"[RECOVERY] [OK] Successfully saved experience data from failed game #{game_count}"
                        )
                    else:
                        logger.info(
                            "[RECOVERY] [FAILED] No RLAgent found - cannot save experience data"
                        )
                except Exception as save_error:
                    logger.info(
                        f"[RECOVERY] [FAILED] Failed to save experience data: {save_error}"
                    )
                    import traceback

                    traceback.print_exc()

                # IMPROVED: Record error in session manager
                if session_manager:
                    error_type = type(game_error).__name__
                    error_message = str(game_error)
                    session_manager.record_error(error_type, error_message)

                # IMPROVED: Handle connection errors with longer wait time
                error_msg = str(game_error).lower()
                is_connection_error = (
                    "connection" in error_msg
                    or "connectionalreadyclosed" in error_msg
                    or "websocket" in error_msg
                    or "closing transport" in error_msg
                )

                if is_connection_error:
                    wait_time = 15  # Longer wait for connection errors
                    logger.error(
                        f"\n[ERROR] Game #{game_count} failed: Connection error"
                    )
                    logger.error(
                        "[ERROR] StarCraft II client connection was closed unexpectedly"
                    )
                    logger.info("[INFO] This usually happens when:")
                    logger.info("   - Previous game session didn't fully close")
                    logger.info("   - SC2 client crashed or was terminated")
                    logger.info("   - Network/WebSocket connection was interrupted")
                    logger.info(
                        f"[RETRY] Waiting {wait_time} seconds for SC2 client to fully close..."
                    )
                    logger.info(
                        "[INFO] Please ensure no SC2 game windows are still open"
                    )
                else:
                    wait_time = 10  # Standard wait for other errors
                    logger.error(f"\n[ERROR] Game #{game_count} failed: {game_error}")
                    logger.info(f"[RETRY] Will retry after {wait_time} seconds...")

                import traceback

                traceback.print_exc()
                time.sleep(wait_time)

                # IMPROVED: Try to check if SC2 processes are still running
                try:
                    import psutil

                    sc2_processes = []
                    for proc in psutil.process_iter(["pid", "name"]):
                        try:
                            proc_name = proc.info["name"].lower()
                            if "sc2" in proc_name or "starcraft" in proc_name:
                                sc2_processes.append(proc.info["pid"])
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    if sc2_processes:
                        logger.info(
                            f"[WARNING] Found {len(sc2_processes)} SC2 process(es) still running"
                        )
                        logger.info(
                            "[INFO] Waiting additional 5 seconds for processes to close..."
                        )
                        time.sleep(5)
                except ImportError:
                    # psutil not available, skip process check
                    pass
                except Exception as proc_error:
                    # Process check failed, continue anyway
                    logger.info(
                        f"[WARNING] Could not check SC2 processes: {proc_error}"
                    )

                continue
        except KeyboardInterrupt:
            logger.info("\n[STOP] Training stopped by user.")

            # ★ MANUAL FEEDBACK FOR INTERRUPTED GAME ★
            try:
                logger.info("\n" + "=" * 50)
                logger.info("MANUAL TERMINATION DETECTED")
                logger.info("=" * 50)
                feedback = (
                    input("Did you stop the game to record a result? (y/n): ")
                    .strip()
                    .lower()
                )

                if feedback == "y":
                    result_input = input("Result (win/loss/tie): ").strip().lower()
                    if "w" in result_input:
                        game_result_str = "Victory"
                    elif "l" in result_input:
                        game_result_str = "Defeat"
                    else:
                        game_result_str = "Tie"

                    reason = input("Reason/Notes for termination: ").strip()

                    if session_manager:
                        session_manager.record_game_result(
                            game_id=game_count,
                            map_name=map_name,
                            opponent_race=opponent_race.name,
                            difficulty=difficulty.name,
                            result=game_result_str,
                            game_time=0.0,  # Unknown time
                            build_order_score=0,
                            loss_reason=f"Manual: {reason}",
                            parameters_updated=0,
                        )
                        logger.info(
                            f"[MANUAL] Recorded result: {game_result_str} ({reason})"
                        )
            except Exception:
                pass

            # Stop local monitoring server on interrupt
            if local_server_manager:
                logger.info("[INFO] Stopping local monitoring server...")
                local_server_manager.stop_server()
            break
        except Exception as e:
            consecutive_failures += 1

            # IMPROVED: Record error in session manager
            if session_manager:
                error_type = type(e).__name__
                error_message = str(e)
                session_manager.record_error(error_type, error_message)

            logger.error(f"\n[ERROR] Unexpected error in training loop: {e}")
            logger.info("[RETRY] Will retry after 5 seconds...")
            import traceback

            traceback.print_exc()
            time.sleep(5)
            continue

    # IMPROVED: Stop background learner before exiting
    if background_learner:
        logger.info("\n[INFO] Stopping background parallel learner...")
        background_learner.stop()
        stats = background_learner.get_stats()
        logger.info("[BACKGROUND LEARNER] Final stats:")
        logger.info(f"  - Experience Files Processed: {stats['files_processed']}")
        logger.info(f"  - Batch Training Runs: {stats['batches_trained']}")
        logger.info(f"  - Total Training Samples: {stats['total_samples']}")
        logger.info(f"  - Average Loss: {stats['avg_loss']:.4f}")
        logger.info(f"  - Total Processing Time: {stats['total_processing_time']:.2f}s")
        logger.info(f"  - Errors: {stats['errors']}")

    # Stop local monitoring server
    if local_server_manager:
        logger.info("\n[INFO] Stopping local monitoring server...")
        local_server_manager.stop_server()

    # IMPROVED: Print final training summary
    logger.info("=" * 70)
    logger.info("TRAINING STOPPED")
    logger.info("=" * 70)
    logger.info(f"Total games completed: {game_count}")
    logger.info("Model saved to: local_training/models/zerg_net_model.pt")
    logger.info("You can now use this trained model in future games!")

    if session_manager:
        logger.info(session_manager.get_training_summary())

    logger.info("=" * 70)

    # ? NEW: Auto-extract and learn from training data after training ends
    # NOTE: Disabled due to missing TrainingDataExtractor module (2026-01-25)
    if False and game_count > 0:
        logger.info("\n" + "=" * 70)
        logger.info("AUTO-EXTRACTING AND LEARNING FROM TRAINING DATA")
        logger.info("=" * 70)
        try:
            # Import extractor module - add parent directory to path
            script_dir = Path(__file__).parent
            if str(script_dir) not in sys.path:
                sys.path.insert(0, str(script_dir))

            from tools.extract_and_train_from_training import TrainingDataExtractor

            extractor = TrainingDataExtractor()

            # Extract data
            logger.info("\n[STEP 1] Extracting training data...")
            training_data = extractor.extract_training_stats()
            comparisons = extractor.extract_build_order_comparisons()
            session_stats = extractor.extract_session_stats()

            if training_data or comparisons:
                # Analyze data
                logger.info("\n[STEP 2] Analyzing training data...")
                analysis = extractor.analyze_training_data(training_data)

                # Learn from data
                logger.info("\n[STEP 3] Learning from training data...")
                learned_params = extractor.learn_from_training_data(
                    training_data, comparisons, learning_rate=0.1
                )

                # Save extracted data
                logger.info("\n[STEP 4] Saving extracted data...")
                extractor.save_extracted_data(
                    training_data, comparisons, analysis, learned_params
                )

                # Generate and print report
                logger.info("\n[STEP 5] Generating report...")
                report = extractor.generate_report(analysis, learned_params)
                logger.info("\n" + report)

                # Save report
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = extractor.output_dir / f"report_{timestamp}.txt"
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"\n[SAVED] Report: {report_file}")

                logger.info("\n" + "=" * 70)
                logger.info("EXTRACTION AND LEARNING COMPLETE")
                logger.info("=" * 70)
            else:
                logger.info(
                    "[INFO] No training data found to extract. Skipping extraction."
                )
        except Exception as e:
            logger.info(
                f"\n[WARNING] Failed to extract and learn from training data: {e}"
            )
            logger.info(
                "[INFO] You can manually run: python -m wicked_zerg_challenger.tools.extract_and_train_from_training"
            )
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
