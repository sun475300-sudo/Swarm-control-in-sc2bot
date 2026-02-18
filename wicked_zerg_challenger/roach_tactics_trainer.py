# -*- coding: utf-8 -*-
"""
Roach Tactics Trainer - 바퀴 전술 학습 시스템

바퀴의 특성을 활용한 고급 전술:
1. 높은 체력 (145 HP) - 탱킹 능력
2. 잠복 시 빠른 체력 회복 (초당 10 HP)
3. 히트 앤 런 전술 (공격 → 잠복 회복 → 재공격)
4. 탱킹 포지셔닝 (앞줄에서 피해 흡수)
"""

from typing import Dict, Set, List, Optional
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from utils.logger import get_logger


class RoachTactics:
    """바퀴 전술 정보"""

    def __init__(self, tag: int):
        self.tag = tag
        self.is_burrowed = False
        self.burrow_start_time = 0.0
        self.hp_when_burrowed = 0.0
        self.last_combat_time = 0.0
        self.times_burrowed = 0
        self.hp_healed = 0.0


class RoachTacticsTrainer:
    """
    바퀴 전술 학습 시스템

    바퀴의 잠복 체력 회복을 활용한 고급 마이크로 전술
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("RoachTactics")

        # 바퀴 추적
        self.roaches: Dict[int, RoachTactics] = {}  # tag -> RoachTactics

        # 잠복 설정
        self.BURROW_HP_THRESHOLD = 0.4  # 체력 40% 이하면 잠복
        self.UNBURROW_HP_THRESHOLD = 0.85  # 체력 85% 이상이면 잠복 해제
        self.MIN_HEAL_TIME = 3.0  # 최소 잠복 시간 (초)
        self.BURROW_COOLDOWN = 5.0  # 잠복 쿨다운 (초)

        # 탱킹 설정
        self.TANKING_DISTANCE = 3.0  # 앞줄 탱킹 거리
        self.MIN_ROACHES_FOR_TANKING = 3  # 탱킹 전술에 필요한 최소 바퀴 수

        # 히트 앤 런 설정
        self.HIT_AND_RUN_ENABLED = True
        self.RETREAT_DISTANCE = 8.0  # 후퇴 거리

        # 통계
        self.total_burrows = 0
        self.total_hp_healed = 0.0
        self.roaches_saved = 0  # 잠복으로 생존한 바퀴 수

        # 업그레이드 확인
        self.has_burrow = False
        self.has_tunneling_claws = False  # 땅굴 발톱 (이동 속도 증가)

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 업그레이드 확인
            self._check_upgrades()

            # 바퀴가 없으면 스킵
            roaches = self.bot.units(UnitTypeId.ROACH)
            if not roaches:
                return

            # 1. 바퀴 추적 업데이트
            self._update_roach_tracking(roaches, game_time)

            # 2. 부상당한 바퀴 잠복 (매 프레임)
            await self._burrow_injured_roaches(roaches, game_time)

            # 3. 회복 완료된 바퀴 잠복 해제 (매 프레임)
            await self._unburrow_healed_roaches(roaches, game_time)

            # 4. 탱킹 포지셔닝 (0.5초마다)
            if iteration % 11 == 0:
                await self._position_tanking_roaches(roaches)

            # 5. 히트 앤 런 전술 (1초마다)
            if iteration % 22 == 0:
                await self._execute_hit_and_run(roaches, game_time)

            # 6. 통계 출력 (30초마다)
            if iteration % 660 == 0 and self.total_burrows > 0:
                self._print_statistics(game_time)

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[ROACH_TACTICS] Error: {e}")

    def _check_upgrades(self):
        """업그레이드 확인"""
        try:
            self.has_burrow = UpgradeId.BURROW in self.bot.state.upgrades
            self.has_tunneling_claws = UpgradeId.TUNNELINGCLAWS in self.bot.state.upgrades
        except Exception:
            pass

    def _update_roach_tracking(self, roaches, game_time: float):
        """바퀴 추적 업데이트"""
        current_tags = {r.tag for r in roaches}

        # 새로운 바퀴 추가
        for roach in roaches:
            if roach.tag not in self.roaches:
                self.roaches[roach.tag] = RoachTactics(roach.tag)

        # 죽은 바퀴 제거
        dead_tags = set(self.roaches.keys()) - current_tags
        for tag in dead_tags:
            del self.roaches[tag]

    async def _burrow_injured_roaches(self, roaches, game_time: float):
        """
        부상당한 바퀴 잠복

        조건:
        1. 체력 40% 이하
        2. 잠복 업그레이드 완료
        3. 전투 중 (적이 근처에 있음)
        4. 쿨다운 경과
        """
        if not self.has_burrow:
            return

        for roach in roaches:
            # 이미 잠복 중이면 스킵
            if roach.is_burrowed:
                continue

            tactics = self.roaches.get(roach.tag)
            if not tactics:
                continue

            # 체력 확인
            hp_ratio = roach.health / roach.health_max
            if hp_ratio > self.BURROW_HP_THRESHOLD:
                continue

            # 쿨다운 확인
            time_since_last_burrow = game_time - tactics.last_combat_time
            if time_since_last_burrow < self.BURROW_COOLDOWN:
                continue

            # 전투 중 확인 (적이 근처에 있는지)
            if not self._is_in_combat(roach):
                continue

            # ★ Unit Authority Check ★
            if hasattr(self.bot, "unit_authority") and self.bot.unit_authority:
                from unit_authority_manager import AuthorityLevel
                # MICRO 권한 요청 (전술적 잠복은 높은 우선순위)
                granted = self.bot.unit_authority.request_authority(
                    {roach.tag}, AuthorityLevel.COMBAT, "RoachTactics", self.bot.state.game_loop
                )
                if roach.tag not in granted:
                    continue

            # 잠복 가능 여부 확인
            if not roach.is_idle and AbilityId.BURROWDOWN_ROACH in await self.bot.get_available_abilities(roach):
                try:
                    self.bot.do(roach(AbilityId.BURROWDOWN_ROACH))

                    # 통계 업데이트
                    tactics.is_burrowed = True
                    tactics.burrow_start_time = game_time
                    tactics.hp_when_burrowed = roach.health
                    tactics.last_combat_time = game_time
                    tactics.times_burrowed += 1

                    self.total_burrows += 1

                    self.logger.info(
                        f"[BURROW] Roach {roach.tag} burrowing at {hp_ratio*100:.1f}% HP"
                    )
                except Exception:
                    pass

    async def _unburrow_healed_roaches(self, roaches, game_time: float):
        """
        회복 완료된 바퀴 잠복 해제

        조건:
        1. 체력 85% 이상 회복
        2. 최소 3초 이상 잠복
        """
        for roach in roaches:
            if not roach.is_burrowed:
                continue

            tactics = self.roaches.get(roach.tag)
            if not tactics or not tactics.is_burrowed:
                continue

            # 잠복 시간 확인
            burrow_duration = game_time - tactics.burrow_start_time
            if burrow_duration < self.MIN_HEAL_TIME:
                continue

            # 체력 확인
            hp_ratio = roach.health / roach.health_max
            if hp_ratio < self.UNBURROW_HP_THRESHOLD:
                # 10초 이상 잠복했으면 강제 해제 (게임 진행을 위해)
                if burrow_duration < 10.0:
                    continue

            # 잠복 해제
            if AbilityId.BURROWUP_ROACH in await self.bot.get_available_abilities(roach):
                try:
                    self.bot.do(roach(AbilityId.BURROWUP_ROACH))

                    # 통계 업데이트
                    hp_healed = roach.health - tactics.hp_when_burrowed
                    tactics.hp_healed += hp_healed
                    tactics.is_burrowed = False

                    self.total_hp_healed += hp_healed
                    self.roaches_saved += 1

                    self.logger.info(
                        f"[UNBURROW] Roach {roach.tag} healed {hp_healed:.1f} HP "
                        f"({hp_ratio*100:.1f}% HP) in {burrow_duration:.1f}s"
                    )
                except Exception:
                    pass

    def _is_in_combat(self, roach) -> bool:
        """바퀴가 전투 중인지 확인"""
        try:
            # 근처 적 유닛 확인
            nearby_enemies = self.bot.enemy_units.closer_than(10, roach.position)
            if nearby_enemies.amount > 0:
                return True

            # 근처 적 건물 확인
            nearby_structures = self.bot.enemy_structures.closer_than(15, roach.position)
            if nearby_structures.amount > 0:
                return True

            return False
        except Exception:
            return False

    async def _position_tanking_roaches(self, roaches):
        """
        탱킹 포지셔닝

        체력이 높은 바퀴를 앞줄에 배치하여 탱킹
        """
        if roaches.amount < self.MIN_ROACHES_FOR_TANKING:
            return

        # 적이 없으면 스킵
        if not self.bot.enemy_units:
            return

        # 체력 순으로 정렬
        roaches_by_hp = sorted(roaches, key=lambda r: r.health, reverse=True)

        # 상위 40%를 탱커로 지정
        num_tanks = max(1, int(roaches.amount * 0.4))
        tanks = roaches_by_hp[:num_tanks]

        # 탱커를 적 방향으로 전진
        if self.bot.enemy_units:
            enemy_center = self.bot.enemy_units.center

            for tank in tanks:
                # 이미 잠복 중이거나 체력이 낮으면 스킵
                if tank.is_burrowed or tank.health / tank.health_max < 0.5:
                    continue

                # 적과의 거리
                distance = tank.distance_to(enemy_center)

                # 너무 멀면 전진
                if distance > 8:
                    self.bot.do(tank.attack(enemy_center))

    async def _execute_hit_and_run(self, roaches, game_time: float):
        """
        히트 앤 런 전술

        공격 → 후퇴 → 잠복 회복 → 재공격
        """
        if not self.HIT_AND_RUN_ENABLED:
            return

        if not self.has_burrow:
            return

        # 전투 중인 바퀴만 선택
        combat_roaches = []
        for roach in roaches:
            if roach.is_burrowed:
                continue
            if self._is_in_combat(roach):
                combat_roaches.append(roach)

        if not combat_roaches:
            return

        # 체력이 낮은 바퀴는 후퇴
        for roach in combat_roaches:
            hp_ratio = roach.health / roach.health_max

            # 체력 50% 이하면 후퇴
            if hp_ratio < 0.5:
                # 아군 기지 방향으로 후퇴
                if self.bot.townhalls.exists:
                    retreat_pos = self.bot.townhalls.closest_to(roach.position).position

                    # 후퇴 거리만큼 이동
                    direction = (retreat_pos - roach.position).normalized
                    retreat_target = roach.position + direction * self.RETREAT_DISTANCE

                    self.bot.do(roach.move(retreat_target))

    def get_roach_statistics(self) -> Dict:
        """바퀴 전술 통계 반환"""
        avg_burrows_per_roach = 0
        if len(self.roaches) > 0:
            avg_burrows_per_roach = sum(r.times_burrowed for r in self.roaches.values()) / len(self.roaches)

        return {
            "total_roaches": len(self.roaches),
            "total_burrows": self.total_burrows,
            "total_hp_healed": f"{self.total_hp_healed:.1f}",
            "roaches_saved": self.roaches_saved,
            "avg_burrows_per_roach": f"{avg_burrows_per_roach:.2f}",
            "has_burrow": self.has_burrow,
            "has_tunneling_claws": self.has_tunneling_claws
        }

    def _print_statistics(self, game_time: float):
        """통계 출력"""
        stats = self.get_roach_statistics()

        self.logger.info(
            f"[ROACH_TACTICS] [{int(game_time)}s] "
            f"Roaches: {stats['total_roaches']}, "
            f"Burrows: {stats['total_burrows']}, "
            f"HP Healed: {stats['total_hp_healed']}, "
            f"Saved: {stats['roaches_saved']}"
        )

        if stats['has_burrow']:
            self.logger.info(
                f"[ROACH_TACTICS] Avg Burrows/Roach: {stats['avg_burrows_per_roach']}"
            )
