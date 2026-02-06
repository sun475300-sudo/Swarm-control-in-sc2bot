#!/usr/bin/env python3
"""
UTF-8 인코딩 복구 스크립트
한글이 깨진 마크다운 파일을 UTF-8로 재저장합니다.
"""
import sys

def fix_encoding(file_path: str, output_path: str = None):
    """
    파일을 여러 인코딩으로 시도하여 읽고 UTF-8로 저장

    Args:
        file_path: 원본 파일 경로
        output_path: 출력 파일 경로 (None이면 원본 덮어쓰기)
    """
    if output_path is None:
        output_path = file_path

    # 시도할 인코딩 목록 (한국어 파일 우선)
    encodings = ['cp949', 'euc-kr', 'utf-8', 'iso-8859-1', 'latin1']

    content = None
    used_encoding = None

    # 각 인코딩으로 파일 읽기 시도
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                used_encoding = encoding
                print(f"[OK] Successfully read with {encoding} encoding")
                break
        except (UnicodeDecodeError, LookupError) as e:
            print(f"[FAIL] Failed with {encoding}: {e}")
            continue

    if content is None:
        print(f"[ERROR] Could not read file with any encoding")
        return False

    # UTF-8로 저장
    try:
        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"[OK] Successfully saved as UTF-8: {output_path}")
        print(f"   Original encoding: {used_encoding}")
        print(f"   File size: {len(content)} characters")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("UTF-8 Encoding Fix Script")
    print("=" * 70)
    print()

    files_to_fix = [
        "프로젝트_전체_진행_보고서.md",
        "부모님_연구보고서.md"
    ]

    success_count = 0
    for file_path in files_to_fix:
        print(f"\n[FILE] Processing: {file_path}")
        print("-" * 70)

        if fix_encoding(file_path):
            success_count += 1

        print("-" * 70)

    print()
    print("=" * 70)
    print(f"[DONE] Successfully fixed: {success_count}/{len(files_to_fix)} files")
    print("=" * 70)
