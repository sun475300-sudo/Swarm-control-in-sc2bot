# -*- coding: utf-8 -*-
"""
Combat Manager Initialization Module

전투 매니저 초기화를 담당하는 모듈
"""

from utils.logger import get_logger


def initialize_combat_state(manager):
    """
    전투 매니저의 초기 상태를 설정

    Args:
        manager: CombatManager 인스턴스
    """
    manager.logger = get_logger("CombatManager")
    manager.targeting = None
    manager.micro_combat = None
    manager.boids = None

    # Air unit micro state
    manager._air_harass_target = None
    manager._last_air_harass_time = 0
    manager._air_harass_cooldown = 30  # 30 seconds between harass decisions

    # === MULTITASKING SYSTEM ===
    # Task priorities (higher = more important)
    manager.task_priorities = {
        "base_defense": 100,      # Defend our base - HIGHEST PRIORITY
        "worker_defense": 90,     # Protect workers
        "counter_attack": 70,     # Attack enemy attackers
        "air_harass": 60,         # Air unit harassment
        "scout": 50,              # Scouting
        "main_attack": 40,        # Main army attack
        "creep_spread": 30,       # Creep spreading
    }

    # Active tasks and assigned units
    manager._active_tasks = {}  # task_name -> {"units": set(), "target": position}
    manager._unit_assignments = {}  # unit_tag -> task_name

    # Task cooldowns
    manager._task_cooldowns = {}

    # === COUNTER ATTACK SYSTEM ===
    manager._last_combat_time = 0  # Track when last combat occurred
    manager._counter_attack_cooldown = 15  # 15 seconds cooldown between counter attacks

    # === RALLY POINT SYSTEM ===
    # Rally point for army units to gather before attacking
    manager._rally_point = None
    manager._last_rally_update = 0
    manager._rally_update_interval = 30  # Update rally point every 30 seconds
    manager._min_army_for_attack = 6  # ★ OPTIMIZED: 8 → 6 (더 빠른 공격) ★
    manager._early_game_min_attack = 3  # ★ OPTIMIZED: 4 → 3 (더 빠른 초반 압박) ★

    # === ★★★ ROACH RUSH TIMING ATTACK ★★★ ===
    manager._roach_rush_active = False
    manager._roach_rush_timing = 360  # 6:00 (6분)
    manager._roach_rush_min_count = 12  # 최소 12 바퀴
    manager._roach_rush_sent = False

    # === ★ ARMY UNITS CACHE (per-frame) ★ ===
    manager._cached_army = None
    manager._cached_army_frame = -1

    # === ★ MANDATORY BASE DEFENSE SYSTEM ★ ===
    manager._base_defense_active = False
    manager._defense_rally_point = None

    # === ★ Creep Denial System (New) ★ ===
    try:
        from combat.creep_denial_system import CreepDenialSystem
        manager.creep_denial = CreepDenialSystem(manager.bot)
        manager.logger.info("CreepDenialSystem initialized")
    except ImportError as e:
        manager.logger.warning(f"CreepDenialSystem import failed: {e}")
        manager.creep_denial = None

    manager._last_defense_check = 0
    manager._defense_check_interval = 3  # ★ OPTIMIZED: 5 → 3 (더 빠른 반응) ★
    manager._worker_defense_threshold = 1  # ★ FIX: 적 1기라도 일꾼 근처 위협 시 방어 ★
    manager._critical_defense_threshold = 8  # 적 8기 이상이면 모든 유닛 방어

    # === ★★★ VICTORY CONDITION TRACKING ★★★ ===
    manager._victory_push_active = False  # 승리 푸시 모드
    manager._last_enemy_structure_count = 0  # 마지막으로 본 적 건물 수
    manager._enemy_structures_destroyed = 0  # 파괴한 적 건물 수
    manager._last_victory_check = 0  # 마지막 승리 조건 체크 시간
    manager._victory_check_interval = 110  # 승리 조건 체크 주기 (약 5초)
    manager._endgame_push_threshold = 360  # 6분 이후 승리 푸시 가능
    manager._known_enemy_expansions = set()  # 발견한 적 확장 위치
    manager._last_expansion_check = 0  # 마지막 확장 체크 시간

    # === ★★★ EXPANSION DEFENSE SYSTEM ★★★ ===
    manager._expansion_under_attack = {}  # 확장 기지 tag -> 공격 시작 시간
    manager._expansion_destroyed_positions = []  # 파괴된 확장 기지 위치
    manager._last_expansion_defense_check = 0
    manager._expansion_defense_check_interval = 10  # 10프레임마다 확장 방어 체크
    manager._expansion_defense_force_size = 8  # 확장 방어에 투입할 최소 유닛 수

    # === ★★★ Phase 17: PERFORMANCE OPTIMIZATION - FRAME SKIP ★★★ ===
    manager._last_combat_frame = 0  # 마지막 전투 로직 실행 프레임
    manager._combat_frame_skip = 4  # 4프레임마다 실행 (약 0.18초)
    manager._combat_emergency_skip = 1  # 긴급 상황에서는 매 프레임
    manager._combat_is_emergency = False  # 긴급 상황 여부
    manager._last_emergency_check = 0  # 마지막 긴급 상황 체크


