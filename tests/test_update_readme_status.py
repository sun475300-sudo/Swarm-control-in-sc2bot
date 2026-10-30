"""Regression checks for source-backed README publication."""

import copy
import json
from pathlib import Path

import pytest
from scripts.update_readme_status import (
    END,
    START,
    benchmark_summary,
    junit_summary,
    main,
)

COMMIT = "a" * 40
CHECKED_AT = "2026-10-30T12:00:00+00:00"


def write_junit(path: Path, outcomes=("passed", "passed", "skipped")):
    children = "".join(
        f'<testcase name="case{index}">{"" if outcome == "passed" else f"<{outcome}/>"}</testcase>'
        for index, outcome in enumerate(outcomes)
    )
    path.write_text(
        f'<testsuites><testsuite tests="{len(outcomes)}" failures="{outcomes.count("failure")}" '
        f'errors="{outcomes.count("error")}" skipped="{outcomes.count("skipped")}">{children}</testsuite></testsuites>',
        encoding="utf-8",
    )
    return path


def real_report():
    return {
        "schema_version": 1,
        "evidence": "real_game",
        "timestamp": "2026-10-30T10:00:00+00:00",
        "finished_at": "2026-10-30T11:00:00+00:00",
        "source_commit": COMMIT,
        "source_dirty": False,
        "total_games": 3,
        "completed_games": 3,
        "wins": 1,
        "losses": 1,
        "ties": 1,
        "errors": 0,
        "win_rate": 100 / 3,
        "min_win_rate": 30,
        "gate_passed": True,
        "status": "passed",
        "games": [
            {
                "map": "AbyssalReefLE",
                "race": "Terran",
                "difficulty": "Medium",
                "result": result,
                "won": result == "WIN",
            }
            for result in ("WIN", "LOSS", "TIE")
        ],
    }


def write_report(tmp_path, report):
    path = tmp_path / "benchmark.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def publish_args(tmp_path, outcomes=("passed", "passed", "skipped")):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Heading\n\n{START}\nold status\n{END}\n\nKeep these commands.\n",
        encoding="utf-8",
    )
    output = tmp_path / "status.json"
    junit = write_junit(tmp_path / "tests.xml", outcomes)
    args = [
        "--junit",
        str(junit),
        "--readme",
        str(readme),
        "--json-output",
        str(output),
        "--source-commit",
        COMMIT,
        "--checked-at",
        CHECKED_AT,
    ]
    return args, readme, output


def test_publish_preserves_manual_content_and_is_idempotent(tmp_path):
    args, readme, output = publish_args(tmp_path)
    assert main(args) == 0
    status = json.loads(output.read_text())
    assert status["unit_tests"] == {
        "tests": 3,
        "passed": 2,
        "failures": 0,
        "errors": 0,
        "skipped": 1,
        "status": "passed",
    }
    assert status["real_games"]["status"] == "unverified"
    before = (readme.read_bytes(), output.read_bytes())
    assert readme.read_text().startswith("# Heading\n")
    assert readme.read_text().endswith("Keep these commands.\n")
    assert "2 통과" in readme.read_text()
    assert main(args) == 0
    assert (readme.read_bytes(), output.read_bytes()) == before


@pytest.mark.parametrize(
    "outcomes", [(), ("skipped",), ("passed", "failure"), ("passed", "error")]
)
def test_no_publication_for_unexecuted_or_failed_tests(tmp_path, outcomes):
    args, readme, output = publish_args(tmp_path, outcomes)
    before = readme.read_bytes()
    assert main(args) == 1
    assert readme.read_bytes() == before
    assert not output.exists()


@pytest.mark.parametrize(
    "xml",
    [
        "<testsuite>",
        '<testsuite tests="3"><testcase name="only"/></testsuite>',
        '<testsuite tests="1"><testcase><failure/><error/></testcase></testsuite>',
    ],
)
def test_malformed_or_conflicting_junit_does_not_publish(tmp_path, xml):
    args, readme, output = publish_args(tmp_path)
    (tmp_path / "tests.xml").write_text(xml)
    assert main(args) == 1
    assert "old status" in readme.read_text()
    assert not output.exists()


