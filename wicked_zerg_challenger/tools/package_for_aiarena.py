#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Package WickedZergBotPro for AI Arena deployment.

Creates a zip file containing only the files needed for Arena matches:
- run.py (entry point)
- ladderbots.json (AI Arena config)
- wicked_zerg_challenger/ (bot code, minus logs/tests/docs)
- requirements.txt

Usage:
    python wicked_zerg_challenger/tools/package_for_aiarena.py
"""

import zipfile
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
BOT_DIR = PROJECT_ROOT / "wicked_zerg_challenger"

# Directories to exclude from packaging
EXCLUDE_DIRS = {
    "__pycache__", "logs", "tests", "docs", "replays",
    "replays_processed", "temp_downloads", "models", "bat",
    "sc2-ai-dashboard", "sc2-mobile-app", "scripts", ".git",
    ".cursor", ".claude", "archived_sessions", "comparison_reports",
    "background_results", "checkpoints", "stats", "games",
    "monitoring", "debug", "htmlcov", "local_training",
}

# File patterns to exclude
EXCLUDE_FILE_PATTERNS = {
    ".log", ".bat", ".ps1", ".md", ".pyc", ".pyo",
    ".egg-info", ".coverage", ".pytest_cache",
}

# File extensions to include
INCLUDE_EXTENSIONS = {".py", ".json", ".txt"}


def should_include_dir(dir_name: str) -> bool:
    """Check if directory should be included."""
    if dir_name.startswith("."):
        return False
    if dir_name in EXCLUDE_DIRS:
        return False
    return True


def should_include_file(filepath: Path) -> bool:
    """Check if file should be included in the package."""
    name = filepath.name

    # Exclude by extension
    if filepath.suffix in EXCLUDE_FILE_PATTERNS:
        return False

    # Only include specific extensions
    if filepath.suffix not in INCLUDE_EXTENSIONS:
        return False

    # Exclude test files
    if name.startswith("test_"):
        return False

    # Exclude debug files
    if name.startswith("debug_"):
        return False

    return True


def main() -> None:
    """Create AI Arena deployment zip."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"WickedZergBotPro_{timestamp}.zip"
    output_path = PROJECT_ROOT / output_name

    file_count = 0

    print("=" * 60)
    print("AI Arena Packaging Tool - WickedZergBotPro")
    print("=" * 60)

    # Verify required files exist
    run_py = PROJECT_ROOT / "run.py"
    lb_json = PROJECT_ROOT / "ladderbots.json"

    if not run_py.exists():
        print("[ERROR] run.py not found at project root!")
        print("[INFO]  Run this command first to create it.")
        return

    if not lb_json.exists():
        print("[ERROR] ladderbots.json not found at project root!")
        return

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. run.py (entry point)
        zf.write(run_py, "run.py")
        file_count += 1
        print(f"  + run.py")

        # 2. ladderbots.json (AI Arena config)
        zf.write(lb_json, "ladderbots.json")
        file_count += 1
        print(f"  + ladderbots.json")

        # 3. requirements.txt
        req = BOT_DIR / "requirements.txt"
        if req.exists():
            zf.write(req, "requirements.txt")
            file_count += 1
            print(f"  + requirements.txt")

        # 4. Bot code (wicked_zerg_challenger/)
        print(f"\n  Scanning bot directory: {BOT_DIR}")
        for root, dirs, files in os.walk(BOT_DIR):
            # Filter excluded directories in-place
            dirs[:] = [d for d in dirs if should_include_dir(d)]

            for f in files:
                filepath = Path(root) / f
                if should_include_file(filepath):
                    arcname = str(filepath.relative_to(PROJECT_ROOT))
                    zf.write(filepath, arcname)
                    file_count += 1

        # 5. Include commander_knowledge.json explicitly
        knowledge_json = BOT_DIR / "commander_knowledge.json"
        arcname_knowledge = str(knowledge_json.relative_to(PROJECT_ROOT))
        if knowledge_json.exists() and arcname_knowledge not in zf.namelist():
            zf.write(knowledge_json, arcname_knowledge)
            file_count += 1

        # 6. Include config directory
        config_dir = BOT_DIR / "config"
        if config_dir.exists():
            for f in config_dir.glob("*.json"):
                arcname = str(f.relative_to(PROJECT_ROOT))
                if arcname not in zf.namelist():
                    zf.write(f, arcname)
                    file_count += 1

    size_kb = output_path.stat().st_size / 1024
    print(f"\n{'=' * 60}")
    print(f"[OK] Package created: {output_path.name}")
    print(f"[OK] Files: {file_count}")
    print(f"[OK] Size: {size_kb:.1f} KB")
    print(f"{'=' * 60}")
    print(f"\nUpload this file to AI Arena: {output_path}")


if __name__ == "__main__":
    main()
