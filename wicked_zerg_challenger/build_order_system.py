# -*- coding: utf-8 -*-
"""

Build Order Optimization System

Purpose: Stable and optimized automated build order execution
- Standard 12 Pool, 14 Hatch, 14 Gas builds
- Improved timing accuracy
- Win-rate based adjustment
"""

import logging
from enum import Enum
from typing import Any, Dict, List

try:
    from config.constants import (
        BUILD_ORDER_END_TIME,
        MAX_STEP_RETRIES,
        EXPANSION_TIMING_TARGET,
        THREAT_CACHE_TTL,
    )
except ImportError:
    BUILD_ORDER_END_TIME = 300.0
    MAX_STEP_RETRIES = 50
    EXPANSION_TIMING_TARGET = 60.0
    THREAT_CACHE_TTL = 0.5

from knowledge_manager import KnowledgeManager  # NEW

logger = logging.getLogger("BuildOrderSystem")

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
except ImportError:

    class BotAI:
        pass

    class _SC2StubSymbol:
        """Sentinel sc2 enum member used when python-sc2 is unavailable.

        Hashable, comparable, stringifies to its name, but is *not* a
        Python ``str`` so build-order classifiers can distinguish stub
        enum members from upgrade-name strings."""

        __slots__ = ("_name",)

        def __init__(self, name):
            self._name = name

        def __eq__(self, other):
            if isinstance(other, _SC2StubSymbol):
                return other._name == self._name
            return NotImplemented

        def __hash__(self):
            return hash(("_SC2StubSymbol", self._name))

        def __repr__(self):
            return self._name

        def __str__(self):
            return self._name

    class _SC2StubMeta(type):
        _cache: dict = {}

        def __getattr__(cls, name):
            key = (cls.__name__, name)
            sym = cls._cache.get(key)
            if sym is None:
                sym = _SC2StubSymbol(name)
                cls._cache[key] = sym
            return sym
    class UnitTypeId(metaclass=_SC2StubMeta):
        pass

    class AbilityId(metaclass=_SC2StubMeta):
        pass

    class UpgradeId(metaclass=_SC2StubMeta):
        pass

    class Point2:
        pass


ZVT_BUILDS = {
    "hatch_first_16": {
        "name": "16 Hatchery macro",
        "condition": "default",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (20, UnitTypeId.QUEEN),
            (20, UnitTypeId.QUEEN),
            (20, UnitTypeId.ZERGLING),
            (24, "METABOLIC_BOOST"),
            (30, UnitTypeId.ROACHWARREN),
        ],
        "transition": "roach_hydra_mid",
        "note": "Safe macro opening after confirming one barracks.",
    },
    "aggressive_pool_first": {
        "name": "14 Pool pressure defense",
        "condition": "enemy_proxy_detected OR enemy_one_base",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),
            (16, UnitTypeId.HATCHERY),
            (16, UnitTypeId.EXTRACTOR),
            (18, UnitTypeId.QUEEN),
            (18, UnitTypeId.ZERGLING),
            (22, "METABOLIC_BOOST"),
        ],
        "transition": "ling_bane_mid",
        "note": "Earlier pool for proxy or one-base Terran pressure.",
    },
    "fast_lair_macro": {
        "name": "Fast Lair macro",
        "condition": "enemy_expand_confirmed AND no_aggression",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (19, UnitTypeId.QUEEN),
            (21, UnitTypeId.QUEEN),
            (24, "METABOLIC_BOOST"),
            (30, UnitTypeId.LAIR),
            (38, UnitTypeId.HYDRALISKDEN),
            (44, UnitTypeId.HATCHERY),
        ],
        "transition": "hydra_lurker_late",
        "note": "Tech ahead when Terran expands safely without aggression.",
    },
}


ZVP_BUILDS = {
    "roach_rush": {
        "name": "Roach rush",
        "condition": "default",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (19, UnitTypeId.QUEEN),
            (20, UnitTypeId.QUEEN),
            (22, UnitTypeId.ROACHWARREN),
            (24, "METABOLIC_BOOST"),
            (28, UnitTypeId.ROACH),
        ],
        "transition": "roach_ravager_push",
        "note": "Default gateway-expand response with a roach timing.",
    },
    "ling_flood_anti_cannon": {
        "name": "Ling flood anti-cannon",
        "condition": "enemy_cannon_rush_detected",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),
            (14, UnitTypeId.HATCHERY),
            (16, UnitTypeId.QUEEN),
            (16, UnitTypeId.ZERGLING),
            (20, "METABOLIC_BOOST"),
        ],
        "transition": "ling_bane_nydus",
        "note": "Fast pool response when cannon pressure is scouted.",
    },
    "hydra_lair_macro": {
        "name": "Hydra lair macro",
        "condition": "enemy_stargate_detected OR enemy_robo_detected",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (19, UnitTypeId.QUEEN),
            (21, UnitTypeId.QUEEN),
            (24, "METABOLIC_BOOST"),
            (28, UnitTypeId.EXTRACTOR),
            (30, UnitTypeId.LAIR),
            (36, UnitTypeId.HYDRALISKDEN),
            (38, UnitTypeId.HATCHERY),
            (44, UnitTypeId.EXTRACTOR),
            (44, UnitTypeId.EXTRACTOR),
        ],
        "transition": "hydra_lurker_viper",
        "note": "Fast lair and hydra tech when Stargate or Robo is confirmed.",
    },
}


