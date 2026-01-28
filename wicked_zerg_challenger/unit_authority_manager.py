# -*- coding: utf-8 -*-
"""
Unit Authority Manager - 유닛 제어 권한 관리

여러 시스템이 같은 유닛을 제어하려는 충돌 해결:
1. 우선순위 기반 권한 부여
2. 유닛 잠금 메커니즘
3. 자동 권한 해제
4. 충돌 로깅 및 통계
"""

from typing import Dict, Set, Optional, List
from enum import Enum
from dataclasses import dataclass
from utils.logger import get_logger


class Authority(Enum):
    """제어 권한 우선순위"""
    DEFENSE = 0        # 최우선: 방어 (DefenseCoordinator)
    COMBAT = 1         # 전투 (CombatManager)
    NYDUS = 2          # Nydus Network 작전
    MICRO = 3          # 마이크로 컨트롤
    PRODUCTION = 4     # 생산/변형
    ECONOMY = 5        # 경제 (일꾼)
    IDLE = 6           # 유휴 유닛
    NONE = 99          # 권한 없음


@dataclass
class UnitLock:
    """유닛 잠금 정보"""
    unit_tag: int
    authority: Authority
    system_name: str
    locked_at_frame: int
    expires_at_frame: int  # 자동 해제 시간


class UnitAuthorityManager:
    """
    유닛 제어 권한 관리

    여러 시스템이 동시에 유닛을 제어하려는 충돌을 해결합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("UnitAuthority")

        # 유닛 잠금 추적
        self.locks: Dict[int, UnitLock] = {}  # unit_tag -> UnitLock

        # 권한 요청 통계
        self.authority_requests: Dict[str, int] = {}
        self.authority_grants: Dict[str, int] = {}
        self.authority_denials: Dict[str, int] = {}

        # 설정
        self.DEFAULT_LOCK_DURATION = 110  # 5초 (프레임)
        self.DEFENSE_LOCK_DURATION = 220  # 10초 (방어는 더 길게)

    def request_authority(self, unit_tags: Set[int], authority: Authority,
                         system_name: str, iteration: int,
                         duration_frames: Optional[int] = None) -> Set[int]:
        """
        유닛 제어 권한 요청

        Args:
            unit_tags: 제어하려는 유닛 태그 집합
            authority: 요청하는 권한 레벨
            system_name: 요청하는 시스템 이름
            iteration: 현재 프레임
            duration_frames: 잠금 지속 시간 (None이면 기본값)

        Returns:
            실제로 권한을 획득한 유닛 태그 집합
        """
        # 통계
        self.authority_requests[system_name] = self.authority_requests.get(system_name, 0) + len(unit_tags)

        granted_units: Set[int] = set()

        for tag in unit_tags:
            if self._can_grant_authority(tag, authority, iteration):
                # 권한 부여
                lock_duration = duration_frames if duration_frames else self._get_lock_duration(authority)

                self.locks[tag] = UnitLock(
                    unit_tag=tag,
                    authority=authority,
                    system_name=system_name,
                    locked_at_frame=iteration,
                    expires_at_frame=iteration + lock_duration
                )

                granted_units.add(tag)
                self.authority_grants[system_name] = self.authority_grants.get(system_name, 0) + 1
            else:
                # 권한 거부
                self.authority_denials[system_name] = self.authority_denials.get(system_name, 0) + 1

        return granted_units

    def _can_grant_authority(self, unit_tag: int, requested_authority: Authority,
                            iteration: int) -> bool:
        """권한 부여 가능 여부 확인"""
        # 1. 잠금이 없으면 허용
        if unit_tag not in self.locks:
            return True

        lock = self.locks[unit_tag]

        # 2. 잠금이 만료되었으면 허용
        if iteration >= lock.expires_at_frame:
            del self.locks[unit_tag]
            return True

        # 3. 우선순위 비교
        # 요청한 권한이 현재 잠금보다 높은 우선순위면 허용 (숫자가 작을수록 높음)
        if requested_authority.value < lock.authority.value:
            # 기존 잠금 강제 해제
            del self.locks[unit_tag]
            return True

        # 4. 같은 시스템이면 허용
        if lock.system_name == requested_authority.name:
            return True

        return False

    def _get_lock_duration(self, authority: Authority) -> int:
        """권한별 기본 잠금 시간"""
        if authority == Authority.DEFENSE:
            return self.DEFENSE_LOCK_DURATION
        elif authority == Authority.COMBAT:
            return 110  # 5초
        elif authority == Authority.NYDUS:
            return 220  # 10초 (Nydus 작전은 길게)
        else:
            return self.DEFAULT_LOCK_DURATION

    def release_authority(self, unit_tags: Set[int], system_name: str):
        """권한 명시적 해제"""
        for tag in unit_tags:
            if tag in self.locks:
                lock = self.locks[tag]
                if lock.system_name == system_name:
                    del self.locks[tag]

    def is_locked(self, unit_tag: int, iteration: int) -> bool:
        """유닛이 잠겨있는지 확인"""
        if unit_tag not in self.locks:
            return False

        lock = self.locks[unit_tag]

        # 만료 확인
        if iteration >= lock.expires_at_frame:
            del self.locks[unit_tag]
            return False

        return True

    def get_lock_info(self, unit_tag: int) -> Optional[UnitLock]:
        """유닛 잠금 정보 반환"""
        return self.locks.get(unit_tag)

    def cleanup_expired_locks(self, iteration: int):
        """만료된 잠금 정리"""
        expired_tags = []

        for tag, lock in self.locks.items():
            if iteration >= lock.expires_at_frame:
                expired_tags.append(tag)

        for tag in expired_tags:
            del self.locks[tag]

    def get_authority_for_system(self, system_name: str) -> Authority:
        """시스템 이름으로 권한 레벨 매핑"""
        mapping = {
            "DefenseCoordinator": Authority.DEFENSE,
            "Combat": Authority.COMBAT,
            "CombatManager": Authority.COMBAT,
            "BattlePrep": Authority.COMBAT,
            "BaseDestruction": Authority.COMBAT,
            "NydusTrainer": Authority.NYDUS,
            "Micro": Authority.MICRO,
            "MicroController": Authority.MICRO,
            "UnitFactory": Authority.PRODUCTION,
            "ProductionController": Authority.PRODUCTION,
            "Economy": Authority.ECONOMY,
            "EconomyManager": Authority.ECONOMY,
        }

        return mapping.get(system_name, Authority.NONE)

    def filter_controllable_units(self, units, authority: Authority,
                                  system_name: str, iteration: int):
        """
        제어 가능한 유닛만 필터링

        Usage:
            units = bot.units(UnitTypeId.ROACH)
            controllable = authority_mgr.filter_controllable_units(
                units, Authority.COMBAT, "CombatManager", iteration
            )
        """
        if not units:
            return units

        controllable_tags = set()

        for unit in units:
            if not self.is_locked(unit.tag, iteration):
                controllable_tags.add(unit.tag)
            else:
                # 우선순위 체크
                if self._can_grant_authority(unit.tag, authority, iteration):
                    controllable_tags.add(unit.tag)

        return units.filter(lambda u: u.tag in controllable_tags)

    def get_statistics(self) -> Dict:
        """통계 반환"""
        total_requests = sum(self.authority_requests.values())
        total_grants = sum(self.authority_grants.values())
        total_denials = sum(self.authority_denials.values())

        grant_rate = (total_grants / total_requests * 100) if total_requests > 0 else 0

        return {
            "active_locks": len(self.locks),
            "total_requests": total_requests,
            "total_grants": total_grants,
            "total_denials": total_denials,
            "grant_rate": f"{grant_rate:.1f}%",
            "requests_by_system": dict(self.authority_requests),
            "denials_by_system": dict(self.authority_denials)
        }

    def print_status(self):
        """상태 출력"""
        stats = self.get_statistics()

        self.logger.info(
            f"[AUTHORITY] Locks: {stats['active_locks']}, "
            f"Grant Rate: {stats['grant_rate']} "
            f"({stats['total_grants']}/{stats['total_requests']})"
        )

        # 충돌이 많은 시스템 경고
        for system, denials in stats['denials_by_system'].items():
            if denials > 10:
                self.logger.warning(
                    f"[AUTHORITY] {system} has {denials} denials - check priority"
                )

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        # 만료된 잠금 정리
        self.cleanup_expired_locks(iteration)

        # 20초마다 상태 출력
        if iteration % 440 == 0 and len(self.locks) > 0:
            self.print_status()
