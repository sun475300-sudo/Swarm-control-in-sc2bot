# -*- coding: utf-8 -*-
"""Telemetry collection for SC2 game runs."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TelemetryLoggerAtomic")


@dataclass
class FrameSnapshot:
    game_time: float
    frame: int
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    worker_count: int
    army_supply: int
    base_count: int
    enemy_units_visible: int
    army_value: float
    enemy_army_value: float
    frame_time_ms: float
    active_strategy: str = ""
    game_phase: str = ""


@dataclass
class GameTelemetry:
    game_id: str
    start_time: str
    enemy_race: str
    map_name: str
    result: str = ""
    end_time: str = ""
    total_frames: int = 0
    frames: List[FrameSnapshot] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)
    performance: Dict = field(default_factory=dict)


def _amount(collection) -> int:
    if collection is None:
        return 0
    if hasattr(collection, "amount"):
        return int(collection.amount)
    try:
        return len(collection)
    except Exception:
        return 0


class TelemetryCollector:
    """Collect sampled frame telemetry and write one JSON file per game."""

    def __init__(self, output_dir: str = "data/telemetry", sample_interval: int = 22):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_game: Optional[GameTelemetry] = None
        self._sample_interval = max(1, int(sample_interval))

    def start_game(self, game_id: str, enemy_race: str, map_name: str) -> None:
        self.current_game = GameTelemetry(
            game_id=game_id,
            start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            enemy_race=enemy_race,
            map_name=map_name,
        )
        logger.info("[TELEMETRY] Game started: %s vs %s on %s", game_id, enemy_race, map_name)

    def record_frame(self, bot, iteration: int, frame_time_ms: float) -> None:
        if not self.current_game or iteration % self._sample_interval != 0:
            return

        units = list(getattr(bot, "units", []) or [])
        enemy_units = list(getattr(bot, "enemy_units", []) or [])
        snapshot = FrameSnapshot(
            game_time=float(getattr(bot, "time", 0.0) or 0.0),
            frame=int(iteration),
            minerals=int(getattr(bot, "minerals", 0) or 0),
            vespene=int(getattr(bot, "vespene", 0) or 0),
            supply_used=int(getattr(bot, "supply_used", 0) or 0),
            supply_cap=int(getattr(bot, "supply_cap", 0) or 0),
            worker_count=_amount(getattr(bot, "workers", [])),
            army_supply=int(getattr(bot, "supply_army", 0) or 0),
            base_count=_amount(getattr(bot, "townhalls", [])),
            enemy_units_visible=_amount(getattr(bot, "enemy_units", [])),
            army_value=sum(
                float(getattr(unit, "health", 0) or 0) + float(getattr(unit, "shield", 0) or 0)
                for unit in units
                if getattr(unit, "can_attack", False)
            ),
            enemy_army_value=sum(
                float(getattr(unit, "health", 0) or 0) + float(getattr(unit, "shield", 0) or 0)
                for unit in enemy_units
            ),
            frame_time_ms=float(frame_time_ms),
            active_strategy=str(getattr(bot, "active_strategy", "")),
            game_phase=str(getattr(bot, "game_phase", "")),
        )
        self.current_game.frames.append(snapshot)

    def record_event(self, event_type: str, details: Optional[Dict] = None) -> None:
        if not self.current_game:
            return
        self.current_game.events.append(
            {"time": time.time(), "type": event_type, **(details or {})}
        )

    def end_game(self, result: str) -> Optional[Path]:
        if not self.current_game:
            return None

        self.current_game.result = result
        self.current_game.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.current_game.total_frames = len(self.current_game.frames)
        if self.current_game.frames:
            frame_times = [frame.frame_time_ms for frame in self.current_game.frames]
            sorted_times = sorted(frame_times)
            p95_index = min(len(sorted_times) - 1, int(len(sorted_times) * 0.95))
            self.current_game.performance = {
                "avg_frame_ms": sum(frame_times) / len(frame_times),
                "max_frame_ms": max(frame_times),
                "p95_frame_ms": sorted_times[p95_index],
                "frames_over_250ms": sum(1 for value in frame_times if value > 250),
                "frames_over_320ms": sum(1 for value in frame_times if value > 320),
            }

        output_path = self.output_dir / f"{self.current_game.game_id}_{result}.json"
        output_path.write_text(
            json.dumps(asdict(self.current_game), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("[TELEMETRY] Game ended: %s. Saved to %s", result, output_path)
        return output_path


class TelemetryLoggerAtomic:
    """Backwards-compatible lightweight logger facade."""

    def __init__(self, *args, **kwargs):
        self.collector = TelemetryCollector(*args, **kwargs)

    def log(self, event_type: str, **details) -> None:
        self.collector.record_event(event_type, details)


def main() -> None:
    logger.info("Telemetry collector module ready.")


if __name__ == "__main__":
    main()
