# -*- coding: utf-8 -*-
"""
���ΰ��̸� ���÷��� �н� �� ���� �Ʒ� ���� ��ũ�÷ο�

1. ���ΰ��̸� ���÷��̿��� ������� �н�
2. �н��� ��������� config.py�� ����
3. ���� �Ʒ� ���� (�н��� ������� ����)
4. ���� ���÷��̿� ���ΰ��̸� ���÷��� �� �м�
5. ���� ���� ���� �� �ݺ�
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

def run_command(cmd: List[str], cwd: Path, description: str, timeout: int = 3600) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    print(f"\n{'='*70}")
    print(f"[STEP] {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"[WARNING] Command timed out after {timeout} seconds")
        return False, "Timeout"
    except Exception as e:
        print(f"[ERROR] Failed to run command: {e}")
        return False, str(e)


def check_learned_parameters(project_root: Path) -> Dict[str, Any]:
    """�н��� �Ķ���� Ȯ��"""
    learned_file = project_root / "local_training" / "scripts" / "learned_build_orders.json"
    
    if not learned_file.exists():
        return {}
    
    try:
        with open(learned_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[WARNING] Failed to load learned parameters: {e}")
        return {}


def print_learned_parameters(learned_params: Dict[str, Any]):
    """�н��� �Ķ���� ���"""
    if not learned_params:
        print("[INFO] No learned parameters found")
        return
    
    print(f"\n{'='*70}")
    print("�н��� ������� �Ķ����")
    print(f"{'='*70}")
    
    if isinstance(learned_params, dict):
        for key, value in learned_params.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value}")
            elif isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (int, float)):
                        print(f"    {sub_key}: {sub_value}")
    
    print(f"{'='*70}\n")


def main():
    project_root = Path(__file__).parent.parent
    
    print("=" * 70)
    print("���ΰ��̸� ���÷��� �н� �� ���� �Ʒ� ���� ��ũ�÷ο�")
    print("=" * 70)
    print("\n�� ��ũ�÷ο�� ���� �ܰ踦 �����մϴ�:")
    print("  1. ���ΰ��̸� ���÷��̿��� ������� �н�")
    print("  2. �н��� ��������� config.py�� ����")
    print("  3. ���� �Ʒ� ���� (�н��� ������� ����)")
    print("  4. ���� ���÷��̿� ���ΰ��̸� ���÷��� �� �м�")
    print("  5. ���� ���� ���� �� �ݺ�")
    print("=" * 70)
    
    # Script paths
    replay_learner = project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
    run_training = project_root / "run_with_training.py"
    strategy_audit = project_root / "local_training" / "strategy_audit.py"
    
    # Check if scripts exist
    scripts = {
        "Replay Learner": replay_learner,
        "Run Training": run_training,
        "Strategy Audit": strategy_audit
    }
    
    for name, script in scripts.items():
        if not script.exists():
            print(f"[ERROR] {name} script not found: {script}")
            sys.exit(1)
    
    iteration = 0
    max_iterations = 5  # �ִ� 5ȸ �ݺ�
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n\n{'#'*70}")
        print(f"# ITERATION {iteration} / {max_iterations}")
        print(f"{'#'*70}\n")
        
        # STEP 1: ���ΰ��̸� ���÷��̿��� ������� �н�
        print(f"\n{'='*70}")
        print(f"[STEP 1] ���ΰ��̸� ���÷��̿��� ������� �н� (Iteration {iteration})")
        print(f"{'='*70}\n")
        
        success_learn, output_learn = run_command(
            [sys.executable, str(replay_learner)],
            project_root,
            f"Iteration {iteration} - Pro Gamer Replay Learning",
            timeout=1800  # 30 minutes
        )
        
        if not success_learn:
            print(f"[WARNING] Replay learning failed in iteration {iteration}")
            print("[INFO] Continuing with existing learned parameters...")
        else:
            print(f"[SUCCESS] Replay learning completed for iteration {iteration}")
        
        # �н��� �Ķ���� Ȯ��
        learned_params = check_learned_parameters(project_root)
        if learned_params:
            print_learned_parameters(learned_params)
            print("[INFO] Learned parameters have been automatically applied to config.py")
        else:
            print("[WARNING] No learned parameters found. Using default parameters.")
        
        # STEP 2: ���� �Ʒ� ���� (�н��� ������� ����)
        print(f"\n{'='*70}")
        print(f"[STEP 2] ���� �Ʒ� ���� (�н��� ������� ����) (Iteration {iteration})")
        print(f"{'='*70}\n")
        
        print("[INFO] ���� �Ʒ��� �����մϴ�...")
        print("[INFO] �н��� ��������� �ڵ����� ����˴ϴ�.")
        print("[INFO] Ctrl+C�� ���� �ߴ��� �� �ֽ��ϴ�.")
        print()
        
        success_training, output_training = run_command(
            [sys.executable, str(run_training)],
            project_root,
            f"Iteration {iteration} - Game Training with Learned Build Orders",
            timeout=3600  # 60 minutes
        )
        
        if success_training:
            print(f"[SUCCESS] Game training completed for iteration {iteration}")
        else:
            print(f"[WARNING] Game training had issues in iteration {iteration}")
            print("[INFO] Continuing with comparison analysis...")
        
        # STEP 3: ���� ���÷��̿� ���ΰ��̸� ���÷��� �� �м�
        print(f"\n{'='*70}")
        print(f"[STEP 3] ���� ���÷��̿� ���ΰ��̸� ���÷��� �� �м� (Iteration {iteration})")
        print(f"{'='*70}\n")
        
        success_audit, output_audit = run_command(
            [sys.executable, str(strategy_audit)],
            project_root,
            f"Iteration {iteration} - Bot vs Pro Gamer Comparison Analysis",
            timeout=1800  # 30 minutes
        )
        
        if success_audit:
            print(f"[SUCCESS] Comparison analysis completed for iteration {iteration}")
            
            # �м� ��� ��� ���
            if "critical_issues" in output_audit.lower() or "recommendations" in output_audit.lower():
                print("\n[INFO] Analysis results:")
                print("  - Check local_training/comparison_reports/ for detailed reports")
        else:
            print(f"[WARNING] Comparison analysis had issues in iteration {iteration}")
        
        # STEP 4: ���� ���� Ȯ�� �� ���
        print(f"\n{'='*70}")
        print(f"[STEP 4] ���� ���� Ȯ�� �� ��� (Iteration {iteration})")
        print(f"{'='*70}\n")
        
        # �н��� �Ķ���� ��Ȯ��
        learned_params_after = check_learned_parameters(project_root)
        if learned_params_after:
            print("[INFO] Updated learned parameters:")
            print_learned_parameters(learned_params_after)
        
        # �� ����Ʈ Ȯ��
        comparison_dir = project_root / "local_training" / "comparison_reports"
        if comparison_dir.exists():
            report_files = list(comparison_dir.glob("*.md"))
            if report_files:
                latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
                print(f"[INFO] Latest comparison report: {latest_report}")
        
        print(f"\n{'='*70}")
        print(f"? ITERATION {iteration} / {max_iterations} COMPLETED")
        print(f"{'='*70}")
        print(f"   Replay Learning: {'?' if success_learn else '?'}")
        print(f"   Game Training: {'?' if success_training else '?'}")
        print(f"   Comparison Analysis: {'?' if success_audit else '?'}")
        print(f"{'='*70}")
        
        if iteration < max_iterations:
            print(f"\n[INFO] Waiting 10 seconds before next iteration...")
            time.sleep(10)
    
    # ���� ���
    print(f"\n\n{'#'*70}")
    print("# ��ü ��ũ�÷ο� �Ϸ�")
    print(f"{'#'*70}\n")
    
    # ���� �н��� �Ķ���� Ȯ��
    final_learned_params = check_learned_parameters(project_root)
    if final_learned_params:
        print("���� �н��� ������� �Ķ����:")
        print_learned_parameters(final_learned_params)
    
    print("\n��� Ȯ��:")
    print("  - �н��� �������: local_training/scripts/learned_build_orders.json")
    print("  - �� ����Ʈ: local_training/comparison_reports/")
    print("  - ���� ���: local_training/scripts/training_session_stats.json")
    print("\n�߰� ����:")
    print("  python tools\\show_learning_rate.py")
    print("  python tools\\monitor_training_progress.py")
    print(f"\n{'#'*70}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n??  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n? Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
