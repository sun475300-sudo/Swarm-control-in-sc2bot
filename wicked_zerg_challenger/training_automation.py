# -*- coding: utf-8 -*-
"""
Phase 56: Mixed-race benchmark runner and result/log analyzer.

Usage:
    python training_automation.py
    python training_automation.py --games 20 --difficulty Medium --enemy-races mixed
    python training_automation.py --games 9 --enemy-races Protoss,Terran,Zerg
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent
RUN_SINGLE_GAME = ROOT / "run_single_game.py"
RUN_LOG_DIR = ROOT / "logs" / "training_runs"
BOT_LOG_CANDIDATES = [
    ROOT / "logs" / "bot.log",
    ROOT.parent / "logs" / "bot.log",
]
MIXED_ENEMY_RACES = ["Protoss", "Terran", "Zerg"]


@dataclass
class GameResult:
    index: int
    map_name: str
    enemy_race: str
    difficulty: str
    outcome: str
    runtime_sec: float
    warnings: int
    errors: int
    return_code: int
    timed_out: bool = False
    crashed: bool = False


@dataclass
class TrainingSummary:
    started_at: str
    finished_at: str
    games: int
    wins: int
    losses: int
    ties: int
    overall_win_rate: float
    avg_runtime_sec: float
    warning_total: int
    error_total: int
    timeouts: int
    crashes: int
    by_race: Dict[str, Dict[str, float | int]]
    game_durations: List[float]
    weakest_matchup: str | None
    benchmark_passed: bool
    next_focus_race: str | None


def _detect_bot_log() -> Path | None:
    for candidate in BOT_LOG_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _read_log_tail(log_path: Path, max_lines: int = 400) -> List[str]:
    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    return content[-max_lines:]


def _count_warn_error(lines: List[str]) -> Dict[str, int]:
    warning = 0
    error = 0
    for line in lines:
        if " WARNING " in line or "[WARNING]" in line:
            warning += 1
        if " ERROR " in line or "[ERROR]" in line or "Traceback" in line:
            error += 1
    return {"warning": warning, "error": error}


def _parse_outcome(output: str) -> str:
    text = output.upper()
    if "[VICTORY]" in text or "VICTORY" in text:
        return "victory"
    if "[TIE]" in text or " TIE" in text:
        return "tie"
    if "[DEFEAT]" in text or "DEFEAT" in text:
        return "defeat"
    return "unknown"


def _normalize_enemy_race(name: str) -> str:
    normalized = (name or "").strip().capitalize()
    if normalized == "Random":
        return "Random"
    if normalized in {"Protoss", "Terran", "Zerg"}:
        return normalized
    raise ValueError(f"Unsupported enemy race: {name}")


def build_enemy_race_sequence(
    games: int,
    enemy_race: str = "Protoss",
    enemy_races: str | None = None,
) -> List[str]:
    if games <= 0:
        return []

    if enemy_races:
        if enemy_races.strip().lower() == "mixed":
            rotation = MIXED_ENEMY_RACES
        else:
            rotation = [
                _normalize_enemy_race(part)
                for part in enemy_races.split(",")
                if part.strip()
            ]
            if not rotation:
                raise ValueError("Enemy race rotation cannot be empty")
    else:
        rotation = [_normalize_enemy_race(enemy_race)]

    return [rotation[index % len(rotation)] for index in range(games)]


def run_one_game(index: int, map_name: str, enemy_race: str, difficulty: str) -> GameResult:
    start = time.time()
    bot_log = _detect_bot_log()

    before_counts = {"warning": 0, "error": 0}
    if bot_log:
        before_counts = _count_warn_error(_read_log_tail(bot_log))

    cmd = [
        sys.executable,
        str(RUN_SINGLE_GAME),
        "--map",
        map_name,
        "--enemy-race",
        enemy_race,
        "--difficulty",
        difficulty,
    ]
    env = os.environ.copy()
    env.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60 * 25,
            env=env,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        runtime_sec = round(time.time() - start, 2)
        combined_output = "\n".join(
            part for part in ((exc.stdout or "").strip(), (exc.stderr or "").strip()) if part
        )
        outcome = _parse_outcome(combined_output) if combined_output else "timeout"
        return GameResult(
            index=index,
            map_name=map_name,
            enemy_race=enemy_race,
            difficulty=difficulty,
            outcome=outcome,
            runtime_sec=runtime_sec,
            warnings=0,
            errors=1,
            return_code=-1,
            timed_out=True,
            crashed=False,
        )

    runtime_sec = round(time.time() - start, 2)
    combined_output = "\n".join(
        part for part in ((proc.stdout or "").strip(), (proc.stderr or "").strip()) if part
    )
    outcome = _parse_outcome(combined_output)

    after_counts = {"warning": 0, "error": 0}
    if bot_log:
        after_counts = _count_warn_error(_read_log_tail(bot_log))

    warnings = max(0, after_counts["warning"] - before_counts["warning"])
    errors = max(0, after_counts["error"] - before_counts["error"])
    crashed = proc.returncode != 0

    return GameResult(
        index=index,
        map_name=map_name,
        enemy_race=enemy_race,
        difficulty=difficulty,
        outcome=outcome,
        runtime_sec=runtime_sec,
        warnings=warnings,
        errors=errors,
        return_code=proc.returncode,
        timed_out=timed_out,
        crashed=crashed,
    )


def build_training_summary(
    results: List[GameResult],
    started_at: str | None = None,
    finished_at: str | None = None,
) -> TrainingSummary:
    wins = sum(1 for result in results if result.outcome == "victory")
    losses = sum(1 for result in results if result.outcome == "defeat")
    ties = sum(1 for result in results if result.outcome == "tie")
    timeouts = sum(1 for result in results if result.timed_out)
    crashes = sum(1 for result in results if result.crashed)
    durations = [result.runtime_sec for result in results]
    avg_runtime = round(sum(durations) / max(1, len(durations)), 2)
    overall_win_rate = round((wins / max(1, len(results))) * 100, 2)

    by_race: Dict[str, Dict[str, float | int]] = {}
    for result in results:
        entry = by_race.setdefault(
            result.enemy_race,
            {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "timeouts": 0,
                "crashes": 0,
                "unknown": 0,
                "warning_total": 0,
                "error_total": 0,
                "win_rate": 0.0,
            },
        )
        entry["games"] += 1
        entry["warning_total"] += result.warnings
        entry["error_total"] += result.errors
        if result.outcome == "victory":
            entry["wins"] += 1
        elif result.outcome == "defeat":
            entry["losses"] += 1
        elif result.outcome == "tie":
            entry["ties"] += 1
        else:
            entry["unknown"] += 1
        if result.timed_out:
            entry["timeouts"] += 1
        if result.crashed:
            entry["crashes"] += 1

    for race, entry in by_race.items():
        games = int(entry["games"])
        entry["win_rate"] = round((int(entry["wins"]) / max(1, games)) * 100, 2)

    weakest_matchup = None
    if by_race:
        weakest_matchup = min(
            by_race.items(),
            key=lambda item: (float(item[1]["win_rate"]), -int(item[1]["games"]), item[0]),
        )[0]

    benchmark_passed = (
        len(results) >= 20
        and overall_win_rate >= 60.0
        and timeouts == 0
        and crashes == 0
    )
    next_focus_race = None if benchmark_passed else weakest_matchup

    started_value = started_at or datetime.now().strftime("%Y%m%d_%H%M%S")
    finished_value = finished_at or datetime.now().strftime("%Y%m%d_%H%M%S")
    return TrainingSummary(
        started_at=started_value,
        finished_at=finished_value,
        games=len(results),
        wins=wins,
        losses=losses,
        ties=ties,
        overall_win_rate=overall_win_rate,
        avg_runtime_sec=avg_runtime,
        warning_total=sum(result.warnings for result in results),
        error_total=sum(result.errors for result in results),
        timeouts=timeouts,
        crashes=crashes,
        by_race=by_race,
        game_durations=durations,
        weakest_matchup=weakest_matchup,
        benchmark_passed=benchmark_passed,
        next_focus_race=next_focus_race,
    )


def save_report(
    results: List[GameResult],
    config: Dict[str, Any],
    report_prefix: str = "training_report",
    started_at: str | None = None,
    finished_at: str | None = None,
) -> Path:
    RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = RUN_LOG_DIR / f"{report_prefix}_{now}.json"

    summary = build_training_summary(
        results,
        started_at=started_at,
        finished_at=finished_at,
    )
    payload = {
        "config": config,
        "summary": asdict(summary),
        "results": [asdict(result) for result in results],
    }

    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automate SC2 mixed-race benchmarks and summarize results."
    )
    parser.add_argument(
        "--games",
        type=int,
        default=20,
        help="Number of games to run",
    )
    parser.add_argument(
        "--map",
        dest="map_name",
        default="AbyssalReefLE",
        help="SC2 map name",
    )
    parser.add_argument(
        "--enemy-race",
        default="Protoss",
        help="Single enemy race fallback when --enemy-races is not set",
    )
    parser.add_argument(
        "--enemy-races",
        default="mixed",
        help="Enemy race rotation: mixed or comma-separated list",
    )
    parser.add_argument(
        "--difficulty",
        default="Medium",
        help="Enemy difficulty",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not RUN_SINGLE_GAME.exists():
        print(f"[ERROR] Missing script: {RUN_SINGLE_GAME}")
        return 1

    enemy_race_sequence = build_enemy_race_sequence(
        games=args.games,
        enemy_race=args.enemy_race,
        enemy_races=args.enemy_races,
    )
    config = {
        "games": args.games,
        "map_name": args.map_name,
        "difficulty": args.difficulty,
        "enemy_races": args.enemy_races,
        "enemy_race_sequence": enemy_race_sequence,
    }

    results: List[GameResult] = []

    for index, enemy_race in enumerate(enemy_race_sequence, start=1):
        print(
            f"[TRAIN] Game {index}/{args.games} starting..."
            f" race={enemy_race} difficulty={args.difficulty}"
        )
        result = run_one_game(
            index=index,
            map_name=args.map_name,
            enemy_race=enemy_race,
            difficulty=args.difficulty,
        )

        results.append(result)
        print(
            f"[TRAIN] Game {index} done: outcome={result.outcome}, "
            f"runtime={result.runtime_sec}s, warn={result.warnings}, "
            f"err={result.errors}, rc={result.return_code}"
        )

    finished_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = save_report(
        results,
        config=config,
        started_at=started_at,
        finished_at=finished_at,
    )
    summary = build_training_summary(
        results,
        started_at=started_at,
        finished_at=finished_at,
    )
    print(f"[TRAIN] Report saved: {report}")
    print(
        f"[TRAIN] Summary: games={summary.games}, "
        f"win_rate={summary.overall_win_rate}%, "
        f"timeouts={summary.timeouts}, crashes={summary.crashes}"
    )
    if summary.next_focus_race:
        print(f"[TRAIN] Next focus race: {summary.next_focus_race}")

    return 0 if summary.benchmark_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
