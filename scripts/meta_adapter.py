# -*- coding: utf-8 -*-
"""Generate matchup adjustments from ladder analytics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class MetaAdapter:
    """Suggest strategy adjustments from recent ladder data."""

    def __init__(self, ladder_data_dir: str = "data/ladder"):
        self.data_dir = Path(ladder_data_dir)

    def generate_strategy_adjustments(self) -> Dict:
        analytics_path = self.data_dir / "analytics.json"
        if not analytics_path.exists():
            return {}

        data = json.loads(analytics_path.read_text(encoding="utf-8"))
        adjustments: Dict[str, Dict] = {}

        for race in ["Terran", "Protoss", "Zerg"]:
            key = f"vs_{race.lower()}"
            stats = data.get(key, {})
            if stats.get("total", 0) > 0 and stats.get("winrate", 100.0) < 50.0:
                adjustments[f"Zv{race[0]}"] = {
                    "winrate": stats.get("winrate", 0.0),
                    "action": self._suggest_adjustment(
                        race, data.get("weaknesses", {})
                    ),
                }

        overall = data.get("overall", {})
        if overall.get("crash_rate", 0.0) > 5.0:
            adjustments["stability"] = {
                "crash_rate": overall["crash_rate"],
                "action": "CRITICAL: crash rate above 5%; inspect exception handling",
                "reasons": data.get("weaknesses", {}).get("crash_reasons", []),
            }

        output_path = self.data_dir / "strategy_adjustments.json"
        output_path.write_text(
            json.dumps(adjustments, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return adjustments

    def _suggest_adjustment(self, race: str, weaknesses: Dict) -> str:
        suggestions = {
            "Terran": "Increase baneling/drop defense emphasis and review siege tank surrounds.",
            "Protoss": "Increase corruptor/viper readiness and strengthen DT/storm responses.",
            "Zerg": "Tighten early ling-bane control and pull roach transition earlier.",
        }
        return suggestions.get(
            race, "Review recent losses and generate a focused test set."
        )
