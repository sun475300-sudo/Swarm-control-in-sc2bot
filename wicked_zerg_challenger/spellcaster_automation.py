# -*- coding: utf-8 -*-
"""
SpellCaster Automation - 마법 유닛 스킬 자동화

퀸, 궤멸충, 살모사, 감염충, 감시군주의 스킬을 자동으로 사용합니다:
- 퀸: 체력 낮은 유닛 수혈 (Transfuse)
- 궤멸충: 적 밀집 지역 담즙 (Corrosive Bile)
- 살모사: 에너지 회복 (Consume), 고가치 유닛 납치 (Abduct), 흑구름 (Blinding Cloud)
- 감염충: 신경 기생충 (Neural Parasite), 진균 번식 (Fungal Growth)
- 감시군주: 무료 정찰 유닛 생성 (Changeling)

효과: 고급 유닛 활용도 0% → 100%
"""

from typing import List, Dict, Optional
from utils.logger import get_logger

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        QUEEN = "QUEEN"
        RAVAGER = "RAVAGER"
        VIPER = "VIPER"
        INFESTOR = "INFESTOR"
        OVERSEER = "OVERSEER"
        OVERLORD = "OVERLORD"
    class AbilityId:
        TRANSFUSION_TRANSFUSION = "TRANSFUSION_TRANSFUSION"
        EFFECT_CORROSIVEBILE = "EFFECT_CORROSIVEBILE"
        EFFECT_ABDUCT = "EFFECT_ABDUCT"
        EFFECT_BLINDINGCLOUD = "EFFECT_BLINDINGCLOUD"
        EFFECT_VIPERCONSUME = "EFFECT_VIPERCONSUME"
        NEURALPARASITE_NEURALPARASITE = "NEURALPARASITE_NEURALPARASITE"
        FUNGALGROWTH_FUNGALGROWTH = "FUNGALGROWTH_FUNGALGROWTH"
        SPAWNCHANGELING_SPAWNCHANGELING = "SPAWNCHANGELING_SPAWNCHANGELING"
    class UpgradeId:
        pass
    Point2 = tuple

try:
    from unit_authority_manager import UnitAuthorityManager, AuthorityLevel
except ImportError:
    UnitAuthorityManager = None
    AuthorityLevel = None


