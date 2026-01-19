# -*- coding: utf-8 -*-
"""
소스코드 종합 최적화 도구

성능, 메모리, 코드 품질을 종합적으로 최적화
"""

import ast
import re
import subprocess
import sys
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Set
from typing import Any
from typing import Union
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class SourceCodeOptimizer:
    """소스코드 최적화기"""

def __init__(self):
    self.optimizations = []

def optimize_loops(self, content: str, file_path: Path) -> Tuple[str, int]:
    """루프 최적화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 for i, line in enumerate(lines):
     # list() 변환 최적화
 # list(units) -> units (이미 Units 객체는 iterable)
     if re.search(r'list\(.*\.units\)|list\(.*\.structures\)|list\(.*\.enemy_units\)', line):
     # .exists 체크 후 사용 제안
 indent = len(line) - len(line.lstrip())
     comment = f"{' ' * indent}# OPTIMIZE: Consider using .exists check before list() conversion"
 modified_lines.append(line)
     if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('#'):
         pass
     modified_lines.append(comment)
 fix_count += 1
 else:
     pass
 modified_lines.append(line)
 else:
     pass
 modified_lines.append(line)

     return '\n'.join(modified_lines), fix_count

def optimize_api_calls(self, content: str, file_path: Path) -> Tuple[str, int]:
    """API 호출 최적화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 for i, line in enumerate(lines):
     # 직접 bot.units() 호출을 캐시 사용으로 변경 제안
     if re.search(r'\bbot\.units\(|\bself\.units\(|\bb\.units\(', line) and 'cached' not in line.lower():
         pass
     indent = len(line) - len(line.lstrip())
     comment = f"{' ' * indent}# OPTIMIZE: Use intel.cached_* instead of direct units() call"
 modified_lines.append(line)
     if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('#'):
         pass
     modified_lines.append(comment)
 fix_count += 1
 else:
     pass
 modified_lines.append(line)
 else:
     pass
 modified_lines.append(line)

     return '\n'.join(modified_lines), fix_count

