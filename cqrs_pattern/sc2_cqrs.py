"""
Phase 664: CQRS Pattern for SC2 Data Access Segregation

Command Query Responsibility Segregation (CQRS) for StarCraft II bot data.
Separates real-time game control (write side) from analytics and
dashboard queries (read side), enabling optimized data access patterns
for both mutation-heavy game actions and read-heavy analysis workloads.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain value objects
# ---------------------------------------------------------------------------

class CommandType(Enum):
    BUILD_UNIT = auto()
    BUILD_STRUCTURE = auto()
    ATTACK_MOVE = auto()
    EXPAND = auto()
    RESEARCH_UPGRADE = auto()
    SET_RALLY_POINT = auto()
    RETREAT = auto()
    SCOUT = auto()
    SET_STRATEGY = auto()
    GATHER_RESOURCE = auto()


class QueryType(Enum):
    WIN_RATE = auto()
    ARMY_COMPOSITION = auto()
    ECONOMY_TIMELINE = auto()
    MATCH_HISTORY = auto()
    UNIT_STATISTICS = auto()
    BUILD_ORDER_ANALYSIS = auto()
    RESOURCE_EFFICIENCY = auto()
    MAP_CONTROL = auto()
    SUPPLY_TIMELINE = auto()
    ENGAGEMENT_HISTORY = auto()


class EventType(Enum):
    UNIT_CREATED = auto()
    STRUCTURE_BUILT = auto()
    ATTACK_ISSUED = auto()
    EXPANSION_STARTED = auto()
    UPGRADE_STARTED = auto()
    GAME_STATE_CHANGED = auto()
    RESOURCE_COLLECTED = auto()
    UNIT_DESTROYED = auto()
    STRATEGY_CHANGED = auto()
    ENGAGEMENT_RESOLVED = auto()


# ---------------------------------------------------------------------------
# Base event / command / query data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DomainEvent:
    """Immutable event emitted by the write side."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: EventType = EventType.GAME_STATE_CHANGED
    timestamp: float = field(default_factory=time.time)
    aggregate_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "timestamp": self.timestamp,
            "aggregate_id": self.aggregate_id,
            "payload": self.payload,
            "version": self.version,
        }


@dataclass
class Command:
    """Mutable intent that requests a state change."""
    command_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    command_type: CommandType = CommandType.BUILD_UNIT
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    issuer: str = "bot"
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.correlation_id:
            self.correlation_id = self.command_id


@dataclass
class Query:
    """Read-side request for data."""
    query_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query_type: QueryType = QueryType.WIN_RATE
    timestamp: float = field(default_factory=time.time)
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 100
    offset: int = 0


@dataclass
class CommandResult:
    success: bool = True
    events: List[DomainEvent] = field(default_factory=list)
    error: Optional[str] = None
    correlation_id: str = ""


@dataclass
class QueryResult:
    data: Any = None
    total_count: int = 0
    cached: bool = False
    query_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Event Store
# ---------------------------------------------------------------------------

class EventStore:
    """Append-only store that persists domain events."""

    def __init__(self) -> None:
        self._events: List[DomainEvent] = []
        self._aggregate_index: Dict[str, List[int]] = defaultdict(list)

    def append(self, event: DomainEvent) -> None:
        idx = len(self._events)
        self._events.append(event)
        if event.aggregate_id:
            self._aggregate_index[event.aggregate_id].append(idx)
        logger.debug("EventStore: appended %s (idx=%d)", event.event_type.name, idx)

    def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        since: Optional[float] = None,
    ) -> List[DomainEvent]:
        if aggregate_id is not None:
            indices = self._aggregate_index.get(aggregate_id, [])
            candidates = [self._events[i] for i in indices]
        else:
            candidates = list(self._events)

        if event_type is not None:
            candidates = [e for e in candidates if e.event_type == event_type]
        if since is not None:
            candidates = [e for e in candidates if e.timestamp >= since]
        return candidates

    @property
    def count(self) -> int:
        return len(self._events)

    def snapshot(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._events]


# ---------------------------------------------------------------------------
# Write Model (Command side)
# ---------------------------------------------------------------------------

