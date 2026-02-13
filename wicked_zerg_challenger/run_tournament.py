# -*- coding: utf-8 -*-
"""
Tournament Simulation - Phase 22 풀 토너먼트 시뮬레이션

모든 종족/난이도 조합 대상 성능 평가.
결과를 JSON + 텍스트 보고서로 저장.

Usage:
    python run_tournament.py                    # 기본 (12 games: 3 races x 2 difficulties x 2)
    python run_tournament.py --games 5          # 조합당 5게임 (총 30게임)
    python run_tournament.py --difficulty hard   # Hard 난이도만
    python run_tournament.py --race terran       # 테란만
    python run_tournament.py --quick             # 퀵 모드 (6게임)
"""

from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl as WickedZergBotPro
import sys
import os
import json
import time
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# SC2 path auto-setup
def _ensure_sc2_path():
    if sys.platform != "win32":
        return
    if "SC2PATH" in os.environ:
        sc2_path = os.environ["SC2PATH"]
        if os.path.exists(os.path.join(sc2_path, "Versions")):
            return
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Blizzard Entertainment\StarCraft II")
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        if os.path.exists(install_path):
            os.environ["SC2PATH"] = install_path
            return
    except Exception:
        pass
    for path in ["C:\\Program Files (x86)\\StarCraft II",
                  "C:\\Program Files\\StarCraft II", "D:\\StarCraft II"]:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return

_ensure_sc2_path()

# Map pool
TOURNAMENT_MAPS = [
    "AbyssalReefLE", "CactusValleyLE", "BelShirVestigeLE",
    "ProximaStationLE", "AcropolisLE", "DiscoBloodbathLE",
    "EphemeronLE", "TritonLE", "WintersGateLE",
    "ThunderbirdLE", "AutomatonLE", "KingsCoveLE",
]

# Difficulty presets
DIFFICULTY_MAP = {
    "easy": Difficulty.Easy,
    "medium": Difficulty.Medium,
    "hard": Difficulty.Hard,
    "harder": Difficulty.Harder,
    "veryhard": Difficulty.VeryHard,
    "cheatvision": Difficulty.CheatVision,
    "cheatmoney": Difficulty.CheatMoney,
    "cheatinsane": Difficulty.CheatInsane,
}

RACE_MAP = {
    "zerg": Race.Zerg,
    "terran": Race.Terran,
    "protoss": Race.Protoss,
}


