#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Training with Monitoring and Auto Learning

�н� ���� ����͸� �� �н� �Ϸ� �� �ڵ� �� �м� �� ���н� ��ũ�÷ο�
"""

import sys
import time
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


class TrainingMonitor:
    """�н� ���� ����͸�"""

    def __init__(self):
        self.monitoring_url = "http://localhost:8000"
        self.stats_file = PROJECT_ROOT / "training_stats.json"

    def check_monitoring_server(self) -> bool:
        """����͸� ���� ���� Ȯ��"""
        try:
            import requests
            # Try local server port (8001)
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                self.monitoring_url = "http://localhost:8001"
                return True
        except Exception:
            pass

        try:
            # Try alternative port (8000)
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                self.monitoring_url = "http://localhost:8000"
                return True
        except Exception:
            pass

        return False

    def open_monitoring_dashboard(self):
        """����͸� ��ú��� ����"""
        try:
            print(
                f"\n[INFO] Opening monitoring dashboard: {self.monitoring_url}")
            webbrowser.open(self.monitoring_url)
            print("[SUCCESS] Monitoring dashboard opened in browser")
        except Exception as e:
            print(f"[WARNING] Failed to open dashboard: {e}")
            print(f"[INFO] Manually open: {self.monitoring_url}")

    def get_training_stats(self) -> Optional[dict]:
        """�н� ��� ��������"""
        try:
            if self.stats_file.exists():
                import json
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to read training stats: {e}")
        return None

    def print_training_summary(self):
        """�н� ��� ���"""
        stats = self.get_training_stats()
        if stats:
            print("\n" + "=" * 70)
            print("TRAINING SUMMARY")
            print("=" * 70)
            print(f"Total games: {stats.get('total_games', 0)}")
            print(f"Wins: {stats.get('wins', 0)}")
            print(f"Losses: {stats.get('losses', 0)}")
            win_rate = stats.get('win_rate', 0)
            print(f"Win rate: {win_rate:.1f}%")
            print("=" * 70)


class PostTrainingLearning:
    """�н� �Ϸ� �� �ڵ� �н� ��ũ�÷ο�"""

    def __init__(self):
        self.comparison_script = PROJECT_ROOT / "tools" / \
            "run_comparison_and_apply_learning.py"
        self.post_learning_script = PROJECT_ROOT / \
            "tools" / "post_training_learning_workflow.py"

    def run_comparison_analysis(self) -> bool:
        """���÷��� �� �м� ����"""
        print("\n[STEP 1] Running comparison analysis...")
        print("-" * 70)

        try:
            result = subprocess.run(
                [sys.executable, str(self.comparison_script)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode == 0:
                print("[SUCCESS] Comparison analysis completed")
                return True
            else:
                print(f"[ERROR] Comparison analysis failed")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to run comparison: {e}")
            return False

    def learn_from_pro_replays(self) -> bool:
        """���� ���÷��̿��� ���н�"""
        print("\n[STEP 2] Learning from pro gamer replays...")
        print("-" * 70)

        try:
            result = subprocess.run(
                [sys.executable, str(self.post_learning_script)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode == 0:
                print("[SUCCESS] Pro replay learning completed")
                return True
            else:
                print(f"[ERROR] Pro replay learning failed")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to learn from pro replays: {e}")
            return False

    def apply_learned_parameters(self) -> bool:
        """�н� �Ķ���� ����"""
        print("\n[STEP 3] Applying learned parameters...")
        print("-" * 70)

        try:
            from tools.apply_optimized_params_to_training import main as apply_params
            apply_params()
            print("[SUCCESS] Learned parameters applied")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to apply parameters: {e}")
            return False

    def run_full_workflow(self) -> bool:
        """��ü ��ũ�÷ο� ����"""
        print("\n" + "=" * 70)
        print("POST TRAINING LEARNING WORKFLOW")
        print("=" * 70)

        success = True

        # Step 1: Comparison analysis
        if not self.run_comparison_analysis():
            success = False

        # Step 2: Learn from pro replays
        if not self.learn_from_pro_replays():
            success = False

        # Step 3: Apply learned parameters
        if not self.apply_learned_parameters():
            success = False

        if success:
            print("\n" + "=" * 70)
            print("POST TRAINING LEARNING COMPLETE")
            print("=" * 70)
            print("[SUCCESS] All steps completed successfully")
            print("[INFO] Learned parameters are ready for next training")
        else:
            print("\n" + "=" * 70)
            print("POST TRAINING LEARNING COMPLETE (WITH ERRORS)")
            print("=" * 70)
            print("[WARNING] Some steps had errors, but workflow completed")

        return success


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Training with monitoring and auto learning")
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Skip training, only run post-learning")
    parser.add_argument(
        "--skip-monitoring",
        action="store_true",
        help="Skip opening monitoring dashboard")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("TRAINING WITH MONITORING AND AUTO LEARNING")
    print("=" * 70)
    print()
    print("This workflow will:")
    print("  1. Start game training with monitoring")
    print("  2. Open monitoring dashboard for real-time statistics")
    print("  3. After training: Run comparison analysis")
    print("  4. Learn from pro gamer replays")
    print("  5. Apply learned parameters")
    print()

    # Initialize monitor
    monitor = TrainingMonitor()

    # Check monitoring server
    if not args.skip_monitoring:
        if monitor.check_monitoring_server():
            print("[SUCCESS] Monitoring server is running")
            monitor.open_monitoring_dashboard()
        else:
            print("[INFO] Monitoring server will start automatically with training")
            print("[INFO] Dashboard will be available at: http://localhost:8000")

    # Start training (if not skipped)
    if not args.skip_training:
        print("\n" + "=" * 70)
        print("STARTING GAME TRAINING")
        print("=" * 70)
        print()
        print("[INFO] Training will start now...")
        print("[INFO] Monitor progress:")
        print("  - Game window: Real-time game visualization")
        print("  - Dashboard: http://localhost:8000")
        print()
        print("[INFO] Press Ctrl+C to stop training and proceed to post-learning")
        print()

        try:
            # Start training
            training_script = PROJECT_ROOT / "run_with_training.py"
            if training_script.exists():
                subprocess.run([sys.executable, str(
                    training_script)], cwd=str(PROJECT_ROOT))
            else:
                print("[ERROR] run_with_training.py not found")
                return 1
        except KeyboardInterrupt:
            print("\n[INFO] Training interrupted by user")
            print("[INFO] Proceeding to post-training learning...")
        except Exception as e:
            print(f"[ERROR] Training failed: {e}")
            return 1

    # Print training summary
    monitor.print_training_summary()

    # Run post-training learning
    post_learning = PostTrainingLearning()
    success = post_learning.run_full_workflow()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
