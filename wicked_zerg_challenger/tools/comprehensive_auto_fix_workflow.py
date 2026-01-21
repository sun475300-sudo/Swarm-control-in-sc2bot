# -*- coding: utf-8 -*-
"""
���� �ڵ� ���� �� �Ʒ� ��ũ�÷ο�

1. ���� ���� �� ���� ���� (�ݺ�)
2. ���� �˻�
3. �ڵ� ��Ÿ�� ����ȭ
4. ���÷��� �н� ���� �� ��ü ���� �˻�
5. ���а˻� �� ���� �н� ����
6. ������ ���� �˻� �� ���� Ȯ�� �� ���� ���� �� ���� Ȯ�� �� ���� ����
7. ���÷��� �� �н� ���α׷� ���� �� ������ ���� �� �Ʒ� ����
8. ���÷��� �н� ������ �� �м� �� �н� ����
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any

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


def fix_errors_iteratively(project_root: Path, max_iterations: int = 10) -> bool:
    """���� ������ �ݺ������� ���� (������ ���� �۵��� ������)"""
    print(f"\n{'#'*70}")
    print("# PHASE 1: ���� ���� �� ���� ���� (�ݺ�)")
    print(f"{'#'*70}\n")
    
    auto_error_fixer = project_root / "tools" / "auto_error_fixer.py"
    logic_checker = project_root / "tools" / "logic_checker.py"
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n[ITERATION {iteration}/{max_iterations}] ���� ���� ��...")
        
        # 1. �ڵ� ���� ����
        success1, _ = run_command(
            [sys.executable, str(auto_error_fixer), "--all"],
            project_root,
            f"Iteration {iteration} - Auto Error Fixing",
            timeout=600
        )
        
        # 2. ���� �˻�
        success2, output2 = run_command(
            [sys.executable, str(logic_checker), "--all"],
            project_root,
            f"Iteration {iteration} - Logic Check",
            timeout=600
        )
        
        # ���� �˻� ��� �м�
        if "�ߺ� ����: 0��" in output2 and "�ߺ� ����: 0��" in output2 and "���� ����: 0��" in output2:
            print(f"\n[SUCCESS] ��� ������ ���װ� �����Ǿ����ϴ�! (Iteration {iteration})")
            return True
        
        if iteration < max_iterations:
            print(f"\n[INFO] ������ �����ֽ��ϴ�. ��� ���� ��... (Iteration {iteration}/{max_iterations})")
            time.sleep(2)
    
    print(f"\n[WARNING] �ִ� �ݺ� Ƚ��({max_iterations})�� �����߽��ϴ�.")
    return False


def main():
    project_root = Path(__file__).parent.parent
    
    print("=" * 70)
    print("���� �ڵ� ���� �� �Ʒ� ��ũ�÷ο�")
    print("=" * 70)
    print("\n�� ��ũ�÷ο�� ���� �ܰ踦 �����մϴ�:")
    print("  1. ���� ���� �� ���� ���� (�ݺ�)")
    print("  2. ���� �˻�")
    print("  3. �ڵ� ��Ÿ�� ����ȭ")
    print("  4. ���÷��� �н� ���� �� ��ü ���� �˻�")
    print("  5. ���а˻� �� ���� �н� ����")
    print("  6. ������ ���� �˻� �� ���� Ȯ�� �� ���� ���� �� ���� Ȯ�� �� ���� ����")
    print("  7. ���÷��� �� �н� ���α׷� ���� �� ������ ���� �� �Ʒ� ����")
    print("  8. ���÷��� �н� ������ �� �м� �� �н� ����")
    print("=" * 70)
    
    # Script paths
    auto_error_fixer = project_root / "tools" / "auto_error_fixer.py"
    code_quality_improver = project_root / "tools" / "code_quality_improver.py"
    logic_checker = project_root / "tools" / "logic_checker.py"
    run_training = project_root / "run_with_training.py"
    replay_learner = project_root / "local_training" / "scripts" / "replay_build_order_learner.py"
    strategy_audit = project_root / "local_training" / "strategy_audit.py"
    
    # Check if scripts exist
    scripts = {
        "Auto Error Fixer": auto_error_fixer,
        "Code Quality Improver": code_quality_improver,
        "Logic Checker": logic_checker,
        "Run Training": run_training,
        "Replay Learner": replay_learner,
        "Strategy Audit": strategy_audit
    }
    
    for name, script in scripts.items():
        if not script.exists():
            print(f"[ERROR] {name} script not found: {script}")
            sys.exit(1)
    
    # PHASE 1: ���� ���� �� ���� ���� (�ݺ�)
    if not fix_errors_iteratively(project_root, max_iterations=10):
        print("[WARNING] �Ϻ� ������ �������� �� �ֽ��ϴ�. ��� �����մϴ�...")
    
    # PHASE 2: ���� �˻�
    print(f"\n{'#'*70}")
    print("# PHASE 2: ���� �˻�")
    print(f"{'#'*70}\n")
    
    success_logic, output_logic = run_command(
        [sys.executable, str(logic_checker), "--all"],
        project_root,
        "Logic Check",
        timeout=600
    )
    
    # PHASE 3: �ڵ� ��Ÿ�� ����ȭ
    print(f"\n{'#'*70}")
    print("# PHASE 3: �ڵ� ��Ÿ�� ����ȭ")
    print(f"{'#'*70}\n")
    
    success_style, _ = run_command(
        [sys.executable, str(code_quality_improver), "--all"],
        project_root,
        "Code Style Unification",
        timeout=600
    )
    
    # PHASE 4: ���÷��� �н� ���� �� ��ü ���� �˻�
    print(f"\n{'#'*70}")
    print("# PHASE 4: ���÷��� �н� ���� �� ��ü ���� �˻�")
    print(f"{'#'*70}\n")
    
    # 4-1. ��ü ���� �˻�
    success_logic2, _ = run_command(
        [sys.executable, str(logic_checker), "--all"],
        project_root,
        "Full Logic Check Before Replay Learning",
        timeout=600
    )
    
    # 4-2. ���÷��� �н�
    success_replay1, _ = run_command(
        [sys.executable, str(replay_learner)],
        project_root,
        "Replay Build Order Learning",
        timeout=1800
    )
    
    # PHASE 5: ���а˻� �� ���� �н� ����
    print(f"\n{'#'*70}")
    print("# PHASE 5: ���а˻� �� ���� �н� ����")
    print(f"{'#'*70}\n")
    
    # 5-1. ���а˻� (���� ���� + �ڵ� ǰ��)
    success_precise1, _ = run_command(
        [sys.executable, str(auto_error_fixer), "--all"],
        project_root,
        "Precise Check - Error Fixing",
        timeout=600
    )
    
    success_precise2, _ = run_command(
        [sys.executable, str(code_quality_improver), "--all"],
        project_root,
        "Precise Check - Code Quality",
        timeout=600
    )
    
    # 5-2. ���� �н� ����
    print(f"\n[INFO] ���� �н��� �����մϴ�...")
    print(f"[INFO] ������ ���� �۵��ϴ��� Ȯ���ϼ���.")
    print(f"[INFO] Ctrl+C�� ���� �ߴ��� �� �ֽ��ϴ�.")
    print()
    
    success_training, _ = run_command(
        [sys.executable, str(run_training)],
        project_root,
        "Game Training",
        timeout=3600  # 60 minutes
    )
    
    # PHASE 6: ������ ���� �˻� �� ���� Ȯ�� �� ���� ���� �� ���� Ȯ�� �� ���� ����
    print(f"\n{'#'*70}")
    print("# PHASE 6: ���� �˻� �� ���� Ȯ�� �� ���� ���� �� ���� Ȯ�� �� ���� ����")
    print(f"{'#'*70}\n")
    
    # 6-1. ���� �˻�
    success_logic3, output_logic3 = run_command(
        [sys.executable, str(logic_checker), "--all"],
        project_root,
        "Post-Training Logic Check",
        timeout=600
    )
    
    # 6-2. ���� Ȯ�� �� ����
    success_error_fix, _ = run_command(
        [sys.executable, str(auto_error_fixer), "--all"],
        project_root,
        "Post-Training Error Fixing",
        timeout=600
    )
    
    # 6-3. ���� Ȯ�� �� ���� (���� �˻� �ٽ�)
    success_bug_fix, _ = run_command(
        [sys.executable, str(logic_checker), "--all"],
        project_root,
        "Post-Training Bug Check",
        timeout=600
    )
    
    # PHASE 7: ���÷��� �� �н� ���α׷� ���� �� ������ ���� �� �Ʒ� ����
    print(f"\n{'#'*70}")
    print("# PHASE 7: ���÷��� �� �н� ���α׷� ���� �� ������ ���� �� �Ʒ� ����")
    print(f"{'#'*70}\n")
    
    # 7-1. ���÷��� �� �н�
    success_replay2, _ = run_command(
        [sys.executable, str(replay_learner)],
        project_root,
        "Replay Comparison Learning",
        timeout=1800
    )
    
    # 7-2. ������ ���� �� �Ʒ� ����
    if success_replay2:
        print(f"\n[INFO] �н��� �����Ͱ� �ڵ� ����Ǿ����ϴ�.")
        print(f"[INFO] �߰� �Ʒ��� �����մϴ�...")
        
        success_training2, _ = run_command(
            [sys.executable, str(run_training)],
            project_root,
            "Additional Training After Replay Learning",
            timeout=3600
        )
    
    # PHASE 8: ���÷��� �н� ������ �� �м� �� �н� ����
    print(f"\n{'#'*70}")
    print("# PHASE 8: ���÷��� �н� ������ �� �м� �� �н� ����")
    print(f"{'#'*70}\n")
    
    success_audit, _ = run_command(
        [sys.executable, str(strategy_audit)],
        project_root,
        "Replay Learning Data Comparison Analysis",
        timeout=1800
    )
    
    # ���� ���
    print(f"\n\n{'#'*70}")
    print("# ��ü ��ũ�÷ο� �Ϸ�")
    print(f"{'#'*70}\n")
    
    print("���� ���:")
    print(f"  - ���� ����: {'?' if success_error_fix else '?'}")
    print(f"  - �ڵ� ��Ÿ�� ����ȭ: {'?' if success_style else '?'}")
    print(f"  - ���� �˻�: {'?' if success_logic else '?'}")
    print(f"  - ���÷��� �н�: {'?' if success_replay1 else '?'}")
    print(f"  - ���� �н�: {'?' if success_training else '?'}")
    print(f"  - ���÷��� �� �н�: {'?' if success_replay2 else '?'}")
    print(f"  - �� �м�: {'?' if success_audit else '?'}")
    
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
