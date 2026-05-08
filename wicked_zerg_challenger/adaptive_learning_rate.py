"""
Adaptive Learning Rate System - 적응형 학습률 시스템

목적: 학습 성능에 따라 학습률 자동 조정
- 승률 향상 시 learning_rate 증가
- 승률 정체 시 learning_rate 감소
- 최적 학습률 자동 탐색
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("AdaptiveLearningRate")


class AdaptiveLearningRate:
    """
    적응형 학습률 조정 시스템

    핵심 기능:
    1. 승률 추적 및 분석
    2. 학습률 자동 조정
    3. 최적 학습률 탐색
    """

    def __init__(
        self,
        initial_lr: float = 0.001,
        min_lr: float = 0.0001,
        max_lr: float = 0.01,
        adjustment_factor: float = 1.2,
        patience: int = 10,
    ):
        # 학습률 파라미터
        self.learning_rate = initial_lr
        self.min_lr = min_lr
        self.max_lr = max_lr
        self.adjustment_factor = adjustment_factor  # 조정 배율 (1.2 = 20% 증가/감소)

        # 성능 추적
        self.recent_win_rates: list[float] = []
        self.window_size = 20  # 최근 20게임 승률 추적
        self.patience = patience  # 개선 없으면 이 횟수 후 조정
        self.games_without_improvement = 0

        # 최적값 추적
        self.best_win_rate = 0.0
        self.best_learning_rate = initial_lr

        # 통계
        self.total_games = 0
        self.total_wins = 0
        self.adjustment_history: list[dict] = []

        # 저장 경로
        self.save_path = Path("local_training/adaptive_lr_stats.json")

        # 로드
        self._load_stats()

    def update(self, game_won: bool) -> Optional[float]:
        """
        게임 결과 업데이트 및 학습률 조정

        Returns:
            새로운 학습률 (조정되었으면), None (조정 안 됨)
        """
        # 게임 기록
        self.total_games += 1
        if game_won:
            self.total_wins += 1

        # 최근 승률 계산 (window_size 게임)
        current_win_rate = self.total_wins / self.total_games

        self.recent_win_rates.append(current_win_rate)
        if len(self.recent_win_rates) > self.window_size:
            self.recent_win_rates.pop(0)

        # 충분한 데이터가 모였으면 조정 판단
        if len(self.recent_win_rates) >= self.window_size:
            recent_avg = sum(self.recent_win_rates) / len(self.recent_win_rates)

            # 승률 개선 확인
            if recent_avg > self.best_win_rate:
                # 개선됨!
                self.best_win_rate = recent_avg
                self.best_learning_rate = self.learning_rate
                self.games_without_improvement = 0

                # 학습률 증가 (더 공격적으로 학습)
                new_lr = self._increase_learning_rate()
                if new_lr:
                    logger.info(
                        f"[OK] 승률 개선! ({recent_avg:.1%}) - 학습률 증가: {self.learning_rate:.6f}"
                    )
                    self._save_stats()
                    return new_lr

            else:
                # 개선 없음
                self.games_without_improvement += 1

                # patience 이상 개선 없으면 학습률 감소
                if self.games_without_improvement >= self.patience:
                    new_lr = self._decrease_learning_rate()
                    if new_lr:
                        logger.warning(
                            f"[WARNING] {self.patience}게임 개선 없음 - 학습률 감소: {self.learning_rate:.6f}"
                        )
                        self.games_without_improvement = 0
                        self._save_stats()
                        return new_lr

        # 주기적으로 저장
        if self.total_games % 10 == 0:
            self._save_stats()

        return None

    def _increase_learning_rate(self) -> Optional[float]:
        """학습률 증가"""
        new_lr = self.learning_rate * self.adjustment_factor

        if new_lr <= self.max_lr:
            old_lr = self.learning_rate
            self.learning_rate = new_lr

            self.adjustment_history.append(
                {
                    "game": self.total_games,
                    "action": "increase",
                    "old_lr": old_lr,
                    "new_lr": new_lr,
                    "win_rate": self.best_win_rate,
                }
            )

            return new_lr

        return None

    def _decrease_learning_rate(self) -> Optional[float]:
        """학습률 감소"""
        new_lr = self.learning_rate / self.adjustment_factor

        if new_lr >= self.min_lr:
            old_lr = self.learning_rate
            self.learning_rate = new_lr

            self.adjustment_history.append(
                {
                    "game": self.total_games,
                    "action": "decrease",
                    "old_lr": old_lr,
                    "new_lr": new_lr,
                    "win_rate": (
                        sum(self.recent_win_rates) / len(self.recent_win_rates)
                        if self.recent_win_rates
                        else 0.0
                    ),
                }
            )

            return new_lr

        # 최소값에 도달했으면 best_learning_rate로 리셋
        if self.learning_rate <= self.min_lr:
            logger.info(
                f"최소 학습률 도달 - 최적값으로 리셋: {self.best_learning_rate:.6f}"
            )
            old_lr = self.learning_rate
            self.learning_rate = self.best_learning_rate

            self.adjustment_history.append(
                {
                    "game": self.total_games,
                    "action": "reset_to_best",
                    "old_lr": old_lr,
                    "new_lr": self.learning_rate,
                    "win_rate": self.best_win_rate,
                }
            )

            return self.learning_rate

        return None

    def get_current_lr(self) -> float:
        """현재 학습률 반환"""
        return self.learning_rate

    def get_stats(self) -> dict:
        """통계 반환"""
        recent_avg = (
            sum(self.recent_win_rates) / len(self.recent_win_rates)
            if self.recent_win_rates
            else 0.0
        )

        return {
            "current_lr": self.learning_rate,
            "best_lr": self.best_learning_rate,
            "best_win_rate": self.best_win_rate,
            "recent_win_rate": recent_avg,
            "total_games": self.total_games,
            "total_wins": self.total_wins,
            "overall_win_rate": (
                self.total_wins / self.total_games if self.total_games > 0 else 0.0
            ),
            "games_without_improvement": self.games_without_improvement,
            "adjustments": len(self.adjustment_history),
        }

    def get_summary(self) -> str:
        """요약 반환"""
        stats = self.get_stats()

        lines = []
        lines.append("\n[ADAPTIVE_LR] === 적응형 학습률 통계 ===")
        lines.append(f"  현재 학습률: {stats['current_lr']:.6f}")
        lines.append(
            f"  최적 학습률: {stats['best_lr']:.6f} (승률: {stats['best_win_rate']:.1%})"
        )
        lines.append(
            f"  최근 승률: {stats['recent_win_rate']:.1%} (최근 {len(self.recent_win_rates)}게임)"
        )
        lines.append(
            f"  전체 승률: {stats['overall_win_rate']:.1%} ({stats['total_wins']}/{stats['total_games']})"
        )
        lines.append(
            f"  개선 없음: {stats['games_without_improvement']}/{self.patience}게임"
        )
        lines.append(f"  총 조정 횟수: {stats['adjustments']}회")

        # 최근 조정 이력
        if self.adjustment_history:
            lines.append("\n  최근 조정:")
            for adj in self.adjustment_history[-3:]:
                action_emoji = (
                    "[UP]"
                    if adj["action"] == "increase"
                    else "[DN]" if adj["action"] == "decrease" else "[~]"
                )
                lines.append(
                    f"    {action_emoji} Game {adj['game']}: {adj['old_lr']:.6f} -> {adj['new_lr']:.6f}"
                )

        lines.append("=" * 40)
        return "\n".join(lines)

    def _save_stats(self) -> None:
        """통계 저장"""
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "learning_rate": self.learning_rate,
                "best_learning_rate": self.best_learning_rate,
                "best_win_rate": self.best_win_rate,
                "total_games": self.total_games,
                "total_wins": self.total_wins,
                "recent_win_rates": self.recent_win_rates,
                "games_without_improvement": self.games_without_improvement,
                "adjustment_history": self.adjustment_history,
            }

            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.info(f"저장 실패: {e}")

    def _load_stats(self) -> None:
        """통계 로드"""
        try:
            if self.save_path.exists():
                with open(self.save_path, encoding="utf-8") as f:
                    data = json.load(f)

                self.learning_rate = data.get("learning_rate", self.learning_rate)
                self.best_learning_rate = data.get(
                    "best_learning_rate", self.best_learning_rate
                )
                self.best_win_rate = data.get("best_win_rate", self.best_win_rate)
                self.total_games = data.get("total_games", 0)
                self.total_wins = data.get("total_wins", 0)
                self.recent_win_rates = data.get("recent_win_rates", [])
                self.games_without_improvement = data.get(
                    "games_without_improvement", 0
                )
                self.adjustment_history = data.get("adjustment_history", [])

                logger.info(f"통계 로드 완료 - 현재 학습률: {self.learning_rate:.6f}")

        except Exception as e:
            logger.info(f"로드 실패 (새로 시작): {e}")

    def reset(self) -> None:
        """통계 리셋"""
        self.learning_rate = (
            self.best_learning_rate
            if self.best_learning_rate > 0
            else self.learning_rate
        )
        self.games_without_improvement = 0
        logger.info(f"리셋 완료 - 학습률: {self.learning_rate:.6f}")