def initialize_managers(manager):
    """
    전투 관련 매니저들을 초기화

    Args:
        manager: CombatManager 인스턴스
    """
    try:
        from combat.targeting import Targeting
        manager.targeting = Targeting(manager.bot)
    except ImportError:
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Targeting system not available")

    try:
        from combat.micro_combat import MicroCombat
        manager.micro_combat = MicroCombat(manager.bot)
    except ImportError:
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Micro combat not available")

    try:
        from combat.boids_swarm_control import BoidsSwarmController
        manager.boids = BoidsSwarmController()
    except ImportError:
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Boids controller not available")

    # ★ Formation Manager (Concave + Choke Control) ★
    try:
        from combat.formation_manager import FormationManager
        manager.formation_manager = FormationManager(manager.bot)
    except ImportError:
        manager.formation_manager = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Formation manager not available")

    # ★ NEW: Mutalisk Micro Controller (Regen Dance + Magic Box) ★
    try:
        from combat.mutalisk_micro import MutaliskMicroController
        manager.mutalisk_micro = MutaliskMicroController()
    except ImportError:
        manager.mutalisk_micro = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Mutalisk micro controller not available")

    # ★ NEW: Baneling Tactics Controller (Land Mines) ★
    try:
        from combat.baneling_tactics import BanelingTacticsController
        manager.baneling_tactics = BanelingTacticsController()
    except ImportError:
        manager.baneling_tactics = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Baneling tactics controller not available")

    # ★ NEW: Overlord Transport (대군주 수송) ★
    try:
        from combat.overlord_transport import OverlordTransport
        manager.overlord_transport = OverlordTransport(manager.bot)
    except ImportError:
        manager.overlord_transport = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Overlord transport not available")

    # ★ NEW: Roach Burrow Heal (바퀴 잠복 회복) ★
    try:
        from combat.roach_burrow_heal import RoachBurrowHeal
        manager.roach_burrow_heal = RoachBurrowHeal(manager.bot)
    except ImportError:
        manager.roach_burrow_heal = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Roach burrow heal not available")

    # ★★★ Phase 19: Lurker Ambush System ★★★
    try:
        from combat.lurker_ambush import LurkerAmbushSystem
        manager.lurker_ambush = LurkerAmbushSystem(manager.bot)
    except ImportError:
        manager.lurker_ambush = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Lurker ambush system not available")

    # ★★★ Phase 19: Smart Consume System ★★★
    try:
        from combat.smart_consume import SmartConsumeSystem
        manager.smart_consume = SmartConsumeSystem(manager.bot)
    except ImportError:
        manager.smart_consume = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Smart consume system not available")

    # ★★★ Phase 20: Overlord Hunter ★★★
    try:
        from combat.overlord_hunter import OverlordHunter
        manager.overlord_hunter = OverlordHunter(manager.bot)
    except ImportError:
        manager.overlord_hunter = None
        if hasattr(manager.bot, 'iteration') and manager.bot.iteration % 500 == 0:
            manager.logger.warning("Overlord hunter not available")
