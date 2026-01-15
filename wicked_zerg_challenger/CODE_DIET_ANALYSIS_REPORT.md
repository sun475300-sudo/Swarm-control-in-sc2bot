======================================================================
CODE DIET ANALYSIS REPORT
======================================================================

Found 67 files with potentially unused imports:

COMPLETE_RUN_SCRIPT.py:
  - loguru.logger
  - wicked_zerg_bot_pro.WickedZergBotPro
  - sc2.data.Race
  - sc2.data.Difficulty
  - sc2.main.run_game
  - sc2.player.Bot
  - sc2.player.Computer
  - sc2.maps

chat_manager.py:
  - chat_manager_utf8.ChatManager

combat_manager.py:
  - traceback
  - config.TARGET_PRIORITY
  - config.Config
  - config.GamePhase
  - sc2.data.Race
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.position.Point2
  - sc2.unit.Unit
  - sc2.ids.upgrade_id.UpgradeId
  - wicked_zerg_bot_pro.WickedZergBotPro
  - personality_manager.ChatPriority

config.py:
  - dataclasses.dataclass
  - enum.Enum
  - enum.auto
  - sc2.ids.unit_typeid.UnitTypeId
  - loguru.logger

economy_manager.py:
  - config.Config
  - sc2.bot_ai.BotAI
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.ids.upgrade_id.UpgradeId
  - sc2.position.Point2
  - config.get_learned_parameter

genai_self_healing.py:
  - dataclasses.dataclass
  - dataclasses.asdict
  - google.generativeai
  - loguru.logger
  - tools.load_api_key.get_gemini_api_key

intel_manager.py:
  - dataclasses.dataclass
  - dataclasses.field
  - enum.Enum
  - enum.IntEnum
  - enum.auto
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.position.Point2
  - sc2.unit.Unit
  - sc2.ids.upgrade_id.UpgradeId
  - wicked_zerg_bot_pro.WickedZergBotPro
  - config.TARGET_PRIORITY

local_training\build_order_learner.py:
  - dataclasses.dataclass
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.ids.ability_id.AbilityId

local_training\combat_tactics.py:
  - sc2.data.Race
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - config.Config

local_training\curriculum_manager.py:
  - sc2.data.Difficulty

local_training\main_integrated.py:
  - subprocess
  - sc2.maps
  - sc2.main.run_game
  - sc2.data.Difficulty
  - sc2.data.Race
  - sc2.data.Result
  - sc2.player.Bot
  - sc2.player.Computer
  - curriculum_manager.CurriculumManager
  - wicked_zerg_bot_pro.WickedZergBotPro
  - loguru.logger
  - multiprocessing
  - config.Config
  - shutil
  - multiprocessing
  - tools.optimize_code.remove_korean_comments
  - local_training.strategy_audit.StrategyAudit
  - scripts.replay_build_order_learner.ReplayBuildOrderExtractor
  - replay_quality_analyzer.ReplayQualityAnalyzer
  - self_evolution.run_self_evolution
  - google.protobuf.pyext._message
  - tools.download_and_train.ReplayDownloader
  - scripts.replay_build_order_learner.ReplayBuildOrderExtractor
  - extract_replay_insights.analyze_latest_replay
  - local_training.strategy_audit.StrategyAudit

local_training\production_resilience.py:
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - loguru.logger

local_training\scripts\move_completed_replays.py:
  - replay_learning_manager.ReplayLearningTracker
  - learning_status_manager.LearningStatusManager

local_training\scripts\parallel_train_integrated.py:
  - config.Config
  - google.protobuf.pyext._message

local_training\scripts\replay_build_order_learner.py:
  - loguru.logger
  - local_training.strategy_audit.StrategyAudit
  - strategy_database.StrategyType
  - strategy_database.MatchupType
  - replay_learning_manager.ReplayLearningTracker
  - strategy_database.StrategyDatabase
  - strategy_database.StrategyType
  - strategy_database.MatchupType
  - replay_crash_handler.ReplayCrashHandler
  - learning_status_manager.LearningStatusManager

local_training\scripts\replay_learning_manager.py:
  - enum.Enum

local_training\scripts\replay_learning_tracker_sqlite.py:
  - enum.Enum

local_training\scripts\replay_quality_filter.py:
  - hashlib

local_training\scripts\run_hybrid_supervised.py:
  - __future__.annotations
  - hybrid_learning.HybridTrainer

local_training\scripts\strategy_database.py:
  - dataclasses.dataclass
  - dataclasses.asdict
  - enum.Enum

local_training\strategy_audit.py:
  - dataclasses.dataclass
  - dataclasses.asdict
  - loguru.logger

