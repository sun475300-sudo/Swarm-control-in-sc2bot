#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mass Testing Script - 난이도/종족별 대규모 인게임 테스트

All difficulties x All races = comprehensive test matrix.
Only completed game-engine matches count toward the win-rate gate.
"""

import argparse
import json
import logging
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

logger = logging.getLogger("RunMassTest")

sys.path.insert(0, str(Path(__file__).parent))

# s2clientprotocol wheels contain legacy generated protobuf definitions.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


# SC2 path auto-setup
def _ensure_sc2_path():
    if sys.platform != "win32":
        return
    if "SC2PATH" in os.environ:
        if os.path.exists(os.path.join(os.environ["SC2PATH"], "Versions")):
            return
    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]
    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return


_ensure_sc2_path()

try:
    from sc2 import maps
    from sc2.data import Difficulty, Race
    from sc2.main import run_game
    from sc2.player import Bot, Computer
    from wicked_zerg_bot_pro_impl import WickedZergBotProImpl
except ImportError as exc:  # SC2 runtime deps optional for CLI/test helpers
    logger.warning("SC2 runtime not available: %s", exc)
    maps = None
    run_game = None
    Bot = Computer = WickedZergBotProImpl = None

    from enum import Enum

    class Race(Enum):
        Random = "Random"
        Terran = "Terran"
        Zerg = "Zerg"
        Protoss = "Protoss"

    class Difficulty(Enum):
        VeryEasy = "VeryEasy"
        Easy = "Easy"
        Medium = "Medium"
        MediumHard = "MediumHard"
        Hard = "Hard"
        Harder = "Harder"
        VeryHard = "VeryHard"
        CheatVision = "CheatVision"
        CheatMoney = "CheatMoney"
        CheatInsane = "CheatInsane"


# GPU setup
try:
    import torch

    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        torch.set_default_device("cuda")
        logger.info(f"{torch.cuda.get_device_name(0)} - CUDA {torch.version.cuda}")
except ImportError:
    GPU_AVAILABLE = False

# Test matrix
MAPS = ["AbyssalReefLE", "AscensiontoAiurLE", "OdysseyLE"]
RACES = [Race.Protoss, Race.Terran, Race.Zerg]
DIFFICULTIES = [
    (Difficulty.VeryEasy, "VeryEasy"),
    (Difficulty.Easy, "Easy"),
    (Difficulty.Medium, "Medium"),
    (Difficulty.MediumHard, "MediumHard"),
]

GAMES_PER_MATCHUP = 1  # 1 game per combination = 36 total games

RACE_BY_NAME = {
    "Terran": Race.Terran,
    "Protoss": Race.Protoss,
    "Zerg": Race.Zerg,
}

DIFFICULTY_BY_NAME = {
    "VeryEasy": Difficulty.VeryEasy,
    "Easy": Difficulty.Easy,
    "Medium": Difficulty.Medium,
    "MediumHard": Difficulty.MediumHard,
    "Hard": Difficulty.Hard,
    "Harder": Difficulty.Harder,
    "VeryHard": Difficulty.VeryHard,
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run SC2 mass benchmark games")
    parser.add_argument(
        "--opponent",
        choices=sorted(RACE_BY_NAME),
        help="Filter to one opponent race",
    )
    parser.add_argument(
        "--difficulty",
        choices=sorted(DIFFICULTY_BY_NAME),
        help="Filter to one AI difficulty",
    )
    parser.add_argument(
        "--games",
        type=_positive_int,
        default=None,
        help="Number of games for the selected matchup",
    )
    parser.add_argument(
        "--maps",
        default=",".join(MAPS),
        help="Comma-separated map list to rotate through",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated matrix without launching SC2",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("mass_test_results.json"),
        help="JSON report path (not written during dry-run)",
    )
    parser.add_argument(
        "--min-win-rate",
        type=_win_rate,
        default=None,
        metavar="PERCENT",
        help="Fail unless completed games reach this win percentage (0..100); ties count as non-wins",
    )
    parser.add_argument(
        "--max-game-time",
        type=_positive_int,
        default=1800,
        metavar="SECONDS",
        help="Maximum in-game seconds per match (default: 1800; not a wall-clock timeout)",
    )
    parser.add_argument(
        "--seed",
        type=_seed,
        default=0,
        help="SC2 random seed for first match; incremented for subsequent matches",
    )
    parser.add_argument(
        "--replay-dir", type=Path, help="Optional directory for per-match SC2 replays"
    )
    return parser.parse_args(argv)


def _positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _win_rate(value):
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise argparse.ArgumentTypeError("must be a finite percentage from 0 to 100")
    return number


def _seed(value):
    number = int(value)
    if not 0 <= number < 2**32:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 4294967295")
    return number


def build_test_cases(args):
    selected_maps = [m.strip() for m in args.maps.split(",") if m.strip()]
    if not selected_maps:
        selected_maps = list(MAPS)

    selected_races = [RACE_BY_NAME[args.opponent]] if args.opponent else list(RACES)
    selected_difficulties = (
        [(DIFFICULTY_BY_NAME[args.difficulty], args.difficulty)]
        if args.difficulty
        else list(DIFFICULTIES)
    )

    if args.games is not None:
        test_cases = []
        games = max(0, args.games)
        for race in selected_races:
            for difficulty, diff_name in selected_difficulties:
                for index in range(games):
                    map_name = selected_maps[index % len(selected_maps)]
                    test_cases.append((map_name, race, difficulty, diff_name))
        return test_cases

    test_cases = []
    for map_name in selected_maps:
        for race in selected_races:
            for difficulty, diff_name in selected_difficulties:
                for _ in range(GAMES_PER_MATCHUP):
                    test_cases.append((map_name, race, difficulty, diff_name))
    return test_cases


def run_single_test(
    map_name,
    race,
    difficulty,
    diff_name,
    game_num,
    total,
    *,
    random_seed=0,
    game_time_limit=1800,
    replay_path=None,
):
    """Run a real match; retain failures and ties separately from defeats."""
    record = {
        "map": map_name,
        "race": race.name,
        "difficulty": diff_name,
        "random_seed": random_seed,
        "game_time_limit": game_time_limit,
        "replay_path": str(replay_path) if replay_path else None,
    }
    logger.info(
        "GAME %s/%s: %s vs %s %s", game_num, total, map_name, race.name, diff_name
    )
    start = time.monotonic()
    try:
        if any(
            item is None
            for item in (maps, run_game, Bot, Computer, WickedZergBotProImpl)
        ):
            raise RuntimeError(
                "SC2 runtime dependencies are unavailable; install bot requirements"
            )
        map_instance = maps.get(map_name)
        if map_instance is None:
            raise FileNotFoundError(f"Map {map_name!r} not found")
        bot = Bot(Race.Zerg, WickedZergBotProImpl(train_mode=False))
        if replay_path:
            Path(replay_path).parent.mkdir(parents=True, exist_ok=True)
        result = run_game(
            map_instance,
            [bot, Computer(race, difficulty)],
            realtime=False,
            random_seed=random_seed,
            game_time_limit=game_time_limit,
            save_replay_as=str(replay_path) if replay_path else None,
        )
        result_name = getattr(result, "name", None)
        outcomes = {"Victory": "WIN", "Defeat": "LOSS", "Tie": "TIE"}
        if result_name not in outcomes:
            raise RuntimeError(f"Game returned no completed outcome: {result!r}")
        record.update(result=outcomes[result_name], won=result_name == "Victory")
        logger.info("Result: %s", record["result"])
    except (Exception, SystemExit) as exc:
        # burnysc2's lazy path setup calls sys.exit when SC2 is absent. Keep
        # that external runtime failure in the report without swallowing Ctrl-C.
        error = (
            f"SC2 runtime exited with status {exc.code} (check SC2PATH and maps)"
            if isinstance(exc, SystemExit)
            else str(exc)
        )
        logger.error("Match failed: %s", error)
        record.update(result="error", error=error, won=False)
    record["time_seconds"] = round(time.monotonic() - start, 3)
    return record


def _source_metadata():
    """Identify the tested working tree without exposing remotes or environment values."""
    repo_root = Path(__file__).resolve().parent.parent
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        )
    except (OSError, subprocess.SubprocessError):
        commit, dirty = None, None
    packages = {}
    for name in ("burnysc2", "s2clientprotocol", "numpy"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {"source_commit": commit, "source_dirty": dirty, "packages": packages}


def _counts(results):
    counts = {"wins": 0, "losses": 0, "ties": 0, "errors": 0}
    names = {"WIN": "wins", "LOSS": "losses", "TIE": "ties", "error": "errors"}
    for result in results:
        counts[names.get(result.get("result"), "errors")] += 1
    completed = counts["wins"] + counts["losses"] + counts["ties"]
    return {
        **counts,
        "completed_games": completed,
        "win_rate": 100 * counts["wins"] / completed if completed else None,
    }


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.monotonic()
    test_cases = build_test_cases(args)
    total = len(test_cases)
    if not total:
        logger.error("No games selected; an empty run cannot validate the bot")
        return 2

    logger.info(
        "MASS TEST: %s games, CPU/GPU: %s", total, "GPU" if GPU_AVAILABLE else "CPU"
    )
    if args.dry_run:
        for index, (map_name, race, _difficulty, diff_name) in enumerate(test_cases, 1):
            logger.info(
                "DRY %02d/%02d: %s vs %s %s",
                index,
                total,
                map_name,
                race.name,
                diff_name,
            )
        logger.info(
            "Dry run complete; no SC2 games launched or win-rate evidence written"
        )
        return 0

    metadata = _source_metadata()
    results = []
    for index, (map_name, race, difficulty, diff_name) in enumerate(test_cases, 1):
        replay_path = None
        if args.replay_dir:
            replay_path = args.replay_dir / f"game_{index:04d}.SC2Replay"
        result = run_single_test(
            map_name,
            race,
            difficulty,
            diff_name,
            index,
            total,
            random_seed=(args.seed + index - 1) % (2**32),
            game_time_limit=args.max_game_time,
            replay_path=replay_path,
        )
        results.append(result)
        counts = _counts(results)
        logger.info(
            "Progress %s/%s: %sW %sL %sT %sE",
            index,
            total,
            counts["wins"],
            counts["losses"],
            counts["ties"],
            counts["errors"],
        )

    counts = _counts(results)
    valid = counts["errors"] == 0 and counts["completed_games"] == total
    gate_passed = valid and (
        args.min_win_rate is None or counts["win_rate"] >= args.min_win_rate
    )
    report = {
        "schema_version": 1,
        "timestamp": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "evidence": "real_game" if counts["completed_games"] else "unvalidated",
        "status": "passed" if gate_passed else "failed",
        "total_games": total,
        **counts,
        **metadata,
        "min_win_rate": args.min_win_rate,
        "gate_passed": gate_passed,
        "total_time_minutes": round((time.monotonic() - start_time) / 60, 3),
        "gpu": torch.cuda.get_device_name(0) if GPU_AVAILABLE else "CPU",
        "settings": {
            "opponent": args.opponent,
            "difficulty": args.difficulty,
            "maps": list(dict.fromkeys(case[0] for case in test_cases)),
            "games_per_matchup": args.games,
            "initial_random_seed": args.seed,
            "max_game_time_seconds": args.max_game_time,
            "train_mode": False,
        },
        "by_race": {
            name: _counts([result for result in results if result["race"] == name])
            for name in sorted({case[1].name for case in test_cases})
        },
        "by_difficulty": {
            name: _counts(
                [result for result in results if result["difficulty"] == name]
            )
            for name in sorted({case[3] for case in test_cases})
        },
        "games": results,
    }
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        logger.error("Cannot write benchmark report %s: %s", args.output, exc)
        return 2
    logger.info(
        "COMPLETE: %sW / %sL / %sT / %sE; completed %s/%s; win rate: %s",
        counts["wins"],
        counts["losses"],
        counts["ties"],
        counts["errors"],
        counts["completed_games"],
        total,
        (
            f"{counts['win_rate']:.1f}%"
            if counts["win_rate"] is not None
            else "unvalidated"
        ),
    )
    logger.info("Report: %s; gate: %s", args.output, "PASS" if gate_passed else "FAIL")
    if not valid:
        return 2
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
