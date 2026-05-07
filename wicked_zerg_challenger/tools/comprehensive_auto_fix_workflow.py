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

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger("ComprehensiveAutoFixWorkflow")

def run_command(cmd: List[str], cwd: Path, description: str, timeout: int = 3600) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    logger.info(f"\n{'='*70}")
    logger.info(f"{description}")
    logger.info(f"{'='*70}")
    logger.info(f"Command: {' '.join(cmd)}")
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
            logger.info(result.stdout)
        if result.stderr:
            logger.info(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout} seconds")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        return False, str(e)


def fix_errors_iteratively(project_root: Path, max_iterations: int = 10) -> bool:
    """���� ������ �ݺ������� ���� (������ ���� �۵��� ������)"""
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 1: ���� ���� �� ���� ���� (�ݺ�)")
    logger.info(f"{'#'*70}\n")
    
    auto_error_fixer = project_root / "tools" / "auto_error_fixer.py"
    logic_checker = project_root / "tools" / "logic_checker.py"
    
    for iteration in range(1, max_iterations + 1):
        logger.info(f"\n[ITERATION {iteration}/{max_iterations}] ���� ���� ��...")
        
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
            logger.info(f"\n[SUCCESS] ��� ������ ���װ� �����Ǿ����ϴ�! (Iteration {iteration})")
            return True
        
        if iteration < max_iterations:
            logger.info(f"\n[INFO] ������ �����ֽ��ϴ�. ��� ���� ��... (Iteration {iteration}/{max_iterations})")
            time.sleep(2)
    
    logger.warning(f"\n[WARNING] �ִ� �ݺ� Ƚ��({max_iterations})�� �����߽��ϴ�.")
    return False


def main():
    project_root = Path(__file__).parent.parent
    
    logger.info("=" * 70)
    logger.info("���� �ڵ� ���� �� �Ʒ� ��ũ�÷ο�")
    logger.info("=" * 70)
    logger.info("\n�� ��ũ�÷ο�� ���� �ܰ踦 �����մϴ�:")
    logger.info("  1. ���� ���� �� ���� ���� (�ݺ�)")
    logger.info("  2. ���� �˻�")
    logger.info("  3. �ڵ� ��Ÿ�� ����ȭ")
    logger.info("  4. ���÷��� �н� ���� �� ��ü ���� �˻�")
    logger.info("  5. ���а˻� �� ���� �н� ����")
    logger.info("  6. ������ ���� �˻� �� ���� Ȯ�� �� ���� ���� �� ���� Ȯ�� �� ���� ����")
    logger.info("  7. ���÷��� �� �н� ���α׷� ���� �� ������ ���� �� �Ʒ� ����")
    logger.info("  8. ���÷��� �н� ������ �� �м� �� �н� ����")
    logger.info("=" * 70)
    
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
            logger.error(f"{name} script not found: {script}")
            sys.exit(1)
    
    # PHASE 1: ���� ���� �� ���� ���� (�ݺ�)
    if not fix_errors_iteratively(project_root, max_iterations=10):
        logger.warning("�Ϻ� ������ �������� �� �ֽ��ϴ�. ��� �����մϴ�...")
    
    # PHASE 2: ���� �˻�
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 2: ���� �˻�")
    logger.info(f"{'#'*70}\n")
    
    success_logic, output_logic = run_command(
        [sys.executable, str(logic_checker), "--all"],
        project_root,
        "Logic Check",
        timeout=600
    )
    
    # PHASE 3: �ڵ� ��Ÿ�� ����ȭ
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 3: �ڵ� ��Ÿ�� ����ȭ")
    logger.info(f"{'#'*70}\n")
    
    success_style, _ = run_command(
        [sys.executable, str(code_quality_improver), "--all"],
        project_root,
        "Code Style Unification",
        timeout=600
    )
    
    # PHASE 4: ���÷��� �н� ���� �� ��ü ���� �˻�
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 4: ���÷��� �н� ���� �� ��ü ���� �˻�")
    logger.info(f"{'#'*70}\n")
    
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
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 5: ���а˻� �� ���� �н� ����")
    logger.info(f"{'#'*70}\n")
    
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
    logger.info("\n[INFO] ���� �н��� �����մϴ�...")
    logger.info("������ ���� �۵��ϴ��� Ȯ���ϼ���.")
    logger.info("Ctrl+C�� ���� �ߴ��� �� �ֽ��ϴ�.")
    success_training, _ = run_command(
        [sys.executable, str(run_training)],
        project_root,
        "Game Training",
        timeout=3600  # 60 minutes
    )
    
    # PHASE 6: ������ ���� �˻� �� ���� Ȯ�� �� ���� ���� �� ���� Ȯ�� �� ���� ����
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 6: ���� �˻� �� ���� Ȯ�� �� ���� ���� �� ���� Ȯ�� �� ���� ����")
    logger.info(f"{'#'*70}\n")
    
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
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 7: ���÷��� �� �н� ���α׷� ���� �� ������ ���� �� �Ʒ� ����")
    logger.info(f"{'#'*70}\n")
    
    # 7-1. ���÷��� �� �н�
    success_replay2, _ = run_command(
        [sys.executable, str(replay_learner)],
        project_root,
        "Replay Comparison Learning",
        timeout=1800
    )
    
    # 7-2. ������ ���� �� �Ʒ� ����
    if success_replay2:
        logger.info("\n[INFO] �н��� �����Ͱ� �ڵ� ����Ǿ����ϴ�.")
        logger.info("�߰� �Ʒ��� �����մϴ�...")
        
        success_training2, _ = run_command(
            [sys.executable, str(run_training)],
            project_root,
            "Additional Training After Replay Learning",
            timeout=3600
        )
    
    # PHASE 8: ���÷��� �н� ������ �� �м� �� �н� ����
    logger.info(f"\n{'#'*70}")
    logger.info("# PHASE 8: ���÷��� �н� ������ �� �м� �� �н� ����")
    logger.info(f"{'#'*70}\n")
    
    success_audit, _ = run_command(
        [sys.executable, str(strategy_audit)],
        project_root,
        "Replay Learning Data Comparison Analysis",
        timeout=1800
    )
    
    # ���� ���
    logger.info(f"\n\n{'#'*70}")
    logger.info("# ��ü ��ũ�÷ο� �Ϸ�")
    logger.info(f"{'#'*70}\n")
    
    logger.info("���� ���:")
    logger.error(f"  - ���� ����: {'?' if success_error_fix else '?'}")
    logger.info(f"  - �ڵ� ��Ÿ�� ����ȭ: {'?' if success_style else '?'}")
    logger.info(f"  - ���� �˻�: {'?' if success_logic else '?'}")
    logger.info(f"  - ���÷��� �н�: {'?' if success_replay1 else '?'}")
    logger.info(f"  - ���� �н�: {'?' if success_training else '?'}")
    logger.info(f"  - ���÷��� �� �н�: {'?' if success_replay2 else '?'}")
    logger.info(f"  - �� �м�: {'?' if success_audit else '?'}")
    
    logger.info(f"\n{'#'*70}")


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
