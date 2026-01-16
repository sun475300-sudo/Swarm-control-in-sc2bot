#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Code Diet

ڵ ̾Ʈ : ʿ ڵ   ȭ
"""

import sys
from pathlib import Path

# Add parent directory to path
script_dir = Path(__file__).parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

PROJECT_ROOT = script_dir


def run_code_diet():
    """Run code diet analysis and optimization"""
    print("\n" + "=" * 70)
    print("CODE DIET - ڵ ̾Ʈ ")
    print("=" * 70)
    print()

    try:
        # Import code diet analyzer
        from tools.code_diet_analyzer import CodeDietAnalyzer

        print("[STEP 1] Analyzing code for unused imports and dead code...")
        print("-" * 70)

        analyzer = CodeDietAnalyzer(str(PROJECT_ROOT))
        analyzer.analyze_project()
        analyzer.find_unused_imports()

        # Print results
        if analyzer.unused_imports:
            print(
                f"\n[FOUND] {len(analyzer.unused_imports)} files with unused imports:")
            for file_path, unused in list(
                    analyzer.unused_imports.items())[:10]:
                rel_path = Path(file_path).relative_to(PROJECT_ROOT)
                print(f"  - {rel_path}: {len(unused)} unused imports")
        else:
            print("\n[SUCCESS] No unused imports found")

        print("\n[STEP 2] Running comprehensive optimization...")
        print("-" * 70)

        # Run comprehensive optimizer
        try:
            from tools.comprehensive_optimizer import ComprehensiveOptimizer

            optimizer = ComprehensiveOptimizer(dry_run=False)
            unnecessary = optimizer.identify_unnecessary_files()

            if unnecessary.get("files"):
                print(
                    f"\n[FOUND] {len(unnecessary['files'])} unnecessary files")
                print(
                    f"[FOUND] {len(unnecessary['dirs'])} unnecessary directories")
            else:
                print("\n[SUCCESS] No unnecessary files found")

        except Exception as e:
            print(f"[WARNING] Comprehensive optimizer not available: {e}")

        print("\n" + "=" * 70)
        print("CODE DIET COMPLETE")
        print("=" * 70)
        print()
        print("[INFO] Code diet analysis completed")
        print("[INFO] Ready for game training")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"[ERROR] Code diet failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_code_diet()
