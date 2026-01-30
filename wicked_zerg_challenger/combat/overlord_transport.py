# -*- coding: utf-8 -*-
"""
Overlord Transport - 대군주 수송 시스템

기능:
1. Ventral Sacs 업그레이드 확인
2. 대군주 수송 로직
3. 드랍 타이밍 관리
4. 저글링/바퀴 드랍 전술
"""

from typing import Optional, List, Dict, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.units import Units
    from sc2.unit import Unit
    from sc2.position import Point2
else:
    try:
        from sc2.units import Units
        from sc2.unit import Unit
        from sc2.position import Point2
    except ImportError:
        Units = object
        Unit = object
        Point2 = tuple

from utils.logger import get_logger


class OverlordTransport:
    """
    대군주 수송 시스템

    책임:
    - Ventral Sacs 업그레이드 관리
    - 대군주 수송 및 드랍 전술
    - 수송 유닛 관리
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("OverlordTransport")

        # Transport state
        self._transport_active = False
        self._loaded_overlords: Dict[int, List[int]] = {}  # overlord_tag -> [unit_tags]
        self._drop_targets: Dict[int, 'Point2'] = {}  # overlord_tag -> target_position
        self._last_drop_time = 0
        self._drop_cooldown = 60  # 1분마다 드랍 시도

        # Upgrade tracking
        self._ventral_sacs_started = False
        self._ventral_sacs_completed = False

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        game_time = getattr(self.bot, "time", 0)

        # Ventral Sacs 업그레이드 확인
        await self.check_ventral_sacs_upgrade()

        # 업그레이드가 완료되지 않았으면 수송 불가
        if not self._ventral_sacs_completed:
            return

        # 드랍 전술 실행 (쿨다운 확인)
        if game_time - self._last_drop_time >= self._drop_cooldown:
            await self.execute_drop_tactics(iteration)
            self._last_drop_time = game_time

    async def check_ventral_sacs_upgrade(self):
        """
        Ventral Sacs 업그레이드 확인

        UpgradeId.OVERLORDTRANSPORT 확인
        """
        try:
            from sc2.ids.upgrade_id import UpgradeId
        except ImportError:
            self.logger.warning("Cannot import UpgradeId - overlord transport disabled")
            return

        # 업그레이드 완료 확인
        if UpgradeId.OVERLORDTRANSPORT in self.bot.state.upgrades:
            if not self._ventral_sacs_completed:
                self._ventral_sacs_completed = True
                game_time = getattr(self.bot, "time", 0)
                print(f"[OVERLORD TRANSPORT] [{int(game_time)}s] ✓ Ventral Sacs upgrade completed!")
            return

        # 업그레이드 진행 중 확인
        if hasattr(self.bot, "already_pending_upgrade"):
            pending = self.bot.already_pending_upgrade(UpgradeId.OVERLORDTRANSPORT)
            if pending > 0 and not self._ventral_sacs_started:
                self._ventral_sacs_started = True
                game_time = getattr(self.bot, "time", 0)
                print(f"[OVERLORD TRANSPORT] [{int(game_time)}s] Ventral Sacs upgrade in progress...")

    async def execute_drop_tactics(self, iteration: int):
        """
        드랍 전술 실행

        전략:
        1. 대군주 2기 이상 확보
        2. 저글링 8기 이상 or 바퀴 4기 이상
        3. 적 본진 후방으로 드랍
        4. 일꾼 라인 공격
        """
        if not hasattr(self.bot, "units"):
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
            from sc2.ids.ability_id import AbilityId
        except ImportError:
            return

        # 사용 가능한 대군주 확인
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        available_overlords = overlords.filter(
            lambda o: o.is_idle and len(o.passengers) == 0
        )

        if len(available_overlords) < 2:
            return

        # 수송할 유닛 확인
        zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
        roaches = self.bot.units(UnitTypeId.ROACH).idle

        transport_units = []

        # 저글링 우선 (8기)
        if len(zerglings) >= 8:
            transport_units = list(zerglings[:8])
        # 바퀴 대안 (4기)
        elif len(roaches) >= 4:
            transport_units = list(roaches[:4])
        else:
            return

        # 드랍 타겟 결정
        drop_target = self.find_drop_target()
        if not drop_target:
            return

        # 대군주에 유닛 탑승
        overlord_list = list(available_overlords[:2])
        units_per_overlord = len(transport_units) // 2

        for idx, overlord in enumerate(overlord_list):
            start_idx = idx * units_per_overlord
            end_idx = start_idx + units_per_overlord if idx < len(overlord_list) - 1 else len(transport_units)
            units_to_load = transport_units[start_idx:end_idx]

            # 유닛 탑승 명령
            for unit in units_to_load:
                try:
                    self.bot.do(unit(AbilityId.LOAD, overlord))
                except AttributeError:
                    # Fallback: smart command
                    self.bot.do(unit.move(overlord.position))

            # 드랍 위치 저장
            self._drop_targets[overlord.tag] = drop_target
            self._loaded_overlords[overlord.tag] = [u.tag for u in units_to_load]

        game_time = getattr(self.bot, "time", 0)
        print(f"[OVERLORD DROP] [{int(game_time)}s] ★ Initiating drop with {len(transport_units)} units! ★")

        # 대군주 이동
        await self.move_overlords_to_drop(overlord_list, drop_target)

    async def move_overlords_to_drop(self, overlords: List, target: 'Point2'):
        """
        대군주를 드랍 위치로 이동

        Args:
            overlords: 대군주 리스트
            target: 드랍 목표 위치
        """
        for overlord in overlords:
            try:
                self.bot.do(overlord.move(target))
            except Exception as e:
                self.logger.warning(f"Failed to move overlord: {e}")

    async def check_drop_execution(self, iteration: int):
        """
        드랍 실행 확인

        대군주가 목표 위치에 도달하면 유닛 하차
        """
        if not self._drop_targets:
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
            from sc2.ids.ability_id import AbilityId
        except ImportError:
            return

        overlords = self.bot.units(UnitTypeId.OVERLORD)

        for overlord in overlords:
            if overlord.tag not in self._drop_targets:
                continue

            drop_target = self._drop_targets[overlord.tag]

            # 목표 위치에 가까워졌는지 확인
            if overlord.distance_to(drop_target) < 5:
                # 유닛 하차
                try:
                    self.bot.do(overlord(AbilityId.UNLOADALLAT, drop_target))
                    game_time = getattr(self.bot, "time", 0)
                    print(f"[OVERLORD DROP] [{int(game_time)}s] ★ DROPPING UNITS! ★")

                    # 드랍 완료 후 정리
                    del self._drop_targets[overlord.tag]
                    if overlord.tag in self._loaded_overlords:
                        del self._loaded_overlords[overlord.tag]

                except AttributeError:
                    self.logger.warning("Failed to unload units - ability not available")

    def find_drop_target(self) -> Optional['Point2']:
        """
        드랍 타겟 찾기

        우선순위:
        1. 적 본진 후방 (미네랄 라인)
        2. 적 확장 기지
        3. 적 테크 건물
        """
        # 적 시작 위치
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_start = self.bot.enemy_start_locations[0]

            # 본진 후방 계산 (미네랄 라인 쪽)
            if hasattr(self.bot, "start_location"):
                our_start = self.bot.start_location

                # 적 본진에서 우리 본진 반대 방향으로 5 거리
                direction_x = enemy_start.x - our_start.x
                direction_y = enemy_start.y - our_start.y

                # 정규화
                length = (direction_x ** 2 + direction_y ** 2) ** 0.5
                if length > 0:
                    direction_x /= length
                    direction_y /= length

                # 드랍 위치 (적 본진 뒤쪽)
                drop_x = enemy_start.x + direction_x * 5
                drop_y = enemy_start.y + direction_y * 5

                try:
                    from sc2.position import Point2
                    return Point2((drop_x, drop_y))
                except ImportError:
                    return enemy_start

            return enemy_start

        # 적 건물이 보이면 그 근처
        enemy_structures = getattr(self.bot, "enemy_structures", None)
        if enemy_structures and enemy_structures.exists:
            return enemy_structures.first.position

        return None

    async def retreat_empty_overlords(self):
        """
        빈 대군주 후퇴

        드랍 완료 후 대군주를 안전한 위치로 후퇴
        """
        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        overlords = self.bot.units(UnitTypeId.OVERLORD)

        for overlord in overlords:
            # 빈 대군주이고, 드랍 타겟이 없으면
            if len(overlord.passengers) == 0 and overlord.tag not in self._drop_targets:
                # 위험 지역에 있으면 후퇴
                enemy_units = getattr(self.bot, "enemy_units", [])
                if enemy_units:
                    nearby_enemies = [e for e in enemy_units if e.distance_to(overlord.position) < 15]

                    if nearby_enemies:
                        # 본진으로 후퇴
                        if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                            retreat_pos = self.bot.townhalls.first.position
                            self.bot.do(overlord.move(retreat_pos))

    def get_transport_status(self) -> Dict:
        """
        수송 상태 반환

        Returns:
            Dict with transport status info
        """
        return {
            "ventral_sacs_completed": self._ventral_sacs_completed,
            "active_transports": len(self._loaded_overlords),
            "pending_drops": len(self._drop_targets),
        }