ZVZ_BUILDS = {
    "safe_14pool": {
        "name": "14 Pool safe",
        "condition": "default",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),
            (16, UnitTypeId.HATCHERY),
            (16, UnitTypeId.EXTRACTOR),
            (18, UnitTypeId.QUEEN),
            (18, UnitTypeId.ZERGLING),
            (20, "METABOLIC_BOOST"),
            (22, UnitTypeId.QUEEN),
            (24, UnitTypeId.BANELINGNEST),
        ],
        "transition": "ling_bane_control",
        "note": "Default ZvZ opener into speedling and baneling control.",
    },
    "12pool_rush": {
        "name": "12 Pool rush",
        "condition": "aggressive_opening",
        "order": [
            (12, UnitTypeId.SPAWNINGPOOL),
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.ZERGLING),
            (17, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.QUEEN),
            (19, "METABOLIC_BOOST"),
            (20, UnitTypeId.HATCHERY),
        ],
        "transition": "ling_bane_allin_or_macro",
        "note": "Aggressive opener to force damage before expanding.",
    },
    "roach_warren_macro": {
        "name": "Roach warren macro",
        "condition": "enemy_ling_flood_detected",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),
            (16, UnitTypeId.HATCHERY),
            (16, UnitTypeId.EXTRACTOR),
            (18, UnitTypeId.QUEEN),
            (20, UnitTypeId.ROACHWARREN),
            (22, UnitTypeId.QUEEN),
            (24, UnitTypeId.ROACH),
        ],
        "transition": "roach_ravager_mid",
        "note": "Fast Roach Warren when enemy speedling flood is detected.",
    },
}


class BuildOrderType(Enum):
    """Build Order Types"""

    STANDARD_12POOL = "STANDARD_12POOL"  # Matches JSON key
    SAFE_14POOL = "SAFE_14POOL"  # Need to add to JSON
    AGGRESSIVE_10POOL = "AGGRESSIVE_10POOL"
    ECONOMY_15HATCH = "ECONOMY_15HATCH"
    HATCH_FIRST_16 = "HATCH_FIRST_16"  # * Phase 22: 1분 멀티 빌드 *
    ROACH_RUSH = "ROACH_RUSH"  # Matches JSON key
    MUTALISK_RUSH = "MUTALISK_RUSH"
    HYDRA_TIMING = "HYDRA_TIMING"
    LURKER_DEFENSE = "LURKER_DEFENSE"


class BuildOrderStep:
    """Build Order Step"""

    def __init__(
        self, supply: int, action: str, unit_type: Any, description: str = ""
    ):
        self.supply = supply  # Supply to execute at
        self.action = action  # "build", "train", "expand", "morph", "upgrade"
        self.unit_type = unit_type
        self.description = description
        self.completed = False

    def __repr__(self):
        return f"BuildOrderStep({self.supply} supply: {self.action} {self.unit_type})"


class BuildOrderTransition:
    """Mid-build transition controller driven by scouting blackboard signals."""

    def __init__(self):
        self.current_build = None
        self.transition_triggered = False
        self.last_reason = None

    async def check_transition(self, game_time, blackboard):
        """Switch the active build plan when scout intel demands it."""
        if not blackboard or not hasattr(blackboard, "get"):
            return None
        if self.transition_triggered:
            return None

        if blackboard.get("cheese_detected", False):
            return self._switch_to_defense_build("cheese_detected")

        if blackboard.get("enemy_all_in", False) and float(game_time or 0.0) < 300.0:
            return self._switch_to_army_build("enemy_all_in")

        if blackboard.get("enemy_expand_confirmed", False) and not blackboard.get(
            "enemy_aggression", False
        ):
            return self._switch_to_greedy_build("enemy_expand_confirmed")

        return None

    def _set_build(self, build_key: str, reason: str, lock: bool):
        if self.current_build == build_key and self.last_reason == reason:
            return None
        self.current_build = build_key
        self.last_reason = reason
        self.transition_triggered = lock
        return build_key

    def _switch_to_defense_build(self, reason: str = "cheese_detected"):
        """Defense build: spines, queens, and zerglings."""
        changed = self._set_build("emergency_defense", reason, True)
        if changed:
            logger.info("[BUILD TRANSITION] Switching to DEFENSE build")
        return changed

    def _switch_to_army_build(self, reason: str = "enemy_all_in"):
        """Full army build: suspend drone greed and spend larvae on units."""
        changed = self._set_build("full_army", reason, True)
        if changed:
            logger.info("[BUILD TRANSITION] Switching to FULL ARMY build")
        return changed

    def _switch_to_greedy_build(self, reason: str = "enemy_expand_confirmed"):
        """Greedy macro build: third hatchery and faster tech."""
        changed = self._set_build("greedy_macro", reason, False)
        if changed:
            logger.info("[BUILD TRANSITION] Switching to GREEDY MACRO build")
        return changed


