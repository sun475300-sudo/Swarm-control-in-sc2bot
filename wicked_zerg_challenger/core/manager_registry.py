#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manager Registry - 모든 매니저 설정 중앙 관리

기존 650줄의 초기화 코드를 선언적 설정으로 변경
"""

from core.manager_factory import ManagerConfig, ManagerPriority


def get_all_manager_configs():
    """
    모든 매니저 설정 반환

    Returns:
        List[ManagerConfig]: 매니저 설정 리스트
    """
    return [
        # ========== CRITICAL SYSTEMS (실패 시 봇 중단) ==========

        ManagerConfig(
            name="Blackboard",
            module_path="blackboard",
            class_name="Blackboard",
            attribute_name="blackboard",
            priority=ManagerPriority.CRITICAL,
        ),

        ManagerConfig(
            name="UnitAuthorityManager",
            module_path="unit_authority_manager",
            class_name="UnitAuthorityManager",
            attribute_name="unit_authority",
            priority=ManagerPriority.CRITICAL,
        ),

        # ========== HIGH PRIORITY (핵심 시스템) ==========

        ManagerConfig(
            name="ProductionResilience",
            module_path="local_training.production_resilience",
            class_name="ProductionResilience",
            attribute_name="production",
            priority=ManagerPriority.HIGH,
            dependencies=["blackboard"],
        ),

        ManagerConfig(
            name="EconomyManager",
            module_path="economy_manager",
            class_name="EconomyManager",
            attribute_name="economy",
            priority=ManagerPriority.HIGH,
        ),

        ManagerConfig(
            name="CombatManager",
            module_path="combat_manager",
            class_name="CombatManager",
            attribute_name="combat",
            priority=ManagerPriority.HIGH,
        ),

        ManagerConfig(
            name="IntelManager",
            module_path="intel_manager",
            class_name="IntelManager",
            attribute_name="intel",
            priority=ManagerPriority.HIGH,
            post_init=lambda bot, manager: manager.load_data(),
        ),

        ManagerConfig(
            name="ScoutingSystem",
            module_path="scouting_system",
            class_name="ScoutingSystem",
            attribute_name="scout",
            priority=ManagerPriority.HIGH,
        ),

        ManagerConfig(
            name="StrategyManager",
            module_path="strategy_manager",
            class_name="StrategyManager",
            attribute_name="strategy_manager",
            priority=ManagerPriority.HIGH,
            post_init=lambda bot, manager: setattr(manager, "blackboard", getattr(bot, "blackboard", None)),
        ),

        ManagerConfig(
            name="DefenseCoordinator",
            module_path="defense_coordinator",
            class_name="DefenseCoordinator",
            attribute_name="defense_coordinator",
            priority=ManagerPriority.HIGH,
            dependencies=["blackboard"],
            post_init=lambda bot, manager: setattr(manager, "blackboard", getattr(bot, "blackboard", None)),
        ),

        # ========== MEDIUM PRIORITY (일반 시스템) ==========

        ManagerConfig(
            name="★ AdvancedWorkerOptimizer",
            module_path="advanced_worker_optimizer",
            class_name="AdvancedWorkerOptimizer",
            attribute_name="worker_optimizer",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="★ IdleUnitManager",
            module_path="idle_unit_manager",
            class_name="IdleUnitManager",
            attribute_name="idle_units",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="★ CombatPhaseController",
            module_path="combat_phase_controller",
            class_name="CombatPhaseController",
            attribute_name="combat_phase",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="PerformanceOptimizer",
            module_path="local_training.performance_optimizer",
            class_name="PerformanceOptimizer",
            attribute_name="performance_optimizer",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="PID FormationController",
            module_path="utils.pid_controller",
            class_name="FormationController",
            attribute_name="formation_controller",
            priority=ManagerPriority.MEDIUM,
            # FormationController는 인자를 받지 않음
        ),

        ManagerConfig(
            name="RogueTacticsManager",
            module_path="rogue_tactics_manager",
            class_name="RogueTacticsManager",
            attribute_name="rogue_tactics",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="UpgradeManager",
            module_path="upgrade_manager",
            class_name="UpgradeManager",
            attribute_name="upgrade_manager",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="QueenManager",
            module_path="queen_manager",
            class_name="QueenManager",
            attribute_name="queen_manager",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="OverlordSafetyManager",
            module_path="overlord_safety_manager",
            class_name="OverlordSafetyManager",
            attribute_name="overlord_safety",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="★ ActiveScoutingSystem",
            module_path="active_scouting_system",
            class_name="ActiveScoutingSystem",
            attribute_name="active_scout",
            priority=ManagerPriority.MEDIUM,
        ),

        ManagerConfig(
            name="★ CreepDenialSystem",
            module_path="creep_denial_system",
            class_name="CreepDenialSystem",
            attribute_name="creep_denial",
            priority=ManagerPriority.MEDIUM,
            dependencies=["unit_authority"],
            post_init=lambda bot, manager: setattr(manager, "unit_authority", bot.unit_authority),
        ),

        # ========== LOW PRIORITY (선택적 시스템) ==========

        ManagerConfig(
            name="★ OpponentModeling",
            module_path="opponent_modeling",
            class_name="OpponentModeling",
            attribute_name="opponent_modeling",
            priority=ManagerPriority.LOW,
            dependencies=["intel"],
        ),

        ManagerConfig(
            name="★ AdvancedMicroControllerV3",
            module_path="advanced_micro_controller_v3",
            class_name="AdvancedMicroControllerV3",
            attribute_name="micro_v3",  # Fixed: code accesses bot.micro_v3
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="MicroController",
            module_path="micro_controller",
            class_name="MicroController",
            attribute_name="micro",  # Fixed: code accesses bot.micro
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="SpellUnitManager",
            module_path="spell_unit_manager",
            class_name="SpellUnitManager",
            attribute_name="spell_manager",  # Fixed: bot_step_integration uses "spell_manager"
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="AggressiveStrategies",
            module_path="aggressive_strategies",
            class_name="AggressiveStrategies",
            attribute_name="aggressive_strategies",
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="HiveTechMaximizer",
            module_path="hive_tech_maximizer",
            class_name="HiveTechMaximizer",
            attribute_name="hive_tech",
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="CreepExpansion",
            module_path="creep_expansion_system",
            class_name="CreepExpansionSystem",
            attribute_name="creep_expansion",
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="★ BattlePreparationSystem",
            module_path="battle_preparation_system",
            class_name="BattlePreparationSystem",
            attribute_name="battle_prep",
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="★ BuildingDestroyer",
            module_path="building_destroyer",
            class_name="BuildingDestroyer",
            attribute_name="building_destroyer",
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="CreepHighwayManager",
            module_path="creep_highway_manager",
            class_name="CreepHighwayManager",
            attribute_name="creep_highway",
            priority=ManagerPriority.LOW,
        ),

        ManagerConfig(
            name="RuntimeSelfHealing",
            module_path="runtime_self_healing",
            class_name="RuntimeSelfHealing",
            attribute_name="self_healing",
            priority=ManagerPriority.LOW,
        ),

        # NOTE: BotStepIntegrator는 on_start에서 수동으로 초기화됨 (_step_integrator)
        # ManagerConfig(
        #     name="★ BotStepIntegrator",
        #     module_path="bot_step_integration",
        #     class_name="BotStepIntegrator",
        #     attribute_name="step_integrator",
        #     priority=ManagerPriority.LOW,
        #     dependencies=["blackboard"],
        # ),

        # ========== OPTIONAL (완전 선택적) ==========

        ManagerConfig(
            name="DataCache",
            module_path="data_cache_manager",
            class_name="DataCacheManager",
            attribute_name="data_cache",
            priority=ManagerPriority.OPTIONAL,
        ),

        ManagerConfig(
            name="UnitFactory",
            module_path="unit_factory",
            class_name="UnitFactory",
            attribute_name="unit_factory",
            priority=ManagerPriority.OPTIONAL,
            dependencies=["blackboard"],
        ),

        ManagerConfig(
            name="ProductionController",
            module_path="production_controller",
            class_name="ProductionController",
            attribute_name="production_controller",
            priority=ManagerPriority.OPTIONAL,
            dependencies=["blackboard"],
        ),
    ]


def get_minimal_manager_configs():
    """
    최소 매니저 설정 (빠른 테스트용)

    Returns:
        List[ManagerConfig]: 최소 매니저 설정 리스트
    """
    return [
        config for config in get_all_manager_configs()
        if config.priority <= ManagerPriority.HIGH
    ]
