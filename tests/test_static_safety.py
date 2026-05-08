"""Static-analysis regression tests for known historical bugs.

Each test here pins a specific class of bug we previously fixed so it cannot
silently reappear. Tests parse source files with ``ast`` only — no runtime
imports of bot modules, so they work in any environment.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _function_locally_imports(node: ast.AST, module: str) -> bool:
    """Return True if ``node`` (a function body) contains an ``import <module>``.

    Any nested function bodies are skipped because they have their own scope.
    """
    for child in ast.walk(node):
        # Don't descend into nested functions — they have their own scope.
        if child is node:
            continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # ast.walk would still descend into this; we filter here.
            # (This is best-effort; the main check below handles the common case.)
            continue
        if isinstance(child, ast.Import):
            for alias in child.names:
                if (alias.asname or alias.name).split(".")[0] == module:
                    return True
        elif isinstance(child, ast.ImportFrom):
            if child.module and child.module.split(".")[0] == module:
                return True
    return False


def _module_imports(tree: ast.Module, module: str) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (alias.asname or alias.name).split(".")[0] == module:
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == module:
                return True
    return False


def test_no_local_traceback_shadow_in_bot_pro_impl():
    """`import traceback` inside an on_end-style handler shadows the
    module-level binding for the *entire* function, raising
    UnboundLocalError on earlier ``traceback.print_exc()`` calls.

    Regression for: wicked_zerg_bot_pro_impl.py — second except block in
    ``on_end`` re-imported traceback even though the module already imports
    it at the top, breaking the first except block in the same function.
    """
    src_path = REPO_ROOT / "wicked_zerg_challenger" / "wicked_zerg_bot_pro_impl.py"
    if not src_path.exists():  # repo layout drift — don't fail the suite.
        pytest.skip(f"{src_path} not present")

    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    assert _module_imports(
        tree, "traceback"
    ), "traceback must remain imported at module level for the existing usages"

    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for inner in ast.walk(node):
                if inner is node:
                    continue
                if isinstance(inner, ast.Import):
                    for alias in inner.names:
                        head = (alias.asname or alias.name).split(".")[0]
                        if head == "traceback":
                            offenders.append(f"{node.name}:{inner.lineno}")
                elif isinstance(inner, ast.ImportFrom):
                    if inner.module and inner.module.split(".")[0] == "traceback":
                        offenders.append(f"{node.name}:{inner.lineno}")

    assert not offenders, (
        "Local 'import traceback' inside a function shadows the module-level "
        "import and breaks earlier `traceback.print_exc()` calls in the same "
        f"function. Offenders: {offenders}"
    )


def _class_method_names(tree: ast.Module, class_name: str) -> list[tuple[str, int]]:
    """Return [(method_name, lineno), …] for every method directly defined on
    ``class_name`` — including duplicates (later defs shadow earlier ones)."""
    out: list[tuple[str, int]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append((item.name, item.lineno))
    return out


def test_no_duplicate_methods_on_opponent_modeling():
    """OpponentModeling had two `on_step` definitions; Python silently kept
    the second (a 5-line stub) and discarded the rich one (build-order
    tracking + timing-attack detection + tech-progression + blackboard
    push). Same class also had inconsistent `current_opponent` /
    `current_opponent_id` attribute naming feeding the dead vs live path.

    Pin: no method on OpponentModeling may be defined twice.
    """
    src_path = REPO_ROOT / "wicked_zerg_challenger" / "opponent_modeling.py"
    if not src_path.exists():
        pytest.skip(f"{src_path} not present")

    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    methods = _class_method_names(tree, "OpponentModeling")
    seen: dict[str, int] = {}
    dups: list[str] = []
    for name, lineno in methods:
        if name in seen:
            dups.append(f"{name}: lines {seen[name]} and {lineno}")
        else:
            seen[name] = lineno

    assert not dups, (
        "OpponentModeling has duplicate method definitions — Python keeps "
        f"only the last one and silently drops the others: {dups}"
    )


def test_no_duplicate_methods_on_production_resilience():
    """ProductionResilience had two `build_terran_counters` definitions;
    the first was older code with no TechCoordinator integration and was
    silently shadowed by the later one. Pin against re-introduction."""
    src_path = (
        REPO_ROOT
        / "wicked_zerg_challenger"
        / "local_training"
        / "production_resilience.py"
    )
    if not src_path.exists():
        pytest.skip(f"{src_path} not present")

    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    # The class name here is ProductionResilience per the file structure;
    # we don't hard-code it: we walk every class.
    dups_by_class: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        seen: dict[str, int] = {}
        cls_dups: list[str] = []
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name in seen:
                cls_dups.append(
                    f"{item.name}: lines {seen[item.name]} and {item.lineno}"
                )
            else:
                seen[item.name] = item.lineno
        if cls_dups:
            dups_by_class[node.name] = cls_dups

    assert not dups_by_class, (
        "Duplicate method definitions in production_resilience.py — Python "
        f"keeps only the last and drops the others: {dups_by_class}"
    )


def test_opponent_modeling_uses_canonical_attribute_names():
    """The OpponentModeling class previously had a split between
    ``current_opponent`` (set by ``on_game_start``, used by 4 trailing
    methods) and ``current_opponent_id`` (set by ``__init__``/``on_start``,
    used by the rich code path). Either branch silently broke the other.

    Pin: the source must not reference the legacy ``self.current_opponent``
    name anywhere — only ``self.current_opponent_id``. Also pin against
    referencing the legacy ``models`` attribute (real name:
    ``opponent_models``).
    """
    src_path = REPO_ROOT / "wicked_zerg_challenger" / "opponent_modeling.py"
    bot_path = REPO_ROOT / "wicked_zerg_challenger" / "wicked_zerg_bot_pro_impl.py"
    for path in (src_path, bot_path):
        if not path.exists():
            pytest.skip(f"{path} not present")

    legacy_attr = "current_opponent"
    canonical_attr = "current_opponent_id"

    for path in (src_path, bot_path):
        text = path.read_text(encoding="utf-8")
        # Strip the canonical name, then look for the legacy bare form.
        stripped = text.replace(canonical_attr, "<<CANON>>")
        # Also tolerate the descriptor-style access via the manager attribute name.
        bad_lines = [
            (i + 1, line)
            for i, line in enumerate(stripped.splitlines())
            if f".{legacy_attr}" in line and "<<CANON>>" not in line
        ]
        assert not bad_lines, (
            f"{path.name} still references the legacy `.{legacy_attr}` "
            f"attribute. Use `.{canonical_attr}` instead. Hits: {bad_lines}"
        )
