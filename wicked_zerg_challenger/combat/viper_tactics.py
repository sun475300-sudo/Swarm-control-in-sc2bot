# -*- coding: utf-8 -*-
"""
Feature #96: 바이퍼 활용 매니저

바이퍼의 스펠 능력을 최대한 활용하는 전술 시스템:
1. 블라인딩 클라우드 (Blinding Cloud) - 적 원거리 유닛 무력화
2. 어브덕트 (Abduct) - 고가치 유닛 끌어오기
3. 패러사이틱 밤 (Parasitic Bomb) - 공중 유닛 그룹 데미지
4. 에너지 관리 및 우선순위 타겟팅
"""

from typing import Dict, List, Optional, Set, Tuple

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.units import Units
except ImportError:
    AbilityId = None
    UnitTypeId = None
    Point2 = None
    Unit = None
    Units = None

from utils.logger import get_logger


class ViperTacticsManager:
    """
    바이퍼 전술 매니저

    바이퍼의 3가지 핵심 능력을 전략적으로 활용합니다:
    - 블라인딩 클라우드: 시즈탱크, 콜로서스 등 원거리 유닛 무력화
    - 어브덕트: 시즈탱크, 콜로서스, 캐리어 등 고가치 유닛 끌어오기
    - 패러사이틱 밤: 뭉친 공중 유닛에 지속 데미지

    에너지 우선순위:
    1. 어브덕트 (75 에너지) - 즉사급 가치
    2. 블라인딩 클라우드 (100 에너지) - 군대 무력화
    3. 패러사이틱 밤 (125 에너지) - 공중 유닛 처리
    """

    # 에너지 비용
    ABDUCT_ENERGY = 75
    BLINDING_CLOUD_ENERGY = 100
    PARASITIC_BOMB_ENERGY = 125

    def __init__(self, bot):
        """
        바이퍼 전술 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot
        self.logger = get_logger("ViperTactics")

        # 바이퍼 상태 추적
        self.viper_last_ability: Dict[int, float] = {}  # tag -> last_cast_time
        self.ability_cooldown: float = 2.0  # 능력 사용 간격

        # 어브덕트 우선순위 타겟 (가치가 높은 유닛부터)
        self.abduct_priority: List = []
        if UnitTypeId:
            self.abduct_priority = [
                UnitTypeId.SIEGETANKSIEGED,     # 시즈 모드 탱크 (최우선)
                UnitTypeId.COLOSSUS,            # 콜로서스
                UnitTypeId.HIGHTEMPLAR,         # 하이템플러
                UnitTypeId.DISRUPTOR,           # 디스럽터
                UnitTypeId.THOR,                # 토르
                UnitTypeId.CARRIER,             # 캐리어
                UnitTypeId.BATTLECRUISER,       # 배틀크루저
                UnitTypeId.TEMPEST,             # 템페스트
                UnitTypeId.IMMORTAL,            # 불멸자
                UnitTypeId.SIEGETANK,            # 이동 모드 탱크
                UnitTypeId.LIBERATORAG,         # 리버레이터 (시즈)
                UnitTypeId.ARCHON,              # 아콘
                UnitTypeId.MOTHERSHIP,          # 모선
            ]

        # 블라인딩 클라우드 우선순위 (원거리 유닛 그룹)
        self.blinding_cloud_targets: List = []
        if UnitTypeId:
            self.blinding_cloud_targets = [
                UnitTypeId.SIEGETANKSIEGED,
                UnitTypeId.MARINE,
                UnitTypeId.MARAUDER,
                UnitTypeId.STALKER,
                UnitTypeId.COLOSSUS,
                UnitTypeId.IMMORTAL,
                UnitTypeId.HYDRALISK,
                UnitTypeId.GHOST,
            ]

        # 패러사이틱 밤 대상
        self.parasitic_bomb_targets: List = []
        if UnitTypeId:
            self.parasitic_bomb_targets = [
                UnitTypeId.VIKINGFIGHTER,
                UnitTypeId.LIBERATOR,
                UnitTypeId.PHOENIX,
                UnitTypeId.VOIDRAY,
                UnitTypeId.MUTALISK,
                UnitTypeId.CORRUPTOR,
                UnitTypeId.BATTLECRUISER,
                UnitTypeId.CARRIER,
            ]

        # 전술 파라미터
        self.abduct_range: float = 9.0          # 어브덕트 사거리
        self.blinding_cloud_range: float = 11.0  # 블라인딩 클라우드 사거리
        self.parasitic_bomb_range: float = 8.0   # 패러사이틱 밤 사거리
        self.safe_distance: float = 10.0         # 바이퍼 안전 거리
        self.min_air_cluster: int = 3            # 패러사이틱 밤 최소 공중 유닛 수
        self.min_ground_cluster: int = 4         # 블라인딩 클라우드 최소 지상 유닛 수

        # 바이퍼 체력 관리
        self.retreat_hp: float = 0.3  # 체력 30% 이하 시 후퇴
        self.consume_hp: float = 0.6  # 체력 60% 이상에서만 Consume 사용

        # 통계
        self.abducts_cast: int = 0
        self.blinding_clouds_cast: int = 0
        self.parasitic_bombs_cast: int = 0

    async def on_step(self, iteration: int):
        """
        매 프레임 바이퍼 전술 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            if not hasattr(self.bot, "units"):
                return

            vipers = self.bot.units(UnitTypeId.VIPER)
            if not vipers.exists:
                return

            game_time = getattr(self.bot, "time", 0.0)

            # 각 바이퍼 관리 (매 8프레임)
            if iteration % 8 == 0:
                for viper in vipers:
                    await self._manage_viper(viper, game_time)

            # 에너지 충전 (Consume) 관리 (매 44프레임)
            if iteration % 44 == 0:
                for viper in vipers:
                    await self._manage_energy(viper, game_time)

            # 통계 출력
            if iteration % 1100 == 0:
                self._print_report(game_time)

        except Exception as e:
            if iteration % 100 == 0:
                self.logger.error(f"[VIPER] Error: {e}")

    async def _manage_viper(self, viper: Unit, game_time: float):
        """
        개별 바이퍼 관리

        우선순위:
        1. 체력 낮으면 후퇴
        2. 어브덕트 대상 있으면 실행
        3. 블라인딩 클라우드 대상 있으면 실행
        4. 패러사이틱 밤 대상 있으면 실행
        5. 안전 거리 유지
        """
        # 쿨다운 체크
        last_cast = self.viper_last_ability.get(viper.tag, 0)
        if game_time - last_cast < self.ability_cooldown:
            return

        # 체력 낮으면 후퇴
        if viper.health_percentage < self.retreat_hp:
            await self._retreat_viper(viper)
            return

        enemy_units = getattr(self.bot, "enemy_units", None)
        if not enemy_units or not enemy_units.exists:
            return

        # 1. 어브덕트 시도
        if viper.energy >= self.ABDUCT_ENERGY:
            target = self._find_abduct_target(viper, enemy_units)
            if target:
                await self._cast_abduct(viper, target, game_time)
                return

        # 2. 블라인딩 클라우드 시도
        if viper.energy >= self.BLINDING_CLOUD_ENERGY:
            target_pos = self._find_blinding_cloud_target(viper, enemy_units)
            if target_pos:
                await self._cast_blinding_cloud(viper, target_pos, game_time)
                return

        # 3. 패러사이틱 밤 시도
        if viper.energy >= self.PARASITIC_BOMB_ENERGY:
            target = self._find_parasitic_bomb_target(viper, enemy_units)
            if target:
                await self._cast_parasitic_bomb(viper, target, game_time)
                return

        # 안전 거리 유지
        await self._maintain_safe_distance(viper, enemy_units)

    def _find_abduct_target(self, viper: Unit, enemy_units) -> Optional[Unit]:
        """
        어브덕트 대상 탐색

        우선순위 리스트에 따라 가장 가치있는 타겟을 선택합니다.

        Args:
            viper: 바이퍼 유닛
            enemy_units: 적 유닛들

        Returns:
            어브덕트 대상 또는 None
        """
        for target_type in self.abduct_priority:
            targets = enemy_units.filter(
                lambda u: u.type_id == target_type
                and u.distance_to(viper) <= self.abduct_range
            )
            if targets.exists:
                # 가장 가까운 타겟 선택
                return targets.closest_to(viper)

        return None

    def _find_blinding_cloud_target(self, viper: Unit, enemy_units) -> Optional[Point2]:
        """
        블라인딩 클라우드 대상 위치 탐색

        원거리 유닛이 밀집된 위치를 찾습니다.

        Args:
            viper: 바이퍼 유닛
            enemy_units: 적 유닛들

        Returns:
            블라인딩 클라우드 시전 위치 또는 None
        """
        ranged_enemies = enemy_units.filter(
            lambda u: u.type_id in self.blinding_cloud_targets
            and u.distance_to(viper) <= self.blinding_cloud_range
            and not u.is_flying
        )

        if ranged_enemies.amount < self.min_ground_cluster:
            return None

        # 가장 밀집된 위치 찾기
        best_pos = None
        best_count = 0

        for enemy in ranged_enemies:
            cluster = ranged_enemies.closer_than(3.5, enemy)
            if cluster.amount > best_count:
                best_count = cluster.amount
                best_pos = cluster.center

        if best_count >= self.min_ground_cluster:
            return best_pos

        return None

    def _find_parasitic_bomb_target(self, viper: Unit, enemy_units) -> Optional[Unit]:
        """
        패러사이틱 밤 대상 탐색

        뭉친 공중 유닛 중 하나를 선택합니다.

        Args:
            viper: 바이퍼 유닛
            enemy_units: 적 유닛들

        Returns:
            패러사이틱 밤 대상 또는 None
        """
        air_enemies = enemy_units.filter(
            lambda u: u.is_flying
            and u.distance_to(viper) <= self.parasitic_bomb_range
        )

        if air_enemies.amount < self.min_air_cluster:
            return None

        # 주변에 공중 유닛이 가장 많은 유닛 선택
        best_target = None
        best_count = 0

        for air_unit in air_enemies:
            nearby_air = air_enemies.closer_than(4, air_unit)
            if nearby_air.amount > best_count:
                best_count = nearby_air.amount
                best_target = air_unit

        if best_count >= self.min_air_cluster:
            return best_target

        return None

    async def _cast_abduct(self, viper: Unit, target: Unit, game_time: float):
        """어브덕트 시전"""
        try:
            self.bot.do(viper(AbilityId.EFFECT_VIPERABDUCT, target))
            self.viper_last_ability[viper.tag] = game_time
            self.abducts_cast += 1
            self.logger.info(
                f"[{int(game_time)}s] [VIPER] 어브덕트! "
                f"대상: {target.type_id.name} (HP: {target.health})"
            )
        except Exception as e:
            self.logger.warning(f"[VIPER] 어브덕트 실패: {e}")

    async def _cast_blinding_cloud(self, viper: Unit, target_pos: Point2, game_time: float):
        """블라인딩 클라우드 시전"""
        try:
            self.bot.do(viper(AbilityId.EFFECT_BLINDINGCLOUD, target_pos))
            self.viper_last_ability[viper.tag] = game_time
            self.blinding_clouds_cast += 1
            self.logger.info(
                f"[{int(game_time)}s] [VIPER] 블라인딩 클라우드! 위치: {target_pos}"
            )
        except Exception as e:
            self.logger.warning(f"[VIPER] 블라인딩 클라우드 실패: {e}")

    async def _cast_parasitic_bomb(self, viper: Unit, target: Unit, game_time: float):
        """패러사이틱 밤 시전"""
        try:
            self.bot.do(viper(AbilityId.EFFECT_PARASITICBOMB, target))
            self.viper_last_ability[viper.tag] = game_time
            self.parasitic_bombs_cast += 1
            self.logger.info(
                f"[{int(game_time)}s] [VIPER] 패러사이틱 밤! "
                f"대상: {target.type_id.name}"
            )
        except Exception as e:
            self.logger.warning(f"[VIPER] 패러사이틱 밤 실패: {e}")

    async def _manage_energy(self, viper: Unit, game_time: float):
        """
        바이퍼 에너지 충전 관리 (Consume)

        아군 건물을 소비하여 에너지를 충전합니다.
        체력이 충분하고 에너지가 부족할 때만 실행합니다.
        """
        if viper.energy > 150:
            return  # 에너지 충분

        if viper.health_percentage < self.consume_hp:
            return  # 체력 부족

        # 근처 아군 건물 찾기 (소비 가능한 건물)
        if not hasattr(self.bot, "structures"):
            return

        consumable = self.bot.structures.filter(
            lambda s: s.type_id in {
                UnitTypeId.SPAWNINGPOOL, UnitTypeId.EVOLUTIONCHAMBER,
                UnitTypeId.ROACHWARREN, UnitTypeId.BANELINGNEST,
                UnitTypeId.HYDRALISKDEN, UnitTypeId.SPIRE,
                UnitTypeId.INFESTATIONPIT, UnitTypeId.ULTRALISKCAVERN,
            }
            and s.distance_to(viper) < 7
            and s.health_percentage > 0.5
        )

        if consumable.exists:
            target_building = consumable.closest_to(viper)
            try:
                self.bot.do(viper(AbilityId.VIPERCONSUMESTRUCTURE_YOURBUILDINGS, target_building))
            except Exception:
                pass

    async def _maintain_safe_distance(self, viper: Unit, enemy_units):
        """바이퍼 안전 거리 유지"""
        threats = enemy_units.filter(
            lambda u: u.can_attack_air and u.distance_to(viper) < self.safe_distance
        )

        if threats.exists:
            # 위협에서 반대 방향으로 이동
            threat_center = threats.center
            flee_direction = viper.position - threat_center
            length = (flee_direction.x ** 2 + flee_direction.y ** 2) ** 0.5
            if length > 0:
                flee_pos = Point2((
                    viper.position.x + (flee_direction.x / length) * 5,
                    viper.position.y + (flee_direction.y / length) * 5,
                ))
                self.bot.do(viper.move(flee_pos))

    async def _retreat_viper(self, viper: Unit):
        """바이퍼 후퇴"""
        retreat_pos = getattr(self.bot, "start_location", None)
        if retreat_pos:
            self.bot.do(viper.move(retreat_pos))

    def _print_report(self, game_time: float):
        """바이퍼 전술 보고"""
        if not hasattr(self.bot, "units"):
            return

        vipers = self.bot.units(UnitTypeId.VIPER)
        self.logger.info(
            f"[{int(game_time)}s] [VIPER] 보고: "
            f"바이퍼 {vipers.amount}기 | "
            f"어브덕트 {self.abducts_cast} | "
            f"블라인딩 {self.blinding_clouds_cast} | "
            f"패러사이틱 {self.parasitic_bombs_cast}"
        )

    def get_viper_stats(self) -> Dict:
        """
        바이퍼 전술 통계 반환

        Returns:
            통계 딕셔너리
        """
        viper_count = 0
        if hasattr(self.bot, "units"):
            viper_count = self.bot.units(UnitTypeId.VIPER).amount

        return {
            "viper_count": viper_count,
            "abducts_cast": self.abducts_cast,
            "blinding_clouds_cast": self.blinding_clouds_cast,
            "parasitic_bombs_cast": self.parasitic_bombs_cast,
            "total_casts": (
                self.abducts_cast + self.blinding_clouds_cast + self.parasitic_bombs_cast
            ),
        }
