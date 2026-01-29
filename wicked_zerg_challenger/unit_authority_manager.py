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
    DEFENSE = 100
    WORKER_COMBAT = 90
    SPELL_UNIT = 80
    COMBAT = 70
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
        if iteration % 44 == 0:
            self._cleanup_expired_authorities()

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

    def _cleanup_expired_authorities(self):
        game_time = getattr(self.bot, "time", 0)
        expired = [(tag, auth.owner) for tag, auth in self.authorities.items()
                   if game_time - auth.request_time > self.AUTHORITY_TIMEOUT]
        for tag, owner in expired:
            self.release_unit(tag, owner)
