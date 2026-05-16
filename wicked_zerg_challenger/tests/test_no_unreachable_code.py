# -*- coding: utf-8 -*-
"""Regression guard: catch unreachable code after return/raise/break/continue.

This bug class produced the iteration-6 dead blocks in
smart_resource_balancer._get_current_worker_ratio,
smart_resource_balancer._move_workers_to_minerals,
economy_manager._force_expansion_if_stuck, and
economy_manager._check_proactive_expansion — each had a `return`
statement followed by 30-40 lines of duplicate body that was silently
dead.
"""

import ast
import os

import pytest

BOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def _find_unreachable(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
    except (SyntaxError, UnicodeDecodeError):
        return []
    unreachable = []
    terminators = (ast.Return, ast.Raise, ast.Continue, ast.Break)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Walk every nested block - terminators inside if/for/while are
            # only "unreachable causes" for the IMMEDIATELY-FOLLOWING sibling.
            for parent in ast.walk(node):
                if hasattr(parent, "body") and isinstance(parent.body, list):
                    for i, stmt in enumerate(parent.body):
                        if isinstance(stmt, terminators):
                            if i + 1 < len(parent.body):
                                dead = parent.body[i + 1]
                                unreachable.append(
                                    (node.name, stmt.lineno, dead.lineno)
                                )
                                break
    return unreachable


def _iter_bot_py_files():
    for fname in sorted(os.listdir(BOT_DIR)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(BOT_DIR, fname)
        if os.path.isfile(path):
            yield path


@pytest.mark.parametrize("path", list(_iter_bot_py_files()), ids=os.path.basename)
def test_no_unreachable_after_terminator(path):
    rel = os.path.relpath(path, BOT_DIR)
    dead = _find_unreachable(path)
    assert not dead, f"{rel}: dead code after terminator:\n" + "\n".join(
        f"  {func}(): line {dead_line} unreachable (terminator at {term_line})"
        for func, term_line, dead_line in dead
    )
