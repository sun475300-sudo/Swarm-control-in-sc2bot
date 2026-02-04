"""
Unit Configuration - 유닛별 전술 파라미터

하드코딩된 매직 넘버를 설정으로 중앙화합니다.
"""


class CombatConfig:
    """전투 관련 설정"""

    # 최소 공격 병력
    MIN_ARMY_FOR_ATTACK = 6
    MIN_MUTALISK_FOR_HARASS = 3
    MIN_ROACH_FOR_TIMING = 8

    # 방어 체크 간격 및 임계값
    DEFENSE_CHECK_INTERVAL = 3  # 프레임
    DEFENSE_THREAT_THRESHOLD = 1  # 최소 적 유닛 수
    DEFENSE_RADIUS = 8  # 방어 범위

    # 승리 푸시 설정
    ENDGAME_PUSH_TIME = 360  # 6분
    ENDGAME_CHECK_INTERVAL = 110  # 프레임

    # 전투 유닛 제한
    MAX_COMBAT_UNITS_PER_UPDATE = 50  # 매 프레임 처리할 최대 유닛 수


class BanelingConfig:
    """Baneling 전술 파라미터"""

    # 폭발 조건
    MIN_ENEMIES_FOR_DETONATION = 3  # 최소 적 유닛 수
    OPTIMAL_DETONATION_RADIUS = 2.5  # 최적 폭발 범위
    SPLASH_DAMAGE_RADIUS = 2.2  # 스플래시 데미지 범위

    # 지뢰 전술
    LANDMINE_BURROW_RANGE = 3.5  # 매복 사거리
    LANDMINE_CHOKE_PRIORITY = 1  # 초크 포인트 우선순위
    LANDMINE_EXPANSION_PRIORITY = 2  # 확장 경로 우선순위

    # HP 관리
    RETREAT_HP_THRESHOLD = 0.3  # 퇴각 HP 비율


class MutaliskConfig:
    """Mutalisk 마이크로 파라미터"""

    # HP 관리
    REGEN_HP_THRESHOLD = 0.7  # 재생 시작 HP
    RETREAT_HP_THRESHOLD = 0.3  # 퇴각 HP

    # Magic Box (스플래시 대응)
    MAGIC_BOX_SPREAD_DISTANCE = 3.0  # 확산 거리
    MAGIC_BOX_MIN_UNITS = 4  # 최소 유닛 수 (Magic Box 발동)

    # 타겟팅
    WORKER_HARASSMENT_RANGE = 9.0  # 일꾼 견제 사거리
    SPLASH_THREAT_UNITS = {
        "THOR", "ARCHON", "INFESTOR",
        "COLOSSUS", "LIBERATOR"
    }


class InfestorConfig:
    """Infestor 전술 파라미터"""

    # Fungal Growth
    FUNGAL_MIN_ENEMIES = 3  # 최소 적 유닛 수
    FUNGAL_OPTIMAL_RANGE = 10.0  # 최적 시전 거리
    FUNGAL_ENERGY_COST = 75  # 에너지 비용

    # Burrow Movement
    BURROW_MOVE_SAFETY_RANGE = 15.0  # 안전 거리
    BURROW_INFILTRATION_RANGE = 8.0  # 침투 거리

    # Neural Parasite
    NEURAL_PRIORITY_HP_THRESHOLD = 0.5  # 우선순위 타겟 HP
    NEURAL_ENERGY_COST = 50  # 에너지 비용