class WriteModel:
    """
    Mutable game state that processes commands and emits events.
    This is the single source of truth for state mutations.
    """

    def __init__(self, event_store: EventStore) -> None:
        self._event_store = event_store
        self._game_state: Dict[str, Any] = {
            "minerals": 50,
            "vespene": 0,
            "supply_used": 12,
            "supply_cap": 15,
            "units": {},
            "structures": {},
            "upgrades": [],
            "current_strategy": "macro",
            "expansions": 1,
            "game_time": 0.0,
        }
        self._command_log: List[Dict[str, Any]] = []

    @property
    def state(self) -> Dict[str, Any]:
        return dict(self._game_state)

    # -- individual command handlers --

    def _handle_build_unit(self, cmd: Command) -> CommandResult:
        unit_type = cmd.payload.get("unit_type", "Zergling")
        count = cmd.payload.get("count", 1)
        cost_minerals = cmd.payload.get("cost_minerals", 25 * count)
        cost_vespene = cmd.payload.get("cost_vespene", 0)
        supply_cost = cmd.payload.get("supply_cost", count)

        if self._game_state["minerals"] < cost_minerals:
            return CommandResult(
                success=False,
                error=f"Insufficient minerals: need {cost_minerals}, have {self._game_state['minerals']}",
                correlation_id=cmd.correlation_id,
            )
        if self._game_state["supply_used"] + supply_cost > self._game_state["supply_cap"]:
            return CommandResult(
                success=False,
                error="Supply blocked",
                correlation_id=cmd.correlation_id,
            )

        self._game_state["minerals"] -= cost_minerals
        self._game_state["vespene"] -= cost_vespene
        self._game_state["supply_used"] += supply_cost
        current = self._game_state["units"].get(unit_type, 0)
        self._game_state["units"][unit_type] = current + count

        event = DomainEvent(
            event_type=EventType.UNIT_CREATED,
            aggregate_id=f"unit-{unit_type}",
            payload={"unit_type": unit_type, "count": count, "total": current + count},
        )
        return CommandResult(success=True, events=[event], correlation_id=cmd.correlation_id)

    def _handle_build_structure(self, cmd: Command) -> CommandResult:
        structure_type = cmd.payload.get("structure_type", "Hatchery")
        cost_minerals = cmd.payload.get("cost_minerals", 300)
        cost_vespene = cmd.payload.get("cost_vespene", 0)

        if self._game_state["minerals"] < cost_minerals:
            return CommandResult(
                success=False,
                error=f"Insufficient minerals for {structure_type}",
                correlation_id=cmd.correlation_id,
            )

        self._game_state["minerals"] -= cost_minerals
        self._game_state["vespene"] -= cost_vespene
        current = self._game_state["structures"].get(structure_type, 0)
        self._game_state["structures"][structure_type] = current + 1

        if structure_type in ("Hatchery", "Nexus", "CommandCenter"):
            self._game_state["supply_cap"] += 6

        event = DomainEvent(
            event_type=EventType.STRUCTURE_BUILT,
            aggregate_id=f"struct-{structure_type}",
            payload={"structure_type": structure_type, "total": current + 1},
        )
        return CommandResult(success=True, events=[event], correlation_id=cmd.correlation_id)

    def _handle_attack_move(self, cmd: Command) -> CommandResult:
        target = cmd.payload.get("target", (50.0, 50.0))
        units = cmd.payload.get("units", list(self._game_state["units"].keys()))

        event = DomainEvent(
            event_type=EventType.ATTACK_ISSUED,
            aggregate_id="army",
            payload={"target": target, "units": units, "timestamp": time.time()},
        )
        return CommandResult(success=True, events=[event], correlation_id=cmd.correlation_id)

    def _handle_expand(self, cmd: Command) -> CommandResult:
        location = cmd.payload.get("location", "natural")
        cost = cmd.payload.get("cost_minerals", 300)

        if self._game_state["minerals"] < cost:
            return CommandResult(
                success=False,
                error="Insufficient minerals for expansion",
                correlation_id=cmd.correlation_id,
            )

        self._game_state["minerals"] -= cost
        self._game_state["expansions"] += 1

        event = DomainEvent(
            event_type=EventType.EXPANSION_STARTED,
            aggregate_id="expansion",
            payload={"location": location, "expansion_count": self._game_state["expansions"]},
        )
        return CommandResult(success=True, events=[event], correlation_id=cmd.correlation_id)

    def _handle_research_upgrade(self, cmd: Command) -> CommandResult:
        upgrade = cmd.payload.get("upgrade", "MetabolicBoost")
        cost_minerals = cmd.payload.get("cost_minerals", 100)
        cost_vespene = cmd.payload.get("cost_vespene", 100)

        if upgrade in self._game_state["upgrades"]:
            return CommandResult(
                success=False,
                error=f"Upgrade {upgrade} already researched",
                correlation_id=cmd.correlation_id,
            )
        if self._game_state["minerals"] < cost_minerals or self._game_state["vespene"] < cost_vespene:
            return CommandResult(
                success=False,
                error="Insufficient resources for upgrade",
                correlation_id=cmd.correlation_id,
            )

        self._game_state["minerals"] -= cost_minerals
        self._game_state["vespene"] -= cost_vespene
        self._game_state["upgrades"].append(upgrade)

        event = DomainEvent(
            event_type=EventType.UPGRADE_STARTED,
            aggregate_id=f"upgrade-{upgrade}",
            payload={"upgrade": upgrade},
        )
        return CommandResult(success=True, events=[event], correlation_id=cmd.correlation_id)

    def _handle_set_strategy(self, cmd: Command) -> CommandResult:
        strategy = cmd.payload.get("strategy", "aggressive")
        previous = self._game_state["current_strategy"]
        self._game_state["current_strategy"] = strategy

        event = DomainEvent(
            event_type=EventType.STRATEGY_CHANGED,
            aggregate_id="strategy",
            payload={"previous": previous, "current": strategy},
        )
        return CommandResult(success=True, events=[event], correlation_id=cmd.correlation_id)

    def _handle_gather_resource(self, cmd: Command) -> CommandResult:
        mineral_gain = cmd.payload.get("minerals", 75)
        vespene_gain = cmd.payload.get("vespene", 25)
        self._game_state["minerals"] += mineral_gain
        self._game_state["vespene"] += vespene_gain

        event = DomainEvent(
            event_type=EventType.RESOURCE_COLLECTED,
            aggregate_id="economy",
            payload={"minerals_gained": mineral_gain, "vespene_gained": vespene_gain},
        )
        return CommandResult(success=True, events=[event], correlation_id=cmd.correlation_id)

    _DISPATCH: Dict[CommandType, str] = {
        CommandType.BUILD_UNIT: "_handle_build_unit",
        CommandType.BUILD_STRUCTURE: "_handle_build_structure",
        CommandType.ATTACK_MOVE: "_handle_attack_move",
        CommandType.EXPAND: "_handle_expand",
        CommandType.RESEARCH_UPGRADE: "_handle_research_upgrade",
        CommandType.SET_STRATEGY: "_handle_set_strategy",
        CommandType.GATHER_RESOURCE: "_handle_gather_resource",
    }

    def execute(self, cmd: Command) -> CommandResult:
        handler_name = self._DISPATCH.get(cmd.command_type)
        if handler_name is None:
            return CommandResult(
                success=False,
                error=f"No handler for {cmd.command_type.name}",
                correlation_id=cmd.correlation_id,
            )

        handler = getattr(self, handler_name)
        result: CommandResult = handler(cmd)

        if result.success:
            for event in result.events:
                self._event_store.append(event)
            self._command_log.append({
                "command_id": cmd.command_id,
                "type": cmd.command_type.name,
                "success": True,
                "events": len(result.events),
            })
        else:
            self._command_log.append({
                "command_id": cmd.command_id,
                "type": cmd.command_type.name,
                "success": False,
                "error": result.error,
            })

        return result


