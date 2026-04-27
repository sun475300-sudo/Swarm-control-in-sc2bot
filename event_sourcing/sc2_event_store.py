"""
Phase 663: Event Sourcing for SC2 Game History
================================================
Event sourcing pattern for SC2 game state reconstruction.

Implements a full event sourcing system:
- Immutable event log for complete game history
- Aggregate state reconstruction from event streams
- Materialized view projections (army value, resource curves)
- Periodic snapshots for fast replay/rebuild
- Event bus for decoupled subscribers
- Time-travel debugging: reconstruct state at any game tick

SC2 event types:
- UnitCreated, UnitDestroyed, ResourceGathered
- BuildingStarted, BuildingCompleted, AttackOrdered
- UpgradeStarted, UpgradeCompleted, GameStarted, GameEnded
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event Types
# ---------------------------------------------------------------------------


class EventType(Enum):
    """SC2 game event types."""

    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    UNIT_CREATED = "unit_created"
    UNIT_DESTROYED = "unit_destroyed"
    RESOURCE_GATHERED = "resource_gathered"
    BUILDING_STARTED = "building_started"
    BUILDING_COMPLETED = "building_completed"
    ATTACK_ORDERED = "attack_ordered"
    UPGRADE_STARTED = "upgrade_started"
    UPGRADE_COMPLETED = "upgrade_completed"
    ABILITY_USED = "ability_used"
    EXPANSION_TAKEN = "expansion_taken"
    SUPPLY_BLOCKED = "supply_blocked"
    SCOUT_SENT = "scout_sent"
    RETREAT_ORDERED = "retreat_ordered"


# ---------------------------------------------------------------------------
# Event Data Class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """
    Immutable event representing a state change.

    All game state is derived from the sequence of events.
    Events are never modified or deleted.
    """

    event_id: str
    event_type: EventType
    aggregate_id: str
    game_tick: int
    timestamp: float
    data: Dict[str, Any]
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        event_type: EventType,
        aggregate_id: str,
        game_tick: int,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        return Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            game_tick=game_tick,
            timestamp=time.time(),
            data=data,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "game_tick": self.game_tick,
            "timestamp": self.timestamp,
            "data": self.data,
            "version": self.version,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> Event:
        return Event(
            event_id=d["event_id"],
            event_type=EventType(d["event_type"]),
            aggregate_id=d["aggregate_id"],
            game_tick=d["game_tick"],
            timestamp=d["timestamp"],
            data=d["data"],
            version=d.get("version", 1),
            metadata=d.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass
class Snapshot:
    """Periodic state snapshot for fast aggregate reconstruction."""

    snapshot_id: str
    aggregate_id: str
    state: Dict[str, Any]
    version: int
    game_tick: int
    timestamp: float

    @staticmethod
    def create(
        aggregate_id: str, state: Dict[str, Any], version: int, game_tick: int
    ) -> Snapshot:
        return Snapshot(
            snapshot_id=str(uuid.uuid4()),
            aggregate_id=aggregate_id,
            state=copy.deepcopy(state),
            version=version,
            game_tick=game_tick,
            timestamp=time.time(),
        )


# ---------------------------------------------------------------------------
# Event Store
# ---------------------------------------------------------------------------


class EventStore:
    """
    Append-only event store.

    Stores all events for all aggregates. Supports event replay,
    snapshot storage, and stream queries.
    """

    def __init__(self, snapshot_interval: int = 100):
        self._events: List[Event] = []
        self._streams: Dict[str, List[int]] = defaultdict(
            list
        )  # aggregate_id -> event indices
        self._snapshots: Dict[str, List[Snapshot]] = defaultdict(list)
        self._snapshot_interval = snapshot_interval
        self._version_counter: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def append(self, event: Event) -> int:
        """Append an event to the store. Returns the global sequence number."""
        with self._lock:
            seq = len(self._events)
            self._events.append(event)
            self._streams[event.aggregate_id].append(seq)
            self._version_counter[event.aggregate_id] += 1
            return seq

    def append_many(self, events: List[Event]) -> List[int]:
        """Append multiple events atomically."""
        sequences = []
        with self._lock:
            for event in events:
                seq = len(self._events)
                self._events.append(event)
                self._streams[event.aggregate_id].append(seq)
                self._version_counter[event.aggregate_id] += 1
                sequences.append(seq)
        return sequences

    def get_events(
        self,
        aggregate_id: str,
        after_version: int = 0,
    ) -> List[Event]:
        """Get all events for an aggregate after a given version."""
        with self._lock:
            indices = self._streams.get(aggregate_id, [])
            return [self._events[i] for i in indices[after_version:]]

    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        """Get all events of a specific type across all aggregates."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def get_events_in_range(
        self,
        aggregate_id: str,
        start_tick: int,
        end_tick: int,
    ) -> List[Event]:
        """Get events for an aggregate within a game tick range."""
        with self._lock:
            indices = self._streams.get(aggregate_id, [])
            return [
                self._events[i]
                for i in indices
                if start_tick <= self._events[i].game_tick <= end_tick
            ]

    def get_all_events(self) -> List[Event]:
        with self._lock:
            return list(self._events)

    def save_snapshot(self, snapshot: Snapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.aggregate_id].append(snapshot)

    def get_latest_snapshot(self, aggregate_id: str) -> Optional[Snapshot]:
        with self._lock:
            snaps = self._snapshots.get(aggregate_id, [])
            return snaps[-1] if snaps else None

    def should_snapshot(self, aggregate_id: str) -> bool:
        with self._lock:
            version = self._version_counter.get(aggregate_id, 0)
            snaps = self._snapshots.get(aggregate_id, [])
            last_snap_version = snaps[-1].version if snaps else 0
            return (version - last_snap_version) >= self._snapshot_interval

    def get_version(self, aggregate_id: str) -> int:
        with self._lock:
            return self._version_counter.get(aggregate_id, 0)

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def stream_ids(self) -> List[str]:
        with self._lock:
            return list(self._streams.keys())

    def export_json(self) -> str:
        with self._lock:
            return json.dumps([e.to_dict() for e in self._events], indent=2)

    def import_json(self, data: str) -> int:
        parsed = json.loads(data)
        events = [Event.from_dict(d) for d in parsed]
        return len(self.append_many(events))


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