class EconomyConfig:
    """경제 관련 설정"""

    # 금광 관련
    GOLD_MINERAL_THRESHOLD = 1200  # 금광 미네랄 임계값
    GOLD_BASE_PRIORITY = 5  # 금광 우선순위

    # 확장 기본 설정
    EXPANSION_COOLDOWN = 120  # 확장 쿨다운 (초)
    EXPANSION_SAFETY_RADIUS = 30  # 확장 안전 반경

    # 능동적 확장 (Proactive Expansion) 설정
    # 기지 수별 목표 시간 및 미네랄 임계값
    # Key: 현재 기지 수 (Next Base Index)
    # ★ Phase 17: 1분 멀티 최적화 ★
    PROACTIVE_EXPANSION_THRESHOLDS = {
        1: {"time": 22, "minerals": 300, "workers": 14, "minerals_worker": 300, "minerals_safe": 350}, # 1 -> 2 bases (★ 30s -> 22s)
        2: {"time": 90, "minerals": 400},   # 2 -> 3 bases
        3: {"time": 120, "minerals": 400},  # 3 -> 4 bases
        4: {"time": 180, "minerals": 500},  # 4 -> 5 bases
        5: {"time": 210, "minerals": 550},  # 5 -> 6 bases
        6: {"time": 240, "minerals": 600},  # 6 -> 7 bases
    }
    
    # 무한 확장 설정 (7+ Bases)
    INFINITE_EXPANSION_INTERVAL = 60  # 초
    INFINITE_EXPANSION_MINERALS = 900

    # 강제 확장 (Force Expansion) 설정 - 기지 수가 부족할 때 긴급 확장
    # (시간, 최소 미네랄, 목표 기지 수)
    # ★ Phase 17: 1분 멀티 최적화 - 더 빠른 확장 트리거 ★
    FORCE_EXPAND_TRIGGERS = [
        (8, 250, 2),    # ★ 8초, 미네랄 250, 2기지 미만 (더 빠른 트리거)
        (15, 200, 2),   # ★ 15초 (10s -> 15s)
        (22, 150, 2),   # ★ 22초 (20s -> 22s)
        (30, 100, 2),   # ★ 30초 (30s -> 30s, 미네랄 150 -> 100)
        (40, 0, 2),     # ★ 40초 (45s -> 40s)
        (50, 0, 2),     # ★ 50초 (60s -> 50s)
        (90, 250, 3),   # 1분 30초, 미네랄 250, 3기지 미만
        (120, 0, 3),
        (150, 0, 3),
        (180, 350, 4),
        (240, 0, 4),
        (300, 0, 5),
        (360, 0, 6),
        (600, 0, 6),
        (900, 0, 7),
    ]

    # 동시 확장 제한 (Pending Limit)
    # (시간, 기지 수, 미네랄) -> 허용 개수
    MAX_PENDING_EXPANSIONS = {
        "NATURAL_EMERGENCY": 2,    # 앞마당 비상 (base < 2)
        "CRITICAL_RETRY": 3,      # 앞마당 심각 (time > 60)
        "DUAL_EXPAND": 2,         # 2분 이후 (base < 4)
        "TRIPLE_EXPAND": 3,       # 5분 이후
        "DEFAULT_HIGH_MINERALS": 3, # 미네랄 > 1000
        "DEFAULT_MID_MINERALS": 2,  # 미네랄 > 600
        "DEFAULT": 1
    }

    # 일꾼 생산
    WORKER_CAP = 80  # 최대 일꾼 수
    WORKER_PER_BASE = 22  # 기지당 일꾼 수 (16 mineral + 6 gas)

    # 자원 밸런싱 및 소비
    GAS_OVERFLOW_THRESHOLD = 3000  # 가스 과잉 임계값
    MINERAL_OVERFLOW_THRESHOLD = 2000 # 미네랄 과잉 임계값 (Emergency Dump)
    MINERAL_DEFICIT_THRESHOLD = 200  # 미네랄 부족 임계값
    
    # 뱅킹 방지 (Resource Banking Prevention)
    BANKING_MINERAL_THRESHOLD = 1000
    BANKING_LARVA_THRESHOLD = 3
    BANKING_DEFENSE_BASE_REQ = 3      # 방어 건물 건설을 위한 최소 기지 수
    BANKING_DEFENSE_TIME_REQ = 180    # 방어 건물 건설 허용 시간 (3분)


