# -*- coding: utf-8 -*-
"""
Phase 44: Automated single-game training runner + result/log analyzer.

Usage:
    python training_automation.py --games 5
    python training_automation.py --games 10 --map AbyssalReefLE --difficulty Easy
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List


ROOT = Path(__file__).resolve().parent
RUN_SINGLE_GAME = ROOT / "run_single_game.py"
RUN_LOG_DIR = ROOT / "logs" / "training_runs"
BOT_LOG_CANDIDATES = [
    ROOT / "logs" / "bot.log",
    ROOT.parent / "logs" / "bot.log",
]


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


@dataclass
class TrainingSummary:
    started_at: str
    finished_at: str
    games: int
    wins: int
    losses: int
    ties: int
    avg_runtime_sec: float
    warning_total: int
    error_total: int


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


def _parse_outcome(stdout: str) -> str:
    text = stdout.upper()
    if "[VICTORY]" in text or "VICTORY" in text:
        return "victory"
    if "[TIE]" in text or " TIE" in text:
        return "tie"
    if "[DEFEAT]" in text or "DEFEAT" in text:
        return "defeat"
    return "unknown"


def run_one_game(index: int, map_name: str, enemy_race: str, difficulty: str) -> GameResult:
    start = time.time()
    bot_log = _detect_bot_log()

    before_counts = {"warning": 0, "error": 0}
    if bot_log:
        before_counts = _count_warn_error(_read_log_tail(bot_log))

    cmd = [
        sys.executable,
        str(RUN_SINGLE_GAME),
        "--map", map_name,
        "--enemy-race", enemy_race,
        "--difficulty", difficulty,
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60 * 25,
    )

    runtime_sec = round(time.time() - start, 2)
    stdout = proc.stdout or ""
    outcome = _parse_outcome(stdout)

    after_counts = {"warning": 0, "error": 0}
    if bot_log:
        after_counts = _count_warn_error(_read_log_tail(bot_log))

    warnings = max(0, after_counts["warning"] - before_counts["warning"])
    errors = max(0, after_counts["error"] - before_counts["error"])

    return GameResult(
        index=index,
        map_name=map_name,
        enemy_race=enemy_race,
        difficulty=difficulty,
        outcome=outcome,
        runtime_sec=runtime_sec,
        warnings=warnings,
        errors=errors,
    )


def save_report(results: List[GameResult], report_prefix: str = "training_report") -> Path:
    RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = RUN_LOG_DIR / f"{report_prefix}_{now}.json"

    wins = sum(1 for r in results if r.outcome == "victory")
    losses = sum(1 for r in results if r.outcome == "defeat")
    ties = sum(1 for r in results if r.outcome == "tie")
    avg_runtime = round(sum(r.runtime_sec for r in results) / max(1, len(results)), 2)

    summary = TrainingSummary(
        started_at=now,
        finished_at=datetime.now().strftime("%Y%m%d_%H%M%S"),
        games=len(results),
        wins=wins,
        losses=losses,
        ties=ties,
        avg_runtime_sec=avg_runtime,
        warning_total=sum(r.warnings for r in results),
        error_total=sum(r.errors for r in results),
    )

    payload = {
        "summary": asdict(summary),
        "results": [asdict(r) for r in results],
    }

    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate SC2 single-game training and summarize results.")
    parser.add_argument("--games", type=int, default=3, help="Number of games to run")
    parser.add_argument("--map", dest="map_name", default="AbyssalReefLE", help="SC2 map name")
    parser.add_argument("--enemy-race", default="Protoss", help="Enemy race name")
    parser.add_argument("--difficulty", default="Easy", help="Enemy difficulty")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not RUN_SINGLE_GAME.exists():
        print(f"[ERROR] Missing script: {RUN_SINGLE_GAME}")
        return 1

    results: List[GameResult] = []

    for i in range(1, args.games + 1):
        print(f"[TRAIN] Game {i}/{args.games} starting...")
        try:
            result = run_one_game(
                index=i,
                map_name=args.map_name,
                enemy_race=args.enemy_race,
                difficulty=args.difficulty,
            )
            results.append(result)
            print(
                f"[TRAIN] Game {i} done: outcome={result.outcome}, "
                f"runtime={result.runtime_sec}s, warn={result.warnings}, err={result.errors}"
            )
        except subprocess.TimeoutExpired:
            print(f"[TRAIN] Game {i} timed out")
            results.append(
                GameResult(
                    index=i,
                    map_name=args.map_name,
                    enemy_race=args.enemy_race,
                    difficulty=args.difficulty,
                    outcome="timeout",
                    runtime_sec=60 * 25,
                    warnings=0,
                    errors=1,
                )
            )

    report = save_report(results)
    print(f"[TRAIN] Report saved: {report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
