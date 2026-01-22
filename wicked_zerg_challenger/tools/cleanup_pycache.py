# -*- coding: utf-8 -*-
"""
__pycache__ 디렉토리 정리 스크립트

파일_정리_최종_완료.md 문서에 명시된 정리 작업을 자동화합니다.

정리 대상:
1. __pycache__ 디렉토리
2. .pyc 파일
3. 임시 파일 (.tmp, .bak, .old, .swp)
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple


def find_pycache_dirs(root_dir: str) -> List[Path]:
    """__pycache__ 디렉토리 찾기"""
    pycache_dirs = []
    root = Path(root_dir)

    for path in root.rglob("__pycache__"):
        if path.is_dir():
            pycache_dirs.append(path)

    return pycache_dirs


def find_pyc_files(root_dir: str) -> List[Path]:
    """.pyc 파일 찾기"""
    pyc_files = []
    root = Path(root_dir)

    for path in root.rglob("*.pyc"):
        if path.is_file():
            pyc_files.append(path)

    return pyc_files


def find_temp_files(root_dir: str) -> List[Path]:
    """임시 파일 찾기 (.tmp, .bak, .old, .swp)"""
    temp_extensions = [".tmp", ".bak", ".old", ".swp"]
    temp_files = []
    root = Path(root_dir)

    for ext in temp_extensions:
        for path in root.rglob(f"*{ext}"):
            if path.is_file():
                temp_files.append(path)

    return temp_files


def cleanup_all(root_dir: str, dry_run: bool = True) -> Tuple[int, int, int]:
    """
    모든 정리 작업 수행

    Args:
        root_dir: 정리할 루트 디렉토리
        dry_run: True면 실제로 삭제하지 않고 삭제할 항목만 출력

    Returns:
        (삭제된 디렉토리 수, 삭제된 파일 수, 총 바이트 수)
    """
    print(f"\n{'='*60}")
    print(f"{'[DRY RUN] ' if dry_run else ''}Cleanup Report for: {root_dir}")
    print(f"{'='*60}\n")

    dirs_deleted = 0
    files_deleted = 0
    total_bytes = 0

    # 1. __pycache__ 디렉토리
    print("1. __pycache__ 디렉토리:")
    print("-" * 40)
    pycache_dirs = find_pycache_dirs(root_dir)
    for d in pycache_dirs:
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        total_bytes += size
        print(f"  [DIR] {d} ({size:,} bytes)")
        if not dry_run:
            try:
                shutil.rmtree(d)
                dirs_deleted += 1
            except Exception as e:
                print(f"    [ERROR] Failed to delete: {e}")
        else:
            dirs_deleted += 1
    print(f"  Total: {len(pycache_dirs)} directories\n")

    # 2. .pyc 파일 (pycache 외부에 있는 것들)
    print("2. Standalone .pyc files:")
    print("-" * 40)
    pyc_files = find_pyc_files(root_dir)
    # pycache 내부 파일은 이미 삭제되었으므로 제외
    standalone_pyc = [f for f in pyc_files if "__pycache__" not in str(f)]
    for f in standalone_pyc:
        size = f.stat().st_size
        total_bytes += size
        print(f"  [FILE] {f} ({size:,} bytes)")
        if not dry_run:
            try:
                f.unlink()
                files_deleted += 1
            except Exception as e:
                print(f"    [ERROR] Failed to delete: {e}")
        else:
            files_deleted += 1
    print(f"  Total: {len(standalone_pyc)} files\n")

    # 3. 임시 파일
    print("3. Temporary files (.tmp, .bak, .old, .swp):")
    print("-" * 40)
    temp_files = find_temp_files(root_dir)
    for f in temp_files:
        size = f.stat().st_size
        total_bytes += size
        print(f"  [FILE] {f} ({size:,} bytes)")
        if not dry_run:
            try:
                f.unlink()
                files_deleted += 1
            except Exception as e:
                print(f"    [ERROR] Failed to delete: {e}")
        else:
            files_deleted += 1
    print(f"  Total: {len(temp_files)} files\n")

    # 요약
    print(f"{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    print(f"  Directories to delete: {len(pycache_dirs)}")
    print(f"  Files to delete: {len(standalone_pyc) + len(temp_files)}")
    print(f"  Total space to free: {total_bytes:,} bytes ({total_bytes/1024/1024:.2f} MB)")

    if dry_run:
        print(f"\n[DRY RUN] No files were actually deleted.")
        print(f"Run with --execute to perform actual cleanup.")
    else:
        print(f"\n[COMPLETED] Cleanup finished!")
        print(f"  Directories deleted: {dirs_deleted}")
        print(f"  Files deleted: {files_deleted}")

    return dirs_deleted, files_deleted, total_bytes


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup __pycache__ and temporary files")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete files (default is dry run)"
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Root path to cleanup (default: parent of this script)"
    )

    args = parser.parse_args()

    # 기본 경로: 이 스크립트의 상위 디렉토리 (wicked_zerg_challenger)
    if args.path:
        root_dir = args.path
    else:
        script_dir = Path(__file__).parent
        root_dir = str(script_dir.parent)

    dry_run = not args.execute
    cleanup_all(root_dir, dry_run=dry_run)


if __name__ == "__main__":
    main()