class PotentialFieldConfig:
    """Potential Field 가중치"""

    # 기본 가중치
    ALLY_WEIGHT = 1.0  # 아군 인력 가중치
    ENEMY_WEIGHT = 1.4  # 적 반발력 가중치
    STRUCTURE_WEIGHT = 6.0  # 건물 인력 가중치
    TERRAIN_WEIGHT = 8.0  # 지형 반발력 가중치

    # 스플래시 대응
    SPLASH_WEIGHT = 3.0  # 스플래시 유닛 추가 반발력

    # 반경 설정
    ALLY_RADIUS = 4.0  # 아군 인력 반경
    ENEMY_RADIUS = 6.0  # 적 반발력 반경
    STRUCTURE_RADIUS = 8.0  # 건물 인력 반경
    TERRAIN_RADIUS = 5.0  # 지형 반발력 반경


class UpgradeConfig:
    """업그레이드 우선순위 설정"""

    # 필수 업그레이드 (절대 우선순위)
    CRITICAL_UPGRADES = {
        "ZERGLINGMOVEMENTSPEED",  # Metabolic Boost
        "OVERLORDSPEED",  # Pneumatized Carapace
    }

    # 유닛별 업그레이드 우선순위
    UNIT_SPECIFIC_UPGRADES = {
        "MUTALISK": ["ZERGFLYERWEAPONSLEVEL2", "ZERGFLYERWEAPONSLEVEL3"],
        "ROACH": ["ZERGGROUNDARMORSLEVEL2"],
        "HYDRALISK": ["EVOLVEGROOVEDSPINES"],  # Range upgrade
    }

    # 업그레이드 타이밍
    ATTACK_UPGRADE_PRIORITY = 1
    ARMOR_UPGRADE_PRIORITY = 2
    TECH_UPGRADE_PRIORITY = 3


# 설정 접근 헬퍼
def get_combat_config() -> CombatConfig:
    """전투 설정 반환"""
    return CombatConfig()


def get_baneling_config() -> BanelingConfig:
    """Baneling 설정 반환"""
    return BanelingConfig()


def get_mutalisk_config() -> MutaliskConfig:
    """Mutalisk 설정 반환"""
    return MutaliskConfig()


def get_infestor_config() -> InfestorConfig:
    """Infestor 설정 반환"""
    return InfestorConfig()


def get_economy_config() -> EconomyConfig:
    """경제 설정 반환"""
    return EconomyConfig()


def get_potential_field_config() -> PotentialFieldConfig:
    """Potential Field 설정 반환"""
    return PotentialFieldConfig()


def get_upgrade_config() -> UpgradeConfig:
    """업그레이드 설정 반환"""
    return UpgradeConfig()