class Aggregate:
    """
    Aggregate root that reconstructs state from events.

    Maintains the current game state for a single game session
    by applying events in order.
    """

    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        self.version = 0
        self.state: Dict[str, Any] = {
            "game_tick": 0,
            "minerals": 50,
            "vespene": 0,
            "supply_used": 0,
            "supply_cap": 15,
            "units": {},
            "buildings": {},
            "upgrades": [],
            "army_value": 0,
            "total_units_created": 0,
            "total_units_lost": 0,
            "total_resources_gathered": 0,
            "attacks_ordered": 0,
            "game_started": False,
            "game_ended": False,
            "winner": None,
        }
        self._event_handlers: Dict[EventType, Callable] = {
            EventType.GAME_STARTED: self._on_game_started,
            EventType.GAME_ENDED: self._on_game_ended,
            EventType.UNIT_CREATED: self._on_unit_created,
            EventType.UNIT_DESTROYED: self._on_unit_destroyed,
            EventType.RESOURCE_GATHERED: self._on_resource_gathered,
            EventType.BUILDING_STARTED: self._on_building_started,
            EventType.BUILDING_COMPLETED: self._on_building_completed,
            EventType.ATTACK_ORDERED: self._on_attack_ordered,
            EventType.UPGRADE_STARTED: self._on_upgrade_started,
            EventType.UPGRADE_COMPLETED: self._on_upgrade_completed,
            EventType.ABILITY_USED: self._on_ability_used,
            EventType.EXPANSION_TAKEN: self._on_expansion_taken,
            EventType.SUPPLY_BLOCKED: self._on_supply_blocked,
        }

    def apply(self, event: Event) -> None:
        """Apply a single event to update state."""
        handler = self._event_handlers.get(event.event_type)
        if handler:
            handler(event)
        self.state["game_tick"] = max(self.state["game_tick"], event.game_tick)
        self.version += 1

    def apply_many(self, events: List[Event]) -> None:
        for event in events:
            self.apply(event)

    def load_from_snapshot(self, snapshot: Snapshot) -> None:
        self.state = copy.deepcopy(snapshot.state)
        self.version = snapshot.version

    def take_snapshot(self) -> Snapshot:
        return Snapshot.create(
            self.aggregate_id,
            self.state,
            self.version,
            self.state["game_tick"],
        )

    # --- Event Handlers ---

    def _on_game_started(self, event: Event) -> None:
        self.state["game_started"] = True
        self.state["race"] = event.data.get("race", "unknown")
        self.state["opponent_race"] = event.data.get("opponent_race", "unknown")
        self.state["map_name"] = event.data.get("map_name", "unknown")

    def _on_game_ended(self, event: Event) -> None:
        self.state["game_ended"] = True
        self.state["winner"] = event.data.get("winner")
        self.state["result"] = event.data.get("result", "unknown")

    def _on_unit_created(self, event: Event) -> None:
        unit_id = event.data.get("unit_id", str(uuid.uuid4()))
        unit_type = event.data.get("unit_type", "unknown")
        cost_minerals = event.data.get("cost_minerals", 0)
        cost_vespene = event.data.get("cost_vespene", 0)
        supply = event.data.get("supply", 1)
        self.state["units"][unit_id] = {
            "type": unit_type,
            "created_tick": event.game_tick,
            "alive": True,
            "cost_minerals": cost_minerals,
            "cost_vespene": cost_vespene,
            "supply": supply,
        }
        self.state["minerals"] -= cost_minerals
        self.state["vespene"] -= cost_vespene
        self.state["supply_used"] += supply
        self.state["army_value"] += cost_minerals + cost_vespene
        self.state["total_units_created"] += 1

    def _on_unit_destroyed(self, event: Event) -> None:
        unit_id = event.data.get("unit_id")
        if unit_id and unit_id in self.state["units"]:
            unit = self.state["units"][unit_id]
            unit["alive"] = False
            unit["destroyed_tick"] = event.game_tick
            self.state["supply_used"] -= unit.get("supply", 0)
            self.state["army_value"] -= unit["cost_minerals"] + unit["cost_vespene"]
            self.state["total_units_lost"] += 1

    def _on_resource_gathered(self, event: Event) -> None:
        minerals = event.data.get("minerals", 0)
        vespene = event.data.get("vespene", 0)
        self.state["minerals"] += minerals
        self.state["vespene"] += vespene
        self.state["total_resources_gathered"] += minerals + vespene

    def _on_building_started(self, event: Event) -> None:
        building_id = event.data.get("building_id", str(uuid.uuid4()))
        building_type = event.data.get("building_type", "unknown")
        cost_minerals = event.data.get("cost_minerals", 0)
        cost_vespene = event.data.get("cost_vespene", 0)
        self.state["buildings"][building_id] = {
            "type": building_type,
            "started_tick": event.game_tick,
            "completed": False,
            "cost_minerals": cost_minerals,
            "cost_vespene": cost_vespene,
        }
        self.state["minerals"] -= cost_minerals
        self.state["vespene"] -= cost_vespene

    def _on_building_completed(self, event: Event) -> None:
        building_id = event.data.get("building_id")
        if building_id and building_id in self.state["buildings"]:
            self.state["buildings"][building_id]["completed"] = True
            self.state["buildings"][building_id]["completed_tick"] = event.game_tick
            supply_add = event.data.get("supply_provided", 0)
            self.state["supply_cap"] += supply_add

    def _on_attack_ordered(self, event: Event) -> None:
        self.state["attacks_ordered"] += 1

    def _on_upgrade_started(self, event: Event) -> None:
        pass  # Tracked in upgrade_completed

    def _on_upgrade_completed(self, event: Event) -> None:
        upgrade_name = event.data.get("upgrade_name", "unknown")
        if upgrade_name not in self.state["upgrades"]:
            self.state["upgrades"].append(upgrade_name)

    def _on_ability_used(self, event: Event) -> None:
        pass  # Can be extended for ability tracking

    def _on_expansion_taken(self, event: Event) -> None:
        self.state.setdefault("expansions", 0)
        self.state["expansions"] += 1

    def _on_supply_blocked(self, event: Event) -> None:
        self.state.setdefault("supply_blocks", 0)
        self.state["supply_blocks"] += 1

    def get_alive_units(self) -> Dict[str, Dict[str, Any]]:
        return {uid: u for uid, u in self.state["units"].items() if u.get("alive")}

    def get_completed_buildings(self) -> Dict[str, Dict[str, Any]]:
        return {
            bid: b for bid, b in self.state["buildings"].items() if b.get("completed")
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "version": self.version,
            "game_tick": self.state["game_tick"],
            "minerals": self.state["minerals"],
            "vespene": self.state["vespene"],
            "supply": f"{self.state['supply_used']}/{self.state['supply_cap']}",
            "alive_units": len(self.get_alive_units()),
            "buildings": len(self.get_completed_buildings()),
            "army_value": self.state["army_value"],
            "upgrades": self.state["upgrades"],
        }


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


