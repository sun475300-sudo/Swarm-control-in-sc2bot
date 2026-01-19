#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telemetry Analysis Tool

Analyzes telemetry data to answer:
1. "Why did we lose?" - Loss reason analysis
2. "Did swarm control algorithms work as expected?" - Swarm control performance analysis
3. Game performance metrics and trends

Usage:
 python tools/analyze_telemetry.py --telemetry telemetry_0.json
 python tools/analyze_telemetry.py --stats training_stats.json
 python tools/analyze_telemetry.py --all # Analyze all available data
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict
from typing import List
from typing import Any
from typing import Optional
from collections import defaultdict
from datetime import datetime
import statistics

try:
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[WARNING] pandas not available - using basic analysis")


class TelemetryAnalyzer:
    """Analyze telemetry data for performance insights"""

def __init__(
    self,
    telemetry_file: Optional[Path] = None,
    stats_file: Optional[Path] = None):
    self.telemetry_file = telemetry_file
 self.stats_file = stats_file
 self.telemetry_data: List[Dict[str, Any]] = []
 self.stats_data: List[Dict[str, Any]] = []

def load_telemetry(self, file_path: Path) -> bool:
    """Load telemetry JSON file"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     with open(file_path, 'r', encoding='utf-8') as f:
 self.telemetry_data = json.load(f)
     print(f"? Loaded {len(self.telemetry_data)} telemetry entries from {file_path.name}")
 return True
 except Exception as e:
     print(f"? Failed to load telemetry: {e}")
 return False

def load_stats(self, file_path: Path) -> bool:
    """Load training stats JSONL file"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     with open(file_path, 'r', encoding='utf-8') as f:
 for line in f:
     if line.strip():
         self.stats_data.append(json.loads(line))
         print(f"? Loaded {len(self.stats_data)} game results from {file_path.name}")
 return True
 except Exception as e:
     print(f"? Failed to load stats: {e}")
 return False

def analyze_loss_reasons(self) -> Dict[str, Any]:
    """Analyze why games were lost"""
 if not self.stats_data:
     return {"error": "No stats data available"}

 loss_reasons = defaultdict(int)
 loss_by_race = defaultdict(lambda: defaultdict(int))
 loss_by_time = defaultdict(list)

 for game in self.stats_data:
     if game.get("result") == "Defeat":
         pass
     reason = game.get("loss_reason", "Unknown")
 loss_reasons[reason] += 1

     opponent = game.get("opponent_race", "Unknown")
 loss_by_race[opponent][reason] += 1

     game_time = game.get("game_time", 0)
 loss_by_time[reason].append(game_time)

 # Calculate average loss times
 avg_loss_times = {}
 for reason, times in loss_by_time.items():
     if times:
         avg_loss_times[reason] = {
         "avg": statistics.mean(times),
         "min": min(times),
         "max": max(times)
 }

 return {
     "total_losses": sum(loss_reasons.values()),
     "loss_reasons": dict(loss_reasons),
     "loss_by_race": {k: dict(v) for k, v in loss_by_race.items()},
     "avg_loss_times": avg_loss_times
 }

def analyze_swarm_control_performance(self) -> Dict[str, Any]:
    """Analyze swarm control algorithm performance"""
 if not self.telemetry_data:
     return {"error": "No telemetry data available"}

 # Analyze unit distribution and formation
 army_distributions = []
 formation_quality = []
 unit_spacing_issues = []

 for entry in self.telemetry_data:
     army_count = entry.get("army_count", 0)
     enemy_army = entry.get("enemy_army_seen", 0)

 if army_count > 0:
     # Calculate army distribution (ideal: spread out, not clustered)
 army_distributions.append({
     "time": entry.get("time", 0),
     "army_count": army_count,
     "enemy_army": enemy_army,
     "army_supply": entry.get("army_supply", 0),
 })

 # Formation quality: check if army is well-distributed
 # (Simplified: assume good formation if army_count > 0 and supply is reasonable)
     if army_count > 0 and entry.get("army_supply", 0) > 0:
         pass
     supply_per_unit = entry.get("army_supply", 0) / army_count
 # Ideal: 1-2 supply per unit (zerglings=0.5, roaches=2, hydras=2)
 if 0.5 <= supply_per_unit <= 2.5:
     formation_quality.append(1)
 else:
     pass
 formation_quality.append(0)

 # Analyze resource efficiency
 resource_efficiency = []
 for entry in self.telemetry_data:
     minerals = entry.get("minerals", 0)
     vespene = entry.get("vespene", 0)
     army_count = entry.get("army_count", 0)

 if army_count > 0:
     # Resource efficiency: resources per army unit
 # Lower is better (more efficient)
 efficiency = (minerals + vespene * 1.5) / army_count if army_count > 0 else 0
 resource_efficiency.append({
     "time": entry.get("time", 0),
     "efficiency": efficiency,
     "army_count": army_count
 })

 return {
     "total_entries": len(self.telemetry_data),
     "army_distributions": army_distributions[-100:],  # Last 100 entries
     "formation_quality_score": statistics.mean(formation_quality) if formation_quality else 0,
     "avg_resource_efficiency": statistics.mean([e["efficiency"] for e in resource_efficiency]) if resource_efficiency else 0,
     "resource_efficiency_trend": resource_efficiency[-50:],  # Last 50 entries
 }

