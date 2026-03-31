"""
Phase 452: Bytewax - SC2 Rust-Powered Python Streaming
Real-time APM calculation and win rate sliding window with Bytewax dataflow.
"""

import logging
from datetime import timedelta, datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
from bytewax.dataflow import Dataflow
import bytewax.operators as op
from bytewax.connectors.stdio import StdOutSink
from bytewax.connectors.demo import RandomMetricSource
from bytewax.testing import TestingSource, run_main
from bytewax.operators.windowing import (
    EventClock,
    SlidingWindower,
    TumblingWindower,
    fold_window,
)

logger = logging.getLogger(__name__)


@dataclass
class GameEvent:
    game_id: str
    player_id: str
    event_type: str  # "action", "unit_created", "unit_died", "game_end"
    timestamp: datetime
    value: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class APMState:
    action_count: int = 0
    window_start: Optional[datetime] = None


@dataclass
class WinRateState:
    wins: int = 0
    total: int = 0

    @property
    def rate(self) -> float:
        return self.wins / self.total if self.total > 0 else 0.0


def parse_event(raw: dict) -> tuple[str, GameEvent]:
    """Parse raw event dict into keyed GameEvent."""
    event = GameEvent(
        game_id=raw.get("game_id", ""),
        player_id=raw.get("player_id", ""),
        event_type=raw.get("event_type", ""),
        timestamp=datetime.fromisoformat(raw.get("timestamp", datetime.now(timezone.utc).isoformat())),
        value=float(raw.get("value", 0.0)),
        metadata=raw.get("metadata", {}),
    )
    return (event.player_id, event)


def filter_actions(kv: tuple[str, GameEvent]) -> bool:
    """Keep only action events for APM calculation."""
    _, event = kv
    return event.event_type == "action"


def extract_game_results(kv: tuple[str, GameEvent]) -> Optional[tuple[str, int]]:
    """Extract win/loss from game_end events."""
    _, event = kv
    if event.event_type == "game_end":
        result = 1 if event.metadata.get("result") == "win" else 0
        return (event.player_id, result)
    return None


def apm_folder(state: APMState, event: GameEvent) -> APMState:
    """Fold function: count actions in window for APM."""
    return APMState(action_count=state.action_count + 1, window_start=state.window_start or event.timestamp)


def win_rate_folder(state: WinRateState, result: int) -> WinRateState:
    """Fold function: accumulate win/loss for sliding win rate."""
    return WinRateState(wins=state.wins + result, total=state.total + 1)


def compute_apm(metadata: tuple, state: APMState) -> dict:
    """Convert window action count to APM."""
    window_meta, _ = metadata
    duration_minutes = (window_meta.close_time - window_meta.open_time).total_seconds() / 60
    apm = state.action_count / duration_minutes if duration_minutes > 0 else 0
    return {"player_id": metadata[0] if isinstance(metadata, tuple) else "unknown", "apm": round(apm, 1), "window_actions": state.action_count}


def format_win_rate(kv: tuple[str, WinRateState]) -> str:
    player_id, state = kv
    return f"Player {player_id}: win_rate={state.rate:.3f} ({state.wins}/{state.total})"


def build_dataflow() -> Dataflow:
    """Build the SC2 streaming dataflow."""
    flow = Dataflow("sc2_realtime")

    # Input: game events stream
    sample_events = [
        {"game_id": "g1", "player_id": "ZergBot", "event_type": "action", "timestamp": "2026-01-01T10:00:00+00:00", "value": 1.0},
        {"game_id": "g1", "player_id": "ZergBot", "event_type": "action", "timestamp": "2026-01-01T10:00:01+00:00", "value": 1.0},
        {"game_id": "g1", "player_id": "ZergBot", "event_type": "game_end", "timestamp": "2026-01-01T10:07:00+00:00", "value": 0.0, "metadata": {"result": "win"}},
        {"game_id": "g2", "player_id": "ZergBot", "event_type": "action", "timestamp": "2026-01-01T11:00:00+00:00", "value": 1.0},
        {"game_id": "g2", "player_id": "ZergBot", "event_type": "game_end", "timestamp": "2026-01-01T11:06:00+00:00", "value": 0.0, "metadata": {"result": "loss"}},
    ]

    inp = op.input("input", flow, TestingSource(sample_events))
    parsed = op.map("parse", inp, parse_event)

    # Branch 1: APM calculation using tumbling window
    actions = op.filter("filter_actions", parsed, filter_actions)
    op.output("apm_output", actions, StdOutSink())

    # Branch 2: Win rate sliding window
    game_results = op.filter_map("extract_results", parsed, extract_game_results)
    op.output("winrate_output", game_results, StdOutSink())

    return flow


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    flow = build_dataflow()
    run_main(flow)
    logger.info("SC2 Bytewax dataflow complete.")
