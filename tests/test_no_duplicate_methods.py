# -*- coding: utf-8 -*-
"""Regression test — guard against F811 duplicate-method shadows in core managers.

History: A run on 2026-05-07 found that 5 methods in 4 core bot files had
been defined twice in the same class — Python keeps the last def, so the
first was silently dead code. The most painful one was
OpponentModeling.on_step, which had a stub at line 765 shadowing the full
implementation at line 341, effectively disabling opponent modeling past
the early game.

This file walks the AST of every Python file under wicked_zerg_challenger/
and asserts that no class body contains two methods with the same name.
Cheap to run, catches the bug class for good.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BOT_ROOT = REPO_ROOT / "wicked_zerg_challenger"


def _iter_class_method_dups(tree: ast.Module):
    """Yield (class_name, method_name, count) for every duplicate."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        method_names = [
            child.name
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for name, count in Counter(method_names).items():
            if count > 1:
                yield (node.name, name, count)


def _python_files(root: Path):
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


@pytest.mark.parametrize("path", list(_python_files(BOT_ROOT)), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_duplicate_methods_in_class(path: Path):
    """Every class body must define each method at most once."""
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    dups = list(_iter_class_method_dups(tree))
    assert not dups, (
        f"{path.relative_to(REPO_ROOT)} has duplicate method definitions "
        f"that silently shadow each other (F811): {dups}"
    )
