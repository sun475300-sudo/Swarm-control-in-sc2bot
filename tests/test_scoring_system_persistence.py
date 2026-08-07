"""
ScoringSystem persistence and DomainScore behavior tests.

Covers:
- DomainScore add() event accounting and grade boundaries
- _save_game_score / _load_cumulative_score / _save_cumulative_score
  resilient to OSError (read-only path) and JSONDecodeError (corrupt file).
- Cumulative score load returns the documented default on first run.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    from wicked_zerg_challenger.scoring_system import DomainScore, ScoringSystem
except ImportError:
    pytest.skip("scoring_system unavailable", allow_module_level=True)


# ---------------------------------------------------------------------------
# DomainScore unit tests
# ---------------------------------------------------------------------------


class TestDomainScore:
    def test_add_positive_event_increments_positive(self):
        d = DomainScore("Combat")
        d.add(5, "win")
        assert d.score == 5
        assert d.positive_events == 1
        assert d.negative_events == 0
        assert d.total_events == 1

    def test_add_negative_event_increments_negative(self):
        d = DomainScore("Combat")
        d.add(-3, "loss")
        assert d.score == -3
        assert d.negative_events == 1
        assert d.positive_events == 0

    def test_zero_event_treated_as_negative(self):
        # Implementation decision: only > 0 counts as positive.
        d = DomainScore("Defense")
        d.add(0, "noop")
        assert d.positive_events == 0
        assert d.negative_events == 1

    def test_history_caps_at_100(self):
        d = DomainScore("Macro")
        for i in range(130):
            d.add(1, f"e{i}")
        assert len(d.history) == 100
        # The oldest 30 should have been dropped — last entry's reason must be 'e129'.
        assert d.history[-1]["reason"] == "e129"

    @pytest.mark.parametrize(
        "score, expected_grade",
        [
            (100, "S"),
            (80, "S"),
            (79, "A"),
            (60, "A"),
            (59, "B"),
            (40, "B"),
            (39, "C"),
            (20, "C"),
            (19, "D"),
            (0, "D"),
            (-1, "F"),
            (-50, "F"),
        ],
    )
    def test_grade_boundaries(self, score, expected_grade):
        d = DomainScore("Test")
        d.score = score
        assert d.grade == expected_grade


# ---------------------------------------------------------------------------
# Persistence resilience tests
# ---------------------------------------------------------------------------


def _make_scoring_system(tmp_path: Path) -> ScoringSystem:
    """Build a ScoringSystem rooted at tmp_path/data/scoring."""

    bot = MagicMock()
    # Patch SAVE_PATH on the *instance via the class attribute* by using a subclass
    save_dir = tmp_path / "scoring_data"
    save_dir.mkdir(parents=True, exist_ok=True)

    class _Scoped(ScoringSystem):
        SAVE_PATH = str(save_dir)

    return _Scoped(bot)


def test_load_cumulative_score_returns_default_when_missing(tmp_path):
    sys = _make_scoring_system(tmp_path)
    result = sys._load_cumulative_score()
    assert result == {"total": 0, "blocks": []}


def test_load_cumulative_score_handles_corrupt_json(tmp_path):
    sys = _make_scoring_system(tmp_path)
    corrupt = Path(sys.SAVE_PATH) / "cumulative_score.json"
    corrupt.write_text("{not valid json", encoding="utf-8")
    # Must not raise; returns default.
    assert sys._load_cumulative_score() == {"total": 0, "blocks": []}


def test_save_and_load_cumulative_score_roundtrip(tmp_path):
    sys = _make_scoring_system(tmp_path)
    sys._cumulative_score = {"total": 42, "blocks": [{"game": 1}]}
    sys._save_cumulative_score()
    loaded = sys._load_cumulative_score()
    assert loaded == {"total": 42, "blocks": [{"game": 1}]}


def test_save_game_score_creates_file(tmp_path):
    sys = _make_scoring_system(tmp_path)
    sys._save_game_score({"total_score": 100, "result": "win"})
    target = Path(sys.SAVE_PATH) / "game_scores.json"
    assert target.exists()
    contents = json.loads(target.read_text(encoding="utf-8"))
    assert contents == [{"total_score": 100, "result": "win"}]


def test_save_game_score_appends_to_existing(tmp_path):
    sys = _make_scoring_system(tmp_path)
    sys._save_game_score({"total_score": 1})
    sys._save_game_score({"total_score": 2})
    target = Path(sys.SAVE_PATH) / "game_scores.json"
    contents = json.loads(target.read_text(encoding="utf-8"))
    assert [c["total_score"] for c in contents] == [1, 2]


def test_save_game_score_caps_history_at_200(tmp_path):
    sys = _make_scoring_system(tmp_path)
    target = Path(sys.SAVE_PATH) / "game_scores.json"
    target.write_text(
        json.dumps([{"total_score": i} for i in range(250)]), encoding="utf-8"
    )
    sys._save_game_score({"total_score": 999})
    contents = json.loads(target.read_text(encoding="utf-8"))
    assert len(contents) == 200
    assert contents[-1] == {"total_score": 999}


def test_save_game_score_swallows_corrupt_existing(tmp_path):
    """If existing file is corrupt, save must not raise — caller stays alive."""
    sys = _make_scoring_system(tmp_path)
    target = Path(sys.SAVE_PATH) / "game_scores.json"
    target.write_text("{not valid", encoding="utf-8")
    # Must not raise, even though loading the existing file fails.
    sys._save_game_score({"total_score": 7})
