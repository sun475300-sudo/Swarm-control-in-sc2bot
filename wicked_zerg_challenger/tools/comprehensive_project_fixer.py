# -*- coding: utf-8 -*-
"""
���� ������Ʈ ���� ���� �� ��üȭ ����

����� �䱸���׿� ���� �켱������ ���� �۾� ����:
1. micro_controller.py ���� (import ����)
2. ���� ���� ��Ī ����
3. �ϵ��ڵ� ��� ����
4. ������Ʈ ���� �籸��
5. requirements.txt ����
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class ComprehensiveProjectFixer:
    """���� ������Ʈ ������"""
 
 def __init__(self):
 self.fixes_applied = []
 self.errors_found = []
 
 def fix_micro_controller_imports(self) -> bool:
        """micro_controller.py�� import ���� ����"""
        file_path = PROJECT_ROOT / "micro_controller.py"
 
 if not file_path.exists():
            self.errors_found.append(f"micro_controller.py not found")
 return False
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 # @dataclass import Ȯ��
            if '@dataclass' in content and 'from dataclasses import dataclass' not in content:
 # dataclass import �߰�
                if 'import math' in content:
 content = content.replace(
                        'import math',
                        'import math\nfrom dataclasses import dataclass'
 )
                    self.fixes_applied.append("Added @dataclass import to micro_controller.py")
 
 # SC2 Point2 import Ȯ��
            if 'from sc2.position import Point2' not in content:
 # SC2 import �߰�
                if 'try:' in content and 'SC2_AVAILABLE' in content:
 # try ���� ����
 content = re.sub(
                        r'try:\s*SC2_AVAILABLE = True',
                        'try:\n    from sc2.position import Point2\n    SC2_AVAILABLE = True',
 content
 )
                    self.fixes_applied.append("Added SC2 Point2 import to micro_controller.py")
 
 # ������ ���� ����
 if self.fixes_applied:
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
                    with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(content)
 except Exception:
 pass
 
                with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 
 return True
 
 except Exception as e:
            self.errors_found.append(f"Error fixing micro_controller.py: {e}")
 return False
 
 return False
 
 def add_replay_paths_to_config(self) -> bool:
        """config.py�� ���÷��� ��� ���� �߰�"""
        file_path = PROJECT_ROOT / "config.py"
 
 if not file_path.exists():
            self.errors_found.append("config.py not found")
 return False
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 # �̹� ��� ������ �ִ��� Ȯ��
            if 'REPLAY_DIR' in content or 'REPLAY_SOURCE_DIR' in content:
 return False # �̹� ����
 
 # ��� ���� �߰�
            path_config = """
# ============================================================================
# Replay Path Configuration
# ============================================================================
# IMPROVED: Replay paths moved from hardcoded values to config
# Environment variables take priority, then defaults

REPLAY_DIR = Path(os.environ.get("REPLAY_DIR", "D:/replays"))
REPLAY_SOURCE_DIR = Path(os.environ.get("REPLAY_SOURCE_DIR", REPLAY_DIR / "replays"))
REPLAY_COMPLETED_DIR = REPLAY_SOURCE_DIR / "completed"
REPLAY_ARCHIVE_DIR = Path(os.environ.get("REPLAY_ARCHIVE_DIR", REPLAY_DIR / "archive"))