class TournamentRunner:
    """풀 토너먼트 시뮬레이션 실행기"""

    def __init__(self, games_per_combo: int = 2,
                 difficulties: List[str] = None,
                 races: List[str] = None,
                 personality: str = "serral"):
        self.games_per_combo = games_per_combo
        self.personality = personality

        # Default: test against all races at Easy + Hard
        self.difficulties = difficulties or ["easy", "hard"]
        self.races = races or ["zerg", "terran", "protoss"]

        # Results storage
        self.results: List[Dict] = []
        self.start_time = None
        self.report_dir = Path("data/tournament")

    def run(self):
        """전체 토너먼트 실행"""
        self.start_time = datetime.now()
        total_combos = len(self.races) * len(self.difficulties)
        total_games = total_combos * self.games_per_combo

        print("\n" + "=" * 70)
        print("  TOURNAMENT SIMULATION - Phase 22")
        print("=" * 70)
        print(f"  Races: {', '.join(r.upper() for r in self.races)}")
        print(f"  Difficulties: {', '.join(d.upper() for d in self.difficulties)}")
        print(f"  Games per combo: {self.games_per_combo}")
        print(f"  Total games: {total_games}")
        print(f"  Personality: {self.personality}")
        print(f"  Started: {self.start_time.strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70 + "\n")

        game_number = 0

        for diff_name in self.difficulties:
            difficulty = DIFFICULTY_MAP.get(diff_name, Difficulty.Easy)
            for race_name in self.races:
                race = RACE_MAP.get(race_name, Race.Protoss)

                for game_i in range(self.games_per_combo):
                    game_number += 1
                    map_name = random.choice(TOURNAMENT_MAPS)

                    print(f"\n{'='*60}")
                    print(f"  GAME {game_number}/{total_games}")
                    print(f"  vs {race_name.upper()} ({diff_name.upper()}) on {map_name}")
                    wins_so_far = sum(1 for r in self.results if r["won"])
                    losses_so_far = len(self.results) - wins_so_far
                    print(f"  Record: {wins_so_far}W - {losses_so_far}L")
                    print(f"{'='*60}\n")

                    result = self._run_single_game(
                        game_number, map_name, race, race_name,
                        difficulty, diff_name
                    )
                    self.results.append(result)

                    # Cleanup between games
                    self._cleanup_sc2()
                    time.sleep(5)

        # Generate reports
        self._generate_report()
        self._save_json_results()

    def _run_single_game(self, game_number: int, map_name: str,
                         race: Race, race_name: str,
                         difficulty: Difficulty, diff_name: str) -> Dict:
        """단일 게임 실행"""
        result = {
            "game_number": game_number,
            "map": map_name,
            "opponent_race": race_name,
            "difficulty": diff_name,
            "won": False,
            "game_time": 0,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            bot_instance = WickedZergBotPro(
                train_mode=False,
                instance_id=game_number,
                personality=self.personality,
                game_count=game_number,
            )
            bot = Bot(Race.Zerg, bot_instance)

            map_instance = maps.get(map_name)
            if map_instance is None:
                # Try fallback map
                map_instance = maps.get("AbyssalReefLE")
                result["map"] = "AbyssalReefLE"

            start_time = time.time()
            game_result = run_game(
                map_instance,
                [bot, Computer(race, difficulty)],
                realtime=False,
            )
            elapsed = time.time() - start_time

            result["game_time"] = round(elapsed, 1)

            # Check result
            result_str = str(game_result).upper() if game_result else ""
            result["won"] = "VICTORY" in result_str or "WIN" in result_str
            result["result_raw"] = result_str

            # Try to get game report from bot
            if hasattr(bot_instance, '_game_quick_summary'):
                result["quick_summary"] = bot_instance._game_quick_summary
            if hasattr(bot_instance, '_training_result'):
                tr = bot_instance._training_result
                result["bot_game_time"] = tr.get("game_time", 0)

            status = "WIN" if result["won"] else "LOSS"
            print(f"\n[GAME {game_number}] {status} in {elapsed:.0f}s")

        except Exception as e:
            result["error"] = str(e)
            print(f"\n[GAME {game_number}] ERROR: {e}")

        return result

    def _cleanup_sc2(self):
        """SC2 프로세스 정리"""
        if sys.platform == "win32":
            try:
                os.system("taskkill /f /im SC2_x64.exe >nul 2>&1")
                os.system("taskkill /f /im SC2.exe >nul 2>&1")
            except Exception:
                pass

    def _generate_report(self):
        """텍스트 보고서 생성"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        lines = []
        lines.append("=" * 70)
        lines.append("  TOURNAMENT RESULTS - Phase 22")
        lines.append("=" * 70)
        lines.append(f"  Date: {self.start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%H:%M')}")
        lines.append(f"  Duration: {int(duration // 60)}m {int(duration % 60)}s")
        lines.append(f"  Personality: {self.personality}")
        lines.append("")

        # Overall stats
        total = len(self.results)
        wins = sum(1 for r in self.results if r["won"])
        losses = total - wins
        errors = sum(1 for r in self.results if r.get("error"))
        win_rate = (wins / total * 100) if total > 0 else 0

        lines.append(f"--- OVERALL ---")
        lines.append(f"  Total: {total} games")
        lines.append(f"  Wins: {wins} | Losses: {losses} | Errors: {errors}")
        lines.append(f"  Win Rate: {win_rate:.1f}%")
        lines.append("")

        # Per-race stats
        lines.append("--- BY RACE ---")
        for race_name in self.races:
            race_games = [r for r in self.results if r["opponent_race"] == race_name]
            race_wins = sum(1 for r in race_games if r["won"])
            race_total = len(race_games)
            rate = (race_wins / race_total * 100) if race_total > 0 else 0
            lines.append(f"  vs {race_name.upper():8s}: {race_wins}W-{race_total - race_wins}L ({rate:.0f}%)")
        lines.append("")

        # Per-difficulty stats
        lines.append("--- BY DIFFICULTY ---")
        for diff_name in self.difficulties:
            diff_games = [r for r in self.results if r["difficulty"] == diff_name]
            diff_wins = sum(1 for r in diff_games if r["won"])
            diff_total = len(diff_games)
            rate = (diff_wins / diff_total * 100) if diff_total > 0 else 0
            lines.append(f"  {diff_name.upper():12s}: {diff_wins}W-{diff_total - diff_wins}L ({rate:.0f}%)")
        lines.append("")

        # Per-combo stats
        lines.append("--- BY COMBO ---")
        for diff_name in self.difficulties:
            for race_name in self.races:
                combo_games = [r for r in self.results
                               if r["opponent_race"] == race_name and r["difficulty"] == diff_name]
                combo_wins = sum(1 for r in combo_games if r["won"])
                combo_total = len(combo_games)
                rate = (combo_wins / combo_total * 100) if combo_total > 0 else 0
                label = f"{diff_name.upper()} vs {race_name.upper()}"
                lines.append(f"  {label:25s}: {combo_wins}W-{combo_total - combo_wins}L ({rate:.0f}%)")
        lines.append("")

        # Game details
        lines.append("--- GAME LOG ---")
        for r in self.results:
            status = "WIN " if r["won"] else "LOSS"
            if r.get("error"):
                status = "ERR "
            time_str = f"{r['game_time']:.0f}s" if r['game_time'] > 0 else "N/A"
            lines.append(f"  #{r['game_number']:2d} {status} vs {r['opponent_race'].upper():8s} "
                         f"({r['difficulty'].upper():8s}) on {r['map']:20s} [{time_str}]")
        lines.append("")
        lines.append("=" * 70)

        report_text = "\n".join(lines)
        print("\n" + report_text)

        # Save to file
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            ts = self.start_time.strftime("%Y%m%d_%H%M%S")
            filepath = self.report_dir / f"tournament_{ts}.txt"
            filepath.write_text(report_text, encoding="utf-8")
            print(f"\n[REPORT] Saved to {filepath}")
        except Exception as e:
            print(f"[REPORT] Save failed: {e}")

    def _save_json_results(self):
        """JSON 결과 저장"""
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            ts = self.start_time.strftime("%Y%m%d_%H%M%S")
            filepath = self.report_dir / f"tournament_{ts}.json"

            total = len(self.results)
            wins = sum(1 for r in self.results if r["won"])

            data = {
                "tournament_date": self.start_time.isoformat(),
                "personality": self.personality,
                "total_games": total,
                "wins": wins,
                "losses": total - wins,
                "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
                "games": self.results,
            }

            filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[JSON] Saved to {filepath}")
        except Exception as e:
            print(f"[JSON] Save failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="SC2 Bot Tournament Simulation")
    parser.add_argument("--games", type=int, default=2,
                        help="Games per race/difficulty combo (default: 2)")
    parser.add_argument("--difficulty", type=str, default=None,
                        help="Specific difficulty (easy/medium/hard/harder/veryhard)")
    parser.add_argument("--race", type=str, default=None,
                        help="Specific race (zerg/terran/protoss)")
    parser.add_argument("--personality", type=str, default="serral",
                        help="Bot personality (default: serral)")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: 1 game per combo, easy+hard only")
    parser.add_argument("--full", action="store_true",
                        help="Full mode: 3 games per combo, easy/medium/hard/harder")
    args = parser.parse_args()

    # Configure
    games = args.games
    difficulties = None
    races = None

    if args.quick:
        games = 1
        difficulties = ["easy", "hard"]
    elif args.full:
        games = 3
        difficulties = ["easy", "medium", "hard", "harder"]

    if args.difficulty:
        difficulties = [args.difficulty.lower()]
    if args.race:
        races = [args.race.lower()]

    runner = TournamentRunner(
        games_per_combo=games,
        difficulties=difficulties,
        races=races,
        personality=args.personality,
    )
    runner.run()


if __name__ == "__main__":
    main()