# ---------------------------------------------------------------------------
# Read Model Projections
# ---------------------------------------------------------------------------

class ReadModelProjection(ABC):
    """Base class for read-model projections."""

    @abstractmethod
    def apply(self, event: DomainEvent) -> None:
        ...

    @abstractmethod
    def query(self, filters: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...


class WinRateProjection(ReadModelProjection):
    """Tracks win/loss statistics across matches."""

    def __init__(self) -> None:
        self._matches: List[Dict[str, Any]] = []
        self._wins = 0
        self._losses = 0
        self._draws = 0
        self._race_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0})

    def apply(self, event: DomainEvent) -> None:
        if event.event_type == EventType.GAME_STATE_CHANGED:
            result = event.payload.get("match_result")
            opponent_race = event.payload.get("opponent_race", "Unknown")
            if result == "win":
                self._wins += 1
                self._race_stats[opponent_race]["wins"] += 1
            elif result == "loss":
                self._losses += 1
                self._race_stats[opponent_race]["losses"] += 1
            elif result == "draw":
                self._draws += 1
            if result:
                self._matches.append({
                    "result": result,
                    "opponent_race": opponent_race,
                    "timestamp": event.timestamp,
                    "strategy": event.payload.get("strategy", "unknown"),
                })

    def query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        total = self._wins + self._losses + self._draws
        win_rate = (self._wins / total * 100.0) if total > 0 else 0.0
        race_filter = filters.get("opponent_race")

        if race_filter and race_filter in self._race_stats:
            stats = self._race_stats[race_filter]
            race_total = stats["wins"] + stats["losses"]
            race_wr = (stats["wins"] / race_total * 100.0) if race_total > 0 else 0.0
            return {
                "opponent_race": race_filter,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate": round(race_wr, 2),
                "total_matches": race_total,
            }

        return {
            "total_matches": total,
            "wins": self._wins,
            "losses": self._losses,
            "draws": self._draws,
            "win_rate": round(win_rate, 2),
            "by_race": {
                race: {
                    "wins": s["wins"],
                    "losses": s["losses"],
                    "win_rate": round(s["wins"] / max(s["wins"] + s["losses"], 1) * 100, 2),
                }
                for race, s in self._race_stats.items()
            },
            "recent_matches": self._matches[-10:],
        }

    def reset(self) -> None:
        self._matches.clear()
        self._wins = self._losses = self._draws = 0
        self._race_stats.clear()


