# -*- coding: utf-8 -*-
"""
긴 함수 분할 도구

37개의 긴 함수를 더 작은 함수로 분할
"""

import ast
from pathlib import Path
from typing import Dict
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent


class LongFunctionSplitter:
    """긴 함수 분할기"""

def __init__(self):
    self.long_functions = []

def find_long_functions(
    self,
    file_path: Path,
    min_lines: int = 100) -> List[Dict]:
    """긴 함수 찾기"""
 long_functions = []

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

 tree = ast.parse(content)
 lines = content.splitlines()

 for node in ast.walk(tree):
     if isinstance(node, ast.FunctionDef):
         # 함수의 시작과 끝 라인 찾기
 start_line = node.lineno - 1
     end_line = node.end_lineno - 1 if hasattr(node, 'end_lineno') else start_line

 function_lines = end_line - start_line + 1

 if function_lines >= min_lines:
     long_functions.append({
     "name": node.name,
     "file": str(file_path),
     "start_line": start_line + 1,
     "end_line": end_line + 1,
     "lines": function_lines
 })

 except Exception as e:
     print(f"[ERROR] 함수 분석 실패 ({file_path.name}): {e}")

 return long_functions

def suggest_splits(self, function_info: Dict) -> List[str]:
    """함수 분할 제안"""
 suggestions = []

 # 일반적인 분할 패턴 제안
    suggestions.append(f"  - {function_info['name']} 함수를 더 작은 함수로 분할 검토")
    suggestions.append(f"    현재: {function_info['lines']}줄")
    suggestions.append(f"    제안: 50줄 이하의 여러 함수로 분할")

 return suggestions


def main():
    """메인 함수"""
    print("=" * 70)
    print("긴 함수 분할 분석 도구")
    print("=" * 70)
 print()

 splitter = LongFunctionSplitter()

 # 주요 파일 분석
 main_files = [
    "wicked_zerg_bot_pro.py",
    "combat_manager.py",
    "production_manager.py",
    "local_training/main_integrated.py"
 ]

 all_long_functions = []

 for file_name in main_files:
     file_path = PROJECT_ROOT / file_name
 if file_path.exists():
     long_functions = splitter.find_long_functions(file_path)
 all_long_functions.extend(long_functions)

 if all_long_functions:
     print(f"[INFO] {len(all_long_functions)}개의 긴 함수 발견:")
 print()

     for func in sorted(all_long_functions, key=lambda x: x['lines'], reverse=True)[:10]:
         pass
     print(f"  {func['file']}:{func['start_line']} - {func['name']} ({func['lines']}줄)")
 suggestions = splitter.suggest_splits(func)
 for suggestion in suggestions:
     print(suggestion)
 print()
 else:
     print("[INFO] 긴 함수를 찾을 수 없습니다.")


if __name__ == "__main__":
    main()
