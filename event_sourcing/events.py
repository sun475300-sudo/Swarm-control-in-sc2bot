"""
Event sourcing pattern for SC2 game state tracking.
Provides immutable event classes, an EventStore, EventBus,
and a GameStateProjection that reconstructs state from events.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, ClassVar

# ── Base Event ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GameEvent:
    """Immutable base class for all SC2 game events."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    game_id: str = ""
    game_loop: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    EVENT_TYPE: ClassVar[str] = "game_event"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.EVENT_TYPE,
            "event_id": self.event_id,
            "game_id": self.game_id,
            "game_loop": self.game_loop,
            "timestamp": self.timestamp.isoformat(),
        }


# ── Concrete Events ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UnitCreated(GameEvent):
    EVENT_TYPE: ClassVar[str] = "unit_created"
    unit_tag: int = 0
    unit_type: int = 0
    player_id: int = 0
    pos_x: float = 0.0
    pos_y: float = 0.0
    health: float = 0.0
    shield: float = 0.0


@dataclass(frozen=True)
class UnitDestroyed(GameEvent):
    EVENT_TYPE: ClassVar[str] = "unit_destroyed"
    unit_tag: int = 0
    unit_type: int = 0
    player_id: int = 0
    killer_tag: int = 0


@dataclass(frozen=True)
class ResourceChanged(GameEvent):
    EVENT_TYPE: ClassVar[str] = "resource_changed"
    player_id: int = 0
    minerals_delta: int = 0
    vespene_delta: int = 0
    minerals_total: int = 0
    vespene_total: int = 0


@dataclass(frozen=True)
class ActionTaken(GameEvent):
    EVENT_TYPE: ClassVar[str] = "action_taken"
    player_id: int = 0
    action_type: str = "noop"
    unit_tag: int = 0
    target_tag: int = 0
    target_x: float = 0.0
    target_y: float = 0.0
    ability_id: int = 0


@dataclass(frozen=True)
class GameEnded(GameEvent):
    EVENT_TYPE: ClassVar[str] = "game_ended"
    winner_id: int = 0
    result: str = "unknown"
    total_loops: int = 0
    final_score: float = 0.0


# ── Event Store ───────────────────────────────────────────────────────────────


class EventStore:
    """Append-only store for game events, indexed by game_id."""

    def __init__(self) -> None:
        self._store: dict[str, list[GameEvent]] = defaultdict(list)
        self._global_log: list[GameEvent] = []

    def append(self, event: GameEvent) -> None:
        """Append a single immutable event."""
        self._store[event.game_id].append(event)
        self._global_log.append(event)

    def get_events(self, game_id: str) -> list[GameEvent]:
        """Return all events for a specific game, in order."""
        return list(self._store[game_id])

    def get_all(self) -> list[GameEvent]:
        return list(self._global_log)

    def __len__(self) -> int:
        return len(self._global_log)


# ── Event Bus ─────────────────────────────────────────────────────────────────


class EventBus:
    """Publish/subscribe event bus for async event dispatching."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: GameEvent) -> None:
        handlers = self._handlers.get(event.EVENT_TYPE, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)


# ── Projection ────────────────────────────────────────────────────────────────


class GameStateProjection:
    """Rebuilds current game state by replaying events from the store."""

    def __init__(self) -> None:
        self.units: dict[int, dict] = {}
        self.resources: dict[int, dict] = {1: {"minerals": 0, "vespene": 0}}
        self.actions_taken: int = 0
        self.game_result: str | None = None
        self.game_loop: int = 0

    def apply(self, event: GameEvent) -> None:
        self.game_loop = max(self.game_loop, event.game_loop)
        if isinstance(event, UnitCreated):
            self.units[event.unit_tag] = {
                "unit_type": event.unit_type,
                "player_id": event.player_id,
                "health": event.health,
                "shield": event.shield,
                "pos": (event.pos_x, event.pos_y),
            }
        elif isinstance(event, UnitDestroyed):
            self.units.pop(event.unit_tag, None)
        elif isinstance(event, ResourceChanged):
            pid = event.player_id
            if pid not in self.resources:
                self.resources[pid] = {"minerals": 0, "vespene": 0}
            self.resources[pid]["minerals"] = event.minerals_total
            self.resources[pid]["vespene"] = event.vespene_total
        elif isinstance(event, ActionTaken):
            self.actions_taken += 1
        elif isinstance(event, GameEnded):
            self.game_result = event.result

    def rebuild(self, events: list[GameEvent]) -> None:
        """Replay all events to reconstruct current state."""
        self.__init__()
        for event in events:
            self.apply(event)

    def snapshot(self) -> dict:
        return {
            "game_loop": self.game_loop,
            "unit_count": len(self.units),
            "resources": self.resources,
            "actions_taken": self.actions_taken,
            "game_result": self.game_result,
        }
