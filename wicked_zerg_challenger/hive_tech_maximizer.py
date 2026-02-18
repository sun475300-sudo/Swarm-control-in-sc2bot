# -*- coding: utf-8 -*-
"""
Hive Tech Maximizer - 군락 이후 고급 기술 극대화

군락(Hive) 완성 후:
1. Greater Spire (Brood Lord)
2. Ultralisk Cavern (Ultralisk)
3. 추가 생산 건물 (Spire x2, Roach Warren x3 등)
4. 고급 유닛 대량 생산
"""

from typing import Dict, Set
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from utils.logger import get_logger


class HiveTechMaximizer:
    """군락 기술 극대화 시스템"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("HiveTech")

        # Hive 상태 추적
        self.hive_active = False
        self.hive_completion_time = 0.0

        # 건물 건설 상태
        self.buildings_built: Set[UnitTypeId] = set()

        # 목표 건물 개수 (Hive 이후)
        self.target_buildings = {
            UnitTypeId.GREATERSPIRE: 1,        # Greater Spire (Brood Lord)
            UnitTypeId.ULTRALISKCAVERN: 1,     # Ultralisk Cavern
            UnitTypeId.SPIRE: 2,                # Spire x2 (빠른 공중 유닛)
            UnitTypeId.ROACHWARREN: 3,          # Roach Warren x3 (Ravager 대량)
            UnitTypeId.HYDRALISKDEN: 2,         # Hydra Den x2 (Lurker 대량)
            UnitTypeId.INFESTATIONPIT: 1,       # Infestation Pit (Infestor)
            UnitTypeId.EVOLUTIONCHAMBER: 2,     # Evolution Chamber x2 (업그레이드)
        }

        # 우선 생산 유닛 (Hive 이후)
        self.priority_units = {
            UnitTypeId.ULTRALISK: 8,        # Ultralisk 8마리
            UnitTypeId.BROODLORD: 6,        # Brood Lord 6마리
            UnitTypeId.LURKERMP: 12,        # Lurker 12마리
            UnitTypeId.VIPER: 4,            # Viper 4마리
            UnitTypeId.INFESTOR: 6,         # Infestor 6마리
        }

        # 통계
        self.advanced_buildings_built = 0
        self.advanced_units_produced = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 44프레임(약 2초)마다 실행
            if iteration % 44 != 0:
                return

            game_time = self.bot.time

            # 1. Hive 상태 확인
            self._check_hive_status(game_time)

            # Hive가 없으면 스킵
            if not self.hive_active:
                return

            # 2. 고급 건물 건설
            await self._build_advanced_structures(game_time)

            # 3. 고급 유닛 생산
            await self._produce_advanced_units(game_time)

            # 4. 업그레이드 진행
            await self._research_advanced_upgrades()

            # 통계 출력 (60초마다)
            if iteration % 1320 == 0:
                self._print_statistics(game_time)

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[HIVE_TECH] Error: {e}")

    def _check_hive_status(self, game_time: float):
        """Hive 상태 확인"""
        hive_structures = self.bot.structures(UnitTypeId.HIVE).ready

        if hive_structures and not self.hive_active:
            self.hive_active = True
            self.hive_completion_time = game_time
            self.logger.info(f"[HIVE] HIVE ACTIVE at {int(game_time)}s! Starting advanced tech!")

    def _analyze_enemy_composition(self) -> str:
        """
        ★ 적 병력 구성 분석 (Tech Path Selection) ★

        Returns:
            "anti_air": 공중 유닛 카운터 필요
            "anti_ground_heavy": 중장갑 지상 유닛 카운터 필요
            "anti_bio": 경장갑 다수 유닛 카운터 필요
            "balanced": 균형 잡힌 조합
        """
        if not hasattr(self.bot, "enemy_units"):
            return "balanced"

        enemy_units = self.bot.enemy_units
        if not enemy_units:
            return "balanced"

        # ★ 공중 유닛 카운트 ★
        air_units = enemy_units.filter(lambda u: u.is_flying)
        air_count = air_units.amount

        # 고가치 공중 유닛
        high_value_air = {
            UnitTypeId.CARRIER, UnitTypeId.BATTLECRUISER, UnitTypeId.TEMPEST,
            UnitTypeId.BROODLORD, UnitTypeId.VOIDRAY
        }
        critical_air = sum(1 for u in air_units if u.type_id in high_value_air)

        # ★ 중장갑 지상 유닛 카운트 ★
        heavy_ground = {
            UnitTypeId.THOR, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED,
            UnitTypeId.IMMORTAL, UnitTypeId.COLOSSUS, UnitTypeId.ULTRALISK,
            UnitTypeId.ARCHON
        }
        heavy_count = sum(1 for u in enemy_units if u.type_id in heavy_ground)

        # ★ 경장갑 다수 유닛 카운트 ★
        bio_units = {
            UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.ZEALOT,
            UnitTypeId.ZERGLING, UnitTypeId.HYDRALISK, UnitTypeId.ROACH
        }
        bio_count = sum(1 for u in enemy_units if u.type_id in bio_units)

        # ★ Tech Path 결정 ★
        total_units = enemy_units.amount

        if total_units < 5:
            return "balanced"  # 초반은 균형 잡힌 조합

        # 공중 위협이 크면 anti_air
        if critical_air >= 3 or (air_count / total_units > 0.4):
            return "anti_air"

        # 중장갑이 많으면 anti_ground_heavy
        if heavy_count >= 4 or (heavy_count / total_units > 0.3):
            return "anti_ground_heavy"

        # 바이오닉이 많으면 anti_bio
        if bio_count >= 15 or (bio_count / total_units > 0.6):
            return "anti_bio"

        return "balanced"

    async def _build_advanced_structures(self, game_time: float):
        """고급 건물 건설"""
        if not self.bot.townhalls.exists:
            return

        main_base = self.bot.townhalls.first

        for building_type, target_count in self.target_buildings.items():
            current = self.bot.structures(building_type).amount
            pending = self.bot.already_pending(building_type)
            total = current + pending

            if total >= target_count:
                continue

            # 자원 확인
            if not self.bot.can_afford(building_type):
                continue

            # Greater Spire는 Spire에서 업그레이드
            if building_type == UnitTypeId.GREATERSPIRE:
                spires = self.bot.structures(UnitTypeId.SPIRE).ready.idle
                if spires:
                    spire = spires.first
                    abilities = await self.bot.get_available_abilities(spire)
                    if AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE in abilities:
                        self.bot.do(spire(AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE))
                        self.logger.info("[HIVE] Upgrading to Greater Spire!")
                        self.advanced_buildings_built += 1
                continue

            # Building Coordination 확인
            if hasattr(self.bot, "building_coord") and self.bot.building_coord:
                if not self.bot.building_coord.can_build(building_type):
                    continue

            # 건설 위치
            position = main_base.position.towards(self.bot.game_info.map_center, 8)

            try:
                await self.bot.build(building_type, near=position)

                if hasattr(self.bot, "building_coord"):
                    self.bot.building_coord.request_building(building_type, "HiveTech")

                self.logger.info(f"[HIVE] Building {building_type.name} ({total+1}/{target_count})")
                self.advanced_buildings_built += 1
                break  # 한 번에 하나씩

            except Exception as e:
                continue

    async def _produce_advanced_units(self, game_time: float):
        """
        고급 유닛 생산 (★ IMPROVED: Tech Path Selection ★)
        적 병력 구성에 따라 최적의 유닛 선택
        """
        # ★ 적 병력 구성 분석 ★
        tech_path = self._analyze_enemy_composition()

        # ★ Tech Path별 우선순위 생산 ★
        if tech_path == "anti_air":
            # vs Air Heavy (Carrier, BC, Mutalisk)
            await self._produce_vipers()      # Abduct high-value air
            await self._morph_broodlords()    # Long-range air counter
            await self._produce_infestors()   # Fungal flying units

        elif tech_path == "anti_ground_heavy":
            # vs Ground Heavy (Thor, Siege Tank, Immortal, Colossus)
            await self._produce_ultralisks()  # Tank ground units
            await self._produce_vipers()      # Abduct key units
            await self._morph_lurkers()       # Long-range siege

        elif tech_path == "anti_bio":
            # vs Bio (Marine, Marauder, Zealot, Hydralisk)
            await self._produce_infestors()   # Fungal clumps
            await self._morph_lurkers()       # AoE damage
            await self._produce_ultralisks()  # Splash tank

        else:
            # Balanced / Unknown → Standard production
            await self._produce_vipers()
            await self._produce_infestors()
            await self._morph_broodlords()
            await self._produce_ultralisks()
            await self._morph_lurkers()

    async def _produce_ultralisks(self):
        """Ultralisk 생산"""
        caverns = self.bot.structures(UnitTypeId.ULTRALISKCAVERN).ready
        if not caverns:
            return

        current_ultralisks = self.bot.units(UnitTypeId.ULTRALISK).amount
        target = self.priority_units[UnitTypeId.ULTRALISK]

        if current_ultralisks >= target:
            return

        # 라바로 생산
        if self.bot.can_afford(UnitTypeId.ULTRALISK):
            larva = self.bot.larva.idle
            if larva:
                self.bot.do(larva.first.train(UnitTypeId.ULTRALISK))
                self.logger.info(f"[HIVE] Training Ultralisk ({current_ultralisks+1}/{target})")
                self.advanced_units_produced += 1

    async def _morph_broodlords(self):
        """Brood Lord 변태"""
        if not self.bot.structures(UnitTypeId.GREATERSPIRE).ready:
            return

        current_broodlords = self.bot.units(UnitTypeId.BROODLORD).amount
        target = self.priority_units[UnitTypeId.BROODLORD]

        if current_broodlords >= target:
            return

        # Corruptor를 Brood Lord로 변태
        corruptors = self.bot.units(UnitTypeId.CORRUPTOR).idle
        if corruptors and self.bot.can_afford(UnitTypeId.BROODLORD):
            corruptor = corruptors.first
            abilities = await self.bot.get_available_abilities(corruptor)
            if AbilityId.MORPHTOBROODLORD_BROODLORD in abilities:
                self.bot.do(corruptor(AbilityId.MORPHTOBROODLORD_BROODLORD))
                self.logger.info(f"[HIVE] Morphing Brood Lord ({current_broodlords+1}/{target})")
                self.advanced_units_produced += 1

    async def _morph_lurkers(self):
        """Lurker 변태"""
        if not self.bot.structures(UnitTypeId.LURKERDENMP).ready:
            return

        current_lurkers = self.bot.units(UnitTypeId.LURKERMP).amount
        target = self.priority_units[UnitTypeId.LURKERMP]

        if current_lurkers >= target:
            return

        # Hydralisk를 Lurker로 변태
        hydralisks = self.bot.units(UnitTypeId.HYDRALISK).idle
        if hydralisks and self.bot.can_afford(UnitTypeId.LURKERMP):
            hydra = hydralisks.first
            abilities = await self.bot.get_available_abilities(hydra)
            if AbilityId.MORPH_LURKER in abilities:
                self.bot.do(hydra(AbilityId.MORPH_LURKER))
                self.logger.info(f"[HIVE] Morphing Lurker ({current_lurkers+1}/{target})")
                self.advanced_units_produced += 1

    async def _produce_vipers(self):
        """Viper 생산"""
        if not self.bot.structures(UnitTypeId.HIVE).ready:
            return

        current_vipers = self.bot.units(UnitTypeId.VIPER).amount
        target = self.priority_units[UnitTypeId.VIPER]

        if current_vipers >= target:
            return

        if self.bot.can_afford(UnitTypeId.VIPER):
            larva = self.bot.larva.idle
            if larva:
                self.bot.do(larva.first.train(UnitTypeId.VIPER))
                self.logger.info(f"[HIVE] Training Viper ({current_vipers+1}/{target})")
                self.advanced_units_produced += 1

    async def _produce_infestors(self):
        """Infestor 생산"""
        if not self.bot.structures(UnitTypeId.INFESTATIONPIT).ready:
            return

        current_infestors = self.bot.units(UnitTypeId.INFESTOR).amount
        target = self.priority_units[UnitTypeId.INFESTOR]

        if current_infestors >= target:
            return

        if self.bot.can_afford(UnitTypeId.INFESTOR):
            larva = self.bot.larva.idle
            if larva:
                self.bot.do(larva.first.train(UnitTypeId.INFESTOR))
                self.logger.info(f"[HIVE] Training Infestor ({current_infestors+1}/{target})")
                self.advanced_units_produced += 1

    async def _research_advanced_upgrades(self):
        """고급 업그레이드 연구"""
        # ★ Adrenal Glands (Zergling 공속 +20%) - 가장 중요! ★
        if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            pool = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.idle
            if pool:
                if self.bot.can_afford(UpgradeId.ZERGLINGATTACKSPEED):
                    if UpgradeId.ZERGLINGATTACKSPEED not in self.bot.state.upgrades:
                        abilities = await self.bot.get_available_abilities(pool.first)
                        if AbilityId.RESEARCH_ZERGLINGADRENALGLANDS in abilities:
                            self.bot.do(pool.first(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS))
                            self.logger.info("[HIVE] ★ Researching Adrenal Glands! (Zergling attack speed +20%) ★")
                            return  # 한 번에 하나씩

        # Chitinous Plating (Ultralisk 방어력)
        if self.bot.structures(UnitTypeId.ULTRALISKCAVERN).ready:
            cavern = self.bot.structures(UnitTypeId.ULTRALISKCAVERN).ready.idle
            if cavern:
                if self.bot.can_afford(UpgradeId.CHITINOUSPLATING):
                    if UpgradeId.CHITINOUSPLATING not in self.bot.state.upgrades:
                        abilities = await self.bot.get_available_abilities(cavern.first)
                        if AbilityId.RESEARCH_CHITINOUSPLATING in abilities:
                            self.bot.do(cavern.first(AbilityId.RESEARCH_CHITINOUSPLATING))
                            self.logger.info("[HIVE] Researching Chitinous Plating!")
                            return

        # Anabolic Synthesis (Ultralisk 이속)
        if self.bot.structures(UnitTypeId.ULTRALISKCAVERN).ready:
            cavern = self.bot.structures(UnitTypeId.ULTRALISKCAVERN).ready.idle
            if cavern:
                if self.bot.can_afford(UpgradeId.ANABOLICSYNTHESIS):
                    if UpgradeId.ANABOLICSYNTHESIS not in self.bot.state.upgrades:
                        abilities = await self.bot.get_available_abilities(cavern.first)
                        if AbilityId.RESEARCH_ANABOLICSYNTHESIS in abilities:
                            self.bot.do(cavern.first(AbilityId.RESEARCH_ANABOLICSYNTHESIS))
                            self.logger.info("[HIVE] Researching Anabolic Synthesis!")
                            return

    def _print_statistics(self, game_time: float):
        """통계 출력"""
        if not self.hive_active:
            return

        time_since_hive = game_time - self.hive_completion_time

        self.logger.info(
            f"[HIVE] [{int(game_time)}s] Time since Hive: {int(time_since_hive)}s"
        )
        self.logger.info(
            f"  Buildings: {self.advanced_buildings_built}, "
            f"Units: {self.advanced_units_produced}"
        )

        # 현재 유닛 카운트
        for unit_type in self.priority_units.keys():
            current = self.bot.units(unit_type).amount
            target = self.priority_units[unit_type]
            self.logger.info(f"  {unit_type.name}: {current}/{target}")