class ArmyCompositionProjection(ReadModelProjection):
    """Tracks current and historical army composition."""

    def __init__(self) -> None:
        self._current_units: Dict[str, int] = {}
        self._snapshots: List[Dict[str, Any]] = []

    def apply(self, event: DomainEvent) -> None:
        if event.event_type == EventType.UNIT_CREATED:
            unit_type = event.payload.get("unit_type", "Unknown")
            total = event.payload.get("total", 1)
            self._current_units[unit_type] = total
            self._snapshots.append({
                "timestamp": event.timestamp,
                "composition": dict(self._current_units),
                "event": "created",
                "unit_type": unit_type,
            })
        elif event.event_type == EventType.UNIT_DESTROYED:
            unit_type = event.payload.get("unit_type", "Unknown")
            remaining = event.payload.get("remaining", 0)
            self._current_units[unit_type] = remaining
            if remaining <= 0:
                self._current_units.pop(unit_type, None)
            self._snapshots.append({
                "timestamp": event.timestamp,
                "composition": dict(self._current_units),
                "event": "destroyed",
                "unit_type": unit_type,
            })

    def query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        total_units = sum(self._current_units.values())
        percentages = {}
        for unit_type, count in self._current_units.items():
            percentages[unit_type] = round(count / max(total_units, 1) * 100, 2)

        result: Dict[str, Any] = {
            "current_composition": dict(self._current_units),
            "total_units": total_units,
            "percentages": percentages,
        }
        if filters.get("include_history"):
            result["history"] = self._snapshots[-20:]

        return result

    def reset(self) -> None:
        self._current_units.clear()
        self._snapshots.clear()


