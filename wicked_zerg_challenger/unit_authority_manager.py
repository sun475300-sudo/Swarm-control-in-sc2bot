"""
Unit Authority Manager - 유닛 제어 권한 관리 시스템

여러 시스템이 같은 유닛을 제어하려 할 때 충돌을 방지합니다
"""

from typing import Dict, Set, Optional, List
from enum import IntEnum
from collections import defaultdict
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
except ImportError:
    class BotAI:
        pass


class AuthorityLevel(IntEnum):
    """유닛 제어 권한 레벨"""
    WORKER_PROTECTED = 125  # ★ 일꾼 보호: 경제 일꾼은 전투 시스템에 빼앗기지 않음
    DEFENSE = 100
    WORKER_COMBAT = 90
    SPELL_UNIT = 80
    COMBAT = 70
    TACTICAL = 65       # ★ 견제/드랍 등 전술적 제어 (COMBAT과 HARASSMENT 사이)
    HARASSMENT = 60
    MULTI_PRONG = 50
    ECONOMY = 40
    SCOUTING = 30
    CREEP = 20
    IDLE = 10


class UnitAuthority:
    def __init__(self, unit_tag: int, owner: str, level: AuthorityLevel, request_time: float):
        self.unit_tag = unit_tag
        self.owner = owner
        self.level = level
        self.request_time = request_time
        self.last_command_time = request_time


class UnitAuthorityManager:
    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("UnitAuthority")
        self.authorities: Dict[int, UnitAuthority] = {}
        self.system_units: Dict[str, Set[int]] = defaultdict(set)
        self.AUTHORITY_TIMEOUT = 5.0  # 30초에서 5초로 단축 (빠른 권한 이관)
        self.total_conflicts = 0

    async def on_step(self, iteration: int):
        # ★ 일꾼 보호: 경제 일꾼을 WORKER_PROTECTED 권한으로 등록
        if iteration % 22 == 0:
            self._protect_economy_workers()

        if iteration % 44 == 0:
            self._cleanup_expired_authorities()

    def _protect_economy_workers(self):
        """경제 활동 중인 일꾼을 WORKER_PROTECTED 권한으로 등록하여 전투 차출 방지"""
        if not hasattr(self.bot, "workers") or not self.bot.workers:
            return

        min_protected = max(8, int(self.bot.workers.amount * 0.6))
        protected_count = 0

        for worker in self.bot.workers:
            if worker.is_gathering or worker.is_returning:
                # 자원 채취 중인 일꾼은 보호
                self.request_unit(worker.tag, "EconomyManager", AuthorityLevel.WORKER_PROTECTED)
                protected_count += 1
            if protected_count >= min_protected:
                break

    def is_worker_protected(self, unit_tag: int) -> bool:
        """해당 유닛이 보호된 일꾼인지 확인"""
        if unit_tag not in self.authorities:
            return False
        auth = self.authorities[unit_tag]
        return auth.level == AuthorityLevel.WORKER_PROTECTED and auth.owner == "EconomyManager"

    def request_unit(self, unit_tag: int, requester: str, level: AuthorityLevel) -> bool:
        game_time = getattr(self.bot, "time", 0)
        
        if unit_tag in self.authorities:
            current = self.authorities[unit_tag]
            if current.owner == requester:
                current.last_command_time = game_time
                return True
            if level > current.level:
                self._transfer_authority(unit_tag, requester, level, game_time)
                self.total_conflicts += 1
                return True
            return False
        
        self.authorities[unit_tag] = UnitAuthority(unit_tag, requester, level, game_time)
        self.system_units[requester].add(unit_tag)
        return True

    def release_unit(self, unit_tag: int, releaser: str) -> bool:
        if unit_tag not in self.authorities:
            return False
        if self.authorities[unit_tag].owner != releaser:
            return False
        del self.authorities[unit_tag]
        self.system_units[releaser].discard(unit_tag)
        return True

    def has_authority(self, unit_tag: int, requester: str) -> bool:
        return unit_tag in self.authorities and self.authorities[unit_tag].owner == requester

    def _transfer_authority(self, unit_tag: int, new_owner: str, level: AuthorityLevel, game_time: float):
        old = self.authorities[unit_tag]
        self.system_units[old.owner].discard(unit_tag)
        self.authorities[unit_tag] = UnitAuthority(unit_tag, new_owner, level, game_time)
        self.system_units[new_owner].add(unit_tag)

    def request_authority(self, unit_tags, level: AuthorityLevel, requester: str, game_loop: int = 0) -> set:
        """호환 메서드: 여러 유닛에 대해 권한 요청 (set 기반)"""
        granted = set()
        for tag in unit_tags:
            if self.request_unit(tag, requester, level):
                granted.add(tag)
        return granted

    def reset(self):
        """게임 간 상태 초기화 (훈련 에피소드 간 호출 필수)"""
        self.authorities.clear()
        self.system_units.clear()
        self.total_conflicts = 0

    def _cleanup_expired_authorities(self):
        game_time = getattr(self.bot, "time", 0)
        expired = [(tag, auth.owner) for tag, auth in self.authorities.items()
                   if game_time - auth.last_command_time > self.AUTHORITY_TIMEOUT]
        for tag, owner in expired:
            self.release_unit(tag, owner)
