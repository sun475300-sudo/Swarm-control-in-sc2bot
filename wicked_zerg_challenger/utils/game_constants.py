# -*- coding: utf-8 -*-
"""
Game Constants - SC2 게임 상수 정의

목적:
1. Magic numbers 제거
2. 일관된 타이밍 관리
3. 쉬운 튜닝 및 밸런싱
"""

# ============================================================================
# GAME TIMING FREQUENCIES (Iteration-based)
# SC2 runs at 22.4 frames per second (real-time)
# ============================================================================

class GameFrequencies:
    """프레임 기반 실행 주기 상수"""

    # Base timing
    GAME_FPS = 22  # Approximate SC2 FPS

    # Sub-second timings
    EVERY_HALF_SECOND = 11      # ~0.5초마다
    EVERY_SECOND = 22           # ~1초마다
    EVERY_1_5_SECONDS = 33      # ~1.5초마다
    EVERY_2_SECONDS = 44        # ~2초마다
    EVERY_3_SECONDS = 66        # ~3초마다
    EVERY_4_SECONDS = 88        # ~4초마다
    EVERY_5_SECONDS = 110       # ~5초마다

    # Multi-second timings
    EVERY_10_SECONDS = 220      # ~10초마다
    EVERY_15_SECONDS = 330      # ~15초마다
    EVERY_30_SECONDS = 660      # ~30초마다
    EVERY_45_SECONDS = 990      # ~45초마다
    EVERY_60_SECONDS = 1320     # ~60초마다 (1분)

    # Minute-based timings
    EVERY_2_MINUTES = 2640      # ~2분마다
    EVERY_3_MINUTES = 3960      # ~3분마다
    EVERY_5_MINUTES = 6600      # ~5분마다


# ============================================================================
# ECONOMIC CONSTANTS
# ============================================================================

class EconomyConstants:
    """경제 관련 상수"""

    # Worker saturation
    OPTIMAL_WORKERS_PER_BASE = 16  # 미네랄 8개 * 2 = 16명
    OPTIMAL_WORKERS_PER_GAS = 3     # 가스당 최적 일꾼 3명
    MAX_WORKERS_PER_BASE = 24       # 과포화 최대값

    # Gas timing
    GAS_RESERVE_THRESHOLD = 100     # 가스 비축 임계값
    GAS_WORKER_TRANSITION = 75      # 가스→미네랄 전환 임계값

    # Expansion timing
    EXPANSION_COOLDOWN = 6.0        # 확장 쿨다운 (초)
    EXPANSION_MINERAL_THRESHOLD = 400  # 확장 시작 미네랄

    # Resource banking prevention
    MAX_MINERAL_BANK = 1000         # 최대 비축 미네랄
    MAX_GAS_BANK = 1000             # 최대 비축 가스


# ============================================================================
# COMBAT CONSTANTS
# ============================================================================

class CombatConstants:
    """전투 관련 상수"""

    # Health thresholds
    BURROW_HP_THRESHOLD = 0.4       # 잠복 체력 (40%)
    RETREAT_HP_THRESHOLD = 0.3      # 후퇴 체력 (30%)
    FULL_HP_THRESHOLD = 0.8         # 완전 회복 체력 (80%)
    TRANSFUSION_HP_THRESHOLD = 0.6  # 수혈 대상 체력 (60%)

    # Distance thresholds
    DETECTOR_THREAT_RANGE = 15      # 디텍터 위협 거리
    RETREAT_DISTANCE = 20           # 후퇴 안전 거리
    MELEE_RANGE = 2                 # 근접 사거리
    BASE_DEFENSE_RANGE = 30         # 기지 방어 범위

    # Army composition
    MIN_ARMY_FOR_ATTACK = 6         # 공격 최소 병력
    MIN_ROACH_FOR_RUSH = 20         # Roach Rush 최소 병력
    MAX_QUEENS_PER_BASE = 2         # 기지당 최대 여왕

    # Combat timings
    ROACH_RUSH_TIMING = 360         # Roach Rush 타이밍 (초)
    DEFENSE_CHECK_INTERVAL = 33     # 방어 체크 주기 (1.5초)


