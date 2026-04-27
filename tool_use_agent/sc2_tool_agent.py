"""
Phase 631: Tool-Use Agent for SC2 Strategic Decision Making

Tool-augmented AI agent that uses structured tools for StarCraft II
strategic analysis.  Implements a ReAct (Reason-Act-Observe) loop where
the agent reasons about the game state, selects and calls appropriate
tools, observes the results, and reasons again until a final decision
is reached.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Definition
# ============================================================================


@dataclass
class Tool:
    """A single callable tool that the agent can invoke.

    Each tool wraps a pure function with typed parameters and a structured
    return value.  The ``description`` is used by the agent's reasoning
    step to decide when this tool is appropriate.
    """

    name: str
    description: str
    parameters: Dict[str, str]  # param_name -> type hint string
    fn: Callable[..., Dict[str, Any]]  # the actual implementation
    category: str = "general"
    examples: List[str] = field(default_factory=list)

    def call(self, **kwargs: Any) -> Dict[str, Any]:
        """Invoke the tool with keyword arguments."""
        start = time.perf_counter()
        try:
            result = self.fn(**kwargs)
            elapsed = time.perf_counter() - start
            result["_meta"] = {
                "tool": self.name,
                "elapsed_ms": round(elapsed * 1000, 2),
            }
            return result
        except Exception as exc:
            return {"error": str(exc), "_meta": {"tool": self.name}}

    def signature(self) -> str:
        params = ", ".join(f"{k}: {v}" for k, v in self.parameters.items())
        return f"{self.name}({params})"

    def __repr__(self) -> str:
        return f"Tool({self.name!r})"


# ============================================================================
# Tool Registry
# ============================================================================


class ToolRegistry:
    """Central registry of all available tools.

    Tools can be looked up by name or filtered by category.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Add a tool to the registry."""
        if tool.name in self._tools:
            logger.warning("Overwriting existing tool '%s'.", tool.name)
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def list_by_category(self, category: str) -> List[Tool]:
        return [t for t in self._tools.values() if t.category == category]

    def tool_descriptions(self) -> str:
        """Format all tool descriptions for the agent prompt."""
        lines: List[str] = []
        for tool in self._tools.values():
            lines.append(f"- {tool.signature()}: {tool.description}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ============================================================================
# Tool Call Parser
# ============================================================================


class ToolCallParser:
    """Parses structured tool-call strings from the agent's reasoning output.

    Supported formats:
        CALL: tool_name(param1=value1, param2=value2)
        ACTION: tool_name {"param1": value1, "param2": value2}
    """

    # Pattern: CALL: name(k=v, k=v, ...)
    _CALL_PATTERN = re.compile(r"CALL:\s*(\w+)\(([^)]*)\)", re.IGNORECASE)
    # Pattern: ACTION: name {json}
    _ACTION_PATTERN = re.compile(
        r"ACTION:\s*(\w+)\s*(\{.*\})", re.IGNORECASE | re.DOTALL
    )

    @classmethod
    def parse(cls, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Try to extract a tool call from text.

        Returns (tool_name, kwargs) or None.
        """
        # Try CALL format first
        match = cls._CALL_PATTERN.search(text)
        if match:
            name = match.group(1)
            raw_args = match.group(2).strip()
            kwargs = cls._parse_kv_args(raw_args)
            return (name, kwargs)

        # Try ACTION format
        match = cls._ACTION_PATTERN.search(text)
        if match:
            name = match.group(1)
            try:
                kwargs = json.loads(match.group(2))
                return (name, kwargs)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON args in ACTION call.")
                return None

        return None

    @staticmethod
    def _parse_kv_args(raw: str) -> Dict[str, Any]:
        """Parse 'key=value, key=value' format into a dict."""
        if not raw:
            return {}
        result: Dict[str, Any] = {}
        for part in raw.split(","):
            part = part.strip()
            if "=" not in part:
                continue
            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            # Try numeric conversion
            try:
                val = int(val)
            except (ValueError, TypeError):
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    pass
            result[key] = val
        return result


# ============================================================================
# Tool Executor
# ============================================================================


