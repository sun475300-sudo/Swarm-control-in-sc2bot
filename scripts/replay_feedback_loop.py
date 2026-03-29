#!/usr/bin/env python3
"""Replay feedback loop utility.

Purpose:
- Discover latest SC2 replay files.
- Extract lightweight feedback (metadata + optional result stats).
- Persist rolling feedback artifacts for downstream training/monitoring.

Outputs:
- data/replay_feedback/latest_feedback.json
- data/replay_feedback/history.json
- data/replay_feedback/summary.md
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, cast


DEFAULT_REPLAY_DIRS = [
    Path.home() / "Documents" / "StarCraft II" / "Accounts",
    Path("replays"),
    Path("wicked_zerg_challenger") / "replays",
]


@dataclass
class ReplayFeedback:
    path: str
    file_name: str
    modified_at: str
    size_kb: float
    map_name: str | None
    game_length: str | None
    category: str | None
    players: list[dict[str, str]]
    player_count: int
    winner_names: list[str]
    priority_score: float
    notes: list[str]


def _calculate_priority_score(size_kb: float, player_count: int, winner_count: int, note_count: int) -> float:
    """Compute replay training priority using Rust when available, else Python fallback."""
    try:
        import swarm_rust_accel  # type: ignore

        return round(
            float(
                swarm_rust_accel.compute_feedback_priority(
                    size_kb,
                    player_count,
                    winner_count,
                    note_count,
                )
            ),
            3,
        )
    except Exception:
        score = 1.0
        score += min(size_kb / 1024.0, 1.5)
        score += min(player_count * 0.25, 1.0)
        score += min(winner_count * 0.3, 0.6)
        score -= min(note_count * 0.2, 0.8)
        return round(max(0.1, score), 3)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate replay feedback artifacts")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent replays to process")
    parser.add_argument(
        "--replay-dir",
        action="append",
        default=[],
        help="Additional replay directory (can be used multiple times)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path("data") / "replay_feedback"),
        help="Artifact output directory",
    )
    parser.add_argument(
        "--history-max",
        type=int,
        default=200,
        help="Max number of feedback records to keep in history",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Exit successfully even when no replay is found",
    )
    return parser.parse_args()


def build_replay_dirs(args: argparse.Namespace) -> list[Path]:
    dirs = list(DEFAULT_REPLAY_DIRS)

    env_dirs = os.getenv("SC2_REPLAY_DIRS", "").strip()
    if env_dirs:
        for raw in env_dirs.split(os.pathsep):
            raw = raw.strip()
            if raw:
                dirs.append(Path(raw))

    for user_dir in args.replay_dir:
        dirs.append(Path(user_dir))

    normalized: list[Path] = []
    seen: set[str] = set()
    for d in dirs:
        key = str(d.resolve()) if d.exists() else str(d)
        if key not in seen:
            seen.add(key)
            normalized.append(d)
    return normalized


def find_latest_replays(dirs: Iterable[Path], limit: int) -> list[Path]:
    found: list[tuple[Path, float]] = []
    max_files = 10000
    scanned = 0

    for base_dir in dirs:
        if not base_dir.exists():
            continue
        for root, _, files in os.walk(base_dir):
            for name in files:
                if not name.endswith(".SC2Replay"):
                    continue
                p = Path(root) / name
                try:
                    found.append((p, p.stat().st_mtime))
                except OSError:
                    continue
                scanned += 1
                if scanned >= max_files:
                    break
            if scanned >= max_files:
                break
        if scanned >= max_files:
            break

    found.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in found[:limit]]


def load_replay_feedback(path: Path) -> ReplayFeedback:
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    notes: list[str] = []
    map_name = None
    game_length = None
    category = None
    players: list[dict[str, str]] = []
    winners: list[str] = []

    try:
        import sc2reader  # type: ignore

        replay = cast(Any, sc2reader).load_replay(str(path))
        map_name = getattr(replay, "map_name", None)
        game_length = str(getattr(replay, "game_length", "")) or None
        category = getattr(replay, "category", None)

        for p in getattr(replay, "players", []):
            entry = {
                "name": str(getattr(p, "name", "Unknown")),
                "race": str(getattr(p, "play_race", "Unknown")),
                "result": str(getattr(p, "result", "Unknown")),
            }
            players.append(entry)
            if entry["result"].lower() in {"win", "victory"}:
                winners.append(entry["name"])
    except ImportError:
        notes.append("sc2reader not installed; metadata-only feedback generated")
    except Exception as exc:
        notes.append(f"sc2reader parse failed: {exc}")

    return ReplayFeedback(
        path=str(path),
        file_name=path.name,
        modified_at=modified_at,
        size_kb=round(stat.st_size / 1024.0, 2),
        map_name=map_name,
        game_length=game_length,
        category=category,
        players=players,
        player_count=len(players),
        winner_names=winners,
        priority_score=_calculate_priority_score(
            size_kb=round(stat.st_size / 1024.0, 2),
            player_count=len(players),
            winner_count=len(winners),
            note_count=len(notes),
        ),
        notes=notes,
    )


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_artifacts(output_dir: Path, feedbacks: list[ReplayFeedback], history_max: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    latest_payload: dict[str, Any] = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(feedbacks),
        "items": [asdict(f) for f in feedbacks],
    }
    latest_path = output_dir / "latest_feedback.json"
    latest_path.write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    history_path = output_dir / "history.json"
    raw_history = _read_json(history_path, default=[])
    history: list[dict[str, Any]]
    if isinstance(raw_history, list):
        raw_items = cast(list[Any], raw_history)
        history = [cast(dict[str, Any], h) for h in raw_items if isinstance(h, dict)]
    else:
        history = []

    for fb in feedbacks:
        history.append(
            {
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                **asdict(fb),
            }
        )

    history = history[-history_max:]
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = output_dir / "summary.md"
    summary_lines = [
        "# Replay Feedback Summary",
        "",
        f"- Generated at (UTC): {datetime.now(tz=timezone.utc).isoformat()}",
        f"- Processed replays: {len(feedbacks)}",
        f"- History size: {len(history)}",
        "",
    ]

    if feedbacks:
        summary_lines.append("## Latest Replays")
        summary_lines.append("")
        summary_lines.append("| File | Map | Length | Priority | Winners | Notes |")
        summary_lines.append("|---|---|---|---:|---|---|")
        for fb in feedbacks:
            winners = ", ".join(fb.winner_names) if fb.winner_names else "N/A"
            notes = "; ".join(fb.notes) if fb.notes else "-"
            summary_lines.append(
                f"| {fb.file_name} | {fb.map_name or 'Unknown'} | {fb.game_length or 'Unknown'} | {fb.priority_score:.3f} | {winners} | {notes} |"
            )

    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    replay_dirs = build_replay_dirs(args)
    recent = find_latest_replays(replay_dirs, args.limit)

    if not recent:
        print("[replay-feedback] No replay found.")
        for d in replay_dirs:
            print(f"  - searched: {d}")
        if args.allow_empty:
            return 0
        return 2

    feedbacks = [load_replay_feedback(path) for path in recent]
    output_dir = Path(args.output_dir)
    write_artifacts(output_dir, feedbacks, history_max=args.history_max)

    print(f"[replay-feedback] processed: {len(feedbacks)}")
    print(f"[replay-feedback] output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
