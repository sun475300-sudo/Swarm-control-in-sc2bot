# -*- coding: utf-8 -*-
"""
Game Analytics System - 게임 분석 및 통계 시스템

목적: 게임 결과 상세 분석 및 통계
- 패배 원인 자동 분석
- 종족별 승률 추적
- 맵별 승률 분석
- 타이밍 분석 (게임 길이, 첫 공격, 확장 등)
"""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("GameAnalyticsSystem")


class DefeatReason(Enum):
    """패배 원인"""

    EARLY_RUSH = "초반 러시"  # 0-3분
    ECONOMY_COLLAPSE = "경제 붕괴"  # 미네랄/가스 부족
    ARMY_WIPEOUT = "병력 전멸"  # 전투 패배
    TECH_DISADVANTAGE = "기술력 열세"  # 업그레이드/유닛 차이
    EXPANSION_FAILURE = "확장 실패"  # 멀티 확장 실패
    HARASSMENT = "견제 피해"  # 드랍, 견제로 인한 피해
    RESOURCE_DENIAL = "자원 봉쇄"  # 가스/미네랄 봉쇄
    TIMEOUT = "시간 초과"  # 장기전 패배
    UNKNOWN = "알 수 없음"


class GameAnalytics:
    """
    게임 분석 시스템

    핵심 기능:
    1. 패배 원인 자동 분석
    2. 종족별/맵별 승률 통계
    3. 타이밍 분석
    4. 개선 제안
    """

    def __init__(self):
        # 게임 기록
        self.games: List[Dict] = []
        self.total_games = 0
        self.total_wins = 0

        # 종족별 통계
        self.race_stats: Dict[str, Dict] = {
            "Terran": {"games": 0, "wins": 0, "avg_time": 0.0},
            "Protoss": {"games": 0, "wins": 0, "avg_time": 0.0},
            "Zerg": {"games": 0, "wins": 0, "avg_time": 0.0},
        }

        # 맵별 통계
        self.map_stats: Dict[str, Dict] = {}

        # 패배 원인 통계
        self.defeat_reasons: Dict[str, int] = {
            reason.value: 0 for reason in DefeatReason
        }

        # 타이밍 분석
        self.timing_stats = {
            "avg_game_time": 0.0,
            "shortest_game": float("inf"),
            "longest_game": 0.0,
            "avg_first_expand": 0.0,
            "avg_pool_timing": 0.0,
        }

        # 저장 경로
        self.save_path = Path("local_training/game_analytics.json")
        self.detailed_log_path = Path("local_training/detailed_game_log.jsonl")

        # 로드
        self._load_stats()

    def record_game(
        self,
        game_id: int,
        map_name: str,
        opponent_race: str,
        difficulty: str,
        result: str,
        game_time: float,
        defeat_reason: Optional[DefeatReason] = None,
        additional_stats: Optional[Dict] = None,
    ) -> None:
        """
        게임 결과 기록 및 분석
        """
        # 승리 여부
        won = "VICTORY" in result.upper() or "WIN" in result.upper()

        # 패배 원인 자동 분석
        if not won and defeat_reason is None:
            defeat_reason = self._analyze_defeat_reason(
                game_time, additional_stats or {}
            )

        # Use globally unique ID to prevent duplicates across session restarts
        unique_game_id = str(uuid.uuid4())[:8] + f"_{self.total_games + 1}"

        # 게임 기록
        game_record = {
            "game_id": unique_game_id,
            "timestamp": datetime.now().isoformat(),
            "map": map_name,
            "opponent_race": opponent_race,
            "difficulty": difficulty,
            "result": result,
            "won": won,
            "game_time": game_time,
            "defeat_reason": defeat_reason.value if defeat_reason else None,
            "additional_stats": additional_stats or {},
        }

        self.games.append(game_record)
        self.total_games += 1
        if won:
            self.total_wins += 1

        # 종족별 통계 업데이트
        if opponent_race in self.race_stats:
            self.race_stats[opponent_race]["games"] += 1
            if won:
                self.race_stats[opponent_race]["wins"] += 1

            # 평균 게임 시간 업데이트
            race = self.race_stats[opponent_race]
            race["avg_time"] = (
                race["avg_time"] * (race["games"] - 1) + game_time
            ) / race["games"]

        # 맵별 통계 업데이트
        if map_name not in self.map_stats:
            self.map_stats[map_name] = {"games": 0, "wins": 0, "avg_time": 0.0}

        self.map_stats[map_name]["games"] += 1
        if won:
            self.map_stats[map_name]["wins"] += 1

        map_stat = self.map_stats[map_name]
        map_stat["avg_time"] = (
            map_stat["avg_time"] * (map_stat["games"] - 1) + game_time
        ) / map_stat["games"]

        # 패배 원인 통계
        if not won and defeat_reason:
            self.defeat_reasons[defeat_reason.value] += 1

        # 타이밍 분석
        self._update_timing_stats(game_time, additional_stats or {})

        # 상세 로그 저장 (JSONL 형식)
        self._save_detailed_log(game_record)

        # 주기적 저장 (10게임마다)
        if self.total_games % 10 == 0:
            self._save_stats()

        # 즉시 분석 출력 (패배 시)
        if not won:
            logger.info(self._get_defeat_analysis(game_record))

    def _analyze_defeat_reason(self, game_time: float, stats: Dict) -> DefeatReason:
        """패배 원인 자동 분석"""
        # 초반 러시 (3분 이내)
        if game_time < 180:
            return DefeatReason.EARLY_RUSH

        # 경제 붕괴 (일꾼 수 부족)
        worker_count = stats.get("worker_count", 0)
        if worker_count < 16 and game_time < 300:
            return DefeatReason.ECONOMY_COLLAPSE

        # 병력 전멸 (유닛 수 극소)
        army_count = stats.get("army_count", 0)
        if army_count < 5:
            return DefeatReason.ARMY_WIPEOUT

        # 확장 실패 (기지 1개만)
        base_count = stats.get("base_count", 1)
        if base_count == 1 and game_time > 300:
            return DefeatReason.EXPANSION_FAILURE

        # 시간 초과 (20분 이상)
        if game_time > 1200:
            return DefeatReason.TIMEOUT

        return DefeatReason.UNKNOWN

    def _update_timing_stats(self, game_time: float, stats: Dict) -> None:
        """타이밍 통계 업데이트"""
        # 평균 게임 시간
        self.timing_stats["avg_game_time"] = (
            self.timing_stats["avg_game_time"] * (self.total_games - 1) + game_time
        ) / self.total_games

        # 최단/최장 게임
        if game_time < self.timing_stats["shortest_game"]:
            self.timing_stats["shortest_game"] = game_time

        if game_time > self.timing_stats["longest_game"]:
            self.timing_stats["longest_game"] = game_time

        # Pool 타이밍
        pool_timing = stats.get("pool_timing", 0)
        if pool_timing > 0:
            if self.timing_stats["avg_pool_timing"] == 0.0:
                self.timing_stats["avg_pool_timing"] = pool_timing
            else:
                self.timing_stats["avg_pool_timing"] = (
                    self.timing_stats["avg_pool_timing"] * 0.9 + pool_timing * 0.1
                )

        # 첫 확장 타이밍
        expand_timing = stats.get("first_expand_timing", 0)
        if expand_timing > 0:
            if self.timing_stats["avg_first_expand"] == 0.0:
                self.timing_stats["avg_first_expand"] = expand_timing
            else:
                self.timing_stats["avg_first_expand"] = (
                    self.timing_stats["avg_first_expand"] * 0.9 + expand_timing * 0.1
                )

    def _get_defeat_analysis(self, game_record: Dict) -> str:
        """패배 분석 메시지 생성"""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"[GAME ANALYTICS] 패배 분석 - Game #{game_record['game_id']}")
        lines.append(f"{'='*60}")

        lines.append(f"맵: {game_record['map']}")
        lines.append(
            f"상대: {game_record['opponent_race']} ({game_record['difficulty']})"
        )
        lines.append(
            f"게임 시간: {int(game_record['game_time'])}초 ({int(game_record['game_time']//60)}분)"
        )
        lines.append(f"패배 원인: {game_record['defeat_reason']}")

        # 개선 제안
        suggestions = self._get_improvement_suggestions(game_record)
        if suggestions:
            lines.append("\n[IDEA] 개선 제안:")
            for suggestion in suggestions:
                lines.append(f"  - {suggestion}")

        lines.append(f"{'='*60}\n")
        return "\n".join(lines)

    def _get_improvement_suggestions(self, game_record: Dict) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        defeat_reason = game_record.get("defeat_reason")
        game_time = game_record.get("game_time", 0)

        if defeat_reason == DefeatReason.EARLY_RUSH.value:
            suggestions.append("초반 방어 강화 필요 (스파인 크롤러, 저글링)")
            suggestions.append("정찰 강화 - 적의 초반 빌드 확인")

        elif defeat_reason == DefeatReason.ECONOMY_COLLAPSE.value:
            suggestions.append("드론 생산 우선순위 높이기")
            suggestions.append("확장 타이밍 개선")

        elif defeat_reason == DefeatReason.ARMY_WIPEOUT.value:
            suggestions.append("병력 보존 - 무리한 교전 회피")
            suggestions.append("전투 전 병력 집결")

        elif defeat_reason == DefeatReason.EXPANSION_FAILURE.value:
            suggestions.append("확장 타이밍 개선 (3-4분)")
            suggestions.append("확장 기지 방어 강화")

        elif game_time < 120:
            suggestions.append("극초반 생존율 향상 필요!")
            suggestions.append("빌드 오더 점검 필요")

        return suggestions

    def get_summary(self) -> str:
        """통계 요약"""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append("[GAME ANALYTICS] 전체 통계")
        lines.append(f"{'='*60}")

        # 전체 승률
        win_rate = (
            (self.total_wins / self.total_games * 100) if self.total_games > 0 else 0.0
        )
        lines.append(
            f"전체 승률: {self.total_wins}/{self.total_games}승 ({win_rate:.1f}%)"
        )
        lines.append(f"평균 게임 시간: {int(self.timing_stats['avg_game_time'])}초")

        # 종족별 승률
        lines.append("\n종족별 승률:")
        for race, stats in self.race_stats.items():
            if stats["games"] > 0:
                race_wr = stats["wins"] / stats["games"] * 100
                lines.append(
                    f"  vs {race}: {stats['wins']}/{stats['games']}승 ({race_wr:.1f}%) | 평균: {int(stats['avg_time'])}초"
                )

        # 맵별 승률 (상위 5개)
        lines.append("\n맵별 승률 (상위 5개):")
        sorted_maps = sorted(
            self.map_stats.items(), key=lambda x: x[1]["games"], reverse=True
        )[:5]
        for map_name, stats in sorted_maps:
            if stats["games"] > 0:
                map_wr = stats["wins"] / stats["games"] * 100
                lines.append(
                    f"  {map_name}: {stats['wins']}/{stats['games']}승 ({map_wr:.1f}%)"
                )

        # 패배 원인 Top 3
        lines.append("\n주요 패배 원인:")
        sorted_reasons = sorted(
            self.defeat_reasons.items(), key=lambda x: x[1], reverse=True
        )[:3]
        for reason, count in sorted_reasons:
            if count > 0:
                lines.append(f"  {reason}: {count}회")

        lines.append(f"{'='*60}\n")
        return "\n".join(lines)

    def get_race_specific_advice(self, opponent_race: str) -> str:
        """종족별 조언"""
        if opponent_race not in self.race_stats:
            return ""

        stats = self.race_stats[opponent_race]
        if stats["games"] < 3:
            return f"\n[ADVICE] vs {opponent_race}: 데이터 부족 (최소 3게임 필요)"

        win_rate = (stats["wins"] / stats["games"] * 100) if stats["games"] > 0 else 0.0

        lines = []
        lines.append(f"\n[ADVICE] vs {opponent_race} 조언:")

        if win_rate < 20:
            lines.append(f"  [!] 승률 매우 낮음 ({win_rate:.1f}%) - 전략 재검토 필요")
            lines.append(f"  - {opponent_race}에 특화된 빌드 오더 연구")
            lines.append(f"  - {opponent_race}의 주요 전략 파악")

        elif win_rate < 40:
            lines.append(f"  [WARNING] 승률 낮음 ({win_rate:.1f}%) - 개선 필요")
            lines.append(f"  - {opponent_race}에 대한 카운터 전략 개발")

        elif win_rate < 60:
            lines.append(f"  [O] 승률 보통 ({win_rate:.1f}%) - 추가 연습 필요")

        else:
            lines.append(f"  [OK] 승률 양호 ({win_rate:.1f}%) - 현재 전략 유지")

        return "\n".join(lines)

    def _save_stats(self) -> None:
        """통계 저장"""
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "total_games": self.total_games,
                "total_wins": self.total_wins,
                "race_stats": self.race_stats,
                "map_stats": self.map_stats,
                "defeat_reasons": self.defeat_reasons,
                "timing_stats": self.timing_stats,
                "recent_games": self.games[-50:],  # 최근 50게임만 저장
            }

            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.info(f"저장 실패: {e}")

    def _save_detailed_log(self, game_record: Dict) -> None:
        """상세 로그 저장 (JSONL)"""
        try:
            self.detailed_log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.detailed_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(game_record, ensure_ascii=False) + "\n")

        except Exception as e:
            logger.info(f"상세 로그 저장 실패: {e}")

    def _load_stats(self) -> None:
        """통계 로드"""
        try:
            if self.save_path.exists():
                with open(self.save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.total_games = data.get("total_games", 0)
                self.total_wins = data.get("total_wins", 0)
                self.race_stats = data.get("race_stats", self.race_stats)
                self.map_stats = data.get("map_stats", {})
                self.defeat_reasons = data.get("defeat_reasons", self.defeat_reasons)
                self.timing_stats = data.get("timing_stats", self.timing_stats)
                self.games = data.get("recent_games", [])

                logger.info(f"통계 로드 완료 - {self.total_games}게임")

        except Exception as e:
            logger.info(f"로드 실패 (새로 시작): {e}")
