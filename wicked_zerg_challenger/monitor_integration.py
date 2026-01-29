# -*- coding: utf-8 -*-
"""
Phase 15 Integration Monitor

Real-time monitoring tool for OpponentModeling and AdvancedMicroControllerV3 systems.
Monitors log files and JSON data to track system performance.

Usage:
    python monitor_integration.py
    python monitor_integration.py --watch
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class IntegrationMonitor:
    """Monitor for Phase 15 integrated systems"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data" / "opponent_models"
        self.log_file = self.base_dir / "logs" / "bot.log"
        self.last_check_time = datetime.now()

    def check_opponent_models(self) -> Dict:
        """Check opponent modeling data"""
        print("\n" + "=" * 70)
        print("OPPONENT MODELING STATUS")
        print("=" * 70)

        if not self.data_dir.exists():
            print("[\!]  Data directory not found. No games played yet.")
            return {"status": "no_data"}

        # Find all opponent model files
        json_files = list(self.data_dir.glob("*.json"))

        if not json_files:
            print("[i]  No opponent models found. Play some games to build the database.")
            return {"status": "no_models"}

        print(f"\n[STATS] Found {len(json_files)} opponent model(s):\n")

        total_games = 0
        total_wins = 0
        models_data = []

        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                opponent_id = data.get("opponent_id", json_file.stem)
                games_played = data.get("games_played", 0)
                games_won = data.get("games_won", 0)
                games_lost = data.get("games_lost", 0)
                win_rate = (games_won / games_played * 100) if games_played > 0 else 0

                total_games += games_played
                total_wins += games_won

                print(f"  [TARGET] {opponent_id}")
                print(f"     Games: {games_played} | Wins: {games_won} | Losses: {games_lost} | Win Rate: {win_rate:.1f}%")

                # Most common strategies
                strategy_freq = data.get("strategy_frequency", {})
                if strategy_freq:
                    sorted_strategies = sorted(strategy_freq.items(), key=lambda x: x[1], reverse=True)[:3]
                    print(f"     Top Strategies: {', '.join([f'{s}({c})' for s, c in sorted_strategies])}")

                # Style classification
                style_counts = data.get("style_counts", {})
                if style_counts:
                    most_common_style = max(style_counts.items(), key=lambda x: x[1])
                    print(f"     Play Style: {most_common_style[0]} ({most_common_style[1]} games)")

                models_data.append({
                    "opponent_id": opponent_id,
                    "games_played": games_played,
                    "games_won": games_won,
                    "win_rate": win_rate
                })

                print()

            except Exception as e:
                print(f"  [X] Error reading {json_file.name}: {e}\n")

        # Summary
        overall_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        print(f"[GRAPH] OVERALL STATISTICS:")
        print(f"   Total Games: {total_games}")
        print(f"   Total Wins: {total_wins}")
        print(f"   Overall Win Rate: {overall_win_rate:.1f}%")

        return {
            "status": "active",
            "total_models": len(json_files),
            "total_games": total_games,
            "total_wins": total_wins,
            "overall_win_rate": overall_win_rate,
            "models": models_data
        }

    def check_micro_v3_status(self) -> Dict:
        """Check micro controller V3 status from logs"""
        print("\n" + "=" * 70)
        print("ADVANCED MICRO CONTROLLER V3 STATUS")
        print("=" * 70)

        if not self.log_file.exists():
            print("\n[\!]  Log file not found. System may not have run yet.")
            return {"status": "no_logs"}

        # Read recent log entries
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Look for micro V3 log entries
            micro_v3_logs = [line for line in lines[-1000:] if "MICRO_V3" in line]

            if not micro_v3_logs:
                print("\n[i]  No Micro V3 logs found. System may not be active yet.")
                return {"status": "no_activity"}

            print(f"\n[STATS] Found {len(micro_v3_logs)} Micro V3 log entries:\n")

            # Parse latest status
            latest_log = micro_v3_logs[-1] if micro_v3_logs else None
            if latest_log:
                print(f"  [GAME] Latest Status:")
                print(f"     {latest_log.strip()}")

            # Count ability usage
            ravager_count = sum(1 for line in micro_v3_logs if "Ravagers:" in line)
            lurker_count = sum(1 for line in micro_v3_logs if "Lurkers burrowed:" in line)
            focus_fire_count = sum(1 for line in micro_v3_logs if "Focus fire:" in line)

            print(f"\n  [GRAPH] Activity Summary:")
            print(f"     Ravager micro executions: {ravager_count}")
            print(f"     Lurker micro executions: {lurker_count}")
            print(f"     Focus fire executions: {focus_fire_count}")

            return {
                "status": "active",
                "log_entries": len(micro_v3_logs),
                "ravager_executions": ravager_count,
                "lurker_executions": lurker_count,
                "focus_fire_executions": focus_fire_count
            }

        except Exception as e:
            print(f"\n[X] Error reading log file: {e}")
            return {"status": "error", "error": str(e)}

    def check_errors(self) -> Dict:
        """Check for error messages in logs"""
        print("\n" + "=" * 70)
        print("ERROR CHECK")
        print("=" * 70)

        if not self.log_file.exists():
            print("\n[\!]  Log file not found.")
            return {"status": "no_logs"}

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Look for errors
            error_patterns = ["OpponentModeling error", "MicroV3 error", "[ERROR]"]
            errors = []

            for line in lines[-1000:]:  # Last 1000 lines
                for pattern in error_patterns:
                    if pattern in line:
                        errors.append(line.strip())
                        break

            if not errors:
                print("\n[OK] No errors found in recent logs!")
                return {"status": "no_errors", "error_count": 0}

            print(f"\n[\!]  Found {len(errors)} error(s) in recent logs:\n")

            # Group by error type
            om_errors = [e for e in errors if "OpponentModeling" in e]
            micro_errors = [e for e in errors if "MicroV3" in e or "Micro" in e]
            other_errors = [e for e in errors if e not in om_errors and e not in micro_errors]

            if om_errors:
                print(f"  [RED] OpponentModeling errors: {len(om_errors)}")
                for err in om_errors[-3:]:  # Last 3
                    print(f"     {err}")

            if micro_errors:
                print(f"\n  [RED] MicroV3 errors: {len(micro_errors)}")
                for err in micro_errors[-3:]:  # Last 3
                    print(f"     {err}")

            if other_errors:
                print(f"\n  [RED] Other errors: {len(other_errors)}")
                for err in other_errors[-3:]:  # Last 3
                    print(f"     {err}")

            return {
                "status": "errors_found",
                "error_count": len(errors),
                "om_errors": len(om_errors),
                "micro_errors": len(micro_errors),
                "other_errors": len(other_errors)
            }

        except Exception as e:
            print(f"\n[X] Error reading log file: {e}")
            return {"status": "error", "error": str(e)}

    def check_performance(self) -> Dict:
        """Check performance metrics"""
        print("\n" + "=" * 70)
        print("PERFORMANCE CHECK")
        print("=" * 70)

        if not self.log_file.exists():
            print("\n[\!]  Log file not found.")
            return {"status": "no_logs"}

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Look for timing information
            timing_logs = [line for line in lines[-1000:] if "ms" in line.lower() or "elapsed" in line.lower()]

            if not timing_logs:
                print("\n[i]  No performance data found in logs.")
                return {"status": "no_data"}

            print(f"\n[STATS] Found {len(timing_logs)} timing entries\n")

            # Look for specific system timings
            om_timings = [line for line in timing_logs if "OpponentModeling" in line]
            micro_timings = [line for line in timing_logs if "MicroV3" in line or "Micro" in line]

            if om_timings:
                print(f"  [TIMER]  OpponentModeling timing entries: {len(om_timings)}")
                if om_timings:
                    print(f"     Latest: {om_timings[-1].strip()}")

            if micro_timings:
                print(f"\n  [TIMER]  MicroV3 timing entries: {len(micro_timings)}")
                if micro_timings:
                    print(f"     Latest: {micro_timings[-1].strip()}")

            # Check for frame rate issues
            lag_indicators = [line for line in lines[-1000:] if "lag" in line.lower() or "slow" in line.lower()]
            if lag_indicators:
                print(f"\n  [\!]  Performance warnings: {len(lag_indicators)}")
            else:
                print(f"\n  [OK] No performance warnings detected")

            return {
                "status": "ok",
                "om_timings": len(om_timings),
                "micro_timings": len(micro_timings),
                "lag_warnings": len(lag_indicators)
            }

        except Exception as e:
            print(f"\n[X] Error reading log file: {e}")
            return {"status": "error", "error": str(e)}

    def generate_summary_report(self) -> Dict:
        """Generate comprehensive summary report"""
        print("\n" + "=" * 70)
        print("INTEGRATION MONITORING SUMMARY")
        print("=" * 70)
        print(f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        summary = {
            "report_time": datetime.now().isoformat(),
            "opponent_modeling": self.check_opponent_models(),
            "micro_v3": self.check_micro_v3_status(),
            "errors": self.check_errors(),
            "performance": self.check_performance()
        }

        # Overall health check
        print("\n" + "=" * 70)
        print("OVERALL SYSTEM HEALTH")
        print("=" * 70 + "\n")

        health_issues = []

        # Check each subsystem
        if summary["opponent_modeling"]["status"] == "no_data":
            health_issues.append("[\!]  No opponent data - play some games")
        elif summary["opponent_modeling"]["status"] == "active":
            print("[OK] OpponentModeling: Active")
        else:
            health_issues.append(f"[X] OpponentModeling: {summary['opponent_modeling']['status']}")

        if summary["micro_v3"]["status"] == "no_activity":
            health_issues.append("[\!]  No Micro V3 activity - check integration")
        elif summary["micro_v3"]["status"] == "active":
            print("[OK] AdvancedMicroV3: Active")
        else:
            health_issues.append(f"[X] AdvancedMicroV3: {summary['micro_v3']['status']}")

        if summary["errors"]["error_count"] > 0:
            health_issues.append(f"[\!]  {summary['errors']['error_count']} errors detected")
        else:
            print("[OK] Error Check: Clean")

        if summary["performance"]["status"] == "ok":
            print("[OK] Performance: OK")
        else:
            health_issues.append(f"[\!]  Performance: {summary['performance']['status']}")

        if health_issues:
            print("\n[SEARCH] Issues Found:")
            for issue in health_issues:
                print(f"   {issue}")
        else:
            print("\n[PARTY] All systems operational!")

        # Save report
        report_file = self.base_dir / "integration_monitor_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[STATS] Full report saved to: {report_file}")

        return summary

    def watch_mode(self, interval: int = 60):
        """Continuous monitoring mode"""
        print("\n" + "=" * 70)
        print("CONTINUOUS MONITORING MODE")
        print("=" * 70)
        print(f"Refresh interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                self.generate_summary_report()
                print(f"\n[WAIT] Next update in {interval} seconds...")
                time.sleep(interval)
                print("\n" + "=" * 70)
                print(f"REFRESH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 70)

        except KeyboardInterrupt:
            print("\n\n[STOP] Monitoring stopped by user")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 15 Integration Monitor"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuous monitoring mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Watch mode refresh interval in seconds (default: 60)"
    )

    args = parser.parse_args()

    monitor = IntegrationMonitor()

    if args.watch:
        monitor.watch_mode(interval=args.interval)
    else:
        monitor.generate_summary_report()


if __name__ == "__main__":
    main()
