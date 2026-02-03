# -*- coding: utf-8 -*-
"""
Roach Burrow Heal - 바퀴 잠복 회복 시스템

기능:
1. Tunneling Claws 업그레이드 확인
2. 저체력 바퀴 자동 잠복
3. 회복 후 전투 복귀
4. 잠복 중 안전 확인
"""

from typing import Dict, Set, TYPE_CHECKING

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

try:
    from config.unit_configs import RoachBurrowConfig
except ImportError:
    RoachBurrowConfig = None


class RoachBurrowHeal:
    """
    바퀴 잠복 회복 시스템

    책임:
    - 저체력 바퀴 잠복
    - 회복 추적
    - 전투 복귀 관리
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("RoachBurrowHeal")

        # Load configuration
        self.config = RoachBurrowConfig() if RoachBurrowConfig else None

        # Burrow tracking
        self._burrowed_roaches: Set[int] = set()  # Set of roach tags that are healing
        self._burrow_start_time: Dict[int, float] = {}  # roach_tag -> burrow_time

        # Thresholds (from config or defaults)
        if self.config:
            self._min_heal_time = self.config.MIN_HEAL_TIME
            self._burrow_hp_threshold = self.config.BURROW_HP_THRESHOLD
            self._return_hp_threshold = self.config.RETURN_HP_THRESHOLD
        else:
            self._min_heal_time = 5
            self._burrow_hp_threshold = 0.3
            self._return_hp_threshold = 0.8

        # Upgrade tracking
        self._burrow_available = False
        self._tunneling_claws_available = False

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        # 업그레이드 확인
        await self.check_burrow_upgrades()

        # 잠복 불가능하면 스킵
        if not self._burrow_available:
            return

        # 바퀴 회복 관리
        await self.manage_roach_healing(iteration)

        # 죽은 바퀴 정리 (50초마다)
        if iteration % 1100 == 0:
            self.cleanup_dead_roaches()

    async def check_burrow_upgrades(self):
        """
        잠복 관련 업그레이드 확인

        - Burrow (기본 잠복)
        - Tunneling Claws (잠복 중 이동)
        """
        try:
            from sc2.ids.upgrade_id import UpgradeId
        except ImportError:
            return

        # Burrow 업그레이드 확인
        if UpgradeId.BURROW in self.bot.state.upgrades:
            if not self._burrow_available:
                self._burrow_available = True
                game_time = getattr(self.bot, "time", 0)
                print(f"[ROACH BURROW] [{int(game_time)}s] ✓ Burrow upgrade completed!")

        # Tunneling Claws 확인 (바퀴 전용)
        if UpgradeId.TUNNELINGCLAWS in self.bot.state.upgrades:
            if not self._tunneling_claws_available:
                self._tunneling_claws_available = True
                game_time = getattr(self.bot, "time", 0)
                print(f"[ROACH BURROW] [{int(game_time)}s] ✓ Tunneling Claws upgrade completed!")

    async def manage_roach_healing(self, iteration: int):
        """
        바퀴 회복 관리

        1. 저체력 바퀴 잠복
        2. 회복 중인 바퀴 추적
        3. 회복 완료 후 전투 복귀
        """
        if not hasattr(self.bot, "units"):
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
            from sc2.ids.ability_id import AbilityId
        except ImportError:
            return

        game_time = getattr(self.bot, "time", 0)

        # 모든 바퀴 확인
        roaches = self.bot.units(UnitTypeId.ROACH)

        for roach in roaches:
            roach_tag = roach.tag

            # === 1. 저체력 바퀴 잠복 ===
            if roach_tag not in self._burrowed_roaches:
                # 체력이 30% 이하면 잠복
                if roach.health_percentage <= self._burrow_hp_threshold:
                    # 적이 근처에 있는지 확인 (설정값 사용)
                    detection_range = self.config.ENEMY_DETECTION_RANGE if self.config else 10
                    enemy_units = getattr(self.bot, "enemy_units", [])
                    nearby_enemies = [e for e in enemy_units if e.distance_to(roach.position) < detection_range]

                    # 적이 근처에 있으면 잠복 (안전)
                    if nearby_enemies or roach.health_percentage <= 0.3:
                        await self.burrow_roach(roach, game_time)

            # === 2. 회복 중인 바퀴 관리 ===
            else:
                # 잠복 중인 바퀴
                burrow_duration = game_time - self._burrow_start_time.get(roach_tag, game_time)

                # 회복 완료 조건: 80% 이상 체력 + 최소 5초 경과
                if roach.health_percentage >= self._return_hp_threshold and burrow_duration >= self._min_heal_time:
                    await self.unburrow_roach(roach, game_time)

                # 위험 감지: 디텍터가 근처에 있으면 이동 (Tunneling Claws 필요)
                elif self._tunneling_claws_available:
                    await self.check_detector_threat(roach)

    async def burrow_roach(self, roach, game_time: float):
        """
        바퀴 잠복

        Args:
            roach: 바퀴 유닛
            game_time: 현재 게임 시간
        """
        try:
            from sc2.ids.ability_id import AbilityId
        except ImportError:
            return

        try:
            # 잠복 명령
            self.bot.do(roach(AbilityId.BURROWDOWN_ROACH))

            # 추적 정보 저장
            self._burrowed_roaches.add(roach.tag)
            self._burrow_start_time[roach.tag] = game_time

            if self.bot.iteration % 22 == 0:  # 1초마다 로그
                print(f"[ROACH BURROW] [{int(game_time)}s] Roach burrowing to heal ({int(roach.health_percentage * 100)}% HP)")

        except AttributeError as e:
            self.logger.warning(f"Failed to burrow roach: {e}")

    async def unburrow_roach(self, roach, game_time: float):
        """
        바퀴 잠복 해제

        Args:
            roach: 바퀴 유닛
            game_time: 현재 게임 시간
        """
        try:
            from sc2.ids.ability_id import AbilityId
        except ImportError:
            return

        try:
            # 잠복 해제 명령
            self.bot.do(roach(AbilityId.BURROWUP_ROACH))

            # 추적 정보 제거
            self._burrowed_roaches.discard(roach.tag)
            if roach.tag in self._burrow_start_time:
                heal_duration = game_time - self._burrow_start_time[roach.tag]
                del self._burrow_start_time[roach.tag]

                if self.bot.iteration % 22 == 0:
                    print(f"[ROACH BURROW] [{int(game_time)}s] Roach healed and returning to combat! "
                          f"({int(roach.health_percentage * 100)}% HP, {int(heal_duration)}s heal time)")

        except AttributeError as e:
            self.logger.warning(f"Failed to unburrow roach: {e}")

    async def check_detector_threat(self, roach):
        """
        디텍터 위협 확인

        잠복 중인 바퀴가 디텍터에 들키면 안전한 위치로 이동
        (Tunneling Claws 필요)

        Args:
            roach: 바퀴 유닛
        """
        if not self._tunneling_claws_available:
            return

        # 디텍터 유닛 타입 (설정값 사용)
        detector_types = self.config.DETECTOR_TYPES if self.config else {
            "OBSERVER", "RAVEN", "OVERSEER", "OBSERVERSIEGEMODE",
            "MISSILETURRET", "SPORECRAWLER", "PHOTONCANNON",
            "SCAN"
        }

        # 디텍터 감지 거리 (설정값 사용)
        detector_range = self.config.DETECTOR_THREAT_RANGE if self.config else 15

        enemy_units = getattr(self.bot, "enemy_units", [])
        enemy_structures = getattr(self.bot, "enemy_structures", [])

        # 근처 디텍터 확인
        nearby_detectors = []

        for enemy in enemy_units:
            enemy_type = getattr(enemy.type_id, "name", "").upper()
            if enemy_type in detector_types and enemy.distance_to(roach.position) < detector_range:
                nearby_detectors.append(enemy)

        for struct in enemy_structures:
            struct_type = getattr(struct.type_id, "name", "").upper()
            if struct_type in detector_types and struct.distance_to(roach.position) < detector_range:
                nearby_detectors.append(struct)

        # 디텍터가 근처에 있으면 이동
        if nearby_detectors:
            # 가장 가까운 아군 기지로 이동
            if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
                safe_position = self.bot.townhalls.closest_to(roach.position).position

                try:
                    self.bot.do(roach.move(safe_position))
                    game_time = getattr(self.bot, "time", 0)

                    if self.bot.iteration % 22 == 0:
                        print(f"[ROACH BURROW] [{int(game_time)}s] Detector detected! Roach retreating while burrowed")

                except AttributeError as e:
                    self.logger.warning(f"Failed to move burrowed roach: {e}")

    def cleanup_dead_roaches(self):
        """
        죽은 바퀴 추적 정보 정리
        """
        if not hasattr(self.bot, "units"):
            return

        try:
            from sc2.ids.unit_typeid import UnitTypeId
        except ImportError:
            return

        # 현재 살아있는 바퀴 태그
        alive_roaches = {r.tag for r in self.bot.units(UnitTypeId.ROACH)}

        # 죽은 바퀴 제거
        dead_roaches = self._burrowed_roaches - alive_roaches
        for roach_tag in dead_roaches:
            self._burrowed_roaches.discard(roach_tag)
            if roach_tag in self._burrow_start_time:
                del self._burrow_start_time[roach_tag]

    def get_healing_status(self) -> Dict:
        """
        회복 상태 반환

        Returns:
            Dict with healing status
        """
        return {
            "burrow_available": self._burrow_available,
            "tunneling_claws_available": self._tunneling_claws_available,
            "burrowed_roaches": len(self._burrowed_roaches),
        }
