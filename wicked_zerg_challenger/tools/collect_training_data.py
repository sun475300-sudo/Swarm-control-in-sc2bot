#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collect Training Data - Monitor and collect training game data

This script monitors the training process and collects build order timing data
for analysis and comparison with pro gamer replays.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import psutil

PROJECT_ROOT = Path(__file__).parent.parent


def check_training_running() -> bool:
    """Check if training process is running"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(str(c) for c in cmdline)
                    if 'run_with_training.py' in cmdline_str and 'check_training_status' not in cmdline_str:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    except Exception:
        return False


def collect_training_stats() -> Dict[str, Any]:
    """Collect current training statistics"""
    stats_files = [
        PROJECT_ROOT / "training_stats.json",
        PROJECT_ROOT / "data" / "training_stats.json",
        PROJECT_ROOT / "local_training" / "training_stats.json",
    ]

    for stats_file in stats_files:
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.startswith('{'):
                        return json.loads(content)
                    else:
                        # JSONL format
                        lines = [line.strip() for line in content.split('\n') if line.strip()]
                        if lines:
                            games = []
                            for line in lines:
                                try:
                                    games.append(json.loads(line))
                                except:
                                    pass
                            if games:
                                total = len(games)
                                wins = sum(1 for g in games if g.get('result', '').upper() == 'VICTORY' or g.get('loss_reason', '').upper() == 'VICTORY')
                                losses = total - wins
                                return {
                                    'total_games': total,
                                    'wins': wins,
                                    'losses': losses,
                                    'win_rate': (wins / total * 100) if total > 0 else 0.0,
                                    'games': games
                                }
            except Exception:
                continue
    return {}


def collect_build_order_timing_data() -> List[Dict[str, Any]]:
    """Collect build order timing data from comparison history"""
    history_file = PROJECT_ROOT / "local_training" / "scripts" / "build_order_comparison_history.json"
    
    if not history_file.exists():
        return []
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        comparisons = history.get('comparisons', [])
        timing_data = []
        
        for comp in comparisons:
            training_build = comp.get('training_build', {})
            pro_baseline = comp.get('pro_baseline', {})
            
            # Extract timing data
            timing_entry = {
                'game_id': comp.get('game_id', 'unknown'),
                'game_result': comp.get('game_result', 'Unknown'),
                'overall_score': comp.get('overall_score', 0.0),
                'training_timings': {},
                'pro_baseline': {},
                'timestamp': comp.get('timestamp', datetime.now().isoformat())
            }
            
            # Training timings
            for param, value in training_build.items():
                if value is not None:
                    timing_entry['training_timings'][param] = value
            
            # Pro baseline
            for param, value in pro_baseline.items():
                if value is not None:
                    timing_entry['pro_baseline'][param] = value
            
            timing_data.append(timing_entry)
        
        return timing_data
    except Exception as e:
        print(f"[ERROR] Failed to collect build order timing data: {e}")
        return []


def generate_data_collection_report(stats: Dict[str, Any], timing_data: List[Dict[str, Any]]) -> str:
    """Generate data collection report"""
    report_lines = [
        "=" * 70,
        "TRAINING DATA COLLECTION REPORT",
        "=" * 70,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "[TRAINING STATISTICS]",
        "-" * 70,
        f"Total Games: {stats.get('total_games', 0)}",
        f"Wins: {stats.get('wins', 0)}",
        f"Losses: {stats.get('losses', 0)}",
        f"Win Rate: {stats.get('win_rate', 0.0):.1f}%",
        "",
        "[BUILD ORDER TIMING DATA]",
        "-" * 70,
        f"Total Comparison Records: {len(timing_data)}",
    ]
    
    if timing_data:
        # Analyze timing data
        param_stats = {}
        for entry in timing_data:
            for param, value in entry.get('training_timings', {}).items():
                if param not in param_stats:
                    param_stats[param] = []
                if value is not None:
                    param_stats[param].append(value)
        
        if param_stats:
            report_lines.append("\n[PARAMETER STATISTICS]")
            report_lines.append("-" * 70)
            for param, values in sorted(param_stats.items()):
                if values:
                    avg = sum(values) / len(values)
                    report_lines.append(f"  {param}:")
                    report_lines.append(f"    Count: {len(values)}")
                    report_lines.append(f"    Average: {avg:.1f}")
                    report_lines.append(f"    Min: {min(values):.1f}")
                    report_lines.append(f"    Max: {max(values):.1f}")
    
    report_lines.append("")
    report_lines.append("=" * 70)
    
    return "\n".join(report_lines)


def main():
    """Main function"""
    print("=" * 70)
    print("TRAINING DATA COLLECTION")
    print("=" * 70)
    print()
    
    # Check if training is running
    if check_training_running():
        print("[INFO] Training process is running")
    else:
        print("[WARNING] Training process is not running")
        print("[INFO] Start training with: python run_with_training.py")
        print()
    
    # Collect statistics
    print("[STEP 1] Collecting training statistics...")
    stats = collect_training_stats()
    if stats:
        print(f"  ? Collected stats: {stats.get('total_games', 0)} games")
    else:
        print("  ? No training statistics found")
    
    print()
    
    # Collect build order timing data
    print("[STEP 2] Collecting build order timing data...")
    timing_data = collect_build_order_timing_data()
    if timing_data:
        print(f"  ? Collected {len(timing_data)} comparison records")
    else:
        print("  ? No build order timing data found")
    
    print()
    
    # Generate report
    print("[STEP 3] Generating data collection report...")
    report = generate_data_collection_report(stats, timing_data)
    
    # Save report
    report_file = PROJECT_ROOT / "local_training" / "data_collection_report.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"  ? Report saved to: {report_file}")
    print()
    
    # Print summary
    print(report)
    
    # Recommendations
    print()
    print("[RECOMMENDATIONS]")
    print("-" * 70)
    total_games = stats.get('total_games', 0)
    
    if total_games < 100:
        print(f"  [WARNING] Current: {total_games} games")
        print(f"  -> Recommended: Collect at least 100 games for reliable statistics")
        print(f"  -> Need: {100 - total_games} more games")
    else:
        print(f"  [OK] Sufficient data collected: {total_games} games")
    
    if len(timing_data) < 10:
        print(f"  [WARNING] Current: {len(timing_data)} build order comparison records")
        print(f"  -> Recommended: At least 10 comparison records for analysis")
        print(f"  -> Need: {10 - len(timing_data)} more records")
    else:
        print(f"  [OK] Sufficient comparison data: {len(timing_data)} records")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