def test_nested_junit_counts_cases_only_once(tmp_path):
    path = tmp_path / "nested.xml"
    path.write_text(
        '<testsuites tests="2"><testsuite tests="2"><testsuite tests="1"><testcase name="first"/></testsuite><testsuite tests="1"><testcase name="second"/></testsuite></testsuite></testsuites>'
    )
    assert junit_summary(path)["passed"] == 2


@pytest.mark.parametrize(
    "content", ["no markers", f"{START}{END}{START}{END}", f"{END}{START}"]
)
def test_marker_errors_leave_outputs_untouched(tmp_path, content):
    args, readme, output = publish_args(tmp_path)
    readme.write_text(content)
    assert main(args) == 1
    assert readme.read_text() == content
    assert not output.exists()


def test_valid_real_game_evidence_distinguishes_current_source(tmp_path):
    path = write_report(tmp_path, real_report())
    result = benchmark_summary(path, COMMIT, CHECKED_AT)
    assert result["status"] == "current"
    assert result["ties"] == 1
    assert result["win_rate"] == pytest.approx(100 / 3)
    assert benchmark_summary(path, "b" * 40, CHECKED_AT)["status"] == "historical"
    report = real_report()
    report["source_dirty"] = True
    assert (
        benchmark_summary(write_report(tmp_path, report), COMMIT, CHECKED_AT)["status"]
        == "historical"
    )


def test_real_loss_below_target_is_retained_without_claiming_goal_success(tmp_path):
    report = real_report()
    report.update(min_win_rate=90, gate_passed=False, status="failed")
    args, readme, output = publish_args(tmp_path)
    assert main(args + ["--benchmark", str(write_report(tmp_path, report))]) == 0
    assert json.loads(output.read_text())["real_games"]["gate_passed"] is False
    assert "기준 미달" in readme.read_text()


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 0},
        {"evidence": "synthetic"},
        {"source_commit": "short"},
        {"source_dirty": None},
        {"wins": 2},
        {"completed_games": 2},
        {"total_games": 4},
        {"win_rate": 100},
        {"gate_passed": False},
        {"min_win_rate": 101},
        {"timestamp": "2026-10-30T13:00:00+00:00"},
        {"finished_at": "2026-10-30T12:00:00.000001+00:00"},
        {"timestamp": "2026-10-30T10:00:00"},
    ],
)
def test_unsupported_or_inconsistent_benchmark_cannot_publish(tmp_path, change):
    report = real_report()
    report.update(change)
    args, readme, output = publish_args(tmp_path)
    assert main(args + ["--benchmark", str(write_report(tmp_path, report))]) == 1
    assert "old status" in readme.read_text()
    assert not output.exists()


@pytest.mark.parametrize(
    "field,value", [("result", "UNKNOWN"), ("won", False), ("map", "")]
)
def test_individual_game_must_match_totals_and_target_metadata(tmp_path, field, value):
    report = copy.deepcopy(real_report())
    report["games"][0][field] = value
    with pytest.raises(ValueError):
        benchmark_summary(write_report(tmp_path, report), COMMIT, CHECKED_AT)


def test_old_report_fixture_is_not_accepted_as_real_evidence(tmp_path):
    report = {"timestamp": "2026-05-09", "wins": 10, "losses": 0, "win_rate": 100}
    with pytest.raises(ValueError, match="real_game"):
        benchmark_summary(write_report(tmp_path, report), COMMIT, CHECKED_AT)


@pytest.mark.parametrize(
    "report",
    [
        [],
        {
            "schema_version": 1,
            "evidence": "real_game",
            "source_commit": COMMIT,
            "source_dirty": False,
        },
    ],
)
def test_missing_or_malformed_benchmark_metadata_has_no_traceback(tmp_path, report):
    args, readme, output = publish_args(tmp_path)
    assert main(args + ["--benchmark", str(write_report(tmp_path, report))]) == 1
    assert "old status" in readme.read_text()
    assert not output.exists()
