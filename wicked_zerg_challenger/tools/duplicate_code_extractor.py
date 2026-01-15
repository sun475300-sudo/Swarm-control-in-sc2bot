# -*- coding: utf-8 -*-
"""
중복 코드 추출 및 통합 도구

REFACTORING_ANALYSIS_REPORT.md에서 식별된 중복 함수와 코드 블록을
공통 유틸리티로 추출
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent


class DuplicateCodeExtractor:
    """중복 코드 추출기"""
 
 def __init__(self):
 self.duplicate_functions = defaultdict(list)
 self.duplicate_blocks = []
 
 def find_duplicate_functions(self, report_path: Path) -> Dict[str, List[Dict]]:
        """REFACTORING_ANALYSIS_REPORT.md에서 중복 함수 찾기"""
 if not report_path.exists():
 return {}
 
        with open(report_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 
 # 중복 함수 섹션 파싱
 duplicates = defaultdict(list)
 in_section = False
 current_function = None
 
 for line in content.splitlines():
            if '중복 함수' in line or 'Duplicate Functions' in line:
 in_section = True
 continue
 
            if in_section and line.strip().startswith('###'):
 # 함수 그룹 시작
                match = re.search(r'###\s+(\w+)\s*\(', line)
 if match:
 current_function = match.group(1)
 
 if in_section and current_function:
 # 파일 경로 찾기
                match = re.search(r'`([\w/\\]+\.py):(\d+)`', line)
 if match:
 file_path = match.group(1)
 line_num = int(match.group(2))
 duplicates[current_function].append({
                        "file": file_path,
                        "line": line_num
 })
 
 return duplicates
 
 def extract_to_common_utilities(self, duplicates: Dict[str, List[Dict]], output_path: Path):
        """중복 함수를 공통 유틸리티로 추출"""
 output_path.parent.mkdir(parents=True, exist_ok=True)
 
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write('"""\n')
            f.write("공통 유틸리티 함수 (중복 코드 제거)\n")
            f.write("\n")
            f.write("REFACTORING_ANALYSIS_REPORT.md에서 식별된 중복 함수들을 통합\n")
            f.write('"""\n\n')
 
 for func_name, occurrences in duplicates.items():
 if len(occurrences) > 1: # 2개 이상 중복
                    f.write(f"def {func_name}(*args, **kwargs):\n")
                    f.write(f'    """\n')
                    f.write(f'    공통 유틸리티 함수: {func_name}\n')
                    f.write(f'    \n')
                    f.write(f'    중복 발생 위치:\n')
 for occ in occurrences:
                        f.write(f'    - {occ["file"]}:{occ["line"]}\n')
                    f.write(f'    """\n')
                    f.write(f"    # TODO: 실제 구현 필요\n")
                    f.write(f"    # 원본 코드를 분석하여 통합 구현\n")
                    f.write(f"    pass\n\n")
 
        print(f"[INFO] 공통 유틸리티 생성: {output_path} ({len(duplicates)}개 함수)")


def main():
    """메인 함수"""
    print("=" * 70)
    print("중복 코드 추출 도구")
    print("=" * 70)
 print()
 
 extractor = DuplicateCodeExtractor()
 
 # 리포트 파일 읽기
    report_path = PROJECT_ROOT / "REFACTORING_ANALYSIS_REPORT.md"
 duplicates = extractor.find_duplicate_functions(report_path)
 
 if duplicates:
        print(f"[INFO] {len(duplicates)}개의 중복 함수 그룹 발견")
 
 # 공통 유틸리티로 추출
        utils_path = PROJECT_ROOT / "utils" / "extracted_utilities.py"
 extractor.extract_to_common_utilities(duplicates, utils_path)
 
 print()
        print("=" * 70)
        print("중복 코드 추출 완료!")
        print("=" * 70)
        print(f"  중복 함수 그룹: {len(duplicates)}개")
        print(f"  공통 유틸리티: {utils_path}")
 else:
        print("[WARNING] 중복 함수를 찾을 수 없습니다.")


if __name__ == "__main__":
 main()