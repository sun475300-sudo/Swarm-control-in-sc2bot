#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Post Training Learning Workflow

게임 훈련이 끝난 후 자동으로 실행되는 워크플로우:
1. 리플레이 비교 분석
2. 프로게이머 리플레이 다시 학습
3. 학습된 파라미터 적용
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def run_comparison_analysis() -> bool:
    """Run comparison analysis between training and pro replays"""
    print("\n[STEP 1] Running comparison analysis...")
    print("-" * 70)

    try:
        from tools.compare_pro_vs_training_replays import ProVsTrainingComparator

        comparator = ProVsTrainingComparator()

        # Load data
        pro_data = comparator.load_pro_replay_data()
        training_data = comparator.load_training_data()

        if not pro_data.get("baseline") and not pro_data.get("build_orders"):
            print("[WARNING] No pro replay data found")
            return False

        if not training_data.get(
                "comparisons") and not training_data.get("build_orders"):
            print("[WARNING] No training data found")
            return False

        # Compare timings
        timing_comparisons = comparator.compare_timings(
            pro_data, training_data)

        # Analyze performance
        performance_analysis = comparator.analyze_performance(
            pro_data, training_data)

        # Generate report
        report = comparator.generate_comparison_report(
            pro_data, training_data, timing_comparisons, performance_analysis
        )

        # Save comparison data
        comparator.save_comparison_data(
            pro_data,
            training_data,
            timing_comparisons,
            performance_analysis,
            report)

        print("[SUCCESS] Comparison analysis complete")
        print(f"[INFO] Comparison report saved")

        return True

    except Exception as e:
        print(f"[ERROR] Comparison analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def learn_from_pro_replays(
        max_replays: int = 50, archive_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Learn from pro gamer replays and track data paths"""
    print("\n[STEP 2] Learning from pro gamer replays...")
    print("-" * 70)

    try:
        from local_training.scripts.replay_build_order_learner import (
            ReplayBuildOrderExtractor,
            update_config_with_learned_params
        )

        # Find pro replay directory
        pro_replay_dir = Path("D:/replays/replays")
        if not pro_replay_dir.exists():
            pro_replay_dir = Path("replays_archive")

        if not pro_replay_dir.exists():
            print(f"[WARNING] Replay directory not found: {pro_replay_dir}")
            return None

        # Set archive directory (default: D:\replays\archive)
        if archive_dir is None:
            archive_dir = Path("D:/replays/archive")

        print(
            f"[INFO] Learning from {max_replays} replays in {pro_replay_dir}...")
        print(f"[INFO] Archive directory: {archive_dir}")

        extractor = ReplayBuildOrderExtractor(replay_dir=str(pro_replay_dir))
        learned_params = extractor.learn_from_replays(max_replays=max_replays)

        if not learned_params:
            print("[WARNING] No parameters learned from replays")
            return None

        # Save learned parameters (will save to archive directory)
        saved_path = extractor.save_learned_parameters(
            learned_params,
            output_file=str(
                archive_dir /
                f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}" /
                "learned_build_orders.json"))

        # Track data paths
        data_paths = {
            "learned_params": learned_params,
            "source_replay_dir": str(pro_replay_dir),
            "archive_dir": str(archive_dir),
            "saved_path": str(saved_path) if saved_path else None,
            "save_timestamp": datetime.now().isoformat()
        }

        print(f"[SUCCESS] Learned parameters saved to: {saved_path}")
        print(f"[INFO] Data paths tracked:")
        print(f"  - Source replay dir: {data_paths['source_replay_dir']}")
        print(f"  - Archive dir: {data_paths['archive_dir']}")
        print(f"  - Saved path: {data_paths['saved_path']}")

        # Also save to local_training/scripts/learned_build_orders.json for
        # immediate use
        local_learned_path = PROJECT_ROOT / "local_training" / \
            "scripts" / "learned_build_orders.json"
        local_learned_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_learned_path, 'w', encoding='utf-8') as f:
            json.dump(learned_params, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Also saved to local training: {local_learned_path}")

        # Update config
        try:
            update_config_with_learned_params(learned_params)
            print("[SUCCESS] Config updated with learned parameters")
        except Exception as e:
            print(f"[WARNING] Failed to update config: {e}")

        print(
            f"[SUCCESS] Learned {len(learned_params)} parameters from {max_replays} replays")

        return data_paths

    except Exception as e:
        print(f"[ERROR] Replay learning failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def track_and_reset_data_paths(
        data_paths: Dict[str, Any], target_archive_dir: Path = Path("D:/replays/archive")) -> bool:
    """Track data paths and reset to target archive directory"""
    print("\n[STEP 3] Tracking and resetting data paths...")
    print("-" * 70)

    try:
        # Create target archive directory if it doesn't exist
        target_archive_dir.mkdir(parents=True, exist_ok=True)

        print(f"[INFO] Target archive directory: {target_archive_dir}")

        # Save path tracking information
        path_tracking_file = target_archive_dir / "learning_path_tracking.json"

        # Load existing tracking data if exists
        existing_tracking = []
        if path_tracking_file.exists():
            try:
                with open(path_tracking_file, 'r', encoding='utf-8') as f:
                    existing_tracking = json.load(f)
            except Exception:
                existing_tracking = []

        # Add new tracking entry
        tracking_entry = {
            "timestamp": data_paths.get(
                "save_timestamp",
                datetime.now().isoformat()),
            "source_replay_dir": data_paths.get("source_replay_dir"),
            "archive_dir": str(target_archive_dir),
            "saved_path": data_paths.get("saved_path"),
            "learned_params_count": len(
                data_paths.get(
                    "learned_params",
                    {}))}

        existing_tracking.append(tracking_entry)

        # Keep only last 100 entries
        if len(existing_tracking) > 100:
            existing_tracking = existing_tracking[-100:]

        # Save tracking data
        with open(path_tracking_file, 'w', encoding='utf-8') as f:
            json.dump(existing_tracking, f, indent=2, ensure_ascii=False)

        print(f"[SUCCESS] Path tracking saved to: {path_tracking_file}")
        print(f"[INFO] Tracking entry:")
        print(f"  - Timestamp: {tracking_entry['timestamp']}")
        print(f"  - Source: {tracking_entry['source_replay_dir']}")
        print(f"  - Archive: {tracking_entry['archive_dir']}")
        print(f"  - Saved: {tracking_entry['saved_path']}")
        print(f"  - Parameters: {tracking_entry['learned_params_count']}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to track and reset data paths: {e}")
        import traceback
        traceback.print_exc()
        return False


def apply_learned_parameters(learned_params: Dict[str, float]) -> bool:
    """Apply learned parameters to training"""
    print("\n[STEP 3] Applying learned parameters...")
    print("-" * 70)

    try:
        learned_path = PROJECT_ROOT / "local_training" / \
            "scripts" / "learned_build_orders.json"

        # Load current parameters
        current_params = {}
        if learned_path.exists():
            with open(learned_path, 'r', encoding='utf-8') as f:
                current_params = json.load(f)

        # Merge learned parameters
        updated_params = current_params.copy()
        changes = []

        for param_name, learned_value in learned_params.items():
            current_value = current_params.get(param_name)
            if current_value != learned_value:
                updated_params[param_name] = float(learned_value)
                changes.append({
                    "parameter": param_name,
                    "old": current_value,
                    "new": learned_value
                })

        if changes:
            # Save updated parameters
            learned_path.parent.mkdir(parents=True, exist_ok=True)
            with open(learned_path, 'w', encoding='utf-8') as f:
                json.dump(updated_params, f, indent=2, ensure_ascii=False)

            print(f"[SUCCESS] Updated {len(changes)} parameters:")
            for change in changes:
                print(
                    f"  {change['parameter']}: {change['old']} → {change['new']}")

            return True
        else:
            print("[INFO] No parameter changes needed")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to apply learned parameters: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("POST TRAINING LEARNING WORKFLOW")
    print("=" * 70)
    print()
    print("This workflow will:")
    print("  1. Run comparison analysis (training vs pro replays)")
    print("  2. Learn from pro gamer replays")
    print("  3. Apply learned parameters to training")
    print()

    # Step 1: Comparison analysis
    comparison_success = run_comparison_analysis()

    # Step 2: Learn from pro replays
    data_paths = None
    learned_params = None
    archive_dir = Path("D:/replays/archive")

    if comparison_success:
        max_replays = 50
        data_paths = learn_from_pro_replays(
            max_replays=max_replays, archive_dir=archive_dir)
    else:
        print("[WARNING] Skipping replay learning due to comparison analysis failure")
        data_paths = learn_from_pro_replays(
            max_replays=50, archive_dir=archive_dir)

    # Step 3: Track and reset data paths
    if data_paths:
        learned_params = data_paths.get("learned_params")
        track_and_reset_data_paths(data_paths, target_archive_dir=archive_dir)

    # Step 4: Apply learned parameters
    if learned_params:
        apply_learned_parameters(learned_params)

    # Summary
    print("\n" + "=" * 70)
    print("POST TRAINING LEARNING WORKFLOW COMPLETE")
    print("=" * 70)
    print()

    if learned_params:
        print(f"Summary:")
        print(
            f"  - Comparison analysis: {'Success' if comparison_success else 'Warning'}")
        print(f"  - Learned parameters: {len(learned_params)}")
        print(f"  - Parameters updated: {len(learned_params) > 0}")
        if data_paths:
            print(f"  - Archive directory: {data_paths.get('archive_dir')}")
            print(f"  - Saved path: {data_paths.get('saved_path')}")
        print()
        print("Next steps:")
        print("  - Start next training session with updated parameters")
        print("  - Monitor performance improvements")
        print(f"  - Data archived to: {archive_dir}")
    else:
        print("[WARNING] No parameters learned. Check replay directory and data.")

    print("=" * 70)


if __name__ == "__main__":
    main()
