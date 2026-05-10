"""
MapManager tests - map selection, persistence, and weighted-pick logic.

No sc2 dependency required.
"""

import json
import sys
from pathlib import Path

import pytest

_PKG_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    from map_manager import TRAINING_MAPS, MapManager
except ImportError:
    pytest.skip("map_manager unavailable", allow_module_level=True)


# ---------------------------------------------------------------------------
# _load_stats / _save_stats
# ---------------------------------------------------------------------------


def test_load_stats_returns_empty_dict_when_file_missing(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "missing.json"))
    assert mgr.stats == {}


def test_load_stats_handles_corrupt_json(tmp_path):
    f = tmp_path / "corrupt.json"
    f.write_text("{not json", encoding="utf-8")
    mgr = MapManager(stats_file=str(f))
    assert mgr.stats == {}


def test_load_stats_ignores_non_dict_root(tmp_path):
    f = tmp_path / "list.json"
    f.write_text(json.dumps(["wrong", "type"]), encoding="utf-8")
    mgr = MapManager(stats_file=str(f))
    assert mgr.stats == {}


def test_record_result_increments_wins(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    mgr.record_result("MapA", win=True)
    assert mgr.stats["MapA"]["wins"] == 1
    assert mgr.stats["MapA"]["losses"] == 0


def test_record_result_increments_losses(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    mgr.record_result("MapA", win=False)
    assert mgr.stats["MapA"]["losses"] == 1


def test_record_result_persists_to_disk(tmp_path):
    f = tmp_path / "s.json"
    mgr = MapManager(stats_file=str(f))
    mgr.record_result("MapA", win=True)
    mgr.record_result("MapA", win=False)
    on_disk = json.loads(f.read_text(encoding="utf-8"))
    assert on_disk == {"MapA": {"wins": 1, "losses": 1}}


def test_record_result_creates_parent_dir(tmp_path):
    nested = tmp_path / "deep" / "nested" / "stats.json"
    mgr = MapManager(stats_file=str(nested))
    mgr.record_result("MapA", win=True)
    assert nested.exists()


def test_load_existing_stats_round_trips(tmp_path):
    f = tmp_path / "s.json"
    mgr1 = MapManager(stats_file=str(f))
    mgr1.record_result("MapA", win=True)
    # New manager with the same path should see the saved data.
    mgr2 = MapManager(stats_file=str(f))
    assert mgr2.stats["MapA"]["wins"] == 1


# ---------------------------------------------------------------------------
# get_map_stats
# ---------------------------------------------------------------------------


def test_get_map_stats_returns_zero_for_unknown_map(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    assert mgr.get_map_stats("NeverSeen") == {"wins": 0, "losses": 0}


def test_get_map_stats_returns_recorded_for_known_map(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    mgr.record_result("MapA", win=True)
    mgr.record_result("MapA", win=True)
    mgr.record_result("MapA", win=False)
    assert mgr.get_map_stats("MapA") == {"wins": 2, "losses": 1}


# ---------------------------------------------------------------------------
# select_map
# ---------------------------------------------------------------------------


def test_select_map_single_mode_returns_first_available(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    selected = mgr.select_map(mode="single")
    # Either the first TRAINING_MAPS entry or the first .SC2Map glob —
    # we just assert it's a non-empty string from the available pool.
    assert isinstance(selected, str) and selected


def test_select_map_sequential_advances_index(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    first = mgr.select_map(mode="sequential")
    second = mgr.select_map(mode="sequential")
    available = mgr.get_available_maps()
    assert first == available[0]
    if len(available) > 1:
        assert second == available[1]


def test_select_map_random_returns_member_of_available(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    available = set(mgr.get_available_maps())
    # Sample a few times to be stable
    for _ in range(5):
        assert mgr.select_map(mode="random") in available


def test_select_map_weighted_returns_member_of_available(tmp_path):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    available = set(mgr.get_available_maps())
    for _ in range(5):
        assert mgr.select_map(mode="weighted") in available


def test_select_map_with_no_maps_returns_default(tmp_path, monkeypatch):
    """If get_available_maps() returns empty, select_map falls back to
    the documented default 'LeyLinesAIE_v3'."""
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    monkeypatch.setattr(mgr, "get_available_maps", lambda: [])
    assert mgr.select_map() == "LeyLinesAIE_v3"


# ---------------------------------------------------------------------------
# _select_weighted: maps with low win rate get higher weight
# ---------------------------------------------------------------------------


def test_select_weighted_prefers_low_win_rate_map(tmp_path, monkeypatch):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    # Inject deterministic stats.
    mgr.stats = {
        "Easy": {"wins": 100, "losses": 0},   # 100% win rate -> weight 0.2
        "Hard": {"wins": 0, "losses": 100},   # 0% win rate -> weight 1.0
    }

    # Pin random.choices so we can inspect the weights it received.
    received = {}

    def fake_choices(population, weights, k):
        received["population"] = population
        received["weights"] = weights
        return [population[0]]

    monkeypatch.setattr("map_manager.random.choices", fake_choices)
    mgr._select_weighted(["Easy", "Hard"])

    assert received["weights"][0] == pytest.approx(0.2)
    assert received["weights"][1] == pytest.approx(1.0)


def test_select_weighted_unrated_maps_get_full_weight(tmp_path, monkeypatch):
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    mgr.stats = {}  # no stats
    received = {}

    def fake_choices(population, weights, k):
        received["weights"] = weights
        return [population[0]]

    monkeypatch.setattr("map_manager.random.choices", fake_choices)
    mgr._select_weighted(["A", "B"])
    # No data → win_rate=0 → weight max(0.2, 1.0 - 0) = 1.0 for everyone.
    assert received["weights"] == [1.0, 1.0]


# ---------------------------------------------------------------------------
# get_available_maps
# ---------------------------------------------------------------------------


def test_get_available_maps_falls_back_to_training_maps(tmp_path, monkeypatch):
    """When the local Maps/ directory doesn't exist or is empty, the manager
    returns the TRAINING_MAPS list."""
    mgr = MapManager(stats_file=str(tmp_path / "s.json"))
    # Force the Maps path to not exist by chdir'ing to an empty dir.
    monkeypatch.chdir(tmp_path)
    result = mgr.get_available_maps()
    assert result == TRAINING_MAPS  # ordering preserved