class ToolExecutor:
    """Executes tool calls with validation and logging."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.call_history: List[Dict[str, Any]] = []

    def execute(self, tool_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Look up and execute a tool, recording the call."""
        tool = self.registry.get(tool_name)
        if tool is None:
            result = {"error": f"Unknown tool: {tool_name}"}
            self.call_history.append(
                {
                    "tool": tool_name,
                    "args": kwargs,
                    "result": result,
                }
            )
            return result

        result = tool.call(**kwargs)
        self.call_history.append(
            {
                "tool": tool_name,
                "args": kwargs,
                "result": result,
            }
        )
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.call_history)

    def clear_history(self) -> None:
        self.call_history.clear()


# ============================================================================
# SC2-Specific Tools
# ============================================================================


def _calculate_army_value(
    unit_counts: str,
    include_upgrades: bool = False,
) -> Dict[str, Any]:
    """Calculate total army mineral/gas value from unit counts.

    Args:
        unit_counts: Comma-separated 'UnitName:Count' pairs.
        include_upgrades: Whether to add estimated upgrade costs.
    """
    unit_costs: Dict[str, Tuple[int, int]] = {
        "Zergling": (25, 0),
        "Baneling": (50, 25),
        "Roach": (75, 25),
        "Ravager": (100, 75),
        "Hydralisk": (100, 50),
        "Lurker": (150, 100),
        "Mutalisk": (100, 100),
        "Corruptor": (150, 100),
        "BroodLord": (300, 250),
        "Ultralisk": (300, 200),
        "Viper": (100, 200),
        "Infestor": (100, 150),
        "Queen": (150, 0),
        "Overlord": (100, 0),
        "Overseer": (150, 50),
        "SwarmHost": (150, 100),
        "Marine": (50, 0),
        "Marauder": (100, 25),
        "SiegeTank": (150, 125),
        "Medivac": (100, 100),
        "Viking": (150, 75),
        "Liberator": (150, 150),
        "Thor": (300, 200),
        "Battlecruiser": (400, 300),
        "Zealot": (100, 0),
        "Stalker": (125, 50),
        "Immortal": (275, 100),
        "Colossus": (300, 200),
        "VoidRay": (250, 150),
        "Carrier": (350, 250),
        "HighTemplar": (50, 150),
        "Archon": (100, 300),
    }

    total_minerals = 0
    total_gas = 0
    parsed: Dict[str, int] = {}
    for pair in unit_counts.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        name, cnt_str = pair.split(":", 1)
        name = name.strip()
        try:
            cnt = int(cnt_str.strip())
        except ValueError:
            continue
        m, g = unit_costs.get(name, (100, 50))
        total_minerals += m * cnt
        total_gas += g * cnt
        parsed[name] = cnt

    upgrade_cost = 0
    if include_upgrades:
        upgrade_cost = len(parsed) * 150  # rough estimate
        total_minerals += upgrade_cost

    return {
        "total_minerals": total_minerals,
        "total_gas": total_gas,
        "total_value": total_minerals + total_gas,
        "unit_breakdown": parsed,
        "upgrade_estimate": upgrade_cost,
    }


def _check_supply(
    supply_used: int,
    supply_cap: int,
    army_supply: int,
    worker_count: int,
) -> Dict[str, Any]:
    """Analyze supply efficiency and recommend adjustments."""
    free_supply = supply_cap - supply_used
    supply_ratio = supply_used / max(supply_cap, 1)
    worker_ratio = worker_count / max(supply_used, 1)
    army_ratio = army_supply / max(supply_used, 1)

    warnings: List[str] = []
    recommendations: List[str] = []

    if free_supply <= 2 and supply_cap < 200:
        warnings.append("SUPPLY_BLOCKED: almost no free supply")
        recommendations.append("Build 2 Overlords immediately")
    elif free_supply <= 6:
        warnings.append("LOW_SUPPLY: supply getting tight")
        recommendations.append("Queue 1 Overlord")

    if supply_cap >= 200:
        recommendations.append("Max supply reached, no more Overlords needed")

    if worker_ratio > 0.55:
        warnings.append("OVER_DRONED: too many workers relative to army")
        recommendations.append("Pause Drone production, build army")
    elif worker_ratio < 0.30 and supply_used > 50:
        warnings.append("UNDER_DRONED: army-heavy but weak economy")
        recommendations.append("Build more Drones before next expansion")

    return {
        "supply_used": supply_used,
        "supply_cap": supply_cap,
        "free_supply": free_supply,
        "supply_efficiency": round(supply_ratio, 2),
        "worker_ratio": round(worker_ratio, 2),
        "army_ratio": round(army_ratio, 2),
        "warnings": warnings,
        "recommendations": recommendations,
    }