class DefenseConfig:
    """방어 시스템 설정"""

    # === 초반 방어 (0-3분) ===
    EARLY_GAME_THRESHOLD = 180.0  # 3분 (초반 게임 기준)
    SPAWNING_POOL_SUPPLY = 12  # 스포닝 풀 건설 시작 보급
    INITIAL_ZERGLING_TARGET = 6  # 초반 목표 저글링 수 (러시 대응)

    # === 위협 감지 ===
    THREAT_CHECK_INTERVAL = 0.5  # 위협 체크 주기 (초)
    BASE_DETECTION_RANGE = 25  # 기지 근처 적 감지 범위
    WORKER_DANGER_RANGE = 10  # 일꾼 위험 거리
    SAFE_DISTANCE = 20  # 안전 거리

    # === 위협 레벨 임계값 ===
    # 초반 러시 판정 (3분 이내)
    EARLY_RUSH_TIME = 180  # 3분
    EARLY_RUSH_ENEMY_COUNT = 4  # 적 유닛 수
    EARLY_RUSH_SUPPLY = 4  # 적 보급

    # 중반 러시 판정 (5분 이내)
    MID_RUSH_TIME = 300  # 5분
    MID_RUSH_ENEMY_COUNT = 8  # 적 유닛 수
    MID_RUSH_SUPPLY = 8  # 적 보급

    # 위협 레벨 기준
    THREAT_CRITICAL_SUPPLY = 20  # Critical 위협 보급
    THREAT_HIGH_SUPPLY = 10  # High 위협 보급
    THREAT_HIGH_COUNT = 6  # High 위협 유닛 수
    THREAT_MEDIUM_SUPPLY = 4  # Medium 위협 보급
    THREAT_MEDIUM_COUNT = 3  # Medium 위협 유닛 수
    THREAT_LOW_COUNT = 1  # Low 위협 유닛 수

    # === 유닛별 보급 값 ===
    UNIT_SUPPLY_VALUES = {
        "ZERGLING": 0.5,
        "MARINE": 0.5,
        "REAPER": 1,
        "BANELING": 1,
        "ROACH": 2,
        "STALKER": 2,
        "IMMORTAL": 4,
        "SIEGETANK": 4,
        "SIEGETANKSIEGED": 4,
        "DEFAULT": 2  # 기본값
    }

    # === 긴급 방어 병력 목표 ===
    # 3분 이내
    EMERGENCY_EARLY_ZERGLINGS = 12
    EMERGENCY_EARLY_QUEENS = 2

    # 5분 이내
    EMERGENCY_MID_ZERGLINGS = 20
    EMERGENCY_MID_QUEENS = 3

    # 5분 이후
    EMERGENCY_LATE_ZERGLINGS = 30
    EMERGENCY_LATE_QUEENS = 4

    # === 방어 건물 ===
    DEFENSE_STRUCTURE_RANGE = 15  # 방어 건물 배치 범위
    SPINE_BUILD_DISTANCE = 8  # 스파인 크롤러 건설 거리 (기지에서)
    SPORE_BUILD_DISTANCE = 6  # 스포어 크롤러 건설 거리

    # 위협 레벨별 목표 스파인 개수
    SPINE_TARGET_HIGH = 3  # High 위협 시
    SPINE_TARGET_MEDIUM = 2  # Medium 위협 시
    SPINE_TARGET_DEFAULT = 1  # 기본

    # === Proactive 공중 방어 ===
    PROACTIVE_SPORE_TIMING = 180.0  # 3:00 (자동 스포어 크롤러 건설)
    SPORE_CRAWLER_COST = 75  # 미네랄 비용


