# -*- coding: utf-8 -*-
"""
Game State Blackboard - 게임 상태 중앙 관리 시스템

Blackboard 패턴을 사용하여 모든 매니저가 접근할 수 있는 "Single Source of Truth" 제공.

아키텍처 개선:
- 분산된 상태를 중앙 집중화
- 중복 계산 제거
- 매니저 간 데이터 공유 간소화

참고: LOGIC_IMPROVEMENT_REPORT.md - Section 2 (State Management)
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum, IntEnum
import time
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:
    UnitTypeId = None
    Point2 = None


class ThreatLevel(IntEnum):
    """
    위협 수준 (숫자 비교 가능)
    """
    NONE = 0        # 안전
    LOW = 1         # 경계
    MEDIUM = 2      # 위험
    HIGH = 3        # 매우 위험
    CRITICAL = 4    # 긴급 상황 (러시, 올인)


class GamePhase(Enum):
    """게임 단계"""
    OPENING = "opening"          # 오프닝 (0-3분)
    EARLY_GAME = "early_game"    # 초반 (3-6분)
    MID_GAME = "mid_game"        # 중반 (6-12분)
    LATE_GAME = "late_game"      # 후반 (12분+)


class AuthorityMode(Enum):
    """생산 권한 모드 - Dynamic Authority System"""
    EMERGENCY = "emergency"      # 긴급: DefenseCoordinator 전권
    COMBAT = "combat"           # 전투: UnitFactory 우선
    STRATEGY = "strategy"       # 전략: AggressiveStrategies 우선
    ECONOMY = "economy"         # 경제: EconomyManager 우선
    BALANCED = "balanced"       # 균형: 모두 협력


@dataclass
class UnitCounts:
    """유닛 카운트 (현재 + pending)"""
    current: int = 0
    pending: int = 0

    @property
    def total(self) -> int:
        """총 개수"""
        return self.current + self.pending


@dataclass
class ThreatInfo:
    """위협 정보"""
    level: ThreatLevel = ThreatLevel.NONE
    enemy_army_supply: float = 0.0
    enemy_units_near_base: int = 0
    is_rushing: bool = False
    is_air_threat: bool = False
    detected_at: float = 0.0
    threat_position: Optional[Any] = None # Point2 or None


@dataclass
class ResourceState:
    """자원 상태"""
    minerals: int = 0
    vespene: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    supply_left: int = 0

    # 자원 수집 속도
    mineral_income: float = 0.0
    vespene_income: float = 0.0

    @property
    def is_supply_blocked(self) -> bool:
        """보급 막힘 여부"""
        return self.supply_left <= 0 and self.supply_used < 200


class GameStateBlackboard:
    """
    게임 상태 블랙보드 - Single Source of Truth

    모든 매니저가 이 클래스를 통해 게임 상태를 읽고 쓴다.
    중복 계산을 제거하고 일관된 상태를 유지한다.
    """

    def __init__(self):
        self.logger = get_logger("Blackboard")
        
        # === 기본 게임 정보 ===
        self.game_time: float = 0.0
        self.iteration: int = 0
        self.game_phase: GamePhase = GamePhase.OPENING

        # === 자원 상태 ===
        self.resources = ResourceState()
        
        # Compatible Accessors (Flat properties)
        self.minerals = 0
        self.vespene = 0
        self.supply_used = 0
        self.supply_cap = 0

        # === 유닛 카운트 (UnitTypeId -> UnitCounts) ===
        self.unit_counts: Dict[Any, UnitCounts] = {}

        # === 건물 상태 ===
        self.building_counts: Dict[Any, UnitCounts] = {}
        self.bases_count: int = 0
        self.worker_count: int = 0

        # === 위협 정보 ===
        self.threat = ThreatInfo()

        # === 권한 모드 (Dynamic Authority) ===
        self.authority_mode: AuthorityMode = AuthorityMode.BALANCED
        self.authority_changed_at: float = 0.0

        # === 전략 정보 ===
        self.enemy_race: str = "Unknown"
        self.current_strategy: str = "none"
        self.build_order_complete: bool = False
        self.strategy_mode: str = "NORMAL" # Backward compatibility

        # === 생산 요청 큐 ===
        # 우선순위별 생산 요청: {priority: [(unit_type, count, requester)]}
        self.production_queue: Dict[int, List[tuple]] = {
            0: [],  # 긴급 (방어)
            1: [],  # 높음 (전투)
            2: [],  # 중간 (전략)
            3: [],  # 낮음 (경제)
        }

        # === 건설 예약 ===
        # 건물 타입 -> (예약 시간, 예약자)
        self.building_reservations: Dict[Any, tuple] = {}

        # === 방어 상태 ===
        self.is_under_attack: bool = False
        self.attacked_bases: Set[int] = set()  # 공격받은 기지 태그

        # === 캐시된 계산 결과 ===
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl: float = 1.0  # 캐시 유효 시간 (초)
        
        # === Generic State (Backward Compatibility) ===
        self.state: Dict[str, Any] = {}
        self.requests: List[Dict[str, Any]] = [] # For old usage if any

    # ========== Compatibility Methods ==========
    
    def set(self, key: str, value: Any) -> None:
        """Update a state value (Backward Compatibility)"""
        self.state[key] = value
        
        # Sync with structured attributes if applicable
        if key == "strategy_mode":
            self.strategy_mode = value
        elif key == "game_phase":
            # Map string to enum if possible, or just store
            pass 
        elif key == "enemy_race":
            self.enemy_race = str(value)
        elif key == "is_rush_detected":
            self.threat.is_rushing = bool(value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value (Backward Compatibility)"""
        return self.state.get(key, default)

    # ========== 상태 업데이트 ==========

    def update_game_info(self, game_time: float, iteration: int = 0):
        """기본 게임 정보 업데이트 (Overloaded for compatibility)"""
        # If called with bot instance as first arg (old signature)
        bot = None
        if hasattr(game_time, "time"): 
            bot = game_time
            game_time = bot.time
            iteration = getattr(bot, "iteration", 0)
        
        self.game_time = game_time
        self.iteration = iteration

        # 게임 단계 자동 결정
        if game_time < 180:
            self.game_phase = GamePhase.OPENING
            self.state["game_phase"] = "OPENING"
        elif game_time < 360:
            self.game_phase = GamePhase.EARLY_GAME
            self.state["game_phase"] = "EARLY_GAME"
        elif game_time < 720:
            self.game_phase = GamePhase.MID_GAME
            self.state["game_phase"] = "MID_GAME"
        else:
            self.game_phase = GamePhase.LATE_GAME
            self.state["game_phase"] = "LATE_GAME"
            
        # If bot passed, update enemy race
        if bot and hasattr(bot, 'enemy_race') and bot.enemy_race:
            self.enemy_race = str(bot.enemy_race)
            self.state["enemy_race"] = self.enemy_race

    def update_resources(self, minerals: int, vespene: int,
                        supply_used: int, supply_cap: int):
        """자원 상태 업데이트"""
        self.resources.minerals = minerals
        self.resources.vespene = vespene
        self.resources.supply_used = supply_used
        self.resources.supply_cap = supply_cap
        self.resources.supply_left = supply_cap - supply_used
        
        # Sync flat usage
        self.minerals = minerals
        self.vespene = vespene
        self.supply_used = supply_used
        self.supply_cap = supply_cap

    def update_unit_count(self, unit_type: Any, current: int, pending: int):
        """유닛 카운트 업데이트"""
        if unit_type not in self.unit_counts:
            self.unit_counts[unit_type] = UnitCounts()

        self.unit_counts[unit_type].current = current
        self.unit_counts[unit_type].pending = pending

    def get_unit_count(self, unit_type: Any) -> UnitCounts:
        """유닛 카운트 조회"""
        return self.unit_counts.get(unit_type, UnitCounts())

    def update_threat(self, level: ThreatLevel, enemy_army_supply: float = 0.0,
                     enemy_units_near_base: int = 0, is_rushing: bool = False,
                     is_air_threat: bool = False, threat_position: Optional[Any] = None):
        """위협 정보 업데이트"""
        self.threat.level = level
        self.threat.enemy_army_supply = enemy_army_supply
        self.threat.enemy_units_near_base = enemy_units_near_base
        self.threat.is_rushing = is_rushing
        self.threat.is_air_threat = is_air_threat
        
        # Sync backward config
        self.state["is_rush_detected"] = is_rushing
        self.state["threat_level"] = int(level)

        if threat_position:
            self.threat.threat_position = threat_position

        # 위협 감지 시간 기록
        if level >= ThreatLevel.MEDIUM and self.threat.detected_at == 0.0:
            self.threat.detected_at = self.game_time

    # ========== Dynamic Authority System ==========

    def set_authority_mode(self, mode: AuthorityMode, reason: str = ""):
        """권한 모드 변경"""
        if self.authority_mode != mode:
            # print(f"[AUTHORITY] {self.authority_mode.value} → {mode.value} ({reason})")
            self.authority_mode = mode
            self.authority_changed_at = self.game_time

    def get_authority_priority(self, requester: str) -> int:
        """
        요청자의 우선순위 반환 (낮을수록 우선)

        Args:
            requester: 요청 시스템 이름

        Returns:
            우선순위 (0=최우선, 3=최하위)
        """
        if self.authority_mode == AuthorityMode.EMERGENCY:
            # 긴급 모드: DefenseCoordinator만 0순위
            return 0 if requester == "DefenseCoordinator" else 3

        elif self.authority_mode == AuthorityMode.COMBAT:
            # 전투 모드: UnitFactory > Defense > Strategy > Economy
            priority_map = {
                "UnitFactory": 0,
                "DefenseCoordinator": 1,
                "AggressiveStrategies": 2,
                "EconomyManager": 3,
            }
            return priority_map.get(requester, 2)

        elif self.authority_mode == AuthorityMode.STRATEGY:
            # 전략 모드: Strategy > UnitFactory > Defense > Economy
            priority_map = {
                "AggressiveStrategies": 0,
                "UnitFactory": 1,
                "DefenseCoordinator": 2,
                "EconomyManager": 3,
            }
            return priority_map.get(requester, 2)

        elif self.authority_mode == AuthorityMode.ECONOMY:
            # 경제 모드: Economy > Defense > UnitFactory > Strategy
            priority_map = {
                "EconomyManager": 0,
                "DefenseCoordinator": 1,
                "UnitFactory": 2,
                "AggressiveStrategies": 3,
            }
            return priority_map.get(requester, 2)

        else:  # BALANCED
            # 균형 모드: Defense > UnitFactory = Strategy > Economy
            priority_map = {
                "DefenseCoordinator": 0,
                "UnitFactory": 1,
                "AggressiveStrategies": 1,
                "EconomyManager": 2,
            }
            return priority_map.get(requester, 2)

    def auto_adjust_authority(self):
        """상황에 따라 권한 모드 자동 조정"""
        # 긴급 상황: 러시 감지 또는 CRITICAL 위협
        if self.threat.is_rushing or self.threat.level == ThreatLevel.CRITICAL:
            self.set_authority_mode(AuthorityMode.EMERGENCY, "Rush detected")
            return

        # 위협 상황: HIGH 위협
        if self.threat.level >= ThreatLevel.HIGH:
            self.set_authority_mode(AuthorityMode.COMBAT, "High threat")
            return

        # 전략 실행 중
        if self.current_strategy != "none" and not self.build_order_complete:
            self.set_authority_mode(AuthorityMode.STRATEGY, "Strategy active")
            return

        # 안전한 경제 성장
        if self.threat.level == ThreatLevel.NONE and self.game_phase == GamePhase.OPENING:
            self.set_authority_mode(AuthorityMode.ECONOMY, "Safe expansion")
            return

        # 기본: 균형 모드
        self.set_authority_mode(AuthorityMode.BALANCED, "Normal play")

    # ========== 생산 요청 시스템 ==========

    def request_production(self, unit_type: Any, count: int,
                          requester: str, priority: Optional[int] = None):
        """
        생산 요청 추가

        Args:
            unit_type: 생산할 유닛 타입
            count: 생산 개수
            requester: 요청자 이름
            priority: 우선순위 (None이면 자동 결정)
        """
        if priority is None:
            priority = self.get_authority_priority(requester)

        # 중복 요청 체크
        queue = self.production_queue[priority]
        for i, (utype, _, req) in enumerate(queue):
            if utype == unit_type and req == requester:
                # 기존 요청 업데이트
                queue[i] = (unit_type, count, requester)
                return

        # 새 요청 추가
        self.production_queue[priority].append((unit_type, count, requester))

    def get_next_production(self) -> Optional[tuple]:
        """
        다음 생산 요청 가져오기 (우선순위 순)

        Returns:
            (unit_type, count, requester) 또는 None
        """
        for priority in sorted(self.production_queue.keys()):
            queue = self.production_queue[priority]
            if queue:
                return queue.pop(0)
        return None

    def clear_production_requests(self, requester: Optional[str] = None):
        """
        생산 요청 초기화

        Args:
            requester: 특정 요청자만 초기화 (None이면 전체)
        """
        if requester is None:
            for priority in self.production_queue:
                self.production_queue[priority] = []
        else:
            for priority in self.production_queue:
                self.production_queue[priority] = [
                    (utype, cnt, req) for utype, cnt, req in self.production_queue[priority]
                    if req != requester
                ]
    
    # Alias for backward compatibility with old blackboard.py
    def clear_requests(self):
        self.clear_production_requests()

    # ========== 건설 예약 시스템 ==========

    def reserve_building(self, building_type: Any, requester: str,
                        duration: float = 10.0) -> bool:
        """
        건물 건설 예약

        Args:
            building_type: 건물 타입
            requester: 예약자 이름
            duration: 예약 유지 시간 (초)

        Returns:
            예약 성공 여부
        """
        # 기존 예약 확인
        if building_type in self.building_reservations:
            reserved_time, reserved_by = self.building_reservations[building_type]

            # 예약 만료되지 않았으면 실패
            if self.game_time - reserved_time < duration:
                return False

        # 예약 등록
        self.building_reservations[building_type] = (self.game_time, requester)
        return True

    def is_building_reserved(self, building_type: Any, duration: float = 10.0) -> bool:
        """건물이 예약되어 있는지 확인"""
        if building_type not in self.building_reservations:
            return False

        reserved_time, _ = self.building_reservations[building_type]
        return self.game_time - reserved_time < duration

    # ========== 캐시 시스템 ==========

    def cache_set(self, key: str, value: Any, ttl: Optional[float] = None):
        """캐시에 값 저장"""
        self._cache[key] = value
        self._cache_timestamps[key] = self.game_time
        if ttl is not None:
            self._cache_ttl = ttl

    def cache_get(self, key: str, default: Any = None) -> Any:
        """캐시에서 값 조회"""
        if key not in self._cache:
            return default

        # TTL 체크
        if self.game_time - self._cache_timestamps[key] > self._cache_ttl:
            del self._cache[key]
            del self._cache_timestamps[key]
            return default

        return self._cache[key]

    def cache_clear(self):
        """캐시 전체 삭제"""
        self._cache.clear()
        self._cache_timestamps.clear()

    # ========== 상태 조회 헬퍼 ==========

    def should_defend(self) -> bool:
        """방어가 필요한 상황인가?"""
        return (self.threat.level >= ThreatLevel.MEDIUM or
                self.is_under_attack or
                self.threat.is_rushing)

    def can_attack(self) -> bool:
        """공격 가능한 상황인가?"""
        return (self.threat.level <= ThreatLevel.LOW and
                not self.is_under_attack and
                self.game_phase != GamePhase.OPENING)

    def should_expand(self) -> bool:
        """확장 가능한 상황인가?"""
        return (self.threat.level == ThreatLevel.NONE and
                not self.resources.is_supply_blocked and
                self.resources.minerals >= 300)
                
    def get_army_value(self) -> float:
        # Simplification for reference
        return 0.0

# Alias for backward compatibility
Blackboard = GameStateBlackboard
