# -*- coding: utf-8 -*-
"""
Game Configuration - 중앙 설정 관리

모든 매직 넘버를 의미있는 상수로 정의하여:
- 파라미터 튜닝 용이
- A/B 테스트 가능
- 코드 가독성 향상
- 설정 변경 시 코드 수정 최소화

참고: LOGIC_IMPROVEMENT_REPORT.md - Section 5 (Magic Numbers)
"""

from typing import Dict, Any
import os


class GameConfig:
    """게임 설정 (기본값)"""

    # ========== 게임 단계 타이밍 ==========
    OPENING_PHASE_END = 180         # 3분 (오프닝 종료)
    EARLY_GAME_END = 360            # 6분 (초반 종료)
    MID_GAME_END = 720              # 12분 (중반 종료)

    # 빌드 오더 전환
    BUILD_ORDER_SWITCH_TIME = 300   # 5분 (Rule-based → RL 전환)

    # ========== 경제 설정 ==========

    # 드론 제한
    DRONE_LIMIT_PER_BASE = 20       # ★ OPTIMIZED: 16 → 20 (초과 포화) ★
    DRONE_LIMIT_PER_BASE_GAS = 26   # ★ OPTIMIZED: 22 → 26 (가스 포함) ★
    MIN_DRONES = 22                 # 최소 드론 수 (절대값)
    MAX_DRONES = 80                 # 최대 드론 수

    # 자원 임계값
    MINERAL_BANKING_THRESHOLD = 1000   # 미네랄 적체 기준
    MINERAL_OVERFLOW = 1500            # 미네랄 넘침 (확장 필요)
    MINERAL_CRITICAL = 2000            # 미네랄 심각 (긴급 소비)

    GAS_OVERFLOW_THRESHOLD = 500       # 가스 넘침
    GAS_CRITICAL = 1000                # 가스 심각 (테크/유닛 소비)

    # 자원 비율
    MINERAL_TO_GAS_RATIO = 2.0         # 미네랄:가스 = 2:1 목표

    # ========== 보급 관리 ==========

    # Overlord 생산 타이밍
    SUPPLY_BUFFER_OPENING = 6          # 초반 보급 여유분 (0-3분)
    SUPPLY_BUFFER_EARLY = 4            # 초반 보급 여유분 (3-6분)
    SUPPLY_BUFFER_MID = 3              # 중반 보급 여유분 (6분+)
    SUPPLY_BUFFER_HIGH_GAS = 10        # 가스 많을 때 여유분

    SUPPLY_CAP = 200                   # 최대 보급

    # ========== 확장 타이밍 ==========

    NATURAL_EXPANSION_TIMING = 17      # 자연 확장 보급 (17풀)
    THIRD_BASE_TIMING = 30             # 3멀티 보급
    FOURTH_BASE_TIMING = 44            # 4멀티 보급

    NATURAL_EXPANSION_TIME = 60        # 자연 확장 시간 (1분, 빠른 확장)

    # ========== 생산 설정 ==========

    # 가스 예비량
    MIN_GAS_RESERVE = 100              # 최소 가스 예비 (업그레이드용)
    TECH_GAS_RESERVE = 200             # 테크 전환용 가스 예비

    # 애벌레 압박
    LARVA_PRESSURE_THRESHOLD = 6       # 애벌레 부족 기준
    LARVA_CRITICAL = 3                 # 애벌레 심각 부족

    # ========== 방어 설정 ==========

    # 초반 방어 타이밍
    SPAWNING_POOL_SUPPLY_STANDARD = 13  # 표준 13풀
    SPAWNING_POOL_SUPPLY_RUSH = 12      # 러시 대응 12풀
    SPAWNING_POOL_TIMING = 95           # 시간 기반 (95초 = 1분 35초)

    # 초반 방어 병력 목표
    EARLY_ZERGLING_TARGET_2MIN = 4      # 2분 목표: 저글링 4
    EARLY_ZERGLING_TARGET_3MIN = 8      # 3분 목표: 저글링 8
    EARLY_QUEEN_TARGET = 2              # 퀸 2

    # 위협 감지 거리
    THREAT_DETECTION_RANGE = 25         # 기지 근처 위협 감지 거리

    # ========== 공격 전략 설정 ==========

    # 12풀 러시
    TWELVE_POOL_DRONE_LIMIT = 12
    TWELVE_POOL_ZERGLING_COUNT = 6

    # 맹독충 올인
    BANELING_BUST_DRONE_LIMIT = 13
    BANELING_BUST_GAS_TIMING = 13       # 13드론에 가스
    BANELING_BUST_POOL_TIMING = 12      # 12드론에 풀
    BANELING_BUST_COUNT = 8

    # 궤멸충 러시
    RAVAGER_RUSH_ROACH_COUNT = 4
    RAVAGER_RUSH_RAVAGER_COUNT = 3
    RAVAGER_RUSH_TIMING = 240           # 4분

    # 뮤탈 러시
    MUTALISK_RUSH_COUNT = 6
    MUTALISK_RUSH_TIMING = 300          # 5분

    # ========== 전투 설정 ==========

    # 교전 비율
    ENGAGE_ARMY_RATIO = 0.7             # 적 병력 70% 이상 시 교전
    RETREAT_ARMY_RATIO = 0.4            # 아군 병력 40% 이하 시 후퇴

    # 병력 비율
    TARGET_ARMY_RATIO = 0.5             # 목표 군대 비율 (50%)
    DRONE_ARMY_BALANCE_RATIO = 1.5      # 드론:군대 = 1.5:1

    # ========== 성능 최적화 ==========

    # 실행 간격 (iteration)
    INTEL_UPDATE_INTERVAL = 1           # 정보 수집 (매 프레임)
    ECONOMY_UPDATE_INTERVAL = 4         # 경제 (4프레임마다 = 0.17초)
    PRODUCTION_UPDATE_INTERVAL = 4      # 생산
    COMBAT_UPDATE_INTERVAL = 2          # 전투 (2프레임마다)
    MICRO_UPDATE_INTERVAL = 1           # 마이크로 (매 프레임)
    CREEP_UPDATE_INTERVAL = 22          # 점막 (22프레임 = 1초)
    TECH_UPDATE_INTERVAL = 50           # 테크 (50프레임 = 2초)

    # 캐시 TTL
    CACHE_TTL_SHORT = 0.5               # 짧은 캐시 (0.5초)
    CACHE_TTL_MEDIUM = 1.0              # 중간 캐시 (1초)
    CACHE_TTL_LONG = 2.0                # 긴 캐시 (2초)

    # ========== Creep Denial System (적 점막 제거) ==========

    # 감시군주 관리
    CREEP_DENIAL_MIN_OVERSEERS = 2          # 최소 감시군주 수 (ZvZ)
    CREEP_DENIAL_MIN_OVERSEERS_OTHER = 1    # 다른 종족전 최소 감시군주 수

    # 종양 탐지 및 기억
    CREEP_DENIAL_TUMOR_MEMORY_DURATION = 60.0   # 종양 위치 기억 시간 (초)
    CREEP_DENIAL_DETECTION_RADIUS = 11          # 감시군주 탐지 반경

    # 유닛 할당 및 공격
    CREEP_DENIAL_MAX_UNITS_PER_TUMOR = 3        # 종양당 최대 할당 유닛 수
    CREEP_DENIAL_ATTACK_UNIT_DISTANCE = 10      # 공격 유닛 근처 적 감지 거리
    CREEP_DENIAL_PATROL_DISTANCE = 3            # 순찰 목표 도달 거리

    # 자원 임계값
    CREEP_DENIAL_MIN_MINERALS = 50              # 감시군주 생산 최소 미네랄
    CREEP_DENIAL_MIN_GAS = 50                   # 감시군주 생산 최소 가스

    # 우선순위 계산
    CREEP_DENIAL_PRIORITY_DISTANCE_BONUS = 20   # 우선순위 지역 거리 보너스
    CREEP_DENIAL_BASE_DISTANCE_THRESHOLD = 15   # 기지 근처 거리 임계값
    CREEP_DENIAL_VISIBLE_TUMOR_BONUS = 10       # 보이는 종양 우선순위 보너스
    CREEP_DENIAL_RECENT_SIGHTING_BONUS = 30     # 최근 목격 시간 보너스

    # 업데이트 간격 (iterations)
    CREEP_DENIAL_PRIORITY_UPDATE_INTERVAL = 110     # 우선순위 지점 업데이트 (5초)
    CREEP_DENIAL_TUMOR_SCAN_INTERVAL = 22           # 종양 탐지 (1초)
    CREEP_DENIAL_OVERSEER_MANAGE_INTERVAL = 66      # 감시군주 관리 (3초)
    CREEP_DENIAL_ATTACK_DISPATCH_INTERVAL = 22      # 공격 유닛 파견 (1초)
    CREEP_DENIAL_CLEANUP_INTERVAL = 110             # 데이터 정리 (5초)

    # 후퇴 로직 (안전성)
    CREEP_DENIAL_RETREAT_ENEMY_DISTANCE = 12        # 후퇴 트리거 적 거리
    CREEP_DENIAL_MIN_HEALTH_PERCENT = 0.5           # 최소 체력 비율 (50%)

    # ========== Production System (생산 시스템) ==========

    # Smart Remax (순간 회전력)
    PRODUCTION_MAX_PER_FRAME_DEFAULT = 100      # 기본 프레임당 최대 생산 수
    PRODUCTION_MAX_PER_FRAME_EMERGENCY = 200    # 긴급 상황 시 (자원 넘침, 공격 후)
    PRODUCTION_UNLIMITED_REMAX = True           # True면 애벌레 수만큼 무제한 생산

    # 생산 우선순위
    PRODUCTION_PRIORITY_WORKER = 100
    PRODUCTION_PRIORITY_DEFENSE = 90
    PRODUCTION_PRIORITY_ARMY = 70
    PRODUCTION_PRIORITY_TECH = 50

    # ========== Active Scouting System (능동 정찰) ==========

    # 정찰 간격
    SCOUT_INTERVAL_DEFAULT = 560            # 기본 정찰 간격 (25초)
    SCOUT_INTERVAL_ALERT = 336              # 경고 모드 정찰 간격 (15초)
    SCOUT_INTEL_STALE_TIME = 30.0           # 정보 오래됨 판정 시간 (초)

    # 위치 재정찰
    SCOUT_LOCATION_REVISIT_TIME = 30.0      # 위치 재정찰 최소 간격 (초)

    # Changeling 관리
    SCOUT_CHANGELING_COOLDOWN = 30.0        # Changeling 재사용 대기시간 (초)

    # 성과 추적
    SCOUT_SUCCESS_RATE_TARGET = 0.8         # 목표 성공률 (80%)

    # ========== 디버그 설정 ==========

    DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # 로그 출력 간격
    LOG_INTERVAL_FREQUENT = 50          # 자주 (2초)
    LOG_INTERVAL_NORMAL = 100           # 보통 (4초)
    LOG_INTERVAL_RARE = 200             # 드물게 (8초)

    # ========== 학습 설정 ==========

    # RL 보상
    REWARD_WIN = 100.0
    REWARD_LOSS = -100.0
    REWARD_EARLY_DEFENSE_PENALTY = -2.0    # 초반 방어 실패 페널티
    REWARD_EARLY_DEFENSE_BONUS = 2.0       # 초반 방어 성공 보너스

    # 학습률
    LEARNING_RATE_DEFAULT = 0.001
    DISCOUNT_FACTOR = 0.95

    # ========== 설정 로드/저장 ==========

    @classmethod
    def load_from_dict(cls, config_dict: Dict[str, Any]):
        """딕셔너리에서 설정 로드"""
        for key, value in config_dict.items():
            if hasattr(cls, key):
                setattr(cls, key, value)

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return {
            key: value
            for key, value in vars(cls).items()
            if not key.startswith('_') and not callable(value)
        }

    @classmethod
    def load_from_file(cls, filepath: str):
        """파일에서 설정 로드 (JSON/YAML)"""
        import json

        if not os.path.exists(filepath):
            print(f"[CONFIG] Config file not found: {filepath}")
            return

        with open(filepath, 'r') as f:
            if filepath.endswith('.json'):
                config_dict = json.load(f)
            elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                try:
                    import yaml
                    config_dict = yaml.safe_load(f)
                except ImportError:
                    print("[CONFIG] PyYAML not installed, skipping YAML config")
                    return
            else:
                print(f"[CONFIG] Unsupported file format: {filepath}")
                return

        cls.load_from_dict(config_dict)
        print(f"[CONFIG] Loaded configuration from {filepath}")

    @classmethod
    def save_to_file(cls, filepath: str):
        """설정을 파일로 저장"""
        import json

        config_dict = cls.to_dict()

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)

        print(f"[CONFIG] Saved configuration to {filepath}")