class Projection:
    """
    Materialized view built from the event stream.

    Projections are read-optimized views derived from events.
    They can be rebuilt from scratch at any time.
    """

    def __init__(self, name: str):
        self.name = name
        self._data: Dict[str, Any] = {}
        self._handlers: Dict[EventType, Callable] = {}
        self._processed_count = 0

    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        self._handlers[event_type] = handler

    def process(self, event: Event) -> None:
        handler = self._handlers.get(event.event_type)
        if handler:
            handler(event, self._data)
            self._processed_count += 1

    def process_many(self, events: List[Event]) -> None:
        for event in events:
            self.process(event)

    def get_data(self) -> Dict[str, Any]:
        return copy.deepcopy(self._data)

    def reset(self) -> None:
        self._data = {}
        self._processed_count = 0


class ArmyValueProjection(Projection):
    """Tracks army value over time."""

    def __init__(self):
        super().__init__("army_value_over_time")
        self._data = {"timeline": [], "current_value": 0}
        self.register_handler(EventType.UNIT_CREATED, self._on_unit_created)
        self.register_handler(EventType.UNIT_DESTROYED, self._on_unit_destroyed)

    def _on_unit_created(self, event: Event, data: Dict[str, Any]) -> None:
        cost = event.data.get("cost_minerals", 0) + event.data.get("cost_vespene", 0)
        data["current_value"] += cost
        data["timeline"].append(
            {
                "tick": event.game_tick,
                "value": data["current_value"],
                "event": "created",
                "unit_type": event.data.get("unit_type"),
            }
        )

    def _on_unit_destroyed(self, event: Event, data: Dict[str, Any]) -> None:
        cost = event.data.get("cost_minerals", 0) + event.data.get("cost_vespene", 0)
        data["current_value"] = max(0, data["current_value"] - cost)
        data["timeline"].append(
            {
                "tick": event.game_tick,
                "value": data["current_value"],
                "event": "destroyed",
                "unit_type": event.data.get("unit_type"),
            }
        )

    def peak_value(self) -> int:
        if not self._data["timeline"]:
            return 0
        return max(entry["value"] for entry in self._data["timeline"])


