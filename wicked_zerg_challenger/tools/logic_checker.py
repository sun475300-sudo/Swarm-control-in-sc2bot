# -*- coding: utf-8 -*-
"""
���� �˻� ����

�ҽ��ڵ��� ���� ����, �ߺ� ����, ���� ������ �˻�
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Any, Set
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent


class LogicChecker:
    """���� �˻��"""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []

    def check_overlapping_commands(self, file_path: Path) -> List[Dict[str, Any]]:
        """�ߺ� ���� �˻� (���� ������ ��ġ�� ���)"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.splitlines()

            # ���� �Լ� ȣ���� �������� ���� �� �������� �˻�
            function_calls: Dict[str, List[int]] = defaultdict(list)

            try:
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            func_name = f"{ast.unparse(node.func)}"
                            function_calls[func_name].append(node.lineno)
            except SyntaxError:
                pass

            # ���� �Լ��� 3�� �̻� ���� ȣ��Ǵ� ���
            for func_name, line_numbers in function_calls.items():
                if len(line_numbers) >= 3:
                    # ���ӵ� ȣ������ Ȯ��
                    consecutive = []
                    for i, line_num in enumerate(line_numbers):
                        if i == 0 or line_num - line_numbers[i-1] <= 5:  # 5�� �̳�
                            consecutive.append(line_num)
                        else:
                            if len(consecutive) >= 3:
                                issues.append({
                                    "type": "overlapping_commands",
                                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                                    "function": func_name,
                                    "lines": consecutive,
                                    "message": f"���� �Լ� '{func_name}'�� {len(consecutive)}�� ���� ȣ���"
                                })
                            consecutive = [line_num]

            return issues

        except Exception as e:
            return [{"type": "error", "file": str(file_path), "message": str(e)}]

    def check_duplicate_logic(self, file_path: Path) -> List[Dict[str, Any]]:
        """�ߺ� ���� �˻�"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # ���� �ڵ� ������ �ݺ��Ǵ��� �˻� (������ ����)
            lines = content.splitlines()
            line_hashes: Dict[str, List[int]] = defaultdict(list)

            # 5�� ������ �ؽ� ����
            for i in range(len(lines) - 4):
                block = '\n'.join(lines[i:i+5])
                block_hash = hash(block.strip())
                line_hashes[block_hash].append(i + 1)

            # ���� ������ 2�� �̻� ������ ���
            for block_hash, line_numbers in line_hashes.items():
                if len(line_numbers) >= 2:
                    issues.append({
                        "type": "duplicate_logic",
                        "file": str(file_path.relative_to(PROJECT_ROOT)),
                        "lines": line_numbers,
                        "message": f"�ߺ��� �ڵ� ���� �߰� (����: {line_numbers})"
                    })

            return issues

        except Exception as e:
            return [{"type": "error", "file": str(file_path), "message": str(e)}]

    def check_bug_patterns(self, file_path: Path) -> List[Dict[str, Any]]:
        """���� ���� �˻�"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.splitlines()

            # ���� 1: None üũ ���� �޼��� ȣ��
            for i, line in enumerate(lines, 1):
                if re.search(r'self\.\w+\.\w+\(', line) and 'if' not in line[:20]:
                    if 'None' not in line and 'is not None' not in line:
                        issues.append({
                            "type": "bug_pattern",
                            "file": str(file_path.relative_to(PROJECT_ROOT)),
                            "line": i,
                            "message": f"None üũ ���� �޼��� ȣ��: {line.strip()[:50]}"
                        })

            # ���� 2: await ���� async �Լ� ȣ��
            for i, line in enumerate(lines, 1):
                if 'async def' in content:
                    # async �Լ� ȣ�⿡ await�� ������ �˻� (������ ����)
                    if re.search(r'\b\w+\(.*\)', line) and 'await' not in line:
                        # �̰� ��Ȯ���� �����Ƿ� �����
                        pass

            # ���� 3: ���� ó�� ���� ����/��Ʈ��ũ �۾�
            for i, line in enumerate(lines, 1):
                if any(keyword in line for keyword in ['open(', 'requests.', 'urllib.']):
                    # ���ʿ� try�� �ִ��� Ȯ�� (������ ����)
                    context = '\n'.join(lines[max(0, i-10):i])
                    if 'try:' not in context:
                        issues.append({
                            "type": "bug_pattern",
                            "file": str(file_path.relative_to(PROJECT_ROOT)),
                            "line": i,
                            "message": f"���� ó�� ���� ����/��Ʈ��ũ �۾�: {line.strip()[:50]}"
                        })

            return issues

        except Exception as e:
            return [{"type": "error", "file": str(file_path), "message": str(e)}]

    def scan_all(self, target_files: List[Path] = None) -> Dict[str, Any]:
        """��ü ��ĵ"""
        if target_files is None:
            target_files = []
            for root, dirs, files in os.walk(PROJECT_ROOT):
                dirs[:] = [d for d in dirs if d not in {
                    '__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models'}]
                for file in files:
                    if file.endswith('.py'):
                        target_files.append(Path(root) / file)

        all_issues = {
            "overlapping_commands": [],
            "duplicate_logic": [],
            "bug_patterns": [],
            "total_files": len(target_files)
        }

        for file_path in target_files:
            overlapping = self.check_overlapping_commands(file_path)
            duplicate = self.check_duplicate_logic(file_path)
            bugs = self.check_bug_patterns(file_path)

            all_issues["overlapping_commands"].extend(overlapping)
            all_issues["duplicate_logic"].extend(duplicate)
            all_issues["bug_patterns"].extend(bugs)

        return all_issues


