"""
Regression lock: type annotations must not use the builtin ``any``
where ``typing.Any`` was intended.

``Dict[str, any]`` is a common copy-paste mistake — it parses (because
``any`` is a callable Python builtin), and at runtime it silently
evaluates to a ``Dict`` indexed by the *function object* ``any``. Static
type checkers reject it; readers misread it.

We had 5 of these in the bot tree before this lock landed (in
``advanced_micro_controller_v3.py``, ``combat/spatial_query_optimizer.py``,
``core/resource_manager.py``, ``economy/queen_transfusion_manager.py``,
``strategy/adaptive_build_order.py``). Keep them out.
"""

from __future__ import annotations

import ast
import builtins
from pathlib import Path

import pytest

WICKED = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


def _iter_bot_sources():
    """Yield every .py file under the bot package, excluding noise."""
    skip_parts = {"__pycache__", "monitoring", "tools", "tests", "docs"}
    for path in WICKED.rglob("*.py"):
        if any(part in skip_parts for part in path.parts):
            continue
        yield path


def _find_bare_any_annotations(source: str, path: Path):
    """
    Return (lineno, snippet) for every annotation that references the
    builtin ``any``. We look at the Name nodes inside annotation contexts
    only; comments/strings/docstrings don't count.
    """
    try:
        tree = ast.parse(source, str(path))
    except SyntaxError:
        return []

    offenders: list[tuple[int, str]] = []

    class Visitor(ast.NodeVisitor):
        def _check_annotation(self, ann):
            if ann is None:
                return
            for child in ast.walk(ann):
                if isinstance(child, ast.Name) and child.id == "any":
                    snippet = ast.unparse(ann)
                    offenders.append((child.lineno, snippet))

        def visit_FunctionDef(self, node):
            for arg in (*node.args.args, *node.args.kwonlyargs):
                self._check_annotation(arg.annotation)
            self._check_annotation(node.returns)
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_AnnAssign(self, node):
            self._check_annotation(node.annotation)
            self.generic_visit(node)

    Visitor().visit(tree)
    return offenders


def test_no_dict_str_any_typo_in_bot_sources():
    """No annotation under wicked_zerg_challenger/ may reference builtin any."""
    assert callable(builtins.any), "sanity: builtins.any still exists"

    offenders = []
    for path in _iter_bot_sources():
        text = path.read_text(encoding="utf-8")
        for lineno, snippet in _find_bare_any_annotations(text, path):
            offenders.append(f"{path.relative_to(WICKED)}:{lineno}: {snippet}")

    assert not offenders, (
        "Found annotations using builtin `any` instead of `typing.Any` "
        "— replace with `Any` (and import it from typing):\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "rel_path",
    [
        "advanced_micro_controller_v3.py",
        "combat/spatial_query_optimizer.py",
        "core/resource_manager.py",
        "economy/queen_transfusion_manager.py",
        "strategy/adaptive_build_order.py",
    ],
)
def test_previously_broken_files_now_use_typing_Any(rel_path):
    """
    Targeted check for the five files that historically had this typo.
    Lock the fix in even if the module-wide scan above misses something
    (e.g. annotation buried in an inner class).
    """
    text = (WICKED / rel_path).read_text(encoding="utf-8")
    tree = ast.parse(text, rel_path)
    bad = _find_bare_any_annotations(text, WICKED / rel_path)
    assert not bad, f"{rel_path} still uses builtin `any` in an annotation: {bad}"

    # And the file should import Any from typing (so the replacement actually works).
    has_any_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            if any(alias.name == "Any" for alias in node.names):
                has_any_import = True
                break
    assert has_any_import, f"{rel_path} should `from typing import ... Any`"
