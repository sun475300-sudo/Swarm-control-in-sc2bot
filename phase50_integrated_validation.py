#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 50 integrated validation runner.

Runs core checks in one place:
1) Python syntax compile for key project files
2) Optional pytest quick run
3) Optional arena package creation
4) JSON report output
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parent
REPORT_DIR = ROOT / "test_results"

CORE_PY_FILES = [
    "wicked_zerg_challenger/bot.py",
    "wicked_zerg_challenger/bot_step_integration.py",
    "wicked_zerg_challenger/combat_manager.py",
    "wicked_zerg_challenger/intel_manager.py",
    "wicked_zerg_challenger/creep_expansion_system.py",
    "wicked_zerg_challenger/rust_accel.py",
    "wicked_zerg_challenger/opencl_accel.py",
    "wicked_zerg_challenger/training_automation.py",
    "wicked_zerg_challenger/composition_optimizer.py",
]


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def compile_check() -> dict:
    missing = [f for f in CORE_PY_FILES if not (ROOT / f).exists()]
    targets = [f for f in CORE_PY_FILES if (ROOT / f).exists()]

    if not targets:
        return {
            "ok": False,
            "checked": [],
            "missing": missing,
            "message": "No target Python files found",
        }

    code, out = run_cmd([sys.executable, "-m", "py_compile", *targets])
    return {
        "ok": code == 0,
        "checked": targets,
        "missing": missing,
        "output": out,
    }


def pytest_quick(skip: bool) -> dict:
    if skip:
        return {"skipped": True}
    code, out = run_cmd([sys.executable, "-m", "pytest", "-q", "-k", "not integration"])
    return {"skipped": False, "ok": code == 0, "output": out}


def create_package(skip: bool) -> dict:
    if skip:
        return {"skipped": True}
    code, out = run_cmd([sys.executable, "create_arena_package.py"])
    return {"skipped": False, "ok": code == 0, "output": out}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 50 integrated validation")
    parser.add_argument("--skip-pytest", action="store_true", help="Skip pytest quick run")
    parser.add_argument("--skip-package", action="store_true", help="Skip arena package creation")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    compile_result = compile_check()
    pytest_result = pytest_quick(skip=args.skip_pytest)
    package_result = create_package(skip=args.skip_package)

    all_ok = bool(compile_result.get("ok", False))
    if not pytest_result.get("skipped", False):
        all_ok = all_ok and bool(pytest_result.get("ok", False))
    if not package_result.get("skipped", False):
        all_ok = all_ok and bool(package_result.get("ok", False))

    report = {
        "phase": 50,
        "timestamp": ts,
        "all_ok": all_ok,
        "compile": compile_result,
        "pytest": pytest_result,
        "package": package_result,
    }

    report_path = REPORT_DIR / f"phase50_validation_{ts}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("Phase 50 Integrated Validation")
    print(f"ALL_OK: {all_ok}")
    print(f"REPORT: {report_path}")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
