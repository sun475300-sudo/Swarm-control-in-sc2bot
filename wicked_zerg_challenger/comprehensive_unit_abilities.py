# -*- coding: utf-8 -*-
"""
Comprehensive Unit Abilities - 모든 유닛 스킬 통합 관리

모든 저그 유닛의 스킬을 상황에 맞게 자동 사용:
1. Queen: Transfusion (치료), Creep Tumor (크립)
2. Ravager: Corrosive Bile (담즙)
3. Infestor: Neural Parasite, Fungal Growth
4. Viper: Abduct, Blinding Cloud, Parasitic Bomb
5. Baneling: Explode (자폭)
6. Overseer: Contaminate, Changeling
7. Roach: Burrow (회복)
8. Corruptor: Caustic Spray
9. Swarm Host: Spawn Locusts
10. Hydralisk: Lurker morph
"""

from typing import Dict, Set, List, Optional
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from utils.logger import get_logger


class ComprehensiveUnitAbilities:
    """모든 유닛 스킬 통합 관리"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("UnitAbilities")

        # 스킬 사용 쿨다운 추적
        self.last_ability_used: Dict[int, Dict[str, float]] = {}  # {unit_tag: {ability_name: game_time}}

        # 스킬 쿨다운 설정 (초)
        self.TRANSFUSION_CD = 1.0
        self.BILE_CD = 7.0
        self.NEURAL_CD = 1.5
        self.FUNGAL_CD = 1.0
        self.ABDUCT_CD = 1.0
        self.BLINDING_CLOUD_CD = 1.0
        self.PARASITIC_BOMB_CD = 1.0
        self.CONTAMINATE_CD = 1.0
        self.CAUSTIC_SPRAY_CD = 15.0
        self.LOCUST_CD = 14.0

        # 통계
        self.ability_stats = {
            "transfusion": 0, "bile": 0, "neural": 0, "fungal": 0,
            "abduct": 0, "blinding_cloud": 0, "parasitic_bomb": 0,
            "contaminate": 0, "baneling_explode": 0, "burrow": 0,
            "caustic_spray": 0, "locust": 0, "changeling": 0,
            "lurker_burrow": 0, "infestor_burrow": 0, "swarmhost_burrow": 0,
            "overlord_creep": 0
        }

        # 잠복 추적
        self.burrowed_units: Set[int] = set()  # 이미 잠복한 유닛 태그

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 11프레임(약 0.5초)마다 실행
            if iteration % 11 != 0:
                return

            # === 1. QUEEN ABILITIES ===
            await self._queen_abilities(game_time)

            # === 2. RAVAGER ABILITIES ===
            await self._ravager_abilities(game_time)

            # === 3. INFESTOR ABILITIES ===
            await self._infestor_abilities(game_time)

            # === 4. VIPER ABILITIES ===
            await self._viper_abilities(game_time)

            # === 5. BANELING ABILITIES ===
            await self._baneling_abilities(game_time)

            # === 6. OVERSEER ABILITIES ===
            await self._overseer_abilities(game_time)

            # === 7. CORRUPTOR ABILITIES ===
            await self._corruptor_abilities(game_time)

            # === 8. SWARM HOST ABILITIES ===
            await self._swarmhost_abilities(game_time)

            # === 9. TACTICAL BURROW (전술적 잠복) ===
            await self._tactical_burrow(game_time)

            # === 10. OVERLORD CREEP (대군주 크립 생성 - 적 건설 방해) ===
            await self._overlord_creep_harass(game_time)

            # 통계 출력 (60초마다)
            if iteration % 1320 == 0:
                self._print_stats(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[ABILITIES] Error: {e}")

    # ========================================
    # QUEEN ABILITIES
    # ========================================
    async def _queen_abilities(self, game_time: float):
        """Queen: Transfusion + Creep Tumor"""
        queens = self.bot.units(UnitTypeId.QUEEN).filter(lambda q: q.energy >= 25)
        if not queens:
            return

        for queen in queens:
            # 1. Transfusion (체력 35% 이하 아군 치료)
            if queen.energy >= 50:
                injured = self.bot.units.filter(
                    lambda u: u.health_percentage < 0.35 and u.health_percentage > 0
                ).closer_than(9, queen)

                if injured:
                    target = injured.sorted(lambda u: u.health_percentage)[0]
                    abilities = await self.bot.get_available_abilities(queen)
                    if AbilityId.TRANSFUSION_TRANSFUSION in abilities:
                        if self._can_use_ability(queen.tag, "transfusion", game_time, self.TRANSFUSION_CD):
                            self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, target))
                            self._record_ability(queen.tag, "transfusion", game_time)
                            self.ability_stats["transfusion"] += 1
                            continue

            # 2. Creep Tumor (크립 확장 - 기지 근처)
            if queen.energy >= 25 and self.bot.townhalls.exists:
                if len(self.bot.structures(UnitTypeId.CREEPTUMORBURROWED)) < 20:
                    # 기지 주변 크립 확장
                    closest_base = self.bot.townhalls.closest_to(queen)
                    if queen.distance_to(closest_base) < 15:
                        # 크립 확장 위치 찾기
                        position = closest_base.position.towards(self.bot.game_info.map_center, 8)
                        abilities = await self.bot.get_available_abilities(queen)
                        if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities:
                            self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, position))

    # ========================================
    # RAVAGER ABILITIES
    # ========================================
    async def _ravager_abilities(self, game_time: float):
        """Ravager: Corrosive Bile (부식성 담즙)"""
        ravagers = self.bot.units(UnitTypeId.RAVAGER)
        if not ravagers:
            return

        for ravager in ravagers:
            if not self._can_use_ability(ravager.tag, "bile", game_time, self.BILE_CD):
                continue

            # 담즙 우선순위: 건물 > 중갑 > 밀집 유닛
            targets = []

            # 1. 적 건물 (사거리 9)
            enemy_structures = self.bot.enemy_structures.closer_than(9, ravager)
            if enemy_structures:
                targets.append(enemy_structures.closest_to(ravager))

            # 2. 중갑 유닛 (Immortal, Siege Tank, Ultralisk)
            heavy_units = self.bot.enemy_units.filter(
                lambda u: u.type_id in {
                    UnitTypeId.IMMORTAL, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED,
                    UnitTypeId.ULTRALISK, UnitTypeId.THOR
                }
            ).closer_than(9, ravager)
            if heavy_units:
                targets.append(heavy_units.closest_to(ravager))

            # 3. 밀집 유닛 (3명 이상)
            enemy_units = self.bot.enemy_units.closer_than(9, ravager)
            if enemy_units.amount >= 3:
                # 밀집도가 가장 높은 위치
                for unit in enemy_units:
                    nearby = enemy_units.closer_than(2, unit)
                    if nearby.amount >= 3:
                        targets.append(unit)
                        break

            if targets:
                target = targets[0]
                abilities = await self.bot.get_available_abilities(ravager)
                if AbilityId.EFFECT_CORROSIVEBILE in abilities:
                    self.bot.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, target.position))
                    self._record_ability(ravager.tag, "bile", game_time)
                    self.ability_stats["bile"] += 1

    # ========================================
    # INFESTOR ABILITIES
    # ========================================
    async def _infestor_abilities(self, game_time: float):
        """Infestor: Neural Parasite + Fungal Growth"""
        infestors = self.bot.units(UnitTypeId.INFESTOR).filter(lambda i: i.energy >= 75)
        if not infestors:
            return

        for infestor in infestors:
            # 1. Neural Parasite (고가치 유닛 탈취)
            if infestor.energy >= 100:
                high_value = self.bot.enemy_units.filter(
                    lambda u: u.type_id in {
                        UnitTypeId.BATTLECRUISER, UnitTypeId.CARRIER, UnitTypeId.MOTHERSHIP,
                        UnitTypeId.THOR, UnitTypeId.COLOSSUS, UnitTypeId.TEMPEST
                    }
                ).closer_than(9, infestor)

                if high_value:
                    target = high_value.closest_to(infestor)
                    abilities = await self.bot.get_available_abilities(infestor)
                    if AbilityId.NEURALPARASITE_NEURALPARASITE in abilities:
                        if self._can_use_ability(infestor.tag, "neural", game_time, self.NEURAL_CD):
                            self.bot.do(infestor(AbilityId.NEURALPARASITE_NEURALPARASITE, target))
                            self._record_ability(infestor.tag, "neural", game_time)
                            self.ability_stats["neural"] += 1
                            continue

            # 2. Fungal Growth (밀집 유닛 속박)
            if infestor.energy >= 75:
                enemies = self.bot.enemy_units.closer_than(9, infestor)
                for enemy in enemies:
                    nearby = enemies.closer_than(2.5, enemy)
                    if nearby.amount >= 5:  # 5명 이상 밀집
                        abilities = await self.bot.get_available_abilities(infestor)
                        if AbilityId.FUNGALGROWTH_FUNGALGROWTH in abilities:
                            if self._can_use_ability(infestor.tag, "fungal", game_time, self.FUNGAL_CD):
                                self.bot.do(infestor(AbilityId.FUNGALGROWTH_FUNGALGROWTH, enemy.position))
                                self._record_ability(infestor.tag, "fungal", game_time)
                                self.ability_stats["fungal"] += 1
                                break

    # ========================================
    # VIPER ABILITIES
    # ========================================
    async def _viper_abilities(self, game_time: float):
        """Viper: Abduct + Blinding Cloud + Parasitic Bomb"""
        vipers = self.bot.units(UnitTypeId.VIPER).filter(lambda v: v.energy >= 75)
        if not vipers:
            return

        for viper in vipers:
            # 1. Parasitic Bomb (공중 유닛 밀집)
            if viper.energy >= 125:
                air_enemies = self.bot.enemy_units.filter(lambda u: u.is_flying).closer_than(8, viper)
                if air_enemies.amount >= 3:
                    abilities = await self.bot.get_available_abilities(viper)
                    if AbilityId.PARASITICBOMB_PARASITICBOMB in abilities:
                        if self._can_use_ability(viper.tag, "parasitic_bomb", game_time, self.PARASITIC_BOMB_CD):
                            target = air_enemies.closest_to(viper)
                            self.bot.do(viper(AbilityId.PARASITICBOMB_PARASITICBOMB, target))
                            self._record_ability(viper.tag, "parasitic_bomb", game_time)
                            self.ability_stats["parasitic_bomb"] += 1
                            continue

            # 2. Abduct (고가치 유닛 끌어오기)
            if viper.energy >= 75:
                high_value = self.bot.enemy_units.filter(
                    lambda u: u.type_id in {
                        UnitTypeId.SIEGETANKSIEGED, UnitTypeId.COLOSSUS, UnitTypeId.TEMPEST,
                        UnitTypeId.CARRIER, UnitTypeId.BATTLECRUISER
                    }
                ).closer_than(9, viper)

                if high_value:
                    target = high_value.closest_to(viper)
                    abilities = await self.bot.get_available_abilities(viper)
                    if AbilityId.EFFECT_ABDUCT in abilities:
                        if self._can_use_ability(viper.tag, "abduct", game_time, self.ABDUCT_CD):
                            self.bot.do(viper(AbilityId.EFFECT_ABDUCT, target))
                            self._record_ability(viper.tag, "abduct", game_time)
                            self.ability_stats["abduct"] += 1
                            continue

            # 3. Blinding Cloud (원거리 유닛 무력화)
            if viper.energy >= 100:
                ranged_enemies = self.bot.enemy_units.filter(
                    lambda u: u.type_id in {
                        UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.STALKER,
                        UnitTypeId.HYDRALISK, UnitTypeId.ROACH
                    }
                ).closer_than(11, viper)

                if ranged_enemies.amount >= 6:
                    abilities = await self.bot.get_available_abilities(viper)
                    if AbilityId.BLINDINGCLOUD_BLINDINGCLOUD in abilities:
                        if self._can_use_ability(viper.tag, "blinding_cloud", game_time, self.BLINDING_CLOUD_CD):
                            center = ranged_enemies.center
                            self.bot.do(viper(AbilityId.BLINDINGCLOUD_BLINDINGCLOUD, center))
                            self._record_ability(viper.tag, "blinding_cloud", game_time)
                            self.ability_stats["blinding_cloud"] += 1

    # ========================================
    # BANELING ABILITIES
    # ========================================
    async def _baneling_abilities(self, game_time: float):
        """Baneling: Explode (최적 타이밍 자폭)"""
        banelings = self.bot.units(UnitTypeId.BANELING)
        if not banelings:
            return

        for baneling in banelings:
            # 밀집 유닛 탐지 (3명 이상)
            enemies = self.bot.enemy_units.closer_than(2.2, baneling)  # 자폭 반경
            if enemies.amount >= 3:
                abilities = await self.bot.get_available_abilities(baneling)
                if AbilityId.EFFECT_EXPLODE in abilities:
                    self.bot.do(baneling(AbilityId.EFFECT_EXPLODE))
                    self.ability_stats["baneling_explode"] += 1

    # ========================================
    # OVERSEER ABILITIES
    # ========================================
    async def _overseer_abilities(self, game_time: float):
        """Overseer: Contaminate + Changeling"""
        overseers = self.bot.units(UnitTypeId.OVERSEER).filter(lambda o: o.energy >= 75)
        if not overseers:
            return

        for overseer in overseers:
            # 1. Contaminate (적 생산 건물 무력화)
            if overseer.energy >= 75:
                production = self.bot.enemy_structures.filter(
                    lambda s: s.type_id in {
                        UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT,
                        UnitTypeId.GATEWAY, UnitTypeId.ROBOTICSFACILITY, UnitTypeId.STARGATE,
                        UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE
                    }
                ).closer_than(7, overseer)

                if production:
                    target = production.closest_to(overseer)
                    abilities = await self.bot.get_available_abilities(overseer)
                    if AbilityId.CONTAMINATE_CONTAMINATE in abilities:
                        if self._can_use_ability(overseer.tag, "contaminate", game_time, self.CONTAMINATE_CD):
                            self.bot.do(overseer(AbilityId.CONTAMINATE_CONTAMINATE, target))
                            self._record_ability(overseer.tag, "contaminate", game_time)
                            self.ability_stats["contaminate"] += 1
                            continue

            # 2. Changeling (정찰)
            if overseer.energy >= 50:
                abilities = await self.bot.get_available_abilities(overseer)
                if AbilityId.SPAWNCHANGELING_SPAWNCHANGELING in abilities:
                    self.bot.do(overseer(AbilityId.SPAWNCHANGELING_SPAWNCHANGELING))
                    self.ability_stats["changeling"] += 1

    # ========================================
    # CORRUPTOR ABILITIES
    # ========================================
    async def _corruptor_abilities(self, game_time: float):
        """Corruptor: Caustic Spray (건물 피해)"""
        corruptors = self.bot.units(UnitTypeId.CORRUPTOR).filter(lambda c: c.energy >= 75)
        if not corruptors:
            return

        for corruptor in corruptors:
            # 적 건물에 Caustic Spray 사용
            enemy_structures = self.bot.enemy_structures.closer_than(6, corruptor)
            if enemy_structures:
                target = enemy_structures.closest_to(corruptor)
                abilities = await self.bot.get_available_abilities(corruptor)
                if AbilityId.CAUSTICSPRAY_CAUSTICSPRAY in abilities:
                    if self._can_use_ability(corruptor.tag, "caustic_spray", game_time, self.CAUSTIC_SPRAY_CD):
                        self.bot.do(corruptor(AbilityId.CAUSTICSPRAY_CAUSTICSPRAY, target))
                        self._record_ability(corruptor.tag, "caustic_spray", game_time)
                        self.ability_stats["caustic_spray"] += 1

    # ========================================
    # SWARM HOST ABILITIES
    # ========================================
    async def _swarmhost_abilities(self, game_time: float):
        """Swarm Host: Spawn Locusts"""
        swarmhosts = self.bot.units(UnitTypeId.SWARMHOSTMP)
        if not swarmhosts:
            return

        for host in swarmhosts:
            # 적이 근처에 있으면 메뚜기 생성
            enemies = self.bot.enemy_units.closer_than(15, host)
            if enemies:
                abilities = await self.bot.get_available_abilities(host)
                if AbilityId.EFFECT_SPAWNLOCUSTS in abilities:
                    if self._can_use_ability(host.tag, "locust", game_time, self.LOCUST_CD):
                        self.bot.do(host(AbilityId.EFFECT_SPAWNLOCUSTS, enemies.center))
                        self._record_ability(host.tag, "locust", game_time)
                        self.ability_stats["locust"] += 1

    # ========================================
    # TACTICAL BURROW
    # ========================================
    async def _tactical_burrow(self, game_time: float):
        """전술적 잠복: Lurker, Infestor, Swarm Host"""

        # === 1. LURKER: 적 근처에서 잠복 (공격 전 필수) ===
        lurkers = self.bot.units(UnitTypeId.LURKERMP).filter(lambda l: not l.is_burrowed)
        for lurker in lurkers:
            # 적이 사거리 내에 있거나 근처에 있으면 잠복
            enemies_nearby = self.bot.enemy_units.closer_than(10, lurker)
            enemy_structures_nearby = self.bot.enemy_structures.closer_than(12, lurker)

            if enemies_nearby or enemy_structures_nearby:
                # 이미 잠복 명령을 내렸는지 확인
                if lurker.tag not in self.burrowed_units:
                    abilities = await self.bot.get_available_abilities(lurker)
                    if AbilityId.BURROWDOWN_LURKER in abilities:
                        self.bot.do(lurker(AbilityId.BURROWDOWN_LURKER))
                        self.burrowed_units.add(lurker.tag)
                        self.ability_stats["lurker_burrow"] += 1
                        self.logger.info(f"[LURKER] Burrowing before attack at {lurker.position}")

        # === 2. INFESTOR: 적이 가까우면 잠복 (은폐) ===
        infestors = self.bot.units(UnitTypeId.INFESTOR).filter(lambda i: not i.is_burrowed and i.energy >= 50)
        for infestor in infestors:
            # 적이 10거리 내에 있으면 잠복
            enemies = self.bot.enemy_units.closer_than(10, infestor)
            if enemies.amount >= 3:  # 적이 3명 이상
                if infestor.tag not in self.burrowed_units:
                    abilities = await self.bot.get_available_abilities(infestor)
                    if AbilityId.BURROWDOWN_INFESTOR in abilities:
                        self.bot.do(infestor(AbilityId.BURROWDOWN_INFESTOR))
                        self.burrowed_units.add(infestor.tag)
                        self.ability_stats["infestor_burrow"] += 1

        # === 3. SWARM HOST: 메뚜기 생성 전 잠복 ===
        swarmhosts = self.bot.units(UnitTypeId.SWARMHOSTMP).filter(lambda s: not s.is_burrowed)
        for host in swarmhosts:
            # 적이 15거리 내에 있으면 잠복 (메뚜기 생성 준비)
            enemies = self.bot.enemy_units.closer_than(15, host)
            if enemies:
                if host.tag not in self.burrowed_units:
                    abilities = await self.bot.get_available_abilities(host)
                    if AbilityId.BURROWDOWN_SWARMHOST in abilities:
                        self.bot.do(host(AbilityId.BURROWDOWN_SWARMHOST))
                        self.burrowed_units.add(host.tag)
                        self.ability_stats["swarmhost_burrow"] += 1

        # === 4. 잠복 해제 조건 체크 (필요시) ===
        # Infestor: 적이 멀어지면 잠복 해제하여 이동
        burrowed_infestors = self.bot.units(UnitTypeId.INFESTORBURROWED)
        for infestor in burrowed_infestors:
            enemies = self.bot.enemy_units.closer_than(8, infestor)
            if not enemies:  # 적이 없으면 해제
                abilities = await self.bot.get_available_abilities(infestor)
                if AbilityId.BURROWUP_INFESTOR in abilities:
                    self.bot.do(infestor(AbilityId.BURROWUP_INFESTOR))
                    if infestor.tag in self.burrowed_units:
                        self.burrowed_units.remove(infestor.tag)

    # ========================================
    # OVERLORD CREEP HARASSMENT
    # ========================================
    async def _overlord_creep_harass(self, game_time: float):
        """대군주로 적 기지에 크립 생성 (건설 방해)"""
        # Lair 업그레이드가 필요
        if not self.bot.structures(UnitTypeId.LAIR).ready and not self.bot.structures(UnitTypeId.HIVE).ready:
            return

        overlords = self.bot.units(UnitTypeId.OVERLORDTRANSPORT)  # Generate Creep 가능한 대군주
        if not overlords:
            return

        for overlord in overlords:
            # 적 기지 근처 확인
            enemy_bases = self.bot.enemy_structures.filter(
                lambda s: s.type_id in {UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
                                       UnitTypeId.PLANETARYFORTRESS, UnitTypeId.NEXUS,
                                       UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE}
            )

            if not enemy_bases:
                continue

            closest_enemy_base = enemy_bases.closest_to(overlord)

            # 적 기지 근처 12 거리 이내
            if overlord.distance_to(closest_enemy_base) < 12:
                abilities = await self.bot.get_available_abilities(overlord)
                if AbilityId.GENERATECREEP_GENERATECREEP in abilities:
                    # 적 기지 확장 위치에 크립 생성
                    target_position = closest_enemy_base.position.towards(self.bot.game_info.map_center, 8)
                    self.bot.do(overlord(AbilityId.GENERATECREEP_GENERATECREEP, target_position))
                    self.ability_stats["overlord_creep"] += 1
                    self.logger.info(f"[OVERLORD] Creep harass at enemy base {closest_enemy_base.position}")
                    break  # 한 번에 하나씩

    # ========================================
    # HELPER FUNCTIONS
    # ========================================
    def _can_use_ability(self, unit_tag: int, ability_name: str, game_time: float, cooldown: float) -> bool:
        """스킬 쿨다운 확인"""
        if unit_tag not in self.last_ability_used:
            return True

        if ability_name not in self.last_ability_used[unit_tag]:
            return True

        last_use = self.last_ability_used[unit_tag][ability_name]
        return (game_time - last_use) >= cooldown

    def _record_ability(self, unit_tag: int, ability_name: str, game_time: float):
        """스킬 사용 기록"""
        if unit_tag not in self.last_ability_used:
            self.last_ability_used[unit_tag] = {}

        self.last_ability_used[unit_tag][ability_name] = game_time

    def _print_stats(self, game_time: float):
        """통계 출력"""
        total = sum(self.ability_stats.values())
        if total == 0:
            return

        self.logger.info(f"[ABILITIES] [{int(game_time)}s] Total: {total}")
        for ability, count in sorted(self.ability_stats.items(), key=lambda x: -x[1]):
            if count > 0:
                self.logger.info(f"  {ability}: {count}")
