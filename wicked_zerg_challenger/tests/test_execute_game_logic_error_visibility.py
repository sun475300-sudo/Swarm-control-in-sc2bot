# -*- coding: utf-8 -*-
"""
Regression guard: every subsystem `except Exception as e:` block inside
BotStepIntegrator.execute_game_logic() must surface the error (via
error_handler.error_counts + logger) when not in debug mode.

Found in practice: 11 blocks only did `if error_handler.debug_mode: raise`
with nothing in the else-path, so any subsystem.on_step() exception in a
live (non-debug) game vanished silently -- the subsystem just stopped
running for the rest of the game with zero trace in the logs.
"""

import ast
import os

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "bot_step_integration.py")


def _get_execute_game_logic_node():
    with open(MODULE_PATH, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=MODULE_PATH)

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute_game_logic":
            return node
    raise AssertionError("execute_game_logic not found in bot_step_integration.py")


def _handles_debug_mode_raise(except_handler):
    """True if this handler's body starts with `if error_handler.debug_mode: raise`."""
    if not except_handler.body:
        return False
    first = except_handler.body[0]
    if not isinstance(first, ast.If):
        return False
    test = first.test
    return (
        isinstance(test, ast.Attribute)
        and test.attr == "debug_mode"
        and isinstance(test.value, ast.Name)
        and test.value.id == "error_handler"
    )


def _references_error_counts(except_handler):
    for node in ast.walk(except_handler):
        if isinstance(node, ast.Attribute) and node.attr == "error_counts":
            return True
    return False


def test_no_silent_exception_swallowing_in_execute_game_logic():
    func_node = _get_execute_game_logic_node()

    silent_blocks = []
    for node in ast.walk(func_node):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not _handles_debug_mode_raise(node):
            continue
        if not _references_error_counts(node):
            silent_blocks.append(node.lineno)

    assert not silent_blocks, (
        "except-blocks that only guard debug_mode-raise but never log/count "
        f"the error in production mode at line(s): {silent_blocks}. "
        "Add error_handler.error_counts[...] + a capped self.logger.error(...) "
        "call in the else path, matching the pattern used elsewhere in "
        "execute_game_logic (e.g. CreepHighway, RLAgent)."
    )