micro_controller.py:
  - dataclasses.dataclass
  - sc2.position.Point2
  - sc2.position.Point3
  - sc2.unit.Unit
  - sc2.units.Units

monitoring\bot_api_connector.py:
  - dataclasses.dataclass
  - sc2.ids.unit_typeid.UnitTypeId

monitoring\dashboard.py:
  - socket
  - hashlib
  - base64
  - glob.glob
  - monitoring_utils.get_base_dir
  - monitoring_utils.load_json
  - monitoring_utils.find_latest_instance_status
  - monitoring_utils.load_training_stats

monitoring\dashboard_api.py:
  - fastapi.FastAPI
  - fastapi.WebSocket
  - fastapi.HTTPException
  - fastapi.Depends
  - fastapi.status
  - fastapi.middleware.cors.CORSMiddleware
  - fastapi.security.HTTPBasic
  - fastapi.security.HTTPBasicCredentials
  - fastapi.responses.JSONResponse
  - fastapi.responses.HTMLResponse
  - fastapi.responses.FileResponse
  - glob.glob
  - starlette.responses.JSONResponse
  - monitoring_utils.get_base_dir
  - monitoring_utils.load_json
  - monitoring_utils.find_latest_instance_status
  - monitoring_utils.load_training_stats
  - bot_api_connector.bot_connector

monitoring\manus_sync.py:
  - monitoring.manus_dashboard_client.create_client_from_env
  - monitoring.monitoring_utils.get_base_dir
  - monitoring.monitoring_utils.find_latest_instance_status

monitoring\monitoring_utils.py:
  - __future__.annotations

monitoring\ngrok_tunnel.py:
  - tools.load_api_key.load_api_key

monitoring\start_with_ngrok.py:
  - signal
  - monitoring.ngrok_tunnel.NgrokTunnel

monitoring\telemetry_logger.py:
  - sc2.data.Result
  - sc2.ids.unit_typeid.UnitTypeId

monitoring\telemetry_logger_atomic.py:
  - tempfile
  - telemetry_logger.TelemetryLogger

production_manager.py:
  - config.COUNTER_BUILD
  - config.Config
  - config.EnemyRace
  - config.GamePhase
  - config.get_learned_parameter
  - unit_factory.UnitFactory
  - sc2.data.Race
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.ids.upgrade_id.UpgradeId
  - sc2.position.Point2
  - wicked_zerg_bot_pro.WickedZergBotPro
  - personality_manager.ChatPriority
  - loguru.logger
  - local_training.personality_manager.ChatPriority

queen_manager.py:
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.buff_id.BuffId
  - sc2.ids.unit_typeid.UnitTypeId

rogue_tactics_manager.py:
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.ids.upgrade_id.UpgradeId
  - sc2.position.Point2
  - sc2.unit.Unit
  - wicked_zerg_bot_pro.WickedZergBotPro

run.py:
  - wicked_zerg_bot_pro.WickedZergBotPro
  - sc2.data.Race
  - sc2.data.Difficulty
  - sc2.main.run_game
  - sc2.player.Bot
  - sc2.player.Computer
  - sc2.maps
  - sc2.main.run_ladder_game

sc2_env\__init__.py:
  - mock_env.MockSC2Env
  - mock_env.MockBotAI
  - mock_env.MockGameState
  - mock_env.Race
  - mock_env.MockUnit

sc2_env\mock_env.py:
  - dataclasses.dataclass
  - dataclasses.field
  - enum.Enum

scouting_system.py:
  - dataclasses.dataclass
  - sc2.bot_ai.BotAI
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.position.Point2
  - config.THREAT_BUILDINGS
  - config.Config
  - config.EnemyRace
  - config.GamePhase

services\hybrid_config.py:
  - dataclasses.dataclass

services\learning_service_client.py:
  - hybrid_config.get_config

services\service_registry.py:
  - dataclasses.dataclass
  - dataclasses.asdict
  - hybrid_config.get_config

services\telemetry_service_client.py:
  - hybrid_config.get_config

spell_unit_manager.py:
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - sc2.position.Point2
  - sc2.unit.Unit
  - wicked_zerg_bot_pro.WickedZergBotPro

telemetry_logger.py:
  - sc2.data.Result
  - sc2.ids.unit_typeid.UnitTypeId
  - monitoring.manus_dashboard_client.create_client_from_env

tools\analyze_and_cleanup.py:
  - re

tools\analyze_telemetry.py:
  - pandas

tools\api_key_usage_limiter.py:
  - time

tools\arena_update.py:
  - package_for_aiarena.AIArenaPackager

