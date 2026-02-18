# -*- coding: utf-8 -*-
"""
Feature #98: 멀티프롱 공격 매니저

여러 방향에서 동시 공격을 조율하는 고급 멀티프롱 시스템:
1. 유닛 그룹 분할 (메인/견제/기습)
2. 다방향 동시 공격 타이밍 동기화
3. 각 공격조 독립적 타겟 할당
4. 공격 성공/실패에 따른 동적 재편성

기존 MultiProngCoordinator와의 차이:
- MultiProngCoordinator: 기본 3방향 공격 (단순 할당)
- MultiprongAttackManager: 타이밍 동기화 + 동적 재편성 + 우선순위 기반 타겟팅
"""

from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import time as _time

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.units import Units
except ImportError:
    UnitTypeId = None
    Point2 = None
    Unit = None
    Units = None

from utils.logger import get_logger


class ProngStatus(Enum):
    """공격조 상태"""
    ASSEMBLING = "assembling"    # 집결 중
    READY = "ready"              # 준비 완료
    ATTACKING = "attacking"      # 공격 중
    RETREATING = "retreating"    # 후퇴 중
    DISBANDED = "disbanded"      # 해산


class AttackProng:
    """개별 공격조"""

    def __init__(self, name: str, target: Optional[Point2] = None):
        self.name = name
        self.unit_tags: Set[int] = set()
        self.target: Optional[Point2] = target
        self.rally_point: Optional[Point2] = None
        self.status: ProngStatus = ProngStatus.ASSEMBLING
        self.start_time: float = 0.0
        self.kills: int = 0

    @property
    def size(self) -> int:
        """공격조 유닛 수"""
        return len(self.unit_tags)