# ============================================================================
# UPGRADE CONSTANTS
# ============================================================================

class UpgradeConstants:
    """업그레이드 관련 상수"""

    # Cooldowns (초 단위)
    INJECT_COOLDOWN = 29.0          # Spawn Larva 쿨다운 (정확한 SC2 값)
    TRANSFUSION_COOLDOWN = 1.0      # 수혈 쿨다운
    CREEP_SPREAD_COOLDOWN = 4.0     # 점막 확산 쿨다운

    # Energy thresholds
    INJECT_ENERGY_THRESHOLD = 25    # Inject 에너지
    TRANSFUSION_ENERGY = 50         # 수혈 에너지
    CREEP_ENERGY_THRESHOLD = 20     # 점막 에너지

    # Distances
    MAX_INJECT_DISTANCE = 4.0       # Inject 최대 거리
    MAX_QUEEN_TRAVEL_DISTANCE = 10.0  # 여왕 이동 거리
    TRANSFUSION_RANGE = 7           # 수혈 사거리


# ============================================================================
# STRATEGIC CONSTANTS
# ============================================================================

class StrategyConstants:
    """전략 관련 상수"""

    # Scouting timing (초 단위)
    INITIAL_SCOUT_TIME = 30         # 첫 정찰 시간
    SCOUT_INTERVAL = 60             # 정찰 주기
    OVERLORD_SCOUT_TIME = 120       # 대군주 정찰 시간

    # Build order timing
    POOL_TIMING = 24                # 산란못 타이밍 (인구수)
    GAS_TIMING = 17                 # 가스 타이밍 (인구수)
    LAIR_TIMING = 240               # 레어 업그레이드 타이밍 (초)

    # Supply management
    SUPPLY_BUFFER = 2               # 보급 버퍼
    OVERLORD_TIMING_THRESHOLD = 2   # 대군주 생산 시점


# ============================================================================
# UNIT PRIORITIES
# ============================================================================

class UnitPriority:
    """유닛 우선순위 가중치"""

    # Transfusion priorities (낮을수록 우선)
    QUEEN = -0.5
    ULTRALISK = -0.3
    BROODLORD = -0.3
    RAVAGER = -0.2
    ROACH = -0.1
    ZERGLING = 0.0

    # Production priorities
    SUPPLY = 100
    ARMY = 50
    WORKERS = 30
    TECH = 20


# ============================================================================
# ABILITY CONSTANTS
# ============================================================================

class AbilityConstants:
    """스킬 사용 관련 상수"""

    # Ravager
    CORROSIVE_BILE_RANGE = 9
    CORROSIVE_BILE_RADIUS = 2

    # Infestor
    FUNGAL_GROWTH_RANGE = 10
    FUNGAL_GROWTH_RADIUS = 2.5
    FUNGAL_ENERGY = 75

    # Viper
    ABDUCT_RANGE = 9
    BLINDING_CLOUD_RANGE = 11
    PARASITIC_BOMB_RANGE = 8


# ============================================================================
# DEBUG CONSTANTS
# ============================================================================

class DebugConstants:
    """디버깅 관련 상수"""

    LOG_INTERVAL = 220              # 로그 출력 주기 (10초)
    STAT_REPORT_INTERVAL = 1320     # 통계 보고 주기 (60초)
    ERROR_LOG_THROTTLE = 200        # 에러 로그 제한 (200 프레임)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def seconds_to_iterations(seconds: float) -> int:
    """초를 프레임(iteration)으로 변환"""
    return int(seconds * GameFrequencies.GAME_FPS)


def iterations_to_seconds(iterations: int) -> float:
    """프레임(iteration)을 초로 변환"""
    return iterations / GameFrequencies.GAME_FPS


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
# Before:
if iteration % 22 == 0:  # What does 22 mean?
    check_something()

# After:
from utils.game_constants import GameFrequencies

if iteration % GameFrequencies.EVERY_SECOND == 0:
    check_something()
"""
