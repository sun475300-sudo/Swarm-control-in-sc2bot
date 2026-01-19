#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 API 키 제거 스크립트
프로젝트에서 하드코딩된 API 키를 찾아서 제거합니다.
"""

import os
import re
from pathlib import Path
from typing import List
from typing import Tuple

# 제거할 기존 키들
OLD_KEYS = [
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY_HERE",  # 예제로만 사용된 키
]

# 제외할 파일/디렉토리
EXCLUDE_PATTERNS = [
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".idea",
    ".vscode",
    "build",
    "dist",
    "*.pyc",
    "*.pyo",
    "*.log",
    "secrets/",
    "api_keys/",  # 실제 키 파일은 제외 (이미 .gitignore에 있음)
]


def should_exclude(path: Path) -> bool:
    """파일/디렉토리를 제외해야 하는지 확인"""
 path_str = str(path)
 for pattern in EXCLUDE_PATTERNS:
     if pattern in path_str:
         return True
 return False

def find_hardcoded_keys(root_dir: Path) -> List[Tuple[Path, int, str]]:
    """하드코딩된 키를 찾습니다"""
 results = []

 # 검색할 파일 확장자
    search_extensions = {".py", ".kt", ".java", ".js", ".ts", ".md", ".txt", ".env", ".bat", ".ps1", ".sh"}

    for file_path in root_dir.rglob("*"):
        if should_exclude(file_path):
            continue

 if file_path.is_file() and file_path.suffix in search_extensions:
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
         with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
 for line_num, line in enumerate(f, 1):
     for old_key in OLD_KEYS:
         if old_key in line:
             results.append((file_path, line_num, line.strip()))
 except Exception as e:
     print(f"? 파일 읽기 실패: {file_path} - {e}")

 return results

def remove_keys_from_file(file_path: Path, old_keys: List[str]) -> bool:
    """파일에서 키를 제거합니다 (예제 키만 마스킹)"""
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
     with open(file_path, 'r', encoding='utf-8') as f:
 content = f.read()

 original_content = content

 # 문서 파일의 경우 예제 키를 마스킹
     if file_path.suffix in {".md", ".txt"}:
         pass
     for old_key in old_keys:
     # 예제 키를 마스킹된 형식으로 변경
     masked = old_key[:10] + "..." + old_key[-4:]
 content = content.replace(old_key, masked)

 # 코드 파일의 경우 주석 처리 또는 제거
     elif file_path.suffix in {".py", ".kt", ".java", ".js", ".ts"}:
         pass
     for old_key in old_keys:
     # 하드코딩된 키를 찾아서 주석 처리
     pattern = rf'["\']?{re.escape(old_key)}["\']?'
     content = re.sub(pattern, '"YOUR_API_KEY_HERE"', content)

 # 변경사항이 있으면 저장
 if content != original_content:
     with open(file_path, 'w', encoding='utf-8') as f:
 f.write(content)
 return True

 return False
 except Exception as e:
     print(f"? 파일 수정 실패: {file_path} - {e}")
 return False

def main():
    """메인 함수"""
 project_root = Path(__file__).parent.parent

    print("=" * 70)
    print("기존 API 키 제거 스크립트")
    print("=" * 70)
 print()

 # 1. 하드코딩된 키 찾기
    print("[1/3] 하드코딩된 키 검색 중...")
 results = find_hardcoded_keys(project_root)

 if not results:
     print("  ? 하드코딩된 키를 찾을 수 없습니다.")
 else:
     print(f"  ? {len(results)}개의 파일에서 키를 발견했습니다:")
 for file_path, line_num, line in results[:10]: # 처음 10개만 표시
 rel_path = file_path.relative_to(project_root)
     print(f"    - {rel_path}:{line_num}")
     print(f"      {line[:80]}...")
 if len(results) > 10:
     print(f"    ... 및 {len(results) - 10}개 더")
 print()

 # 2. 문서 파일에서 예제 키 마스킹
    print("[2/3] 문서 파일에서 예제 키 마스킹 중...")
    doc_files = [r[0] for r in results if r[0].suffix in {".md", ".txt"}]
 masked_count = 0
 for file_path in doc_files:
     if remove_keys_from_file(file_path, OLD_KEYS):
         masked_count += 1
 rel_path = file_path.relative_to(project_root)
     print(f"  ? {rel_path} 업데이트됨")

 if masked_count == 0:
     print("  ? 마스킹할 파일이 없습니다.")
 else:
     print(f"  ? {masked_count}개 파일 업데이트 완료")
 print()

 # 3. 요약
    print("[3/3] 요약")
    print("=" * 70)
    print(f"발견된 키: {len(results)}개")
    print(f"마스킹된 파일: {masked_count}개")
 print()
    print("? 중요:")
    print("  1. 실제 키 파일 (secrets/, api_keys/)은 이미 .gitignore에 있습니다")
    print("  2. Git history에서 키를 제거하려면 git-filter-repo를 사용하세요")
    print("  3. 환경 변수에서도 키를 제거해야 합니다")
 print()

if __name__ == "__main__":
    main()
