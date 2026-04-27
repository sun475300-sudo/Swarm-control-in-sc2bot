"""
Phase 630: Agent Chain Orchestration for SC2 Decision Pipeline

Multi-agent chain orchestration system for StarCraft II decision making.
Supports sequential, parallel, and conditional chain composition to build
complex strategy pipelines from simple, reusable agent nodes.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
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


# ── Game Phase Enumeration ───────────────────────────────────────────────────


class GamePhase(Enum):
    """SC2 game phases for conditional routing."""

    EARLY = "early"
    MID = "mid"
    LATE = "late"
    EMERGENCY = "emergency"


# ── Chain Context ────────────────────────────────────────────────────────────


@dataclass
class ChainContext:
    """Shared mutable state passed through the chain pipeline.

    Every AgentNode receives this context, reads what it needs, and writes
    its results back so downstream nodes can consume them.
    """

    # Core game state
    game_loop: int = 0
    game_phase: GamePhase = GamePhase.EARLY
    minerals: int = 0
    vespene: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    worker_count: int = 0
    army_supply: int = 0
    enemy_race: str = "unknown"
    enemy_army_supply: int = 0
    expansion_count: int = 1

    # Scouting data
    scouting_info: Dict[str, Any] = field(default_factory=dict)
    enemy_buildings: List[str] = field(default_factory=list)
    enemy_units: List[str] = field(default_factory=list)

    # Analysis results (populated by chain nodes)
    threat_level: float = 0.0
    economy_score: float = 0.0
    military_score: float = 0.0
    tech_score: float = 0.0

    # Decision outputs
    strategy: str = ""
    action_queue: List[str] = field(default_factory=list)
    build_order: List[str] = field(default_factory=list)
    priority_targets: List[str] = field(default_factory=list)

    # Metadata
    chain_trace: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)

    def log_node(self, node_name: str, elapsed: float) -> None:
        """Record that a node executed."""
        self.chain_trace.append(node_name)
        self.timings[node_name] = elapsed

    def has_error(self) -> bool:
        return len(self.errors) > 0


# ── Agent Node ───────────────────────────────────────────────────────────────


class AgentNode(ABC):
    """Base class for a single processing node in an agent chain.

    Each node performs one well-defined task: scouting analysis, threat
    assessment, build-order selection, etc.
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._enabled = True

    @abstractmethod
    def process(self, ctx: ChainContext) -> ChainContext:
        """Execute this node's logic, mutating and returning the context."""
        ...

    def run(self, ctx: ChainContext) -> ChainContext:
        """Wrapper that adds timing and trace logging."""
        if not self._enabled:
            logger.debug("Node '%s' is disabled, skipping.", self.name)
            return ctx
        start = time.perf_counter()
        try:
            ctx = self.process(ctx)
        except Exception as exc:
            ctx.errors.append(f"{self.name}: {exc}")
            logger.error("Node '%s' failed: %s", self.name, exc)
        elapsed = time.perf_counter() - start
        ctx.log_node(self.name, elapsed)
        return ctx

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def __repr__(self) -> str:
        return f"AgentNode({self.name!r})"


class FunctionNode(AgentNode):
    """Convenience node wrapping a plain function."""

    def __init__(
        self,
        name: str,
        fn: Callable[[ChainContext], ChainContext],
        description: str = "",
    ) -> None:
        super().__init__(name, description)
        self._fn = fn

    def process(self, ctx: ChainContext) -> ChainContext:
        return self._fn(ctx)


# ── Agent Chain (sequential) ────────────────────────────────────────────────


class AgentChain:
    """Sequential chain: nodes execute one after another.

    Example pipeline: Scout -> Analyze -> Decide -> Execute
    """

    def __init__(self, name: str, nodes: Optional[List[AgentNode]] = None) -> None:
        self.name = name
        self.nodes: List[AgentNode] = list(nodes) if nodes else []

    def add(self, node: AgentNode) -> "AgentChain":
        self.nodes.append(node)
        return self

    def run(self, ctx: ChainContext) -> ChainContext:
        """Run all nodes sequentially."""
        logger.info("Chain '%s' starting with %d nodes.", self.name, len(self.nodes))
        for node in self.nodes:
            ctx = node.run(ctx)
        return ctx

    def __repr__(self) -> str:
        names = " -> ".join(n.name for n in self.nodes)
        return f"AgentChain({self.name!r}: {names})"

    def __len__(self) -> int:
        return len(self.nodes)


