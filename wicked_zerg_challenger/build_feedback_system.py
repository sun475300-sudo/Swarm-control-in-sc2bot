"""
빌드 오더 피드백 시스템

게임 결과를 분석하여 빌드 오더를 자동으로 개선합니다.

기능:
1. 승리/패배 타이밍 분석
2. 자원 효율성 측정
3. 유닛 조합 분석
4. 빌드 오더 자동 조정
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class BuildFeedbackSystem:
    """빌드 오더 피드백 및 자동 개선 시스템"""

    def __init__(self, bot):
        self.bot = bot
        self.data_file = Path("wicked_zerg_challenger/local_training/data/build_feedback.json")
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        # 게임 데이터
        self.game_data = {
            "start_time": datetime.now().isoformat(),
            "build_order": None,
            "milestones": [],
            "resources": [],
            "army_composition": [],
            "result": None,
            "victory_time": None,
            "defeat_reason": None,
        }

        # 마일스톤 추적
        self.milestones_tracked = {
            "spawning_pool": False,
            "first_expansion": False,
            "lair": False,
            "hive": False,
            "spire": False,
        }

        # 자원 효율성 추적
        self.last_resource_check = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        game_time = getattr(self.bot, "time", 0)

        # 초기화
        if iteration == 0:
            self._record_build_order()

        # 마일스톤 추적 (5초마다)
        if iteration % 110 == 0:
            self._track_milestones(game_time)

        # 자원 효율성 측정 (10초마다)
        if iteration % 220 == 0:
            self._track_resources(game_time)

        # 군대 조합 추적 (10초마다)
        if iteration % 220 == 0:
            self._track_army_composition(game_time)

    def _record_build_order(self):
        """현재 빌드 오더 기록"""
        if hasattr(self.bot, "build_order_system"):
            build_order = getattr(self.bot.build_order_system, "current_build_order", "unknown")
            self.game_data["build_order"] = build_order

    def _track_milestones(self, game_time: float):
        """주요 마일스톤 추적"""
        from sc2.ids.unit_typeid import UnitTypeId

        # Spawning Pool
        if not self.milestones_tracked["spawning_pool"]:
            if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                self.game_data["milestones"].append({
                    "name": "spawning_pool",
                    "time": game_time,
                })
                self.milestones_tracked["spawning_pool"] = True

        # First Expansion
        if not self.milestones_tracked["first_expansion"]:
            if self.bot.townhalls.amount >= 2:
                self.game_data["milestones"].append({
                    "name": "first_expansion",
                    "time": game_time,
                })
                self.milestones_tracked["first_expansion"] = True

        # Lair
        if not self.milestones_tracked["lair"]:
            if self.bot.structures(UnitTypeId.LAIR).ready.exists:
                self.game_data["milestones"].append({
                    "name": "lair",
                    "time": game_time,
                })
                self.milestones_tracked["lair"] = True

        # Hive
        if not self.milestones_tracked["hive"]:
            if self.bot.structures(UnitTypeId.HIVE).ready.exists:
                self.game_data["milestones"].append({
                    "name": "hive",
                    "time": game_time,
                })
                self.milestones_tracked["hive"] = True

        # Spire
        if not self.milestones_tracked["spire"]:
            if self.bot.structures(UnitTypeId.SPIRE).ready.exists:
                self.game_data["milestones"].append({
                    "name": "spire",
                    "time": game_time,
                })
                self.milestones_tracked["spire"] = True

    def _track_resources(self, game_time: float):
        """자원 효율성 추적"""
        minerals = getattr(self.bot, "minerals", 0)
        vespene = getattr(self.bot, "vespene", 0)
        workers = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
        supply_used = getattr(self.bot, "supply_used", 0)
        supply_cap = getattr(self.bot, "supply_cap", 0)

        self.game_data["resources"].append({
            "time": game_time,
            "minerals": minerals,
            "vespene": vespene,
            "workers": workers,
            "supply_used": supply_used,
            "supply_cap": supply_cap,
        })

    def _track_army_composition(self, game_time: float):
        """군대 조합 추적"""
        from sc2.ids.unit_typeid import UnitTypeId

        composition = {}

        combat_types = [
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.ULTRALISK,
        ]

        for unit_type in combat_types:
            count = self.bot.units(unit_type).amount
            if count > 0:
                composition[unit_type.name] = count

        if composition:
            self.game_data["army_composition"].append({
                "time": game_time,
                "composition": composition,
            })

    async def on_game_end(self, result: str):
        """게임 종료 시 호출"""
        game_time = getattr(self.bot, "time", 0)

        self.game_data["result"] = result

        if result == "Victory":
            self.game_data["victory_time"] = game_time
        else:
            # 패배 원인 파악
            if hasattr(self.bot, "defeat_detection"):
                defeat_status = self.bot.defeat_detection._get_current_status()
                self.game_data["defeat_reason"] = defeat_status.get("defeat_reason", "Unknown")

        # 데이터 저장
        self._save_game_data()

        # 피드백 분석 및 빌드 조정
        self._analyze_and_improve()

    def _save_game_data(self):
        """게임 데이터 저장"""
        try:
            # 기존 데이터 로드
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            else:
                all_data = {"games": []}

            # 새 게임 데이터 추가
            all_data["games"].append(self.game_data)

            # 최근 100게임만 유지
            if len(all_data["games"]) > 100:
                all_data["games"] = all_data["games"][-100:]

            # 저장
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)

            print(f"[BUILD FEEDBACK] Game data saved: {len(all_data['games'])} total games")

        except Exception as e:
            print(f"[BUILD FEEDBACK ERROR] Failed to save: {e}")

    def _analyze_and_improve(self):
        """
        게임 데이터 분석 및 빌드 개선

        분석 항목:
        1. 승리 시 평균 타이밍
        2. 자원 효율성
        3. 최적 유닛 조합
        4. 빌드 오더별 승률
        """
        try:
            if not self.data_file.exists():
                return

            with open(self.data_file, "r", encoding="utf-8") as f:
                all_data = json.load(f)

            games = all_data.get("games", [])

            if len(games) < 5:
                print("[BUILD FEEDBACK] Not enough data yet (need 5+ games)")
                return

            # 최근 20게임 분석
            recent_games = games[-20:]

            # 승률 계산
            victories = [g for g in recent_games if g["result"] == "Victory"]
            win_rate = len(victories) / len(recent_games)

            # 평균 승리 시간
            if victories:
                avg_victory_time = sum(g["victory_time"] for g in victories) / len(victories)
            else:
                avg_victory_time = 0

            print(f"\n[BUILD FEEDBACK] Analysis:")
            print(f"  Win Rate: {win_rate * 100:.1f}% ({len(victories)}/{len(recent_games)})")
            print(f"  Avg Victory Time: {avg_victory_time:.0f}s")

            # 빌드 오더별 분석
            build_stats = {}
            for game in recent_games:
                build = game.get("build_order", "unknown")
                if build not in build_stats:
                    build_stats[build] = {"wins": 0, "total": 0}

                build_stats[build]["total"] += 1
                if game["result"] == "Victory":
                    build_stats[build]["wins"] += 1

            print(f"\n  Build Order Stats:")
            for build, stats in build_stats.items():
                wr = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
                print(f"    {build}: {wr * 100:.1f}% ({stats['wins']}/{stats['total']})")

            # 추천 사항
            self._generate_recommendations(recent_games, victories, avg_victory_time)

        except Exception as e:
            print(f"[BUILD FEEDBACK ERROR] Analysis failed: {e}")

    def _generate_recommendations(self, recent_games: List, victories: List, avg_victory_time: float):
        """개선 추천 사항 생성"""
        print(f"\n[BUILD FEEDBACK] Recommendations:")

        # 1. 승리 시간 분석
        if avg_victory_time > 600:  # 10분 이상
            print(f"  - 승리가 너무 느림 ({avg_victory_time:.0f}s) → 더 공격적인 전략 필요")
            print(f"    → 제안: 3분 저글링 공격, 5분 바퀴 푸시")
        elif avg_victory_time < 300:  # 5분 미만
            print(f"  - 매우 빠른 승리! ({avg_victory_time:.0f}s) → 현재 전략 유지")

        # 2. 자원 효율성
        if victories:
            # 승리 게임의 자원 활용도 분석
            for game in victories[-3:]:  # 최근 3승
                resources = game.get("resources", [])
                if resources:
                    # 중반 (5분) 자원 상태
                    mid_game = [r for r in resources if 250 < r["time"] < 350]
                    if mid_game:
                        avg_minerals = sum(r["minerals"] for r in mid_game) / len(mid_game)
                        if avg_minerals > 1000:
                            print(f"  - 미네랄 과잉 ({avg_minerals:.0f}) → 유닛 생산 증가 필요")

        # 3. 유닛 조합
        if victories:
            # 승리 게임의 유닛 조합 분석
            unit_usage = {}
            for game in victories:
                compositions = game.get("army_composition", [])
                for comp in compositions:
                    for unit, count in comp["composition"].items():
                        if unit not in unit_usage:
                            unit_usage[unit] = []
                        unit_usage[unit].append(count)

            if unit_usage:
                print(f"  - 승리 시 주력 유닛:")
                for unit, counts in sorted(unit_usage.items(), key=lambda x: sum(x[1]), reverse=True)[:3]:
                    avg = sum(counts) / len(counts)
                    print(f"    → {unit}: 평균 {avg:.1f}마리")

        print()