def _estimate_timing(
    target_unit: str,
    current_minerals: int,
    current_gas: int,
    income_minerals: int,
    income_gas: int,
) -> Dict[str, Any]:
    """Estimate when a target unit or tech can be afforded.

    Args:
        target_unit: Name of the unit/building to estimate.
        current_minerals: Current mineral count.
        current_gas: Current gas count.
        income_minerals: Mineral income per minute.
        income_gas: Gas income per minute.
    """
    costs: Dict[str, Tuple[int, int, int]] = {
        # (minerals, gas, build_time_seconds)
        "Hatchery": (300, 0, 71),
        "Lair": (150, 100, 57),
        "Hive": (200, 150, 71),
        "SpawningPool": (200, 0, 46),
        "RoachWarren": (150, 0, 39),
        "HydraliskDen": (100, 100, 29),
        "Spire": (200, 200, 71),
        "UltraliskCavern": (150, 200, 46),
        "InfestationPit": (100, 100, 36),
        "Ultralisk": (300, 200, 39),
        "BroodLord": (300, 250, 34),
        "Mutalisk": (100, 100, 24),
        "Lurker": (150, 100, 18),
    }

    if target_unit not in costs:
        return {
            "target": target_unit,
            "error": f"Unknown unit/building: {target_unit}",
            "known_targets": list(costs.keys()),
        }

    m_cost, g_cost, build_time = costs[target_unit]
    m_deficit = max(0, m_cost - current_minerals)
    g_deficit = max(0, g_cost - current_gas)

    if income_minerals > 0:
        m_wait = m_deficit / income_minerals * 60  # seconds
    else:
        m_wait = float("inf") if m_deficit > 0 else 0

    if income_gas > 0:
        g_wait = g_deficit / income_gas * 60
    else:
        g_wait = float("inf") if g_deficit > 0 else 0

    gather_time = max(m_wait, g_wait)
    total_time = gather_time + build_time

    return {
        "target": target_unit,
        "cost": {"minerals": m_cost, "gas": g_cost},
        "deficit": {"minerals": m_deficit, "gas": g_deficit},
        "gather_seconds": round(gather_time, 1),
        "build_seconds": build_time,
        "total_seconds": round(total_time, 1),
        "ready_in": (
            f"{total_time / 60:.1f} minutes"
            if total_time > 60
            else f"{total_time:.0f} seconds"
        ),
        "can_afford_now": m_deficit == 0 and g_deficit == 0,
    }


def _suggest_counter(
    enemy_units: str,
    player_race: str = "Zerg",
) -> Dict[str, Any]:
    """Suggest counter units based on observed enemy composition.

    Args:
        enemy_units: Comma-separated list of enemy unit names.
        player_race: The player's race (default Zerg).
    """
    counters: Dict[str, Dict[str, List[str]]] = {
        "Zerg": {
            "Marine": ["Baneling", "Zergling"],
            "Marauder": ["Zergling", "Mutalisk"],
            "SiegeTank": ["Mutalisk", "Ravager", "SwarmHost"],
            "Medivac": ["Corruptor", "Hydralisk"],
            "Liberator": ["Corruptor", "Viper"],
            "Thor": ["Zergling", "Broodlord"],
            "Battlecruiser": ["Corruptor", "Viper", "Infestor"],
            "Zealot": ["Roach", "Baneling"],
            "Stalker": ["Zergling", "Hydralisk"],
            "Immortal": ["Zergling", "Mutalisk"],
            "Colossus": ["Corruptor", "Viper"],
            "VoidRay": ["Hydralisk", "Corruptor", "Queen"],
            "Carrier": ["Corruptor", "Viper", "Hydralisk"],
            "HighTemplar": ["Ultralisk", "Ghost"],
            "Archon": ["Roach", "Hydralisk"],
            "Phoenix": ["Hydralisk", "Queen"],
            "DarkTemplar": ["Overseer", "Zergling"],
            "Banshee": ["Queen", "Hydralisk", "Overseer"],
            "Hellion": ["Roach", "Queen"],
        },
        "Terran": {
            "Zergling": ["Hellion", "Hellbat"],
            "Roach": ["Marauder", "SiegeTank"],
            "Mutalisk": ["Marine", "Thor", "Liberator"],
            "Ultralisk": ["Marauder", "Liberator", "Ghost"],
        },
        "Protoss": {
            "Zergling": ["Zealot", "Adept", "Sentry"],
            "Roach": ["Immortal", "Stalker"],
            "Mutalisk": ["Phoenix", "Stalker", "Archon"],
            "Ultralisk": ["Immortal", "VoidRay"],
        },
    }

    race_counters = counters.get(player_race, counters["Zerg"])
    suggestions: Dict[str, List[str]] = {}
    priority_units: Dict[str, int] = {}

    for unit in enemy_units.split(","):
        unit = unit.strip()
        if not unit:
            continue
        unit_counters = race_counters.get(unit, ["Hydralisk"])
        suggestions[unit] = unit_counters
        for cu in unit_counters:
            priority_units[cu] = priority_units.get(cu, 0) + 1

    # Rank by frequency
    ranked = sorted(priority_units.items(), key=lambda x: x[1], reverse=True)
    top_units = [u for u, _ in ranked[:5]]

    return {
        "enemy_units_analyzed": list(suggestions.keys()),
        "counter_map": suggestions,
        "recommended_composition": top_units,
        "primary_counter": top_units[0] if top_units else "Zergling",
        "composition_note": _composition_note(top_units),
    }


