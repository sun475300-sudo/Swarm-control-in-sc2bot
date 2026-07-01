"""
sc2_encyclopedia helper-function tests.

The encyclopedia is pure data + lookup helpers — no sc2 dependency.
We pin: case-insensitivity, missing-key behavior, weighting in
suggest_composition, and the formatted report.
"""

import sys
from pathlib import Path

import pytest

_PKG_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    from sc2_encyclopedia import (
        COUNTER_MATRIX,
        TECH_REQUIREMENTS,
        TIMING_BENCHMARKS,
        ZERG_UNITS,
        get_counter,
        get_encyclopedia_report,
        get_tech_path,
        get_unit_info,
        suggest_composition,
    )
except ImportError:
    pytest.skip("sc2_encyclopedia unavailable", allow_module_level=True)


# ---------------------------------------------------------------------------
# get_counter
# ---------------------------------------------------------------------------


def test_get_counter_known_unit_returns_dict():
    info = get_counter("MARINE")
    assert info is not None
    assert "BANELING" in info["counter"]
    assert info["priority"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def test_get_counter_case_insensitive():
    assert get_counter("marine") == get_counter("MARINE")


def test_get_counter_with_spaces_normalised_to_underscore():
    assert get_counter("siege tank") == get_counter("SIEGE_TANK")


def test_get_counter_unknown_returns_none():
    assert get_counter("FAKE_UNIT_THAT_DOES_NOT_EXIST") is None


# ---------------------------------------------------------------------------
# get_unit_info
# ---------------------------------------------------------------------------


def test_get_unit_info_returns_zerg_unit_data():
    info = get_unit_info("ZERGLING")
    assert info is not None
    assert info["name"] == "저글링"
    assert info["cost"] == (25, 0, 0.5)


def test_get_unit_info_case_insensitive():
    assert get_unit_info("zergling") == get_unit_info("ZERGLING")


def test_get_unit_info_unknown_returns_none():
    assert get_unit_info("PROBE") is None  # Probes are not in ZERG_UNITS


# ---------------------------------------------------------------------------
# get_tech_path
# ---------------------------------------------------------------------------


def test_get_tech_path_known_unit():
    path = get_tech_path("BANELING")
    assert path is not None
    assert path["building"] == "BANELINGNEST"
    assert path["morph_from"] == "ZERGLING"


def test_get_tech_path_lurker_requires_lair():
    path = get_tech_path("LURKER")
    assert path["requires"] == "LAIR"


def test_get_tech_path_unknown_returns_none():
    assert get_tech_path("ARCHON") is None  # Archons are Protoss


# ---------------------------------------------------------------------------
# suggest_composition
# ---------------------------------------------------------------------------


def test_suggest_composition_empty_input_returns_empty_dict():
    assert suggest_composition([]) == {}


def test_suggest_composition_unknown_units_ignored():
    assert suggest_composition(["FAKE", "ALSO_FAKE"]) == {}


def test_suggest_composition_critical_priority_outweighs_low():
    """SIEGE_TANK is CRITICAL (weight 3); VIKING is LOW (weight 0.5).
    Their counters that overlap in HYDRALISK/CORRUPTOR/etc accumulate;
    the critical-tier counters should rank highest."""
    comp = suggest_composition(["SIEGE_TANK", "VIKING"])
    # RAVAGER counters SIEGE_TANK only (priority CRITICAL → weight 3).
    # HYDRALISK counters VIKING only (priority LOW → weight 0.5).
    # MUTALISK counters SIEGE_TANK only.
    # CORRUPTOR appears in both VIKING and ... well, RAVEN, not VIKING list.
    # Easiest assertion: RAVAGER (3.0) ranks above HYDRALISK (0.5).
    items = list(comp.items())
    pos = {name: i for i, (name, _) in enumerate(items)}
    assert pos["RAVAGER"] < pos["HYDRALISK"]


def test_suggest_composition_aggregates_overlapping_counters():
    """If two enemy units share a counter, the weight should accumulate."""
    # MARAUDER counter list contains ZERGLING_SURROUND (priority MEDIUM=1)
    # GHOST counter list also contains ZERGLING_SURROUND (priority HIGH=2)
    comp = suggest_composition(["MARAUDER", "GHOST"])
    assert comp.get("ZERGLING_SURROUND") == pytest.approx(3.0)


def test_suggest_composition_sorted_descending_by_weight():
    comp = suggest_composition(["MARINE", "SIEGE_TANK", "MARAUDER"])
    weights = list(comp.values())
    assert weights == sorted(weights, reverse=True)


# ---------------------------------------------------------------------------
# get_encyclopedia_report
# ---------------------------------------------------------------------------


def test_report_unknown_unit_friendly_message():
    msg = get_encyclopedia_report("UNKNOWN_UNIT_XYZ")
    assert "찾을 수 없습니다" in msg


def test_report_known_unit_contains_key_facts():
    msg = get_encyclopedia_report("ZERGLING")
    assert "저글링" in msg
    assert "ZERGLING" in msg
    assert "DPS" in msg
    assert "체력" in msg


def test_report_includes_tech_when_available():
    msg = get_encyclopedia_report("BANELING")
    assert "BANELINGNEST" in msg
    assert "변태원본" in msg or "morph_from" in msg.upper() or "ZERGLING" in msg


# ---------------------------------------------------------------------------
# Data integrity
# ---------------------------------------------------------------------------


def test_counter_matrix_priorities_are_valid():
    valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    for unit, info in COUNTER_MATRIX.items():
        assert info["priority"] in valid, f"{unit}: invalid priority"
        assert isinstance(info["counter"], list), f"{unit}: counter must be list"
        assert info["counter"], f"{unit}: counter list must not be empty"


def test_zerg_units_have_required_fields():
    required = {"name", "cost", "hp", "dps", "speed", "attributes"}
    for unit, info in ZERG_UNITS.items():
        missing = required - set(info)
        assert not missing, f"{unit} missing fields: {missing}"


def test_zerg_unit_costs_are_three_tuples():
    for unit, info in ZERG_UNITS.items():
        cost = info["cost"]
        assert len(cost) == 3, f"{unit}: cost must be (minerals, gas, supply)"
        assert all(isinstance(v, (int, float)) for v in cost), unit


def test_timing_benchmarks_monotonic_for_known_pair():
    """Lair (240s) must come before Hive (540s)."""
    assert (
        TIMING_BENCHMARKS["lair"]["time"] < TIMING_BENCHMARKS["hive"]["time"]
    )
