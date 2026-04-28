"""
Phase 665: GraphQL API for SC2 Game Data

GraphQL-style API that provides flexible querying of StarCraft II game data.
Implements a type system, resolver architecture, query/mutation/subscription
model, and a lightweight server for single-request access to any combination
of game state, match history, player statistics, and real-time events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
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
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GraphQL Type System
# ---------------------------------------------------------------------------


class TypeKind(Enum):
    SCALAR = auto()
    OBJECT = auto()
    LIST = auto()
    NON_NULL = auto()
    ENUM = auto()
    INPUT_OBJECT = auto()


@dataclass
class Field:
    """A single field on an object type."""

    name: str
    type_name: str
    description: str = ""
    args: Dict[str, str] = field(default_factory=dict)
    nullable: bool = True
    is_list: bool = False
    default_value: Any = None

    def to_schema_str(self) -> str:
        args_str = ""
        if self.args:
            inner = ", ".join(f"{k}: {v}" for k, v in self.args.items())
            args_str = f"({inner})"
        t = f"[{self.type_name}]" if self.is_list else self.type_name
        if not self.nullable:
            t += "!"
        return f"  {self.name}{args_str}: {t}"


@dataclass
class ObjectType:
    """GraphQL object type definition."""

    name: str
    fields: Dict[str, Field] = field(default_factory=dict)
    description: str = ""

    def add_field(self, f: Field) -> None:
        self.fields[f.name] = f

    def to_schema_str(self) -> str:
        desc = f'"""{self.description}"""\n' if self.description else ""
        fields_str = "\n".join(f.to_schema_str() for f in self.fields.values())
        return f"{desc}type {self.name} {{\n{fields_str}\n}}"


@dataclass
class EnumType:
    """GraphQL enum type definition."""

    name: str
    values: List[str] = field(default_factory=list)
    description: str = ""

    def to_schema_str(self) -> str:
        vals = "\n".join(f"  {v}" for v in self.values)
        return f"enum {self.name} {{\n{vals}\n}}"


@dataclass
class InputType:
    """GraphQL input object type definition."""

    name: str
    fields: Dict[str, Field] = field(default_factory=dict)
    description: str = ""

    def add_field(self, f: Field) -> None:
        self.fields[f.name] = f

    def to_schema_str(self) -> str:
        fields_str = "\n".join(f.to_schema_str() for f in self.fields.values())
        return f"input {self.name} {{\n{fields_str}\n}}"


# ---------------------------------------------------------------------------
# Schema registry
# ---------------------------------------------------------------------------


class Schema:
    """Holds all type definitions and the root query/mutation/subscription types."""

    def __init__(self) -> None:
        self._types: Dict[str, Union[ObjectType, EnumType, InputType]] = {}
        self._scalars: Set[str] = {"String", "Int", "Float", "Boolean", "ID"}
        self._query_type: Optional[ObjectType] = None
        self._mutation_type: Optional[ObjectType] = None
        self._subscription_type: Optional[ObjectType] = None

    def add_type(self, t: Union[ObjectType, EnumType, InputType]) -> None:
        self._types[t.name] = t

    def add_scalar(self, name: str) -> None:
        self._scalars.add(name)

    def set_query_type(self, t: ObjectType) -> None:
        self._query_type = t
        self.add_type(t)

    def set_mutation_type(self, t: ObjectType) -> None:
        self._mutation_type = t
        self.add_type(t)

    def set_subscription_type(self, t: ObjectType) -> None:
        self._subscription_type = t
        self.add_type(t)

    def get_type(self, name: str) -> Optional[Union[ObjectType, EnumType, InputType]]:
        return self._types.get(name)

    @property
    def query_type(self) -> Optional[ObjectType]:
        return self._query_type

    @property
    def mutation_type(self) -> Optional[ObjectType]:
        return self._mutation_type

    def to_schema_str(self) -> str:
        parts: List[str] = []
        for t in self._types.values():
            parts.append(t.to_schema_str())
        parts.append("schema {")
        if self._query_type:
            parts.append(f"  query: {self._query_type.name}")
        if self._mutation_type:
            parts.append(f"  mutation: {self._mutation_type.name}")
        if self._subscription_type:
            parts.append(f"  subscription: {self._subscription_type.name}")
        parts.append("}")
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Resolver infrastructure
# ---------------------------------------------------------------------------


@dataclass
class ResolverContext:
    """Context passed to every resolver."""

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    user: str = "bot"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Resolver:
    """Maps field names to resolver functions."""

    def __init__(self) -> None:
        self._resolvers: Dict[str, Dict[str, Callable]] = defaultdict(dict)

    def register(self, type_name: str, field_name: str, fn: Callable) -> None:
        self._resolvers[type_name][field_name] = fn

    def resolve(
        self,
        type_name: str,
        field_name: str,
        parent: Any,
        args: Dict[str, Any],
        context: ResolverContext,
    ) -> Any:
        fn = self._resolvers.get(type_name, {}).get(field_name)
        if fn is None:
            # Default field resolution: dict key or attribute
            if isinstance(parent, dict):
                return parent.get(field_name)
            return getattr(parent, field_name, None)
        return fn(parent, args, context)

    @property
    def registered_count(self) -> int:
        return sum(len(v) for v in self._resolvers.values())


# ---------------------------------------------------------------------------
# Simple query parser
# ---------------------------------------------------------------------------


@dataclass
class ParsedField:
    name: str
    alias: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    sub_fields: List["ParsedField"] = field(default_factory=list)


@dataclass
class ParsedOperation:
    operation_type: str = "query"  # query | mutation | subscription
    name: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    fields: List[ParsedField] = field(default_factory=list)


class QueryParser:
    """
    Lightweight parser for a simplified GraphQL query syntax.
    Supports nested field selection, arguments, and aliases.
    """

    @staticmethod
    def parse(
        query_str: str, variables: Optional[Dict[str, Any]] = None
    ) -> ParsedOperation:
        query_str = query_str.strip()
        op_type = "query"
        op_name = ""

        # Detect operation type
        for prefix in ("query", "mutation", "subscription"):
            if query_str.lower().startswith(prefix):
                op_type = prefix
                query_str = query_str[len(prefix) :].strip()
                # Optional operation name
                name_match = re.match(r"^(\w+)", query_str)
                if name_match:
                    op_name = name_match.group(1)
                    query_str = query_str[len(op_name) :].strip()
                break

        # Strip outer braces
        if query_str.startswith("{"):
            query_str = query_str[1:]
        if query_str.endswith("}"):
            query_str = query_str[:-1]

        fields = QueryParser._parse_fields(query_str.strip())
        return ParsedOperation(
            operation_type=op_type,
            name=op_name,
            variables=variables or {},
            fields=fields,
        )

    @staticmethod
    def _parse_fields(text: str) -> List[ParsedField]:
        fields: List[ParsedField] = []
        i = 0
        n = len(text)

        while i < n:
            # Skip whitespace and commas
            while i < n and text[i] in " \t\n\r,":
                i += 1
            if i >= n:
                break

            # Read field name (or alias)
            name_start = i
            while i < n and text[i] not in " \t\n\r,({:}":
                i += 1
            token = text[name_start:i].strip()
            if not token:
                i += 1
                continue

            alias = None
            # Check for alias (token: actualName)
            while i < n and text[i] in " \t":
                i += 1
            if i < n and text[i] == ":":
                alias = token
                i += 1
                while i < n and text[i] in " \t":
                    i += 1
                name_start2 = i
                while i < n and text[i] not in " \t\n\r,({:}":
                    i += 1
                token = text[name_start2:i].strip()

            field_name = token
            if not field_name:
                continue

            # Parse args
            args: Dict[str, Any] = {}
            while i < n and text[i] in " \t":
                i += 1
            if i < n and text[i] == "(":
                paren_end = QueryParser._find_matching(text, i, "(", ")")
                args_str = text[i + 1 : paren_end]
                args = QueryParser._parse_args(args_str)
                i = paren_end + 1

            # Parse sub-fields
            sub_fields: List[ParsedField] = []
            while i < n and text[i] in " \t\n\r":
                i += 1
            if i < n and text[i] == "{":
                brace_end = QueryParser._find_matching(text, i, "{", "}")
                inner = text[i + 1 : brace_end]
                sub_fields = QueryParser._parse_fields(inner)
                i = brace_end + 1

            fields.append(
                ParsedField(
                    name=field_name,
                    alias=alias,
                    args=args,
                    sub_fields=sub_fields,
                )
            )

        return fields

    @staticmethod
    def _find_matching(text: str, start: int, open_ch: str, close_ch: str) -> int:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_ch:
                depth += 1
            elif text[i] == close_ch:
                depth -= 1
                if depth == 0:
                    return i
        return len(text) - 1

    @staticmethod
    def _parse_args(args_str: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        parts = args_str.split(",")
        for part in parts:
            part = part.strip()
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Attempt type coercion
            if value.lower() == "true":
                result[key] = True
            elif value.lower() == "false":
                result[key] = False
            elif value.isdigit():
                result[key] = int(value)
            else:
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = value
        return result


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------


class ExecutionEngine:
    """Executes parsed operations against resolvers."""

    def __init__(self, schema: Schema, resolver: Resolver) -> None:
        self._schema = schema
        self._resolver = resolver

    def execute(
        self,
        operation: ParsedOperation,
        context: Optional[ResolverContext] = None,
    ) -> Dict[str, Any]:
        ctx = context or ResolverContext()
        start = time.time()

        if operation.operation_type == "query":
            root_type_name = (
                self._schema.query_type.name if self._schema.query_type else "Query"
            )
        elif operation.operation_type == "mutation":
            root_type_name = (
                self._schema.mutation_type.name
                if self._schema.mutation_type
                else "Mutation"
            )
        else:
            root_type_name = "Subscription"

        data: Dict[str, Any] = {}
        errors: List[Dict[str, Any]] = []

        for pf in operation.fields:
            try:
                value = self._resolve_field(root_type_name, pf, None, ctx)
                key = pf.alias or pf.name
                data[key] = value
            except Exception as exc:
                errors.append({"field": pf.name, "message": str(exc)})
                data[pf.alias or pf.name] = None

        elapsed = (time.time() - start) * 1000
        result: Dict[str, Any] = {"data": data}
        if errors:
            result["errors"] = errors
        result["extensions"] = {"execution_time_ms": round(elapsed, 3)}
        return result

    def _resolve_field(
        self,
        type_name: str,
        parsed: ParsedField,
        parent: Any,
        ctx: ResolverContext,
    ) -> Any:
        value = self._resolver.resolve(type_name, parsed.name, parent, parsed.args, ctx)

        if parsed.sub_fields and value is not None:
            if isinstance(value, list):
                return [self._resolve_object(parsed, item, ctx) for item in value]
            return self._resolve_object(parsed, value, ctx)

        return value

    def _resolve_object(
        self,
        parsed: ParsedField,
        obj: Any,
        ctx: ResolverContext,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        obj_type = parsed.name  # simplified: use field name as type hint
        for sf in parsed.sub_fields:
            key = sf.alias or sf.name
            result[key] = self._resolve_field(obj_type, sf, obj, ctx)
        return result


# ---------------------------------------------------------------------------
# SC2-specific data store
# ---------------------------------------------------------------------------


class SC2DataStore:
    """In-memory data store for SC2 game data."""

    def __init__(self) -> None:
        self.games: List[Dict[str, Any]] = []
        self.players: Dict[str, Dict[str, Any]] = {}
        self.units: List[Dict[str, Any]] = []
        self.buildings: List[Dict[str, Any]] = []
        self.resources: Dict[str, Dict[str, int]] = {}
        self.strategies: Dict[str, str] = {}
        self.subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self.events: List[Dict[str, Any]] = []
        self.training_active: bool = False

    def add_game(self, game: Dict[str, Any]) -> str:
        game_id = game.get("id", uuid.uuid4().hex[:8])
        game["id"] = game_id
        game.setdefault("timestamp", time.time())
        self.games.append(game)
        self._emit("game_added", game)
        return game_id

    def add_player(self, player: Dict[str, Any]) -> str:
        pid = player.get("id", uuid.uuid4().hex[:8])
        player["id"] = pid
        self.players[pid] = player
        return pid

    def add_unit(self, unit: Dict[str, Any]) -> str:
        uid = unit.get("id", uuid.uuid4().hex[:8])
        unit["id"] = uid
        self.units.append(unit)
        self._emit("unit_created", unit)
        return uid

    def add_building(self, building: Dict[str, Any]) -> str:
        bid = building.get("id", uuid.uuid4().hex[:8])
        building["id"] = bid
        self.buildings.append(building)
        self._emit("building_placed", building)
        return bid

    def set_resources(self, player_id: str, minerals: int, vespene: int) -> None:
        self.resources[player_id] = {"minerals": minerals, "vespene": vespene}

    def subscribe(self, event_name: str, callback: Callable) -> str:
        sub_id = uuid.uuid4().hex[:8]
        self.subscriptions[event_name].append(callback)
        return sub_id

    def _emit(self, event_name: str, data: Any) -> None:
        event = {"event": event_name, "data": data, "timestamp": time.time()}
        self.events.append(event)
        for cb in self.subscriptions.get(event_name, []):
            try:
                cb(event)
            except Exception as exc:
                logger.warning("Subscription callback error: %s", exc)


# ---------------------------------------------------------------------------
# SC2 Schema Builder
# ---------------------------------------------------------------------------


class SC2Schema:
    """Builds the complete GraphQL schema for SC2 game data."""

    @staticmethod
    def build(store: SC2DataStore) -> Tuple[Schema, Resolver]:
        schema = Schema()
        resolver = Resolver()

        # --- Define types ---

        # Race enum
        race_enum = EnumType(
            name="Race",
            values=["ZERG", "TERRAN", "PROTOSS", "RANDOM"],
            description="StarCraft II playable races",
        )
        schema.add_type(race_enum)

        # GameResult enum
        result_enum = EnumType(
            name="GameResult",
            values=["WIN", "LOSS", "DRAW", "IN_PROGRESS"],
        )
        schema.add_type(result_enum)

        # Resource type
        resource_type = ObjectType(name="Resource", description="Player resources")
        resource_type.add_field(Field(name="minerals", type_name="Int"))
        resource_type.add_field(Field(name="vespene", type_name="Int"))
        resource_type.add_field(Field(name="supply_used", type_name="Int"))
        resource_type.add_field(Field(name="supply_cap", type_name="Int"))
        schema.add_type(resource_type)

        # Unit type
        unit_type = ObjectType(name="Unit", description="A game unit")
        unit_type.add_field(Field(name="id", type_name="ID", nullable=False))
        unit_type.add_field(Field(name="name", type_name="String", nullable=False))
        unit_type.add_field(Field(name="type", type_name="String"))
        unit_type.add_field(Field(name="health", type_name="Int"))
        unit_type.add_field(Field(name="max_health", type_name="Int"))
        unit_type.add_field(Field(name="shield", type_name="Int"))
        unit_type.add_field(Field(name="energy", type_name="Int"))
        unit_type.add_field(Field(name="position_x", type_name="Float"))
        unit_type.add_field(Field(name="position_y", type_name="Float"))
        unit_type.add_field(Field(name="owner", type_name="String"))
        schema.add_type(unit_type)

        # Building type
        building_type = ObjectType(name="Building", description="A structure/building")
        building_type.add_field(Field(name="id", type_name="ID", nullable=False))
        building_type.add_field(Field(name="name", type_name="String", nullable=False))
        building_type.add_field(Field(name="type", type_name="String"))
        building_type.add_field(Field(name="health", type_name="Int"))
        building_type.add_field(Field(name="is_completed", type_name="Boolean"))
        building_type.add_field(Field(name="position_x", type_name="Float"))
        building_type.add_field(Field(name="position_y", type_name="Float"))
        schema.add_type(building_type)

        # Player type
        player_type = ObjectType(name="Player", description="A game player or bot")
        player_type.add_field(Field(name="id", type_name="ID", nullable=False))
        player_type.add_field(Field(name="name", type_name="String", nullable=False))
        player_type.add_field(Field(name="race", type_name="Race"))
        player_type.add_field(Field(name="mmr", type_name="Int"))
        player_type.add_field(Field(name="wins", type_name="Int"))
        player_type.add_field(Field(name="losses", type_name="Int"))
        player_type.add_field(Field(name="win_rate", type_name="Float"))
        player_type.add_field(Field(name="resources", type_name="Resource"))
        player_type.add_field(Field(name="units", type_name="Unit", is_list=True))
        schema.add_type(player_type)

        # Game type
        game_type = ObjectType(name="Game", description="A SC2 game/match")
        game_type.add_field(Field(name="id", type_name="ID", nullable=False))
        game_type.add_field(Field(name="map_name", type_name="String"))
        game_type.add_field(Field(name="duration", type_name="Float"))
        game_type.add_field(Field(name="result", type_name="GameResult"))
        game_type.add_field(Field(name="players", type_name="Player", is_list=True))
        game_type.add_field(Field(name="timestamp", type_name="Float"))
        game_type.add_field(Field(name="strategy", type_name="String"))
        game_type.add_field(Field(name="replay_path", type_name="String"))
        schema.add_type(game_type)

        # PlayerStats type
        stats_type = ObjectType(
            name="PlayerStats", description="Aggregated player statistics"
        )
        stats_type.add_field(Field(name="total_games", type_name="Int"))
        stats_type.add_field(Field(name="wins", type_name="Int"))
        stats_type.add_field(Field(name="losses", type_name="Int"))
        stats_type.add_field(Field(name="win_rate", type_name="Float"))
        stats_type.add_field(Field(name="avg_game_duration", type_name="Float"))
        stats_type.add_field(Field(name="most_played_strategy", type_name="String"))
        stats_type.add_field(Field(name="favorite_unit", type_name="String"))
        schema.add_type(stats_type)

        # GameEvent type (for subscriptions)
        event_type = ObjectType(name="GameEvent", description="Real-time game event")
        event_type.add_field(Field(name="event", type_name="String"))
        event_type.add_field(Field(name="data", type_name="String"))
        event_type.add_field(Field(name="timestamp", type_name="Float"))
        schema.add_type(event_type)

        # --- Query root ---

        query_root = ObjectType(name="Query")
        query_root.add_field(
            Field(
                name="gameState",
                type_name="Game",
                description="Current game state",
            )
        )
        query_root.add_field(
            Field(
                name="games",
                type_name="Game",
                is_list=True,
                description="Match history",
                args={"limit": "Int", "offset": "Int", "result": "GameResult"},
            )
        )
        query_root.add_field(
            Field(
                name="game",
                type_name="Game",
                description="Single game by ID",
                args={"id": "ID!"},
            )
        )
        query_root.add_field(
            Field(
                name="units",
                type_name="Unit",
                is_list=True,
                description="List of units",
                args={"owner": "String", "type": "String", "limit": "Int"},
            )
        )
        query_root.add_field(
            Field(
                name="buildings",
                type_name="Building",
                is_list=True,
                args={"type": "String"},
            )
        )
        query_root.add_field(
            Field(
                name="player",
                type_name="Player",
                args={"id": "ID!"},
            )
        )
        query_root.add_field(
            Field(
                name="players",
                type_name="Player",
                is_list=True,
            )
        )
        query_root.add_field(
            Field(
                name="playerStats",
                type_name="PlayerStats",
                args={"playerId": "ID!"},
            )
        )
        query_root.add_field(
            Field(
                name="resources",
                type_name="Resource",
                args={"playerId": "ID!"},
            )
        )
        schema.set_query_type(query_root)

        # --- Mutation root ---

        mutation_root = ObjectType(name="Mutation")
        mutation_root.add_field(
            Field(
                name="setStrategy",
                type_name="String",
                args={"strategy": "String!", "playerId": "ID"},
            )
        )
        mutation_root.add_field(
            Field(
                name="configureBot",
                type_name="Boolean",
                args={
                    "aggression": "Float",
                    "expansion_priority": "Float",
                    "tech_priority": "Float",
                },
            )
        )
        mutation_root.add_field(
            Field(
                name="startTraining",
                type_name="Boolean",
                args={"episodes": "Int", "opponent": "String"},
            )
        )
        mutation_root.add_field(
            Field(
                name="stopTraining",
                type_name="Boolean",
            )
        )
        mutation_root.add_field(
            Field(
                name="recordGame",
                type_name="Game",
                args={
                    "map_name": "String!",
                    "result": "GameResult!",
                    "duration": "Float",
                    "strategy": "String",
                },
            )
        )
        schema.set_mutation_type(mutation_root)

        # --- Subscription root ---

        sub_root = ObjectType(name="Subscription")
        sub_root.add_field(
            Field(
                name="gameEvents",
                type_name="GameEvent",
                description="Real-time game events via WebSocket",
            )
        )
        sub_root.add_field(
            Field(
                name="unitCreated",
                type_name="Unit",
            )
        )
        sub_root.add_field(
            Field(
                name="buildingPlaced",
                type_name="Building",
            )
        )
        schema.set_subscription_type(sub_root)

        # --- Register resolvers ---

        # Query resolvers
        resolver.register(
            "Query",
            "gameState",
            lambda p, a, c: store.games[-1] if store.games else None,
        )

        def resolve_games(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> List[Dict]:
            games = list(store.games)
            result_filter = args.get("result")
            if result_filter:
                games = [g for g in games if g.get("result") == result_filter]
            offset = args.get("offset", 0)
            limit = args.get("limit", 50)
            return games[offset : offset + limit]

        resolver.register("Query", "games", resolve_games)

        def resolve_game(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> Optional[Dict]:
            gid = args.get("id", "")
            for g in store.games:
                if g.get("id") == gid:
                    return g
            return None

        resolver.register("Query", "game", resolve_game)

        def resolve_units(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> List[Dict]:
            units = list(store.units)
            owner = args.get("owner")
            unit_type = args.get("type")
            if owner:
                units = [u for u in units if u.get("owner") == owner]
            if unit_type:
                units = [u for u in units if u.get("type") == unit_type]
            limit = args.get("limit", 100)
            return units[:limit]

        resolver.register("Query", "units", resolve_units)

        def resolve_buildings(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> List[Dict]:
            buildings = list(store.buildings)
            btype = args.get("type")
            if btype:
                buildings = [b for b in buildings if b.get("type") == btype]
            return buildings

        resolver.register("Query", "buildings", resolve_buildings)

        def resolve_player(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> Optional[Dict]:
            pid = args.get("id", "")
            return store.players.get(pid)

        resolver.register("Query", "player", resolve_player)
        resolver.register(
            "Query", "players", lambda p, a, c: list(store.players.values())
        )

        def resolve_player_stats(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> Dict[str, Any]:
            pid = args.get("playerId", "")
            player = store.players.get(pid, {})
            player_games = [
                g
                for g in store.games
                if any(pl.get("id") == pid for pl in g.get("players", []))
            ]
            wins = sum(1 for g in player_games if g.get("result") == "WIN")
            losses = sum(1 for g in player_games if g.get("result") == "LOSS")
            total = len(player_games)
            durations = [
                g.get("duration", 0) for g in player_games if g.get("duration")
            ]
            strategies = [g.get("strategy", "unknown") for g in player_games]
            strategy_counts: Dict[str, int] = defaultdict(int)
            for s in strategies:
                strategy_counts[s] += 1
            most_played = (
                max(strategy_counts, key=strategy_counts.get, default="none")
                if strategy_counts
                else "none"
            )

            return {
                "total_games": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / max(total, 1) * 100, 2),
                "avg_game_duration": round(sum(durations) / max(len(durations), 1), 1),
                "most_played_strategy": most_played,
                "favorite_unit": player.get("favorite_unit", "Zergling"),
            }

        resolver.register("Query", "playerStats", resolve_player_stats)

        def resolve_resources(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> Dict[str, Any]:
            pid = args.get("playerId", "")
            return store.resources.get(
                pid, {"minerals": 0, "vespene": 0, "supply_used": 0, "supply_cap": 0}
            )

        resolver.register("Query", "resources", resolve_resources)

        # Mutation resolvers
        def resolve_set_strategy(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> str:
            strategy = args.get("strategy", "balanced")
            pid = args.get("playerId", "default")
            store.strategies[pid] = strategy
            logger.info("Strategy set to '%s' for player '%s'", strategy, pid)
            return f"Strategy set to: {strategy}"

        resolver.register("Mutation", "setStrategy", resolve_set_strategy)

        def resolve_configure_bot(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> bool:
            logger.info(
                "Bot configured: aggression=%.2f expansion=%.2f tech=%.2f",
                args.get("aggression", 0.5),
                args.get("expansion_priority", 0.5),
                args.get("tech_priority", 0.5),
            )
            return True

        resolver.register("Mutation", "configureBot", resolve_configure_bot)

        def resolve_start_training(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> bool:
            episodes = args.get("episodes", 100)
            opponent = args.get("opponent", "built-in-ai")
            store.training_active = True
            logger.info("Training started: %d episodes vs %s", episodes, opponent)
            return True

        resolver.register("Mutation", "startTraining", resolve_start_training)

        def resolve_stop_training(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> bool:
            store.training_active = False
            logger.info("Training stopped")
            return True

        resolver.register("Mutation", "stopTraining", resolve_stop_training)

        def resolve_record_game(
            parent: Any, args: Dict[str, Any], ctx: ResolverContext
        ) -> Dict[str, Any]:
            game: Dict[str, Any] = {
                "map_name": args.get("map_name", "Unknown"),
                "result": args.get("result", "DRAW"),
                "duration": args.get("duration", 0.0),
                "strategy": args.get("strategy", "unknown"),
                "players": [],
            }
            gid = store.add_game(game)
            game["id"] = gid
            return game

        resolver.register("Mutation", "recordGame", resolve_record_game)

        return schema, resolver


# ---------------------------------------------------------------------------
# GraphQL Server
# ---------------------------------------------------------------------------


class GraphQLServer:
    """
    Lightweight GraphQL server that processes queries against the SC2 schema.
    In production this would serve over HTTP/WebSocket; here we execute in-process.
    """

    def __init__(self, store: Optional[SC2DataStore] = None) -> None:
        self._store = store or SC2DataStore()
        self._schema, self._resolver = SC2Schema.build(self._store)
        self._parser = QueryParser()
        self._engine = ExecutionEngine(self._schema, self._resolver)
        self._request_count: int = 0
        self._subscription_handlers: Dict[str, List[Callable]] = defaultdict(list)

    @property
    def store(self) -> SC2DataStore:
        return self._store

    @property
    def schema(self) -> Schema:
        return self._schema

    def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        context: Optional[ResolverContext] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query string and return the result."""
        self._request_count += 1
        try:
            operation = self._parser.parse(query, variables)
            return self._engine.execute(operation, context)
        except Exception as exc:
            return {
                "data": None,
                "errors": [{"message": str(exc)}],
            }

    def introspect(self) -> str:
        """Return the schema definition as a string."""
        return self._schema.to_schema_str()

    def subscribe(self, event_name: str, callback: Callable) -> str:
        """Subscribe to real-time game events."""
        sub_id = self._store.subscribe(event_name, callback)
        return sub_id

    @property
    def request_count(self) -> int:
        return self._request_count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "request_count": self._request_count,
            "resolver_count": self._resolver.registered_count,
            "games_stored": len(self._store.games),
            "players_stored": len(self._store.players),
            "units_stored": len(self._store.units),
            "buildings_stored": len(self._store.buildings),
            "events_emitted": len(self._store.events),
            "training_active": self._store.training_active,
        }


