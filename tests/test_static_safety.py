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
