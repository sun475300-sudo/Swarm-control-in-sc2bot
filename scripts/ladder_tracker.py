# -*- coding: utf-8 -*-
"""Track ladder match outcomes and generate simple analytics."""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class LadderMatch:
    opponent: str
    opponent_race: str
    map_name: str
    result: str
    date: str
    our_elo_after: float = 1000.0
    crash_reason: str = ""


class LadderTracker:
    """Persist match history and expose winrate/weakness summaries."""

    def __init__(self, data_dir: str = "data/ladder"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.matches: List[LadderMatch] = []
        self._load()

    def record_match(
        self,
        opponent: str,
        opponent_race: str,
        map_name: str,
        result: str,
        our_elo_after: float = 1000.0,
        crash_reason: str = "",
    ) -> LadderMatch:
        match = LadderMatch(
            opponent=opponent,
            opponent_race=opponent_race,
            map_name=map_name,
            result=result.lower(),
            date=_dt.datetime.now().isoformat(),
            our_elo_after=float(our_elo_after),
            crash_reason=crash_reason,
        )
        self.matches.append(match)
        self._save()
        self._update_analytics()
        return match

    def get_winrate(self, vs_race: Optional[str] = None, last_n: Optional[int] = None) -> Dict:
        matches = self.matches
        if vs_race:
            matches = [m for m in matches if m.opponent_race.lower() == vs_race.lower()]
        if last_n:
            matches = matches[-last_n:]
        if not matches:
            return {"total": 0, "wins": 0, "losses": 0, "crashes": 0, "winrate": 0.0, "crash_rate": 0.0}

        wins = sum(1 for m in matches if m.result == "win")
        losses = sum(1 for m in matches if m.result == "loss")
        crashes = sum(1 for m in matches if m.result == "crash")
        total = len(matches)
        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "crashes": crashes,
            "winrate": wins / total * 100.0,
            "crash_rate": crashes / total * 100.0,
        }

    def get_weakness_report(self) -> Dict:
        losses = [m for m in self.matches if m.result in {"loss", "crash"}]
        race_losses: Dict[str, int] = {}
        map_losses: Dict[str, int] = {}
        opponent_losses: Dict[str, int] = {}
        for match in losses:
            race_losses[match.opponent_race] = race_losses.get(match.opponent_race, 0) + 1
            map_losses[match.map_name] = map_losses.get(match.map_name, 0) + 1
            opponent_losses[match.opponent] = opponent_losses.get(match.opponent, 0) + 1
        return {
            "worst_matchup": max(race_losses, key=race_losses.get) if race_losses else None,
            "worst_map": max(map_losses, key=map_losses.get) if map_losses else None,
            "hardest_opponent": max(opponent_losses, key=opponent_losses.get) if opponent_losses else None,
            "race_breakdown": race_losses,
            "crash_reasons": [m.crash_reason for m in losses if m.crash_reason],
        }

    def get_elo_history(self) -> List[Dict]:
        return [{"date": m.date, "elo": m.our_elo_after, "opponent": m.opponent} for m in self.matches]

    def _update_analytics(self) -> None:
        report = {
            "last_updated": _dt.datetime.now().isoformat(),
            "total_matches": len(self.matches),
            "overall": self.get_winrate(),
            "last_20": self.get_winrate(last_n=20),
            "vs_terran": self.get_winrate(vs_race="Terran"),
            "vs_protoss": self.get_winrate(vs_race="Protoss"),
            "vs_zerg": self.get_winrate(vs_race="Zerg"),
            "weaknesses": self.get_weakness_report(),
            "elo_history": self.get_elo_history()[-50:],
        }
        (self.data_dir / "analytics.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _save(self) -> None:
        (self.data_dir / "matches.json").write_text(
            json.dumps([asdict(m) for m in self.matches], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load(self) -> None:
        path = self.data_dir / "matches.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.matches = [LadderMatch(**item) for item in data]
        except (json.JSONDecodeError, TypeError):
            self.matches = []
