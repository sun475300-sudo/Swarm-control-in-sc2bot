# -*- coding: utf-8 -*-
"""
Unit Morph Manager - Automatic unit morphing system

자동 유닛 변태 시스템:
- 저글링 -> 베인링
- 바퀴 -> 파멸충
- 히드라 -> 럴커
- 코럽터 -> 무리군주

Features:
- 게임 단계별 변태 비율 자동 조정
- 상대 종족별 최적 변태 비율
- 자원 효율 극대화
"""

from typing import Dict, Optional

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    UnitTypeId = None
    AbilityId = None

from utils.logger import get_logger


class UnitMorphManager:
    """자동 유닛 변태 관리자"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("UnitMorphManager")
        self.last_morph_check = 0
        self.morph_check_interval = 44  # ~2초마다 체크

        # 변태 쿨다운 추적
        self.last_baneling_morph = 0
        self.last_ravager_morph = 0
        self.last_lurker_morph = 0
        self.last_broodlord_morph = 0

        # 변태 비율 설정 (상대 종족별)
        self.morph_ratios = {
            "Terran": {
                "baneling_ratio": 0.2,   
                "ravager_ratio": 0.3,    # ★ AGGRESSIVE: 15% -> 30%
                "lurker_ratio": 0.3,     
                "broodlord_ratio": 0.4,  
            },
            "Protoss": {
                "baneling_ratio": 0.25,  
                "ravager_ratio": 0.35,   # ★ AGGRESSIVE: 25% -> 35%
                "lurker_ratio": 0.4,     
                "broodlord_ratio": 0.3,
            },
            "Zerg": {
                "baneling_ratio": 0.3,   
                "ravager_ratio": 0.3,    # ★ AGGRESSIVE: 20% -> 30%
                "lurker_ratio": 0.2,
                "broodlord_ratio": 0.3,
            },
            "Unknown": {
                "baneling_ratio": 0.2,
                "ravager_ratio": 0.3,
                "lurker_ratio": 0.25,
                "broodlord_ratio": 0.3,
            }
        }

    async def on_step(self, iteration: int):
        """메인 루프"""
        if not UnitTypeId or not AbilityId:
            return

        if iteration - self.last_morph_check < self.morph_check_interval:
            return

        self.last_morph_check = iteration
        game_time = getattr(self.bot, "time", 0)

        # 상대 종족 확인
        enemy_race = self._get_enemy_race()

        try:
            # 0. 오버시어 변태 (탐지기 확보 - 레어 필요)
            if self._has_lair():
                await self._morph_overseers(iteration)

            # 1. 베인링 변태 (가장 빠름 - 2분 30초 이후)
            if game_time >= 150:
                await self._morph_banelings(enemy_race, iteration)

            # 2. 파멸충 변태 (3분 이후, Lair 불필요)
            # ★ OPTIMIZATION: 레어 조건 삭제 (빠른 파멸충)
            if game_time >= 180 and self._has_roach_warren():
                await self._morph_ravagers(enemy_race, iteration)

            # 3. 럴커 변태 (6분 이후, Lurker Den 필요)
            if game_time >= 360 and self._has_lurker_den():
                await self._morph_lurkers(enemy_race, iteration)

            # 4. 무리군주 변태 (10분 이후, Greater Spire 필요)
            if game_time >= 600 and self._has_greater_spire():
                await self._morph_broodlords(enemy_race, iteration)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"Morph manager error: {e}")

    async def _morph_banelings(self, enemy_race: str, iteration: int):
        """저글링 -> 베인링 변태"""
        # 쿨다운 체크 (10초마다)
        if self.bot.time - self.last_baneling_morph < 10:
            return

        # 베인링 둥지 확인
        baneling_nests = self.bot.structures(UnitTypeId.BANELINGNEST).ready
        if not baneling_nests.exists:
            return

        # 저글링/베인링 수 확인
        zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
        banelings = self.bot.units(UnitTypeId.BANELING)

        if not zerglings.exists:
            return

        # 목표 비율 계산
        ratios = self.morph_ratios.get(enemy_race, self.morph_ratios["Unknown"])
        target_ratio = ratios["baneling_ratio"]

        total_lings = zerglings.amount + banelings.amount
        if total_lings == 0:
            return

        current_ratio = banelings.amount / total_lings

        # 베인링이 부족하면 변태
        if current_ratio < target_ratio:
            # 변태할 저글링 수 계산
            target_banelings = int(total_lings * target_ratio)
            morphs_needed = target_banelings - banelings.amount

            if morphs_needed <= 0:
                return

            # 최대 8마리씩 변태
            morphs_needed = min(morphs_needed, 8)

            # 자원 확인
            if not self.bot.can_afford(UnitTypeId.BANELING):
                return

            # 변태 실행
            morphed = 0
            for zergling in zerglings[:morphs_needed]:
                if self.bot.can_afford(UnitTypeId.BANELING):
                    try:
                        self.bot.do(zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING))
                        morphed += 1
                    except Exception:
                        continue

            if morphed > 0:
                self.last_baneling_morph = self.bot.time
                if iteration % 100 == 0:
                    self.logger.info(f"[{int(self.bot.time)}s] Morphed {morphed} Banelings (target ratio: {target_ratio:.1%})")

    async def _morph_ravagers(self, enemy_race: str, iteration: int):
        """바퀴 -> 파멸충 변태"""
        # 쿨다운 체크 (15초마다)
        if self.bot.time - self.last_ravager_morph < 15:
            return

        # 바퀴 굴 확인
        roach_warrens = self.bot.structures(UnitTypeId.ROACHWARREN).ready
        if not roach_warrens.exists:
            return

        # 바퀴/파멸충 수 확인
        roaches = self.bot.units(UnitTypeId.ROACH).idle
        ravagers = self.bot.units(UnitTypeId.RAVAGER)

        if not roaches.exists:
            return

        # 목표 비율 계산
        ratios = self.morph_ratios.get(enemy_race, self.morph_ratios["Unknown"])
        target_ratio = ratios["ravager_ratio"]

        total_roaches = roaches.amount + ravagers.amount
        if total_roaches < 5:  # 최소 5마리 이상일 때만 변태
            return

        current_ratio = ravagers.amount / total_roaches

        # 파멸충이 부족하면 변태
        if current_ratio < target_ratio:
            target_ravagers = int(total_roaches * target_ratio)
            morphs_needed = target_ravagers - ravagers.amount

            if morphs_needed <= 0:
                return

            # 최대 4마리씩 변태
            morphs_needed = min(morphs_needed, 4)

            # 자원 확인
            if not self.bot.can_afford(UnitTypeId.RAVAGER):
                return

            # 변태 실행
            morphed = 0
            for roach in roaches[:morphs_needed]:
                if self.bot.can_afford(UnitTypeId.RAVAGER):
                    try:
                        self.bot.do(roach(AbilityId.MORPHTORAVAGER_RAVAGER))
                        morphed += 1
                    except Exception:
                        continue

            if morphed > 0:
                self.last_ravager_morph = self.bot.time
                self.logger.info(f"[{int(self.bot.time)}s] Morphed {morphed} Ravagers (target ratio: {target_ratio:.1%})")

    async def _morph_lurkers(self, enemy_race: str, iteration: int):
        """히드라 -> 럴커 변태"""
        # 쿨다운 체크 (20초마다)
        if self.bot.time - self.last_lurker_morph < 20:
            return

        # 럴커 덴 확인
        lurker_dens = self.bot.structures(UnitTypeId.LURKERDENMP).ready
        if not lurker_dens.exists:
            return

        # 히드라/럴커 수 확인
        hydralisks = self.bot.units(UnitTypeId.HYDRALISK).idle
        lurkers = self.bot.units(UnitTypeId.LURKERMP)

        if not hydralisks.exists:
            return

        # 목표 비율 계산
        ratios = self.morph_ratios.get(enemy_race, self.morph_ratios["Unknown"])
        target_ratio = ratios["lurker_ratio"]

        total_hydras = hydralisks.amount + lurkers.amount
        if total_hydras < 4:  # 최소 4마리 이상일 때만 변태
            return

        current_ratio = lurkers.amount / total_hydras

        # 럴커가 부족하면 변태
        if current_ratio < target_ratio:
            target_lurkers = int(total_hydras * target_ratio)
            morphs_needed = target_lurkers - lurkers.amount

            if morphs_needed <= 0:
                return

            # 최대 3마리씩 변태
            morphs_needed = min(morphs_needed, 3)

            # 자원 확인
            if not self.bot.can_afford(UnitTypeId.LURKERMP):
                return

            # 변태 실행
            morphed = 0
            for hydra in hydralisks[:morphs_needed]:
                if self.bot.can_afford(UnitTypeId.LURKERMP):
                    try:
                        self.bot.do(hydra(AbilityId.MORPH_LURKER))
                        morphed += 1
                    except Exception:
                        continue

            if morphed > 0:
                self.last_lurker_morph = self.bot.time
                self.logger.info(f"[{int(self.bot.time)}s] Morphed {morphed} Lurkers (target ratio: {target_ratio:.1%})")

    async def _morph_broodlords(self, enemy_race: str, iteration: int):
        """코럽터 -> 무리군주 변태"""
        # 쿨다운 체크 (30초마다)
        if self.bot.time - self.last_broodlord_morph < 30:
            return

        # Greater Spire 확인
        greater_spires = self.bot.structures(UnitTypeId.GREATERSPIRE).ready
        if not greater_spires.exists:
            return

        # 코럽터/무리군주 수 확인
        corruptors = self.bot.units(UnitTypeId.CORRUPTOR).idle
        broodlords = self.bot.units(UnitTypeId.BROODLORD)

        if not corruptors.exists:
            return

        # 목표 비율 계산
        ratios = self.morph_ratios.get(enemy_race, self.morph_ratios["Unknown"])
        target_ratio = ratios["broodlord_ratio"]

        total_corruptors = corruptors.amount + broodlords.amount
        if total_corruptors < 3:  # 최소 3마리 이상일 때만 변태
            return

        current_ratio = broodlords.amount / total_corruptors

        # 무리군주가 부족하면 변태
        if current_ratio < target_ratio:
            target_broodlords = int(total_corruptors * target_ratio)
            morphs_needed = target_broodlords - broodlords.amount

            if morphs_needed <= 0:
                return

            # 최대 2마리씩 변태 (무리군주는 강력하므로)
            morphs_needed = min(morphs_needed, 2)

            # 자원 확인
            if not self.bot.can_afford(UnitTypeId.BROODLORD):
                return

            # 변태 실행
            morphed = 0
            for corruptor in corruptors[:morphs_needed]:
                if self.bot.can_afford(UnitTypeId.BROODLORD):
                    try:
                        self.bot.do(corruptor(AbilityId.MORPH_BROODLORD))
                        morphed += 1
                    except Exception:
                        continue

            if morphed > 0:
                self.last_broodlord_morph = self.bot.time
                self.logger.info(f"[{int(self.bot.time)}s] Morphed {morphed} Brood Lords (target ratio: {target_ratio:.1%})")

    async def _morph_overseers(self, iteration: int):
        """오버로드 -> 오버시어 변태 (탐지기 확보)"""
        # 쿨다운 체크 (10초마다)
        if hasattr(self, "last_overseer_morph") and self.bot.time - self.last_overseer_morph < 10:
            return

        # 레어/하이브 필요
        if not self._has_lair():
            return

        # 오버시어 수 확인
        overseers = self.bot.units(UnitTypeId.OVERSEER)
        
        # 목표 오버시어 수: 기본 2기, 프로토스전 3기 (DT 대비)
        target_count = 2
        enemy_race = self._get_enemy_race()
        if enemy_race == "Protoss":
            target_count = 3
        
        if overseers.amount >= target_count:
            return

        # 변태 가능한 오버로드 확인
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        if not overlords.exists:
            return
            
        # 자원 확인 (미네랄 50, 가스 50)
        if not self.bot.can_afford(UnitTypeId.OVERSEER):
            return

        # 변태 실행 (가장 가까운 오버로드 선택? 그냥 랜덤)
        # 본진 근처 오버로드 선호?
        target_overlord = overlords.closest_to(self.bot.start_location)
        
        try:
            self.bot.do(target_overlord(AbilityId.MORPH_OVERSEER))
            self.last_overseer_morph = self.bot.time
            self.logger.info(f"[{int(self.bot.time)}s] Morphed Overseer (Active: {overseers.amount}/{target_count})")
        except Exception:
            pass

    def _get_enemy_race(self) -> str:
        """상대 종족 확인"""
        # Strategy Manager에서 확인
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy:
            race = getattr(strategy, "detected_enemy_race", None)
            if race:
                race_name = race.value if hasattr(race, "value") else str(race)
                return race_name

        # 직접 확인
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race:
            race_str = str(enemy_race)
            for race_name in ["Terran", "Protoss", "Zerg"]:
                if race_name in race_str:
                    return race_name

        return "Unknown"

    def _has_lair(self) -> bool:
        """Lair or Hive 존재 확인"""
        if not hasattr(self.bot, "structures"):
            return False
        lairs = self.bot.structures(UnitTypeId.LAIR)
        hives = self.bot.structures(UnitTypeId.HIVE)
        return (lairs.exists or hives.exists)

    def _has_roach_warren(self) -> bool:
        """Roach Warren 존재 확인"""
        if not hasattr(self.bot, "structures"):
            return False
        return self.bot.structures(UnitTypeId.ROACHWARREN).ready.exists

    def _has_lurker_den(self) -> bool:
        """Lurker Den 존재 확인"""
        if not hasattr(self.bot, "structures"):
            return False
        return self.bot.structures(UnitTypeId.LURKERDENMP).ready.exists

    def _has_greater_spire(self) -> bool:
        """Greater Spire 존재 확인"""
        if not hasattr(self.bot, "structures"):
            return False
        return self.bot.structures(UnitTypeId.GREATERSPIRE).ready.exists