class MultiprongAttackManager:
    """
    멀티프롱 공격 매니저

    여러 공격조를 동시에 조율하여 적의 방어를 분산시킵니다.

    전술 원리:
    - 메인 아미: 정면 돌파 (전체 군대의 50~60%)
    - 견제조: 적 확장 기지/일꾼 라인 공격 (20~30%)
    - 기습조: 적 본진 후방 침투 (10~20%)

    동기화:
    - 모든 공격조가 READY 상태가 되면 동시 공격 개시
    - 한 공격조가 후퇴해도 다른 공격조는 계속 공격
    """

    def __init__(self, bot):
        """
        멀티프롱 공격 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot
        self.logger = get_logger("MultiprongAttack")

        # 공격조 관리
        self.prongs: Dict[str, AttackProng] = {}
        self.attack_active: bool = False
        self.attack_start_time: float = 0.0

        # 전술 파라미터
        self.min_army_supply: int = 40          # 최소 군대 서플라이
        self.main_army_ratio: float = 0.55      # 메인 아미 비율
        self.harass_ratio: float = 0.25         # 견제조 비율
        self.flank_ratio: float = 0.20          # 기습조 비율
        self.sync_timeout: float = 15.0         # 동기화 대기 시간 (초)
        self.attack_cooldown: float = 90.0      # 공격 쿨다운 (초)
        self.retreat_loss_threshold: float = 0.6  # 60% 이상 손실 시 후퇴

        # 타이밍
        self.last_attack_time: float = 0.0
        self.sync_start_time: float = 0.0

        # 통계
        self.attacks_launched: int = 0
        self.successful_attacks: int = 0

    async def on_step(self, iteration: int):
        """
        매 프레임 멀티프롱 공격 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            game_time = getattr(self.bot, "time", 0.0)

            # 죽은 유닛 정리
            if iteration % 22 == 0:
                self._clean_dead_units()

            if not self.attack_active:
                # 공격 기회 평가
                if iteration % 66 == 0:
                    self._evaluate_attack_opportunity(game_time)
            else:
                # 공격 진행 관리
                if iteration % 11 == 0:
                    await self._manage_attack(game_time)

        except Exception as e:
            if iteration % 100 == 0:
                self.logger.error(f"[MULTIPRONG] Error: {e}")

    def _evaluate_attack_opportunity(self, game_time: float):
        """
        멀티프롱 공격 기회 평가

        조건:
        1. 쿨다운 경과
        2. 충분한 군대 서플라이
        3. 적 위치 정보 보유
        """
        if game_time - self.last_attack_time < self.attack_cooldown:
            return

        if not hasattr(self.bot, "units"):
            return

        # 군대 서플라이 계산
        army_supply = self._calculate_army_supply()
        if army_supply < self.min_army_supply:
            return

        # 적 위치 정보
        targets = self._find_attack_targets()
        if len(targets) < 2:
            return  # 최소 2개 타겟 필요

        # 공격조 편성
        self._organize_prongs(targets)
        self.attack_active = True
        self.attack_start_time = game_time
        self.attacks_launched += 1

        self.logger.info(
            f"[{int(game_time)}s] [MULTIPRONG] 멀티프롱 공격 개시! "
            f"#{self.attacks_launched} | 공격조 {len(self.prongs)}개 | "
            f"서플라이 {army_supply}"
        )

    def _calculate_army_supply(self) -> int:
        """아군 군대 서플라이 계산"""
        if not hasattr(self.bot, "units"):
            return 0

        combat_types = set()
        if UnitTypeId:
            combat_types = {
                UnitTypeId.ZERGLING, UnitTypeId.BANELING,
                UnitTypeId.ROACH, UnitTypeId.RAVAGER,
                UnitTypeId.HYDRALISK, UnitTypeId.LURKERMP,
                UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR,
                UnitTypeId.INFESTOR, UnitTypeId.ULTRALISK,
                UnitTypeId.BROODLORD, UnitTypeId.VIPER,
                UnitTypeId.SWARMHOSTMP,
            }

        total_supply = 0
        for unit in self.bot.units:
            if unit.type_id in combat_types:
                supply = getattr(unit, "supply_cost", 1)
                total_supply += max(supply, 1)
        return total_supply

    def _find_attack_targets(self) -> List[Tuple[Point2, str]]:
        """
        공격 목표 탐색

        Returns:
            (위치, 타겟 유형) 리스트
        """
        targets = []

        enemy_structures = getattr(self.bot, "enemy_structures", None)
        if enemy_structures and enemy_structures.exists:
            # 적 기지 (메인 타겟)
            bases = enemy_structures.filter(
                lambda s: s.type_id in {
                    UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
                    UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
                    UnitTypeId.PLANETARYFORTRESS, UnitTypeId.NEXUS,
                }
            )
            for base in bases:
                targets.append((base.position, "base"))

            # 적 생산/테크 시설
            tech_buildings = enemy_structures.filter(
                lambda s: s.type_id not in {
                    UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
                    UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
                    UnitTypeId.PLANETARYFORTRESS, UnitTypeId.NEXUS,
                    UnitTypeId.SUPPLYDEPOT, UnitTypeId.PYLON,
                    UnitTypeId.OVERLORD,
                }
            )
            if tech_buildings.exists:
                targets.append((tech_buildings.center, "tech"))

        # 적 시작 위치 (폴백)
        if not targets and hasattr(self.bot, "enemy_start_locations"):
            if self.bot.enemy_start_locations:
                targets.append((self.bot.enemy_start_locations[0], "main"))

        return targets

    def _organize_prongs(self, targets: List[Tuple[Point2, str]]):
        """
        공격조 편성

        Args:
            targets: (위치, 타겟 유형) 리스트
        """
        self.prongs.clear()

        if not hasattr(self.bot, "units"):
            return

        # 전투 유닛 수집
        combat_units = []
        if UnitTypeId:
            combat_types = {
                UnitTypeId.ZERGLING, UnitTypeId.BANELING,
                UnitTypeId.ROACH, UnitTypeId.RAVAGER,
                UnitTypeId.HYDRALISK, UnitTypeId.MUTALISK,
                UnitTypeId.ULTRALISK, UnitTypeId.CORRUPTOR,
                UnitTypeId.INFESTOR, UnitTypeId.BROODLORD,
                UnitTypeId.LURKERMP, UnitTypeId.VIPER,
                UnitTypeId.SWARMHOSTMP,
            }
            for unit in self.bot.units:
                if unit.type_id in combat_types:
                    combat_units.append(unit)

        if not combat_units:
            return

        total_units = len(combat_units)

        # 메인 아미
        main_count = int(total_units * self.main_army_ratio)
        harass_count = int(total_units * self.harass_ratio)
        # flank_count는 나머지

        # 메인 아미 공격조
        main_prong = AttackProng("main_army", targets[0][0])
        for unit in combat_units[:main_count]:
            main_prong.unit_tags.add(unit.tag)
        self.prongs["main_army"] = main_prong

        # 견제 공격조
        if len(targets) > 1:
            harass_prong = AttackProng("harass", targets[1][0])
            # 빠른 유닛 우선 (저글링, 뮤탈)
            fast_units = [u for u in combat_units[main_count:]
                          if u.type_id in {UnitTypeId.ZERGLING, UnitTypeId.MUTALISK, UnitTypeId.BANELING}]
            slow_units = [u for u in combat_units[main_count:]
                          if u.type_id not in {UnitTypeId.ZERGLING, UnitTypeId.MUTALISK, UnitTypeId.BANELING}]

            for unit in fast_units[:harass_count]:
                harass_prong.unit_tags.add(unit.tag)
            self.prongs["harass"] = harass_prong

            # 기습 공격조 (나머지)
            remaining = fast_units[harass_count:] + slow_units
            if remaining and len(targets) > 1:
                flank_target = targets[-1][0]  # 마지막 타겟
                flank_prong = AttackProng("flank", flank_target)
                for unit in remaining:
                    flank_prong.unit_tags.add(unit.tag)
                self.prongs["flank"] = flank_prong

        # 집결 지점 설정
        if hasattr(self.bot, "start_location") and hasattr(self.bot, "game_info"):
            map_center = self.bot.game_info.map_center
            for prong in self.prongs.values():
                if prong.target:
                    prong.rally_point = self.bot.start_location.towards(prong.target, 20)

        self.sync_start_time = getattr(self.bot, "time", 0.0)

    async def _manage_attack(self, game_time: float):
        """공격 진행 관리"""
        if not self.prongs:
            self._end_attack("공격조 없음")
            return

        # 각 공격조 상태별 관리
        all_disbanded = True
        for name, prong in list(self.prongs.items()):
            if prong.status == ProngStatus.DISBANDED:
                continue

            all_disbanded = False

            if prong.status == ProngStatus.ASSEMBLING:
                await self._manage_assembling(prong, game_time)

            elif prong.status == ProngStatus.READY:
                # 모든 공격조가 준비되었는지 확인
                if self._all_prongs_ready() or game_time - self.sync_start_time > self.sync_timeout:
                    await self._launch_synchronized_attack(game_time)

            elif prong.status == ProngStatus.ATTACKING:
                await self._manage_attacking(prong, game_time)

            elif prong.status == ProngStatus.RETREATING:
                await self._manage_retreating(prong, game_time)

        if all_disbanded:
            self._end_attack("모든 공격조 해산")

    async def _manage_assembling(self, prong: AttackProng, game_time: float):
        """공격조 집결 관리"""
        if not prong.rally_point:
            prong.status = ProngStatus.READY
            return

        all_gathered = True
        for tag in list(prong.unit_tags):
            unit = self._find_unit(tag)
            if not unit:
                prong.unit_tags.discard(tag)
                continue

            if unit.distance_to(prong.rally_point) > 10:
                self.bot.do(unit.move(prong.rally_point))
                all_gathered = False

        if all_gathered or game_time - self.attack_start_time > 15:
            prong.status = ProngStatus.READY

    def _all_prongs_ready(self) -> bool:
        """모든 공격조가 준비 완료인지 확인"""
        for prong in self.prongs.values():
            if prong.status not in {ProngStatus.READY, ProngStatus.DISBANDED}:
                return False
        return True

    async def _launch_synchronized_attack(self, game_time: float):
        """동기화된 동시 공격 개시"""
        self.logger.info(
            f"[{int(game_time)}s] [MULTIPRONG] 동시 공격 개시!"
        )

        for name, prong in self.prongs.items():
            if prong.status == ProngStatus.READY:
                prong.status = ProngStatus.ATTACKING
                prong.start_time = game_time

                for tag in prong.unit_tags:
                    unit = self._find_unit(tag)
                    if unit and prong.target:
                        self.bot.do(unit.attack(prong.target))

                self.logger.info(
                    f"  -> [{name}] {prong.size}기 -> {prong.target}"
                )

    async def _manage_attacking(self, prong: AttackProng, game_time: float):
        """공격 중 관리"""
        if not prong.target:
            prong.status = ProngStatus.DISBANDED
            return

        # 생존 유닛 확인
        initial_size = prong.size
        alive_count = 0
        for tag in list(prong.unit_tags):
            unit = self._find_unit(tag)
            if unit:
                alive_count += 1
                # 계속 공격
                if unit.is_idle:
                    self.bot.do(unit.attack(prong.target))
            else:
                prong.unit_tags.discard(tag)

        # 손실률 체크
        if initial_size > 0:
            loss_rate = 1 - (alive_count / initial_size)
            if loss_rate > self.retreat_loss_threshold:
                prong.status = ProngStatus.RETREATING
                self.logger.info(
                    f"[{int(game_time)}s] [MULTIPRONG] [{prong.name}] "
                    f"손실 {loss_rate*100:.0f}% - 후퇴!"
                )

        # 유닛 없으면 해산
        if not prong.unit_tags:
            prong.status = ProngStatus.DISBANDED

    async def _manage_retreating(self, prong: AttackProng, game_time: float):
        """후퇴 관리"""
        retreat_pos = getattr(self.bot, "start_location", None)
        if not retreat_pos:
            prong.status = ProngStatus.DISBANDED
            return

        all_safe = True
        for tag in list(prong.unit_tags):
            unit = self._find_unit(tag)
            if unit:
                if unit.distance_to(retreat_pos) > 15:
                    self.bot.do(unit.move(retreat_pos))
                    all_safe = False
            else:
                prong.unit_tags.discard(tag)

        if all_safe or not prong.unit_tags:
            prong.status = ProngStatus.DISBANDED

    def _clean_dead_units(self):
        """죽은 유닛 정리"""
        if not hasattr(self.bot, "units"):
            return

        alive_tags = {u.tag for u in self.bot.units}
        for prong in self.prongs.values():
            prong.unit_tags &= alive_tags

    def _find_unit(self, tag: int) -> Optional[Unit]:
        """태그로 유닛 찾기"""
        if not hasattr(self.bot, "units"):
            return None
        return self.bot.units.find_by_tag(tag)

    def _end_attack(self, reason: str):
        """공격 종료"""
        game_time = getattr(self.bot, "time", 0.0)
        self.logger.info(
            f"[{int(game_time)}s] [MULTIPRONG] 공격 종료: {reason}"
        )
        self.attack_active = False
        self.last_attack_time = game_time
        self.prongs.clear()

    def get_multiprong_stats(self) -> Dict:
        """
        멀티프롱 공격 통계 반환

        Returns:
            통계 딕셔너리
        """
        prong_info = {}
        for name, prong in self.prongs.items():
            prong_info[name] = {
                "size": prong.size,
                "status": prong.status.value,
                "target": str(prong.target) if prong.target else None,
            }

        return {
            "attack_active": self.attack_active,
            "attacks_launched": self.attacks_launched,
            "successful_attacks": self.successful_attacks,
            "prongs": prong_info,
        }
