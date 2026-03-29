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
import argparse

# 설정
PROJECT_DIR = Path(__file__).parent

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


def create_arena_zip(output_dir: Path, zip_name: str):
    """Arena 업로드용 ZIP 생성"""
    zip_path = output_dir / zip_name
    print(f"=" * 60)
    print(f"  SC2 AI Arena 패키지 생성기")
    print(f"  프로젝트: {PROJECT_DIR}")
    print(f"  출력: {zip_path}")
    print(f"=" * 60)

    # CI/Linux 환경에서도 동작하도록 출력 디렉토리를 보장
    output_dir.mkdir(parents=True, exist_ok=True)

    file_count = 0
    total_size = 0

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
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
    zip_size = zip_path.stat().st_size
    print(f"\n{'=' * 60}")
    print(f"  DONE! Package created!")
    print(f"  Files: {file_count}")
    print(f"  Original: {total_size / 1024 / 1024:.1f} MB")
    print(f"  ZIP: {zip_size / 1024 / 1024:.1f} MB")
    print(f"  Path: {zip_path}")
    print(f"{'=' * 60}")
    print(f"\n  SC2 AI Arena Upload:")
    print(f"  1. https://aiarena.net")
    print(f"  2. My Bots > Upload Bot")
    print(f"  3. Race: Zerg, Type: Python")
    print(f"  4. Upload: {zip_name}")

    return str(zip_path)


def _default_output_dir() -> Path:
    env_dir = os.getenv("ARENA_OUTPUT_DIR")
    if env_dir:
        return Path(env_dir)
    if os.name == "nt":
        return Path(os.path.expanduser("~")) / "Desktop"
    return PROJECT_DIR / "dist"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SC2 AI Arena 업로드용 패키지 생성")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(_default_output_dir()),
        help="ZIP 출력 디렉토리 (기본: Windows=Desktop, 그 외=./dist)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="",
        help="ZIP 파일명 (미지정 시 타임스탬프 기반 자동 생성)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="생성 후 폴더 자동 열기 비활성화",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.name:
        zip_name = args.name
        if not zip_name.lower().endswith(".zip"):
            zip_name += ".zip"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        zip_name = f"WickedZergBotPro_Arena_{timestamp}.zip"

    result = create_arena_zip(out_dir, zip_name)

    # CI/Linux 환경에서는 자동 열기를 생략하고, Windows 로컬 실행 시에만 연다.
    if os.name == "nt" and not args.no_open:
        os.startfile(str(Path(result).parent))