# Ensure directories exist
REPLAY_DIR.mkdir(parents=True, exist_ok=True)
REPLAY_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
REPLAY_COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
"""
 
 # Config Ŭ���� ���� ���� �߰�
            if 'class Config' in content:
                content = content.replace('class Config', path_config + '\nclass Config')
                self.fixes_applied.append("Added replay path configuration to config.py")
            elif '@dataclass' in content and 'class Config' in content:
 # @dataclass �ٷ� �տ� �߰�
 content = re.sub(
                    r'(@dataclass\(frozen\s*=\s*True\)\s*class Config)',
                    path_config + r'\n\1',
 content
 )
                self.fixes_applied.append("Added replay path configuration to config.py")
 
 # os import Ȯ��
            if 'import os' not in content and 'from pathlib import Path' in content:
 content = content.replace(
                    'from pathlib import Path',
                    'import os\nfrom pathlib import Path'
 )
 
 if self.fixes_applied:
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
                    with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(content)
 except Exception:
 pass
 
                with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 
 return True
 
 except Exception as e:
            self.errors_found.append(f"Error adding paths to config.py: {e}")
 return False
 
 return False
 
 def remove_hardcoded_paths(self) -> int:
        """�ϵ��ڵ��� ��θ� config���� �ε��ϵ��� ����"""
 fixed_count = 0
 
 # �ϵ��ڵ��� ��ΰ� �ִ� ���ϵ�
 target_files = [
            "tools/integrated_pipeline.py",
            "local_training/scripts/replay_build_order_learner.py"
 ]
 
 for file_rel_path in target_files:
 file_path = PROJECT_ROOT / file_rel_path
 if not file_path.exists():
 continue
 
 try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 original_content = content
 
 # D:\replays\replays �ϵ��ڵ� ����
                if 'D:/replays/replays' in content or r'D:\replays\replays' in content:
 # config���� import �߰�
                    if 'from config import' not in content:
 # import ���� ã��
                        import_pattern = r'(^import\s+\w+|^from\s+\w+\s+import)'
 if re.search(import_pattern, content, re.MULTILINE):
 # ������ import �ڿ� �߰�
 last_import = list(re.finditer(import_pattern, content, re.MULTILINE))[-1]
 insert_pos = last_import.end()
 content = (
 content[:insert_pos] +
                                '\nfrom config import REPLAY_SOURCE_DIR, REPLAY_COMPLETED_DIR, REPLAY_ARCHIVE_DIR' +
 content[insert_pos:]
 )
 
 # �ϵ��ڵ��� ��θ� ������ ��ü
 content = re.sub(
                        r'["\']D:[/\\]replays[/\\]replays["\']',
                        'REPLAY_SOURCE_DIR',
 content
 )
 content = re.sub(
                        r'Path\(["\']D:[/\\]replays[/\\]replays["\']\)',
                        'REPLAY_SOURCE_DIR',
 content
 )
 content = re.sub(
                        r'Path\(["\']D:[/\\]replays[/\\]replays[/\\]completed["\']\)',
                        'REPLAY_COMPLETED_DIR',
 content
 )
 content = re.sub(
                        r'["\']D:[/\\]replays[/\\]archive["\']',
                        'REPLAY_ARCHIVE_DIR',
 content
 )
 
 if content != original_content:
                        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
                            with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(original_content)
 except Exception:
 pass
 
                        with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 
 fixed_count += 1
                        self.fixes_applied.append(f"Removed hardcoded paths from {file_rel_path}")
 
 except Exception as e:
                self.errors_found.append(f"Error fixing {file_rel_path}: {e}")
 
 return fixed_count
 
 def check_state_vector_matching(self) -> Dict:
        """���� ���� ��Ī ����"""
 results = {
            "zerg_net_input_size": None,
            "state_collector_found": False,
            "dimension_match": False,
            "issues": []
 }
 
 # zerg_net.py Ȯ��
        zerg_net_path = PROJECT_ROOT / "zerg_net.py"
 if zerg_net_path.exists():
 try:
                with open(zerg_net_path, 'r', encoding='utf-8', errors='replace') as f:
 zerg_net_content = f.read()
 
 # input_size ã��
                input_size_match = re.search(r'input_size\s*[:=]\s*(\d+)', zerg_net_content)
 if input_size_match:
                    results["zerg_net_input_size"] = int(input_size_match.group(1))
 except Exception as e:
                results["issues"].append(f"Error reading zerg_net.py: {e}")
 
 # _collect_state �Լ� ã��
        bot_pro_path = PROJECT_ROOT / "wicked_zerg_bot_pro.py"
 if bot_pro_path.exists():
 try:
                with open(bot_pro_path, 'r', encoding='utf-8', errors='replace') as f:
 bot_content = f.read()
 
                if '_collect_state' in bot_content:
                    results["state_collector_found"] = True
 
 # ���� ���� ���� Ȯ��
 # Self (5) + Enemy (10) = 15 ���� ���
                    if results["zerg_net_input_size"] == 15:
                        results["dimension_match"] = True
                    elif results["zerg_net_input_size"]:
                        results["issues"].append(
                            f"Dimension mismatch: zerg_net expects {results['zerg_net_input_size']}, "
                            f"but should be 15 (Self 5 + Enemy 10)"
 )
 except Exception as e:
                results["issues"].append(f"Error reading wicked_zerg_bot_pro.py: {e}")
 
 return results
 
 def create_requirements_essential(self) -> bool:
        """�ʼ� ���̺귯���� ������ requirements.txt ����"""
        essential_requirements = """# Essential dependencies for StarCraft II Bot
