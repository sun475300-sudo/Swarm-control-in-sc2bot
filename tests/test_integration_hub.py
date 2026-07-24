# -*- coding: utf-8 -*-
"""Regression tests for integration_hub.py."""

from pathlib import Path

from integration_hub import IntegrationHub


def test_generate_test_script_does_not_crash(tmp_path: Path) -> None:
    """generate_test_script() used to crash with NameError('positions').

    The template body was built with an `f'''...'''` string even though its
    only brace expression (`{len(positions)}`) belongs to the *generated*
    script text, not the enclosing scope. That made the outer f-string
    evaluate `positions` immediately, which was never defined here.
    """
    hub = IntegrationHub()
    output_path = tmp_path / "generated_test.py"

    result = hub.generate_test_script(output_path)

    assert result == str(output_path)
    content = output_path.read_text(encoding="utf-8")
    assert "positions = hub.formation_plan(10, \"circle\")" in content
    assert "{len(positions)}" in content
