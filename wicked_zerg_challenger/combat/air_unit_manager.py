# -*- coding: utf-8 -*-
"""
Air Unit Manager - 공중 유닛 전용 관리

기능:
1. 뮤탈리스크 하라스
2. 뮤탈리스크 방어
3. 공중 유닛 전투
4. Regen Dance, Magic Box 마이크로
"""

from typing import Optional, List, TYPE_CHECKING

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


class AirUnitManager:
    """
    공중 유닛 관리자

    책임:
    - 뮤탈리스크 하라스 및 마이크로
    - 공중 유닛 방어
    - 커럽터/무리군주 관리
    """

    def __init__(self, bot, mutalisk_micro=None):
        self.bot = bot
        self.logger = get_logger("AirUnitManager")

        # 뮤탈리스크 마이크로 시스템
        self.mutalisk_micro = mutalisk_micro

        # Air harassment state
        self._air_harass_target = None
        self._last_air_harass_time = 0
        self._air_harass_cooldown = 30  # 30 seconds

    async def handle_air_units(self, air_units, enemy_units, iteration: int):
        """
        공중 유닛 처리

        우선순위:
        1. 기지 방어 (적이 기지 공격 시)
        2. 일꾼 하라스
        3. 고립된 유닛 제거
        4. 메인 병력과 함께 공격
        """
        game_time = getattr(self.bot, "time", 0)

        # 기지 공격 확인
        base_threatened = self._is_base_under_attack()

        # 뮤탈리스크와 다른 공중 유닛 분리
        mutalisks = self._filter_units_by_type(air_units, ["MUTALISK"])
        other_air = self._filter_units_by_type(air_units, ["CORRUPTOR", "BROODLORD", "VIPER"])

        # === 뮤탈리스크 마이크로 ===
        if self._has_units(mutalisks):
            mutalisk_count = self._units_amount(mutalisks)

            # 기지 방어 우선
            if base_threatened:
                await self.mutalisk_defense(mutalisks, enemy_units)
            # 5기 이상이면 하라스 시작
            elif mutalisk_count >= 5:
                await self.mutalisk_harass(mutalisks, enemy_units, iteration)
            # 적이 보이면 공격
            elif self._has_units(enemy_units):
                await self.mutalisk_attack(mutalisks, enemy_units)

        # === 다른 공중 유닛 ===
        if self._has_units(other_air) and self._has_units(enemy_units):
            await self.other_air_attack(other_air, enemy_units)

    async def mutalisk_defense(self, mutalisks, enemy_units):
        """뮤탈리스크 기지 방어"""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return

        base = self.bot.townhalls.first

        # 기지 근처 적 찾기
        if hasattr(enemy_units, "closer_than"):
            nearby_enemies = enemy_units.closer_than(25, base.position)
        else:
            nearby_enemies = [e for e in enemy_units if e.distance_to(base.position) < 25]

        if not nearby_enemies:
            return

        # 우선순위 타겟 선택
        target = self.select_mutalisk_target(nearby_enemies)
        if target:
            for muta in mutalisks:
                try:
                    self.bot.do(muta.attack(target))
                except Exception:
                    continue

    async def mutalisk_harass(self, mutalisks, enemy_units, iteration: int):
        """
        뮤탈리스크 하라스

        적 기지로 뮤탈을 보내 일꾼 견제
        대공이 감지되면 즉시 후퇴
        """
        game_time = getattr(self.bot, "time", 0)

        # 쿨다운 체크
        if game_time - self._last_air_harass_time < self._air_harass_cooldown:
            if self._air_harass_target:
                await self.execute_harass(mutalisks, enemy_units)
                return
            elif self._has_units(enemy_units):
                await self.mutalisk_attack(mutalisks, enemy_units)
                return

        # 새 하라스 타겟 결정
        self._last_air_harass_time = game_time
        self._air_harass_target = self.find_harass_target()

        if self._air_harass_target:
            await self.execute_harass(mutalisks, enemy_units)
            if iteration % 100 == 0:
                print(f"[AIR HARASS] [{int(game_time)}s] Mutalisks harassing enemy base")
        else:
            if self._has_units(enemy_units):
                await self.mutalisk_attack(mutalisks, enemy_units)

    def find_harass_target(self):
        """하라스 타겟 찾기 (적 기지)"""
        # 적 본진
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        # 적 건물
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        if enemy_structures:
            townhall_names = ["NEXUS", "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS", "HATCHERY", "LAIR", "HIVE"]
            for struct in enemy_structures:
                if getattr(struct.type_id, "name", "") in townhall_names:
                    return struct.position
            return enemy_structures[0].position

        return None

    async def execute_harass(self, mutalisks, enemy_units):
        """
        하라스 실행

        기능:
        - Regen Dance (피 빠진 뮤탈은 후퇴)
        - Bounce Attack 최적화
        - 대공 위협 감지
        """
        if not self._air_harass_target:
            return

        # Regen Dance: 손상된 유닛 분리
        if self.mutalisk_micro:
            current_time = getattr(self.bot, 'time', 0)
            combat_ready, regenerating = await self.mutalisk_micro.execute_regen_dance(
                mutalisks,
                current_time,
                self.bot
            )
        else:
            combat_ready = list(mutalisks)
            regenerating = []

        if not combat_ready:
            return

        # 대공 위협 체크
        anti_air_threats = self.get_anti_air_threats(enemy_units, self._air_harass_target)

        # 대공 1기라도 있으면 즉시 후퇴 (뮤탈은 약함)
        if anti_air_threats and len(anti_air_threats) >= 1:
            await self.mutalisk_retreat(combat_ready)
            self._air_harass_target = None
            return

        # 일꾼 찾기
        workers_only = [e for e in enemy_units
                       if getattr(e.type_id, "name", "") in ["SCV", "PROBE", "DRONE"]]

        enemy_workers = [w for w in workers_only
                        if w.distance_to(self._air_harass_target) < 15]

        if enemy_workers:
            # 바운스 공격
            await self.mutalisk_bounce_attack(combat_ready, enemy_workers)
        else:
            # 하라스 타겟으로 이동
            for muta in combat_ready:
                try:
                    self.bot.do(muta.attack(self._air_harass_target))
                except Exception:
                    continue

    def get_anti_air_threats(self, enemy_units, position, range_check=15):
        """대공 가능한 적 유닛 찾기"""
        anti_air_names = [
            "MARINE", "HYDRALISK", "STALKER", "PHOENIX", "VOIDRAY",
            "VIKINGFIGHTER", "THOR", "CYCLONE", "LIBERATOR",
            "QUEEN", "CORRUPTOR", "MUTALISK", "ARCHON",
            "MISSILETURRET", "SPORECRAWLER", "PHOTONCANNON"
        ]
        return [e for e in enemy_units
                if getattr(e.type_id, "name", "") in anti_air_names
                and e.distance_to(position) < range_check]

    async def mutalisk_bounce_attack(self, mutalisks, targets):
        """
        뮤탈리스크 바운스 공격

        뮤탈은 직선으로 스플래시 데미지를 줌
        밀집된 일꾼을 노려 바운스 데미지 최대화
        """
        if not targets:
            return

        # 가장 밀집된 타겟 찾기
        best_target = None
        best_nearby_count = 0

        for target in targets:
            nearby = [t for t in targets if t.tag != target.tag and target.distance_to(t) < 3]
            if len(nearby) >= best_nearby_count:
                best_nearby_count = len(nearby)
                best_target = target

        if not best_target:
            best_target = targets[0]

        # 공격
        for muta in mutalisks:
            try:
                self.bot.do(muta.attack(best_target))
            except Exception:
                continue

    async def mutalisk_retreat(self, mutalisks):
        """뮤탈리스크 후퇴"""
        retreat_pos = None

        # 본진으로 후퇴
        if hasattr(self.bot, "townhalls") and self.bot.townhalls.exists:
            retreat_pos = self.bot.townhalls.first.position
        elif hasattr(self.bot, "start_location"):
            retreat_pos = self.bot.start_location

        if retreat_pos:
            for muta in mutalisks:
                try:
                    self.bot.do(muta.move(retreat_pos))
                except Exception:
                    continue

    async def mutalisk_attack(self, mutalisks, enemy_units):
        """
        뮤탈리스크 공격 (고급 마이크로)

        기능:
        - Regen Dance: 손상된 유닛 후퇴
        - Magic Box: 스플래시 대미지 회피를 위한 산개
        - 우선순위 타겟팅
        """
        if not mutalisks:
            return

        # Regen Dance
        if self.mutalisk_micro:
            current_time = getattr(self.bot, 'time', 0)
            combat_ready, regenerating = await self.mutalisk_micro.execute_regen_dance(
                mutalisks,
                current_time,
                self.bot
            )
        else:
            combat_ready = list(mutalisks)
            regenerating = []

        if not combat_ready:
            return

        # Magic Box 필요 여부 확인
        use_magic_box = False
        if self.mutalisk_micro:
            use_magic_box = self.mutalisk_micro.should_use_magic_box(enemy_units)

        # 타겟 선택
        target = self.select_mutalisk_target(enemy_units)
        if not target:
            return

        # 공격 실행
        if use_magic_box:
            # Magic Box 진형 사용
            await self.mutalisk_micro.execute_magic_box(
                combat_ready,
                target.position,
                self.bot
            )
            # 위치 잡은 후 공격
            for muta in combat_ready:
                try:
                    self.bot.do(muta.attack(target))
                except Exception:
                    continue
        else:
            # 일반 공격
            for muta in combat_ready:
                try:
                    self.bot.do(muta.attack(target))
                except Exception:
                    continue

    def select_mutalisk_target(self, enemy_units):
        """
        뮤탈리스크 최적 타겟 선택

        우선순위:
        1. 일꾼 (고가치)
        2. 시즈 유닛 (탱크, 콜로서스)
        3. 저체력 유닛 (쉬운 킬)
        4. 일반 유닛
        """
        if not enemy_units:
            return None

        workers = []
        siege = []
        low_hp = []
        other = []

        for enemy in enemy_units:
            name = getattr(enemy.type_id, "name", "")

            if name in ["SCV", "PROBE", "DRONE"]:
                workers.append(enemy)
            elif name in ["SIEGETANK", "SIEGETANKSIEGED", "COLOSSUS", "LIBERATOR", "WIDOWMINE"]:
                siege.append(enemy)
            elif enemy.health_percentage < 0.3:
                low_hp.append(enemy)
            else:
                other.append(enemy)

        # 최우선 타겟 반환
        if workers:
            return min(workers, key=lambda e: e.health)
        if siege:
            return siege[0]
        if low_hp:
            return min(low_hp, key=lambda e: e.health)
        if other:
            return other[0]

        return None

    async def other_air_attack(self, air_units, enemy_units):
        """커럽터와 무리군주 처리"""
        corruptors = self._filter_units_by_type(air_units, ["CORRUPTOR"])
        broodlords = self._filter_units_by_type(air_units, ["BROODLORD"])

        # 커럽터: 적 공중 유닛 또는 거대 유닛 공격
        if self._has_units(corruptors):
            air_targets = [e for e in enemy_units if getattr(e, "is_flying", False)]
            massive_targets = [e for e in enemy_units
                             if getattr(e.type_id, "name", "") in
                             ["COLOSSUS", "THOR", "BATTLECRUISER", "CARRIER", "TEMPEST", "MOTHERSHIP"]]

            target = None
            if air_targets:
                target = min(air_targets, key=lambda e: e.health)
            elif massive_targets:
                target = massive_targets[0]

            if target:
                for corr in corruptors:
                    try:
                        self.bot.do(corr.attack(target))
                    except Exception:
                        continue

        # 무리군주: 후방에서 지상 공격
        if self._has_units(broodlords):
            ground_targets = [e for e in enemy_units if not getattr(e, "is_flying", False)]
            if ground_targets:
                target = min(ground_targets, key=lambda e: e.health)
                for bl in broodlords:
                    try:
                        self.bot.do(bl.attack(target))
                    except Exception:
                        continue

    # ===== Helper Methods =====

    def _has_units(self, units) -> bool:
        """유닛 존재 확인"""
        if hasattr(units, "exists"):
            return bool(units.exists)
        return bool(units)

    def _units_amount(self, units) -> int:
        """유닛 수 반환"""
        if hasattr(units, "amount"):
            return int(units.amount)
        return len(units)

    def _filter_units_by_type(self, units, names):
        """유닛 타입으로 필터링"""
        if hasattr(units, "filter"):
            return units.filter(lambda u: u.type_id.name in names)
        return [u for u in units if getattr(u.type_id, "name", "") in names]

    def _is_base_under_attack(self) -> bool:
        """기지 공격 확인"""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls.exists:
            return False

        enemy_units = getattr(self.bot, "enemy_units", [])
        if not enemy_units:
            return False

        for th in self.bot.townhalls:
            nearby_enemies = [e for e in enemy_units if e.distance_to(th.position) < 25]
            if len(nearby_enemies) >= 1:
                return True

        return False
