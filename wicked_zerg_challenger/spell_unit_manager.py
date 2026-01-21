# -*- coding: utf-8 -*-
"""
Spell Unit Manager - Optimized targeting for spell units (Infestor, Viper, Ravager)
"""

from typing import TYPE_CHECKING, List, Optional, Dict

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.position import Point2
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
else:
    try:
        from sc2.unit import Unit
        from sc2.position import Point2
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.ids.ability_id import AbilityId
    except ImportError:
        Unit = None
        Point2 = None
        UnitTypeId = None
        AbilityId = None


class SpellUnitManager:
    def __init__(self, bot: "WickedZergBotPro"):
        self.bot = bot
        self.last_spell_update_frame: int = 0
        self.spell_update_interval: int = 16
        self.infestor_last_spell: Dict[int, float] = {}
        self.viper_last_spell: Dict[int, float] = {}
        self.ravager_last_bile: Dict[int, float] = {}
        self.NEURAL_PARASITE_COOLDOWN = 1.5
        self.FUNGAL_GROWTH_COOLDOWN = 1.0
        self.ABDUCT_COOLDOWN = 1.0
        self.PARASITIC_BOMB_COOLDOWN = 1.0
        self.BLINDING_CLOUD_COOLDOWN = 1.0
        self.CORROSIVE_BILE_COOLDOWN = 0.71
        self.bile_lead_time = getattr(self.bot, "bile_lead_time", 1.7)
        self.bile_structure_bonus = getattr(self.bot, "bile_structure_bonus", 80.0)
        self.bile_forcefield_bonus = getattr(self.bot, "bile_forcefield_bonus", 120.0)
        self.bile_siegetank_bonus = getattr(self.bot, "bile_siegetank_bonus", 100.0)

    async def update(self, iteration: int):
        if iteration - self.last_spell_update_frame < self.spell_update_interval:
            return
        self.last_spell_update_frame = iteration
        await self._update_infestors()
        await self._update_vipers()
        await self._update_ravagers()

    async def _update_infestors(self):
        b = self.bot
        infestors = b.units(UnitTypeId.INFESTOR).ready
        if not infestors.exists:
            return
        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return
        current_time = b.time
        for infestor in infestors:
            last_spell = self.infestor_last_spell.get(infestor.tag, 0.0)
            time_since = current_time - last_spell

            if time_since >= self.NEURAL_PARASITE_COOLDOWN:
                high_value = [
                    e for e in enemy_units
                    if e.type_id in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.COLOSSUS,
                        UnitTypeId.BATTLECRUISER,
                        UnitTypeId.CARRIER,
                        UnitTypeId.HIGHTEMPLAR,
                        UnitTypeId.RAVEN,
                        UnitTypeId.LURKER,
                        UnitTypeId.IMMORTAL,
                    ]
                ]
                nearby = self._find_nearby_targets(infestor, high_value, 9.0)
                if nearby and infestor.energy >= 100:
                    try:
                        await b.do(infestor(AbilityId.NEURALPARASITE_NEURALPARASITE, nearby[0]))
                        self.infestor_last_spell[infestor.tag] = current_time
                        continue
                    except Exception:
                        pass

            if time_since >= self.FUNGAL_GROWTH_COOLDOWN:
                nearby = self._find_nearby_targets(infestor, enemy_units, 10.0)
                if len(nearby) >= 3 and infestor.energy >= 75:
                    best = self._find_best_fungal_target(infestor, nearby)
                    if best:
                        try:
                            await b.do(infestor(AbilityId.FUNGALGROWTH_FUNGALGROWTH, best))
                            self.infestor_last_spell[infestor.tag] = current_time
                        except Exception:
                            pass

            if infestor.energy < 50:
                await self._retreat_low_energy_unit(infestor)

    async def _update_vipers(self):
        b = self.bot
        vipers = b.units(UnitTypeId.VIPER).ready
        if not vipers.exists:
            return
        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return
        current_time = b.time
        for viper in vipers:
            last_spell = self.viper_last_spell.get(viper.tag, 0.0)
            time_since = current_time - last_spell

            if time_since >= self.ABDUCT_COOLDOWN:
                high_value = [
                    e for e in enemy_units
                    if e.type_id in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.COLOSSUS,
                        UnitTypeId.THOR,
                        UnitTypeId.BATTLECRUISER,
                    ]
                ]
                nearby = self._find_nearby_targets(viper, high_value, 11.0)
                if nearby and viper.energy >= 75:
                    try:
                        await b.do(viper(AbilityId.ABDUCT_ABDUCT, nearby[0]))
                        self.viper_last_spell[viper.tag] = current_time
                        continue
                    except Exception:
                        pass

            if time_since >= self.PARASITIC_BOMB_COOLDOWN:
                air_targets = [
                    e for e in enemy_units
                    if e.is_flying and e.type_id in [
                        UnitTypeId.BANSHEE,
                        UnitTypeId.VIKING,
                        UnitTypeId.MEDIVAC,
                        UnitTypeId.VOIDRAY,
                        UnitTypeId.PHOENIX,
                        UnitTypeId.CARRIER,
                    ]
                ]
                nearby = self._find_nearby_targets(viper, air_targets, 14.0)
                if nearby and viper.energy >= 125:
                    try:
                        await b.do(viper(AbilityId.PARASITICBOMB_PARASITICBOMB, nearby[0]))
                        self.viper_last_spell[viper.tag] = current_time
                        continue
                    except Exception:
                        pass

            if time_since >= self.BLINDING_CLOUD_COOLDOWN:
                ground_targets = [
                    e for e in enemy_units
                    if not e.is_flying and e.type_id in [
                        UnitTypeId.SIEGETANKSIEGED,
                        UnitTypeId.MARINE,
                        UnitTypeId.MARAUDER,
                    ]
                ]
                nearby = self._find_nearby_targets(viper, ground_targets, 12.0)
                if nearby and viper.energy >= 100:
                    best = self._find_best_blinding_cloud_position(viper, nearby)
                    if best:
                        try:
                            await b.do(viper(AbilityId.BLINDINGCLOUD_BLINDINGCLOUD, best))
                            self.viper_last_spell[viper.tag] = current_time
                        except Exception:
                            pass

            if viper.energy < 50:
                await self._retreat_low_energy_unit(viper)

    async def _update_ravagers(self):
        b = self.bot
        ravagers = b.units(UnitTypeId.RAVAGER).ready
        if not ravagers.exists:
            return
        enemy_units = getattr(b, "enemy_units", [])
        if not enemy_units:
            return
        current_time = b.time
        for ravager in ravagers:
            last_bile = self.ravager_last_bile.get(ravager.tag, 0.0)
            if current_time - last_bile < self.CORROSIVE_BILE_COOLDOWN:
                continue
            nearby = self._find_nearby_targets(ravager, enemy_units, 12.0)
            if not nearby:
                continue
            best = self._find_best_bile_target(ravager, nearby)
            if best:
                try:
                    await b.do(ravager(AbilityId.CORROSIVEBILE_CORROSIVEBILE, best))
                    self.ravager_last_bile[ravager.tag] = current_time
                except Exception:
                    pass

    def _find_nearby_targets(self, unit: Unit, targets: List[Unit], max_range: float) -> List[Unit]:
        if hasattr(targets, "closer_than"):
            return list(targets.closer_than(max_range, unit.position))
        return [e for e in targets if unit.distance_to(e.position) < max_range]

    async def _retreat_low_energy_unit(self, unit: Unit):
        b = self.bot
        if not b.townhalls.exists:
            return
        safe_pos = b.townhalls.first.position

        # Viper consume
        if unit.type_id == UnitTypeId.VIPER:
            consumable_types = [
                UnitTypeId.HYDRALISKDEN,
                UnitTypeId.SPIRE,
                UnitTypeId.EVOLUTIONCHAMBER,
                UnitTypeId.HATCHERY,
                UnitTypeId.LAIR,
                UnitTypeId.HIVE,
            ]
            consumables = b.units.filter(
                lambda u: u.type_id in consumable_types
                and getattr(u, "health_percentage", 1.0) >= 0.2
            )
            if consumables.exists:
                building = consumables.closest_to(unit.position)
                if unit.distance_to(building.position) < 5.0:
                    try:
                        await b.do(unit(AbilityId.CONSUME_CONSUME, building))
                        return
                    except Exception:
                        pass

        if unit.distance_to(safe_pos) > 10.0:
            await b.do(unit.move(safe_pos))

    def _find_best_fungal_target(self, infestor: Unit, enemies: List[Unit]) -> Optional[Point2]:
        best_pos = None
        max_hits = 0
        for enemy in enemies[:10]:
            hits = sum(1 for e in enemies if e.distance_to(enemy.position) <= 2.5)
            if hits > max_hits:
                max_hits = hits
                best_pos = enemy.position
        return best_pos

    def _find_best_blinding_cloud_position(self, viper: Unit, enemies: List[Unit]) -> Optional[Point2]:
        if len(enemies) == 1:
            return enemies[0].position
        total_x = sum(e.position.x for e in enemies)
        total_y = sum(e.position.y for e in enemies)
        return Point2((total_x / len(enemies), total_y / len(enemies)))

    def _find_best_bile_target(self, ravager: Unit, enemies: List[Unit]) -> Optional[Point2]:
        best_pos = None
        best_score = 0.0
        for enemy in enemies[:15]:
            # 예측 사격: 이동 벡터 기반 리드
            target_pos = self._predict_position(enemy, lead_time=self.bile_lead_time)
            nearby_count = sum(1 for e in enemies if e.distance_to(target_pos) <= 2.5)
            structure_bonus = self.bile_structure_bonus if getattr(enemy, "is_structure", False) else 0.0

            # 고정 위협 우선 (Force Field, SiegeTank 등)
            priority_bonus = 0.0
            if hasattr(UnitTypeId, "FORCEFIELD") and enemy.type_id == UnitTypeId.FORCEFIELD:
                priority_bonus = self.bile_forcefield_bonus
            if enemy.type_id in [UnitTypeId.SIEGETANKSIEGED, UnitTypeId.SIEGETANK]:
                priority_bonus = max(priority_bonus, self.bile_siegetank_bonus)

            score = nearby_count * 20.0 + structure_bonus + priority_bonus
            if score > best_score:
                best_score = score
                best_pos = target_pos
        return best_pos if best_score >= 40.0 else None

    def _predict_position(self, unit: Unit, lead_time: float = 1.7) -> "Point2":
        """
        이동 경로 예측 (간단 리드)
        """
        pos = unit.position
        velocity = getattr(unit, "velocity", None)
        if velocity is None:
            return pos
        try:
            return pos + velocity * lead_time
        except Exception:
            return pos
