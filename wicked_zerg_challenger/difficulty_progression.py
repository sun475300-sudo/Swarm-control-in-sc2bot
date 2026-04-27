# -*- coding: utf-8 -*-
"""
Difficulty Progression System - 난이도 자동 조정

승률 90% 도달 시 자동으로 다음 난이도로 상승:
- 맵별, 종족별, 난이도별 승률 추적
- 90% 승률 도달 시 난이도 자동 상승
- 데이터 영구 저장
"""

import json
from pathlib import Path
from typing import Dict, Optional
from sc2.data import Difficulty, Race
import logging

logger = logging.getLogger("DifficultyProgression")


class DifficultyProgression:
    """
    난이도 자동 조정 시스템

    기능:
    1. 맵별/종족별/난이도별 승률 추적
    2. 90% 승률 도달 시 자동 상승
    3. 진행도 저장/로드
    """

    # 난이도 순서
    DIFFICULTY_LADDER = [
        Difficulty.VeryEasy,
        Difficulty.Easy,
        Difficulty.Medium,
        Difficulty.MediumHard,
        Difficulty.Hard,
        Difficulty.Harder,
        Difficulty.VeryHard,
        Difficulty.CheatVision,
        Difficulty.CheatMoney,
        Difficulty.CheatInsane,
    ]

    def __init__(
        self, data_file: str = "local_training/data/difficulty_progression.json"
    ):
        self.data_file = Path(data_file)
        self.stats: Dict = {}  # {map_name: {race: {difficulty: {wins, losses}}}}
        self.win_rate_threshold = 0.90  # 90%
        self.min_games_for_progression = 10  # 최소 10게임

        self._load_stats()

    def _load_stats(self) -> None:
        """통계 데이터 로드"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert string keys back to enums
                    self.stats = self._deserialize_stats(data)
                    logger.info(f"Loaded progression data: {len(self.stats)} maps")
            except Exception as e:
                logger.info(f"Error loading stats: {e}")
                self.stats = {}
        else:
            self.stats = {}
            logger.info(f"No existing progression data, starting fresh")

    def _save_stats(self) -> None:
        """통계 데이터 저장"""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            # Convert enums to strings for JSON
            serialized = self._serialize_stats(self.stats)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved progression data")
        except Exception as e:
            logger.info(f"Error saving stats: {e}")

    def _serialize_stats(self, stats: Dict) -> Dict:
        """Enum을 문자열로 변환"""
        serialized = {}
        for map_name, map_data in stats.items():
            serialized[map_name] = {}
            for race, race_data in map_data.items():
                race_str = race.name if isinstance(race, Race) else str(race)
                serialized[map_name][race_str] = {}
                for diff, diff_data in race_data.items():
                    diff_str = diff.name if isinstance(diff, Difficulty) else str(diff)
                    serialized[map_name][race_str][diff_str] = diff_data
        return serialized

    def _deserialize_stats(self, serialized: Dict) -> Dict:
        """문자열을 Enum으로 변환"""
        stats = {}
        for map_name, map_data in serialized.items():
            stats[map_name] = {}
            for race_str, race_data in map_data.items():
                try:
                    race = Race[race_str]
                except (KeyError, AttributeError):
                    continue
                stats[map_name][race] = {}
                for diff_str, diff_data in race_data.items():
                    try:
                        diff = Difficulty[diff_str]
                    except (KeyError, AttributeError):
                        continue
                    stats[map_name][race][diff] = diff_data
        return stats

    def record_game(
        self, map_name: str, opponent_race: Race, difficulty: Difficulty, won: bool
    ) -> None:
        """게임 결과 기록"""
        # 맵 초기화
        if map_name not in self.stats:
            self.stats[map_name] = {}

        # 종족 초기화
        if opponent_race not in self.stats[map_name]:
            self.stats[map_name][opponent_race] = {}

        # 난이도 초기화
        if difficulty not in self.stats[map_name][opponent_race]:
            self.stats[map_name][opponent_race][difficulty] = {"wins": 0, "losses": 0}

        # 기록
        if won:
            self.stats[map_name][opponent_race][difficulty]["wins"] += 1
        else:
            self.stats[map_name][opponent_race][difficulty]["losses"] += 1

        # 저장
        self._save_stats()

        # 진행도 체크
        self._check_progression(map_name, opponent_race, difficulty)

    def _check_progression(
        self, map_name: str, opponent_race: Race, difficulty: Difficulty
    ) -> None:
        """승률 체크 및 난이도 상승 판단"""
        stats = self.stats[map_name][opponent_race][difficulty]
        wins = stats["wins"]
        losses = stats["losses"]
        total = wins + losses

        if total < self.min_games_for_progression:
            return

        win_rate = wins / total

        if win_rate >= self.win_rate_threshold:
            next_diff = self._get_next_difficulty(difficulty)
            if next_diff:
                logger.info(f"\n{'='*70}")
                logger.info(f"🎉 DIFFICULTY PROGRESSION! 🎉")
                logger.info(f"{'='*70}")
                logger.info(f"  Map: {map_name}")
                logger.info(f"  Opponent: {opponent_race.name}")
                logger.info(f"  Current: {difficulty.name}")
                logger.info(f"  Win Rate: {win_rate*100:.1f}% ({wins}W/{losses}L)")
                logger.info(f"  >>> ADVANCING TO: {next_diff.name} <<<")
                logger.info(f"{'='*70}\n")

    def _get_next_difficulty(self, current: Difficulty) -> Optional[Difficulty]:
        """다음 난이도 반환"""
        try:
            current_index = self.DIFFICULTY_LADDER.index(current)
            if current_index < len(self.DIFFICULTY_LADDER) - 1:
                return self.DIFFICULTY_LADDER[current_index + 1]
        except ValueError:
            pass
        return None

    def get_recommended_difficulty(
        self, map_name: str, opponent_race: Race
    ) -> Difficulty:
        """추천 난이도 반환"""
        if map_name not in self.stats:
            return Difficulty.Easy  # 기본값

        if opponent_race not in self.stats[map_name]:
            return Difficulty.Easy

        # 가장 높은 난이도 중 90% 미만인 것 찾기
        race_stats = self.stats[map_name][opponent_race]

        highest_qualified = Difficulty.Easy
        for diff in self.DIFFICULTY_LADDER:
            if diff not in race_stats:
                # 아직 시도하지 않은 난이도면 이전 난이도가 90% 넘었는지 확인
                prev_diff = self._get_previous_difficulty(diff)
                if prev_diff and prev_diff in race_stats:
                    prev_stats = race_stats[prev_diff]
                    total = prev_stats["wins"] + prev_stats["losses"]
                    if total >= self.min_games_for_progression:
                        win_rate = prev_stats["wins"] / total
                        if win_rate >= self.win_rate_threshold:
                            return diff
                break
            else:
                stats = race_stats[diff]
                total = stats["wins"] + stats["losses"]
                if total >= self.min_games_for_progression:
                    win_rate = stats["wins"] / total
                    if win_rate < self.win_rate_threshold:
                        return diff
                    else:
                        highest_qualified = diff

        # 모든 난이도를 90% 이상으로 클리어했으면 다음 난이도
        next_diff = self._get_next_difficulty(highest_qualified)
        return next_diff if next_diff else highest_qualified

    def _get_previous_difficulty(self, current: Difficulty) -> Optional[Difficulty]:
        """이전 난이도 반환"""
        try:
            current_index = self.DIFFICULTY_LADDER.index(current)
            if current_index > 0:
                return self.DIFFICULTY_LADDER[current_index - 1]
        except ValueError:
            pass
        return None

    def get_stats_summary(self, map_name: str, opponent_race: Race) -> str:
        """통계 요약"""
        if map_name not in self.stats:
            return f"No stats for {map_name}"

        if opponent_race not in self.stats[map_name]:
            return f"No stats for {opponent_race.name} on {map_name}"

        race_stats = self.stats[map_name][opponent_race]

        lines = []
        lines.append(f"\n{'='*70}")
        lines.append(f"Progression Stats: {map_name} vs {opponent_race.name}")
        lines.append(f"{'='*70}")

        for diff in self.DIFFICULTY_LADDER:
            if diff in race_stats:
                stats = race_stats[diff]
                wins = stats["wins"]
                losses = stats["losses"]
                total = wins + losses
                win_rate = (wins / total * 100) if total > 0 else 0

                status = "[OK]" if win_rate >= self.win_rate_threshold * 100 else "[~]"
                lines.append(
                    f"  {status} {diff.name:15s}: {wins:3d}W / {losses:3d}L "
                    f"= {win_rate:5.1f}% ({total} games)"
                )

        lines.append(f"{'='*70}\n")
        return "\n".join(lines)
