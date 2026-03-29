#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replay feedback loop for Phase 52.

Reads replay summary JSON files and creates a prioritized training focus report.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def _extract_focus_tags(item: dict[str, Any]) -> list[str]:
    tags: list[str] = []

    # Expected optional keys from replay summary pipelines
    race = str(item.get("enemy_race", "unknown")).lower()
    if race in {"terran", "protoss", "zerg"}:
        tags.append(f"matchup_{race}")

    if item.get("early_rush"):
        tags.append("early_defense")
    if item.get("supply_block"):
        tags.append("macro_supply")
    if item.get("float_minerals", 0) and float(item.get("float_minerals", 0)) > 1200:
        tags.append("resource_spend")
    if item.get("lost_to_air"):
        tags.append("anti_air_response")
    if item.get("lost_to_drop"):
        tags.append("drop_defense")
    if item.get("creep_coverage", 100) and float(item.get("creep_coverage", 100)) < 35:
        tags.append("creep_spread")

    return tags


def build_feedback(input_dir: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("*.json"))
    total = 0
    wins = 0
    losses = 0
    counter: Counter[str] = Counter()

    for fp in files:
        item = _safe_load_json(fp)
        if not item:
            continue

        total += 1
        result = str(item.get("result", "")).lower()
        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1
            for tag in _extract_focus_tags(item):
                counter[tag] += 1

    win_rate = (wins / total) if total else 0.0
    top_focus = [
        {"tag": tag, "count": count, "priority": rank + 1}
        for rank, (tag, count) in enumerate(counter.most_common(5))
    ]

    next_actions = []
    for item in top_focus:
        tag = item["tag"]
        if tag == "early_defense":
            next_actions.append("Relax early defense thresholds and retrain from pre-5min combat replays.")
        elif tag == "macro_supply":
            next_actions.append("Improve overlord timing in supply-block segments and add macro cycle alerts.")
        elif tag == "resource_spend":
            next_actions.append("Increase production priority during mineral and gas float windows.")
        elif tag == "anti_air_response":
            next_actions.append("Trigger hydra/queen transition earlier when air threats are detected.")
        elif tag == "drop_defense":
            next_actions.append("Increase drop-defense response units and reduce return-to-defense delay.")
        elif tag == "creep_spread":
            next_actions.append("Raise queen energy allocation and creep-tumor target scoring weights.")

    return {
        "total_replays": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "focus_areas": top_focus,
        "next_actions": next_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay feedback loop")
    parser.add_argument("--input", required=True, help="Input directory of replay summary JSON files")
    parser.add_argument("--output", required=True, help="Output feedback JSON path")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}")
        return 1

    report = build_feedback(input_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Replay feedback generated")
    print(f"Input: {input_dir}")
    print(f"Output: {output_path}")
    print(f"Win rate: {report['win_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
