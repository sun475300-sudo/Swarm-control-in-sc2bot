#!/usr/bin/env python3
"""Phase 54 quality gate runner.

Runs cross-language quality checks and writes a JSON report:
1) Python syntax compile for core files
2) TypeScript dashboard type check (npm run check)
3) Rust cargo check for rust_accel
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    "scripts/replay_feedback_loop.py",
]


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
        )
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()
        return proc.returncode, output
    except FileNotFoundError as exc:
        return 127, str(exc)


def python_compile_check() -> dict[str, Any]:
    missing = [f for f in CORE_PY_FILES if not (ROOT / f).exists()]
    targets = [f for f in CORE_PY_FILES if (ROOT / f).exists()]

    if not targets:
        return {
            "name": "python_compile",
            "skipped": False,
            "ok": False,
            "reason": "no_target_files",
            "checked": [],
            "missing": missing,
        }

    code, out = run_cmd([sys.executable, "-m", "py_compile", *targets])
    return {
        "name": "python_compile",
        "skipped": False,
        "ok": code == 0,
        "checked": targets,
        "missing": missing,
        "output": out,
    }


def dashboard_ts_check() -> dict[str, Any]:
    dashboard_dir = ROOT / "sc2-ai-dashboard"
    package_json = dashboard_dir / "package.json"

    if not package_json.exists():
        return {
            "name": "typescript_check",
            "skipped": True,
            "reason": "dashboard_package_json_not_found",
        }

    npm_exe = shutil.which("npm") or shutil.which("npm.cmd")
    if npm_exe is None:
        return {
            "name": "typescript_check",
            "skipped": True,
            "reason": "npm_not_found",
        }

    code, out = run_cmd([npm_exe, "run", "check"], cwd=dashboard_dir)
    return {
        "name": "typescript_check",
        "skipped": False,
        "ok": code == 0,
        "command": "npm run check",
        "cwd": str(dashboard_dir),
        "output": out,
    }


def rust_cargo_check() -> dict[str, Any]:
    rust_dir = ROOT / "rust_accel"
    cargo_toml = rust_dir / "Cargo.toml"

    if not cargo_toml.exists():
        return {
            "name": "rust_cargo_check",
            "skipped": True,
            "reason": "cargo_toml_not_found",
        }

    cargo_exe = shutil.which("cargo") or shutil.which("cargo.exe")
    if cargo_exe is None:
        return {
            "name": "rust_cargo_check",
            "skipped": True,
            "reason": "cargo_not_found",
        }

    code, out = run_cmd([cargo_exe, "check"], cwd=rust_dir)
    return {
        "name": "rust_cargo_check",
        "skipped": False,
        "ok": code == 0,
        "command": "cargo check",
        "cwd": str(rust_dir),
        "output": out,
    }


def _is_success(result: dict[str, Any]) -> bool:
    if result.get("skipped", False):
        return True
    return bool(result.get("ok", False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 54 quality gate")
    parser.add_argument(
        "--fail-on-skipped",
        action="store_true",
        help="Treat skipped checks as failure",
    )
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

    checks = [
        python_compile_check(),
        dashboard_ts_check(),
        rust_cargo_check(),
    ]

    all_ok = True
    for item in checks:
        if item.get("skipped", False):
            if args.fail_on_skipped:
                all_ok = False
        elif not _is_success(item):
            all_ok = False

    report = {
        "phase": 54,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "all_ok": all_ok,
        "fail_on_skipped": args.fail_on_skipped,
        "checks": checks,
    }

    report_path = REPORT_DIR / f"phase54_quality_gate_{ts}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 70)
    print("Phase 54 Quality Gate")
    print(f"ALL_OK: {all_ok}")
    print(f"REPORT: {report_path}")
    print("=" * 70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