tools\background_parallel_learner.py:
  - dataclasses.dataclass
  - queue.Queue
  - queue.Empty
  - local_training.scripts.replay_build_order_learner.ReplayBuildOrderExtractor
  - zerg_net.ZergNet
  - zerg_net.ReinforcementLearner

tools\build_order_comparator.py:
  - dataclasses.dataclass

tools\check_all_api_keys.py:
  - tools.load_api_key.get_gemini_api_key
  - tools.load_api_key.get_google_api_key
  - tools.load_api_key.get_gcp_project_id
  - tools.load_api_key.load_api_key

tools\check_api_key.py:
  - tools.load_api_key.get_gemini_api_key
  - tools.load_api_key.get_google_api_key

tools\code_diet_analyzer.py:
  - re

tools\compare_pro_vs_training_replays.py:
  - local_training.scripts.replay_build_order_learner.ReplayBuildOrderExtractor
  - tools.build_order_comparator.BuildOrderComparator

tools\download_and_train.py:
  - __future__.annotations
  - re
  - local_training.scripts.replay_quality_filter.ReplayQualityFilter
  - local_training.scripts.strategy_database.StrategyDatabase
  - local_training.scripts.strategy_database.StrategyType
  - local_training.scripts.strategy_database.MatchupType

tools\extract_and_train_from_training.py:
  - tools.build_order_comparator.BuildOrderComparator
  - tools.training_session_manager.TrainingSessionManager

tools\fix_all_encoding_issues.py:
  - codecs

tools\generate_pwa_icons.py:
  - PIL.Image
  - PIL.ImageDraw
  - PIL.ImageFont
  - PIL.Image
  - PIL.ImageDraw
  - PIL.ImageFont

tools\generate_readme.py:
  - textwrap.dedent

tools\integrated_pipeline.py:
  - scripts.replay_learning_manager.ReplayLearningTracker

tools\replay_lifecycle_manager.py:
  - replay_learning_manager.ReplayLearningTracker
  - learning_status_manager.LearningStatusManager

tools\runtime_check.py:
  - __future__.annotations

tools\training_session_manager.py:
  - dataclasses.dataclass
  - dataclasses.asdict

tools\validate_arena_deployment.py:
  - sc2.bot_ai.BotAI
  - sc2.data.Race
  - sc2.player.Bot
  - wicked_zerg_bot_pro.WickedZergBotPro
  - zerg_net.ZergNet
  - zerg_net.ReinforcementLearner
  - numpy
  - config.Config
  - wicked_zerg_bot_pro.WickedZergBotPro
  - sc2.player.Bot
  - sc2.data.Race
  - sc2.main.run_ladder_game

unit_factory.py:
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - config.EnemyRace
  - config.GamePhase
  - loguru.logger

wicked_zerg_bot_pro.py:
  - io
  - combat_manager.CombatManager
  - config.Config
  - config.EnemyRace
  - config.GamePhase
  - economy_manager.EconomyManager
  - intel_manager.IntelManager
  - rogue_tactics_manager.RogueTacticsManager
  - production_manager.ProductionManager
  - production_resilience.ProductionResilience
  - queen_manager.QueenManager
  - scouting_system.ScoutingSystem
  - telemetry_logger.TelemetryLogger
  - sc2.bot_ai.BotAI
  - sc2.data.Race
  - sc2.data.Result
  - sc2.ids.ability_id.AbilityId
  - sc2.ids.unit_typeid.UnitTypeId
  - numpy
  - combat_tactics.CombatTactics
  - micro_controller.MicroController
  - personality_manager.PersonalityManager
  - strategy_analyzer.StrategyAnalyzer
  - bot_api_connector.bot_connector
  - genai_self_healing.GenAISelfHealing
  - genai_self_healing.init_self_healing
  - debug_visualizer.DebugVisualizer
  - zerg_net.Action
  - zerg_net.ReinforcementLearner
  - zerg_net.ZergNet
  - spell_unit_manager.SpellUnitManager
  - sc2.ids.buff_id.BuffId
  - loguru.logger
  - local_training.combat_tactics.CombatTactics
  - local_training.personality_manager.PersonalityManager
  - build_order_comparator.BuildOrderComparator
  - local_training.strategy_audit.analyze_bot_performance
  - tools.training_session_manager.TrainingSessionManager
  - tools.training_session_manager.TrainingSessionManager
  - local_training.strategy_audit.StrategyAudit

zerg_net.py:
  - enum.Enum
  - numpy
  - multiprocessing

Total unused imports: 318

======================================================================
RECOMMENDATIONS
======================================================================
1. Review unused imports - some may be used indirectly
2. Remove confirmed unused imports
3. Consider using tools like 'autoflake' or 'unimport' for automated cleanup
======================================================================