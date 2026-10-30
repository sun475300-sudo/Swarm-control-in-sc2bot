#!/usr/bin/env python3
"""Publish README status from completed JUnit and optional real-match evidence."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

START = "<!-- VERIFIED-STATUS:START -->"
END = "<!-- VERIFIED-STATUS:END -->"
COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


def utc_time(value: str) -> str:
    """Require a timezone so a report cannot silently use the worker timezone."""
    if not isinstance(value, str):
        raise ValueError("Evidence timestamps must be ISO 8601 dates")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Evidence timestamps must be ISO 8601 dates") from exc
    if parsed.tzinfo is None:
        raise ValueError("Evidence timestamps must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def integer(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def junit_summary(path: Path) -> dict:
    """Check summary attributes against test cases instead of trusting counters."""
    root = ET.parse(path).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Expected a JUnit testsuite or testsuites document")
    cases = list(root.iter("testcase"))
    if not cases:
        raise ValueError("Zero tests cannot establish readiness")

    def counts(elements):
        tally = Counter(tests=0, failures=0, errors=0, skipped=0)
        for case in elements:
            present = [
                name
                for name in ("failure", "error", "skipped")
                if case.find(name) is not None
            ]
            if len(present) > 1:
                raise ValueError("A JUnit test case has conflicting outcomes")
            tally["tests"] += 1
            if present:
                tally[
                    {"failure": "failures", "error": "errors", "skipped": "skipped"}[
                        present[0]
                    ]
                ] += 1
        return dict(tally)

    for node in root.iter():
        if node.tag not in {"testsuite", "testsuites"}:
            continue
        actual = counts(node.iter("testcase"))
        for name, value in actual.items():
            if name in node.attrib:
                try:
                    declared = int(node.attrib[name])
                except ValueError as exc:
                    raise ValueError(f"Invalid JUnit {name} counter") from exc
                if declared != value:
                    raise ValueError(f"JUnit {name} counter disagrees with test cases")
    summary = counts(cases)
    summary["passed"] = (
        summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
    )
    summary["status"] = (
        "passed" if not summary["failures"] and not summary["errors"] else "failed"
    )
    return summary


def benchmark_summary(path: Path | None, source_commit: str, checked_at: str) -> dict:
    if path is None:
        return {"status": "unverified", "reason": "No real-game benchmark was supplied"}
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Benchmark must be a JSON object")
    if report.get("schema_version") != 1 or report.get("evidence") != "real_game":
        raise ValueError(
            "Only schema_version=1 real_game benchmark evidence is supported"
        )
    commit = report.get("source_commit")
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        raise ValueError(
            "Benchmark source_commit must identify the full tested Git commit"
        )
    dirty = report.get("source_dirty")
    if not isinstance(dirty, bool):
        raise ValueError("Benchmark must state whether the tested source was dirty")
    timestamp = utc_time(report.get("timestamp"))
    finished_at = utc_time(report.get("finished_at"))
    if (
        not datetime.fromisoformat(timestamp)
        <= datetime.fromisoformat(finished_at)
        <= datetime.fromisoformat(checked_at)
    ):
        raise ValueError("Benchmark timestamps are out of order or in the future")
    games = report.get("games")
    if not isinstance(games, list) or not games:
        raise ValueError("A real-game report needs individual game outcomes")
    tally = Counter(wins=0, losses=0, ties=0, errors=0)
    outcomes = {"WIN": "wins", "LOSS": "losses", "TIE": "ties", "error": "errors"}
    for game in games:
        if not isinstance(game, dict) or game.get("result") not in outcomes:
            raise ValueError("Benchmark contains an unknown game outcome")
        if game.get("won") is not (game["result"] == "WIN"):
            raise ValueError("Benchmark won flag disagrees with its outcome")
        for field in ("map", "race", "difficulty"):
            if not isinstance(game.get(field), str) or not game[field].strip():
                raise ValueError(f"Benchmark game is missing {field}")
        tally[outcomes[game["result"]]] += 1
    for name, actual in tally.items():
        if integer(report.get(name), name) != actual:
            raise ValueError(f"Benchmark {name} counter disagrees with game outcomes")
    total = integer(report.get("total_games"), "total_games")
    completed = integer(report.get("completed_games"), "completed_games")
    if total != len(games) or completed != total - tally["errors"] or completed == 0:
        raise ValueError("Benchmark game totals are incomplete or inconsistent")
    rate = report.get("win_rate")
    expected_rate = 100 * tally["wins"] / completed
    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not math.isclose(rate, expected_rate, abs_tol=1e-8)
    ):
        raise ValueError("Benchmark win_rate disagrees with completed games")
    target = report.get("min_win_rate")
    if target is not None and (
        isinstance(target, bool)
        or not isinstance(target, (int, float))
        or not math.isfinite(target)
        or not 0 <= target <= 100
    ):
        raise ValueError("Benchmark min_win_rate must be a percentage")
    gate = tally["errors"] == 0 and (target is None or rate >= target)
    if report.get("gate_passed") is not gate or report.get("status") != (
        "passed" if gate else "failed"
    ):
        raise ValueError("Benchmark gate status disagrees with the reported results")
    current = commit == source_commit and not dirty
    return {
        "status": "current" if current else "historical",
        "source_commit": commit,
        "source_dirty": dirty,
        "timestamp": timestamp,
        "finished_at": finished_at,
        "total_games": total,
        "completed_games": completed,
        **dict(tally),
        "win_rate": rate,
        "min_win_rate": target,
        "gate_passed": gate,
    }


def render(status: dict) -> str:
    tests = status["unit_tests"]
    lines = [
        START,
        "",
        f"검증 시각: {status['checked_at']} · 소스: `{status['source_commit'][:12]}`",
        "",
        "| 검증 항목 | 결과 |",
        "|:---|:---|",
        f"| 봇·도구 테스트 | {tests['passed']} 통과 / {tests['failures']} 실패 / {tests['errors']} 오류 / {tests['skipped']} 건너뜀 (총 {tests['tests']}) |",
    ]
    games = status["real_games"]
    if games["status"] == "unverified":
        lines.append(
            "| 실제 SC2 경기 | 미검증 — 실제 경기 결과가 제공되지 않았습니다 |"
        )
    else:
        label = (
            "현재 커밋·깨끗한 소스"
            if games["status"] == "current"
            else "이전 커밋 또는 수정된 소스의 기록"
        )
        lines.append(
            f"| 실제 SC2 경기 | {label}: {games['wins']}승 {games['losses']}패 {games['ties']}무, 오류 {games['errors']}건 · 완료 {games['completed_games']}경기 · 승률 {games['win_rate']:.1f}% |"
        )
        lines.append(
            f"| 경기 판정 | {'설정된 기준 통과' if games['gate_passed'] else '설정된 기준 미달 또는 경기 오류'} · 소스 `{games['source_commit'][:12]}` · {games['finished_at']} |"
        )
    lines.extend(
        [
            "",
            "단위 테스트 통과와 실제 경기 승률은 별도 결과입니다. 대회 승리를 보장하지 않습니다.",
            "",
            END,
        ]
    )
    return "\n".join(lines)


def replace_block(content: str, block: str) -> str:
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError(
            "README must contain exactly one pair of verified status markers"
        )
    start = content.index(START)
    end = content.index(END)
    if end < start:
        raise ValueError("README verified status markers are out of order")
    return content[:start] + block + content[end + len(END) :]


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument(
        "--json-output", type=Path, default=Path("data/reports/readiness.json")
    )
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--checked-at")
    args = parser.parse_args(argv)
    try:
        source_commit = (
            args.source_commit
            or subprocess.run(
                ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
            ).stdout.strip()
        )
        if not COMMIT.fullmatch(source_commit):
            raise ValueError("source_commit must be a full Git commit hash")
        checked_at = utc_time(args.checked_at or datetime.now(timezone.utc).isoformat())
        tests = junit_summary(args.junit)
        if tests["status"] != "passed" or tests["passed"] == 0:
            raise ValueError(
                "Failed, errored, or wholly skipped tests cannot publish readiness"
            )
        status = {
            "schema_version": 1,
            "checked_at": checked_at,
            "source_commit": source_commit,
            "unit_tests": tests,
            "real_games": benchmark_summary(args.benchmark, source_commit, checked_at),
        }
        updated = replace_block(args.readme.read_text(encoding="utf-8"), render(status))
        serialized = (
            json.dumps(status, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
        if args.readme.resolve() == args.json_output.resolve():
            raise ValueError("README and JSON output must be different files")
        atomic_write(args.json_output, serialized)
        atomic_write(args.readme, updated)
    except (
        OSError,
        ValueError,
        TypeError,
        ET.ParseError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"Readiness update failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Updated {args.readme}: {tests['passed']} tests passed; real games {status['real_games']['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