def optimize_conditionals(self, content: str, file_path: Path) -> Tuple[str, int]:
    """조건문 최적화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 for i, line in enumerate(lines):
     # 중첩된 if 문 최적화 제안
     if line.count('if ') > 1 and 'elif' not in line:
         pass
     indent = len(line) - len(line.lstrip())
     comment = f"{' ' * indent}# OPTIMIZE: Consider combining conditions or using early return"
 modified_lines.append(line)
     if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('#'):
         pass
     modified_lines.append(comment)
 fix_count += 1
 else:
     pass
 modified_lines.append(line)
 else:
     pass
 modified_lines.append(line)

     return '\n'.join(modified_lines), fix_count

def remove_unused_imports(self, content: str, file_path: Path) -> Tuple[str, int]:
    """사용하지 않는 import 제거"""
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
     tree = ast.parse(content)
 imports = set()
 used_names = set()

 # Import 수집
 for node in ast.walk(tree):
     if isinstance(node, ast.Import):
         for alias in node.names:
             imports.add(alias.name.split('.')[0])
 elif isinstance(node, ast.ImportFrom):
     if node.module:
         imports.add(node.module.split('.')[0])

 # 사용된 이름 수집
 for node in ast.walk(tree):
     if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
         used_names.add(node.id)

 # 사용하지 않는 import 찾기
 unused = imports - used_names

 if unused:
     lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 for line in lines:
     # 사용하지 않는 import 라인 제거
 should_remove = False
 for imp in unused:
     if re.match(rf'^\s*(import\s+{imp}|from\s+{imp})', line):
         pass
     should_remove = True
 fix_count += 1
 break

 if not should_remove:
     modified_lines.append(line)

     return '\n'.join(modified_lines), fix_count
 except Exception:
     pass

 return content, 0

def optimize_string_operations(self, content: str, file_path: Path) -> Tuple[str, int]:
    """문자열 연산 최적화"""
 lines = content.splitlines()
 modified_lines = []
 fix_count = 0

 for i, line in enumerate(lines):
     # 문자열 연결 최적화 (f-string 사용 제안)
     if re.search(r'["\'].*["\']\s*\+\s*["\']|["\'].*["\']\s*\+\s*\w+', line):
         pass
     indent = len(line) - len(line.lstrip())
     comment = f"{' ' * indent}# OPTIMIZE: Consider using f-string for string concatenation"
 modified_lines.append(line)
     if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('#'):
         pass
     modified_lines.append(comment)
 fix_count += 1
 else:
     pass
 modified_lines.append(line)
 else:
     pass
 modified_lines.append(line)

     return '\n'.join(modified_lines), fix_count


def optimize_source_code(file_path: Path) -> Dict:
    """소스코드 최적화"""
 optimizer = SourceCodeOptimizer()

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

 # 루프 최적화
 content, loop_fixes = optimizer.optimize_loops(content, file_path)

 # API 호출 최적화
 content, api_fixes = optimizer.optimize_api_calls(content, file_path)

 # 조건문 최적화
 content, cond_fixes = optimizer.optimize_conditionals(content, file_path)

 # 사용하지 않는 import 제거
 content, import_fixes = optimizer.remove_unused_imports(content, file_path)

 # 문자열 연산 최적화
 content, string_fixes = optimizer.optimize_string_operations(content, file_path)

 total_fixes = loop_fixes + api_fixes + cond_fixes + import_fixes + string_fixes

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
     "loop_fixes": loop_fixes,
     "api_fixes": api_fixes,
     "cond_fixes": cond_fixes,
     "import_fixes": import_fixes,
     "string_fixes": string_fixes,
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
    print("소스코드 종합 최적화 도구")
    print("=" * 70)
 print()

 # 주요 파일 목록
 main_files = [
    "wicked_zerg_bot_pro.py",
    "production_manager.py",
    "combat_manager.py",
    "economy_manager.py",
    "intel_manager.py",
    "scouting_system.py",
    "queen_manager.py",
    "unit_factory.py",
    "zerg_net.py"
 ]

 total_loop_fixes = 0
 total_api_fixes = 0
 total_cond_fixes = 0
 total_import_fixes = 0
 total_string_fixes = 0

    print("소스코드 최적화 적용 중...")
 for main_file in main_files:
     file_path = PROJECT_ROOT / main_file
 if file_path.exists():
     print(f"  - {main_file}")
 result = optimize_source_code(file_path)

     if result.get("success"):
         pass
     print(f"    루프: {result['loop_fixes']}개")
     print(f"    API 호출: {result['api_fixes']}개")
     print(f"    조건문: {result['cond_fixes']}개")
     print(f"    Import: {result['import_fixes']}개")
     print(f"    문자열: {result['string_fixes']}개")
     total_loop_fixes += result['loop_fixes']
     total_api_fixes += result['api_fixes']
     total_cond_fixes += result['cond_fixes']
     total_import_fixes += result['import_fixes']
     total_string_fixes += result['string_fixes']
     elif result.get("error"):
         pass
     print(f"    오류: {result['error']}")
 else:
     print(f"    변경 사항 없음")

 print()
    print("=" * 70)
    print("소스코드 최적화 완료!")
    print(f"  루프: {total_loop_fixes}개")
    print(f"  API 호출: {total_api_fixes}개")
    print(f"  조건문: {total_cond_fixes}개")
    print(f"  Import: {total_import_fixes}개")
    print(f"  문자열: {total_string_fixes}개")
    print("=" * 70)

 # 추가 최적화 도구 실행
 print()
    print("추가 최적화 도구 실행 중...")

 tools = [
     ("게임 성능", "tools/game_performance_optimizer.py"),
     ("학습 속도", "tools/learning_speed_enhancer.py"),
     ("코드 스타일", "tools/code_style_unifier.py"),
 ]

 for tool_name, tool_path in tools:
     print(f"  - {tool_name} 최적화...")
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
     result = subprocess.run(
 [sys.executable, tool_path],
 cwd=PROJECT_ROOT,
 capture_output=True,
 text=True,
 timeout=300
 )
 if result.returncode == 0:
     print(f"    완료")
 else:
     print(f"    오류: {result.stderr[:100]}")
 except Exception as e:
     print(f"    실패: {e}")

 print()
    print("=" * 70)
    print("모든 최적화 완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