# Core SC2 API
burnysc2==5.0.12

# Neural Network (optional but recommended)
torch>=2.0.0

# Numerical operations
numpy>=1.24.0,<2.0.0

# Logging
loguru>=0.6.0,<0.7.0

# Replay analysis
sc2reader>=1.8.0

# Self-Healing DevOps
google-generativeai>=0.3.0

# Dashboard & API
flask>=3.0.0
fastapi>=0.100.0
uvicorn[standard]>=0.23.0

# Utilities
python-dotenv>=1.0.0
requests>=2.31.0
psutil>=5.9.0
protobuf<=3.20.3
"""
 
        essential_path = PROJECT_ROOT / "requirements_essential.txt"
 try:
            with open(essential_path, 'w', encoding='utf-8') as f:
 f.write(essential_requirements)
            self.fixes_applied.append("Created requirements_essential.txt")
 return True
 except Exception as e:
            self.errors_found.append(f"Error creating requirements_essential.txt: {e}")
 return False


def main():
    """���� �Լ�"""
    print("=" * 70)
    print("���� ������Ʈ ���� ���� �� ��üȭ ����")
    print("=" * 70)
 print()
 
 fixer = ComprehensiveProjectFixer()
 
 # 1. micro_controller.py ����
    print("[1/5] micro_controller.py import ���� ��...")
 if fixer.fix_micro_controller_imports():
        print("  ? micro_controller.py ���� �Ϸ�")
 else:
        print("  ?? micro_controller.py ���� ���ʿ� �Ǵ� ����")
 print()
 
 # 2. config.py�� ��� �߰�
    print("[2/5] config.py�� ���÷��� ��� ���� �߰� ��...")
 if fixer.add_replay_paths_to_config():
        print("  ? config.py ��� ���� �߰� �Ϸ�")
 else:
        print("  ?? config.py ��� ���� �߰� ���ʿ� �Ǵ� ����")
 print()
 
 # 3. �ϵ��ڵ��� ��� ����
    print("[3/5] �ϵ��ڵ��� ��� ���� ��...")
 fixed_count = fixer.remove_hardcoded_paths()
    print(f"  ? {fixed_count}�� ���Ͽ��� �ϵ��ڵ��� ��� ����")
 print()
 
 # 4. ���� ���� ��Ī ����
    print("[4/5] ���� ���� ��Ī ���� ��...")
 state_check = fixer.check_state_vector_matching()
    if state_check["zerg_net_input_size"]:
        print(f"  - zerg_net.py input_size: {state_check['zerg_net_input_size']}")
    if state_check["state_collector_found"]:
        print("  ? _collect_state() �Լ� �߰�")
    if state_check["dimension_match"]:
        print("  ? ���� ���� ���� ��ġ (15����)")
 else:
        print("  ?? ���� ���� ���� ����ġ �Ǵ� Ȯ�� �Ұ�")
        for issue in state_check["issues"]:
            print(f"    - {issue}")
 print()
 
 # 5. �ʼ� requirements.txt ����
    print("[5/5] �ʼ� requirements.txt ���� ��...")
 if fixer.create_requirements_essential():
        print("  ? requirements_essential.txt ���� �Ϸ�")
 else:
        print("  ?? requirements_essential.txt ���� ����")
 print()
 
    print("=" * 70)
    print("���� ������Ʈ ���� �Ϸ�!")
    print("=" * 70)
    print(f"  ����� ����: {len(fixer.fixes_applied)}��")
 if fixer.errors_found:
        print(f"  �߰ߵ� ����: {len(fixer.errors_found)}��")
 print()
 
 if fixer.fixes_applied:
        print("����� ���� ����:")
 for fix in fixer.fixes_applied:
            print(f"  ? {fix}")
 print()
 
 if fixer.errors_found:
        print("�߰ߵ� ����:")
 for error in fixer.errors_found:
            print(f"  ?? {error}")
 print()


if __name__ == "__main__":
 main()