def main():
    """���� �Լ�"""
    import argparse

    parser = argparse.ArgumentParser(description="���� �˻� ����")
    parser.add_argument("--file", help="Ư�� ���ϸ� �˻�")
    parser.add_argument("--all", action="store_true", help="��� ���� �˻�")

    args = parser.parse_args()

    print("=" * 70)
    print("���� �˻� ����")
    print("=" * 70)
    print()

    checker = LogicChecker()

    if args.file:
        file_path = PROJECT_ROOT / args.file
        if file_path.exists():
            overlapping = checker.check_overlapping_commands(file_path)
            duplicate = checker.check_duplicate_logic(file_path)
            bugs = checker.check_bug_patterns(file_path)

            print(f"[FILE] {args.file}")
            print(f"  �ߺ� ����: {len(overlapping)}��")
            print(f"  �ߺ� ����: {len(duplicate)}��")
            print(f"  ���� ����: {len(bugs)}��")

            if overlapping:
                print("\n�ߺ� ����:")
                for issue in overlapping:
                    print(f"  - {issue['message']}")

            if duplicate:
                print("\n�ߺ� ����:")
                for issue in duplicate:
                    print(f"  - {issue['message']}")

            if bugs:
                print("\n���� ����:")
                for issue in bugs:
                    print(f"  - {issue['message']}")

        else:
            print(f"[ERROR] File not found: {args.file}")
    elif args.all:
        print("��� ���� ���� �˻� ��...")
        results = checker.scan_all()
        print(f"\n�˻� �Ϸ�: {results['total_files']}�� ����")
        print(f"�ߺ� ����: {len(results['overlapping_commands'])}��")
        print(f"�ߺ� ����: {len(results['duplicate_logic'])}��")
        print(f"���� ����: {len(results['bug_patterns'])}��")

        if results['overlapping_commands']:
            print("\n�ߺ� ���� �߰�:")
            for issue in results['overlapping_commands'][:10]:
                print(f"  - {issue['file']}: {issue['message']}")

        if results['duplicate_logic']:
            print("\n�ߺ� ���� �߰�:")
            for issue in results['duplicate_logic'][:10]:
                print(f"  - {issue['file']}: {issue['message']}")

        if results['bug_patterns']:
            print("\n���� ���� �߰�:")
            for issue in results['bug_patterns'][:10]:
                print(f"  - {issue['file']}: {issue['message']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
