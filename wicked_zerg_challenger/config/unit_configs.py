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

    # 확장 타이밍
    EXPANSION_MINERAL_THRESHOLD = 400  # 확장 미네랄 임계값
    EXPANSION_COOLDOWN = 120  # 확장 쿨다운 (초)
    EXPANSION_SAFETY_RADIUS = 30  # 확장 안전 반경

    # 일꾼 생산
    WORKER_CAP = 80  # 최대 일꾼 수
    WORKER_PER_BASE = 22  # 기지당 일꾼 수 (16 mineral + 6 gas)

    # 자원 밸런싱
    GAS_OVERFLOW_THRESHOLD = 3000  # 가스 과잉 임계값
    MINERAL_DEFICIT_THRESHOLD = 200  # 미네랄 부족 임계값


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
