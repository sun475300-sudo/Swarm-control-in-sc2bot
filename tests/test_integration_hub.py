# -*- coding: utf-8 -*-
"""IntegrationHub regression tests."""

from pathlib import Path

from integration_hub import IntegrationHub


def test_generate_test_script_does_not_crash(tmp_path: Path):
    """generate_test_script used to raise NameError('positions' not defined)
    because its output-script template was an f-string, so the `{...}`
    placeholders meant to stay literal in the generated file were evaluated
    immediately against IntegrationHub's own local scope."""
    hub = IntegrationHub()
    output_path = tmp_path / "generated_test.py"

    hub.generate_test_script(output_path)

    script = output_path.read_text(encoding="utf-8")
    assert "positions" in script
    assert "{len(positions)}" in script
