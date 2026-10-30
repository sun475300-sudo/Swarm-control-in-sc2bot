"""Validate the shipped ZIP in isolation, rather than imports from the checkout."""

import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "arena_packager", Path(__file__).resolve().parents[2] / "create_arena_package.py"
)
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


@pytest.mark.parametrize(
    "name",
    [
        "bot/model.pt",
        "bot/model.pth",
        "bot/network.onnx",
        "bot/output.log",
        "bot/__pycache__/module.pyc",
        "bot/.env.production",
        "bot/credentials.json",
        "bot/local_training/comparison_reports/report.json",
    ],
)
def test_generated_artifacts_and_credentials_are_excluded(name):
    assert packager.should_exclude(name)


@pytest.mark.parametrize(
    "name",
    [
        "bot/local_training/economy_combat_balancer.py",
        "bot/local_training/production_resilience.py",
        "bot/local_training/hierarchical_rl/improved_hierarchical_rl.py",
        "bot/config/unit_configs.py",
        "bot/utils/logger.py",
    ],
)
def test_runtime_code_is_retained(name):
    assert not packager.should_exclude(name)


def test_missing_inputs_fail_before_writing_partial_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(packager, "PROJECT_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="run.py"):
        packager.create_arena_zip(tmp_path, "bot.zip")
    assert not (tmp_path / "bot.zip").exists()


def test_built_zip_imports_real_bot_and_economy_from_extracted_package(tmp_path):
    archive = packager.create_arena_zip(tmp_path, "bot.zip")
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        names = package.namelist()
        assert "wicked_zerg_challenger/local_training/production_resilience.py" in names
        assert not any("__pycache__" in name for name in names)
        package.extractall(extracted)

    code = """
import runpy
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'wicked_zerg_challenger'))
entrypoint = runpy.run_path(str(root / 'run.py'), run_name='arena_smoke')
from sc2.bot_ai import BotAI
from economy_manager import EconomyManager
from local_training.production_resilience import ProductionResilience, BALANCER_AVAILABLE
from local_training.hierarchical_rl.improved_hierarchical_rl import HierarchicalRLSystem
from arena.preflight_validator import PreflightValidator
assert issubclass(entrypoint['WickedZergBotProImpl'], BotAI)
assert entrypoint['WickedZergBotProImpl']().blackboard is not None
assert BALANCER_AVAILABLE
assert PreflightValidator(str(root)).validate().passed
assert Path(sys.modules['economy_manager'].__file__).is_relative_to(root)
print('Extracted Arena bot, economy, production, hierarchical RL imports: PASS')
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(extracted)],
        cwd=extracted,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Extracted Arena bot" in result.stdout
