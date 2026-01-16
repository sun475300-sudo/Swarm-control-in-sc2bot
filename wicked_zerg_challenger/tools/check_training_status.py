#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Training Status - Check background training process status
"""

import sys
import json
import os
import psutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def check_python_processes():
    """Check if training Python process is running"""
    print("\n" + "=" * 70)
    print("PYTHON PROCESSES")
    print("=" * 70)
    
    training_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_info']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(cmdline)
                    if 'run_with_training' in cmdline_str or 'training' in cmdline_str.lower():
                        training_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline_str,
                            'create_time': datetime.fromtimestamp(proc.info['create_time']).strftime('%Y-%m-%d %H:%M:%S'),
                            'cpu_percent': proc.cpu_percent(interval=0.1),
                            'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                        })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if training_processes:
        print(f"\n[FOUND] {len(training_processes)} training process(es):")
        for proc in training_processes:
            print(f"\n  PID: {proc['pid']}")
            print(f"  Command: {proc['cmdline'][:100]}...")
            print(f"  Started: {proc['create_time']}")
            print(f"  CPU: {proc['cpu_percent']:.1f}%")
            print(f"  Memory: {proc['memory_mb']:.1f} MB")
    else:
        print("\n[NOT FOUND] No training process detected")
        print("  Training may have stopped or not started yet")
    
    return len(training_processes) > 0


def check_monitoring_server():
    """Check if monitoring server is running"""
    print("\n" + "=" * 70)
    print("MONITORING SERVER")
    print("=" * 70)
    
    try:
        import requests
        response = requests.get("http://localhost:8001/api/health", timeout=2)
        if response.status_code == 200:
            print("\n[RUNNING] Monitoring server is active")
            print("  URL: http://localhost:8001")
            print("  Status: OK")
            return True
        else:
            print("\n[WARNING] Monitoring server responded with status:", response.status_code)
            return False
    except requests.exceptions.ConnectionError:
        print("\n[NOT RUNNING] Monitoring server is not accessible")
        print("  URL: http://localhost:8001")
        print("  Status: Connection refused")
        return False
    except Exception as e:
        print(f"\n[ERROR] Failed to check monitoring server: {e}")
        return False


def check_training_stats():
    """Check training statistics files"""
    print("\n" + "=" * 70)
    print("TRAINING STATISTICS")
    print("=" * 70)
    
    # Check multiple possible locations
    stats_files = [
        PROJECT_ROOT / "training_stats.json",
        PROJECT_ROOT / "data" / "training_stats.json",
        PROJECT_ROOT / "local_training" / "training_stats.json",
    ]
    
    stats_found = False
    for stats_file in stats_files:
        if stats_file.exists():
            stats_found = True
            print(f"\n[FOUND] {stats_file}")
            try:
                # Try JSON format first
                with open(stats_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.startswith('{'):
                        stats = json.loads(content)
                        print(f"  Total Games: {stats.get('total_games', 0)}")
                        print(f"  Wins: {stats.get('wins', 0)}")
                        print(f"  Losses: {stats.get('losses', 0)}")
                        print(f"  Win Rate: {stats.get('win_rate', 0):.1f}%")
                        if 'episode' in stats:
                            print(f"  Episode: {stats.get('episode', 0)}/{stats.get('total_episodes', 0)}")
                            print(f"  Progress: {stats.get('progress_percent', 0):.1f}%")
                    else:
                        # JSONL format - read all lines
                        lines = [line.strip() for line in content.split('\n') if line.strip()]
                        if lines:
                            print(f"  Format: JSONL ({len(lines)} records)")
                            # Parse all lines and aggregate
                            games = []
                            wins = 0
                            losses = 0
                            for line in lines:
                                try:
                                    game_data = json.loads(line)
                                    games.append(game_data)
                                    if game_data.get('result', '').upper() == 'VICTORY' or game_data.get('loss_reason', '').upper() == 'VICTORY':
                                        wins += 1
                                    elif game_data.get('result', '').upper() == 'DEFEAT' or game_data.get('loss_reason', '').upper() == 'DEFEAT':
                                        losses += 1
                                except:
                                    pass
                            
                            if games:
                                total = len(games)
                                win_rate = (wins / total * 100) if total > 0 else 0.0
                                print(f"  Total Games: {total}")
                                print(f"  Wins: {wins}")
                                print(f"  Losses: {losses}")
                                print(f"  Win Rate: {win_rate:.1f}%")
                                
                                # Show last game info
                                if games:
                                    last_game = games[-1]
                                    print(f"\n  Last Game:")
                                    print(f"    Result: {last_game.get('result', last_game.get('loss_reason', 'N/A'))}")
                                    if 'map_name' in last_game:
                                        print(f"    Map: {last_game.get('map_name', 'N/A')}")
                                    if 'enemy_race' in last_game:
                                        print(f"    Enemy: {last_game.get('enemy_race', 'N/A')}")
            except Exception as e:
                print(f"  [ERROR] Failed to read: {e}")
            break
    
    if not stats_found:
        print("\n[NOT FOUND] No training statistics file found")
        print("  Training may not have started yet or no games completed")
    
    return stats_found


def check_instance_status():
    """Check instance status file"""
    print("\n" + "=" * 70)
    print("INSTANCE STATUS")
    print("=" * 70)
    
    instance_file = PROJECT_ROOT / "local_training" / "stats" / "instance_0_status.json"
    if instance_file.exists():
        print(f"\n[FOUND] {instance_file}")
        try:
            with open(instance_file, 'r', encoding='utf-8') as f:
                instance_data = json.load(f)
                print(f"  Game Count: {instance_data.get('game_count', 0)}")
                print(f"  Win Count: {instance_data.get('win_count', 0)}")
                print(f"  Loss Count: {instance_data.get('loss_count', 0)}")
                print(f"  Win Rate: {instance_data.get('win_rate', 0):.1f}%")
                print(f"  Difficulty: {instance_data.get('difficulty', 'N/A')}")
                print(f"  Status: {instance_data.get('status', 'N/A')}")
                if 'last_update' in instance_data:
                    print(f"  Last Update: {instance_data.get('last_update', 'N/A')}")
        except Exception as e:
            print(f"  [ERROR] Failed to read: {e}")
    else:
        print("\n[NOT FOUND] Instance status file not found")
        print("  Training may not have started yet")


def check_recent_replays():
    """Check for recent replay files"""
    print("\n" + "=" * 70)
    print("RECENT REPLAYS")
    print("=" * 70)
    
    replay_dirs = [
        PROJECT_ROOT / "replays",
        Path("D:/replays"),
        PROJECT_ROOT / "local_training" / "replays",
    ]
    
    recent_replays = []
    for replay_dir in replay_dirs:
        if replay_dir.exists():
            for replay_file in replay_dir.glob("*.SC2Replay"):
                try:
                    stat = replay_file.stat()
                    recent_replays.append({
                        'path': str(replay_file),
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'size_mb': stat.st_size / 1024 / 1024
                    })
                except:
                    pass
    
    if recent_replays:
        # Sort by modification time
        recent_replays.sort(key=lambda x: x['modified'], reverse=True)
        print(f"\n[FOUND] {len(recent_replays)} replay file(s)")
        print("\n  Most recent replays:")
        for replay in recent_replays[:5]:
            print(f"    {replay['modified'].strftime('%Y-%m-%d %H:%M:%S')} - {Path(replay['path']).name} ({replay['size_mb']:.1f} MB)")
    else:
        print("\n[NOT FOUND] No replay files found")
        print("  Training may not have generated replays yet")


def main():
    """Main function"""
    print("=" * 70)
    print("TRAINING STATUS CHECK")
    print("=" * 70)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check processes
    process_running = check_python_processes()
    
    # Check monitoring server
    server_running = check_monitoring_server()
    
    # Check training stats
    stats_found = check_training_stats()
    
    # Check instance status
    check_instance_status()
    
    # Check recent replays
    check_recent_replays()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Training Process: {'RUNNING' if process_running else 'NOT RUNNING'}")
    print(f"  Monitoring Server: {'RUNNING' if server_running else 'NOT RUNNING'}")
    print(f"  Training Stats: {'FOUND' if stats_found else 'NOT FOUND'}")
    
    if process_running or server_running:
        print("\n? Training appears to be active")
        print("\n  Monitor at: http://localhost:8001")
    else:
        print("\n??  Training does not appear to be running")
        print("\n  To start training: python run_with_training.py")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