def _composition_note(units: List[str]) -> str:
    """Generate a short note about the suggested composition."""
    if not units:
        return "No specific counters identified. Build a balanced army."
    air_units = {"Corruptor", "Mutalisk", "Viper", "Phoenix", "Viking", "Liberator"}
    has_air = any(u in air_units for u in units)
    has_splash = any(
        u in {"Baneling", "Lurker", "Colossus", "SiegeTank"} for u in units
    )
    notes: List[str] = []
    if has_air:
        notes.append("Include anti-air units")
    if has_splash:
        notes.append("Spread units to minimize splash damage")
    if not notes:
        notes.append("Standard ground composition should work well")
    return ". ".join(notes) + "."


# ── Build the default SC2 tool registry ──────────────────────────────────────


def build_sc2_tool_registry() -> ToolRegistry:
    """Create and populate the default SC2 tool registry."""
    registry = ToolRegistry()

    registry.register(
        Tool(
            name="calculate_army_value",
            description="Calculate total mineral/gas value of an army composition",
            parameters={"unit_counts": "str", "include_upgrades": "bool"},
            fn=_calculate_army_value,
            category="economy",
            examples=["CALL: calculate_army_value(unit_counts=Zergling:20,Roach:8)"],
        )
    )

    registry.register(
        Tool(
            name="check_supply",
            description="Analyze supply usage and detect supply blocks or imbalances",
            parameters={
                "supply_used": "int",
                "supply_cap": "int",
                "army_supply": "int",
                "worker_count": "int",
            },
            fn=_check_supply,
            category="macro",
            examples=[
                "CALL: check_supply(supply_used=80, supply_cap=84, army_supply=40, worker_count=44)"
            ],
        )
    )

    registry.register(
        Tool(
            name="estimate_timing",
            description="Estimate when a unit or building can be afforded and completed",
            parameters={
                "target_unit": "str",
                "current_minerals": "int",
                "current_gas": "int",
                "income_minerals": "int",
                "income_gas": "int",
            },
            fn=_estimate_timing,
            category="planning",
            examples=[
                "CALL: estimate_timing(target_unit=Hive, current_minerals=400, current_gas=200, income_minerals=1000, income_gas=300)"
            ],
        )
    )

    registry.register(
        Tool(
            name="suggest_counter",
            description="Suggest counter units based on observed enemy composition",
            parameters={"enemy_units": "str", "player_race": "str"},
            fn=_suggest_counter,
            category="strategy",
            examples=[
                "CALL: suggest_counter(enemy_units=Marine,SiegeTank,Medivac, player_race=Zerg)"
            ],
        )
    )

    return registry


# ============================================================================
# ReAct Loop State
# ============================================================================


class ReActStep(Enum):
    REASON = "reason"
    ACT = "act"
    OBSERVE = "observe"
    FINAL = "final"


@dataclass
class ReActTrace:
    """Records one step in the ReAct loop."""

    step_type: ReActStep
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# Tool-Use Agent
# ============================================================================