class ResourceCurveProjection(Projection):
    """Tracks resource income and spending over time."""

    def __init__(self):
        super().__init__("resource_curve")
        self._data = {
            "income": [],
            "spending": [],
            "total_mined_minerals": 0,
            "total_mined_vespene": 0,
            "total_spent_minerals": 0,
            "total_spent_vespene": 0,
        }
        self.register_handler(EventType.RESOURCE_GATHERED, self._on_gathered)
        self.register_handler(EventType.UNIT_CREATED, self._on_spent)
        self.register_handler(EventType.BUILDING_STARTED, self._on_building_spent)

    def _on_gathered(self, event: Event, data: Dict[str, Any]) -> None:
        minerals = event.data.get("minerals", 0)
        vespene = event.data.get("vespene", 0)
        data["total_mined_minerals"] += minerals
        data["total_mined_vespene"] += vespene
        data["income"].append(
            {
                "tick": event.game_tick,
                "minerals": minerals,
                "vespene": vespene,
            }
        )

    def _on_spent(self, event: Event, data: Dict[str, Any]) -> None:
        minerals = event.data.get("cost_minerals", 0)
        vespene = event.data.get("cost_vespene", 0)
        data["total_spent_minerals"] += minerals
        data["total_spent_vespene"] += vespene
        data["spending"].append(
            {
                "tick": event.game_tick,
                "minerals": minerals,
                "vespene": vespene,
                "item": event.data.get("unit_type", "unknown"),
            }
        )

    def _on_building_spent(self, event: Event, data: Dict[str, Any]) -> None:
        minerals = event.data.get("cost_minerals", 0)
        vespene = event.data.get("cost_vespene", 0)
        data["total_spent_minerals"] += minerals
        data["total_spent_vespene"] += vespene
        data["spending"].append(
            {
                "tick": event.game_tick,
                "minerals": minerals,
                "vespene": vespene,
                "item": event.data.get("building_type", "unknown"),
            }
        )

    def net_resources(self) -> Dict[str, int]:
        return {
            "minerals": self._data["total_mined_minerals"]
            - self._data["total_spent_minerals"],
            "vespene": self._data["total_mined_vespene"]
            - self._data["total_spent_vespene"],
        }


