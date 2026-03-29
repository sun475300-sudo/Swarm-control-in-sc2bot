#!/usr/bin/env python3
"""Phase 55 language-aware validation router.

Detects changed files and routes quality checks by language domain.

Default behavior:
- Collect changed files via `git diff --name-only HEAD~1..HEAD`
- Map files to language buckets (python/typescript/rust/docs)
- Build an execution plan and optionally run checks

Outputs:
- test_results/phase55_language_router_<timestamp>.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
REPORT_DIR = ROOT / "test_results"


@dataclass
class CommandResult:
    command: str
    cwd: str
    skipped: bool
    ok: bool
    output: str
    reason: str | None = None


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


def get_changed_files(base_ref: str) -> list[str]:
    code, out = run_cmd(["git", "diff", "--name-only", f"{base_ref}..HEAD"])
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def classify_files(files: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "python": [],
        "typescript": [],
        "rust": [],
        "docs": [],
        "other": [],
    }

    for f in files:
        lower = f.lower()
        if lower.endswith(".py"):
            buckets["python"].append(f)
        elif lower.endswith(".ts") or lower.endswith(".tsx"):
            buckets["typescript"].append(f)
        elif lower.endswith(".rs"):
            buckets["rust"].append(f)
        elif lower.endswith(".md"):
            buckets["docs"].append(f)
        else:
            buckets["other"].append(f)

    return buckets


def route_python(files: list[str], execute: bool) -> CommandResult:
    if not files:
        return CommandResult("python -m py_compile <changed .py>", str(ROOT), True, True, "", "no_python_changes")

    cmd = [sys.executable, "-m", "py_compile", *files]
    if not execute:
        return CommandResult(" ".join(cmd), str(ROOT), True, True, "", "dry_run")

    code, out = run_cmd(cmd)
    return CommandResult(" ".join(cmd), str(ROOT), False, code == 0, out)


def route_typescript(files: list[str], execute: bool) -> CommandResult:
    if not files:
        return CommandResult("npm run check", str(ROOT / "sc2-ai-dashboard"), True, True, "", "no_typescript_changes")

    dash_dir = ROOT / "sc2-ai-dashboard"
    if not (dash_dir / "package.json").exists():
        return CommandResult("npm run check", str(dash_dir), True, True, "", "dashboard_not_found")

    npm_exe = shutil.which("npm") or shutil.which("npm.cmd")
    if npm_exe is None:
        return CommandResult("npm run check", str(dash_dir), True, False, "", "npm_not_found")

    cmd = [npm_exe, "run", "check"]
    if not execute:
        return CommandResult(" ".join(cmd), str(dash_dir), True, True, "", "dry_run")

    code, out = run_cmd(cmd, cwd=dash_dir)
    return CommandResult(" ".join(cmd), str(dash_dir), False, code == 0, out)


def route_rust(files: list[str], execute: bool) -> CommandResult:
    if not files:
        return CommandResult("cargo check", str(ROOT / "rust_accel"), True, True, "", "no_rust_changes")

    rust_dir = ROOT / "rust_accel"
    if not (rust_dir / "Cargo.toml").exists():
        return CommandResult("cargo check", str(rust_dir), True, True, "", "cargo_toml_not_found")

    cargo_exe = shutil.which("cargo") or shutil.which("cargo.exe")
    if cargo_exe is None:
        return CommandResult("cargo check", str(rust_dir), True, False, "", "cargo_not_found")

    cmd = [cargo_exe, "check"]
    if not execute:
        return CommandResult(" ".join(cmd), str(rust_dir), True, True, "", "dry_run")

    code, out = run_cmd(cmd, cwd=rust_dir)
    return CommandResult(" ".join(cmd), str(rust_dir), False, code == 0, out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 55 language-aware router")
    parser.add_argument("--base-ref", default="HEAD~1", help="Git base ref for changed-file detection")
    parser.add_argument("--execute", action="store_true", help="Run routed commands")
    args = parser.parse_args()

    changed = get_changed_files(args.base_ref)
    buckets = classify_files(changed)

    python_result = route_python(buckets["python"], execute=args.execute)
    ts_result = route_typescript(buckets["typescript"], execute=args.execute)
    rust_result = route_rust(buckets["rust"], execute=args.execute)

    results = [python_result, ts_result, rust_result]
    all_ok = all(r.ok for r in results if not r.skipped)

    payload: dict[str, Any] = {
        "phase": 55,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "base_ref": args.base_ref,
        "execute": args.execute,
        "changed_files": changed,
        "buckets": buckets,
        "results": [asdict(r) for r in results],
        "all_ok": all_ok,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"phase55_language_router_{ts}.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 70)
    print("Phase 55 Language Router")
    print(f"EXECUTE: {args.execute}")
    print(f"ALL_OK: {all_ok}")
    print(f"REPORT: {report_path}")
    print("=" * 70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
