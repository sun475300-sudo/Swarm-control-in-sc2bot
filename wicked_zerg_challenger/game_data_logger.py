# -*- coding: utf-8 -*-
"""
Game Data Logger - 게임 플레이 데이터 수집 시스템

모든 의사결정, 타이밍, 결과를 기록하여 학습 데이터로 활용
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    UnitTypeId = None


class GameDataLogger:
    """
    게임 플레이 데이터 로거

    기록 항목:
    1. 빌드 오더 (build_order)
    2. 확장 타이밍 (expansions)
    3. 유닛 생산 (unit_production)
    4. 테크 업그레이드 (tech_upgrades)
    5. 교전 기록 (engagements)
    6. 자원 상태 (resources_snapshots)
    7. 최종 결과 (game_result)
    """

    def __init__(self, bot):
        self.bot = bot
        self.game_data = {
            "meta": {},
            "build_order": [],
            "expansions": [],
            "unit_production": [],
            "tech_upgrades": [],
            "engagements": [],
            "resource_snapshots": [],
            "decision_log": [],
            "game_result": {},
            # ★ 추가 학습 항목 ★
            "enemy_scouts": [],           # 적 정찰 정보
            "harassment": [],             # 하라스 기록
            "defense_events": [],         # 방어 성공/실패
            "unit_composition": [],       # 유닛 구성비 스냅샷
            "upgrade_sequence": [],       # 업그레이드 순서
            "map_control": [],            # 맵 장악도
            "enemy_build_detected": {}    # 적 빌드 패턴
        }

        self.start_time = datetime.now()
        self.last_snapshot_time = 0
        self.snapshot_interval = 60  # 60초마다 스냅샷

        # 건설 추적
        self._tracked_structures = set()
        self._tracked_units = set()
        self._tracked_upgrades = set()

        # 교전 추적
        self._last_army_supply = 0
        self._engagement_cooldown = 0

        # ★ 추가 추적 변수 ★
        self._last_composition_time = 0
        self._composition_interval = 120  # 2분마다
        self._harassment_cooldown = 0
        self._defense_events_buffer = []
        self._enemy_units_history = []

    def initialize_game_meta(self):
        """게임 시작 시 메타 정보 기록"""
        self.game_data["meta"] = {
            "timestamp": self.start_time.isoformat(),
            "map_name": self.bot.game_info.map_name if hasattr(self.bot, "game_info") else "Unknown",
            "opponent_race": str(self.bot.enemy_race) if hasattr(self.bot, "enemy_race") else "Unknown",
            "bot_race": "Zerg",
            "game_version": "5.0.12",  # SC2 버전
        }

    async def on_step(self, iteration: int):
        """매 프레임 호출"""
        if not hasattr(self.bot, "time"):
            return

        game_time = self.bot.time

        # 빌드 오더 추적
        await self._track_build_order(game_time)

        # 확장 추적
        await self._track_expansions(game_time)

        # 유닛 생산 추적
        await self._track_unit_production(game_time)

        # 테크/업그레이드 추적
        await self._track_tech_upgrades(game_time)

        # 교전 감지
        await self._detect_engagements(game_time)

        # 자원 스냅샷 (60초마다)
        if game_time - self.last_snapshot_time >= self.snapshot_interval:
            self._take_resource_snapshot(game_time)
            self.last_snapshot_time = game_time

        # ★ 추가 학습 항목 추적 ★
        # 적 정찰 정보
        await self._track_enemy_scouts(game_time)

        # 하라스 감지
        await self._track_harassment(game_time)

        # 방어 이벤트
        await self._track_defense_events(game_time)

        # 유닛 구성비 스냅샷 (2분마다)
        if game_time - self._last_composition_time >= self._composition_interval:
            self._track_unit_composition(game_time)
            self._last_composition_time = game_time

        # 맵 장악도 (60초마다)
        if game_time - self.last_snapshot_time >= self.snapshot_interval:
            self._track_map_control(game_time)

    async def _track_build_order(self, game_time: float):
        """빌드 오더 추적 (처음 5분)"""
        if game_time > 300:  # 5분 이후는 추적 안함
            return

        for structure in self.bot.structures:
            if structure.tag not in self._tracked_structures:
                self._tracked_structures.add(structure.tag)

                # 건설 시작 시간 기록
                if not structure.is_ready:
                    self.game_data["build_order"].append({
                        "time": round(game_time, 1),
                        "supply": self.bot.supply_used,
                        "action": "build_start",
                        "unit_type": str(structure.type_id),
                        "position": [round(structure.position.x, 1), round(structure.position.y, 1)]
                    })

    async def _track_expansions(self, game_time: float):
        """확장 기지 추적"""
        current_bases = self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 0

        # 새로운 확장 발견
        for townhall in self.bot.townhalls:
            if townhall.tag not in self._tracked_structures:
                expansion_number = len([e for e in self.game_data["expansions"]]) + 1

                self.game_data["expansions"].append({
                    "time": round(game_time, 1),
                    "expansion_number": expansion_number,
                    "supply": self.bot.supply_used,
                    "minerals": self.bot.minerals,
                    "vespene": self.bot.vespene,
                    "position": [round(townhall.position.x, 1), round(townhall.position.y, 1)]
                })

                self._tracked_structures.add(townhall.tag)

    async def _track_unit_production(self, game_time: float):
        """유닛 생산 추적"""
        if game_time > 600:  # 10분 이후는 추적 안함 (너무 많음)
            return

        for unit in self.bot.units:
            if unit.tag not in self._tracked_units:
                self._tracked_units.add(unit.tag)

                # 전투 유닛만 기록
                combat_units = [
                    UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.HYDRALISK,
                    UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR, UnitTypeId.BANELING,
                    UnitTypeId.RAVAGER, UnitTypeId.LURKERMP, UnitTypeId.INFESTOR,
                    UnitTypeId.SWARMHOSTMP, UnitTypeId.VIPER, UnitTypeId.ULTRALISK,
                    UnitTypeId.BROODLORD
                ]

                if UnitTypeId and unit.type_id in combat_units:
                    self.game_data["unit_production"].append({
                        "time": round(game_time, 1),
                        "unit_type": str(unit.type_id),
                        "supply": self.bot.supply_used
                    })

    async def _track_tech_upgrades(self, game_time: float):
        """테크 건물 및 업그레이드 추적"""
        tech_buildings = [
            UnitTypeId.LAIR, UnitTypeId.HIVE,
            UnitTypeId.ROACHWARREN, UnitTypeId.HYDRALISKDEN,
            UnitTypeId.SPIRE, UnitTypeId.GREATERSPIRE,
            UnitTypeId.INFESTATIONPIT, UnitTypeId.ULTRALISKCAVERN,
            UnitTypeId.LURKERDENMP, UnitTypeId.EVOLUTIONCHAMBER
        ]

        if not UnitTypeId:
            return

        for structure in self.bot.structures:
            if structure.type_id in tech_buildings:
                if structure.tag not in self._tracked_upgrades:
                    self._tracked_upgrades.add(structure.tag)

                    self.game_data["tech_upgrades"].append({
                        "time": round(game_time, 1),
                        "building": str(structure.type_id),
                        "supply": self.bot.supply_used,
                        "minerals": self.bot.minerals,
                        "vespene": self.bot.vespene
                    })

    async def _detect_engagements(self, game_time: float):
        """교전 감지 (병력 손실 감지)"""
        if self._engagement_cooldown > 0:
            self._engagement_cooldown -= 1
            return

        current_army_supply = self.bot.supply_army

        # 병력이 갑자기 10 이상 줄었으면 교전 발생
        supply_lost = self._last_army_supply - current_army_supply

        if supply_lost >= 10:
            self.game_data["engagements"].append({
                "time": round(game_time, 1),
                "supply_lost": supply_lost,
                "remaining_army": current_army_supply,
                "minerals": self.bot.minerals,
                "vespene": self.bot.vespene
            })

            self._engagement_cooldown = 10  # 10초 쿨다운

        self._last_army_supply = current_army_supply

    def _take_resource_snapshot(self, game_time: float):
        """자원 상태 스냅샷"""
        self.game_data["resource_snapshots"].append({
            "time": round(game_time, 1),
            "minerals": self.bot.minerals,
            "vespene": self.bot.vespene,
            "supply_used": self.bot.supply_used,
            "supply_cap": self.bot.supply_cap,
            "supply_army": self.bot.supply_army,
            "supply_workers": self.bot.supply_workers,
            "bases": self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 0,
            "workers": self.bot.workers.amount if hasattr(self.bot, "workers") else 0
        })

    def log_decision(self, decision_type: str, details: Dict[str, Any]):
        """의사결정 로그 (중요한 결정만)"""
        if not hasattr(self.bot, "time"):
            return

        self.game_data["decision_log"].append({
            "time": round(self.bot.time, 1),
            "type": decision_type,
            "details": details
        })

    def finalize_game(self, result: str):
        """게임 종료 시 최종 결과 기록"""
        end_time = datetime.now()
        game_duration = (end_time - self.start_time).total_seconds()

        self.game_data["game_result"] = {
            "result": result,  # "Victory" or "Defeat"
            "duration": round(game_duration, 1),
            "final_supply": self.bot.supply_used,
            "final_minerals": self.bot.minerals,
            "final_vespene": self.bot.vespene,
            "final_bases": self.bot.townhalls.amount if hasattr(self.bot, "townhalls") else 0,
            "end_time": end_time.isoformat()
        }

        # 파일 저장
        self._save_to_file()

    def _save_to_file(self):
        """JSON 파일로 저장"""
        # 디렉토리 생성
        games_dir = os.path.join("data", "games")
        os.makedirs(games_dir, exist_ok=True)

        # 파일명 생성
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        map_name = self.game_data["meta"].get("map_name", "Unknown").replace(" ", "_")
        opponent_race = self.game_data["meta"].get("opponent_race", "Unknown")
        result = self.game_data["game_result"].get("result", "Unknown")

        filename = f"{timestamp}_{map_name}_vs_{opponent_race}_{result}.json"
        filepath = os.path.join(games_dir, filename)

        # JSON 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.game_data, f, indent=2, ensure_ascii=False)

        print(f"[GAME_LOGGER] Game data saved: {filename}")

    # ============================================================
    # ★ 추가 학습 항목 추적 메서드 ★
    # ============================================================

    async def _track_enemy_scouts(self, game_time: float):
        """적 정찰 정보 추적"""
        if not hasattr(self.bot, "enemy_units"):
            return

        enemy_units = self.bot.enemy_units
        our_bases = self.bot.townhalls if hasattr(self.bot, "townhalls") else []

        # 우리 기지 근처에 적 유닛 감지
        for base in our_bases:
            nearby_enemies = enemy_units.closer_than(15, base)
            if nearby_enemies:
                # 정찰 유닛 감지 (Overlord, Observer, Reaper 등)
                scout_types = ["OVERLORD", "OBSERVER", "REAPER", "SCV", "PROBE", "DRONE"]
                scouts = [u for u in nearby_enemies if str(u.type_id).upper() in scout_types]

                if scouts:
                    for scout in scouts:
                        self.game_data["enemy_scouts"].append({
                            "time": round(game_time, 1),
                            "unit_type": str(scout.type_id),
                            "position": [round(scout.position.x, 1), round(scout.position.y, 1)],
                            "near_base": [round(base.position.x, 1), round(base.position.y, 1)]
                        })

    async def _track_harassment(self, game_time: float):
        """하라스 기록 (적 확장, 일꾼 등 공격)"""
        if self._harassment_cooldown > 0:
            self._harassment_cooldown -= 1
            return

        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_structures"):
            return

        our_units = self.bot.units
        enemy_structures = self.bot.enemy_structures
        enemy_workers = self.bot.enemy_units.filter(
            lambda u: str(u.type_id).upper() in ["SCV", "PROBE", "DRONE"]
        ) if hasattr(self.bot, "enemy_units") else []

        # 적 기지 근처에 우리 유닛이 있으면 하라스 중
        for structure in enemy_structures:
            nearby_our_units = our_units.closer_than(10, structure)
            if nearby_our_units.amount >= 3:  # 3마리 이상
                self.game_data["harassment"].append({
                    "time": round(game_time, 1),
                    "our_units": nearby_our_units.amount,
                    "target_structure": str(structure.type_id),
                    "target_position": [round(structure.position.x, 1), round(structure.position.y, 1)],
                    "workers_killed": len([w for w in enemy_workers if w.distance_to(structure) < 10])
                })
                self._harassment_cooldown = 30  # 30초 쿨다운
                break

    async def _track_defense_events(self, game_time: float):
        """방어 이벤트 추적"""
        if not hasattr(self.bot, "enemy_units") or not hasattr(self.bot, "townhalls"):
            return

        enemy_units = self.bot.enemy_units
        our_bases = self.bot.townhalls

        for base in our_bases:
            nearby_enemies = enemy_units.closer_than(15, base)

            if nearby_enemies.amount >= 5:  # 5명 이상 적이 있으면 방어 상황
                self.game_data["defense_events"].append({
                    "time": round(game_time, 1),
                    "enemy_count": nearby_enemies.amount,
                    "base_position": [round(base.position.x, 1), round(base.position.y, 1)],
                    "our_army_nearby": self.bot.units.closer_than(15, base).amount,
                    "base_health": round(base.health / base.health_max * 100, 1) if hasattr(base, "health") else 100
                })

    def _track_unit_composition(self, game_time: float):
        """유닛 구성비 스냅샷"""
        if not hasattr(self.bot, "units"):
            return

        composition = {}
        total_supply = 0

        for unit in self.bot.units:
            unit_type = str(unit.type_id)
            supply = getattr(unit, "supply_cost", 1)

            if unit_type not in composition:
                composition[unit_type] = {"count": 0, "supply": 0}

            composition[unit_type]["count"] += 1
            composition[unit_type]["supply"] += supply
            total_supply += supply

        # 비율 계산
        for unit_type, data in composition.items():
            data["ratio"] = round(data["supply"] / total_supply, 3) if total_supply > 0 else 0

        self.game_data["unit_composition"].append({
            "time": round(game_time, 1),
            "total_supply": total_supply,
            "composition": composition
        })

    def _track_map_control(self, game_time: float):
        """맵 장악도 추적"""
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return

        our_units = self.bot.units
        enemy_units = self.bot.enemy_units

        # 맵을 그리드로 나눠서 장악도 계산
        map_center = self.bot.game_info.map_center if hasattr(self.bot, "game_info") else None
        if not map_center:
            return

        # 중앙 장악도 (중앙 30 거리 내 유닛 수)
        our_center_units = our_units.closer_than(30, map_center).amount
        enemy_center_units = enemy_units.closer_than(30, map_center).amount

        # 확장 위치 장악도
        expansion_locations = self.bot.expansion_locations_list if hasattr(self.bot, "expansion_locations_list") else []
        controlled_expansions = 0
        for exp_loc in expansion_locations[:5]:  # 첫 5개만
            our_nearby = our_units.closer_than(10, exp_loc).amount
            enemy_nearby = enemy_units.closer_than(10, exp_loc).amount
            if our_nearby > enemy_nearby:
                controlled_expansions += 1

        self.game_data["map_control"].append({
            "time": round(game_time, 1),
            "center_control": {
                "our_units": our_center_units,
                "enemy_units": enemy_center_units,
                "control_ratio": round(our_center_units / (our_center_units + enemy_center_units + 1), 2)
            },
            "controlled_expansions": controlled_expansions,
            "total_expansions_checked": min(5, len(expansion_locations))
        })
