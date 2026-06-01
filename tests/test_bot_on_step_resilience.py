"""
Source-level regression locks for WickedZergBotProImpl.on_step error
containment.

Two behaviors must stay locked in:

1. The scoring system and awareness engine calls inside on_step must be
   guarded by try/except so a single misbehaving subsystem can't crash
   the entire game loop.

2. The except blocks must NOT be the silent ``except Exception: pass``
   anti-pattern — they must funnel through ``self.logger`` so failures
   are visible. We caught real bugs hiding behind ``pass`` before.

Doing this at the source level rather than via runtime instantiation
keeps the test portable: spinning up the full bot pulls in dozens of
optional collaborators and an SC2 client, which we don't want as a CI
dependency just to lock in an exception-handling shape.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BOT_FILE = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "wicked_zerg_bot_pro_impl.py"
)


def _find_method(tree: ast.AST, name: str) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"async def {name} not found")


def _try_blocks_in(node: ast.AST):
    """Yield every Try node found anywhere under ``node``."""
    for child in ast.walk(node):
        if isinstance(child, ast.Try):
            yield child


def _call_targets_attr(call: ast.Call, attr_chain: tuple[str, ...]) -> bool:
    """True if ``call`` is e.g. ``self.scoring_system.on_step(...)``."""
    func = call.func
    expected = list(reversed(attr_chain))
    for piece in expected:
        if not isinstance(func, ast.Attribute) or func.attr != piece:
            return False
        func = func.value
    return isinstance(func, ast.Name) and func.id == "self"


@pytest.fixture(scope="module")
def on_step_ast() -> ast.AsyncFunctionDef:
    src = BOT_FILE.read_text(encoding="utf-8")
    tree = ast.parse(src, str(BOT_FILE))
    return _find_method(tree, "on_step")


def _try_block_wrapping(method: ast.AsyncFunctionDef, attr_chain: tuple[str, ...]):
    for try_node in _try_blocks_in(method):
        for stmt in try_node.body:
            for call in ast.walk(stmt):
                if isinstance(call, ast.Call) and _call_targets_attr(call, attr_chain):
                    return try_node
    return None


def test_scoring_system_on_step_is_wrapped_in_try(on_step_ast):
    """Scoring system must be called inside a try/except."""
    try_node = _try_block_wrapping(on_step_ast, ("scoring_system", "on_step"))
    assert try_node is not None, (
        "self.scoring_system.on_step(...) must be inside a try/except"
    )


def test_scoring_system_except_logs_instead_of_pass(on_step_ast):
    """The scoring system except branch must call self.logger.*, not pass."""
    try_node = _try_block_wrapping(on_step_ast, ("scoring_system", "on_step"))
    assert try_node is not None
    handlers = try_node.handlers
    assert handlers, "scoring system try must have an except clause"

    handler = handlers[0]
    body_dump = "\n".join(ast.unparse(s) for s in handler.body)
    assert "self.logger" in body_dump, (
        f"expected self.logger.* call in scoring except, got:\n{body_dump}"
    )
    assert body_dump.strip() != "pass", (
        "scoring except must not be a silent `pass`"
    )


def test_awareness_engine_on_step_is_wrapped_in_try(on_step_ast):
    """Awareness engine must be called inside a try/except."""
    try_node = _try_block_wrapping(on_step_ast, ("awareness_engine", "on_step"))
    assert try_node is not None, (
        "self.awareness_engine.on_step(...) must be inside a try/except"
    )


def test_awareness_engine_except_logs_instead_of_pass(on_step_ast):
    """The awareness engine except branch must call self.logger.*, not pass."""
    try_node = _try_block_wrapping(on_step_ast, ("awareness_engine", "on_step"))
    assert try_node is not None
    handlers = try_node.handlers
    assert handlers, "awareness engine try must have an except clause"

    handler = handlers[0]
    body_dump = "\n".join(ast.unparse(s) for s in handler.body)
    assert "self.logger" in body_dump, (
        f"expected self.logger.* call in awareness except, got:\n{body_dump}"
    )
    assert body_dump.strip() != "pass", (
        "awareness except must not be a silent `pass`"
    )
