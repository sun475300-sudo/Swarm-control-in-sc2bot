# -*- coding: utf-8 -*-
"""Generate post-game analytics from telemetry JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class PostGameReport:
    """Analyze a telemetry file and emit actionable summary fields."""

    def generate(self, telemetry_path: str) -> Dict:
        data = json.loads(Path(telemetry_path).read_text(encoding="utf-8"))
        frames = data.get("frames", [])
        if not frames:
            return {"error": "No frame data"}

        report = {
            "summary": {
                "result": data.get("result", "Unknown"),
                "enemy_race": data.get("enemy_race", "Unknown"),
                "map": data.get("map_name", "Unknown"),
                "game_length_seconds": frames[-1].get("game_time", 0),
            },
            "economy": self._analyze_economy(frames),
            "military": self._analyze_military(frames),
            "performance": data.get("performance", {}),
            "events": data.get("events", []),
            "recommendations": [],
        }
        report["recommendations"] = self._generate_recommendations(report)
        return report

    def _analyze_economy(self, frames: List[Dict]) -> Dict:
        minerals = [frame.get("minerals", 0) for frame in frames]
        workers = [frame.get("worker_count", 0) for frame in frames]
        bases = [frame.get("base_count", 0) for frame in frames]
        return {
            "peak_minerals": max(minerals),
            "avg_minerals": sum(minerals) / len(minerals),
            "float_frames": sum(1 for value in minerals if value > 1000),
            "peak_workers": max(workers),
            "final_workers": workers[-1],
            "max_bases": max(bases),
            "first_expansion_time": next(
                (frame.get("game_time") for frame in frames if frame.get("base_count", 0) >= 2),
                None,
            ),
        }

    def _analyze_military(self, frames: List[Dict]) -> Dict:
        army = [frame.get("army_supply", 0) for frame in frames]
        return {
            "peak_army_supply": max(army),
            "avg_army_supply": sum(army) / len(army),
            "peak_army_value": max(frame.get("army_value", 0) for frame in frames),
        }

    def _generate_recommendations(self, report: Dict) -> List[str]:
        recs: List[str] = []
        economy = report.get("economy", {})
        if economy.get("float_frames", 0) > 20:
            recs.append("Reduce mineral float with macro hatch or army spending.")
        expansion_time = economy.get("first_expansion_time")
        if expansion_time and expansion_time > 180:
            recs.append(f"First expansion was late at {expansion_time:.0f}s.")
        if economy.get("peak_workers", 0) < 50:
            recs.append(f"Worker count low: peak {economy.get('peak_workers', 0)}.")
        performance = report.get("performance", {})
        if performance.get("frames_over_320ms", 0) > 0:
            recs.append(f"{performance['frames_over_320ms']} frames exceeded 320ms.")
        if report.get("summary", {}).get("result") not in {"Victory", "win", "Win"}:
            recs.append("Review loss events and scouting response timing.")
        return recs