def analyze_game_performance(self) -> Dict[str, Any]:
    """Analyze overall game performance metrics"""
 if not self.telemetry_data:
     return {"error": "No telemetry data available"}

 # Extract key metrics
     minerals_over_time = [e.get("minerals", 0) for e in self.telemetry_data]
     army_over_time = [e.get("army_count", 0) for e in self.telemetry_data]
     workers_over_time = [e.get("drone_count", 0) for e in self.telemetry_data]
     supply_over_time = [e.get("supply_used", 0) for e in self.telemetry_data]

 # Calculate trends
def calculate_trend(values: List[float]) -> Dict[str, float]:
    if len(values) < 2:
        pass
    return {"trend": "insufficient_data", "change": 0.0}

 first_half = values[:len(values)//2]
 second_half = values[len(values)//2:]

 first_avg = statistics.mean(first_half) if first_half else 0
 second_avg = statistics.mean(second_half) if second_half else 0

 if first_avg == 0:
     # Avoid division by zero
 if second_avg > 0:
     return {"trend": "increasing", "change": 100.0}
 else:
     return {"trend": "stable", "change": 0.0}

 change_percent = (second_avg - first_avg) / first_avg * 100

 if second_avg > first_avg * 1.1:
     return {"trend": "increasing", "change": change_percent}
 elif second_avg < first_avg * 0.9:
     return {"trend": "decreasing", "change": change_percent}
 else:
     return {"trend": "stable", "change": change_percent}

 return {
     "game_duration": self.telemetry_data[-1].get("time", 0) if self.telemetry_data else 0,
     "minerals": {
     "max": max(minerals_over_time) if minerals_over_time else 0,
     "avg": statistics.mean(minerals_over_time) if minerals_over_time else 0,
     "final": minerals_over_time[-1] if minerals_over_time else 0,
     "trend": calculate_trend(minerals_over_time)
 },
     "army": {
     "max": max(army_over_time) if army_over_time else 0,
     "avg": statistics.mean(army_over_time) if army_over_time else 0,
     "final": army_over_time[-1] if army_over_time else 0,
     "trend": calculate_trend(army_over_time)
 },
     "workers": {
     "max": max(workers_over_time) if workers_over_time else 0,
     "avg": statistics.mean(workers_over_time) if workers_over_time else 0,
     "final": workers_over_time[-1] if workers_over_time else 0,
     "trend": calculate_trend(workers_over_time)
 },
     "supply": {
     "max": max(supply_over_time) if supply_over_time else 0,
     "avg": statistics.mean(supply_over_time) if supply_over_time else 0,
     "final": supply_over_time[-1] if supply_over_time else 0,
     "trend": calculate_trend(supply_over_time)
 }
 }

def generate_report(self) -> str:
    """Generate comprehensive analysis report"""
 report = []
    report.append("="*70)
    report.append("TELEMETRY ANALYSIS REPORT")
    report.append("="*70)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

 # Loss reason analysis
 if self.stats_data:
     report.append("## 1. LOSS REASON ANALYSIS")
     report.append("-"*70)
 loss_analysis = self.analyze_loss_reasons()

     if "error" not in loss_analysis:
         pass
     report.append(f"Total Losses: {loss_analysis['total_losses']}")
     report.append("")
     report.append("Loss Reasons:")
     for reason, count in sorted(loss_analysis['loss_reasons'].items(), key=lambda x: x[1], reverse=True):
         pass
     percentage = (count / loss_analysis['total_losses'] * 100) if loss_analysis['total_losses'] > 0 else 0
     report.append(f"  - {reason}: {count} ({percentage:.1f}%)")

     report.append("")
     report.append("Average Loss Times by Reason:")
     for reason, times in loss_analysis.get('avg_loss_times', {}).items():
         pass
     report.append(f"  - {reason}: {times['avg']:.1f}s (min: {times['min']}s, max: {times['max']}s)")
 else:
     report.append(f"  {loss_analysis['error']}")

     report.append("")

 # Swarm control analysis
 if self.telemetry_data:
     report.append("## 2. SWARM CONTROL ALGORITHM PERFORMANCE")
     report.append("-"*70)
 swarm_analysis = self.analyze_swarm_control_performance()

     if "error" not in swarm_analysis:
         pass
     report.append(f"Formation Quality Score: {swarm_analysis['formation_quality_score']:.2%}")
     report.append(f"  (1.0 = Perfect formation, 0.0 = Poor formation)")
     report.append("")
     report.append(f"Average Resource Efficiency: {swarm_analysis['avg_resource_efficiency']:.2f}")
     report.append(f"  (Lower is better - resources per army unit)")
     report.append("")
     report.append(f"Total Telemetry Entries: {swarm_analysis['total_entries']}")
 else:
     report.append(f"  {swarm_analysis['error']}")

     report.append("")

 # Game performance
 if self.telemetry_data:
     report.append("## 3. GAME PERFORMANCE METRICS")
     report.append("-"*70)
 perf_analysis = self.analyze_game_performance()

     if "error" not in perf_analysis:
         pass
     report.append(f"Game Duration: {perf_analysis['game_duration']}s")
     report.append("")

     for metric_name, metric_data in [("Minerals", perf_analysis['minerals']),
     ("Army", perf_analysis['army']),
     ("Workers", perf_analysis['workers']),
     ("Supply", perf_analysis['supply'])]:
     report.append(f"{metric_name}:")
     report.append(f"  Max: {metric_data['max']}")
     report.append(f"  Avg: {metric_data['avg']:.1f}")
     report.append(f"  Final: {metric_data['final']}")
     if isinstance(metric_data['trend'], dict):
         pass
     trend = metric_data['trend'].get('trend', 'unknown')
     change = metric_data['trend'].get('change', 0)
     report.append(f"  Trend: {trend} ({change:+.1f}%)")
     report.append("")
 else:
     report.append(f"  {perf_analysis['error']}")

     report.append("="*70)
     return "\n".join(report)


def find_telemetry_files(directory: Path) -> List[Path]:
    """Find all telemetry JSON files"""
    return list(directory.glob("telemetry_*.json"))


def find_stats_files(directory: Path) -> List[Path]:
    """Find all training stats files"""
    return list(directory.glob("training_stats.json"))


def main():
    parser = argparse.ArgumentParser(description="Analyze telemetry data")
    parser.add_argument("--telemetry", type=str, help="Telemetry JSON file path")
    parser.add_argument("--stats", type=str, help="Training stats JSONL file path")
    parser.add_argument("--all", action="store_true", help="Analyze all available files")
    parser.add_argument("--output", type=str, help="Output report file path")
 args = parser.parse_args()

 # Find files
 project_root = Path(__file__).parent.parent

 analyzer = TelemetryAnalyzer()

 if args.all:
     # Find all telemetry files
 telemetry_files = find_telemetry_files(project_root)
 stats_files = find_stats_files(project_root)

 if telemetry_files:
     print(f"Found {len(telemetry_files)} telemetry files")
 # Load latest
 latest_telemetry = max(telemetry_files, key=lambda p: p.stat().st_mtime)
 analyzer.load_telemetry(latest_telemetry)

 if stats_files:
     print(f"Found {len(stats_files)} stats files")
 analyzer.load_stats(stats_files[0])
 else:
 # Load specified files
 if args.telemetry:
     analyzer.load_telemetry(Path(args.telemetry))
 elif args.stats:
     analyzer.load_stats(Path(args.stats))
 else:
 # Try to find files automatically
 telemetry_files = find_telemetry_files(project_root)
 stats_files = find_stats_files(project_root)

 if telemetry_files:
     latest = max(telemetry_files, key=lambda p: p.stat().st_mtime)
 analyzer.load_telemetry(latest)

 if stats_files:
     analyzer.load_stats(stats_files[0])

 # Generate report
 report = analyzer.generate_report()

 # Output
 if args.output:
     output_path = Path(args.output)
     output_path.write_text(report, encoding='utf-8')
     print(f"\n? Report saved to: {output_path}")
 else:
     print("\n" + report)


if __name__ == "__main__":
    main()