class BuildOrderSystem:
    """

    Build Order System (Data-Driven by KnowledgeManager)

    Key Features:
    1. Load build order data via KnowledgeManager
    2. JSON-based automated execution
    3. Real-time progress tracking
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.knowledge_manager = KnowledgeManager()  # Initialize Knowledge Manager
        self.blackboard = getattr(bot, "blackboard", None)
        self.enabled = True
        self.build_order_active = True

        # Current Build Order (Selected by enemy race)
        self.current_build_order: BuildOrderType = self._select_build_by_enemy_race()
        self.current_matchup_build_key = None
        self.current_build_transition = None
        self.transition_manager = BuildOrderTransition()
        self.build_steps: List[BuildOrderStep] = []
        self.current_step_index = 0

        # Timing tracking
        self.step_timings: Dict[int, float] = {}  # supply -> game_time
        self.missed_timings: List[str] = []

        # Performance Stats
        self.build_order_stats = {
            BuildOrderType.STANDARD_12POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.SAFE_14POOL: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.AGGRESSIVE_10POOL: {
                "games": 0,
                "wins": 0,
                "avg_timing": 0.0,
            },
            BuildOrderType.ECONOMY_15HATCH: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.HATCH_FIRST_16: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.ROACH_RUSH: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.MUTALISK_RUSH: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.HYDRA_TIMING: {"games": 0, "wins": 0, "avg_timing": 0.0},
            BuildOrderType.LURKER_DEFENSE: {"games": 0, "wins": 0, "avg_timing": 0.0},
        }

        # Build Order End Time
        self.build_order_end_time = BUILD_ORDER_END_TIME

        # * Phase 25: 스텝 재시도 시스템 *
        self._step_retry_count = 0
        self._max_retries_before_skip = MAX_STEP_RETRIES
        self._skipped_steps: List[BuildOrderStep] = []  # 건너뛴 스텝 (나중에 재실행)

        # * Phase 22: 확장 타이밍 검증 *
        self.expansion_timing_target = EXPANSION_TIMING_TARGET
        self.expansion_actual_time = 0.0  # 실제 확장 시작 시간
        self.expansion_timing_verified = False

        # Initialization
        self._setup_build_order()
        self.transition_manager.current_build = (
            self.current_matchup_build_key or self.current_build_order.value
        )

    def _select_build_by_enemy_race(self) -> BuildOrderType:
        """
        Select best build order by enemy race

        Returns:
            BuildOrderType: Selected Build Order
        """
        if not hasattr(self.bot, "enemy_race") or not self.bot.enemy_race:
            return BuildOrderType.ROACH_RUSH  # Fallback

        race_name = str(self.bot.enemy_race).lower()

        if "protoss" in race_name:
            # vs Protoss: Roach/Ravager timing (Roach Rush)
            # * 14pool은 너무 수동적 -> 로치 러쉬로 적극적 대응
            # Protoss deathball 완성 전에 압박
            return BuildOrderType.ROACH_RUSH
        elif "terran" in race_name:
            # vs Terran: 16 Hatch First (경제 우선)
            # * 12pool은 너무 공격적 -> 확장 우선 + 링/바네 전환
            return BuildOrderType.HATCH_FIRST_16
        else:
            # vs Zerg: 14-pool (Mirror matchup stability)
            # Secure economy while matching pool timing
            return BuildOrderType.SAFE_14POOL

    def _setup_build_order(self) -> None:
        """Setup current build order (From KnowledgeManager)"""
        if self._is_terran_matchup():
            build_key = self._select_zvt_build()
            build_data = ZVT_BUILDS.get(build_key, ZVT_BUILDS["hatch_first_16"])
            self.current_matchup_build_key = build_key
            self.current_build_transition = build_data.get("transition")
            self.build_steps = self._build_steps_from_order(build_data.get("order", []))
            logger.info(
                f"Loaded ZvT build '{build_data.get('name')}' ({build_key})"
            )
            self.current_step_index = 0
            logger.info(f"Build Order Set: {self.current_build_order.value}:{build_key}")
            logger.info(f"Total {len(self.build_steps)} steps")
            return

        if self._is_protoss_matchup():
            build_key = self._select_zvp_build()
            build_data = ZVP_BUILDS.get(build_key, ZVP_BUILDS["roach_rush"])
            self.current_matchup_build_key = build_key
            self.current_build_transition = build_data.get("transition")
            self.build_steps = self._build_steps_from_order(build_data.get("order", []))
            logger.info(
                f"Loaded ZvP build '{build_data.get('name')}' ({build_key})"
            )
            self.current_step_index = 0
            logger.info(f"Build Order Set: {self.current_build_order.value}:{build_key}")
            logger.info(f"Total {len(self.build_steps)} steps")
            return

        if self._is_zerg_matchup():
            build_key = self._select_zvz_build()
            build_data = ZVZ_BUILDS.get(build_key, ZVZ_BUILDS["safe_14pool"])
            self.current_matchup_build_key = build_key
            self.current_build_transition = build_data.get("transition")
            self.build_steps = self._build_steps_from_order(build_data.get("order", []))
            logger.info(
                f"Loaded ZvZ build '{build_data.get('name')}' ({build_key})"
            )
            self.current_step_index = 0
            logger.info(f"Build Order Set: {self.current_build_order.value}:{build_key}")
            logger.info(f"Total {len(self.build_steps)} steps")
            return

        build_key = self.current_build_order.value
        build_data = self.knowledge_manager.get_build_order(build_key)

        if build_data:
            self.build_steps = self._parse_build_steps(build_data.get("steps", []))
            logger.info(f"Loaded '{build_data.get('name')}' from KnowledgeManager")
        else:
            logger.error(f"Error: '{build_key}' not found in KnowledgeManager.")
            self.build_steps = []

        self.current_step_index = 0
        logger.info(f"Build Order Set: {self.current_build_order.value}")
        logger.info(f"Total {len(self.build_steps)} steps")

    def _is_terran_matchup(self) -> bool:
        if not hasattr(self.bot, "enemy_race") or not self.bot.enemy_race:
            return False
        return "terran" in str(self.bot.enemy_race).lower()

    def _is_protoss_matchup(self) -> bool:
        if not hasattr(self.bot, "enemy_race") or not self.bot.enemy_race:
            return False
        return "protoss" in str(self.bot.enemy_race).lower()

    def _is_zerg_matchup(self) -> bool:
        if not hasattr(self.bot, "enemy_race") or not self.bot.enemy_race:
            return False
        return "zerg" in str(self.bot.enemy_race).lower()

    def _blackboard_get(self, key: str, default=None):
        if self.blackboard and hasattr(self.blackboard, "get"):
            return self.blackboard.get(key, default)
        return default

    def _select_zvt_build(self) -> str:
        if self._blackboard_get("enemy_proxy_detected", False) or self._blackboard_get(
            "enemy_one_base", False
        ):
            return "aggressive_pool_first"
        if self._blackboard_get("enemy_expand_confirmed", False) and not self._blackboard_get(
            "enemy_aggression", False
        ):
            return "fast_lair_macro"
        return "hatch_first_16"

    def _select_zvp_build(self) -> str:
        cannon_flags = (
            self._blackboard_get("enemy_cannon_rush_detected", False),
            self._blackboard_get("cannon_rush", False),
            self._blackboard_get("enemy_proxy_detected", False),
        )
        if any(cannon_flags):
            return "ling_flood_anti_cannon"

        tech_flags = (
            self._blackboard_get("enemy_stargate_detected", False),
            self._blackboard_get("stargate_existence", False),
            self._blackboard_get("enemy_robo_detected", False),
            self._blackboard_get("robotics_facility", False),
        )
        if any(tech_flags):
            return "hydra_lair_macro"

        return "roach_rush"

    def _select_zvz_build(self) -> str:
        if self._blackboard_get("enemy_ling_flood_detected", False):
            return "roach_warren_macro"
        if self._blackboard_get("aggressive_opening", False) or self._blackboard_get(
            "use_12pool", False
        ):
            return "12pool_rush"
        return "safe_14pool"

    def _build_steps_from_order(self, order: List[tuple]) -> List[BuildOrderStep]:
        steps = []
        for supply, unit_type in order:
            action = self._infer_zvt_action(unit_type)
            steps.append(
                BuildOrderStep(
                    supply=supply,
                    action=action,
                    unit_type=unit_type,
                    description=f"ZvT {action} {unit_type}",
                )
            )
        return steps

    def _infer_zvt_action(self, unit_type: Any) -> str:
        if isinstance(unit_type, str):
            return "upgrade"
        if unit_type == getattr(UnitTypeId, "HATCHERY", None):
            return "expand"
        if unit_type == getattr(UnitTypeId, "LAIR", None):
            return "morph"
        train_types = {
            getattr(UnitTypeId, "DRONE", None),
            getattr(UnitTypeId, "OVERLORD", None),
            getattr(UnitTypeId, "QUEEN", None),
            getattr(UnitTypeId, "ZERGLING", None),
            getattr(UnitTypeId, "ROACH", None),
            getattr(UnitTypeId, "HYDRALISK", None),
        }
        if unit_type in train_types:
            return "train"
        return "build"

    def _parse_build_steps(self, steps_data: List[Dict]) -> List[BuildOrderStep]:
        """Parse JSON steps into objects"""
        parsed_steps = []
        for step in steps_data:
            try:
                # Convert string unit type to UnitTypeId enum
                unit_str = step["unit_type"]
                # Handle UnitTypeId attribute lookup safely
                if hasattr(UnitTypeId, unit_str):
                    unit_type = getattr(UnitTypeId, unit_str)
                else:
                    # Try uppercase just in case
                    unit_type = getattr(UnitTypeId, unit_str.upper())

                parsed_steps.append(
                    BuildOrderStep(
                        supply=step["supply"],
                        action=step["action"],
                        unit_type=unit_type,
                        description=step["description"],
                    )
                )
            except Exception as e:
                logger.info(f"Error parsing step {step}: {e}")
        return parsed_steps

    async def execute(self, iteration: int) -> None:
        """
        Execute build order every frame
        * Phase 25: 재시도 + 스킵 + 연성 종료 개선 *
        """
        # * Phase 25: 연성 종료 - 모든 스텝 완료 시 즉시 종료, 하드컷은 안전장치
        if self.current_step_index >= len(self.build_steps) and not self._skipped_steps:
            if self.build_order_active:
                self.build_order_active = False
                logger.info(f"All steps completed at {int(self.bot.time)}s")
                self._publish_build_complete()
            return

        if self.bot.time > self.build_order_end_time:
            if self.build_order_active:
                self.build_order_active = False
                skipped = len(self._skipped_steps)
                msg = f"[BUILD_ORDER] Time limit at {int(self.bot.time)}s"
                if skipped > 0:
                    msg += f" ({skipped} steps skipped)"
                logger.info(msg)
                self._publish_build_complete()
            return

        if not self.enabled or not self.build_order_active:
            return

        await self._check_dynamic_transition()

        # * Phase 25: 건너뛴 스텝 재시도 (매 16프레임)
        if iteration % 16 == 0 and self._skipped_steps:
            await self._retry_skipped_steps()

        # Check current supply
        current_supply = int(self.bot.supply_used)

        # Check next step
        if self.current_step_index >= len(self.build_steps):
            return

        current_step = self.build_steps[self.current_step_index]

        # Check supply requirement
        if current_supply >= current_step.supply:
            # Execute step
            success = await self._execute_step(current_step)

            if success:
                # Record timing
                self.step_timings[current_step.supply] = self.bot.time
                logger.info(
                    f"[OK] {current_step.supply} Supply: {current_step.description} (Timing: {int(self.bot.time)}s)"
                )

                # Next step
                current_step.completed = True
                self.current_step_index += 1
                self._step_retry_count = 0
            else:
                # * Phase 25: 재시도 카운터 - 일정 횟수 실패 시 스킵 후 다음 스텝
                self._step_retry_count += 1
                if self._should_hold_opening_expansion(current_step):
                    return
                if self._step_retry_count >= self._max_retries_before_skip:
                    logger.info(
                        f"[SKIP] {current_step.supply} Supply: {current_step.description} (retried {self._step_retry_count}x)"
                    )
                    self._skipped_steps.append(current_step)
                    self.current_step_index += 1
                    self._step_retry_count = 0

    def _should_hold_opening_expansion(self, step: BuildOrderStep) -> bool:
        """Keep the first hatchery step active until the economy can pay for it."""
        if step.action != "expand" or step.unit_type != UnitTypeId.HATCHERY:
            return False

        if getattr(self.bot, "time", 0.0) >= 120.0:
            return False

        townhalls = getattr(self.bot, "townhalls", None)
        if townhalls is not None and getattr(townhalls, "amount", 1) >= 2:
            return False

        already_pending = getattr(self.bot, "already_pending", None)
        if already_pending and already_pending(UnitTypeId.HATCHERY) > 0:
            return False

        return True

    async def _execute_step(self, step: BuildOrderStep) -> bool:
        """Execute Build Order Step"""
        try:
            if step.action == "build":
                return await self._build_structure(step.unit_type)
            elif step.action == "train":
                return await self._train_unit(step.unit_type)
            elif step.action == "expand":
                return await self._expand(step.unit_type)
            elif step.action == "morph":
                return await self._morph_unit(step.unit_type)
            elif step.action == "upgrade":
                return await self._research_upgrade(step.unit_type)
            return False
        except Exception as e:
            logger.error(f"Step Execution Failed: {e}")
            return False

    async def _build_structure(self, structure_type: UnitTypeId) -> bool:
        """Build Structure"""
        # Skip if already exists or pending
        if (
            structure_type != UnitTypeId.EXTRACTOR
            and self.bot.structures(structure_type).exists
        ):
            return True
        if self.bot.already_pending(structure_type) > 0:
            return True

        if structure_type == UnitTypeId.EXTRACTOR and self._should_delay_extractor():
            return False

        if (
            structure_type != UnitTypeId.HATCHERY
            and structure_type != UnitTypeId.SPAWNINGPOOL
            and self._should_reserve_third_base_minerals()
        ):
            return False

        # Check Resources
        if not self.bot.can_afford(structure_type):
            return False

        # Check Workers
        if not self.bot.workers:
            return False

        # Use TechCoordinator if available
        tech_coordinator = getattr(self.bot, "tech_coordinator", None)
        PRIORITY_BUILD_ORDER = 50

        # Build Spawning Pool
        if structure_type == UnitTypeId.SPAWNINGPOOL:
            if not self.bot.townhalls.exists:
                return False
            main_base = self.bot.townhalls.first
            # Calculate approx location
            pos = main_base.position.towards(self.bot.game_info.map_center, 5)

            if tech_coordinator:
                if not tech_coordinator.is_planned(structure_type):
                    tech_coordinator.request_structure(
                        UnitTypeId.SPAWNINGPOOL,
                        pos,
                        PRIORITY_BUILD_ORDER,
                        "BuildOrderSystem",
                    )
                    return True  # Request accepted, move to next step
            else:
                if not self.bot.workers.exists:
                    return False
                worker = self.bot.workers.random
                location = await self.bot.find_placement(
                    UnitTypeId.SPAWNINGPOOL, pos, max_distance=15, placement_step=2
                )
                if location:
                    self.bot.do(worker.build(UnitTypeId.SPAWNINGPOOL, location))
                    return True

        # Build Extractor
        elif structure_type == UnitTypeId.EXTRACTOR:
            if self.bot.townhalls:
                main_base = self.bot.townhalls.first
                geysers = self.bot.vespene_geyser.closer_than(10, main_base)
                built_any = False

                for geyser in geysers:
                    if not self.bot.structures(UnitTypeId.EXTRACTOR).closer_than(
                        1, geyser
                    ):
                        if tech_coordinator:
                            tech_coordinator.request_structure(
                                UnitTypeId.EXTRACTOR,
                                geyser,
                                PRIORITY_BUILD_ORDER,
                                "BuildOrderSystem",
                            )
                            built_any = True
                        else:
                            worker = self.bot.workers.closest_to(geyser)
                            if worker:
                                worker.build_gas(geyser)
                                built_any = True
                if built_any:
                    return True

        # General Structure Fallback (e.g. Roach Warren)
        else:
            if self.bot.townhalls:
                pos = self.bot.townhalls.first.position
                if tech_coordinator:
                    if not tech_coordinator.is_planned(structure_type):
                        tech_coordinator.request_structure(
                            structure_type,
                            pos,
                            PRIORITY_BUILD_ORDER,
                            "BuildOrderSystem",
                        )
                        return True
                else:
                    await self.bot.build(structure_type, near=pos)
                    return True

        return False

    async def _train_unit(self, unit_type: UnitTypeId) -> bool:
        """Train Unit"""
        if (
            unit_type != UnitTypeId.OVERLORD
            and self._should_reserve_third_base_minerals()
        ):
            return False

        # Check Resources
        if not self.bot.can_afford(unit_type):
            return False

        # Train Overlord
        if unit_type == UnitTypeId.OVERLORD:
            if self.bot.larva:
                larva = self.bot.larva.first
                self.bot.do(larva.train(UnitTypeId.OVERLORD))
                return True

        # Train Queen
        elif unit_type == UnitTypeId.QUEEN:
            # Check Spawning Pool
            if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
                return False

            # Find Idle Hatchery
            for hatchery in self.bot.townhalls.ready.idle:
                if self.bot.can_afford(UnitTypeId.QUEEN):
                    self.bot.do(hatchery.train(UnitTypeId.QUEEN))
                    return True

        # Train Zergling
        elif unit_type == UnitTypeId.ZERGLING:
            # Check Spawning Pool
            if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
                return False

            if self.bot.larva:
                larva = self.bot.larva.first
                self.bot.do(larva.train(UnitTypeId.ZERGLING))
                return True

        # Train Drone
        elif unit_type == UnitTypeId.DRONE:
            if self.bot.larva:
                larva = self.bot.larva.first
                self.bot.do(larva.train(UnitTypeId.DRONE))
                return True

        # * Phase 25: 일반 라바 유닛 (Roach, Hydra 등) *
        else:
            if self.bot.larva:
                larva = self.bot.larva.first
                self.bot.do(larva.train(unit_type))
                return True

        return False

    def _should_delay_extractor(self) -> bool:
        """Delay extra gas until Hatcheries are actually started."""
        townhalls = getattr(self.bot, "townhalls", None)
        try:
            base_count = int(getattr(townhalls, "amount", 1) or 1)
        except (TypeError, ValueError):
            base_count = 1

        already_pending = getattr(self.bot, "already_pending", lambda _: 0)
        pending_hatch = int(already_pending(UnitTypeId.HATCHERY) or 0)
        pending_gas = int(already_pending(UnitTypeId.EXTRACTOR) or 0)

        extractors = self.bot.structures(UnitTypeId.EXTRACTOR)
        try:
            extractor_count = int(getattr(extractors, "amount", 0) or 0)
        except (TypeError, ValueError):
            extractor_count = 0

        if base_count < 2 and pending_hatch == 0:
            return True
        if base_count < 3 and extractor_count + pending_gas >= 1:
            return True
        return False

    def _should_reserve_third_base_minerals(self) -> bool:
        """Hold non-essential spending until the third Hatchery is started."""
        if getattr(self.bot, "time", 0.0) < 150.0:
            return False

        base_count = self._count_bases()
        pending_hatch = self._pending_hatchery_count()

        if base_count >= 3:
            if getattr(self.bot, "time", 0.0) >= 360.0 and base_count < 4 and pending_hatch == 0:
                return not self._has_active_base_threat()
            return False
        if base_count < 2:
            return pending_hatch > 0 and not self._has_active_base_threat()
        if pending_hatch > 0:
            return False

        return not self._has_active_base_threat()

    def _count_bases(self) -> int:
        townhalls = getattr(self.bot, "townhalls", None)
        ready = getattr(townhalls, "ready", None) if townhalls else None

        for source in (ready, townhalls):
            if not source:
                continue
            amount = getattr(source, "amount", None)
            if isinstance(amount, (int, float)):
                return int(amount)
            if amount is not None:
                continue
            try:
                return len(list(source))
            except TypeError:
                pass

        return 1

    def _pending_hatchery_count(self) -> int:
        already_pending = getattr(self.bot, "already_pending", lambda _: 0)
        try:
            return int(already_pending(UnitTypeId.HATCHERY) or 0)
        except (TypeError, ValueError):
            return 0

    def _has_active_base_threat(self) -> bool:
        # 0.5s frame cache — avoids O(bases×enemies) on every mineral-reserve call
        current_time = getattr(self.bot, "time", 0.0)
        cached = getattr(self, "_threat_cache", None)
        if cached is not None and abs(current_time - cached[0]) < THREAT_CACHE_TTL:
            return cached[1]

        result = self.__has_active_base_threat_uncached()
        self._threat_cache = (current_time, result)
        return result

    def __has_active_base_threat_uncached(self) -> bool:
        enemy_units = getattr(self.bot, "enemy_units", None)
        townhalls = getattr(self.bot, "townhalls", None)
        if enemy_units is None or townhalls is None:
            return False

        try:
            bases = list(townhalls)
        except TypeError:
            first_base = getattr(townhalls, "first", None)
            bases = [first_base] if first_base else []

        for base in bases:
            if not base:
                continue
            try:
                nearby = enemy_units.closer_than(12, base)
            except Exception:
                continue

            amount = getattr(nearby, "amount", 0)
            if isinstance(amount, (int, float)) and amount > 0:
                return True
            try:
                if len(nearby) > 0:
                    return True
            except TypeError:
                pass

        return False

    async def _morph_unit(self, unit_type: UnitTypeId) -> bool:
        """Morph tech structures that are represented as build-order steps."""
        if self._should_reserve_third_base_minerals():
            return False

        if unit_type != getattr(UnitTypeId, "LAIR", None):
            return False
        if self.bot.structures(UnitTypeId.LAIR).exists:
            return True
        if self.bot.already_pending(UnitTypeId.LAIR) > 0:
            return True
        if not self.bot.can_afford(UnitTypeId.LAIR):
            return False
        if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready:
            return False

        townhalls = getattr(self.bot, "townhalls", None)
        ready_hatches = getattr(townhalls, "ready", None)
        if not ready_hatches:
            return False

        hatchery = getattr(ready_hatches, "idle", ready_hatches)
        if hasattr(hatchery, "first"):
            hatchery = hatchery.first
        elif hasattr(ready_hatches, "first"):
            hatchery = ready_hatches.first
        if not hatchery:
            return False

        self.bot.do(hatchery.build(UnitTypeId.LAIR))
        return True

    async def _research_upgrade(self, upgrade_name: str) -> bool:
        """Research upgrades referenced by string names in matchup build orders."""
        if self._should_reserve_third_base_minerals():
            return False

        if upgrade_name != "METABOLIC_BOOST":
            return False

        speed_upgrade = getattr(UpgradeId, "ZERGLINGMOVEMENTSPEED", None)
        upgrades = getattr(getattr(self.bot, "state", None), "upgrades", set())
        if speed_upgrade and speed_upgrade in upgrades:
            return True
        pending_fn = getattr(self.bot, "already_pending_upgrade", None)
        if speed_upgrade and pending_fn:
            try:
                if pending_fn(speed_upgrade) > 0:
                    return True
            except TypeError:
                pass

        pool_group = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
        if not pool_group:
            return False
        pool = pool_group.first if hasattr(pool_group, "first") else None
        if not pool:
            return False

        if not self.bot.can_afford(
            getattr(UpgradeId, "ZERGLINGMOVEMENTSPEED", upgrade_name)
        ):
            return False
        ability = getattr(AbilityId, "RESEARCH_ZERGLINGMETABOLICBOOST", None)
        if not ability:
            return False
        self.bot.do(pool(ability))
        return True

    async def _expand(self, structure_type: UnitTypeId) -> bool:
        """
        Expand Base
        * Phase 22: 확장 타이밍 기록 + 1분 멀티 검증 *
        """
        # Skip if already expanded
        if self.bot.townhalls.amount >= 2:
            if not self.expansion_timing_verified:
                self._verify_expansion_timing()
            return True
        if self.bot.already_pending(UnitTypeId.HATCHERY) > 0:
            if self.expansion_actual_time == 0:
                self.expansion_actual_time = self.bot.time
                logger.info(
                    f"[*] Natural expansion started at {int(self.bot.time)}s [*]"
                )
            return True

        # Check Resources
        if not self.bot.can_afford(UnitTypeId.HATCHERY):
            # * Phase 22: 1분 멀티 경고 - 60초 넘었는데 아직 확장 못 함 *
            if (
                self.bot.time > self.expansion_timing_target
                and self.expansion_actual_time == 0
            ):
                # * FIX: 스팸 방지 - 10초마다 1회만 출력
                if int(self.bot.time) % 10 == 0:
                    logger.warning(
                        f"[!] WARNING: Natural expansion delayed! ({int(self.bot.time)}s > {int(self.expansion_timing_target)}s target)"
                    )
            return False

        # Find Expansion Location. The first hatchery must be the closest
        # natural; BotAI.get_next_expansion can choose a distant safe base.
        location = None
        if self.bot.townhalls.amount < 2:
            location = await self._get_opening_natural_location()
        if not location:
            location = await self.bot.get_next_expansion()
        if location:
            # Use TechCoordinator if available
            tech_coordinator = getattr(self.bot, "tech_coordinator", None)
            PRIORITY_EXPANSION = 55  # * Phase 22: 확장 우선순위 상향 (50 -> 55)

            if tech_coordinator:
                if not tech_coordinator.is_planned(UnitTypeId.HATCHERY):
                    if not self.bot.workers.exists:
                        return False
                    worker = self.bot.workers.closest_to(location)
                    if not worker:
                        return False
                    self.bot.do(worker.build(UnitTypeId.HATCHERY, location))
                    self.expansion_actual_time = self.bot.time
                    logger.info(
                        f"[*] Natural expansion ordered at {int(self.bot.time)}s [*]"
                    )
                    return True
            else:
                if not self.bot.workers.exists:
                    return False
                worker = self.bot.workers.random
                if worker:
                    self.bot.do(worker.build(UnitTypeId.HATCHERY, location))
                    self.expansion_actual_time = self.bot.time
                    logger.info(
                        f"[*] Natural expansion ordered at {int(self.bot.time)}s [*]"
                    )
                    return True

        return False

    async def _get_opening_natural_location(self):
        """Return the closest untaken expansion to our start location."""
        if not hasattr(self.bot, "expansion_locations_list") or not hasattr(
            self.bot, "start_location"
        ):
            return None

        taken = []
        if hasattr(self.bot, "townhalls"):
            try:
                for townhall in self.bot.townhalls:
                    taken.append(getattr(townhall, "position", townhall))
            except TypeError:
                first = getattr(self.bot.townhalls, "first", None)
                if first:
                    taken.append(getattr(first, "position", first))

        candidates = []
        for location in self.bot.expansion_locations_list:
            if any(location.distance_to(taken_pos) < 5 for taken_pos in taken):
                continue
            candidates.append(location)

        candidates.sort(key=lambda pos: pos.distance_to(self.bot.start_location))
        for candidate in candidates:
            if hasattr(self.bot, "can_place"):
                try:
                    if not await self.bot.can_place(UnitTypeId.HATCHERY, candidate):
                        continue
                except (AttributeError, TypeError):
                    continue
            return candidate
        return None

    async def _retry_skipped_steps(self):
        """* Phase 25: 건너뛴 스텝 재시도 *"""
        still_skipped = []
        for step in self._skipped_steps:
            if step.completed:
                continue
            success = await self._execute_step(step)
            if success:
                step.completed = True
                logger.info(f"[RETRY OK] {step.supply} Supply: {step.description}")
            else:
                still_skipped.append(step)
        self._skipped_steps = still_skipped

    async def _check_dynamic_transition(self):
        """Publish dynamic build transitions without disrupting current step state."""
        blackboard = self.blackboard or getattr(self.bot, "blackboard", None)
        new_build = await self.transition_manager.check_transition(
            getattr(self.bot, "time", 0.0), blackboard
        )
        if not new_build:
            return

        self.current_matchup_build_key = new_build
        self.current_build_transition = new_build
        if blackboard and hasattr(blackboard, "set"):
            blackboard.set("matchup_build_key", new_build)
            blackboard.set("build_transition", new_build)
            blackboard.set("build_transition_reason", self.transition_manager.last_reason)
            blackboard.set(
                "build_transition_locked",
                self.transition_manager.transition_triggered,
            )

    def _publish_build_complete(self):
        """* Phase 25: 빌드오더 완료를 Blackboard에 전파 *"""
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard and hasattr(blackboard, "set"):
            blackboard.set("build_order_complete", True)
            blackboard.set("build_order_type", self.current_build_order.value)
            if self.current_matchup_build_key:
                blackboard.set("matchup_build_key", self.current_matchup_build_key)
            if self.current_build_transition:
                blackboard.set("build_transition", self.current_build_transition)

    def _verify_expansion_timing(self):
        """* Phase 22: 확장 타이밍 검증 *"""
        if self.expansion_timing_verified:
            return

        self.expansion_timing_verified = True
        actual = self.expansion_actual_time

        if actual == 0:
            logger.info(f"[!] Expansion timing: NOT RECORDED")
            return

        target = self.expansion_timing_target
        diff = actual - target

        if diff <= 5:
            logger.info(
                f"[OK] EXPANSION TIMING: {int(actual)}s (Target: {int(target)}s) - ON TIME"
            )
        elif diff <= 15:
            logger.info(
                f"[~] EXPANSION TIMING: {int(actual)}s (Target: {int(target)}s) - SLIGHTLY LATE (+{int(diff)}s)"
            )
        else:
            logger.info(
                f"[X] EXPANSION TIMING: {int(actual)}s (Target: {int(target)}s) - LATE (+{int(diff)}s)"
            )

    def select_build_order_by_win_rate(self) -> BuildOrderType:
        """Auto-select Build Order by Win Rate"""
        # Calculate Win Rates
        win_rates = {}
        for build_type, stats in self.build_order_stats.items():
            if stats["games"] > 0:
                win_rates[build_type] = stats["wins"] / stats["games"]
            else:
                win_rates[build_type] = 0.0

        # Select Best Build (Min 5 games)
        best_build = BuildOrderType.STANDARD_12POOL
        best_win_rate = 0.0

        for build_type, win_rate in win_rates.items():
            if (
                self.build_order_stats[build_type]["games"] >= 5
                and win_rate > best_win_rate
            ):
                best_build = build_type
                best_win_rate = win_rate

        return best_build

    def record_game_result(self, build_order: BuildOrderType, won: bool) -> None:
        """Record Game Result"""
        if build_order in self.build_order_stats:
            self.build_order_stats[build_order]["games"] += 1
            if won:
                self.build_order_stats[build_order]["wins"] += 1

    def get_progress(self) -> str:
        """Return Build Order Progress"""
        if not self.build_order_active:
            return "Build Order Complete"

        completed = sum(1 for step in self.build_steps if step.completed)
        total = len(self.build_steps)

        if total > 0:
            progress = f"{completed}/{total} ({int(completed/total*100)}%)"
        else:
            progress = "0/0"

        # Current Target
        if self.current_step_index < len(self.build_steps):
            next_step = self.build_steps[self.current_step_index]
            target = f"Next: {next_step.supply} Supply {next_step.description}"
        else:
            target = "All Steps Completed"

        return f"{progress} | {target}"

    def get_stats_summary(self) -> str:
        """Build Order Stats Summary"""
        lines = []
        lines.append("\n[BUILD_ORDER] === Build Order Stats ===")

        for build_type, stats in self.build_order_stats.items():
            games = stats["games"]
            wins = stats["wins"]
            win_rate = (wins / games * 100) if games > 0 else 0.0

            lines.append(f"  {build_type.value}: {wins}/{games} wins ({win_rate:.1f}%)")

        lines.append("=" * 40)
        return "\n".join(lines)
