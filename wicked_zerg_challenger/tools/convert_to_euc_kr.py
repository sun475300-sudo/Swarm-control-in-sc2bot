# -*- coding: utf-8 -*-
"""
전체 파일을 EUC-KR 인코딩으로 변환하는 스크립트

?? 주의사항:
1. Python 소스 코드는 일반적으로 UTF-8을 사용합니다
2. EUC-KR로 변환하면 일부 특수문자나 영어가 깨질 수 있습니다
3. 변환 전에 백업을 권장합니다
4. 이미 UTF-8로 잘 작동하는 파일은 변환하지 않는 것이 좋습니다
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# 변환 제외할 파일/디렉토리
EXCLUDE_PATTERNS = [
    '__pycache__',
    '.git',
    'node_modules',
    '.pyc',
    '.pyo',
    '.pt',  # PyTorch 모델 파일
    '.json',  # JSON 파일은 UTF-8이 표준
    '.csv',  # CSV 파일은 UTF-8이 표준
    '.md',  # 마크다운 파일은 UTF-8이 표준
    '.html',
    '.css',
    '.js',
    '.bat',  # 배치 파일은 이미 적절한 인코딩 사용
    '.sh',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.ico',
    '.zip',
    '.exe',
    '.dll',
    '.so',
    '.dylib',
]

# 변환할 파일 확장자
TARGET_EXTENSIONS = ['.py', '.txt']


def detect_encoding(file_path: Path) -> str:
    """파일의 인코딩을 감지"""
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin-1']
 
 for encoding in encodings:
 try:
            with open(file_path, 'r', encoding=encoding) as f:
 f.read()
 return encoding
 except (UnicodeDecodeError, UnicodeError):
 continue
 
    return 'unknown'


def should_convert_file(file_path: Path) -> bool:
    """파일을 변환해야 하는지 확인"""
 # 확장자 확인
 if file_path.suffix.lower() not in TARGET_EXTENSIONS:
 return False
 
 # 제외 패턴 확인
 file_str = str(file_path)
 for pattern in EXCLUDE_PATTERNS:
 if pattern in file_str:
 return False
 
 return True


def convert_file_to_euc_kr(file_path: Path) -> Tuple[bool, str]:
    """파일을 EUC-KR로 변환"""
 try:
 # 현재 인코딩 감지
 current_encoding = detect_encoding(file_path)
 
        if current_encoding == 'euc-kr':
            return False, "이미 EUC-KR 인코딩입니다"
 
        if current_encoding == 'unknown':
            return False, "인코딩을 감지할 수 없습니다"
 
 # 파일 읽기
 try:
            with open(file_path, 'r', encoding=current_encoding, errors='replace') as f:
 content = f.read()
 except Exception as e:
            return False, f"파일 읽기 실패: {e}"
 
 # EUC-KR로 변환 시도
 try:
 # UTF-8로 먼저 정규화
            content_utf8 = content.encode('utf-8').decode('utf-8')
 # EUC-KR로 변환
            content_euc_kr = content_utf8.encode('euc-kr', errors='replace').decode('euc-kr')
 except Exception as e:
            return False, f"인코딩 변환 실패: {e}"
 
 # 백업 파일 생성
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
            with open(backup_path, 'w', encoding=current_encoding, errors='replace') as f:
 f.write(content)
 except Exception as e:
            return False, f"백업 파일 생성 실패: {e}"
 
 # EUC-KR로 저장
 try:
            with open(file_path, 'w', encoding='euc-kr', errors='replace') as f:
 f.write(content_euc_kr)
 except Exception as e:
 # 실패 시 백업에서 복원
 try:
                with open(backup_path, 'r', encoding=current_encoding) as f:
 original_content = f.read()
                with open(file_path, 'w', encoding=current_encoding) as f:
 f.write(original_content)
 except:
 pass
            return False, f"파일 저장 실패: {e}"
 
        return True, f"{current_encoding} -> euc-kr 변환 완료"
 
 except Exception as e:
        return False, f"오류: {e}"


def find_all_files(root_dir: Path) -> List[Path]:
    """변환할 모든 파일 찾기"""
 files = []
 
 for root, dirs, filenames in os.walk(root_dir):
 # 제외할 디렉토리 제거
 dirs[:] = [d for d in dirs if not any(pattern in d for pattern in EXCLUDE_PATTERNS)]
 
 for filename in filenames:
 file_path = Path(root) / filename
 if should_convert_file(file_path):
 files.append(file_path)
 
 return files


def main():
    """메인 함수"""
    print("=" * 70)
    print("전체 파일을 EUC-KR 인코딩으로 변환")
    print("=" * 70)
 print()
    print("??  주의사항:")
    print("1. Python 소스 코드는 일반적으로 UTF-8을 사용합니다")
    print("2. EUC-KR로 변환하면 일부 특수문자나 영어가 깨질 수 있습니다")
    print("3. 변환 전에 백업을 권장합니다")
    print("4. 이미 UTF-8로 잘 작동하는 파일은 변환하지 않는 것이 좋습니다")
 print()
 
 # 사용자 확인
    response = input("정말로 모든 파일을 EUC-KR로 변환하시겠습니까? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("변환을 취소했습니다.")
 return
 
 print()
    print("파일 검색 중...")
 
 # 모든 파일 찾기
 files = find_all_files(PROJECT_ROOT)
 
    print(f"총 {len(files)}개의 파일을 찾았습니다.")
 print()
 
 # 변환 통계
 converted = 0
 skipped = 0
 failed = 0
 
 # 각 파일 변환
 for i, file_path in enumerate(files, 1):
 relative_path = file_path.relative_to(PROJECT_ROOT)
        print(f"[{i}/{len(files)}] {relative_path}...", end=' ')
 
 success, message = convert_file_to_euc_kr(file_path)
 
 if success:
            print(f"? {message}")
 converted += 1
        elif "이미" in message:
            print(f"??  {message}")
 skipped += 1
 else:
            print(f"? {message}")
 failed += 1
 
 print()
    print("=" * 70)
    print("변환 완료")
    print("=" * 70)
    print(f"변환 성공: {converted}개")
    print(f"건너뜀: {skipped}개")
    print(f"실패: {failed}개")
 print()
    print("??  백업 파일(.bak)이 생성되었습니다.")
    print("   문제가 발생하면 백업 파일을 사용하여 복원할 수 있습니다.")


if __name__ == "__main__":
 main()