class EconomyTimelineProjection(ReadModelProjection):
    """Tracks resource collection and spending over time."""

    def __init__(self) -> None:
        self._timeline: List[Dict[str, Any]] = []
        self._total_minerals_collected: int = 0
        self._total_vespene_collected: int = 0
        self._total_minerals_spent: int = 0
        self._total_vespene_spent: int = 0

    def apply(self, event: DomainEvent) -> None:
        if event.event_type == EventType.RESOURCE_COLLECTED:
            m = event.payload.get("minerals_gained", 0)
            v = event.payload.get("vespene_gained", 0)
            self._total_minerals_collected += m
            self._total_vespene_collected += v
            self._timeline.append({
                "timestamp": event.timestamp,
                "type": "income",
                "minerals": m,
                "vespene": v,
            })
        elif event.event_type in (EventType.UNIT_CREATED, EventType.STRUCTURE_BUILT, EventType.UPGRADE_STARTED):
            cost_m = event.payload.get("cost_minerals", 0)
            cost_v = event.payload.get("cost_vespene", 0)
            self._total_minerals_spent += cost_m
            self._total_vespene_spent += cost_v
            self._timeline.append({
                "timestamp": event.timestamp,
                "type": "expense",
                "minerals": cost_m,
                "vespene": cost_v,
                "item": event.payload.get("unit_type") or event.payload.get("structure_type") or event.payload.get("upgrade"),
            })

    def query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        since = filters.get("since", 0.0)
        filtered = [e for e in self._timeline if e["timestamp"] >= since]
        return {
            "total_minerals_collected": self._total_minerals_collected,
            "total_vespene_collected": self._total_vespene_collected,
            "total_minerals_spent": self._total_minerals_spent,
            "total_vespene_spent": self._total_vespene_spent,
            "mineral_efficiency": round(
                self._total_minerals_spent / max(self._total_minerals_collected, 1) * 100, 2
            ),
            "timeline_entries": len(filtered),
            "timeline": filtered[-30:],
        }

    def reset(self) -> None:
        self._timeline.clear()
        self._total_minerals_collected = 0
        self._total_vespene_collected = 0
        self._total_minerals_spent = 0
        self._total_vespene_spent = 0


class SupplyTimelineProjection(ReadModelProjection):
    """Tracks supply usage over time for supply-block analysis."""

    def __init__(self) -> None:
        self._snapshots: List[Dict[str, Any]] = []
        self._supply_blocks: int = 0

    def apply(self, event: DomainEvent) -> None:
        if event.event_type in (EventType.UNIT_CREATED, EventType.STRUCTURE_BUILT):
            supply_used = event.payload.get("supply_used", 0)
            supply_cap = event.payload.get("supply_cap", 0)
            if supply_used and supply_cap:
                self._snapshots.append({
                    "timestamp": event.timestamp,
                    "supply_used": supply_used,
                    "supply_cap": supply_cap,
                    "utilization": round(supply_used / max(supply_cap, 1) * 100, 2),
                })
                if supply_used >= supply_cap:
                    self._supply_blocks += 1

    def query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "snapshots": self._snapshots[-50:],
            "supply_blocks": self._supply_blocks,
            "total_entries": len(self._snapshots),
        }

    def reset(self) -> None:
        self._snapshots.clear()
        self._supply_blocks = 0


