#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimize and sort learning data
- Sorts strategy_db.json by matchup and extraction time
- Optimizes learned_build_orders.json
- Creates summary report
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Set
from typing import Any
from typing import Union


def load_json_safe(file_path: Path) -> Dict:
    """Safely load JSON file"""
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
 return json.load(f)
 except FileNotFoundError:
     return {}
 except json.JSONDecodeError as e:
     print(f"[ERROR] Invalid JSON in {file_path}: {e}")
 return {}

def save_json_safe(file_path: Path, data: Dict, indent: int = 2):
    """Safely save JSON file with backup"""
 # Create backup
 if file_path.exists():
     backup_path = file_path.with_suffix('.json.backup')
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
 backup_data = json.load(f)
     with open(backup_path, 'w', encoding='utf-8') as f:
 json.dump(backup_data, f, indent=indent, ensure_ascii=False)
     print(f"[BACKUP] Created backup: {backup_path}")
 except Exception as e:
     print(f"[WARNING] Failed to create backup: {e}")

 # Save new data
 file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
 json.dump(data, f, indent=indent, ensure_ascii=False, sort_keys=True)
    print(f"[SAVE] Saved: {file_path}")

def optimize_strategy_db(strategy_db_path: Path) -> Dict[str, Any]:
    """Optimize and sort strategy_db.json"""
    print(f"\n[OPTIMIZE] Processing strategy_db.json...")

 data = load_json_safe(strategy_db_path)
 if not data:
     print("[WARNING] strategy_db.json is empty or not found")
 return {}

 # Separate build orders from metadata
 build_orders = {}
 metadata = {}

 for key, value in data.items():
     if key.startswith("build_order"):
         pass
     build_orders[key] = value
 else:
     pass
 metadata[key] = value

 # Sort build orders by:
 # 1. Matchup (ZvT, ZvP, ZvZ)
 # 2. Extraction time (newest first)
def sort_key(item):
    key, strategy = item
    matchup = strategy.get("matchup", "Unknown")
    extracted_at = strategy.get("extracted_at", "1970-01-01T00:00:00")
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
     dt = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
 timestamp = dt.timestamp()
 except:
     timestamp = 0
 return (matchup, -timestamp) # Negative for descending order

 sorted_build_orders = dict(sorted(build_orders.items(), key=sort_key))

 # Reconstruct optimized data
 optimized_data = {**metadata, **sorted_build_orders}

 # Statistics
 matchup_counts = defaultdict(int)
 for strategy in build_orders.values():
     matchup = strategy.get("matchup", "Unknown")
 matchup_counts[matchup] += 1

    print(f"[STATS] Total strategies: {len(build_orders)}")
 for matchup, count in sorted(matchup_counts.items()):
     print(f"  {matchup}: {count}")

 return optimized_data

def optimize_learned_build_orders(learned_orders_path: Path) -> Dict[str, Any]:
    """Optimize learned_build_orders.json"""
    print(f"\n[OPTIMIZE] Processing learned_build_orders.json...")

 data = load_json_safe(learned_orders_path)
 if not data:
     print("[WARNING] learned_build_orders.json is empty or not found")
 return {}

 # Sort learned parameters by key
    if "learned_parameters" in data:
        data["learned_parameters"] = dict(sorted(data["learned_parameters"].items()))

 # Sort build orders by timing
    if "build_orders" in data and isinstance(data["build_orders"], list):
        def sort_build_order(bo):
            timings = bo.get("timings", {})
 if timings:
     # Sort by first timing value
 first_timing = min(timings.values()) if timings.values() else 0
 return first_timing
 return 0

     data["build_orders"] = sorted(data["build_orders"], key=sort_build_order)

    print(f"[STATS] Learned parameters: {len(data.get('learned_parameters', {}))}")
    print(f"[STATS] Build order samples: {len(data.get('build_orders', []))}")

 return data

def create_summary_report(
 strategy_db_path: Path,
 learned_orders_path: Path,
 output_path: Path
):
    """Create summary report of learning data"""
    print(f"\n[REPORT] Creating summary report...")

 strategy_db = load_json_safe(strategy_db_path)
 learned_orders = load_json_safe(learned_orders_path)

 # Collect statistics
 stats = {
    "generated_at": datetime.now().isoformat(),
    "strategy_database": {
    "total_strategies": 0,
    "by_matchup": {},
    "by_replay": {},
    "latest_extraction": None,
    "earliest_extraction": None
 },
    "learned_parameters": {
    "total_parameters": len(learned_orders.get("learned_parameters", {})),
    "source_replays": learned_orders.get("source_replays", 0),
    "replay_directory": learned_orders.get("replay_directory", "Unknown")
 }
 }

 # Analyze strategy database
    build_orders = {k: v for k, v in strategy_db.items() if k.startswith("build_order")}
    stats["strategy_database"]["total_strategies"] = len(build_orders)

 matchup_counts = defaultdict(int)
 replay_counts = defaultdict(int)
 extraction_times = []

 for strategy in build_orders.values():
     matchup = strategy.get("matchup", "Unknown")
 matchup_counts[matchup] += 1

     replay_name = strategy.get("replay_name", "Unknown")
 replay_counts[replay_name] += 1

     extracted_at = strategy.get("extracted_at")
 if extracted_at:
     extraction_times.append(extracted_at)

    stats["strategy_database"]["by_matchup"] = dict(matchup_counts)
    stats["strategy_database"]["by_replay"] = dict(sorted(
 replay_counts.items(),
 key=lambda x: x[1],
 reverse=True
 )[:10]) # Top 10 replays

 if extraction_times:
     extraction_times.sort()
     stats["strategy_database"]["earliest_extraction"] = extraction_times[0]
     stats["strategy_database"]["latest_extraction"] = extraction_times[-1]

 # Save report
 save_json_safe(output_path, stats)

    print(f"[REPORT] Summary saved to: {output_path}")
 return stats

def main():
    """Main optimization function"""
    print("=" * 60)
    print("Learning Data Optimization and Sorting")
    print("=" * 60)

 # Paths
    replay_dir = Path("D:/replays/replays")
    strategy_db_path = replay_dir / "strategy_db.json"
    learned_orders_path = Path("local_training/scripts/learned_build_orders.json")
    summary_path = replay_dir / "learning_summary.json"

 # Check if files exist
 if not strategy_db_path.exists():
     print(f"[WARNING] strategy_db.json not found at {strategy_db_path}")
     print("[INFO] Skipping strategy database optimization")
 else:
 # Optimize strategy database
 optimized_strategy_db = optimize_strategy_db(strategy_db_path)
 if optimized_strategy_db:
     save_json_safe(strategy_db_path, optimized_strategy_db)

 if not learned_orders_path.exists():
     print(f"[WARNING] learned_build_orders.json not found at {learned_orders_path}")
     print("[INFO] Skipping learned build orders optimization")
 else:
 # Optimize learned build orders
 optimized_learned_orders = optimize_learned_build_orders(learned_orders_path)
 if optimized_learned_orders:
     save_json_safe(learned_orders_path, optimized_learned_orders)

 # Create summary report
 if strategy_db_path.exists() or learned_orders_path.exists():
     create_summary_report(strategy_db_path, learned_orders_path, summary_path)

    print("\n" + "=" * 60)
    print("Optimization Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review optimized files")
    print("2. Check learning_summary.json for statistics")
    print("3. Continue training with optimized data")

if __name__ == "__main__":
    main()
