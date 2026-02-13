# -*- coding: utf-8 -*-
"""
Log Analyzer - Phase 22 로그 정밀 분석 도구

모든 게임 데이터를 종합하여 봇 성능 분석 및 개선 방향 도출.

Data Sources:
- local_training/data/race_stats.json  (종족별 승률)
- game_stats.json                      (맵/난이도/종족별 통계)
- data/games/*.json                    (GameDataLogger 상세 데이터)
- data/reports/*.txt                   (GameResultReporter 보고서)
- data/tournament/*.json               (토너먼트 결과)
- logs/bot.log                         (런타임 로그)

Usage:
    python log_analyzer.py              # 전체 분석
    python log_analyzer.py --focus race  # 종족별 분석만
    python log_analyzer.py --focus timing # 타이밍 분석만
"""

import json
import os
import glob
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import Counter, defaultdict


class LogAnalyzer:
    """통합 로그 분석 도구"""

    def __init__(self):
        self.base_dir = Path(".")
        self.race_stats = {}
        self.game_stats = {}
        self.game_data_files: List[Dict] = []
        self.tournament_results: List[Dict] = []
        self.bot_log_lines: List[str] = []

    def load_all_data(self):
        """모든 데이터 소스 로드"""
        print("[ANALYZER] Loading data sources...")

        # 1. Race stats
        race_path = self.base_dir / "local_training" / "data" / "race_stats.json"
        if race_path.exists():
            self.race_stats = json.loads(race_path.read_text(encoding="utf-8"))
            print(f"  race_stats.json: {sum(v.get('games', 0) for v in self.race_stats.values())} games")

        # 2. Game stats
        stats_path = self.base_dir / "game_stats.json"
        if stats_path.exists():
            self.game_stats = json.loads(stats_path.read_text(encoding="utf-8"))
            print(f"  game_stats.json: {self.game_stats.get('total_games', 0)} games")

        # 3. Game data files (from GameDataLogger)
        game_dir = self.base_dir / "data" / "games"
        if game_dir.exists():
            for filepath in sorted(game_dir.glob("*.json")):
                try:
                    data = json.loads(filepath.read_text(encoding="utf-8"))
                    data["_filename"] = filepath.name
                    self.game_data_files.append(data)
                except Exception:
                    pass
            print(f"  data/games/: {len(self.game_data_files)} game files")

        # 4. Tournament results
        tourney_dir = self.base_dir / "data" / "tournament"
        if tourney_dir.exists():
            for filepath in sorted(tourney_dir.glob("*.json")):
                try:
                    data = json.loads(filepath.read_text(encoding="utf-8"))
                    self.tournament_results.append(data)
                except Exception:
                    pass
            print(f"  data/tournament/: {len(self.tournament_results)} tournaments")

        # 5. Bot log (last 500 lines)
        log_path = self.base_dir / "logs" / "bot.log"
        if log_path.exists():
            try:
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                self.bot_log_lines = lines[-500:]
                print(f"  logs/bot.log: {len(lines)} lines (last 500 loaded)")
            except Exception:
                pass

        print("[ANALYZER] Data loading complete.\n")

    def analyze_all(self) -> str:
        """전체 분석 실행"""
        self.load_all_data()

        sections = []
        sections.append(self._header())
        sections.append(self._analyze_overall())
        sections.append(self._analyze_race_matchups())
        sections.append(self._analyze_maps())
        sections.append(self._analyze_timings())
        sections.append(self._analyze_economy())
        sections.append(self._analyze_combat_patterns())
        sections.append(self._analyze_defeat_patterns())
        sections.append(self._analyze_log_errors())
        sections.append(self._generate_recommendations())

        report = "\n".join(sections)

        # Save report
        self._save_report(report)

        return report

    def _header(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  LOG ANALYSIS REPORT - Phase 22")
        lines.append("=" * 70)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        total_games = sum(v.get("games", 0) for v in self.race_stats.values())
        lines.append(f"  Total Games Analyzed: {total_games}")
        lines.append(f"  Detailed Game Files: {len(self.game_data_files)}")
        lines.append(f"  Tournament Sessions: {len(self.tournament_results)}")
        lines.append("")
        return "\n".join(lines)

    def _analyze_overall(self) -> str:
        """전체 승률 분석"""
        lines = ["--- OVERALL PERFORMANCE ---"]

        total_games = sum(v.get("games", 0) for v in self.race_stats.values())
        total_wins = sum(v.get("wins", 0) for v in self.race_stats.values())

        if total_games == 0:
            lines.append("  No game data available")
            lines.append("")
            return "\n".join(lines)

        win_rate = total_wins / total_games * 100
        lines.append(f"  Total: {total_games} games, {total_wins}W-{total_games - total_wins}L")
        lines.append(f"  Overall Win Rate: {win_rate:.1f}%")

        # Rating
        if win_rate >= 80:
            lines.append("  Rating: EXCELLENT")
        elif win_rate >= 60:
            lines.append("  Rating: GOOD")
        elif win_rate >= 40:
            lines.append("  Rating: AVERAGE")
        elif win_rate >= 20:
            lines.append("  Rating: NEEDS IMPROVEMENT")
        else:
            lines.append("  Rating: CRITICAL - Major issues")

        lines.append("")
        return "\n".join(lines)

    def _analyze_race_matchups(self) -> str:
        """종족별 상세 분석"""
        lines = ["--- RACE MATCHUP ANALYSIS ---"]

        if not self.race_stats:
            lines.append("  No race data available")
            lines.append("")
            return "\n".join(lines)

        # Sort by win rate (worst first - needs most improvement)
        sorted_races = sorted(self.race_stats.items(),
                              key=lambda x: x[1].get("win_rate", 0))

        for race, stats in sorted_races:
            games = stats.get("games", 0)
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            win_rate = stats.get("win_rate", 0)

            indicator = "!!" if win_rate < 20 else ("!" if win_rate < 40 else " ")
            lines.append(f"  {indicator} vs {race:8s}: {wins}W-{losses}L ({win_rate:.1f}%) [{games} games]")

        # Identify weakest matchup
        weakest = sorted_races[0]
        lines.append(f"\n  WEAKEST MATCHUP: vs {weakest[0]} ({weakest[1].get('win_rate', 0):.1f}%)")

        # Specific recommendations per race
        for race, stats in sorted_races:
            wr = stats.get("win_rate", 0)
            if wr < 20:
                if race == "Zerg":
                    lines.append(f"  -> vs Zerg: Need better ZvZ opening (roach timing / baneling bust defense)")
                elif race == "Terran":
                    lines.append(f"  -> vs Terran: Need better anti-bio strategy (banelings vs marines)")
                elif race == "Protoss":
                    lines.append(f"  -> vs Protoss: Need better anti-gateway pressure (roach/ravager timing)")

        lines.append("")
        return "\n".join(lines)

    def _analyze_maps(self) -> str:
        """맵별 성능 분석"""
        lines = ["--- MAP PERFORMANCE ---"]

        by_map = self.game_stats.get("by_map", {})
        if not by_map:
            lines.append("  No map data available")
            lines.append("")
            return "\n".join(lines)

        for map_name, stats in sorted(by_map.items()):
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            total = wins + losses
            rate = (wins / total * 100) if total > 0 else 0
            lines.append(f"  {map_name:25s}: {wins}W-{losses}L ({rate:.0f}%)")

        lines.append("")
        return "\n".join(lines)

    def _analyze_timings(self) -> str:
        """타이밍 분석 (게임 데이터 기반)"""
        lines = ["--- TIMING ANALYSIS ---"]

        if not self.game_data_files:
            lines.append("  No detailed game data available")
            lines.append("")
            return "\n".join(lines)

        expansion_times = []
        pool_times = []
        game_durations = []

        for gd in self.game_data_files:
            # Expansion timings
            expansions = gd.get("expansions", [])
            if expansions:
                first_exp = expansions[0].get("time", 0)
                if first_exp > 0:
                    expansion_times.append(first_exp)

            # Game duration
            result = gd.get("game_result", {})
            duration = result.get("duration", 0)
            if duration > 0:
                game_durations.append(duration)

            # Pool timing (from build order)
            for bo in gd.get("build_order", []):
                if "SPAWNINGPOOL" in str(bo.get("unit_type", "")):
                    pool_times.append(bo.get("time", 0))
                    break

        if expansion_times:
            avg_exp = sum(expansion_times) / len(expansion_times)
            min_exp = min(expansion_times)
            max_exp = max(expansion_times)
            lines.append(f"  Natural Expansion:")
            lines.append(f"    Average: {avg_exp:.0f}s (target: 60s)")
            lines.append(f"    Best: {min_exp:.0f}s | Worst: {max_exp:.0f}s")
            if avg_exp > 90:
                lines.append(f"    !! LATE - Average {avg_exp - 60:.0f}s behind target")
            elif avg_exp > 70:
                lines.append(f"    ! Slightly late - aim for sub-60s")
            else:
                lines.append(f"    OK - On target")

        if pool_times:
            avg_pool = sum(pool_times) / len(pool_times)
            lines.append(f"\n  Spawning Pool:")
            lines.append(f"    Average: {avg_pool:.0f}s")

        if game_durations:
            avg_dur = sum(game_durations) / len(game_durations)
            short_games = sum(1 for d in game_durations if d < 180)
            long_games = sum(1 for d in game_durations if d > 600)
            lines.append(f"\n  Game Duration:")
            lines.append(f"    Average: {avg_dur / 60:.1f} minutes")
            lines.append(f"    Quick losses (<3min): {short_games}")
            lines.append(f"    Long games (>10min): {long_games}")

        lines.append("")
        return "\n".join(lines)

    def _analyze_economy(self) -> str:
        """경제 분석"""
        lines = ["--- ECONOMY ANALYSIS ---"]

        if not self.game_data_files:
            lines.append("  No detailed game data available")
            lines.append("")
            return "\n".join(lines)

        high_mineral_games = 0
        peak_workers_list = []

        for gd in self.game_data_files:
            snapshots = gd.get("resource_snapshots", [])
            if not snapshots:
                continue

            # Check for mineral floating
            has_high_minerals = any(s.get("minerals", 0) > 1000 for s in snapshots)
            if has_high_minerals:
                high_mineral_games += 1

            # Peak workers
            max_workers = max((s.get("workers", 0) for s in snapshots), default=0)
            if max_workers > 0:
                peak_workers_list.append(max_workers)

        total = len(self.game_data_files)
        if total > 0:
            lines.append(f"  Mineral Banking (>1000): {high_mineral_games}/{total} games ({high_mineral_games/total*100:.0f}%)")
            if high_mineral_games / total > 0.5:
                lines.append("    !! SPENDING ISSUE - Over half of games have mineral banking")

        if peak_workers_list:
            avg_peak = sum(peak_workers_list) / len(peak_workers_list)
            lines.append(f"  Peak Workers (avg): {avg_peak:.0f}")
            if avg_peak < 50:
                lines.append("    !! LOW WORKER COUNT - Target 66+ for 3-base economy")

        lines.append("")
        return "\n".join(lines)

    def _analyze_combat_patterns(self) -> str:
        """전투 패턴 분석"""
        lines = ["--- COMBAT PATTERNS ---"]

        if not self.game_data_files:
            lines.append("  No detailed game data available")
            lines.append("")
            return "\n".join(lines)

        total_engagements = 0
        total_supply_lost = 0
        big_losses = 0

        for gd in self.game_data_files:
            engagements = gd.get("engagements", [])
            total_engagements += len(engagements)
            for eng in engagements:
                lost = eng.get("supply_lost", 0)
                total_supply_lost += lost
                if lost > 30:
                    big_losses += 1

        if total_engagements > 0:
            avg_loss = total_supply_lost / total_engagements
            lines.append(f"  Total Engagements: {total_engagements}")
            lines.append(f"  Total Supply Lost: {total_supply_lost}")
            lines.append(f"  Average Loss per Fight: {avg_loss:.1f} supply")
            lines.append(f"  Big Losses (>30 supply): {big_losses}")
            if big_losses > total_engagements * 0.3:
                lines.append("    !! TOO MANY BIG LOSSES - Improve engagement decisions")

        # Unit composition from production logs
        unit_counts = Counter()
        for gd in self.game_data_files:
            for prod in gd.get("unit_production", []):
                unit_type = prod.get("unit_type", "Unknown")
                unit_counts[unit_type] += 1

        if unit_counts:
            lines.append(f"\n  Most Produced Units:")
            for unit, count in unit_counts.most_common(5):
                lines.append(f"    {unit}: {count}")

        lines.append("")
        return "\n".join(lines)

    def _analyze_defeat_patterns(self) -> str:
        """패배 패턴 분석"""
        lines = ["--- DEFEAT PATTERN ANALYSIS ---"]

        defeat_timings = []
        defeat_reasons = Counter()

        for gd in self.game_data_files:
            result = gd.get("game_result", {})
            result_str = result.get("result", "").upper()

            if "DEFEAT" in result_str or "LOSS" in result_str:
                duration = result.get("duration", 0)
                defeat_timings.append(duration)

                # Classify defeat
                if duration < 180:
                    defeat_reasons["Early Rush Loss (<3min)"] += 1
                elif duration < 360:
                    defeat_reasons["Early-Mid Loss (3-6min)"] += 1
                elif duration < 600:
                    defeat_reasons["Mid Game Loss (6-10min)"] += 1
                else:
                    defeat_reasons["Late Game Loss (10min+)"] += 1

        if defeat_timings:
            avg_defeat = sum(defeat_timings) / len(defeat_timings)
            lines.append(f"  Defeats Analyzed: {len(defeat_timings)}")
            lines.append(f"  Average Defeat Time: {avg_defeat / 60:.1f} minutes")

            lines.append(f"\n  Defeat Timing Distribution:")
            for reason, count in defeat_reasons.most_common():
                lines.append(f"    {reason}: {count}")

            # Key insight
            most_common = defeat_reasons.most_common(1)
            if most_common:
                pattern, count = most_common[0]
                lines.append(f"\n  PRIMARY WEAKNESS: {pattern} ({count} occurrences)")
                if "Early Rush" in pattern:
                    lines.append("    -> Focus on: Early defense (spine crawlers, queens, zergling production)")
                elif "Early-Mid" in pattern:
                    lines.append("    -> Focus on: Macro efficiency, timely expansion, roach timing")
                elif "Mid Game" in pattern:
                    lines.append("    -> Focus on: Army composition, tech transitions, engagement timing")
                elif "Late Game" in pattern:
                    lines.append("    -> Focus on: Upgrades, Hive tech, endgame composition")
        else:
            lines.append("  No defeat data available")

        lines.append("")
        return "\n".join(lines)

    def _analyze_log_errors(self) -> str:
        """런타임 에러 분석"""
        lines = ["--- RUNTIME ERROR ANALYSIS ---"]

        if not self.bot_log_lines:
            lines.append("  No bot.log data available")
            lines.append("")
            return "\n".join(lines)

        error_counts = Counter()
        warning_counts = Counter()

        for line in self.bot_log_lines:
            if "ERROR" in line:
                # Extract error category
                parts = line.split(" - ")
                if len(parts) >= 3:
                    error_counts[parts[1].strip()] += 1
                else:
                    error_counts["Unknown"] += 1
            elif "WARNING" in line:
                parts = line.split(" - ")
                if len(parts) >= 3:
                    warning_counts[parts[1].strip()] += 1

        if error_counts:
            lines.append(f"  Errors ({sum(error_counts.values())} total):")
            for source, count in error_counts.most_common(5):
                lines.append(f"    {source}: {count}")
        else:
            lines.append("  No errors detected")

        if warning_counts:
            lines.append(f"\n  Warnings ({sum(warning_counts.values())} total):")
            for source, count in warning_counts.most_common(5):
                lines.append(f"    {source}: {count}")

        lines.append("")
        return "\n".join(lines)

    def _generate_recommendations(self) -> str:
        """종합 개선 권고"""
        lines = ["--- IMPROVEMENT RECOMMENDATIONS ---"]

        total_games = sum(v.get("games", 0) for v in self.race_stats.values())
        total_wins = sum(v.get("wins", 0) for v in self.race_stats.values())
        overall_wr = (total_wins / total_games * 100) if total_games > 0 else 0

        priority = 1

        # 1. Weakest matchup
        if self.race_stats:
            weakest_race = min(self.race_stats.items(),
                               key=lambda x: x[1].get("win_rate", 100))
            if weakest_race[1].get("win_rate", 100) < 20:
                lines.append(f"  {priority}. [CRITICAL] vs {weakest_race[0]} win rate is "
                             f"{weakest_race[1]['win_rate']:.0f}% - needs dedicated practice")
                priority += 1

        # 2. Overall rate
        if overall_wr < 30:
            lines.append(f"  {priority}. [HIGH] Overall win rate {overall_wr:.0f}% - "
                         "focus on fundamentals (macro, spending, expansion timing)")
            priority += 1

        # 3. Game data insights
        if self.game_data_files:
            # Expansion timing
            exp_times = []
            for gd in self.game_data_files:
                exps = gd.get("expansions", [])
                if exps:
                    exp_times.append(exps[0].get("time", 999))
            if exp_times and sum(exp_times) / len(exp_times) > 90:
                lines.append(f"  {priority}. [HIGH] Natural expansion averaging "
                             f"{sum(exp_times)/len(exp_times):.0f}s - use Hatch First build (target: 60s)")
                priority += 1

            # Mineral banking
            banking = sum(1 for gd in self.game_data_files
                          if any(s.get("minerals", 0) > 1000
                                 for s in gd.get("resource_snapshots", [])))
            if banking > len(self.game_data_files) * 0.5:
                lines.append(f"  {priority}. [MEDIUM] Mineral banking detected in "
                             f"{banking}/{len(self.game_data_files)} games - add more production")
                priority += 1

        # 4. General recommendations
        if total_games < 50:
            lines.append(f"  {priority}. [INFO] Only {total_games} games recorded - "
                         "need more data for accurate analysis (target: 100+ games)")
            priority += 1

        if priority == 1:
            lines.append("  No critical issues detected. Keep training!")

        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)

    def _save_report(self, report: str):
        """분석 보고서 저장"""
        try:
            report_dir = self.base_dir / "data" / "analysis"
            report_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = report_dir / f"analysis_{ts}.txt"
            filepath.write_text(report, encoding="utf-8")
            print(f"\n[ANALYZER] Report saved to {filepath}")
        except Exception as e:
            print(f"[ANALYZER] Save failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="SC2 Bot Log Analyzer")
    parser.add_argument("--focus", type=str, default=None,
                        choices=["race", "timing", "combat", "economy", "errors"],
                        help="Focus on specific analysis area")
    args = parser.parse_args()

    analyzer = LogAnalyzer()

    if args.focus:
        analyzer.load_all_data()
        sections = {
            "race": analyzer._analyze_race_matchups,
            "timing": analyzer._analyze_timings,
            "combat": analyzer._analyze_combat_patterns,
            "economy": analyzer._analyze_economy,
            "errors": analyzer._analyze_log_errors,
        }
        result = sections[args.focus]()
        print(result)
    else:
        report = analyzer.analyze_all()
        print(report)


if __name__ == "__main__":
    main()
