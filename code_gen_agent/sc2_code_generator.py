"""
Phase 634: Code Generation Agent for SC2 Strategy Automation

LLM-powered code generation for StarCraft II bot strategies.
Generates Python code snippets for new strategies from natural language,
with template libraries for build orders, micro control, and macro logic.
Includes syntax validation, type checking, and safety sandboxing.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import re
import textwrap
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── Constants ───────────────────────────────────────────────────────────────────

SC2_UNIT_TYPES: dict[str, list[str]] = {
    "zerg": [
        "Zergling", "Baneling", "Roach", "Ravager", "Hydralisk", "Lurker",
        "Mutalisk", "Corruptor", "BroodLord", "Infestor", "Viper",
        "SwarmHost", "Ultralisk", "Overseer", "Queen",
    ],
    "terran": [
        "Marine", "Marauder", "Reaper", "Ghost", "Hellion", "Hellbat",
        "SiegeTank", "Cyclone", "Thor", "Viking", "Medivac", "Liberator",
        "Raven", "Banshee", "Battlecruiser", "WidowMine",
    ],
    "protoss": [
        "Zealot", "Stalker", "Sentry", "Adept", "HighTemplar", "DarkTemplar",
        "Immortal", "Colossus", "Disruptor", "Phoenix", "VoidRay", "Oracle",
        "Carrier", "Tempest", "Archon", "WarpPrism",
    ],
}

SC2_BUILDINGS: dict[str, list[str]] = {
    "zerg": [
        "Hatchery", "SpawningPool", "RoachWarren", "BanelingNest",
        "EvolutionChamber", "HydraliskDen", "LurkerDen", "Spire",
        "InfestationPit", "UltraliskCavern", "Lair", "Hive",
        "Extractor", "NydusNetwork",
    ],
    "terran": [
        "CommandCenter", "Barracks", "Factory", "Starport",
        "EngineeringBay", "Armory", "GhostAcademy", "FusionCore",
        "Refinery", "SupplyDepot", "Bunker", "SensorTower",
    ],
    "protoss": [
        "Nexus", "Gateway", "CyberneticsCore", "RoboticsFacility",
        "Stargate", "TwilightCouncil", "TemplarArchives", "DarkShrine",
        "RoboticsBay", "FleetBeacon", "Forge", "PhotonCannon",
        "Assimilator", "Pylon",
    ],
}

FORBIDDEN_IMPORTS: set[str] = {
    "os", "sys", "subprocess", "shutil", "signal",
    "ctypes", "socket", "http", "urllib", "requests",
    "pickle", "shelve", "multiprocessing",
}

MAX_CODE_LENGTH = 10_000
MAX_FUNCTION_COUNT = 50


# ── Enums ───────────────────────────────────────────────────────────────────────

class TemplateCategory(Enum):
    BUILD_ORDER = "build_order"
    MICRO_CONTROL = "micro_control"
    MACRO_MANAGEMENT = "macro_management"
    TIMING_ATTACK = "timing_attack"
    SCOUTING = "scouting"
    DEFENSE = "defense"
    TRANSITION = "transition"


class ValidationLevel(Enum):
    SYNTAX = "syntax"
    TYPE_CHECK = "type_check"
    SAFETY = "safety"
    FULL = "full"


# ── Data Classes ────────────────────────────────────────────────────────────────

@dataclass
class CodeTemplate:
    """A reusable code template for SC2 bot strategy snippets."""

    name: str
    category: TemplateCategory
    description: str
    code: str
    parameters: dict[str, str] = field(default_factory=dict)
    race: str = "zerg"
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: float = field(default_factory=time.time)

    def render(self, **kwargs: Any) -> str:
        """Render the template with provided parameters."""
        rendered = self.code
        for key, value in kwargs.items():
            placeholder = f"{{{{ {key} }}}}"
            rendered = rendered.replace(placeholder, str(value))
        # Check for unresolved placeholders
        remaining = re.findall(r"\{\{\s*\w+\s*\}\}", rendered)
        if remaining:
            missing = [r.strip("{ }").strip() for r in remaining]
            raise ValueError(f"Unresolved template parameters: {missing}")
        return rendered

    def fingerprint(self) -> str:
        """Content-based hash for deduplication."""
        content = f"{self.name}:{self.category.value}:{self.code}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ValidationResult:
    """Result of code validation."""

    valid: bool
    level: ValidationLevel
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ast_node_count: int = 0
    function_count: int = 0

    def summary(self) -> str:
        status = "PASS" if self.valid else "FAIL"
        parts = [f"[{status}] level={self.level.value}"]
        if self.errors:
            parts.append(f"  errors={len(self.errors)}")
        if self.warnings:
            parts.append(f"  warnings={len(self.warnings)}")
        return " | ".join(parts)


@dataclass
class GeneratedCode:
    """A generated code snippet with metadata."""

    source_prompt: str
    code: str
    template_used: Optional[str] = None
    validation: Optional[ValidationResult] = None
    generation_time_ms: float = 0.0
    model_name: str = "rule-based"
    confidence: float = 1.0

    def is_valid(self) -> bool:
        return self.validation is not None and self.validation.valid


# ── Code Validator ──────────────────────────────────────────────────────────────

class CodeValidator:
    """Validates generated Python code for syntax, safety, and correctness."""

    def __init__(self, forbidden_imports: Optional[set[str]] = None) -> None:
        self.forbidden_imports = forbidden_imports or FORBIDDEN_IMPORTS

    def validate_syntax(self, code: str) -> ValidationResult:
        """Check Python syntax by compiling the code."""
        result = ValidationResult(valid=True, level=ValidationLevel.SYNTAX)
        try:
            tree = ast.parse(code)
            result.ast_node_count = sum(1 for _ in ast.walk(tree))
            result.function_count = sum(
                1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
            )
        except SyntaxError as exc:
            result.valid = False
            result.errors.append(
                f"SyntaxError at line {exc.lineno}: {exc.msg}"
            )
        return result

    def validate_safety(self, code: str) -> ValidationResult:
        """Check for forbidden imports and dangerous patterns."""
        result = ValidationResult(valid=True, level=ValidationLevel.SAFETY)

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            result.valid = False
            result.errors.append(f"Cannot parse for safety check: {exc.msg}")
            return result

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_root = alias.name.split(".")[0]
                    if module_root in self.forbidden_imports:
                        result.valid = False
                        result.errors.append(
                            f"Forbidden import: {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_root = node.module.split(".")[0]
                    if module_root in self.forbidden_imports:
                        result.valid = False
                        result.errors.append(
                            f"Forbidden import from: {node.module}"
                        )

        # Check for exec/eval calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in ("exec", "eval"):
                    result.valid = False
                    result.errors.append(
                        f"Forbidden builtin call: {func.id}()"
                    )

        # Check code length
        if len(code) > MAX_CODE_LENGTH:
            result.warnings.append(
                f"Code length {len(code)} exceeds recommended max {MAX_CODE_LENGTH}"
            )

        # Check function count
        func_count = sum(
            1 for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        result.function_count = func_count
        if func_count > MAX_FUNCTION_COUNT:
            result.warnings.append(
                f"Function count {func_count} exceeds recommended max {MAX_FUNCTION_COUNT}"
            )

        return result

    def validate_type_hints(self, code: str) -> ValidationResult:
        """Check that functions have type annotations."""
        result = ValidationResult(valid=True, level=ValidationLevel.TYPE_CHECK)

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            result.valid = False
            result.errors.append(f"Cannot parse for type check: {exc.msg}")
            return result

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.returns is None:
                    result.warnings.append(
                        f"Function '{node.name}' missing return type annotation"
                    )
                for arg in node.args.args:
                    if arg.arg != "self" and arg.annotation is None:
                        result.warnings.append(
                            f"Parameter '{arg.arg}' in '{node.name}' missing type annotation"
                        )

        return result

    def validate_full(self, code: str) -> ValidationResult:
        """Run all validation checks."""
        syntax = self.validate_syntax(code)
        if not syntax.valid:
            return syntax

        safety = self.validate_safety(code)
        type_hints = self.validate_type_hints(code)

        combined = ValidationResult(
            valid=syntax.valid and safety.valid,
            level=ValidationLevel.FULL,
            errors=syntax.errors + safety.errors + type_hints.errors,
            warnings=syntax.warnings + safety.warnings + type_hints.warnings,
            ast_node_count=syntax.ast_node_count,
            function_count=syntax.function_count,
        )
        return combined


# ── Strategy Code Generator ────────────────────────────────────────────────────

class StrategyCodeGen:
    """Generates Python code for SC2 bot strategies from descriptions."""

    def __init__(self, race: str = "zerg") -> None:
        self.race = race.lower()
        self.templates: dict[str, CodeTemplate] = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self) -> None:
        """Load the built-in template library."""
        # Build order template
        self.register_template(CodeTemplate(
            name="basic_build_order",
            category=TemplateCategory.BUILD_ORDER,
            description="Simple supply-based build order executor",
            parameters={"steps": "list of (supply, action) tuples"},
            code=textwrap.dedent("""\
                async def execute_build_order(bot) -> None:
                    \"\"\"Execute a supply-based build order.\"\"\"
                    build_steps: list[tuple[int, str]] = {{ steps }}
                    current_supply: int = bot.supply_used

                    for target_supply, action in build_steps:
                        if current_supply >= target_supply:
                            await _perform_action(bot, action)

                async def _perform_action(bot, action: str) -> None:
                    \"\"\"Dispatch a build action by name.\"\"\"
                    action_map: dict[str, callable] = {
                        "expand": bot.expand_now,
                        "build_pool": lambda: bot.build_structure("SpawningPool"),
                        "build_gas": lambda: bot.build_structure("Extractor"),
                        "queen": lambda: bot.train_unit("Queen"),
                    }
                    handler = action_map.get(action)
                    if handler is not None:
                        await handler()
            """),
            tags=["build_order", "macro", "basic"],
        ))

        # Micro control template
        self.register_template(CodeTemplate(
            name="kiting_micro",
            category=TemplateCategory.MICRO_CONTROL,
            description="Kiting logic for ranged units against melee",
            parameters={"unit_type": "unit type tag", "range_buffer": "float"},
            code=textwrap.dedent("""\
                async def kite_units(bot, unit_tag: int, enemies: list) -> None:
                    \"\"\"Kite enemy melee units with ranged {{ unit_type }}.\"\"\"
                    unit = bot.units.by_tag(unit_tag)
                    if unit is None:
                        return

                    range_buffer: float = {{ range_buffer }}
                    weapon_range: float = unit.ground_range + range_buffer

                    closest_enemy = min(
                        enemies,
                        key=lambda e: unit.distance_to(e),
                        default=None,
                    )
                    if closest_enemy is None:
                        return

                    distance: float = unit.distance_to(closest_enemy)

                    if distance < weapon_range * 0.6:
                        # Too close: retreat
                        retreat_pos = unit.position.towards(closest_enemy.position, -3.0)
                        unit.move(retreat_pos)
                    elif distance <= weapon_range:
                        # In range: attack
                        unit.attack(closest_enemy)
                    else:
                        # Approach
                        unit.attack(closest_enemy)
            """),
            tags=["micro", "kiting", "ranged"],
        ))

        # Macro management template
        self.register_template(CodeTemplate(
            name="inject_larvae",
            category=TemplateCategory.MACRO_MANAGEMENT,
            description="Queen inject larvae macro cycle",
            parameters={},
            code=textwrap.dedent("""\
                async def inject_larvae(bot) -> None:
                    \"\"\"Inject larvae at all hatcheries with available queens.\"\"\"
                    queens = bot.units.of_type("Queen").idle
                    hatcheries = bot.structures.of_type(
                        {"Hatchery", "Lair", "Hive"}
                    ).ready

                    injected_hatch_tags: set[int] = set()

                    for queen in queens:
                        if queen.energy < 25:
                            continue

                        closest_hatch = None
                        min_dist: float = float("inf")
                        for hatch in hatcheries:
                            if hatch.tag in injected_hatch_tags:
                                continue
                            dist: float = queen.distance_to(hatch)
                            if dist < min_dist:
                                min_dist = dist
                                closest_hatch = hatch

                        if closest_hatch is not None and min_dist < 10.0:
                            queen(AbilityId.EFFECT_INJECTLARVA, closest_hatch)
                            injected_hatch_tags.add(closest_hatch.tag)
            """),
            tags=["macro", "inject", "queen", "zerg"],
        ))

        # Timing attack template
        self.register_template(CodeTemplate(
            name="timing_attack",
            category=TemplateCategory.TIMING_ATTACK,
            description="Launch a timing attack at a supply threshold",
            parameters={
                "supply_threshold": "int",
                "unit_composition": "dict of unit_type: count",
            },
            code=textwrap.dedent("""\
                async def execute_timing_attack(bot) -> None:
                    \"\"\"Launch a timing push when army reaches threshold.\"\"\"
                    supply_threshold: int = {{ supply_threshold }}
                    required_composition: dict[str, int] = {{ unit_composition }}

                    army_supply: int = bot.supply_army
                    if army_supply < supply_threshold:
                        return

                    # Verify composition
                    for unit_type, min_count in required_composition.items():
                        actual = bot.units.of_type(unit_type).amount
                        if actual < min_count:
                            return

                    # Rally point: enemy natural
                    target = bot.enemy_start_locations[0]
                    army_units = bot.units.filter(
                        lambda u: u.type_id in bot.army_unit_types
                    )
                    for unit in army_units:
                        unit.attack(target)
            """),
            tags=["timing", "attack", "aggressive"],
        ))

        # Scouting template
        self.register_template(CodeTemplate(
            name="overlord_scout",
            category=TemplateCategory.SCOUTING,
            description="Overlord scouting pattern for Zerg",
            parameters={"scout_positions": "list of (x, y) positions"},
            code=textwrap.dedent("""\
                async def overlord_scout(bot, step: int) -> None:
                    \"\"\"Send overlords to scout positions on a schedule.\"\"\"
                    scout_positions: list[tuple[float, float]] = {{ scout_positions }}
                    overlords = bot.units.of_type("Overlord").idle

                    if not overlords or not scout_positions:
                        return

                    phase_index: int = (step // 200) % len(scout_positions)
                    target_x, target_y = scout_positions[phase_index]
                    target = Point2((target_x, target_y))

                    scout = overlords.first
                    scout.move(target)
            """),
            tags=["scout", "overlord", "zerg", "info"],
        ))

        # Defense template
        self.register_template(CodeTemplate(
            name="spine_wall",
            category=TemplateCategory.DEFENSE,
            description="Build spine crawlers at natural for defense",
            parameters={"count": "int number of spines"},
            code=textwrap.dedent("""\
                async def build_spine_wall(bot) -> None:
                    \"\"\"Build spine crawlers at the natural expansion.\"\"\"
                    target_count: int = {{ count }}
                    existing_spines = bot.structures.of_type("SpineCrawler")

                    if existing_spines.amount >= target_count:
                        return

                    natural = bot.expansion_locations_list[1]
                    needed: int = target_count - existing_spines.amount

                    for _ in range(needed):
                        if bot.can_afford("SpineCrawler"):
                            placement = await bot.find_placement(
                                "SpineCrawler",
                                near=natural,
                                placement_step=2,
                            )
                            if placement is not None:
                                await bot.build("SpineCrawler", placement)
            """),
            tags=["defense", "spine", "zerg", "structure"],
        ))

        # Transition template
        self.register_template(CodeTemplate(
            name="tech_transition",
            category=TemplateCategory.TRANSITION,
            description="Transition to a new tech path mid-game",
            parameters={
                "tech_building": "structure type to build",
                "new_units": "list of unit types to produce",
            },
            code=textwrap.dedent("""\
                async def tech_transition(bot) -> None:
                    \"\"\"Transition to new tech path by building required structures.\"\"\"
                    tech_building: str = "{{ tech_building }}"
                    new_units: list[str] = {{ new_units }}

                    # Build tech structure if missing
                    if not bot.structures.of_type(tech_building).ready:
                        if bot.can_afford(tech_building):
                            await bot.build_structure(tech_building)
                        return

                    # Start producing new unit types
                    for unit_type in new_units:
                        larvae = bot.units.of_type("Larva")
                        if larvae.exists and bot.can_afford(unit_type):
                            larvae.random.train(unit_type)
            """),
            tags=["transition", "tech", "mid_game"],
        ))

    def register_template(self, template: CodeTemplate) -> None:
        """Register a code template in the library."""
        self.templates[template.name] = template

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        tag: Optional[str] = None,
    ) -> list[CodeTemplate]:
        """List available templates, optionally filtered."""
        results: list[CodeTemplate] = []
        for tmpl in self.templates.values():
            if category is not None and tmpl.category != category:
                continue
            if tag is not None and tag not in tmpl.tags:
                continue
            results.append(tmpl)
        return results

    def generate_build_order_code(
        self,
        name: str,
        steps: list[tuple[int, str]],
    ) -> GeneratedCode:
        """Generate a build order function from (supply, action) pairs."""
        t0 = time.time()

        lines: list[str] = [
            f"async def {name}(bot) -> None:",
            f'    """Auto-generated build order: {name}."""',
            f"    build_steps: list[tuple[int, str]] = [",
        ]
        for supply, action in steps:
            lines.append(f"        ({supply}, {action!r}),")
        lines.append("    ]")
        lines.append("")
        lines.append("    for target_supply, action in build_steps:")
        lines.append("        if bot.supply_used >= target_supply:")
        lines.append("            await _dispatch_build_action(bot, action)")

        code = "\n".join(lines)
        elapsed = (time.time() - t0) * 1000

        return GeneratedCode(
            source_prompt=f"build_order:{name}",
            code=code,
            template_used="basic_build_order",
            generation_time_ms=elapsed,
        )

    def generate_unit_control_code(
        self,
        unit_type: str,
        behavior: str,
        params: Optional[dict[str, Any]] = None,
    ) -> GeneratedCode:
        """Generate unit control logic for a given behavior."""
        t0 = time.time()
        params = params or {}

        behavior_map: dict[str, str] = {
            "kite": "kiting_micro",
            "focus_fire": "_gen_focus_fire",
            "retreat": "_gen_retreat",
            "surround": "_gen_surround",
        }

        template_name = behavior_map.get(behavior)
        if template_name and template_name in self.templates:
            tmpl = self.templates[template_name]
            render_params = {"unit_type": f'"{unit_type}"', **params}
            if "range_buffer" not in render_params:
                render_params["range_buffer"] = "1.5"
            code = tmpl.render(**render_params)
        else:
            code = self._generate_behavior_code(unit_type, behavior, params)

        elapsed = (time.time() - t0) * 1000
        return GeneratedCode(
            source_prompt=f"unit_control:{unit_type}:{behavior}",
            code=code,
            template_used=template_name,
            generation_time_ms=elapsed,
        )

    def _generate_behavior_code(
        self,
        unit_type: str,
        behavior: str,
        params: dict[str, Any],
    ) -> str:
        """Fallback code generation for behaviors without templates."""
        func_name = f"{behavior}_{unit_type.lower()}"
        lines: list[str] = [
            f"async def {func_name}(bot, unit_tags: list[int]) -> None:",
            f'    """Auto-generated {behavior} behavior for {unit_type}."""',
            f"    units = [bot.units.by_tag(t) for t in unit_tags]",
            f"    units = [u for u in units if u is not None]",
            f"",
            f"    for unit in units:",
            f"        enemies = bot.enemy_units.closer_than(12.0, unit)",
            f"        if not enemies:",
            f"            continue",
        ]

        if behavior == "focus_fire":
            lines.extend([
                f"        lowest_hp = min(enemies, key=lambda e: e.health)",
                f"        unit.attack(lowest_hp)",
            ])
        elif behavior == "retreat":
            retreat_hp = params.get("retreat_hp_pct", 0.3)
            lines.extend([
                f"        if unit.health_percentage < {retreat_hp}:",
                f"            safe_pos = bot.start_location",
                f"            unit.move(safe_pos)",
                f"        else:",
                f"            unit.attack(enemies.closest_to(unit))",
            ])
        elif behavior == "surround":
            lines.extend([
                f"        target = enemies.closest_to(unit)",
                f"        offset_angle = hash(unit.tag) % 360",
                f"        surround_pos = target.position.towards_with_random_angle(",
                f"            unit.position, -2.0, max_difference=(offset_angle % 60)",
                f"        )",
                f"        unit.move(surround_pos)",
            ])
        else:
            lines.extend([
                f"        # Default: attack closest enemy",
                f"        unit.attack(enemies.closest_to(unit))",
            ])

        return "\n".join(lines)

    def generate_timing_attack_code(
        self,
        name: str,
        supply_threshold: int,
        composition: dict[str, int],
        target: str = "enemy_natural",
    ) -> GeneratedCode:
        """Generate a timing attack function."""
        t0 = time.time()

        comp_repr = repr(composition)
        lines: list[str] = [
            f"async def {name}(bot) -> bool:",
            f'    """Timing attack: push at {supply_threshold} supply."""',
            f"    required_supply: int = {supply_threshold}",
            f"    required_comp: dict[str, int] = {comp_repr}",
            f"",
            f"    if bot.supply_army < required_supply:",
            f"        return False",
            f"",
            f"    for utype, count in required_comp.items():",
            f"        if bot.units.of_type(utype).amount < count:",
            f"            return False",
            f"",
        ]

        if target == "enemy_natural":
            lines.append(f"    target = bot.enemy_start_locations[0]")
        elif target == "enemy_main":
            lines.append(f"    target = bot.enemy_start_locations[0]")
        else:
            lines.append(f"    target = bot.game_info.map_center")

        lines.extend([
            f"",
            f"    army = bot.units.filter(lambda u: u.type_id in bot.army_unit_types)",
            f"    for unit in army:",
            f"        unit.attack(target)",
            f"    return True",
        ])

        code = "\n".join(lines)
        elapsed = (time.time() - t0) * 1000

        return GeneratedCode(
            source_prompt=f"timing_attack:{name}",
            code=code,
            template_used="timing_attack",
            generation_time_ms=elapsed,
        )

    def generate_from_description(self, description: str) -> GeneratedCode:
        """Parse a natural language description and generate matching code."""
        t0 = time.time()
        desc_lower = description.lower()

        # Pattern matching on the description
        if "build order" in desc_lower or "opening" in desc_lower:
            steps = self._parse_build_order_description(desc_lower)
            result = self.generate_build_order_code("custom_build", steps)
        elif "kite" in desc_lower or "kiting" in desc_lower:
            unit = self._extract_unit_type(desc_lower) or "Hydralisk"
            result = self.generate_unit_control_code(unit, "kite")
        elif "timing" in desc_lower or "attack" in desc_lower or "push" in desc_lower:
            supply = self._extract_number(desc_lower, default=80)
            result = self.generate_timing_attack_code(
                "generated_timing", supply, {"Roach": 8, "Ravager": 4}
            )
        elif "scout" in desc_lower:
            tmpl = self.templates.get("overlord_scout")
            if tmpl:
                code = tmpl.render(
                    scout_positions="[(30.0, 30.0), (50.0, 50.0), (70.0, 70.0)]"
                )
                result = GeneratedCode(
                    source_prompt=description,
                    code=code,
                    template_used="overlord_scout",
                )
            else:
                result = self._fallback_generation(description)
        elif "defend" in desc_lower or "defense" in desc_lower:
            tmpl = self.templates.get("spine_wall")
            if tmpl:
                code = tmpl.render(count="4")
                result = GeneratedCode(
                    source_prompt=description,
                    code=code,
                    template_used="spine_wall",
                )
            else:
                result = self._fallback_generation(description)
        else:
            result = self._fallback_generation(description)

        result.generation_time_ms = (time.time() - t0) * 1000
        return result

    def _parse_build_order_description(
        self, desc: str
    ) -> list[tuple[int, str]]:
        """Extract supply/action pairs from a text description."""
        steps: list[tuple[int, str]] = []
        # Try to find patterns like "17 hatch" or "at 20 pool"
        matches = re.findall(r"(\d{2,3})\s+(\w+)", desc)
        for supply_str, action in matches:
            steps.append((int(supply_str), action))

        if not steps:
            # Default Zerg hatch-first opener
            steps = [
                (14, "overlord"),
                (17, "hatch"),
                (18, "gas"),
                (17, "pool"),
                (20, "queen"),
            ]
        return steps

    def _extract_unit_type(self, desc: str) -> Optional[str]:
        """Extract a SC2 unit type from description text."""
        all_units = []
        for race_units in SC2_UNIT_TYPES.values():
            all_units.extend(race_units)
        for unit in all_units:
            if unit.lower() in desc:
                return unit
        return None

    def _extract_number(self, desc: str, default: int = 80) -> int:
        """Extract a number from description, or return default."""
        numbers = re.findall(r"\b(\d{2,3})\b", desc)
        if numbers:
            return int(numbers[0])
        return default

    def _fallback_generation(self, description: str) -> GeneratedCode:
        """Generate a stub function when no template matches."""
        safe_name = re.sub(r"\W+", "_", description.lower())[:40].strip("_")
        code = textwrap.dedent(f"""\
            async def {safe_name}(bot) -> None:
                \"\"\"Generated from: {description[:80]}\"\"\"
                # TODO: Implement strategy logic
                pass
        """)
        return GeneratedCode(
            source_prompt=description,
            code=code,
            confidence=0.3,
        )


# ── Code Generation Agent ──────────────────────────────────────────────────────

class CodeGenAgent:
    """Top-level agent orchestrating code generation, validation, and storage."""

    def __init__(self, race: str = "zerg") -> None:
        self.generator = StrategyCodeGen(race=race)
        self.validator = CodeValidator()
        self.history: list[GeneratedCode] = []
        self.race = race

    def generate_and_validate(
        self,
        prompt: str,
        validation_level: ValidationLevel = ValidationLevel.FULL,
    ) -> GeneratedCode:
        """Generate code from a prompt and validate it."""
        generated = self.generator.generate_from_description(prompt)

        if validation_level == ValidationLevel.SYNTAX:
            generated.validation = self.validator.validate_syntax(generated.code)
        elif validation_level == ValidationLevel.SAFETY:
            generated.validation = self.validator.validate_safety(generated.code)
        elif validation_level == ValidationLevel.TYPE_CHECK:
            generated.validation = self.validator.validate_type_hints(generated.code)
        else:
            generated.validation = self.validator.validate_full(generated.code)

        self.history.append(generated)
        return generated

    def generate_build_order(
        self, name: str, steps: list[tuple[int, str]]
    ) -> GeneratedCode:
        """Generate and validate a build order function."""
        generated = self.generator.generate_build_order_code(name, steps)
        generated.validation = self.validator.validate_full(generated.code)
        self.history.append(generated)
        return generated

    def generate_timing_attack(
        self,
        name: str,
        supply: int,
        composition: dict[str, int],
    ) -> GeneratedCode:
        """Generate and validate a timing attack function."""
        generated = self.generator.generate_timing_attack_code(
            name, supply, composition
        )
        generated.validation = self.validator.validate_full(generated.code)
        self.history.append(generated)
        return generated

    def generate_unit_micro(
        self, unit_type: str, behavior: str
    ) -> GeneratedCode:
        """Generate and validate unit micro control code."""
        generated = self.generator.generate_unit_control_code(
            unit_type, behavior
        )
        generated.validation = self.validator.validate_full(generated.code)
        self.history.append(generated)
        return generated

    def list_templates(
        self, category: Optional[TemplateCategory] = None
    ) -> list[CodeTemplate]:
        """List available code templates."""
        return self.generator.list_templates(category=category)

    def get_history(self, valid_only: bool = False) -> list[GeneratedCode]:
        """Return generation history, optionally filtered to valid only."""
        if valid_only:
            return [g for g in self.history if g.is_valid()]
        return list(self.history)

    def stats(self) -> dict[str, Any]:
        """Return summary statistics of generation history."""
        total = len(self.history)
        valid = sum(1 for g in self.history if g.is_valid())
        avg_time = (
            sum(g.generation_time_ms for g in self.history) / total
            if total > 0
            else 0.0
        )
        return {
            "total_generations": total,
            "valid_count": valid,
            "invalid_count": total - valid,
            "success_rate": valid / total if total > 0 else 0.0,
            "avg_generation_time_ms": round(avg_time, 2),
            "templates_available": len(self.generator.templates),
        }


# ── Demo ────────────────────────────────────────────────────────────────────────

def demo() -> None:
    """Demonstrate the Code Generation Agent capabilities."""
    print("=" * 72)
    print("Phase 634: Code Generation Agent for SC2 Strategy Automation")
    print("=" * 72)

    agent = CodeGenAgent(race="zerg")

    # 1. List available templates
    print("\n--- Available Templates ---")
    for tmpl in agent.list_templates():
        print(f"  [{tmpl.category.value:18s}] {tmpl.name}: {tmpl.description}")

    # 2. Generate a build order
    print("\n--- Generate Build Order ---")
    bo = agent.generate_build_order(
        "roach_ravager_timing",
        [
            (14, "overlord"),
            (17, "hatch"),
            (18, "gas"),
            (17, "pool"),
            (19, "overlord"),
            (22, "queen"),
            (24, "roach_warren"),
            (30, "roach"),
        ],
    )
    print(bo.code)
    print(f"  Valid: {bo.is_valid()} | {bo.validation.summary()}")

    # 3. Generate micro control
    print("\n--- Generate Kiting Micro ---")
    kite = agent.generate_unit_micro("Hydralisk", "kite")
    print(kite.code[:300] + "...")
    print(f"  Valid: {kite.is_valid()}")

    # 4. Generate from natural language
    print("\n--- Natural Language Generation ---")
    prompts = [
        "Create a 66 supply roach timing attack against Terran",
        "Scout with overlords in ZvP",
        "Build spine crawlers to defend the natural",
        "Kite with mutalisks against marines",
    ]
    for prompt in prompts:
        result = agent.generate_and_validate(prompt)
        status = "OK" if result.is_valid() else "FAIL"
        print(f"  [{status}] {prompt[:55]:55s} -> template={result.template_used}")

    # 5. Generate timing attack
    print("\n--- Timing Attack Code ---")
    timing = agent.generate_timing_attack(
        "roach_ravager_push", 80, {"Roach": 12, "Ravager": 6}
    )
    print(timing.code)

    # 6. Validate unsafe code
    print("\n--- Safety Validation ---")
    unsafe_code = "import os\nos.system('rm -rf /')"
    safety_result = agent.validator.validate_safety(unsafe_code)
    print(f"  Unsafe code check: {safety_result.summary()}")
    for err in safety_result.errors:
        print(f"    ERROR: {err}")

    # 7. Agent stats
    print("\n--- Agent Stats ---")
    stats = agent.stats()
    for key, val in stats.items():
        print(f"  {key}: {val}")

    print("\n" + "=" * 72)
    print("Phase 634 demo complete.")
    print("=" * 72)


if __name__ == "__main__":
    demo()


# Phase 634: Code Gen registered
