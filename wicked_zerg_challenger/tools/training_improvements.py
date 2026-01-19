# -*- coding: utf-8 -*-
"""
�Ʒ� ���� ���� ����

�Ʒ� ����, ������, ȿ������ ����Ű�� �پ��� ���� ���� ����
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict
import Any
import Optional
import Tuple
from dataclasses import dataclass
import asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TrainingMetrics:
    """�Ʒ� ��Ʈ��"""
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_game_time: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    total_training_time: float = 0.0
    errors: int = 0
    last_updated: float = 0.0


class AdaptiveDifficultyManager:
    """������ ���̵� ������"""

    def __init__(self):
        self.base_difficulty = "Hard"
        self.current_difficulty = "Hard"
        self.win_rate_threshold_increase = 0.7  # 70% �·� �̻��̸� ���̵� ����
        self.win_rate_threshold_decrease = 0.4  # 40% �·� ���ϸ� ���̵� ����
        self.min_games_for_change = 10  # �ּ� ���� ��

    def update(self, metrics: TrainingMetrics) -> str:
        """���̵� ������Ʈ"""
        if metrics.total_games < self.min_games_for_change:
            return self.current_difficulty

        if metrics.win_rate >= self.win_rate_threshold_increase:
            if self.current_difficulty == "Hard":
                self.current_difficulty = "VeryHard"
                logger.info(
                    f"Difficulty increased to {self.current_difficulty} (win rate: {metrics.win_rate:.1%})")
        elif metrics.win_rate <= self.win_rate_threshold_decrease:
            if self.current_difficulty == "VeryHard":
                self.current_difficulty = "Hard"
                logger.info(
                    f"Difficulty decreased to {self.current_difficulty} (win rate: {metrics.win_rate:.1%})")

        return self.current_difficulty


class TrainingPerformanceMonitor:
    """�Ʒ� ���� �����"""

    def __init__(self):
        self.game_times: list[float] = []
        self.max_game_time_history = 100

    def record_game(self, game_time: float, result: str):
        """���� ���"""
        self.game_times.append(game_time)
        if len(self.game_times) > self.max_game_time_history:
            self.game_times.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """��� ��ȯ"""
        if not self.game_times:
            return {"avg_time": 0.0, "min_time": 0.0, "max_time": 0.0}

        return {
            "avg_time": sum(self.game_times) / len(self.game_times),
            "min_time": min(self.game_times),
            "max_time": max(self.game_times),
            "recent_avg": sum(self.game_times[-10:]) / min(10, len(self.game_times))
        }


class TrainingStateManager:
    """�Ʒ� ���� ������"""

    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            state_file = Path("data/training_state.json")
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> Dict[str, Any]:
        """���� �ε�"""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load training state: {e}")
            return {}

    def save_state(self, state: Dict[str, Any]):
        """���� ����"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save training state: {e}")

    def update_metrics(self, metrics: TrainingMetrics):
        """��Ʈ�� ������Ʈ"""
        state = self.load_state()
        state['metrics'] = asdict(metrics)
        self.save_state(state)


class TrainingErrorHandler:
    """�Ʒ� ���� ó����"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.max_retries = 5
        self.backoff_factor = 2.0

    def handle_error(self, error: Exception,
                     context: str = "") -> Tuple[bool, float]:
        """���� ó��

        Returns:
            (should_continue, wait_time)
        """
        error_type = type(error).__name__
        error_key = f"{error_type}:{context}"

        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        count = self.error_counts[error_key]

        if count > self.max_retries:
            logger.error(
                f"Too many errors ({count}) for {error_key}. Stopping training.")
            return False, 0.0

        wait_time = min(30.0, self.backoff_factor ** count)
        logger.warning(
            f"Error {count}/{self.max_retries}: {error_type} - Waiting {wait_time:.1f}s")

        return True, wait_time

    def reset_error_count(self, context: str = ""):
        """���� ī��Ʈ ����"""
        keys_to_remove = [k for k in self.error_counts.keys() if context in k]
        for key in keys_to_remove:
            del self.error_counts[key]


class TrainingProgressTracker:
    """�Ʒ� ���� ��Ȳ ������"""

    def __init__(self):
        self.start_time = time.time()
        self.checkpoint_interval = 10  # 10���Ӹ��� üũ����Ʈ

    def get_progress_summary(self, metrics: TrainingMetrics) -> str:
        """���� ��Ȳ ���"""
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)

        if metrics.total_games > 0:
            avg_time_per_game = elapsed / metrics.total_games
            games_per_hour = 3600 / avg_time_per_game if avg_time_per_game > 0 else 0
        else:
            games_per_hour = 0

        return f"""
{'='*70}
Training Progress Summary
{'='*70}
Total Games: {metrics.total_games}
Wins: {metrics.wins} | Losses: {metrics.losses}
Win Rate: {metrics.win_rate:.1%}
Current Streak: {'W' if metrics.consecutive_wins > 0 else 'L'}{max(metrics.consecutive_wins, metrics.consecutive_losses)}
Average Game Time: {metrics.avg_game_time:.1f}s
Training Time: {hours}h {minutes}m
Games per Hour: {games_per_hour:.1f}
Errors: {metrics.errors}
{'='*70}
        """.strip()

    def should_save_checkpoint(self, game_count: int) -> bool:
        """üũ����Ʈ ���� ����"""
        return game_count % self.checkpoint_interval == 0


def improve_training_config() -> Dict[str, Any]:
    """�Ʒ� ���� ����"""
    return {
        "adaptive_difficulty": True,
        "performance_monitoring": True,
        "error_recovery": True,
        "progress_tracking": True,
        "auto_save_interval": 10,  # 10���Ӹ��� �ڵ� ����
        "max_consecutive_failures": 5,
        "wait_between_games": 10,  # ���� �� ��� �ð� (��)
        "min_games_for_difficulty_change": 10,
    }


if __name__ == "__main__":
    print("Training Improvements Module")
    print("This module provides utilities for improving training logic.")
    print()
    print("Available components:")
    print("  - AdaptiveDifficultyManager: Auto-adjusts difficulty based on performance")
    print("  - TrainingPerformanceMonitor: Tracks game performance metrics")
    print("  - TrainingStateManager: Saves/loads training state")
    print("  - TrainingErrorHandler: Handles errors with exponential backoff")
    print("  - TrainingProgressTracker: Tracks and displays training progress")