class EngagementHistoryProjection(ReadModelProjection):
    """Tracks attack commands and engagement outcomes."""

    def __init__(self) -> None:
        self._engagements: List[Dict[str, Any]] = []

    def apply(self, event: DomainEvent) -> None:
        if event.event_type == EventType.ATTACK_ISSUED:
            self._engagements.append({
                "timestamp": event.timestamp,
                "target": event.payload.get("target"),
                "units": event.payload.get("units", []),
                "outcome": event.payload.get("outcome", "pending"),
            })
        elif event.event_type == EventType.ENGAGEMENT_RESOLVED:
            eng_id = event.payload.get("engagement_index")
            if eng_id is not None and 0 <= eng_id < len(self._engagements):
                self._engagements[eng_id]["outcome"] = event.payload.get("outcome", "unknown")

    def query(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        limit = filters.get("limit", 20)
        return {
            "total_engagements": len(self._engagements),
            "recent": self._engagements[-limit:],
        }

    def reset(self) -> None:
        self._engagements.clear()


# ---------------------------------------------------------------------------
# Read Model
# ---------------------------------------------------------------------------

class ReadModel:
    """
    Aggregates multiple projections and serves read-side queries.
    Updated asynchronously from the event store.
    """

    def __init__(self) -> None:
        self._projections: Dict[QueryType, ReadModelProjection] = {
            QueryType.WIN_RATE: WinRateProjection(),
            QueryType.ARMY_COMPOSITION: ArmyCompositionProjection(),
            QueryType.ECONOMY_TIMELINE: EconomyTimelineProjection(),
            QueryType.SUPPLY_TIMELINE: SupplyTimelineProjection(),
            QueryType.ENGAGEMENT_HISTORY: EngagementHistoryProjection(),
        }
        self._all_projections: List[ReadModelProjection] = list(self._projections.values())
        self._last_processed_index: int = 0
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl: float = 2.0  # seconds

    def apply_event(self, event: DomainEvent) -> None:
        for projection in self._all_projections:
            projection.apply(event)
        self._last_processed_index += 1

    def catch_up(self, event_store: EventStore) -> int:
        """Replay events from the store that haven't been processed yet."""
        all_events = event_store.get_events()
        new_events = all_events[self._last_processed_index:]
        for event in new_events:
            self.apply_event(event)
        return len(new_events)

    def execute_query(self, query: Query) -> QueryResult:
        start = time.time()

        cache_key = f"{query.query_type.name}:{json.dumps(query.filters, sort_keys=True)}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                elapsed = (time.time() - start) * 1000
                return QueryResult(data=cached_data, cached=True, query_time_ms=round(elapsed, 3))

        projection = self._projections.get(query.query_type)
        if projection is None:
            elapsed = (time.time() - start) * 1000
            return QueryResult(
                data={"error": f"No projection for {query.query_type.name}"},
                query_time_ms=round(elapsed, 3),
            )

        data = projection.query(query.filters)
        self._cache[cache_key] = (time.time(), data)
        elapsed = (time.time() - start) * 1000
        return QueryResult(data=data, query_time_ms=round(elapsed, 3))

    def reset_all(self) -> None:
        for projection in self._all_projections:
            projection.reset()
        self._last_processed_index = 0
        self._cache.clear()


# ---------------------------------------------------------------------------
# Command Handler / Query Handler
# ---------------------------------------------------------------------------

class CommandHandler:
    """Validates and dispatches commands to the write model."""

    def __init__(self, write_model: WriteModel) -> None:
        self._write_model = write_model
        self._middleware: List[Callable[[Command], Optional[str]]] = []

    def add_middleware(self, fn: Callable[[Command], Optional[str]]) -> None:
        self._middleware.append(fn)

    def handle(self, command: Command) -> CommandResult:
        for mw in self._middleware:
            error = mw(command)
            if error is not None:
                return CommandResult(success=False, error=error, correlation_id=command.correlation_id)

        return self._write_model.execute(command)


class QueryHandler:
    """Dispatches queries to the read model."""

    def __init__(self, read_model: ReadModel) -> None:
        self._read_model = read_model

    def handle(self, query: Query) -> QueryResult:
        return self._read_model.execute_query(query)


# ---------------------------------------------------------------------------
# CQRS Bus (facade)
# ---------------------------------------------------------------------------

class CQRSBus:
    """
    Central bus that routes commands and queries to the correct side.
    Also handles eventual consistency by propagating events from write to read.
    """

    def __init__(self) -> None:
        self._event_store = EventStore()
        self._write_model = WriteModel(self._event_store)
        self._read_model = ReadModel()
        self._command_handler = CommandHandler(self._write_model)
        self._query_handler = QueryHandler(self._read_model)
        self._event_listeners: List[Callable[[DomainEvent], None]] = []
        self._propagation_mode: str = "sync"  # "sync" or "async"
        self._pending_events: List[DomainEvent] = []

    @property
    def event_store(self) -> EventStore:
        return self._event_store

    @property
    def write_model(self) -> WriteModel:
        return self._write_model

    @property
    def read_model(self) -> ReadModel:
        return self._read_model

    def add_command_middleware(self, fn: Callable[[Command], Optional[str]]) -> None:
        self._command_handler.add_middleware(fn)

    def add_event_listener(self, fn: Callable[[DomainEvent], None]) -> None:
        self._event_listeners.append(fn)

    def set_propagation_mode(self, mode: str) -> None:
        if mode not in ("sync", "async"):
            raise ValueError(f"Invalid mode: {mode}")
        self._propagation_mode = mode

    def dispatch_command(self, command: Command) -> CommandResult:
        result = self._command_handler.handle(command)

        if result.success and result.events:
            if self._propagation_mode == "sync":
                self._propagate_events(result.events)
            else:
                self._pending_events.extend(result.events)

        return result

    def dispatch_query(self, query: Query) -> QueryResult:
        # Ensure read model is up to date before querying
        if self._propagation_mode == "async" and self._pending_events:
            self._flush_pending()
        return self._query_handler.handle(query)

    def _propagate_events(self, events: List[DomainEvent]) -> None:
        for event in events:
            self._read_model.apply_event(event)
            for listener in self._event_listeners:
                try:
                    listener(event)
                except Exception as exc:
                    logger.warning("Event listener error: %s", exc)

    def _flush_pending(self) -> None:
        pending = list(self._pending_events)
        self._pending_events.clear()
        self._propagate_events(pending)

    def flush(self) -> int:
        """Manually flush pending events (for async mode). Returns count flushed."""
        count = len(self._pending_events)
        self._flush_pending()
        return count

    def get_state_snapshot(self) -> Dict[str, Any]:
        return {
            "write_state": self._write_model.state,
            "event_count": self._event_store.count,
            "propagation_mode": self._propagation_mode,
            "pending_events": len(self._pending_events),
        }


# ---------------------------------------------------------------------------
# Async CQRS Bus (for async event propagation)
# ---------------------------------------------------------------------------

class AsyncCQRSBus:
    """
    Async variant of CQRSBus supporting eventual consistency
    with configurable propagation delay.
    """

    def __init__(self, propagation_delay: float = 0.01) -> None:
        self._bus = CQRSBus()
        self._bus.set_propagation_mode("async")
        self._propagation_delay = propagation_delay
        self._running = False
        self._event_queue: List[DomainEvent] = []

    async def dispatch_command(self, command: Command) -> CommandResult:
        result = self._bus.dispatch_command(command)
        if result.success and result.events:
            self._event_queue.extend(result.events)
        return result

    async def dispatch_query(self, query: Query) -> QueryResult:
        return self._bus.dispatch_query(query)

    async def propagate_once(self) -> int:
        """Process one batch of pending events with simulated delay."""
        if not self._event_queue:
            return 0
        await asyncio.sleep(self._propagation_delay)
        batch = list(self._event_queue)
        self._event_queue.clear()
        for event in batch:
            self._bus.read_model.apply_event(event)
        return len(batch)

    async def run_propagation_loop(self) -> None:
        self._running = True
        while self._running:
            await self.propagate_once()
            await asyncio.sleep(self._propagation_delay)

    def stop(self) -> None:
        self._running = False

    @property
    def inner_bus(self) -> CQRSBus:
        return self._bus


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def create_sc2_cqrs_bus(mode: str = "sync") -> CQRSBus:
    """Factory function to create a pre-configured CQRS bus for SC2."""
    bus = CQRSBus()
    bus.set_propagation_mode(mode)

    # Add logging middleware
    def log_command(cmd: Command) -> Optional[str]:
        logger.info("CQRS command: %s [%s]", cmd.command_type.name, cmd.command_id)
        return None

    bus.add_command_middleware(log_command)
    return bus


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    """Demonstrate CQRS pattern for SC2 data access."""
    print("=" * 70)
    print("Phase 664: CQRS Pattern for SC2 Data Access Segregation")
    print("=" * 70)

    bus = create_sc2_cqrs_bus(mode="sync")

    # --- Track some events for the read model ---
    listened_events: List[str] = []
    bus.add_event_listener(lambda e: listened_events.append(e.event_type.name))

    # 1) Gather resources
    print("\n[1] Gathering resources...")
    for _ in range(5):
        r = bus.dispatch_command(Command(
            command_type=CommandType.GATHER_RESOURCE,
            payload={"minerals": 100, "vespene": 50},
        ))
        assert r.success

    # 2) Build units
    print("[2] Building units...")
    r = bus.dispatch_command(Command(
        command_type=CommandType.BUILD_UNIT,
        payload={"unit_type": "Zergling", "count": 12, "cost_minerals": 150, "supply_cost": 6},
    ))
    print(f"    Zerglings: success={r.success}")

    r = bus.dispatch_command(Command(
        command_type=CommandType.BUILD_UNIT,
        payload={"unit_type": "Roach", "count": 4, "cost_minerals": 150, "cost_vespene": 50, "supply_cost": 8},
    ))
    print(f"    Roaches: success={r.success}")

    # 3) Build structure
    print("[3] Building structure...")
    r = bus.dispatch_command(Command(
        command_type=CommandType.BUILD_STRUCTURE,
        payload={"structure_type": "SpawningPool", "cost_minerals": 200},
    ))
    print(f"    SpawningPool: success={r.success}")

    # 4) Attack
    print("[4] Issuing attack...")
    r = bus.dispatch_command(Command(
        command_type=CommandType.ATTACK_MOVE,
        payload={"target": (45.0, 60.0), "units": ["Zergling", "Roach"]},
    ))
    print(f"    Attack: success={r.success}")

    # 5) Set strategy
    print("[5] Changing strategy...")
    r = bus.dispatch_command(Command(
        command_type=CommandType.SET_STRATEGY,
        payload={"strategy": "all-in"},
    ))
    print(f"    Strategy: success={r.success}")

    # 6) Inject match results for win-rate projection
    print("[6] Recording match results...")
    for result, race in [("win", "Protoss"), ("win", "Terran"), ("loss", "Zerg"), ("win", "Protoss")]:
        event = DomainEvent(
            event_type=EventType.GAME_STATE_CHANGED,
            aggregate_id="match",
            payload={"match_result": result, "opponent_race": race, "strategy": "all-in"},
        )
        bus.event_store.append(event)
        bus.read_model.apply_event(event)

    # --- Read-side queries ---
    print("\n--- Read-Side Queries ---")

    # Win rate
    qr = bus.dispatch_query(Query(query_type=QueryType.WIN_RATE))
    print(f"\n[Q] Win Rate: {json.dumps(qr.data, indent=2)}")
    print(f"    (query time: {qr.query_time_ms:.3f}ms, cached: {qr.cached})")

    # Win rate vs Protoss
    qr = bus.dispatch_query(Query(query_type=QueryType.WIN_RATE, filters={"opponent_race": "Protoss"}))
    print(f"\n[Q] Win Rate vs Protoss: {json.dumps(qr.data, indent=2)}")

    # Army composition
    qr = bus.dispatch_query(Query(query_type=QueryType.ARMY_COMPOSITION, filters={"include_history": True}))
    print(f"\n[Q] Army Composition: {json.dumps(qr.data, indent=2)}")

    # Economy timeline
    qr = bus.dispatch_query(Query(query_type=QueryType.ECONOMY_TIMELINE))
    eco = qr.data
    print(f"\n[Q] Economy: collected M={eco['total_minerals_collected']} V={eco['total_vespene_collected']}")
    print(f"    spent M={eco['total_minerals_spent']} V={eco['total_vespene_spent']}")
    print(f"    efficiency={eco['mineral_efficiency']}%")

    # Engagement history
    qr = bus.dispatch_query(Query(query_type=QueryType.ENGAGEMENT_HISTORY))
    print(f"\n[Q] Engagements: {qr.data['total_engagements']} total")

    # --- Write-side state ---
    print("\n--- Write-Side State ---")
    snapshot = bus.get_state_snapshot()
    print(f"  Game state: {json.dumps(snapshot['write_state'], indent=2)}")
    print(f"  Event count: {snapshot['event_count']}")

    # --- Async mode demo ---
    print("\n--- Async Propagation Demo ---")
    async_bus = CQRSBus()
    async_bus.set_propagation_mode("async")

    for _ in range(3):
        async_bus.dispatch_command(Command(
            command_type=CommandType.GATHER_RESOURCE,
            payload={"minerals": 50, "vespene": 25},
        ))

    snap = async_bus.get_state_snapshot()
    print(f"  Pending events before flush: {snap['pending_events']}")
    flushed = async_bus.flush()
    print(f"  Flushed {flushed} events")
    snap = async_bus.get_state_snapshot()
    print(f"  Pending events after flush: {snap['pending_events']}")

    # Event listener summary
    print(f"\n  Total events observed by listener: {len(listened_events)}")
    print(f"  Event types: {listened_events}")

    print("\n" + "=" * 70)
    print("Phase 664 CQRS demonstration complete.")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()

# Phase 664: CQRS registered
