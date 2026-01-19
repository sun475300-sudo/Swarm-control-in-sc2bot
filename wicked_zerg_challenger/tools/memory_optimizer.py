# -*- coding: utf-8 -*-
"""
메모리 최적화 도구

메모리 사용량을 최적화하고 캐시 크기를 제한
"""

import re
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Set
from typing import Any
from typing import Union
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class MemoryOptimizer:
    """메모리 최적화기"""

def __init__(self):
    self.optimizations_applied: List[Dict] = []

def add_cache_size_limit(
    self, content: str, file_path: Path) -> Tuple[str, int]:
    """캐시 크기 제한 추가"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 # 캐시 관련 변수 찾기
 cache_patterns = [
    r'cached_\w+',
    r'self\.units',
    r'self\.enemy_units',
    r'self\.structures',
    r'history\s*=',
    r'cache\s*=',
 ]

 for i, line in enumerate(lines):
     modified_lines.append(line)

 # 캐시 변수 선언 찾기
 for pattern in cache_patterns:
     if re.search(pattern, line) and '=' in line and 'self.' in line:
     # 다음 줄이 비어있고 주석이 없으면 캐시 크기 제한 주석 추가
 if i + 1 < len(lines):
     next_line = lines[i + 1].strip()
     if not next_line or next_line.startswith('#'):
     # 이미 주석이 있으면 스킵
 continue

 # 캐시 크기 제한 주석 추가
 indent = len(line) - len(line.lstrip())
     comment = f"{' ' * indent}# MEMORY: Consider limiting cache size (e.g., max 1000 entries)"
 modified_lines.append(comment)
 fix_count += 1
 break

     return '\n'.join(modified_lines), fix_count

def optimize_list_comprehensions(self, content: str, file_path: Path) -> Tuple[str, int]:
    """리스트 컴프리헨션 최적화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 for i, line in enumerate(lines):
     # 큰 리스트 컴프리헨션 찾기
     if re.search(r'\[.*for.*in.*\]', line) and len(line) > 100:
     # 제한 추가 제안 (주석)
     if '[:' not in line and 'limit' not in line.lower():
         pass
     indent = len(line) - len(line.lstrip())
     comment = f"{' ' * indent}# MEMORY: Consider limiting result size (e.g., [:100])"
 modified_lines.append(line)
 modified_lines.append(comment)
 fix_count += 1
 else:
     pass
 modified_lines.append(line)
 else:
     pass
 modified_lines.append(line)

     return '\n'.join(modified_lines), fix_count

def add_gc_hints(self, content: str, file_path: Path) -> Tuple[str, int]:
    """가비지 컬렉션 힌트 추가"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 # 큰 데이터 구조를 사용하는 함수 끝에 GC 힌트 추가
 in_large_function = False
 function_indent = 0

 for i, line in enumerate(lines):
     # 함수 정의 찾기
     if re.match(r'^\s*def\s+\w+', line):
         pass
     in_large_function = False
 function_indent = len(line) - len(line.lstrip())

 # 함수 내부에 큰 데이터 구조 사용 확인
 j = i + 1
 has_large_data = False
 while j < len(lines) and j < i + 50: # 함수 시작 50줄만 확인
     if re.search(r'\.units\.|\.enemy_units\.|list\(|dict\(|set\(', lines[j]):
         pass
     has_large_data = True
 break
 if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= function_indent:
     break
 j += 1

 if has_large_data:
     in_large_function = True

 modified_lines.append(line)
 continue

 # 함수 끝 확인
 if in_large_function:
     current_indent = len(line) - len(line.lstrip())
     if line.strip() and current_indent <= function_indent and not line.strip().startswith('#'):
     # 함수 끝에 GC 힌트 추가
     gc_hint = f"{' ' * (function_indent + 4)}# MEMORY: Consider gc.collect() if memory usage is high"
 modified_lines.append(gc_hint)
 fix_count += 1
 in_large_function = False

 modified_lines.append(line)

     return '\n'.join(modified_lines), fix_count


def optimize_file_memory(file_path: Path) -> Dict:
    """파일 메모리 최적화"""
 optimizer = MemoryOptimizer()

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
     with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()

 original_content = content

 # 캐시 크기 제한 추가
 content, cache_fixes = optimizer.add_cache_size_limit(content, file_path)

 # 리스트 컴프리헨션 최적화
 content, list_fixes = optimizer.optimize_list_comprehensions(content, file_path)

 # GC 힌트 추가
 content, gc_fixes = optimizer.add_gc_hints(content, file_path)

 total_fixes = cache_fixes + list_fixes + gc_fixes

 if total_fixes > 0:
     # 백업 생성
     backup_path = file_path.with_suffix(file_path.suffix + '.bak')
     with open(backup_path, 'w', encoding='utf-8') as f:
 f.write(original_content)

 # 수정된 내용 저장
     with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)

 return {
     "success": True,
     "cache_fixes": cache_fixes,
     "list_fixes": list_fixes,
     "gc_fixes": gc_fixes,
     "total_fixes": total_fixes
 }
 else:
     pass
 return {
     "success": False,
     "total_fixes": 0
 }

 except Exception as e:
     return {
     "success": False,
     "error": str(e)
 }


def main():
    """메인 함수"""
    print("=" * 70)
    print("메모리 최적화 도구")
    print("=" * 70)
 print()

 # 주요 파일 목록
 main_files = [
    "intel_manager.py",
    "wicked_zerg_bot_pro.py",
    "production_manager.py",
    "combat_manager.py",
    "economy_manager.py"
 ]

 total_cache_fixes = 0
 total_list_fixes = 0
 total_gc_fixes = 0

    print("메모리 최적화 적용 중...")
 for main_file in main_files:
     file_path = PROJECT_ROOT / main_file
 if file_path.exists():
     print(f"  - {main_file}")
 result = optimize_file_memory(file_path)

     if result.get("success"):
         pass
     print(f"    캐시 제한: {result['cache_fixes']}개")
     print(f"    리스트 최적화: {result['list_fixes']}개")
     print(f"    GC 힌트: {result['gc_fixes']}개")
     total_cache_fixes += result['cache_fixes']
     total_list_fixes += result['list_fixes']
     total_gc_fixes += result['gc_fixes']
     elif result.get("error"):
         pass
     print(f"    오류: {result['error']}")
 else:
     print(f"    변경 사항 없음")

 print()
    print("=" * 70)
    print("메모리 최적화 완료!")
    print(f"  캐시 제한: {total_cache_fixes}개")
    print(f"  리스트 최적화: {total_list_fixes}개")
    print(f"  GC 힌트: {total_gc_fixes}개")
    print("=" * 70)


if __name__ == "__main__":
    main()