class SpellCasterAutomation:
    """
    ★ SpellCaster Automation ★

    마법 유닛들의 스킬을 자동으로 사용하여
    전투 효율을 극대화합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("SpellCaster")

        # ★ 체크 주기 ★
        self.last_check = 0
        self.check_interval = 11  # 약 0.5초마다

        # ★ 스킬 쿨다운 추적 ★
        self.last_skill_used = {}  # {unit_tag: {ability: game_time}}

        # ★ 스킬 우선순위 ★
        self.queen_transfuse_threshold = 0.35  # 체력 35% 이하
        self.ravager_min_targets = 3  # 최소 3명 이상 밀집
        self.viper_abduct_range = 9
        self.infestor_fungal_min_targets = 3  # ★ IMPROVED: 5 → 3 (실전에서 5명 밀집은 드뭄)

        # ★ 통계 ★
        self.skills_used = {
            "transfuse": 0,
            "bile": 0,
            "consume": 0,
            "abduct": 0,
            "blinding_cloud": 0,
            "neural": 0,
            "fungal": 0,
            "changeling": 0,
        }

        # ★ Authority Tracking ★
        self.active_casters: Dict[int, str] = {}  # {tag: ability_name}

    def _cleanup_authorities(self):
        """Clean up finished assignments"""
        if not hasattr(self.bot, "unit_authority"):
            return

        # Release units that are no longer casting or died
        for tag in list(self.active_casters.keys()):
            unit = self.bot.units.find_by_tag(tag)
            
            # If unit dead or idle (finished casting), release
            if not unit or (unit.is_idle and self._is_cast_finished(tag)):
                self.bot.unit_authority.release_unit(tag, "SpellCaster")
                del self.active_casters[tag]

    def _is_cast_finished(self, tag: int) -> bool:
        """Check if enough time passed since cast"""
        if tag not in self.active_casters:
            return True
            
        ability = self.active_casters[tag]
        last_used = self.last_skill_used.get(tag, {}).get(ability, 0)
        
        # Give 2 seconds for cast execution
        return (getattr(self.bot, "time", 0) - last_used) > 1.0

    async def _request_authority(self, unit, ability_name: str) -> bool:
        """Request authority for unit (SPELL_UNIT > COMBAT priority)"""
        if not hasattr(self.bot, "unit_authority"):
            return True  # No authority manager, allow

        if self.bot.unit_authority.request_unit(
            unit.tag,
            "SpellCaster",
            AuthorityLevel.SPELL_UNIT  # ★ 80 > COMBAT(70) - 스펠캐스터 우선권 ★
        ):
            self.active_casters[unit.tag] = ability_name
            return True

        return False

    def _release_authority(self, unit_tag: int) -> None:
        """Release authority after spell cast"""
        if hasattr(self.bot, "unit_authority"):
            self.bot.unit_authority.release_unit(unit_tag, "SpellCaster")
        self.active_casters.pop(unit_tag, None)

    async def on_step(self, iteration: int) -> None:
        """매 프레임 실행"""
        try:
            if iteration - self.last_check < self.check_interval:
                return

            self.last_check = iteration

            # ★ 1. 퀸 수혈 (Transfuse) ★
            await self._queen_transfuse()

            # ★ 2. 궤멸충 담즙 (Corrosive Bile) ★
            await self._ravager_bile()

            # ★ 3. 살모사 스킬 (Abduct, Blinding Cloud) ★
            await self._viper_skills()

            # ★ 4. 감염충 스킬 (Neural, Fungal) ★
            await self._infestor_skills()

            # ★ 5. 감시군주 환상 (Changeling) ★
            await self._overseer_changeling()

            # ★ 6. Authority Cleanup (매 프레임) ★
            self._cleanup_authorities()

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[SPELLCASTER] Error: {e}")

    async def _queen_transfuse(self):
        """
        퀸 수혈 (Transfuse) - 체력 낮은 유닛 치료
        """
        if not hasattr(self.bot, "units"):
            return

        queens = self.bot.units(UnitTypeId.QUEEN)
        if not queens:
            return

        for queen in queens:
            # 에너지 체크 (50 필요)
            if queen.energy < 50:
                continue

            # 쿨다운 체크
            if self._is_on_cooldown(queen.tag, "transfuse", 10):
                continue

            # 체력 낮은 유닛 찾기
            injured_units = []
            for unit in self.bot.units:
                if unit.health_percentage < self.queen_transfuse_threshold:
                    # 기계 유닛은 치료 불가
                    type_name = getattr(unit.type_id, "name", "").upper()
                    if "MECHANICAL" in type_name or "BUILDING" in type_name:
                        continue

                    if queen.distance_to(unit) < 7:  # 사거리
                        injured_units.append(unit)

            if not injured_units:
                continue

            # 가장 체력이 낮은 유닛 선택
            target = min(injured_units, key=lambda u: u.health_percentage)

            # 권한 요청 (이미 가지고 있으면 True 반환)
            if not await self._request_authority(queen, "transfuse"):
                continue

            # 수혈 실행
            abilities = await self.bot.get_available_abilities(queen)
            if AbilityId.TRANSFUSION_TRANSFUSION in abilities:
                self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, target))
                self._record_skill_use(queen.tag, "transfuse")
                self._release_authority(queen.tag)  # ★ 즉시 해제 ★
                self.skills_used["transfuse"] += 1

                game_time = getattr(self.bot, "time", 0)
                self.logger.info(
                    f"[{int(game_time)}s] ★ TRANSFUSE: {target.type_id.name} "
                    f"({target.health}/{target.health_max}) ★"
                )
                break

    async def _ravager_bile(self):
        """
        궤멸충 담즙 (Corrosive Bile) - 적 밀집 지역 공격
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        ravagers = self.bot.units(UnitTypeId.RAVAGER)
        if not ravagers:
            return

        enemy_units = self.bot.enemy_units

        for ravager in ravagers:
            # 쿨다운 체크 (7초)
            if self._is_on_cooldown(ravager.tag, "bile", 7):
                continue

            # 사거리 내 적 찾기 (사거리 9)
            enemies_in_range = enemy_units.closer_than(9, ravager)
            if not enemies_in_range:
                continue

            # 밀집 지역 찾기
            best_target, target_count = self._find_bile_target(enemies_in_range)

            if target_count < self.ravager_min_targets:
                continue

            # 권한 요청
            if not await self._request_authority(ravager, "bile"):
                continue

            # 담즙 발사
            abilities = await self.bot.get_available_abilities(ravager)
            if AbilityId.EFFECT_CORROSIVEBILE in abilities:
                self.bot.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, best_target))
                self._record_skill_use(ravager.tag, "bile")
                self._release_authority(ravager.tag)  # ★ 즉시 해제 ★
                self.skills_used["bile"] += 1

                game_time = getattr(self.bot, "time", 0)
                self.logger.info(
                    f"[{int(game_time)}s] ★ BILE: {target_count} targets ★"
                )
                break

    def _find_bile_target(self, enemies: List) -> tuple:
        """
        담즙 최적 목표 위치 찾기

        Args:
            enemies: 적 유닛 리스트

        Returns:
            (best_position, target_count)
        """
        best_pos = None
        max_count = 0

        for enemy in enemies:
            pos = enemy.position
            # 2.5 반경 내 적 개수 (담즙 효과 범위)
            nearby = sum(1 for e in enemies if e.position.distance_to(pos) < 2.5)

            if nearby > max_count:
                max_count = nearby
                best_pos = pos

        return best_pos, max_count

    async def _viper_skills(self):
        """
        살모사 스킬 (Consume, Abduct, Blinding Cloud)
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        vipers = self.bot.units(UnitTypeId.VIPER)
        if not vipers:
            return

        enemy_units = self.bot.enemy_units

        for viper in vipers:
            # ★ 0. 에너지 회복 (Consume) - 에너지 < 25 ★
            if viper.energy < 25:
                if not self._is_on_cooldown(viper.tag, "consume", 30):
                    await self._viper_consume(viper)
                    continue

            # ★ 1. 납치 (Abduct) - 75 에너지 ★
            if viper.energy >= 75:
                if not self._is_on_cooldown(viper.tag, "abduct", 15):
                    await self._viper_abduct(viper, enemy_units)
                    continue

                if not self._is_on_cooldown(viper.tag, "blinding_cloud", 20):
                    await self._viper_blinding_cloud(viper, enemy_units)
                    continue

            # ★ 3. 안전 후퇴 (Phase 18) ★
            await self._viper_safety(viper, enemy_units)

    async def _viper_abduct(self, viper, enemies):
        """
        ★★★ 살모사 납치 - 안전 검사 + 우선순위 점수 기반 ★★★

        안전 검사:
        1. 착지 지점(살모사 위치) 주변 적 5명 이상이면 거부
        2. 착지 주변 아군 5명 미만이면 거부
        3. 적 진형 가장자리 유닛 보너스
        """
        # 고가치 유닛 점수 (높을수록 우선)
        UNIT_VALUE = {
            "COLOSSUS": 10, "CARRIER": 10, "BATTLECRUISER": 10,
            "SIEGETANKSIEGED": 9, "SIEGETANK": 9, "TEMPEST": 9,
            "THOR": 8, "IMMORTAL": 8, "MOTHERSHIP": 10,
            "BROODLORD": 7, "ULTRALISK": 7,
            "LURKER": 6, "RAVAGER": 5, "DISRUPTOR": 8,
        }

        # ★ 안전 검사 1: 살모사 주변 적이 너무 많으면 납치 금지 ★
        enemies_near_viper = sum(
            1 for e in enemies if viper.distance_to(e) < 5
        )
        if enemies_near_viper >= 5:
            return

        # ★ 안전 검사 2: 살모사 주변 아군이 부족하면 납치 금지 ★
        friendlies_near = 0
        if hasattr(self.bot, "units"):
            friendlies_near = sum(
                1 for u in self.bot.units
                if u.can_attack and u.tag != viper.tag and viper.distance_to(u) < 5
            )
        if friendlies_near < 5:
            return

        # 사거리 내 고가치 유닛 점수 계산
        scored_targets = []
        for enemy in enemies:
            if viper.distance_to(enemy) > self.viper_abduct_range:
                continue

            type_name = getattr(enemy.type_id, "name", "").upper()
            base_score = UNIT_VALUE.get(type_name, 0)
            if base_score == 0:
                continue

            # ★ 진형 가장자리 보너스: 주변 4범위 내 적 적을수록 + ★
            nearby_allies_of_target = sum(
                1 for e in enemies if e.tag != enemy.tag and enemy.distance_to(e) < 4
            )
            edge_bonus = max(0, 5 - nearby_allies_of_target)

            total_score = base_score + edge_bonus
            scored_targets.append((enemy, total_score))

        if not scored_targets:
            return

        # 최고 점수 타겟 납치
        scored_targets.sort(key=lambda x: x[1], reverse=True)
        target = scored_targets[0][0]

        # 권한 요청
        if not await self._request_authority(viper, "abduct"):
            return

        abilities = await self.bot.get_available_abilities(viper)
        if AbilityId.EFFECT_ABDUCT in abilities:
            self.bot.do(viper(AbilityId.EFFECT_ABDUCT, target))
            self._record_skill_use(viper.tag, "abduct")
            self._release_authority(viper.tag)
            self.skills_used["abduct"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ ABDUCT: {target.type_id.name} "
                f"(score: {scored_targets[0][1]}) ★"
            )

    async def _viper_blinding_cloud(self, viper, enemies):
        """
        살모사 흑구름 - 원거리 유닛 무력화
        """
        ranged_units = {
            "MARINE", "MARAUDER", "STALKER", "HYDRALISK",
            "ROACH", "IMMORTAL", "THOR"
        }

        # 원거리 유닛 밀집 지역 찾기
        best_pos = None
        max_count = 0

        for enemy in enemies:
            type_name = getattr(enemy.type_id, "name", "").upper()
            if type_name not in ranged_units:
                continue

            if viper.distance_to(enemy) > 11:  # 사거리
                continue

            pos = enemy.position
            nearby_ranged = sum(
                1 for e in enemies
                if e.position.distance_to(pos) < 4 and
                   getattr(e.type_id, "name", "").upper() in ranged_units
            )

            if nearby_ranged > max_count:
                max_count = nearby_ranged
                best_pos = pos

        if max_count < 3:  # 최소 3명
            return

        # 권한 요청
        if not await self._request_authority(viper, "blinding_cloud"):
            return

        abilities = await self.bot.get_available_abilities(viper)
        if AbilityId.EFFECT_BLINDINGCLOUD in abilities:
            self.bot.do(viper(AbilityId.EFFECT_BLINDINGCLOUD, best_pos))
            self._record_skill_use(viper.tag, "blinding_cloud")
            self._release_authority(viper.tag)
            self.skills_used["blinding_cloud"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ BLINDING CLOUD: {max_count} targets ★"
            )

    async def _viper_consume(self, viper):
        """
        ★★★ 살모사 에너지 회복 (Consume) - 건물 우선 → 오버로드 fallback ★★★

        우선순위 1: 아군 건물 (HP > 250, 해처리/레어/하이브 제외) consume
        우선순위 2: Overlord 소비 (기존 방식)
        """
        if not hasattr(self.bot, "units"):
            return

        # ★ 우선순위 1: 아군 건물에서 흡수 (해처리/레어/하이브 제외) ★
        if hasattr(self.bot, "structures"):
            exclude_buildings = set()
            if UnitTypeId:
                exclude_buildings = {
                    UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE,
                }

            consumable_buildings = [
                b for b in self.bot.structures
                if b.health > 250
                and b.type_id not in exclude_buildings
                and viper.distance_to(b) < 8
            ]

            if consumable_buildings:
                target = min(consumable_buildings, key=lambda b: viper.distance_to(b))

                if not await self._request_authority(viper, "consume"):
                    return

                abilities = await self.bot.get_available_abilities(viper)
                if AbilityId.EFFECT_VIPERCONSUME in abilities:
                    self.bot.do(viper(AbilityId.EFFECT_VIPERCONSUME, target))
                    self._record_skill_use(viper.tag, "consume")
                    self.skills_used["consume"] = self.skills_used.get("consume", 0) + 1

                    game_time = getattr(self.bot, "time", 0)
                    self.logger.info(
                        f"[{int(game_time)}s] ★ CONSUME: Building {target.type_id.name} "
                        f"(HP: {int(target.health)}) ★"
                    )
                    return

        # ★ 우선순위 2: Overlord fallback ★
        overlords = self.bot.units(UnitTypeId.OVERLORD).filter(
            lambda o: not o.has_cargo and o.distance_to(viper) < 8
        )

        if not overlords:
            return

        target_overlord = overlords.closest_to(viper)

        if not await self._request_authority(viper, "consume"):
            return

        abilities = await self.bot.get_available_abilities(viper)
        if AbilityId.EFFECT_VIPERCONSUME in abilities:
            self.bot.do(viper(AbilityId.EFFECT_VIPERCONSUME, target_overlord))
            self._record_skill_use(viper.tag, "consume")
            self.skills_used["consume"] = self.skills_used.get("consume", 0) + 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ CONSUME: Overlord sacrificed ★"
            )

    async def _viper_safety(self, viper, enemies):
        """살모사 안전 관리 - 스킬 사용 후 후퇴"""
        # 최근에 스킬을 썼으면 후퇴
        if self._is_on_cooldown(viper.tag, "abduct", 2) or self._is_on_cooldown(viper.tag, "blinding_cloud", 2):
             retreat_pos = viper.position.towards(self.bot.game_info.map_center, -5)
             self.bot.do(viper.move(retreat_pos))
             return

        # 적이 너무 가까우면 후퇴
        closest_enemy = enemies.closest_to(viper) if enemies else None
        if closest_enemy and closest_enemy.distance_to(viper) < 8:
             retreat_pos = viper.position.towards(closest_enemy, -4)
             self.bot.do(viper.move(retreat_pos))

    async def _infestor_skills(self):
        """
        감염충 스킬 (Neural Parasite, Fungal Growth)
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        infestors = self.bot.units(UnitTypeId.INFESTOR)
        if not infestors:
            return

        enemy_units = self.bot.enemy_units

        for infestor in infestors:
            # ★ 1. 진균 번식 (Fungal Growth) - 75 에너지 ★
            if infestor.energy >= 75:
                if not self._is_on_cooldown(infestor.tag, "fungal", 10):
                    await self._infestor_fungal(infestor, enemy_units)
                    continue

            # ★ 2. 신경 기생충 (Neural Parasite) - 100 에너지 ★
                if not self._is_on_cooldown(infestor.tag, "neural", 20):
                    await self._infestor_neural(infestor, enemy_units)
                    continue

            # ★ 3. 안전 잠복 (Phase 18) ★
            await self._infestor_safety(infestor, enemy_units)

    async def _infestor_fungal(self, infestor, enemies):
        """
        ★★★ 감염충 진균 번식 - 예측 타겟팅 + 가치 합산 ★★★

        1. 적 유닛의 facing + movement_speed로 0.5초 후 예상 위치 계산
        2. 각 후보 위치 중심으로 2.0 반경 내 히트 가치 합산
        3. 최대 가치 지점에 시전 (mineral_cost + vespene_cost 가중)
        4. 최소 3타겟 유지
        """
        import math

        FUNGAL_RADIUS = 2.0
        LEAD_TIME = 0.5  # 0.5초 예측

        # 사거리 내 적 유닛의 예상 위치 계산
        predicted_positions = []
        for enemy in enemies:
            if infestor.distance_to(enemy) > 10:
                continue

            pos = enemy.position

            # ★ 예측 타겟팅: facing + speed로 미래 위치 계산 ★
            try:
                facing = getattr(enemy, "facing", None)
                speed = getattr(enemy, "movement_speed", 0)
                if facing is not None and speed > 0:
                    dx = math.cos(facing) * speed * LEAD_TIME
                    dy = math.sin(facing) * speed * LEAD_TIME
                    predicted = Point2((pos.x + dx, pos.y + dy))
                else:
                    predicted = pos
            except Exception as e:
                self.logger.warning(f"[SpellCaster] Predicted position calc suppressed: {e}")
                predicted = pos

            # 유닛 가치 계산 (mineral + vespene cost)
            try:
                m_cost = getattr(enemy, "mineral_cost", 50) or 50
                g_cost = getattr(enemy, "vespene_cost", 0) or 0
                value = m_cost + g_cost * 1.5  # 가스 유닛 가중
            except Exception as e:
                self.logger.warning(f"[SpellCaster] Unit value calc suppressed: {e}")
                value = 50

            predicted_positions.append((predicted, value, enemy))

        if len(predicted_positions) < self.infestor_fungal_min_targets:
            return

        # ★ 최적 시전 지점 탐색: 각 후보 중심으로 반경 내 가치 합산 ★
        best_pos = None
        best_value = 0
        best_count = 0

        for pred_pos, _, _ in predicted_positions:
            total_value = 0
            hit_count = 0
            for other_pos, other_value, _ in predicted_positions:
                try:
                    if pred_pos.distance_to(other_pos) <= FUNGAL_RADIUS:
                        total_value += other_value
                        hit_count += 1
                except Exception as e:
                    self.logger.warning(f"[SpellCaster] Fungal target distance suppressed: {e}")
                    continue

            if hit_count >= self.infestor_fungal_min_targets and total_value > best_value:
                best_value = total_value
                best_pos = pred_pos
                best_count = hit_count

        if not best_pos:
            return

        # 권한 요청
        if not await self._request_authority(infestor, "fungal"):
            return

        abilities = await self.bot.get_available_abilities(infestor)
        if AbilityId.FUNGALGROWTH_FUNGALGROWTH in abilities:
            self.bot.do(infestor(AbilityId.FUNGALGROWTH_FUNGALGROWTH, best_pos))
            self._record_skill_use(infestor.tag, "fungal")
            self._release_authority(infestor.tag)
            self.skills_used["fungal"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ FUNGAL (PREDICTED): "
                f"{best_count} targets, value: {int(best_value)} ★"
            )

    async def _infestor_neural(self, infestor, enemies):
        """
        감염충 신경 기생충 - 고가치 유닛 빼앗기
        """
        high_value = {
            "THOR", "BATTLECRUISER", "SIEGETANK",
            "COLOSSUS", "IMMORTAL", "CARRIER", "TEMPEST",
            "ULTRALISK", "BROODLORD"
        }

        targets = []
        for enemy in enemies:
            if infestor.distance_to(enemy) > 9:  # 사거리
                continue

            type_name = getattr(enemy.type_id, "name", "").upper()
            if type_name in high_value:
                targets.append(enemy)

        if not targets:
            return

        target = min(targets, key=lambda e: infestor.distance_to(e))

        # 권한 요청
        if not await self._request_authority(infestor, "neural"):
            return

        abilities = await self.bot.get_available_abilities(infestor)
        if AbilityId.NEURALPARASITE_NEURALPARASITE in abilities:
            self.bot.do(infestor(AbilityId.NEURALPARASITE_NEURALPARASITE, target))
            self._record_skill_use(infestor.tag, "neural")
            self._release_authority(infestor.tag)
            self.skills_used["neural"] += 1

            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[{int(game_time)}s] ★ NEURAL: {target.type_id.name} ★"
            )

    async def _infestor_safety(self, infestor, enemies):
        """감염충 안전 잠복"""
        # 적이 가까우면 잠복
        nearby_enemies = enemies.closer_than(9, infestor)
        
        if nearby_enemies.exists:
             if not infestor.is_burrowed:
                 self.bot.do(infestor(AbilityId.BURROWDOWN_INFESTOR))
        else:
             # 적이 없고 에너지가 차면 잠복 해제 (이동을 위해)
             # 단, 진균/신경 쓸 때는 자동 해제되므로 평소엔 잠복 해제 상태 유지
             if infestor.is_burrowed and infestor.energy > 80:
                 self.bot.do(infestor(AbilityId.BURROWUP_INFESTOR))

    async def _overseer_changeling(self):
        """
        감시군주 환상 (Changeling) - 무료 정찰 유닛 생성
        """
        if not hasattr(self.bot, "units"):
            return

        overseers = self.bot.units(UnitTypeId.OVERSEER)
        if not overseers:
            return

        for overseer in overseers:
            # 에너지 체크 (50 필요)
            if overseer.energy < 50:
                continue

            # 쿨다운 체크 (14초)
            if self._is_on_cooldown(overseer.tag, "changeling", 14):
                continue

            # 환상 생성 (적 본진 방향으로)
            if self.bot.enemy_start_locations:
                target_pos = self.bot.enemy_start_locations[0]
            else:
                target_pos = self.bot.game_info.map_center

            # 권한 요청
            if not await self._request_authority(overseer, "changeling"):
                continue

            abilities = await self.bot.get_available_abilities(overseer)
            if AbilityId.SPAWNCHANGELING_SPAWNCHANGELING in abilities:
                self.bot.do(overseer(AbilityId.SPAWNCHANGELING_SPAWNCHANGELING, target_pos))
                self._record_skill_use(overseer.tag, "changeling")
                self.skills_used["changeling"] = self.skills_used.get("changeling", 0) + 1

                game_time = getattr(self.bot, "time", 0)
                self.logger.info(
                    f"[{int(game_time)}s] ★ CHANGELING: Scout sent to {target_pos} ★"
                )
                break  # 한 프레임에 하나만

    def _is_on_cooldown(self, unit_tag: int, ability: str, cooldown: float) -> bool:
        """
        스킬 쿨다운 체크

        Args:
            unit_tag: 유닛 태그
            ability: 스킬 이름
            cooldown: 쿨다운 시간 (초)

        Returns:
            True if on cooldown
        """
        if unit_tag not in self.last_skill_used:
            return False

        if ability not in self.last_skill_used[unit_tag]:
            return False

        game_time = getattr(self.bot, "time", 0)
        last_used = self.last_skill_used[unit_tag][ability]

        return (game_time - last_used) < cooldown

    def _record_skill_use(self, unit_tag: int, ability: str):
        """
        스킬 사용 기록

        Args:
            unit_tag: 유닛 태그
            ability: 스킬 이름
        """
        game_time = getattr(self.bot, "time", 0)

        if unit_tag not in self.last_skill_used:
            self.last_skill_used[unit_tag] = {}

        self.last_skill_used[unit_tag][ability] = game_time

    def get_statistics(self) -> Dict:
        """통계 반환"""
        return self.skills_used.copy()