class StrategyConfig:
    """전략 매니저 설정"""

    # === 승리 조건 감지 ===
    WIN_CONDITION_UPDATE_INTERVAL = 5.0  # 승리 조건 체크 주기 (초)
    WIN_CONDITION_HISTORY_SIZE = 20  # 승리 조건 히스토리 유지 개수

    # 승리/패배 점수 임계값
    STRONG_WINNING_SCORE = 6  # 강한 우위
    STRONG_LOSING_SCORE = -6  # 강한 열세
    SCORE_CATEGORY_THRESHOLD = 2  # 카테고리별 임계값

    # === 경제 점수 기준 ===
    ECONOMY_WORKER_RATIO_STRONG = 1.5  # 일꾼 비율 강한 우위
    ECONOMY_WORKER_RATIO_GOOD = 1.2  # 일꾼 비율 우위
    ECONOMY_WORKER_RATIO_WEAK = 0.7  # 일꾼 비율 열세
    ECONOMY_WORKER_RATIO_BAD = 0.8  # 일꾼 비율 약한 열세

    ECONOMY_BASE_RATIO_GOOD = 1.5  # 기지 비율 우위
    ECONOMY_BASE_RATIO_BAD = 0.7  # 기지 비율 열세

    ECONOMY_SCORE_STRONG = 2.0
    ECONOMY_SCORE_GOOD = 1.0
    ECONOMY_SCORE_WEAK = -2.0
    ECONOMY_SCORE_BAD = -1.0

    # === 군사 점수 기준 ===
    ARMY_RATIO_OVERWHELMING = 2.0  # 압도적 우위
    ARMY_RATIO_STRONG = 1.5  # 강한 우위
    ARMY_RATIO_GOOD = 1.2  # 우위
    ARMY_RATIO_WEAK = 0.5  # 열세
    ARMY_RATIO_BAD = 0.7  # 약한 열세
    ARMY_RATIO_POOR = 0.8  # 불리

    ARMY_SCORE_OVERWHELMING = 3.0
    ARMY_SCORE_STRONG = 2.0
    ARMY_SCORE_GOOD = 1.0
    ARMY_SCORE_WEAK = -3.0
    ARMY_SCORE_BAD = -2.0
    ARMY_SCORE_POOR = -1.0

    # === 기술 점수 기준 ===
    TECH_DIFF_STRONG = 2  # 기술 우위
    TECH_DIFF_GOOD = 1
    TECH_DIFF_BAD = -2  # 기술 열세
    TECH_DIFF_POOR = -1

    TECH_SCORE_STRONG = 2.0
    TECH_SCORE_GOOD = 1.0
    TECH_SCORE_BAD = -2.0
    TECH_SCORE_POOR = -1.0

    # === 기본 추정값 ===
    DEFAULT_ENEMY_WORKERS = 16  # 기본 적 일꾼 수
    DEFAULT_ENEMY_SUPPLY = 10  # 기본 적 보급
    DEFAULT_ENEMY_BASES = 1  # 기본 적 기지 수
    DEFAULT_ENEMY_TECH = 1  # 기본 적 기술 수준
    MIN_ENEMY_WORKERS = 16  # 최소 적 일꾼 수
    MIN_ENEMY_SUPPLY = 10  # 최소 적 보급
    MIN_ENEMY_BASES = 1  # 최소 적 기지 수
    MIN_ENEMY_TECH = 1  # 최소 적 기술 수준

    # 유닛별 보급 값
    UNIT_SUPPLY_COSTS = {
        "MARINE": 1, "MARAUDER": 2, "SIEGETANK": 3, "THOR": 6,
        "ZEALOT": 2, "STALKER": 2, "IMMORTAL": 4, "COLOSSUS": 6,
        "ZERGLING": 0.5, "ROACH": 2, "HYDRALISK": 2, "ULTRALISK": 6,
        "DEFAULT": 2
    }

    # === 빌드 오더 페이즈 타이밍 ===
    OPENING_PHASE_TIME = 180  # 0-3분
    TRANSITION_PHASE_TIME = 360  # 3-6분
    MIDGAME_PHASE_TIME = 600  # 6-10분
    # 10분 이후는 LATEGAME

    # === 확장 타이밍 ===
    TRANSITION_EXPANSION_TIME = 380  # 6:20 (중반 확장)
    LATEGAME_EXPANSION_TIME = 650  # 10:50 (후반 확장)
    EXPANSION_TIMING_WINDOW = 10  # 확장 타이밍 윈도우 (±10초)

    # === 리소스 우선순위 (기본값) ===
    DEFAULT_PRIORITY_ECONOMY = 0.4  # 경제 40%
    DEFAULT_PRIORITY_ARMY = 0.4  # 군대 40%
    DEFAULT_PRIORITY_TECH = 0.1  # 기술 10%
    DEFAULT_PRIORITY_DEFENSE = 0.1  # 방어 10%

    # 승리 조건별 우선순위 조정
    LOSING_ARMY_PRIORITY_ARMY = 0.6
    LOSING_ARMY_PRIORITY_ECONOMY = 0.2
    LOSING_ARMY_PRIORITY_DEFENSE = 0.2

    WINNING_ECONOMY_PRIORITY_ECONOMY = 0.6
    WINNING_ECONOMY_PRIORITY_ARMY = 0.2
    WINNING_ECONOMY_PRIORITY_DEFENSE = 0.2

    WINNING_ARMY_PRIORITY_ARMY = 0.6
    WINNING_ARMY_PRIORITY_ECONOMY = 0.2
    WINNING_ARMY_PRIORITY_TECH = 0.2

    LOSING_EMERGENCY_PRIORITY_ARMY = 0.7
    LOSING_EMERGENCY_PRIORITY_DEFENSE = 0.3
    LOSING_EMERGENCY_PRIORITY_ECONOMY = 0.0
    LOSING_EMERGENCY_PRIORITY_TECH = 0.0

    # === 기타 설정 ===
    CONCURRENT_STRATEGY_LIMIT = 3  # 동시 실행 전략 제한
    STATUS_PRINT_INTERVAL = 60  # 상태 출력 간격 (초)

    # 전략 평가 임계값
    SHOULD_EXPAND_THRESHOLD = 0.4  # 확장 우선순위 임계값
    SHOULD_BUILD_ARMY_THRESHOLD = 0.5  # 군대 우선순위 임계값