# ========== 프리셋 설정 ==========

class AggressiveConfig(GameConfig):
    """공격적 설정"""
    DRONE_LIMIT_PER_BASE = 14           # 더 적은 드론
    SPAWNING_POOL_SUPPLY_STANDARD = 12  # 12풀 표준
    TARGET_ARMY_RATIO = 0.6             # 군대 비율 60%
    NATURAL_EXPANSION_TIMING = 20       # 늦은 확장


class EconomicConfig(GameConfig):
    """경제 중심 설정"""
    DRONE_LIMIT_PER_BASE = 18           # 더 많은 드론
    SPAWNING_POOL_SUPPLY_STANDARD = 15  # 15풀
    TARGET_ARMY_RATIO = 0.4             # 군대 비율 40%
    NATURAL_EXPANSION_TIMING = 15       # 빠른 확장


class SafeConfig(GameConfig):
    """안전한 설정 (방어 중심)"""
    SPAWNING_POOL_SUPPLY_STANDARD = 13  # 표준 13풀
    EARLY_ZERGLING_TARGET_2MIN = 6      # 2분: 저글링 6
    EARLY_ZERGLING_TARGET_3MIN = 12     # 3분: 저글링 12
    TARGET_ARMY_RATIO = 0.55            # 군대 비율 55%


# ========== 전역 인스턴스 ==========

# 기본 설정 사용
config = GameConfig()

# 환경 변수로 설정 변경 가능
CONFIG_PROFILE = os.environ.get("CONFIG_PROFILE", "default")

if CONFIG_PROFILE == "aggressive":
    config = AggressiveConfig()
elif CONFIG_PROFILE == "economic":
    config = EconomicConfig()
elif CONFIG_PROFILE == "safe":
    config = SafeConfig()

# 설정 파일 로드 (선택적)
CONFIG_FILE = os.environ.get("CONFIG_FILE")
if CONFIG_FILE:
    config.load_from_file(CONFIG_FILE)

print(f"[CONFIG] Using configuration profile: {CONFIG_PROFILE}")
print(f"[CONFIG] DEBUG_MODE: {config.DEBUG_MODE}")
