# -*- coding: utf-8 -*-
"""Regression guard: catch silent class-method shadowing across the bot.

A class with two `def foo(self)` definitions causes the second to silently
overwrite the first — typically dropping logic. This bug class produced
the P1.2 / P1.4 / P1.5 / P1.6 issues in iteration 1 (opponent_modeling
on_step, combat_manager._find_harass_target, economy_manager._prevent_
resource_banking and _reduce_gas_workers).

Test fails if any class in the bot package defines the same method name
twice. Properties/overloads are not generally used here, so duplicates
are bugs.
"""

import ast
import os

import pytest

BOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

# Modules that legitimately use overload patterns or @typing.overload.
# Keep empty - add only with justification.
ALLOWLIST: set[tuple[str, str, str]] = set()


def _find_shadowed_methods(path: str):
    """Return list of (class_name, method_name, lineno) for duplicates."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
    except (SyntaxError, UnicodeDecodeError):
        return []

    dups = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        seen: dict[str, int] = {}
        for body_item in node.body:
            if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip @overload stubs and @property accessors
                is_overload = any(
                    (isinstance(d, ast.Name) and d.id == "overload")
                    or (isinstance(d, ast.Attribute) and d.attr == "overload")
                    for d in body_item.decorator_list
                )
                if is_overload:
                    continue
                name = body_item.name
                if name in seen:
                    dups.append((node.name, name, body_item.lineno, seen[name]))
                else:
                    seen[name] = body_item.lineno
    return dups


def _iter_bot_py_files():
    for fname in sorted(os.listdir(BOT_DIR)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(BOT_DIR, fname)
        if os.path.isfile(path):
            yield path


@pytest.mark.parametrize("path", list(_iter_bot_py_files()), ids=os.path.basename)
def test_no_shadowed_class_methods(path):
    rel = os.path.relpath(path, BOT_DIR)
    dups = _find_shadowed_methods(path)
    filtered = [d for d in dups if (rel, d[0], d[1]) not in ALLOWLIST]
    assert (
        not filtered
    ), f"{rel}: shadowed methods (second def overrides first):\n" + "\n".join(
        f"  class {cls}.{method} re-defined at line {late}, "
        f"earlier def at line {early}"
        for cls, method, late, early in filtered
    )
