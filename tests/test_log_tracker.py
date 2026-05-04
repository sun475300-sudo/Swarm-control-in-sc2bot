"""TestLogTracker 단위 테스트."""

import json
import os
from pathlib import Path

import pytest

# 프로젝트 루트의 모듈 import
import sys

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_log_tracker import TestLogTracker  # noqa: E402


@pytest.fixture
def tracker(tmp_path: Path) -> TestLogTracker:
    return TestLogTracker(log_file=str(tmp_path / "log.json"))


def test_log_appends_and_persists(tmp_path: Path) -> None:
    log_path = tmp_path / "log.json"
    tracker = TestLogTracker(log_file=str(log_path))
    tracker.log("a", "PASS", 12.5, {"tests": 1})

    # 새 인스턴스가 파일에서 다시 로드한다.
    other = TestLogTracker(log_file=str(log_path))
    assert len(other.entries) == 1
    assert other.entries[0].test_name == "a"
    assert other.entries[0].status == "PASS"


def test_unknown_status_normalized_to_error(tracker: TestLogTracker) -> None:
    entry = tracker.log("x", "WAT", 0.0)
    assert entry.status == "ERROR"


def test_summary_excludes_skip_from_denominator(
    tracker: TestLogTracker,
) -> None:
    tracker.log("a", "PASS", 1, {"tests": 1, "passed": 1})
    tracker.log("b", "PASS", 1, {"tests": 1, "passed": 1})
    tracker.log("c", "SKIP", 0)

    summary = tracker.get_summary()
    # 분모에서 SKIP 은 빠지므로 PASS 100%
    assert summary["pass_rate"] == 100.0
    assert summary["passed"] == 2
    assert summary["skipped"] == 1


def test_summary_partial_uses_inner_ratio(tracker: TestLogTracker) -> None:
    tracker.log("a", "PASS", 1, {"tests": 1, "passed": 1})
    tracker.log("b", "PARTIAL", 1, {"tests": 100, "passed": 25})

    summary = tracker.get_summary()
    # PASS=1, PARTIAL=0.25 → effective pass=1.25 / total=2 = 62.5%
    assert summary["partial"] == 1
    assert abs(summary["pass_rate"] - 62.5) < 0.01


def test_summary_partial_without_details_falls_back(
    tracker: TestLogTracker,
) -> None:
    tracker.log("a", "PARTIAL", 1)  # no inner counts

    summary = tracker.get_summary()
    # 0.5 / 1 → 50%
    assert abs(summary["pass_rate"] - 50.0) < 0.01


def test_summary_empty(tracker: TestLogTracker) -> None:
    summary = tracker.get_summary()
    assert summary["total_executions"] == 0
    assert summary["pass_rate"] == 0.0


def test_get_recent_returns_tail(tracker: TestLogTracker) -> None:
    for i in range(20):
        tracker.log(f"t{i}", "PASS", 0)
    recent = tracker.get_recent(5)
    assert [e.test_name for e in recent] == ["t15", "t16", "t17", "t18", "t19"]


def test_load_corrupt_file_resets(tmp_path: Path) -> None:
    log_path = tmp_path / "log.json"
    log_path.write_text("not json", encoding="utf-8")
    tracker = TestLogTracker(log_file=str(log_path))
    assert tracker.entries == []


def test_ingest_comprehensive_results_classifies_categories(
    tmp_path: Path,
) -> None:
    results = {
        "summary": {"total_tests": 100},
        "all_pass": {"tests": 5, "passed": 5, "duration": 10},
        "all_fail": {"tests": 5, "passed": 0, "duration": 10},
        "partial_run": {"tests": 5, "passed": 3, "duration": 10},
        "errored": {
            "tests": 0,
            "passed": 0,
            "duration": 1,
            "error": "boom",
        },
        "empty": {"tests": 0, "passed": 0, "duration": 0},
    }
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(results), encoding="utf-8")

    tracker = TestLogTracker(log_file=str(tmp_path / "log.json"))
    n = tracker.ingest_comprehensive_results(str(results_path))
    assert n == 5

    statuses = {e.test_name: e.status for e in tracker.entries}
    assert statuses["all_pass"] == "PASS"
    assert statuses["all_fail"] == "FAIL"
    assert statuses["partial_run"] == "PARTIAL"
    assert statuses["errored"] == "ERROR"
    assert statuses["empty"] == "SKIP"
