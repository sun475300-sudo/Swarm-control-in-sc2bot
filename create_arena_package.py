#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 AI Arena 업로드용 패키지 생성기

실행: python create_arena_package.py
결과: 바탕화면에 WickedZergBotPro_Arena.zip 생성
"""

import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

# 설정
PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(os.path.expanduser("~")) / "Desktop"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")
ZIP_NAME = f"WickedZergBotPro_Arena_{TIMESTAMP}.zip"
ZIP_PATH = OUTPUT_DIR / ZIP_NAME

# Arena에 필요한 파일/폴더
INCLUDE_FILES = [
    "run.py",
    "ladderbots.json",
    "requirements.txt",
]

INCLUDE_DIRS = [
    "wicked_zerg_challenger",
]

# 제외할 패턴 (불필요한 파일)
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    ".pyo",
    ".git",
    ".env",
    ".vscode",
    ".idea",
    "node_modules",
    "local_training",
    "replays",
    "logs",
    "test_results",
    ".pytest_cache",
    "*.log",
    "*.replay",
    "*.pt",        # 학습 모델 (용량 큼)
    "*.pth",
    "*.onnx",
    "credentials",
    "PHASE_",      # Phase 문서
    "CLAUDE.md",
    ".claude",
]

# Arena용 최소 requirements.txt 생성
ARENA_REQUIREMENTS = """# SC2 AI Arena - Minimal Requirements
burnysc2>=5.0.0
numpy>=1.20.0
aiohttp>=3.9.0
s2clientprotocol>=4.19.0.0
pyyaml>=6.0
"""


def should_exclude(path_str: str) -> bool:
    """파일/폴더 제외 여부 확인"""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False


def create_arena_zip():
    """Arena 업로드용 ZIP 생성"""
    print(f"=" * 60)
    print(f"  SC2 AI Arena 패키지 생성기")
    print(f"  프로젝트: {PROJECT_DIR}")
    print(f"  출력: {ZIP_PATH}")
    print(f"=" * 60)

    file_count = 0
    total_size = 0

    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. 루트 파일 추가
        for fname in INCLUDE_FILES:
            fpath = PROJECT_DIR / fname
            if fpath.exists():
                if fname == "requirements.txt":
                    # Arena용 최소 requirements로 대체
                    zf.writestr("requirements.txt", ARENA_REQUIREMENTS)
                    print(f"  [대체] requirements.txt → Arena 최소 버전")
                else:
                    zf.write(fpath, fname)
                    print(f"  [추가] {fname}")
                file_count += 1

        # 2. 봇 소스 디렉토리 추가
        for dir_name in INCLUDE_DIRS:
            dir_path = PROJECT_DIR / dir_name
            if not dir_path.exists():
                print(f"  [경고] {dir_name} 디렉토리 없음!")
                continue

            for root, dirs, files in os.walk(dir_path):
                # 제외 디렉토리 필터
                dirs[:] = [d for d in dirs if not should_exclude(d)]

                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(PROJECT_DIR)
                    rel_str = str(rel_path)

                    if should_exclude(rel_str):
                        continue

                    # 테스트/문서 파일 제외 (봇 실행에 불필요)
                    if file.startswith("test_") or file.endswith(".md"):
                        continue

                    try:
                        zf.write(full_path, rel_str)
                        fsize = full_path.stat().st_size
                        total_size += fsize
                        file_count += 1
                    except ValueError:
                        # ZIP timestamp issue — read and write manually
                        data = full_path.read_bytes()
                        zf.writestr(rel_str, data)
                        total_size += len(data)
                        file_count += 1

    # 결과 출력
    zip_size = ZIP_PATH.stat().st_size
    print(f"\n{'=' * 60}")
    print(f"  DONE! Package created!")
    print(f"  Files: {file_count}")
    print(f"  Original: {total_size / 1024 / 1024:.1f} MB")
    print(f"  ZIP: {zip_size / 1024 / 1024:.1f} MB")
    print(f"  Path: {ZIP_PATH}")
    print(f"{'=' * 60}")
    print(f"\n  SC2 AI Arena Upload:")
    print(f"  1. https://aiarena.net")
    print(f"  2. My Bots > Upload Bot")
    print(f"  3. Race: Zerg, Type: Python")
    print(f"  4. Upload: {ZIP_NAME}")

    return str(ZIP_PATH)


if __name__ == "__main__":
    result = create_arena_zip()
    # Windows에서 생성된 파일 열기
    os.startfile(str(Path(result).parent))