# ── Parallel Chain ───────────────────────────────────────────────────────────


class ParallelChain(AgentNode):
    """Runs multiple nodes/chains concurrently and merges results.

    Useful for simultaneous economy + military analysis where the two
    branches are independent.
    """

    def __init__(
        self,
        name: str,
        branches: Optional[List[AgentNode]] = None,
        max_workers: int = 4,
        merge_fn: Optional[
            Callable[[ChainContext, List[ChainContext]], ChainContext]
        ] = None,
    ) -> None:
        super().__init__(name, "Parallel execution of independent branches")
        self.branches: List[AgentNode] = list(branches) if branches else []
        self.max_workers = max_workers
        self._merge_fn = merge_fn or self._default_merge

    def add_branch(self, node: AgentNode) -> "ParallelChain":
        self.branches.append(node)
        return self

    # ── default merge: take highest scores, concatenate lists ────────────
    @staticmethod
    def _default_merge(
        original: ChainContext, results: List[ChainContext]
    ) -> ChainContext:
        """Merge parallel branch results into the original context."""
        merged = ChainContext(
            game_loop=original.game_loop,
            game_phase=original.game_phase,
            minerals=original.minerals,
            vespene=original.vespene,
            supply_used=original.supply_used,
            supply_cap=original.supply_cap,
            worker_count=original.worker_count,
            army_supply=original.army_supply,
            enemy_race=original.enemy_race,
            enemy_army_supply=original.enemy_army_supply,
            expansion_count=original.expansion_count,
            scouting_info=dict(original.scouting_info),
            enemy_buildings=list(original.enemy_buildings),
            enemy_units=list(original.enemy_units),
        )
        for res in results:
            merged.threat_level = max(merged.threat_level, res.threat_level)
            merged.economy_score = max(merged.economy_score, res.economy_score)
            merged.military_score = max(merged.military_score, res.military_score)
            merged.tech_score = max(merged.tech_score, res.tech_score)
            merged.action_queue.extend(res.action_queue)
            merged.build_order.extend(res.build_order)
            merged.priority_targets.extend(res.priority_targets)
            merged.chain_trace.extend(res.chain_trace)
            merged.errors.extend(res.errors)
            merged.timings.update(res.timings)
        # Keep strategy from the first branch that set one
        for res in results:
            if res.strategy:
                merged.strategy = res.strategy
                break
        return merged

    def process(self, ctx: ChainContext) -> ChainContext:
        """Execute branches in parallel threads, then merge."""
        import copy

        branch_contexts: List[ChainContext] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(branch.run, copy.deepcopy(ctx)): branch
                for branch in self.branches
            }
            for future in as_completed(futures):
                branch = futures[future]
                try:
                    result = future.result()
                    branch_contexts.append(result)
                except Exception as exc:
                    logger.error("Parallel branch '%s' failed: %s", branch.name, exc)
                    err_ctx = copy.deepcopy(ctx)
                    err_ctx.errors.append(f"parallel/{branch.name}: {exc}")
                    branch_contexts.append(err_ctx)

        return self._merge_fn(ctx, branch_contexts)


# ── Conditional Chain ────────────────────────────────────────────────────────


