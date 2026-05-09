# -*- coding: utf-8 -*-
"""Convert replay feedback summaries into compact RL training data."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ReplayToTrainingPipeline:
    """Build training episodes from replay analysis JSON summaries."""

    def __init__(self, replay_dir: str, output_dir: str):
        self.replay_dir = Path(replay_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_replay_summaries(self) -> List[Dict]:
        summaries = sorted(self.replay_dir.glob("*.json"))
        training_data: List[Dict] = []

        for summary_path in summaries:
            try:
                with open(summary_path, encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping replay summary %s: %s", summary_path, exc)
                continue

            training_data.append(
                {
                    "enemy_race": data.get("enemy_race", "Unknown"),
                    "result": data.get("result", "Unknown"),
                    "game_length": float(data.get("game_length_seconds", 0.0) or 0.0),
                    "reward": self._compute_reward(data),
                    "loss_tags": list(data.get("loss_tags", [])),
                    "focus_areas": list(data.get("focus_areas", [])),
                }
            )

        output_path = self.output_dir / "training_data.json"
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(training_data, handle, indent=2, ensure_ascii=False)
        return training_data

    def _compute_reward(self, summary: Dict) -> float:
        result = str(summary.get("result", "")).lower()
        reward = 10.0 if result in {"victory", "win", "won"} else -10.0
        reward += 0.05 * float(summary.get("enemy_units_killed", 0) or 0)
        reward += 0.01 * (float(summary.get("resources_collected", 0) or 0) / 100.0)
        reward -= 0.5 * float(summary.get("supply_blocks", 0) or 0)
        reward -= 1.0 * len(summary.get("loss_tags", []) or [])
        return reward
