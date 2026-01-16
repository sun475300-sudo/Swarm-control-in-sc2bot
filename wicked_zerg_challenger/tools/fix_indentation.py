#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 들여쓰기 수정 도구
Python 파일의 들여쓰기를 4 spaces로 통일
"""

import re
import sys
from pathlib import Path


def fix_file_indentation(file_path: Path) -> bool:
    """파일의 들여쓰기를 수정"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed_lines = []
        indent_stack = [0]  # 들여쓰기 레벨 스택
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if not stripped:  # 빈 줄
                fixed_lines.append('\n')
                continue
            
            # 현재 줄의 원래 들여쓰기 계산
            original_indent = len(line) - len(stripped)
            
            # 들여쓰기 키워드 감지
            if stripped.startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except ', 'finally:', 'with ', 'async def ')):
                # 키워드 줄은 이전 레벨과 동일
                current_indent = indent_stack[-1]
                fixed_lines.append(' ' * current_indent + stripped)
                # 다음 줄은 +1 레벨
                if not stripped.endswith(':'):
                    # : 가 없으면 다음 줄은 +1
                    indent_stack.append(current_indent + 4)
            elif stripped.startswith('#'):
                # 주석은 이전 레벨과 동일
                current_indent = indent_stack[-1]
                fixed_lines.append(' ' * current_indent + stripped)
            else:
                # 일반 코드
                current_indent = indent_stack[-1]
                fixed_lines.append(' ' * current_indent + stripped)
                # 줄 끝이 : 이면 다음 줄은 +1
                if stripped.endswith(':'):
                    indent_stack.append(current_indent + 4)
                # 줄이 pass, return, break, continue 등이면 들여쓰기 레벨 유지
                elif stripped.startswith(('pass', 'return', 'break', 'continue', 'raise')):
                    pass  # 레벨 유지
                # 줄이 except, finally 등이면 레벨 감소
                elif stripped.startswith(('except ', 'finally:', 'else:', 'elif ')):
                    if len(indent_stack) > 1:
                        indent_stack.pop()
                    current_indent = indent_stack[-1]
                    fixed_lines[-1] = ' ' * current_indent + stripped
        
        # 파일 쓰기
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        
        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_indentation.py <file1> [file2] ...")
        sys.exit(1)
    
    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if path.exists():
            print(f"Fixing {path}...")
            if fix_file_indentation(path):
                print(f"  ? Fixed {path}")
            else:
                print(f"  ? Failed to fix {path}")
        else:
            print(f"  ? File not found: {path}")