class ToolUseAgent:
    """AI agent that uses a ReAct loop with structured tool calls for SC2.

    The agent cycle:
    1. REASON: Analyze the game state and decide what information is needed.
    2. ACT:    Select and call a tool to get that information.
    3. OBSERVE: Incorporate the tool result into the reasoning.
    4. Repeat until a FINAL decision is reached or max steps are hit.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        max_steps: int = 5,
        verbose: bool = True,
    ) -> None:
        self.registry = registry
        self.executor = ToolExecutor(registry)
        self.max_steps = max_steps
        self.verbose = verbose
        self.trace: List[ReActTrace] = []
        self._rules: List[Callable[[Dict[str, Any]], Optional[str]]] = []
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Register built-in reasoning rules."""
        self._rules.append(self._rule_supply_check)
        self._rules.append(self._rule_counter_check)
        self._rules.append(self._rule_timing_check)
        self._rules.append(self._rule_army_value_check)

    # ── Reasoning Rules ──────────────────────────────────────────────────

    @staticmethod
    def _rule_supply_check(game_state: Dict[str, Any]) -> Optional[str]:
        """Trigger supply analysis when supply is tight."""
        used = game_state.get("supply_used", 0)
        cap = game_state.get("supply_cap", 200)
        if cap > 0 and (cap - used) < 8:
            army = game_state.get("army_supply", 0)
            workers = game_state.get("worker_count", 0)
            return (
                f"CALL: check_supply(supply_used={used}, supply_cap={cap}, "
                f"army_supply={army}, worker_count={workers})"
            )
        return None

    @staticmethod
    def _rule_counter_check(game_state: Dict[str, Any]) -> Optional[str]:
        """Trigger counter suggestion when enemy units are known."""
        enemy = game_state.get("enemy_units", [])
        if enemy:
            units_str = ",".join(enemy)
            race = game_state.get("player_race", "Zerg")
            return f"CALL: suggest_counter(enemy_units={units_str}, player_race={race})"
        return None

    @staticmethod
    def _rule_timing_check(game_state: Dict[str, Any]) -> Optional[str]:
        """Trigger timing estimate for a planned tech target."""
        target = game_state.get("next_tech_target")
        if target:
            m = game_state.get("minerals", 0)
            g = game_state.get("vespene", 0)
            mi = game_state.get("mineral_income", 500)
            gi = game_state.get("gas_income", 150)
            return (
                f"CALL: estimate_timing(target_unit={target}, "
                f"current_minerals={m}, current_gas={g}, "
                f"income_minerals={mi}, income_gas={gi})"
            )
        return None

    @staticmethod
    def _rule_army_value_check(game_state: Dict[str, Any]) -> Optional[str]:
        """Trigger army value calculation when unit counts are available."""
        counts = game_state.get("own_unit_counts")
        if counts:
            return f"CALL: calculate_army_value(unit_counts={counts})"
        return None

    # ── Core ReAct Loop ──────────────────────────────────────────────────

    def run(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ReAct loop on the given game state.

        Returns a decision dict with strategy, actions, and reasoning trace.
        """
        self.trace.clear()
        self.executor.clear_history()

        observations: List[Dict[str, Any]] = []
        tool_calls_made: List[str] = []

        for step in range(self.max_steps):
            # ── REASON ───────────────────────────────────────────────
            reason_text, action_text = self._reason(
                game_state, observations, tool_calls_made
            )
            self.trace.append(ReActTrace(ReActStep.REASON, reason_text))
            if self.verbose:
                logger.info("[Step %d] REASON: %s", step + 1, reason_text)

            if action_text is None:
                # No more tool calls needed, produce final answer
                break

            # ── ACT ──────────────────────────────────────────────────
            parsed = ToolCallParser.parse(action_text)
            if parsed is None:
                self.trace.append(
                    ReActTrace(ReActStep.ACT, f"Parse failed: {action_text}")
                )
                break

            tool_name, kwargs = parsed
            self.trace.append(
                ReActTrace(
                    ReActStep.ACT,
                    action_text,
                    tool_name=tool_name,
                    tool_args=kwargs,
                )
            )
            if self.verbose:
                logger.info("[Step %d] ACT: %s(%s)", step + 1, tool_name, kwargs)

            # ── Execute ──────────────────────────────────────────────
            result = self.executor.execute(tool_name, kwargs)
            tool_calls_made.append(tool_name)

            # ── OBSERVE ──────────────────────────────────────────────
            observations.append(result)
            self.trace.append(
                ReActTrace(
                    ReActStep.OBSERVE,
                    json.dumps(result, default=str),
                    tool_name=tool_name,
                    tool_result=result,
                )
            )
            if self.verbose:
                logger.info("[Step %d] OBSERVE: %s", step + 1, result)

        # ── FINAL decision ───────────────────────────────────────────
        decision = self._synthesize(game_state, observations)
        self.trace.append(
            ReActTrace(ReActStep.FINAL, json.dumps(decision, default=str))
        )
        return decision

    def _reason(
        self,
        game_state: Dict[str, Any],
        observations: List[Dict[str, Any]],
        already_called: List[str],
    ) -> Tuple[str, Optional[str]]:
        """Determine the next tool call by evaluating rules.

        Returns (reasoning_text, action_text_or_none).
        """
        for rule in self._rules:
            action = rule(game_state)
            if action is not None:
                parsed = ToolCallParser.parse(action)
                if parsed and parsed[0] not in already_called:
                    reason = f"Rule triggered tool '{parsed[0]}' based on game state."
                    return reason, action

        return "All relevant tools have been consulted.", None

    def _synthesize(
        self,
        game_state: Dict[str, Any],
        observations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Combine all observations into a final decision."""
        decision: Dict[str, Any] = {
            "strategy": "balanced",
            "actions": [],
            "warnings": [],
            "tool_calls": len(observations),
            "reasoning_steps": len(self.trace),
        }

        for obs in observations:
            # Merge supply recommendations
            if "recommendations" in obs:
                decision["actions"].extend(obs["recommendations"])
            if "warnings" in obs:
                decision["warnings"].extend(obs["warnings"])

            # Merge counter suggestions
            if "recommended_composition" in obs:
                decision["recommended_units"] = obs["recommended_composition"]
                decision["primary_counter"] = obs.get("primary_counter", "")

            # Merge timing info
            if "target" in obs and "total_seconds" in obs:
                decision.setdefault("timings", {})[obs["target"]] = obs["total_seconds"]

            # Merge army value
            if "total_value" in obs:
                decision["army_value"] = obs["total_value"]

        # Determine overall strategy from observations
        if decision.get("warnings"):
            for w in decision["warnings"]:
                if "SUPPLY_BLOCKED" in w:
                    decision["strategy"] = "fix_supply_block"
                    decision["actions"].insert(0, "PRIORITY: build Overlords")
                    break
                if "OVER_DRONED" in w:
                    decision["strategy"] = "army_transition"
                    break

        return decision

    def add_rule(self, rule: Callable[[Dict[str, Any]], Optional[str]]) -> None:
        """Add a custom reasoning rule."""
        self._rules.append(rule)

    def get_trace(self) -> List[Dict[str, Any]]:
        """Return the full ReAct trace as dicts."""
        return [
            {
                "step": t.step_type.value,
                "content": t.content,
                "tool": t.tool_name,
                "args": t.tool_args,
            }
            for t in self.trace
        ]


# ============================================================================
# Demo
# ============================================================================


def demo() -> None:
    """Demonstrate the tool-use agent with sample SC2 game states."""
    print("=" * 70)
    print("Phase 631: Tool-Use Agent for SC2 Demo")
    print("=" * 70)

    registry = build_sc2_tool_registry()

    # ── Demo 1: Direct tool calls ────────────────────────────────────────
    print("\n--- Demo 1: Direct Tool Calls ---")
    print(f"  Registered tools: {len(registry)}")
    for tool in registry.list_tools():
        print(f"    {tool.signature()}")

    executor = ToolExecutor(registry)

    print("\n  [calculate_army_value]")
    result = executor.execute(
        "calculate_army_value",
        {
            "unit_counts": "Zergling:20, Roach:8, Hydralisk:6",
        },
    )
    print(
        f"    Total value: {result['total_value']} "
        f"(M:{result['total_minerals']} G:{result['total_gas']})"
    )

    print("\n  [check_supply]")
    result = executor.execute(
        "check_supply",
        {
            "supply_used": 78,
            "supply_cap": 84,
            "army_supply": 40,
            "worker_count": 44,
        },
    )
    print(f"    Free supply: {result['free_supply']}")
    print(f"    Warnings: {result['warnings']}")
    print(f"    Recommendations: {result['recommendations']}")

    print("\n  [estimate_timing]")
    result = executor.execute(
        "estimate_timing",
        {
            "target_unit": "Hive",
            "current_minerals": 400,
            "current_gas": 100,
            "income_minerals": 1000,
            "income_gas": 300,
        },
    )
    print(f"    Target: {result['target']}")
    print(f"    Ready in: {result['ready_in']}")
    print(f"    Can afford now: {result['can_afford_now']}")

    print("\n  [suggest_counter]")
    result = executor.execute(
        "suggest_counter",
        {
            "enemy_units": "Marine, SiegeTank, Medivac, Liberator",
            "player_race": "Zerg",
        },
    )
    print(f"    Recommended comp: {result['recommended_composition']}")
    print(f"    Primary counter: {result['primary_counter']}")
    print(f"    Note: {result['composition_note']}")

    # ── Demo 2: ToolCallParser ───────────────────────────────────────────
    print("\n--- Demo 2: Tool Call Parsing ---")
    test_calls = [
        "CALL: check_supply(supply_used=80, supply_cap=84, army_supply=40, worker_count=44)",
        'ACTION: suggest_counter {"enemy_units": "Marine,Tank", "player_race": "Zerg"}',
        "CALL: estimate_timing(target_unit=Ultralisk, current_minerals=300, current_gas=150, income_minerals=800, income_gas=200)",
    ]
    for call_str in test_calls:
        parsed = ToolCallParser.parse(call_str)
        if parsed:
            print(f"  Parsed: {parsed[0]}({parsed[1]})")
        else:
            print(f"  Failed to parse: {call_str}")

    # ── Demo 3: Full ReAct loop ──────────────────────────────────────────
    print("\n--- Demo 3: Full ReAct Agent Loop ---")
    agent = ToolUseAgent(registry, max_steps=5, verbose=False)

    game_state = {
        "supply_used": 82,
        "supply_cap": 84,
        "army_supply": 42,
        "worker_count": 44,
        "minerals": 350,
        "vespene": 180,
        "mineral_income": 900,
        "gas_income": 250,
        "player_race": "Zerg",
        "enemy_units": ["Marine", "SiegeTank", "Medivac"],
        "own_unit_counts": "Zergling:20,Roach:8,Hydralisk:6",
        "next_tech_target": "Hive",
    }

    print(
        f"  Game state: supply={game_state['supply_used']}/{game_state['supply_cap']}, "
        f"minerals={game_state['minerals']}, enemy={game_state['enemy_units']}"
    )
    print("  Running ReAct loop...")

    decision = agent.run(game_state)

    print(f"\n  Decision:")
    print(f"    Strategy: {decision['strategy']}")
    print(f"    Actions: {decision['actions'][:5]}")
    print(f"    Warnings: {decision['warnings']}")
    print(f"    Tool calls made: {decision['tool_calls']}")
    if "recommended_units" in decision:
        print(f"    Recommended units: {decision['recommended_units']}")
    if "army_value" in decision:
        print(f"    Current army value: {decision['army_value']}")
    if "timings" in decision:
        print(f"    Tech timings: {decision['timings']}")

    print("\n  ReAct Trace:")
    for entry in agent.get_trace():
        step = entry["step"].upper()
        content = entry["content"][:80]
        print(f"    [{step:8s}] {content}")

    # ── Demo 4: Custom rule ──────────────────────────────────────────────
    print("\n--- Demo 4: Agent with Custom Rule ---")

    def custom_panic_rule(gs: Dict[str, Any]) -> Optional[str]:
        """Emergency rule: if very few workers, skip army value."""
        if gs.get("worker_count", 0) < 10:
            return "CALL: check_supply(supply_used=20, supply_cap=28, army_supply=8, worker_count=8)"
        return None

    agent2 = ToolUseAgent(registry, max_steps=3, verbose=False)
    agent2.add_rule(custom_panic_rule)

    panic_state = {
        "supply_used": 20,
        "supply_cap": 28,
        "army_supply": 8,
        "worker_count": 8,
        "minerals": 100,
        "vespene": 0,
        "player_race": "Zerg",
        "enemy_units": ["Zealot", "Stalker"],
    }
    decision2 = agent2.run(panic_state)
    print(f"  Panic decision: {decision2['strategy']}")
    print(f"  Actions: {decision2['actions']}")

    print("\n" + "=" * 70)
    print("Phase 631 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()

# Phase 631: Tool-Use registered
