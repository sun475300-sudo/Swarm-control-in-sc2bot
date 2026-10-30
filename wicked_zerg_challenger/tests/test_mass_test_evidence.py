"""Benchmark failures must not be presented as successful game evidence."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_mass_test as runner


@pytest.fixture
def game_engine(monkeypatch):
    """Keep the real result enums but replace only the external SC2 process boundary."""
    from sc2.data import Result

    calls = []
    monkeypatch.setattr(runner, "maps", SimpleNamespace(get=lambda name: name))
    monkeypatch.setattr(runner, "WickedZergBotProImpl", lambda **kwargs: kwargs)
    monkeypatch.setattr(runner, "Bot", lambda race, bot: (race, bot))
    monkeypatch.setattr(runner, "Computer", lambda race, difficulty: (race, difficulty))

    def run_game(map_settings, players, **kwargs):
        calls.append((map_settings, players, kwargs))
        return Result.Victory

    monkeypatch.setattr(runner, "run_game", run_game)
    return calls


def command(output, *options):
    return [
        "--opponent",
        "Terran",
        "--difficulty",
        "Medium",
        "--games",
        "1",
        "--output",
        str(output),
        *options,
    ]


@pytest.mark.parametrize(
    "option,value",
    [
        ("--games", "0"),
        ("--games", "-1"),
        ("--max-game-time", "0"),
        ("--min-win-rate", "101"),
        ("--min-win-rate", "-1"),
        ("--min-win-rate", "nan"),
        ("--min-win-rate", "inf"),
        ("--seed", "-1"),
        ("--seed", "4294967296"),
    ],
)
def test_invalid_benchmark_settings_fail_before_launch(option, value):
    with pytest.raises(SystemExit) as error:
        runner.parse_args([option, value])
    assert error.value.code == 2


def test_dry_run_does_not_overwrite_existing_match_evidence(tmp_path, monkeypatch):
    output = tmp_path / "report.json"
    output.write_text("existing match evidence")
    monkeypatch.setattr(runner, "run_game", None)
    assert runner.main(command(output, "--dry-run")) == 0
    assert output.read_text() == "existing match evidence"


def test_real_win_records_engine_settings_and_provenance(tmp_path, game_engine):
    output = tmp_path / "nested" / "report.json"
    replay_dir = tmp_path / "replays"
    exit_code = runner.main(
        command(
            output,
            "--min-win-rate",
            "100",
            "--seed",
            "42",
            "--max-game-time",
            "600",
            "--replay-dir",
            str(replay_dir),
        )
    )
    report = json.loads(output.read_text())
    assert exit_code == 0
    assert report["completed_games"] == report["wins"] == 1
    assert report["evidence"] == "real_game"
    assert report["gate_passed"] is True
    assert report["win_rate"] == 100
    assert report["timestamp"].endswith("+00:00")
    assert report["source_commit"]
    assert "burnysc2" in report["packages"]
    assert game_engine[0][2] == {
        "realtime": False,
        "random_seed": 42,
        "game_time_limit": 600,
        "save_replay_as": str(replay_dir / "game_0001.SC2Replay"),
    }
    assert game_engine[0][1][0][1] == {"train_mode": False}
    assert report["by_race"]["Terran"]["wins"] == 1
    assert report["by_difficulty"]["Medium"]["wins"] == 1


@pytest.mark.parametrize("outcome,field", [("Defeat", "losses"), ("Tie", "ties")])
def test_completed_non_wins_fail_threshold_without_becoming_errors(
    tmp_path,
    monkeypatch,
    game_engine,
    outcome,
    field,
):
    from sc2.data import Result

    monkeypatch.setattr(runner, "run_game", lambda *args, **kwargs: Result[outcome])
    output = tmp_path / "report.json"
    assert runner.main(command(output, "--min-win-rate", "90")) == 1
    report = json.loads(output.read_text())
    assert report[field] == 1
    assert report["errors"] == 0
    assert report["completed_games"] == 1
    assert report["gate_passed"] is False
    assert report["win_rate"] == 0


def test_ties_remain_in_win_rate_denominator(tmp_path, monkeypatch, game_engine):
    from sc2.data import Result

    outcomes = iter([Result.Victory, Result.Tie])
    monkeypatch.setattr(runner, "run_game", lambda *args, **kwargs: next(outcomes))
    output = tmp_path / "report.json"
    assert runner.main(command(output, "--games", "2", "--min-win-rate", "60")) == 1
    report = json.loads(output.read_text())
    assert report["win_rate"] == 50
    assert report["ties"] == 1


def test_missing_runtime_is_unvalidated_even_with_zero_percent_gate(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(runner, "run_game", None)
    output = tmp_path / "report.json"
    assert runner.main(command(output, "--min-win-rate", "0")) == 2
    report = json.loads(output.read_text())
    assert report["evidence"] == "unvalidated"
    assert report["completed_games"] == 0
    assert report["errors"] == 1
    assert report["win_rate"] is None
    assert report["gate_passed"] is False


@pytest.mark.parametrize(
    "failure", ["map", "construction", "engine", "undecided", "runtime_exit"]
)
def test_runtime_failures_propagate_to_report_and_exit_status(
    tmp_path,
    monkeypatch,
    game_engine,
    failure,
):
    from sc2.data import Result

    def fail(*args, **kwargs):
        raise RuntimeError("expected runtime failure")

    if failure == "map":
        monkeypatch.setattr(runner, "maps", SimpleNamespace(get=lambda name: None))
    elif failure == "construction":
        monkeypatch.setattr(runner, "WickedZergBotProImpl", fail)
    elif failure == "engine":
        monkeypatch.setattr(runner, "run_game", fail)
    elif failure == "runtime_exit":

        def exit_runtime(name):
            raise SystemExit(1)

        monkeypatch.setattr(runner, "maps", SimpleNamespace(get=exit_runtime))
    else:
        monkeypatch.setattr(
            runner, "run_game", lambda *args, **kwargs: Result.Undecided
        )
    output = tmp_path / "report.json"
    assert runner.main(command(output)) == 2
    report = json.loads(output.read_text())
    assert report["errors"] == 1
    assert report["losses"] == 0
    assert report["games"][0]["race"] == "Terran"
    assert report["games"][0]["difficulty"] == "Medium"
    assert report["games"][0]["error"]


def test_partial_engine_failure_cannot_pass_on_other_wins(
    tmp_path, monkeypatch, game_engine
):
    from sc2.data import Result

    outcomes = iter([Result.Victory, Result.Undecided])
    monkeypatch.setattr(runner, "run_game", lambda *args, **kwargs: next(outcomes))
    output = tmp_path / "report.json"
    assert runner.main(command(output, "--games", "2", "--min-win-rate", "100")) == 2
    report = json.loads(output.read_text())
    assert report["win_rate"] == 100
    assert report["completed_games"] == 1
    assert report["gate_passed"] is False


def test_seed_increments_and_wraps_without_exceeding_sc2_uint32(tmp_path, game_engine):
    assert (
        runner.main(
            command(
                tmp_path / "report.json",
                "--games",
                "2",
                "--seed",
                "4294967295",
            )
        )
        == 0
    )
    assert [call[2]["random_seed"] for call in game_engine] == [4294967295, 0]


def test_report_write_failure_returns_failure(tmp_path, game_engine):
    assert runner.main(command(tmp_path)) == 2


def test_empty_selection_cannot_validate(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "build_test_cases", lambda args: [])
    output = tmp_path / "report.json"
    assert runner.main(command(output)) == 2
    assert not output.exists()