class ConditionalChain(AgentNode):
    """Routes to different sub-chains based on a condition function.

    Typical use: select early/mid/late game chain, or trigger an emergency
    response chain when threat is critical.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "Conditional chain router")
        self._routes: List[Tuple[Callable[[ChainContext], bool], AgentNode]] = []
        self._default: Optional[AgentNode] = None

    def when(
        self,
        condition: Callable[[ChainContext], bool],
        node: AgentNode,
    ) -> "ConditionalChain":
        """Add a conditional route."""
        self._routes.append((condition, node))
        return self

    def otherwise(self, node: AgentNode) -> "ConditionalChain":
        """Fallback route when no condition matches."""
        self._default = node
        return self

    def process(self, ctx: ChainContext) -> ChainContext:
        for cond, node in self._routes:
            if cond(ctx):
                logger.info(
                    "ConditionalChain '%s' routed to '%s'.", self.name, node.name
                )
                return node.run(ctx)
        if self._default is not None:
            logger.info("ConditionalChain '%s' using default route.", self.name)
            return self._default.run(ctx)
        logger.warning(
            "ConditionalChain '%s': no route matched, passing through.", self.name
        )
        return ctx


# ── Chain Router (multi-key routing) ─────────────────────────────────────────


class ChainRouter:
    """Routes to named chains by key (e.g., game phase string).

    Unlike ConditionalChain which evaluates predicates, ChainRouter uses
    a selector function that returns a string key, then looks up the
    matching chain from a registry.
    """

    def __init__(
        self,
        name: str,
        selector: Callable[[ChainContext], str],
    ) -> None:
        self.name = name
        self._selector = selector
        self._registry: Dict[str, AgentNode] = {}
        self._default: Optional[AgentNode] = None

    def register(self, key: str, node: AgentNode) -> "ChainRouter":
        self._registry[key] = node
        return self

    def set_default(self, node: AgentNode) -> "ChainRouter":
        self._default = node
        return self

    def run(self, ctx: ChainContext) -> ChainContext:
        key = self._selector(ctx)
        node = self._registry.get(key, self._default)
        if node is None:
            logger.warning("ChainRouter '%s': no chain for key '%s'.", self.name, key)
            return ctx
        logger.info(
            "ChainRouter '%s' selected '%s' -> '%s'.", self.name, key, node.name
        )
        return node.run(ctx)


# ============================================================================
# SC2-Specific Agent Nodes
# ============================================================================


class ScoutAnalyzerNode(AgentNode):
    """Processes raw scouting data into structured threat intelligence."""

    def __init__(self) -> None:
        super().__init__("scout_analyzer", "Analyze scouting information")

    def process(self, ctx: ChainContext) -> ChainContext:
        # Detect aggressive openings
        aggressive_buildings = {
            "BanelingNest",
            "DarkShrine",
            "ProxyBarracks",
            "NydusNetwork",
        }
        detected = set(ctx.enemy_buildings) & aggressive_buildings
        if detected:
            ctx.threat_level = max(ctx.threat_level, 0.8)
            ctx.scouting_info["aggressive_opening"] = True
            ctx.scouting_info["detected_aggression"] = list(detected)
        else:
            ctx.scouting_info["aggressive_opening"] = False

        # Estimate enemy tech level
        tech_buildings = {"HiveTech", "FleetBeacon", "FusionCore", "GreaterSpire"}
        if set(ctx.enemy_buildings) & tech_buildings:
            ctx.scouting_info["enemy_tech"] = "high"
            ctx.tech_score = max(ctx.tech_score, 0.7)
        elif len(ctx.enemy_buildings) > 3:
            ctx.scouting_info["enemy_tech"] = "medium"
        else:
            ctx.scouting_info["enemy_tech"] = "low"

        return ctx


class EconomyAnalyzerNode(AgentNode):
    """Evaluates current economic status and recommends macro adjustments."""

    def __init__(self) -> None:
        super().__init__("economy_analyzer", "Evaluate economy and macro")

    def process(self, ctx: ChainContext) -> ChainContext:
        # Worker saturation check
        ideal_workers = ctx.expansion_count * 16
        saturation = ctx.worker_count / max(ideal_workers, 1)
        ctx.economy_score = min(saturation, 1.0)

        # Mineral bank warnings
        if ctx.minerals > 1000 and ctx.supply_cap - ctx.supply_used < 10:
            ctx.action_queue.append("build_supply")
            ctx.action_queue.append("spend_minerals")
        elif ctx.minerals > 800:
            ctx.action_queue.append("expand_or_spend")

        # Gas check
        if ctx.vespene > 500 and ctx.minerals < 200:
            ctx.action_queue.append("reduce_gas_workers")

        # Expansion timing
        if saturation > 0.9 and ctx.minerals > 400:
            ctx.action_queue.append("take_expansion")
            ctx.build_order.append("Hatchery")

        ctx.scouting_info["worker_saturation"] = round(saturation, 2)
        return ctx


class MilitaryAnalyzerNode(AgentNode):
    """Assesses army strength relative to the enemy."""

    def __init__(self) -> None:
        super().__init__("military_analyzer", "Evaluate army composition")

    def process(self, ctx: ChainContext) -> ChainContext:
        if ctx.enemy_army_supply == 0:
            ratio = 2.0  # assume advantage if no data
        else:
            ratio = ctx.army_supply / ctx.enemy_army_supply

        ctx.military_score = min(ratio / 2.0, 1.0)

        if ratio < 0.6:
            ctx.threat_level = max(ctx.threat_level, 0.9)
            ctx.action_queue.append("defensive_stance")
            ctx.priority_targets.append("high_value_units")
        elif ratio > 1.5:
            ctx.action_queue.append("consider_attack")
        else:
            ctx.action_queue.append("continue_production")

        ctx.scouting_info["army_ratio"] = round(ratio, 2)
        return ctx


class StrategyDeciderNode(AgentNode):
    """Synthesizes analysis scores into a coherent strategy."""

    def __init__(self) -> None:
        super().__init__("strategy_decider", "Decide overall strategy")

    def process(self, ctx: ChainContext) -> ChainContext:
        # Weighted composite score
        composite = (
            ctx.economy_score * 0.3 + ctx.military_score * 0.4 + ctx.tech_score * 0.3
        )

        if ctx.threat_level > 0.8:
            ctx.strategy = "all_in_defense"
            ctx.build_order = ["SpineCrawler", "Zergling", "Baneling"]
        elif composite > 0.7:
            ctx.strategy = "aggressive_timing"
            ctx.build_order.append("attack_move")
        elif ctx.economy_score < 0.5:
            ctx.strategy = "macro_focus"
            ctx.build_order.extend(["Drone", "Hatchery"])
        else:
            ctx.strategy = "balanced"
            ctx.build_order.extend(["Drone", "Zergling", "Queen"])

        return ctx


class ExecutionPlannerNode(AgentNode):
    """Converts strategy into an ordered execution plan."""

    def __init__(self) -> None:
        super().__init__("execution_planner", "Plan action execution order")

    def process(self, ctx: ChainContext) -> ChainContext:
        plan: List[str] = []

        # Supply first
        if "build_supply" in ctx.action_queue:
            plan.append("PRIORITY: build Overlord/Supply Depot")

        # Defense takes precedence
        if ctx.strategy == "all_in_defense":
            plan.append("EMERGENCY: build static defense")
            plan.append("EMERGENCY: produce defensive units")
            plan.append("EMERGENCY: recall army to base")
        else:
            # Normal plan
            if "take_expansion" in ctx.action_queue:
                plan.append("MACRO: take next expansion")
            for unit in ctx.build_order:
                plan.append(f"BUILD: {unit}")
            if "consider_attack" in ctx.action_queue:
                plan.append("MILITARY: move out with army")

        ctx.action_queue = plan
        return ctx


# ── Emergency Response Chain ─────────────────────────────────────────────────


class EmergencyDetectorNode(AgentNode):
    """Detects emergency situations that override normal decision flow."""

    def __init__(self) -> None:
        super().__init__("emergency_detector", "Detect critical threats")

    def process(self, ctx: ChainContext) -> ChainContext:
        # Proxy detection
        if ctx.scouting_info.get("aggressive_opening"):
            ctx.game_phase = GamePhase.EMERGENCY
            ctx.strategy = "emergency_response"
            ctx.action_queue.insert(0, "ALERT: cancel non-essential production")
            ctx.action_queue.insert(1, "ALERT: pull workers if needed")

        # Supply blocked
        if ctx.supply_used >= ctx.supply_cap and ctx.supply_cap < 200:
            ctx.action_queue.insert(0, "CRITICAL: build supply immediately")

        # Mineral float crisis
        if ctx.minerals > 2000:
            ctx.action_queue.insert(0, "WARNING: severe mineral float, mass produce")

        return ctx


class EmergencyResponseNode(AgentNode):
    """Generates rapid response actions for emergency situations."""

    def __init__(self) -> None:
        super().__init__("emergency_response", "Generate emergency actions")

    def process(self, ctx: ChainContext) -> ChainContext:
        ctx.action_queue = [
            "EMERGENCY: pull 3 workers to defend",
            "EMERGENCY: build SpineCrawler at natural",
            "EMERGENCY: produce 6 Zerglings immediately",
            "EMERGENCY: send Overlord to scout enemy base",
            "EMERGENCY: delay expansion until safe",
        ]
        ctx.build_order = ["Zergling", "Zergling", "SpineCrawler", "Queen"]
        ctx.strategy = "survive_and_stabilize"
        return ctx


# ── Game-Phase Specific Chains ───────────────────────────────────────────────


def build_early_game_chain() -> AgentChain:
    """Chain optimized for the first 5 minutes."""
    chain = AgentChain("early_game")
    chain.add(ScoutAnalyzerNode())
    chain.add(FunctionNode("early_econ", _early_economy_logic, "Early economy"))
    chain.add(FunctionNode("early_build", _early_build_order, "Opening build order"))
    chain.add(ExecutionPlannerNode())
    return chain


def _early_economy_logic(ctx: ChainContext) -> ChainContext:
    """Focus on worker production and first expansion."""
    ctx.economy_score = ctx.worker_count / 22.0  # 22 = ideal early workers
    if ctx.worker_count < 16:
        ctx.build_order.append("Drone")
    if ctx.minerals > 300 and ctx.expansion_count < 2:
        ctx.action_queue.append("take_expansion")
        ctx.build_order.append("Hatchery")
    return ctx


def _early_build_order(ctx: ChainContext) -> ChainContext:
    """Standard Hatch-first opening."""
    if not ctx.build_order:
        ctx.build_order = ["Hatchery", "Gas", "Pool", "Queen", "Zergling", "Zergling"]
    ctx.strategy = "economic_opening"
    return ctx


def build_mid_game_chain() -> AgentChain:
    """Chain for minutes 5-12: tech and army composition."""
    analysis = ParallelChain("mid_analysis")
    analysis.add_branch(EconomyAnalyzerNode())
    analysis.add_branch(MilitaryAnalyzerNode())

    chain = AgentChain("mid_game")
    chain.add(ScoutAnalyzerNode())
    chain.add(analysis)
    chain.add(StrategyDeciderNode())
    chain.add(ExecutionPlannerNode())
    return chain


def build_late_game_chain() -> AgentChain:
    """Chain for 12+ minutes: max army, tech switches, map control."""
    chain = AgentChain("late_game")
    chain.add(ScoutAnalyzerNode())
    chain.add(FunctionNode("late_tech", _late_tech_assessment, "Late tech check"))
    chain.add(MilitaryAnalyzerNode())
    chain.add(StrategyDeciderNode())
    chain.add(FunctionNode("late_army", _late_army_comp, "Late army composition"))
    chain.add(ExecutionPlannerNode())
    return chain


def _late_tech_assessment(ctx: ChainContext) -> ChainContext:
    """Ensure Hive tech and upgrades are in progress."""
    ctx.tech_score = 0.9  # assume high tech by late game
    if "HiveTech" not in ctx.enemy_buildings:
        ctx.build_order.append("Hive")
    ctx.build_order.extend(["Adrenal Glands", "3-3 Upgrades"])
    return ctx


def _late_army_comp(ctx: ChainContext) -> ChainContext:
    """Transition to late-game army composition."""
    ctx.build_order.extend(["Ultralisk", "Corruptor", "Viper"])
    if ctx.army_supply > 120:
        ctx.action_queue.append("consider_multi_prong_attack")
    return ctx


def build_emergency_chain() -> AgentChain:
    """Chain for crisis situations: all-ins, proxy rushes, etc."""
    chain = AgentChain("emergency")
    chain.add(EmergencyDetectorNode())
    chain.add(EmergencyResponseNode())
    return chain


# ── Master Strategy Chain ────────────────────────────────────────────────────


def build_master_chain() -> ChainRouter:
    """Compose all sub-chains into a master strategy router.

    Selects the appropriate chain based on current game phase.
    """

    def phase_selector(ctx: ChainContext) -> str:
        # Emergency overrides everything
        if ctx.threat_level > 0.85:
            return "emergency"
        return ctx.game_phase.value

    router = ChainRouter("master_strategy", phase_selector)
    router.register("early", build_early_game_chain())
    router.register("mid", build_mid_game_chain())
    router.register("late", build_late_game_chain())
    router.register("emergency", build_emergency_chain())
    router.set_default(build_mid_game_chain())

    return router


def build_conditional_attack_chain() -> ConditionalChain:
    """Example conditional chain: decide attack timing."""
    chain = ConditionalChain("attack_decision")

    chain.when(
        lambda ctx: ctx.military_score > 0.8 and ctx.army_supply > 80,
        FunctionNode("full_attack", lambda ctx: _set_strategy(ctx, "all_out_attack")),
    )
    chain.when(
        lambda ctx: ctx.military_score > 0.6,
        FunctionNode("harass", lambda ctx: _set_strategy(ctx, "harass_and_expand")),
    )
    chain.otherwise(
        FunctionNode("defend", lambda ctx: _set_strategy(ctx, "turtle_and_macro")),
    )
    return chain


def _set_strategy(ctx: ChainContext, strategy: str) -> ChainContext:
    ctx.strategy = strategy
    return ctx


# ============================================================================
# Demo
# ============================================================================


def demo() -> None:
    """Demonstrate agent chain orchestration with sample game states."""
    print("=" * 70)
    print("Phase 630: Agent Chain Orchestration Demo")
    print("=" * 70)

    # ── Demo 1: Sequential chain ─────────────────────────────────────────
    print("\n--- Demo 1: Sequential Scout -> Analyze -> Decide -> Execute ---")
    seq_chain = AgentChain("basic_pipeline")
    seq_chain.add(ScoutAnalyzerNode())
    seq_chain.add(EconomyAnalyzerNode())
    seq_chain.add(MilitaryAnalyzerNode())
    seq_chain.add(StrategyDeciderNode())
    seq_chain.add(ExecutionPlannerNode())
    print(f"  Chain: {seq_chain}")

    ctx = ChainContext(
        game_loop=3000,
        game_phase=GamePhase.MID,
        minerals=450,
        vespene=200,
        supply_used=60,
        supply_cap=76,
        worker_count=44,
        army_supply=30,
        enemy_race="Terran",
        enemy_army_supply=35,
        expansion_count=3,
        enemy_buildings=["Barracks", "Factory", "Starport"],
    )
    result = seq_chain.run(ctx)
    print(f"  Strategy: {result.strategy}")
    print(f"  Actions: {result.action_queue[:5]}")
    print(f"  Trace: {' -> '.join(result.chain_trace)}")
    print(f"  Total time: {sum(result.timings.values()):.4f}s")

    # ── Demo 2: Parallel chain ───────────────────────────────────────────
    print("\n--- Demo 2: Parallel Economy + Military Analysis ---")
    parallel = ParallelChain("dual_analysis")
    parallel.add_branch(EconomyAnalyzerNode())
    parallel.add_branch(MilitaryAnalyzerNode())

    ctx2 = ChainContext(
        game_loop=5000,
        game_phase=GamePhase.MID,
        minerals=800,
        vespene=300,
        supply_used=90,
        supply_cap=100,
        worker_count=50,
        army_supply=50,
        enemy_race="Protoss",
        enemy_army_supply=45,
        expansion_count=3,
    )
    result2 = parallel.run(ctx2)
    print(f"  Economy score: {result2.economy_score:.2f}")
    print(f"  Military score: {result2.military_score:.2f}")
    print(f"  Parallel actions: {result2.action_queue}")

    # ── Demo 3: Conditional chain ────────────────────────────────────────
    print("\n--- Demo 3: Conditional Attack Decision ---")
    cond_chain = build_conditional_attack_chain()

    ctx3 = ChainContext(military_score=0.9, army_supply=100)
    result3 = cond_chain.run(ctx3)
    print(f"  High military -> strategy: {result3.strategy}")

    ctx4 = ChainContext(military_score=0.3, army_supply=30)
    result4 = cond_chain.run(ctx4)
    print(f"  Low military  -> strategy: {result4.strategy}")

    # ── Demo 4: Master chain router ──────────────────────────────────────
    print("\n--- Demo 4: Master Strategy Router ---")
    master = build_master_chain()

    for phase, gl in [
        (GamePhase.EARLY, 1000),
        (GamePhase.MID, 6000),
        (GamePhase.LATE, 15000),
    ]:
        ctx_r = ChainContext(
            game_loop=gl,
            game_phase=phase,
            minerals=400,
            vespene=200,
            supply_used=60,
            supply_cap=76,
            worker_count=40,
            army_supply=30,
            enemy_army_supply=25,
            expansion_count=2,
        )
        result_r = master.run(ctx_r)
        print(
            f"  {phase.value:10s} -> strategy={result_r.strategy:25s} "
            f"trace={' -> '.join(result_r.chain_trace)}"
        )

    # ── Demo 5: Emergency chain ──────────────────────────────────────────
    print("\n--- Demo 5: Emergency Response ---")
    emergency = build_emergency_chain()
    ctx_e = ChainContext(
        game_loop=2000,
        game_phase=GamePhase.EARLY,
        minerals=200,
        supply_used=22,
        supply_cap=22,
        worker_count=16,
        army_supply=4,
        enemy_buildings=["ProxyBarracks", "Barracks"],
        scouting_info={"aggressive_opening": True},
    )
    result_e = emergency.run(ctx_e)
    print(f"  Strategy: {result_e.strategy}")
    print(f"  Emergency actions:")
    for act in result_e.action_queue[:5]:
        print(f"    - {act}")

    print("\n" + "=" * 70)
    print("Phase 630 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()

# Phase 630: Agent Chain registered