def get_defense_config() -> DefenseConfig:
    """방어 시스템 설정 반환"""
    return DefenseConfig()


def get_strategy_config() -> StrategyConfig:
    """전략 매니저 설정 반환"""
    return StrategyConfig()


class RoachBurrowConfig:
    """Roach Burrow Heal 설정"""

    # HP 임계값
    BURROW_HP_THRESHOLD = 0.3  # 30% 이하면 잠복
    RETURN_HP_THRESHOLD = 0.8  # 80% 이상이면 전투 복귀

    # 회복 시간
    MIN_HEAL_TIME = 5  # 최소 5초 회복

    # 감지 거리
    ENEMY_DETECTION_RANGE = 10  # 적 감지 거리
    DETECTOR_THREAT_RANGE = 15  # 디텍터 위협 거리

    # 디텍터 타입
    DETECTOR_TYPES = {
        "OBSERVER", "RAVEN", "OVERSEER", "OBSERVERSIEGEMODE",
        "MISSILETURRET", "SPORECRAWLER", "PHOTONCANNON",
        "SCAN"
    }


def get_roach_burrow_config() -> RoachBurrowConfig:
    """Roach Burrow 설정 반환"""
    return RoachBurrowConfig()


class CreepDenialConfig:
    """Creep Denial System 설정"""

    # 제거 유닛 타입 (킬러)
    KILLER_UNIT_TYPES = {
        "QUEEN",
        "HYDRALISK",
        "ROACH",
        "RAVAGER"
    }

    # 크립 종양 타입
    TUMOR_TYPES = {
        "CREEPTUMOR",
        "CREEPTUMORQUEEN",
        "CREEPTUMORBURROWED"
    }

    # 거리 설정
    ASSIGNMENT_RANGE = 20  # 킬러 할당 거리
    DANGER_DETECTION_RANGE = 12  # 위험 감지 거리

    # 위협 판단 기준
    DANGER_ENEMY_COUNT = 2  # 위험한 적 유닛 수

    # 방어 건물 타입
    STATIC_DEFENSE_TYPES = {
        "SIEGETANK",
        "SIEGETANKSIEGED",
        "SPINECRAWLER",
        "PHOTONCANNON",
        "BUNKER",
        "PLANETARYFORTRESS"
    }

    # 무시할 유닛 타입 (위협 계산 시)
    IGNORE_UNIT_TYPES = {
        "DRONE", "PROBE", "SCV",  # 일꾼
        "CREEPTUMOR", "CREEPTUMORQUEEN", "CREEPTUMORBURROWED"  # 종양
    }

    # 업데이트 간격
    UPDATE_INTERVAL = 11  # 11프레임마다 실행


def get_creep_denial_config() -> CreepDenialConfig:
    """Creep Denial 설정 반환"""
    return CreepDenialConfig()