class UnitCompositionProjection(Projection):
    """Tracks current unit composition."""

    def __init__(self):
        super().__init__("unit_composition")
        self._data = {"alive": defaultdict(int), "total_created": defaultdict(int)}
        self.register_handler(EventType.UNIT_CREATED, self._on_created)
        self.register_handler(EventType.UNIT_DESTROYED, self._on_destroyed)

    def _on_created(self, event: Event, data: Dict[str, Any]) -> None:
        unit_type = event.data.get("unit_type", "unknown")
        data["alive"][unit_type] += 1
        data["total_created"][unit_type] += 1

    def _on_destroyed(self, event: Event, data: Dict[str, Any]) -> None:
        unit_type = event.data.get("unit_type", "unknown")
        data["alive"][unit_type] = max(0, data["alive"].get(unit_type, 0) - 1)


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


class EventBus:
    """
    Pub/sub event bus for decoupled event processing.

    Subscribers receive events asynchronously after they are stored.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._global_subscribers: List[Callable] = []
        self._lock = threading.Lock()
        self._event_count = 0

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        with self._lock:
            self._subscribers[event_type.value].append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        with self._lock:
            self._global_subscribers.append(handler)

    def publish(self, event: Event) -> int:
        """Publish an event to all matching subscribers. Returns handler count."""
        handlers_called = 0
        with self._lock:
            type_handlers = list(self._subscribers.get(event.event_type.value, []))
            global_handlers = list(self._global_subscribers)
        for handler in type_handlers:
            try:
                handler(event)
                handlers_called += 1
            except Exception as e:
                logger.warning("Event handler error: %s", e)
        for handler in global_handlers:
            try:
                handler(event)
                handlers_called += 1
            except Exception as e:
                logger.warning("Global event handler error: %s", e)
        self._event_count += 1
        return handlers_called

    def publish_many(self, events: List[Event]) -> int:
        total = 0
        for event in events:
            total += self.publish(event)
        return total

    @property
    def total_published(self) -> int:
        return self._event_count


# ---------------------------------------------------------------------------
# SC2EventSource - Main Facade
# ---------------------------------------------------------------------------


class SC2EventSource:
    """
    Complete event sourcing system for SC2 game history.

    Provides a unified interface for recording game events,
    reconstructing state, building projections, and time-travel debugging.
    """

    def __init__(self, snapshot_interval: int = 50):
        self.store = EventStore(snapshot_interval=snapshot_interval)
        self.bus = EventBus()
        self._aggregates: Dict[str, Aggregate] = {}
        self._projections: List[Projection] = []
        self._lock = threading.Lock()

    def register_projection(self, projection: Projection) -> None:
        self._projections.append(projection)

    def _get_or_create_aggregate(self, game_id: str) -> Aggregate:
        if game_id not in self._aggregates:
            self._aggregates[game_id] = Aggregate(game_id)
        return self._aggregates[game_id]

    def record_event(self, event: Event) -> int:
        """Record an event: store, apply to aggregate, update projections, publish."""
        seq = self.store.append(event)
        agg = self._get_or_create_aggregate(event.aggregate_id)
        agg.apply(event)
        for proj in self._projections:
            proj.process(event)
        self.bus.publish(event)
        # Auto-snapshot
        if self.store.should_snapshot(event.aggregate_id):
            snapshot = agg.take_snapshot()
            self.store.save_snapshot(snapshot)
            logger.debug(
                "Snapshot taken for %s at version %d", event.aggregate_id, agg.version
            )
        return seq

    def record_events(self, events: List[Event]) -> List[int]:
        return [self.record_event(e) for e in events]

    # --- SC2 convenience methods ---

    def game_started(
        self,
        game_id: str,
        race: str,
        opponent_race: str,
        map_name: str,
    ) -> Event:
        event = Event.create(
            EventType.GAME_STARTED,
            game_id,
            game_tick=0,
            data={"race": race, "opponent_race": opponent_race, "map_name": map_name},
        )
        self.record_event(event)
        return event

    def unit_created(
        self,
        game_id: str,
        tick: int,
        unit_id: str,
        unit_type: str,
        cost_minerals: int = 0,
        cost_vespene: int = 0,
        supply: int = 1,
    ) -> Event:
        event = Event.create(
            EventType.UNIT_CREATED,
            game_id,
            game_tick=tick,
            data={
                "unit_id": unit_id,
                "unit_type": unit_type,
                "cost_minerals": cost_minerals,
                "cost_vespene": cost_vespene,
                "supply": supply,
            },
        )
        self.record_event(event)
        return event

    def unit_destroyed(
        self,
        game_id: str,
        tick: int,
        unit_id: str,
        unit_type: str,
        cost_minerals: int = 0,
        cost_vespene: int = 0,
    ) -> Event:
        event = Event.create(
            EventType.UNIT_DESTROYED,
            game_id,
            game_tick=tick,
            data={
                "unit_id": unit_id,
                "unit_type": unit_type,
                "cost_minerals": cost_minerals,
                "cost_vespene": cost_vespene,
            },
        )
        self.record_event(event)
        return event

    def resource_gathered(
        self,
        game_id: str,
        tick: int,
        minerals: int = 0,
        vespene: int = 0,
    ) -> Event:
        event = Event.create(
            EventType.RESOURCE_GATHERED,
            game_id,
            game_tick=tick,
            data={"minerals": minerals, "vespene": vespene},
        )
        self.record_event(event)
        return event

    def building_started(
        self,
        game_id: str,
        tick: int,
        building_id: str,
        building_type: str,
        cost_minerals: int = 0,
        cost_vespene: int = 0,
    ) -> Event:
        event = Event.create(
            EventType.BUILDING_STARTED,
            game_id,
            game_tick=tick,
            data={
                "building_id": building_id,
                "building_type": building_type,
                "cost_minerals": cost_minerals,
                "cost_vespene": cost_vespene,
            },
        )
        self.record_event(event)
        return event

    def building_completed(
        self,
        game_id: str,
        tick: int,
        building_id: str,
        supply_provided: int = 0,
    ) -> Event:
        event = Event.create(
            EventType.BUILDING_COMPLETED,
            game_id,
            game_tick=tick,
            data={"building_id": building_id, "supply_provided": supply_provided},
        )
        self.record_event(event)
        return event

    def attack_ordered(
        self, game_id: str, tick: int, target: str, unit_count: int
    ) -> Event:
        event = Event.create(
            EventType.ATTACK_ORDERED,
            game_id,
            game_tick=tick,
            data={"target": target, "unit_count": unit_count},
        )
        self.record_event(event)
        return event

    def upgrade_completed(self, game_id: str, tick: int, upgrade_name: str) -> Event:
        event = Event.create(
            EventType.UPGRADE_COMPLETED,
            game_id,
            game_tick=tick,
            data={"upgrade_name": upgrade_name},
        )
        self.record_event(event)
        return event

    def game_ended(self, game_id: str, tick: int, winner: str, result: str) -> Event:
        event = Event.create(
            EventType.GAME_ENDED,
            game_id,
            game_tick=tick,
            data={"winner": winner, "result": result},
        )
        self.record_event(event)
        return event

    # --- State Reconstruction ---

    def get_state(self, game_id: str) -> Dict[str, Any]:
        agg = self._aggregates.get(game_id)
        if agg is None:
            return {}
        return agg.summary()

    def get_full_state(self, game_id: str) -> Dict[str, Any]:
        agg = self._aggregates.get(game_id)
        if agg is None:
            return {}
        return copy.deepcopy(agg.state)

    def rebuild_state_at_tick(self, game_id: str, target_tick: int) -> Dict[str, Any]:
        """
        Time-travel: reconstruct state at a specific game tick.

        Uses the latest snapshot before target_tick, then replays
        remaining events.
        """
        agg = Aggregate(game_id)

        # Try to load from snapshot
        snapshot = self.store.get_latest_snapshot(game_id)
        start_version = 0
        if snapshot and snapshot.game_tick <= target_tick:
            agg.load_from_snapshot(snapshot)
            start_version = snapshot.version

        # Replay events after snapshot up to target tick
        events = self.store.get_events(game_id, after_version=start_version)
        for event in events:
            if event.game_tick > target_tick:
                break
            agg.apply(event)

        return agg.summary()

    def get_event_log(self, game_id: str) -> List[Dict[str, Any]]:
        events = self.store.get_events(game_id)
        return [e.to_dict() for e in events]

    def get_projection_data(self, projection_name: str) -> Dict[str, Any]:
        for proj in self._projections:
            if proj.name == projection_name:
                return proj.get_data()
        return {}

    def stats(self) -> Dict[str, Any]:
        return {
            "total_events": self.store.count(),
            "streams": self.store.stream_ids(),
            "projections": [p.name for p in self._projections],
            "bus_published": self.bus.total_published,
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate event sourcing for SC2 game history."""
    print("=" * 70)
    print("Phase 663: Event Sourcing for SC2 Game History - Demo")
    print("=" * 70)

    # Create the event source system
    sc2es = SC2EventSource(snapshot_interval=10)

    # Register projections
    army_proj = ArmyValueProjection()
    resource_proj = ResourceCurveProjection()
    composition_proj = UnitCompositionProjection()
    sc2es.register_projection(army_proj)
    sc2es.register_projection(resource_proj)
    sc2es.register_projection(composition_proj)

    # Subscribe to events via bus
    attack_log: List[str] = []
    sc2es.bus.subscribe(
        EventType.ATTACK_ORDERED,
        lambda e: attack_log.append(f"Attack at tick {e.game_tick}"),
    )

    game_id = "game_001"

    # --- Simulate a game ---
    print("\n[1] Recording Game Events")
    sc2es.game_started(
        game_id, race="Zerg", opponent_race="Terran", map_name="Oxide LE"
    )

    # Early game: gather resources, build
    for tick in range(1, 6):
        sc2es.resource_gathered(game_id, tick=tick * 10, minerals=75, vespene=0)

    sc2es.building_started(
        game_id,
        tick=50,
        building_id="pool_1",
        building_type="SpawningPool",
        cost_minerals=200,
    )
    sc2es.building_completed(game_id, tick=115, building_id="pool_1")

    sc2es.building_started(
        game_id,
        tick=60,
        building_id="hatch_2",
        building_type="Hatchery",
        cost_minerals=300,
    )
    sc2es.building_completed(
        game_id, tick=160, building_id="hatch_2", supply_provided=6
    )

    # Mid game: create units
    zerglings = []
    for i in range(8):
        uid = f"ling_{i}"
        zerglings.append(uid)
        sc2es.unit_created(
            game_id,
            tick=120 + i * 5,
            unit_id=uid,
            unit_type="Zergling",
            cost_minerals=25,
            supply=1,
        )

    for tick in range(6, 16):
        sc2es.resource_gathered(game_id, tick=tick * 10, minerals=100, vespene=25)

    # Roaches
    for i in range(4):
        uid = f"roach_{i}"
        sc2es.unit_created(
            game_id,
            tick=200 + i * 8,
            unit_id=uid,
            unit_type="Roach",
            cost_minerals=75,
            cost_vespene=25,
            supply=2,
        )

    # Attack
    sc2es.attack_ordered(game_id, tick=250, target="enemy_natural", unit_count=12)

    # Losses
    sc2es.unit_destroyed(
        game_id, tick=260, unit_id="ling_0", unit_type="Zergling", cost_minerals=25
    )
    sc2es.unit_destroyed(
        game_id, tick=262, unit_id="ling_1", unit_type="Zergling", cost_minerals=25
    )
    sc2es.unit_destroyed(
        game_id,
        tick=265,
        unit_id="roach_0",
        unit_type="Roach",
        cost_minerals=75,
        cost_vespene=25,
    )

    # Upgrade
    sc2es.upgrade_completed(game_id, tick=300, upgrade_name="MetabolicBoost")

    # More resources
    for tick in range(16, 26):
        sc2es.resource_gathered(game_id, tick=tick * 10, minerals=120, vespene=40)

    # Second attack
    sc2es.attack_ordered(game_id, tick=350, target="enemy_main", unit_count=9)

    # Game ends
    sc2es.game_ended(game_id, tick=400, winner="Zerg", result="victory")

    print(f"  Total events recorded: {sc2es.store.count()}")
    print(f"  Event streams: {sc2es.store.stream_ids()}")

    # --- Current State ---
    print("\n[2] Current Game State (Aggregate)")
    state = sc2es.get_state(game_id)
    for key, val in state.items():
        print(f"  {key}: {val}")

    # --- Projections ---
    print("\n[3] Army Value Projection")
    army_data = army_proj.get_data()
    print(f"  Current army value: {army_data['current_value']}")
    print(f"  Peak army value: {army_proj.peak_value()}")
    print(f"  Timeline entries: {len(army_data['timeline'])}")

    print("\n[4] Resource Curve Projection")
    res_data = resource_proj.get_data()
    print(f"  Total mined minerals: {res_data['total_mined_minerals']}")
    print(f"  Total mined vespene: {res_data['total_mined_vespene']}")
    print(f"  Total spent minerals: {res_data['total_spent_minerals']}")
    print(f"  Total spent vespene: {res_data['total_spent_vespene']}")
    print(f"  Net resources: {resource_proj.net_resources()}")

    print("\n[5] Unit Composition Projection")
    comp_data = composition_proj.get_data()
    print(f"  Alive units: {dict(comp_data['alive'])}")
    print(f"  Total created: {dict(comp_data['total_created'])}")

    # --- Event Bus ---
    print("\n[6] Event Bus Subscriptions")
    print(f"  Attack events received: {len(attack_log)}")
    for entry in attack_log:
        print(f"    - {entry}")
    print(f"  Total events published via bus: {sc2es.bus.total_published}")

    # --- Time-Travel Debugging ---
    print("\n[7] Time-Travel Debugging")
    for target_tick in [100, 200, 260, 400]:
        past_state = sc2es.rebuild_state_at_tick(game_id, target_tick)
        print(
            f"  Tick {target_tick:>4d}: units={past_state['alive_units']}, "
            f"army_value={past_state['army_value']}, "
            f"supply={past_state['supply']}"
        )

    # --- Event Log Export ---
    print("\n[8] Event Log (first 5 events)")
    log = sc2es.get_event_log(game_id)
    for entry in log[:5]:
        print(f"  [{entry['game_tick']:>4d}] {entry['event_type']}: {entry['data']}")
    print(f"  ... ({len(log)} total events)")

    # --- Snapshots ---
    print("\n[9] Snapshots")
    snap = sc2es.store.get_latest_snapshot(game_id)
    if snap:
        print(f"  Latest snapshot: version={snap.version}, tick={snap.game_tick}")
        print(f"  Snapshot state keys: {list(snap.state.keys())}")
    else:
        print("  No snapshots taken (game too short for interval)")

    # --- JSON Export/Import ---
    print("\n[10] JSON Export/Import")
    exported = sc2es.store.export_json()
    parsed = json.loads(exported)
    print(f"  Exported {len(parsed)} events as JSON ({len(exported)} bytes)")

    new_store = EventStore()
    imported = new_store.import_json(exported)
    print(f"  Re-imported {imported} events into fresh store")

    # --- Stats ---
    print("\n[11] System Stats")
    stats = sc2es.stats()
    for key, val in stats.items():
        print(f"  {key}: {val}")

    print("\n" + "=" * 70)
    print("Phase 663 Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 663: Event Sourcing registered
