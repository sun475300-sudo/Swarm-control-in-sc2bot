# -*- coding: utf-8 -*-
"""
Active Scouting System - 능동형 정찰 시스템

주기적으로 저글링을 파견하여:
- 적 멀티 타이밍 확인
- 적 병력 구성 파악
- 적 테크 진행 상황 감시

⚠️ DEPRECATED: This system has been superseded by AdvancedScoutingSystemV2
(scouting/advanced_scout_system_v2.py). Use the new system instead.

This file is kept for reference only and should not be used in new code.
"""

from typing import List, Set, Dict, Tuple
from utils.logger import get_logger
from game_config import GameConfig

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    class UnitTypeId:
        ZERGLING = "ZERGLING"
        OVERSEER = "OVERSEER"
        OVERLORD = "OVERLORD"
        CHANGELING = "CHANGELING"
        CHANGELINGZERGLING = "CHANGELINGZERGLING"
        CHANGELINGMARINE = "CHANGELINGMARINE"
        CHANGELINGZEALOT = "CHANGELINGZEALOT"

    class AbilityId:
        SPAWNCHANGELING_SPAWNCHANGELING = "SPAWNCHANGELING_SPAWNCHANGELING"

    Point2 = tuple


class ActiveScoutingSystem:
    """
    ★ Active Scouting System ★

    저글링을 이용한 능동형 정찰로
    적 정보를 지속적으로 수집합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ActiveScout")

        # ★ 정찰 주기 (동적 조정, GameConfig에서 로드) ★
        self.last_scout_sent = 0
        self.scout_interval_default = GameConfig.SCOUT_INTERVAL_DEFAULT
        self.scout_interval_alert = GameConfig.SCOUT_INTERVAL_ALERT
        self.scout_interval = self.scout_interval_default
        self.last_intel_update = 0  # 마지막 정보 업데이트 시간

        # ★ 정찰 목표 ★
        self.scout_targets: List[Point2] = []
        self.scouted_locations: Set[Tuple[int, int]] = set()
        self.location_scout_times: Dict[Tuple[int, int], float] = {}  # 위치별 마지막 정찰 시간
        self.active_scouts: Dict[int, Dict] = {}  # {unit_tag: {target: pos, sent_time: time}}

        # ★ 타겟 우선순위 설정 ★
        self.watchtower_positions: List[Point2] = []  # 감시탑 위치

        # ★ Changeling 관리 ★
        self.active_changelings: Dict[int, Dict] = {}  # {unit_tag: {spawn_time: time, target: pos}}
        self.last_changeling_spawn = 0  # 마지막 Changeling 생성 시간

        # ★ 성과 추적 ★
        self.scouts_sent = 0  # 파견한 정찰 유닛 수
        self.scouts_arrived = 0  # 목표 도달한 정찰 유닛 수
        self.scouts_lost = 0  # 손실된 정찰 유닛 수
        self.changelings_spawned = 0  # 생성한 Changeling 수
        self.new_info_discovered = 0  # 발견한 새로운 정보 수

        # ★ 정찰 정보 ★
        self.enemy_expansion_timings: Dict[Point2, float] = {}
        self.enemy_army_composition: Dict[str, int] = {}
        self.enemy_tech_progress: Dict[str, float] = {}

        # ★ Overlord Speed Upgrade 관리 ★
        self.overlord_speed_requested = False  # 업그레이드 요청 여부

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = getattr(self.bot, "time", 0)

            # ★ 0. 동적 정찰 간격 조정 ★
            self._adjust_scout_interval(game_time)

            # ★ 1. 정찰 목표 업데이트 ★
            if iteration % 100 == 0:
                self._update_scout_targets()

            # ★ 2. 정찰 파견 ★
            if game_time - self.last_scout_sent > self.scout_interval:
                await self._send_scout()
                self.last_scout_sent = game_time

            # ★ 3. 활성 정찰 모니터링 ★
            await self._monitor_active_scouts()

            # ★ 4. 정찰 정보 분석 ★
            if iteration % 220 == 0:  # 10초마다
                await self._analyze_scouted_info()

            # ★ 5. Overlord Speed 업그레이드 우선순위 관리 ★
            if iteration % 220 == 0:  # 10초마다
                self._request_overlord_speed_upgrade(game_time)

        except (AttributeError, TypeError, KeyError) as e:
            if iteration % 50 == 0:
                self.logger.error(f"[ACTIVE_SCOUT] Error in on_step at iteration {iteration}: {type(e).__name__} - {e}")
        except Exception as e:
            # Catch-all for unexpected errors
            if iteration % 50 == 0:
                self.logger.error(f"[ACTIVE_SCOUT] Unexpected error in on_step: {type(e).__name__} - {e}")

    def _adjust_scout_interval(self, game_time: float):
        """
        동적 정찰 간격 조정

        정보가 오래되었거나 부족하면 경고 모드로 전환 (15초 간격)
        """
        # 마지막 정보 업데이트로부터 일정 시간 이상 경과 시 경고 모드
        time_since_intel = game_time - self.last_intel_update

        # 적 정보가 매우 적은 경우 (초반 또는 정보 부족)
        has_minimal_intel = (
            len(self.enemy_expansion_timings) == 0 and
            len(self.enemy_tech_progress) == 0 and
            game_time > 120  # 2분 이후에도 정보가 없으면
        )

        # 경고 모드 조건
        if time_since_intel > GameConfig.SCOUT_INTEL_STALE_TIME or has_minimal_intel:
            self.scout_interval = self.scout_interval_alert
        else:
            self.scout_interval = self.scout_interval_default

    def _update_scout_targets(self):
        """
        정찰 목표 위치 업데이트 (우선순위 기반)

        우선순위:
        1. 미정찰 확장 위치
        2. 적 본진
        3. 감시탑
        """
        if not hasattr(self.bot, "expansion_locations_list"):
            return

        # ★ 확장 위치들을 정찰 목표로 (최우선) ★
        self.scout_targets = []

        # 1. 미정찰 확장 위치 (최우선)
        for exp_pos in self.bot.expansion_locations_list:
            loc_key = (int(exp_pos.x), int(exp_pos.y))
            if loc_key not in self.scouted_locations:
                self.scout_targets.append(exp_pos)

        # 2. 적 본진 (항상 포함)
        if self.bot.enemy_start_locations:
            enemy_main = self.bot.enemy_start_locations[0]
            if enemy_main not in self.scout_targets:
                self.scout_targets.append(enemy_main)

        # 3. 감시탑 (낮은 우선순위)
        self._update_watchtower_positions()
        for tower_pos in self.watchtower_positions:
            if tower_pos not in self.scout_targets:
                self.scout_targets.append(tower_pos)

        # 4. 이미 정찰한 확장 위치 재확인 (가장 낮은 우선순위)
        for exp_pos in self.bot.expansion_locations_list:
            if exp_pos not in self.scout_targets:
                self.scout_targets.append(exp_pos)

    def _update_watchtower_positions(self):
        """
        감시탑 위치 업데이트
        """
        if self.watchtower_positions:
            return  # 이미 찾았으면 스킵

        # 맵에서 감시탑 찾기 (Xel'Naga Tower)
        if hasattr(self.bot, "all_units"):
            towers = self.bot.all_units.filter(
                lambda u: getattr(u.type_id, "name", "").upper() == "XELNAGATOWER"
            )
            self.watchtower_positions = [tower.position for tower in towers]

    async def _send_scout(self):
        """
        정찰 유닛 파견 (다중 유닛 타입 지원)

        우선순위:
        1. 오버시어 (공중 정찰 + 감지)
        2. 오버로드 (속도 업그레이드 시)
        3. 저글링 (지상 정찰)
        """
        if not hasattr(self.bot, "units"):
            return

        # ★ 정찰 목표 선택 (스마트 필터링) ★
        if not self.scout_targets:
            return

        game_time = getattr(self.bot, "time", 0)

        # 최근 일정 시간 이내에 정찰하지 않은 위치만 선택
        valid_targets = []

        for target in self.scout_targets:
            loc_key = (int(target.x), int(target.y))
            last_scout_time = self.location_scout_times.get(loc_key, 0)

            # 일정 시간 이상 지났거나 한 번도 정찰하지 않은 위치
            if game_time - last_scout_time > GameConfig.SCOUT_LOCATION_REVISIT_TIME:
                valid_targets.append(target)

        # 유효한 타겟이 없으면 모든 타겟 사용
        if not valid_targets:
            valid_targets = self.scout_targets

        unscouted = valid_targets

        # ★ 정찰 유닛 선택 (우선순위 기반) ★
        scout = None
        scout_type = "UNKNOWN"

        # 1. 오버시어 (최우선)
        overseers = self.bot.units(UnitTypeId.OVERSEER).idle
        if overseers:
            scout = overseers.first
            scout_type = "OVERSEER"
        else:
            # 2. 오버로드 (속도 업그레이드 시)
            overlords = self.bot.units(UnitTypeId.OVERLORD).idle
            if overlords:
                # 속도 업그레이드 확인 (Pneumatized Carapace)
                has_speed = getattr(self.bot, "overlord_speed_upgraded", False)
                if has_speed or len(overlords) > 3:  # 여유가 많으면 사용
                    scout = overlords.first
                    scout_type = "OVERLORD"

        # 3. 저글링 (기본)
        if not scout:
            zerglings = self.bot.units(UnitTypeId.ZERGLING).idle
            if not zerglings:
                # Idle이 없으면 전체에서 선택
                zerglings = self.bot.units(UnitTypeId.ZERGLING)

            if zerglings:
                scout = zerglings.first
                scout_type = "ZERGLING"

        if not scout:
            return

        # 가장 가까운 미정찰 위치 선택
        target = min(unscouted, key=lambda pos: scout.position.distance_to(pos))

        # ★ 정찰 파견 ★
        self.bot.do(scout.move(target))
        self.active_scouts[scout.tag] = {
            "target": target,
            "sent_time": getattr(self.bot, "time", 0),
            "unit_type": scout_type,
        }

        game_time = getattr(self.bot, "time", 0)
        self.scouts_sent += 1

        self.logger.info(
            f"[SCOUT][{int(game_time)}s] Sent {scout_type} to {target} (Total sent: {self.scouts_sent})"
        )

    async def _monitor_active_scouts(self):
        """
        활성 정찰 모니터링
        """
        if not self.active_scouts:
            return

        game_time = getattr(self.bot, "time", 0)

        # 정찰 완료 확인
        completed = []

        for scout_tag, scout_info in self.active_scouts.items():
            # 유닛 존재 확인
            scout = self.bot.units.find_by_tag(scout_tag)
            if not scout:
                # 유닛 손실
                self.scouts_lost += 1
                completed.append(scout_tag)
                continue

            target = scout_info["target"]

            # 목표 도달 확인 (5거리 이내)
            if scout.position.distance_to(target) < 5:
                # 정찰 완료 기록
                loc_key = (int(target.x), int(target.y))
                was_new = loc_key not in self.scouted_locations
                self.scouted_locations.add(loc_key)
                self.location_scout_times[loc_key] = game_time  # 정찰 시간 기록
                self.scouts_arrived += 1
                completed.append(scout_tag)

                scout_type = scout_info.get("unit_type", "UNKNOWN")
                success_rate = (self.scouts_arrived / self.scouts_sent * 100) if self.scouts_sent > 0 else 0

                self.logger.info(
                    f"[SCOUT][{int(game_time)}s] {scout_type} arrived at {target} "
                    f"(Success: {self.scouts_arrived}/{self.scouts_sent} = {success_rate:.1f}%)"
                    f"{' [NEW]' if was_new else ' [REVISIT]'}"
                )

                # 정찰 정보 수집
                await self._collect_scout_info(scout, target)

                # ★ Overseer인 경우 Changeling 생성 시도 ★
                scout_type = scout_info.get("unit_type", "UNKNOWN")
                if scout_type == "OVERSEER":
                    await self._spawn_changeling(scout, target, game_time)

            # 타임아웃 (60초)
            elif game_time - scout_info["sent_time"] > 60:
                completed.append(scout_tag)

        # 완료된 정찰 제거
        for tag in completed:
            del self.active_scouts[tag]

    async def _spawn_changeling(self, overseer, location: Point2, game_time: float):
        """
        오버시어를 이용한 Changeling 생성

        Args:
            overseer: 오버시어 유닛
            location: 정찰 위치
            game_time: 현재 게임 시간
        """
        # Changeling 재사용 대기 시간 확인
        if game_time - self.last_changeling_spawn < GameConfig.SCOUT_CHANGELING_COOLDOWN:
            return

        try:
            # Changeling 능력 사용 가능 여부 확인
            abilities = await self.bot.get_available_abilities(overseer)
            if AbilityId.SPAWNCHANGELING_SPAWNCHANGELING in abilities:
                # Changeling 생성
                self.bot.do(overseer(AbilityId.SPAWNCHANGELING_SPAWNCHANGELING))
                self.last_changeling_spawn = game_time
                self.changelings_spawned += 1

                self.logger.info(
                    f"[SCOUT][{int(game_time)}s] Changeling spawned at {location} "
                    f"(Total: {self.changelings_spawned})"
                )

                # Changeling은 자동으로 정찰하므로 별도 명령 불필요

        except (AttributeError, TypeError) as e:
            # 능력 사용 실패 시 무시
            pass

    async def _collect_scout_info(self, scout, location: Point2):
        """
        정찰 정보 수집

        Args:
            scout: 정찰 유닛
            location: 정찰 위치
        """
        if not hasattr(self.bot, "enemy_structures") or not hasattr(self.bot, "enemy_units"):
            return

        game_time = getattr(self.bot, "time", 0)

        # ★ 1. 적 확장 확인 ★
        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: s.position.distance_to(location) < 10 and
            getattr(s.type_id, "name", "").upper() in {
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE"
            }
        )

        if enemy_bases:
            if location not in self.enemy_expansion_timings:
                self.new_info_discovered += 1  # 새로운 기지 발견
            self.enemy_expansion_timings[location] = game_time
            self.last_intel_update = game_time  # 정보 업데이트 시간 갱신
            self.logger.info(
                f"[INTEL][{int(game_time)}s] Enemy base found at {location} "
                f"(Total bases: {len(self.enemy_expansion_timings)})"
            )

        # ★ 2. 적 유닛 구성 확인 ★
        nearby_enemies = self.bot.enemy_units.closer_than(15, scout)
        for enemy in nearby_enemies:
            type_name = getattr(enemy.type_id, "name", "").upper()
            self.enemy_army_composition[type_name] = self.enemy_army_composition.get(type_name, 0) + 1

        # ★ 3. 적 테크 건물 확인 ★
        tech_buildings = {
            "FACTORY", "STARPORT", "ARMORY",
            "ROBOTICSFACILITY", "STARGATE", "TWILIGHTCOUNCIL",
            "SPIRE", "HYDRALISKDEN", "ROACHWARREN"
        }

        enemy_tech = self.bot.enemy_structures.closer_than(15, scout)
        for building in enemy_tech:
            type_name = getattr(building.type_id, "name", "").upper()
            if type_name in tech_buildings:
                if type_name not in self.enemy_tech_progress:
                    self.enemy_tech_progress[type_name] = game_time
                    self.last_intel_update = game_time  # 정보 업데이트 시간 갱신
                    self.new_info_discovered += 1  # 새로운 테크 발견
                    self.logger.info(
                        f"[INTEL][{int(game_time)}s] Enemy tech discovered: {type_name} "
                        f"(Total tech: {len(self.enemy_tech_progress)})"
                    )

    async def _analyze_scouted_info(self):
        """
        정찰 정보 분석 및 보고
        """
        if not self.enemy_expansion_timings and not self.enemy_army_composition:
            return

        game_time = getattr(self.bot, "time", 0)

        # ★ 1. 적 확장 수 ★
        enemy_base_count = len(self.enemy_expansion_timings)

        # ★ 2. 적 주력 유닛 ★
        if self.enemy_army_composition:
            main_unit = max(self.enemy_army_composition.items(), key=lambda x: x[1])
        else:
            main_unit = ("UNKNOWN", 0)

        # ★ 3. 적 테크 진행 ★
        tech_buildings = len(self.enemy_tech_progress)

        # ★ 4. Blackboard에 정보 등록 ★
        self._push_scout_data_to_blackboard(enemy_base_count, main_unit, tech_buildings)

        # ★ 5. 정기 보고 ★
        if int(game_time) % 60 == 0:  # 1분마다
            success_rate = (self.scouts_arrived / self.scouts_sent * 100) if self.scouts_sent > 0 else 0
            scout_mode = "ALERT" if self.scout_interval == self.scout_interval_alert else "NORMAL"

            self.logger.info(
                f"[REPORT][{int(game_time)}s] Scout System Status:\n"
                f"  Mode: {scout_mode} (interval: {self.scout_interval/22.4:.1f}s)\n"
                f"  Performance: {self.scouts_arrived}/{self.scouts_sent} scouts arrived ({success_rate:.1f}%)\n"
                f"  Lost: {self.scouts_lost}, Changelings: {self.changelings_spawned}\n"
                f"  Intel: {self.new_info_discovered} new discoveries\n"
                f"  Enemy: {enemy_base_count} bases, {tech_buildings} tech buildings\n"
                f"  Main Unit: {main_unit[0]} ({main_unit[1]})\n"
                f"  Coverage: {len(self.scouted_locations)} locations"
            )

    def _push_scout_data_to_blackboard(self, enemy_base_count: int,
                                        main_unit: tuple, tech_buildings: int) -> None:
        """
        Push scouting data to Blackboard for other systems to use.

        Args:
            enemy_base_count: Number of enemy bases detected
            main_unit: Tuple of (unit_type, count)
            tech_buildings: Number of enemy tech buildings
        """
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard:
            return

        try:
            # Push basic scout data
            blackboard.set("enemy_base_count_scout", enemy_base_count)
            blackboard.set("enemy_main_unit", main_unit[0])
            blackboard.set("enemy_tech_buildings_scout", tech_buildings)

            # Push scout system status
            scout_mode = "alert" if self.scout_interval == self.scout_interval_alert else "normal"
            blackboard.set("scout_mode", scout_mode)
            blackboard.set("scout_interval", self.scout_interval)

            # Push detailed composition
            blackboard.set("enemy_army_composition_scout", self.enemy_army_composition.copy())
            blackboard.set("enemy_expansion_timings", dict(self.enemy_expansion_timings))

            # Push coverage metrics
            blackboard.set("scouted_locations_count", len(self.scouted_locations))
            blackboard.set("active_scouts_count", len(self.active_scouts))

        except (AttributeError, TypeError) as e:
            # Silently fail if blackboard doesn't support set operation
            pass

    def _request_overlord_speed_upgrade(self, game_time: float) -> None:
        """
        ★ Overlord Speed 업그레이드 우선순위 요청 ★

        정찰 효율을 60% 향상시키는 Pneumatized Carapace (오버로드 속업) 요청

        조건:
        1. Lair가 완성되었을 때
        2. 아직 업그레이드가 안 되었을 때
        3. Scout 모드가 alert일 때 우선순위 상승
        """
        # 이미 요청했으면 스킵
        if self.overlord_speed_requested:
            return

        # Lair/Hive가 있는지 확인
        if not hasattr(self.bot, "structures"):
            return

        try:
            # Lair 또는 Hive가 ready 상태인지 확인
            lairs = self.bot.structures(UnitTypeId.LAIR).ready
            hives = self.bot.structures(UnitTypeId.HIVE).ready

            if not lairs and not hives:
                return

            # 이미 업그레이드가 완료되었는지 확인
            if hasattr(self.bot, "already_pending_upgrade"):
                from sc2.ids.upgrade_id import UpgradeId
                if UpgradeId.OVERLORDSPEED in self.bot.state.upgrades:
                    # 이미 완료됨
                    return

                if self.bot.already_pending_upgrade(UpgradeId.OVERLORDSPEED) > 0:
                    # 이미 진행 중
                    self.overlord_speed_requested = True
                    return

            # ★ Blackboard를 통해 업그레이드 요청 ★
            blackboard = getattr(self.bot, "blackboard", None)
            if blackboard:
                # Scout 모드가 alert이면 높은 우선순위
                is_alert_mode = self.scout_interval == self.scout_interval_alert

                blackboard.set("request_overlord_speed", True)
                blackboard.set("overlord_speed_priority", "high" if is_alert_mode else "normal")

                self.overlord_speed_requested = True

                priority_str = "HIGH" if is_alert_mode else "NORMAL"
                self.logger.info(
                    f"[SCOUT][{int(game_time)}s] ★ Requesting Overlord Speed upgrade "
                    f"(Priority: {priority_str}) ★"
                )

        except (AttributeError, TypeError) as e:
            # 구조 접근 실패 시 무시
            pass

    def get_enemy_info(self) -> Dict:
        """
        적 정보 반환

        Returns:
            적 정보 딕셔너리
        """
        return {
            "base_count": len(self.enemy_expansion_timings),
            "base_timings": self.enemy_expansion_timings,
            "army_composition": self.enemy_army_composition,
            "tech_buildings": self.enemy_tech_progress,
            "scouted_locations": len(self.scouted_locations),
        }
