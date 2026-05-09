# -*- coding: utf-8 -*-
"""Static dashboard generation from telemetry files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("Dashboard")


class DashboardServer:
    """Read telemetry files and generate a compact HTML dashboard."""

    def __init__(self, telemetry_dir: str = "data/telemetry", port: int = 8765, data_dir: str = None):
        self.telemetry_dir = Path(data_dir or telemetry_dir)
        self.telemetry_dir.mkdir(parents=True, exist_ok=True)
        self.port = int(port)

    def get_recent_games(self, limit: int = 20) -> List[Dict]:
        files = sorted(
            [path for path in self.telemetry_dir.glob("*.json") if path.name != "analytics.json"],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        games: List[Dict] = []
        for path in files[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            games.append(
                {
                    "game_id": data.get("game_id", path.stem),
                    "result": data.get("result", "Unknown"),
                    "enemy_race": data.get("enemy_race", "Unknown"),
                    "map": data.get("map_name", "Unknown"),
                    "date": data.get("start_time", ""),
                    "performance": data.get("performance", {}),
                }
            )
        return games

    def get_winrate_summary(self) -> Dict:
        games = self.get_recent_games(limit=100)
        if not games:
            return {"overall": {"total": 0, "wins": 0, "winrate": 0.0}, "by_race": {}}

        total = len(games)
        wins = sum(1 for game in games if game["result"] in {"Victory", "win", "Win"})
        by_race: Dict[str, Dict] = {}
        for race in ["Terran", "Protoss", "Zerg"]:
            race_games = [game for game in games if game["enemy_race"] == race]
            race_wins = sum(1 for game in race_games if game["result"] in {"Victory", "win", "Win"})
            by_race[race] = {
                "total": len(race_games),
                "wins": race_wins,
                "winrate": race_wins / len(race_games) * 100.0 if race_games else 0.0,
            }
        return {
            "overall": {"total": total, "wins": wins, "winrate": wins / total * 100.0},
            "by_race": by_race,
        }

    def generate_dashboard_html(self) -> str:
        summary = self.get_winrate_summary()
        recent = self.get_recent_games(10)
        overall = summary.get("overall", {})
        rows = []
        for game in recent:
            css = "win" if game["result"] in {"Victory", "win", "Win"} else "loss"
            rows.append(
                f'<tr><td class="{css}">{game["result"]}</td>'
                f"<td>{game['enemy_race']}</td><td>{game['map']}</td><td>{game['date']}</td></tr>"
            )
        rows_html = "\n".join(rows)
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>WickedZergBotPro Dashboard</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #111; color: #eee; }}
h1 {{ color: #6f6; }}
.card {{ background: #222; border-radius: 8px; padding: 16px; margin: 12px 0; }}
.win {{ color: #6f6; }} .loss {{ color: #f66; }}
table {{ width: 100%; border-collapse: collapse; }}
td, th {{ padding: 8px; text-align: left; border-bottom: 1px solid #333; }}
</style></head><body>
<h1>WickedZergBotPro Dashboard</h1>
<div class="card"><h2>Overall: {overall.get('winrate', 0.0):.1f}% ({overall.get('wins', 0)}/{overall.get('total', 0)})</h2></div>
<div class="card"><h3>Recent Games</h3>
<table><tr><th>Result</th><th>vs</th><th>Map</th><th>Date</th></tr>
{rows_html}
</table></div></body></html>"""

    def generate_report(self) -> str:
        return self.generate_dashboard_html()

    def save_dashboard(self) -> Path:
        output = self.telemetry_dir / "dashboard.html"
        output.write_text(self.generate_dashboard_html(), encoding="utf-8")
        logger.info("[DASHBOARD] Saved to %s", output)
        return output


def run_dashboard() -> None:
    DashboardServer().save_dashboard()


def main() -> None:
    run_dashboard()


if __name__ == "__main__":
    main()