# ---------------------------------------------------------------------------
# WebSocket subscription simulator
# ---------------------------------------------------------------------------


class WebSocketSubscriptionSimulator:
    """Simulates WebSocket-based subscriptions for real-time events."""

    def __init__(self, server: GraphQLServer) -> None:
        self._server = server
        self._active_subs: Dict[str, Callable] = {}
        self._received: List[Dict[str, Any]] = []

    def subscribe(self, event_name: str) -> str:
        def handler(event: Dict[str, Any]) -> None:
            self._received.append(event)
            logger.debug("WS event received: %s", event.get("event"))

        sub_id = self._server.subscribe(event_name, handler)
        self._active_subs[sub_id] = handler
        return sub_id

    def get_received(self) -> List[Dict[str, Any]]:
        return list(self._received)

    def clear(self) -> None:
        self._received.clear()

    @property
    def active_count(self) -> int:
        return len(self._active_subs)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate GraphQL API for SC2 game data."""
    print("=" * 70)
    print("Phase 665: GraphQL API for SC2 Game Data")
    print("=" * 70)

    server = GraphQLServer()
    store = server.store

    # --- Seed data ---
    print("\n[Setup] Seeding game data...")

    pid1 = store.add_player(
        {
            "name": "CommanderBot",
            "race": "ZERG",
            "mmr": 4200,
            "wins": 45,
            "losses": 20,
            "win_rate": 69.2,
            "favorite_unit": "Roach",
        }
    )
    pid2 = store.add_player(
        {
            "name": "OpponentAI",
            "race": "PROTOSS",
            "mmr": 3800,
            "wins": 30,
            "losses": 35,
            "win_rate": 46.2,
        }
    )

    store.set_resources(pid1, minerals=1500, vespene=800)
    store.set_resources(pid2, minerals=1200, vespene=600)

    for i in range(5):
        store.add_game(
            {
                "map_name": [
                    "Equilibrium",
                    "GoldenAura",
                    "HardLead",
                    "Oceanborn",
                    "SiteDelta",
                ][i],
                "result": "WIN" if i % 2 == 0 else "LOSS",
                "duration": 300.0 + i * 60,
                "strategy": ["rush", "macro", "timing", "turtle", "all-in"][i],
                "players": [{"id": pid1}, {"id": pid2}],
            }
        )

    for name, utype in [
        ("Zergling", "light"),
        ("Roach", "armored"),
        ("Hydralisk", "ranged"),
        ("Baneling", "light"),
        ("Mutalisk", "flyer"),
    ]:
        for j in range(3):
            store.add_unit(
                {
                    "name": f"{name}_{j}",
                    "type": utype,
                    "health": 80 + j * 10,
                    "max_health": 100,
                    "shield": 0,
                    "energy": 0,
                    "position_x": 30.0 + j * 5,
                    "position_y": 40.0 + j * 3,
                    "owner": "CommanderBot",
                }
            )

    for bname, btype in [
        ("Hatchery", "base"),
        ("SpawningPool", "tech"),
        ("Extractor", "resource"),
        ("RoachWarren", "tech"),
    ]:
        store.add_building(
            {
                "name": bname,
                "type": btype,
                "health": 1500,
                "is_completed": True,
                "position_x": 25.0,
                "position_y": 25.0,
            }
        )

    # --- Set up WebSocket subscription ---
    ws_sim = WebSocketSubscriptionSimulator(server)
    ws_sim.subscribe("game_added")
    ws_sim.subscribe("unit_created")

    # --- Execute queries ---

    print("\n--- Query: Game State ---")
    result = server.execute(
        "query { gameState { id, map_name, result, duration, strategy } }"
    )
    print(json.dumps(result, indent=2))

    print("\n--- Query: Match History ---")
    result = server.execute(
        "query { games(limit: 3) { id, map_name, result, strategy } }"
    )
    print(json.dumps(result, indent=2))

    print("\n--- Query: Units (filtered) ---")
    result = server.execute(
        'query { units(owner: "CommanderBot", limit: 5) { id, name, type, health } }'
    )
    print(json.dumps(result, indent=2))

    print("\n--- Query: Buildings ---")
    result = server.execute(
        'query { buildings(type: "tech") { id, name, is_completed } }'
    )
    print(json.dumps(result, indent=2))

    print("\n--- Query: Player ---")
    result = server.execute(
        f'query {{ player(id: "{pid1}") {{ id, name, race, mmr, win_rate }} }}'
    )
    print(json.dumps(result, indent=2))

    print("\n--- Query: Player Stats ---")
    result = server.execute(
        f'query {{ playerStats(playerId: "{pid1}") {{ total_games, wins, losses, win_rate, avg_game_duration, most_played_strategy }} }}'
    )
    print(json.dumps(result, indent=2))

    print("\n--- Query: Resources ---")
    result = server.execute(
        f'query {{ resources(playerId: "{pid1}") {{ minerals, vespene }} }}'
    )
    print(json.dumps(result, indent=2))

    # --- Execute mutations ---

    print("\n--- Mutation: Set Strategy ---")
    result = server.execute('mutation { setStrategy(strategy: "aggressive-timing") }')
    print(json.dumps(result, indent=2))

    print("\n--- Mutation: Configure Bot ---")
    result = server.execute(
        "mutation { configureBot(aggression: 0.8, expansion_priority: 0.3, tech_priority: 0.6) }"
    )
    print(json.dumps(result, indent=2))

    print("\n--- Mutation: Start Training ---")
    result = server.execute(
        'mutation { startTraining(episodes: 500, opponent: "very-hard-ai") }'
    )
    print(json.dumps(result, indent=2))

    print("\n--- Mutation: Record Game ---")
    result = server.execute(
        'mutation { recordGame(map_name: "Equilibrium", result: "WIN", duration: 420.0, strategy: "roach-timing") }'
    )
    print(json.dumps(result, indent=2))

    print("\n--- Mutation: Stop Training ---")
    result = server.execute("mutation { stopTraining }")
    print(json.dumps(result, indent=2))

    # --- Schema introspection ---
    print("\n--- Schema Introspection (first 40 lines) ---")
    schema_str = server.introspect()
    for line in schema_str.split("\n")[:40]:
        print(f"  {line}")
    print("  ...")

    # --- Subscription events ---
    print("\n--- WebSocket Subscription Events ---")
    ws_events = ws_sim.get_received()
    print(f"  Total events received: {len(ws_events)}")
    for ev in ws_events[:5]:
        print(f"    {ev['event']}: {json.dumps(ev['data'].get('id', 'N/A'))}")

    # --- Server stats ---
    print("\n--- Server Stats ---")
    stats = server.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 70)
    print("Phase 665 GraphQL API demonstration complete.")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()

# Phase 665: GraphQL registered
