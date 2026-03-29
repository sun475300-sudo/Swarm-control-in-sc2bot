#!/usr/bin/env python3
"""Phase 55/56 language-aware validation router.

Detects changed files and routes quality checks by language domain.

Default behavior:
- Collect changed files via `git diff --name-only HEAD~1..HEAD`
- Map files to language buckets (21-language coverage)
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

LANGUAGE_BUCKETS: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "typescript": (".ts", ".tsx", ".js", ".jsx"),
    "rust": (".rs",),
    "cpp": (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx"),
    "go": (".go",),
    "java": (".java",),
    "kotlin": (".kt", ".kts"),
    "swift": (".swift",),
    "csharp": (".cs",),
    "scala": (".scala",),
    "r_lang": (".r",),
    "julia": (".jl",),
    "lua": (".lua",),
    "dart": (".dart",),
    "ruby": (".rb",),
    "haskell": (".hs",),
    "elixir": (".ex", ".exs"),
    "sql": (".sql",),
    "protobuf": (".proto",),
    "shell": (".sh", ".bash", ".zsh", ".ps1", ".cmd", ".bat"),
    "perl": (".pl", ".pm"),
    "docs": (".md",),
}


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


def _parse_file_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


def _git_name_only(*args: str) -> list[str]:
    code, out = run_cmd(["git", "diff", "--name-only", *args])
    if code != 0:
        return []
    return _parse_file_lines(out)


def _get_untracked_files() -> list[str]:
    code, out = run_cmd(["git", "ls-files", "--others", "--exclude-standard"])
    if code != 0:
        return []
    return _parse_file_lines(out)


def _unique_preserve_order(files: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for file_path in files:
        if file_path in seen:
            continue
        seen.add(file_path)
        ordered.append(file_path)
    return ordered


def get_changed_files(base_ref: str, change_mode: str) -> list[str]:
    if change_mode == "range":
        return _git_name_only(f"{base_ref}..HEAD")
    if change_mode == "staged":
        return _git_name_only("--cached")
    if change_mode == "worktree":
        return _unique_preserve_order(_git_name_only() + _get_untracked_files())
    if change_mode == "local":
        return _unique_preserve_order(
            _git_name_only("--cached") + _git_name_only() + _get_untracked_files()
        )
    raise ValueError(f"unsupported change_mode: {change_mode}")


def existing_files(files: list[str]) -> list[str]:
    return [f for f in files if (ROOT / f).exists()]


def find_executable(candidates: list[str]) -> str | None:
    for exe in candidates:
        path = shutil.which(exe)
        if path:
            return path
    return None


def classify_files(files: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {key: [] for key in LANGUAGE_BUCKETS}
    buckets["other"] = []

    for f in files:
        lower = f.lower()
        matched = False
        for bucket, exts in LANGUAGE_BUCKETS.items():
            if lower.endswith(exts):
                buckets[bucket].append(f)
                matched = True
                break
        if not matched:
            buckets["other"].append(f)

    return buckets


def route_python(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("python -m py_compile <changed .py>", str(ROOT), True, True, "", "no_python_changes")

    cmd = [sys.executable, "-m", "py_compile", *files]
    if not execute:
        return CommandResult(" ".join(cmd), str(ROOT), True, True, "", "dry_run")

    code, out = run_cmd(cmd)
    return CommandResult(" ".join(cmd), str(ROOT), False, code == 0, out)


def route_typescript(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("npm run check", str(ROOT / "sc2-ai-dashboard"), True, True, "", "no_typescript_changes")

    dash_dir = ROOT / "sc2-ai-dashboard"
    if not (dash_dir / "package.json").exists():
        return CommandResult("npm run check", str(dash_dir), True, True, "", "dashboard_not_found")

    npm_exe = find_executable(["npm", "npm.cmd"])
    if npm_exe is None:
        return CommandResult("npm run check", str(dash_dir), True, False, "", "npm_not_found")

    cmd = [npm_exe, "run", "check"]
    if not execute:
        return CommandResult(" ".join(cmd), str(dash_dir), True, True, "", "dry_run")

    code, out = run_cmd(cmd, cwd=dash_dir)
    return CommandResult(" ".join(cmd), str(dash_dir), False, code == 0, out)


def route_rust(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("cargo check", str(ROOT / "rust_accel"), True, True, "", "no_rust_changes")

    rust_dir = ROOT / "rust_accel"
    if not (rust_dir / "Cargo.toml").exists():
        return CommandResult("cargo check", str(rust_dir), True, True, "", "cargo_toml_not_found")

    cargo_exe = find_executable(["cargo", "cargo.exe"])
    if cargo_exe is None:
        return CommandResult("cargo check", str(rust_dir), True, False, "", "cargo_not_found")

    cmd = [cargo_exe, "check"]
    if not execute:
        return CommandResult(" ".join(cmd), str(rust_dir), True, True, "", "dry_run")

    code, out = run_cmd(cmd, cwd=rust_dir)
    return CommandResult(" ".join(cmd), str(rust_dir), False, code == 0, out)


def route_shell(files: list[str], execute: bool) -> CommandResult:
    files = [f for f in existing_files(files) if Path(f).suffix.lower() in {".sh", ".bash", ".zsh"}]
    if not files:
        return CommandResult("bash -n <changed shell>", str(ROOT), True, True, "", "no_shell_script_changes")

    shell_exe = find_executable(["bash", "sh"])
    if shell_exe is None:
        return CommandResult("bash -n <changed shell>", str(ROOT), True, True, "", "shell_not_found")

    if not execute:
        return CommandResult(f"{shell_exe} -n <changed shell>", str(ROOT), True, True, "", "dry_run")

    outputs: list[str] = []
    ok = True
    for f in files:
        cmd = [shell_exe, "-n", str(ROOT / f)]
        code, out = run_cmd(cmd)
        if code != 0:
            ok = False
        if out:
            outputs.append(f"[{f}]\n{out}")

    return CommandResult(f"{shell_exe} -n <changed shell>", str(ROOT), False, ok, "\n\n".join(outputs))


def route_perl(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("perl -c <changed perl>", str(ROOT), True, True, "", "no_perl_changes")

    perl_exe = find_executable(["perl", "perl.exe"])
    if perl_exe is None:
        return CommandResult("perl -c <changed perl>", str(ROOT), True, True, "", "perl_not_found")

    if not execute:
        return CommandResult(f"{perl_exe} -c <changed perl>", str(ROOT), True, True, "", "dry_run")

    outputs: list[str] = []
    ok = True
    for f in files:
        cmd = [perl_exe, "-c", str(ROOT / f)]
        code, out = run_cmd(cmd)
        if code != 0:
            ok = False
        if out:
            outputs.append(f"[{f}]\n{out}")

    return CommandResult(f"{perl_exe} -c <changed perl>", str(ROOT), False, ok, "\n\n".join(outputs))


def route_go(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("gofmt -l <changed go>", str(ROOT), True, True, "", "no_go_changes")

    gofmt_exe = find_executable(["gofmt", "gofmt.exe"])
    if gofmt_exe is None:
        return CommandResult("gofmt -l <changed go>", str(ROOT), True, True, "", "gofmt_not_found")

    cmd = [gofmt_exe, "-l", *[str(ROOT / f) for f in files]]
    if not execute:
        return CommandResult(" ".join(cmd), str(ROOT), True, True, "", "dry_run")

    code, out = run_cmd(cmd)
    # gofmt -l prints files needing formatting; non-empty output is treated as failed check.
    needs_format = bool(out.strip())
    ok = (code == 0) and (not needs_format)
    return CommandResult(" ".join(cmd), str(ROOT), False, ok, out)


def route_protobuf(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("protoc --descriptor_set_out", str(ROOT), True, True, "", "no_protobuf_changes")

    protoc_exe = find_executable(["protoc", "protoc.exe"])
    if protoc_exe is None:
        return CommandResult("protoc --descriptor_set_out", str(ROOT), True, True, "", "protoc_not_found")

    if not execute:
        return CommandResult(f"{protoc_exe} --proto_path {ROOT} ...", str(ROOT), True, True, "", "dry_run")

    outputs: list[str] = []
    ok = True
    for f in files:
        out_file = REPORT_DIR / (Path(f).stem + ".desc")
        cmd = [
            protoc_exe,
            f"--proto_path={ROOT}",
            f"--descriptor_set_out={out_file}",
            str(ROOT / f),
        ]
        code, out = run_cmd(cmd, cwd=ROOT)
        if code != 0:
            ok = False
        if out:
            outputs.append(f"[{f}]\n{out}")

    return CommandResult(f"{protoc_exe} --proto_path {ROOT} <changed proto>", str(ROOT), False, ok, "\n\n".join(outputs))


def route_java(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("javac -d <tmp> <changed java>", str(ROOT), True, True, "", "no_java_changes")

    javac_exe = find_executable(["javac", "javac.exe"])
    if javac_exe is None:
        return CommandResult("javac -d <tmp> <changed java>", str(ROOT), True, True, "", "javac_not_found")

    out_dir = REPORT_DIR / "java_classes"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [javac_exe, "-Xlint:none", "-d", str(out_dir), *[str(ROOT / f) for f in files]]
    if not execute:
        return CommandResult(" ".join(cmd), str(ROOT), True, True, "", "dry_run")

    code, out = run_cmd(cmd, cwd=ROOT)
    return CommandResult(" ".join(cmd), str(ROOT), False, code == 0, out)


def route_kotlin(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("kotlinc -d <tmp.jar> <changed kotlin>", str(ROOT), True, True, "", "no_kotlin_changes")

    kotlinc_exe = find_executable(["kotlinc", "kotlinc.bat", "kotlinc.cmd"])
    if kotlinc_exe is None:
        return CommandResult("kotlinc -d <tmp.jar> <changed kotlin>", str(ROOT), True, True, "", "kotlinc_not_found")

    out_jar = REPORT_DIR / "kotlin_check.jar"
    cmd = [kotlinc_exe, *[str(ROOT / f) for f in files], "-d", str(out_jar)]
    if not execute:
        return CommandResult(" ".join(cmd), str(ROOT), True, True, "", "dry_run")

    code, out = run_cmd(cmd, cwd=ROOT)
    return CommandResult(" ".join(cmd), str(ROOT), False, code == 0, out)


def route_sql(files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult("sqlfluff lint <changed sql>", str(ROOT), True, True, "", "no_sql_changes")

    sqlfluff_exe = find_executable(["sqlfluff", "sqlfluff.exe"])
    if sqlfluff_exe is None:
        return CommandResult("sqlfluff lint <changed sql>", str(ROOT), True, True, "", "sqlfluff_not_found")

    cmd = [sqlfluff_exe, "lint", *[str(ROOT / f) for f in files]]
    if not execute:
        return CommandResult(" ".join(cmd), str(ROOT), True, True, "", "dry_run")

    code, out = run_cmd(cmd, cwd=ROOT)
    return CommandResult(" ".join(cmd), str(ROOT), False, code == 0, out)


def route_policy_stub(language: str, files: list[str], execute: bool) -> CommandResult:
    files = existing_files(files)
    if not files:
        return CommandResult(f"policy:{language}", str(ROOT), True, True, "", f"no_{language}_changes")

    reason = "phase56_policy_stub_execute_pending" if execute else "dry_run"
    return CommandResult(f"policy:{language}", str(ROOT), True, True, "", reason)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 55 language-aware router")
    parser.add_argument("--base-ref", default="HEAD~1", help="Git base ref for changed-file detection")
    parser.add_argument(
        "--change-mode",
        choices=["range", "staged", "worktree", "local"],
        default="range",
        help="Change source: committed range, staged diff, worktree diff, or local union",
    )
    parser.add_argument("--execute", action="store_true", help="Run routed commands")
    args = parser.parse_args()

    changed = get_changed_files(args.base_ref, args.change_mode)
    buckets = classify_files(changed)

    results = [
        route_python(buckets["python"], execute=args.execute),
        route_typescript(buckets["typescript"], execute=args.execute),
        route_rust(buckets["rust"], execute=args.execute),
        route_policy_stub("cpp", buckets["cpp"], execute=args.execute),
        route_go(buckets["go"], execute=args.execute),
        route_java(buckets["java"], execute=args.execute),
        route_kotlin(buckets["kotlin"], execute=args.execute),
        route_policy_stub("swift", buckets["swift"], execute=args.execute),
        route_policy_stub("csharp", buckets["csharp"], execute=args.execute),
        route_policy_stub("scala", buckets["scala"], execute=args.execute),
        route_policy_stub("r_lang", buckets["r_lang"], execute=args.execute),
        route_policy_stub("julia", buckets["julia"], execute=args.execute),
        route_policy_stub("lua", buckets["lua"], execute=args.execute),
        route_policy_stub("dart", buckets["dart"], execute=args.execute),
        route_policy_stub("ruby", buckets["ruby"], execute=args.execute),
        route_policy_stub("haskell", buckets["haskell"], execute=args.execute),
        route_policy_stub("elixir", buckets["elixir"], execute=args.execute),
        route_sql(buckets["sql"], execute=args.execute),
        route_protobuf(buckets["protobuf"], execute=args.execute),
        route_shell(buckets["shell"], execute=args.execute),
        route_perl(buckets["perl"], execute=args.execute),
        route_policy_stub("docs", buckets["docs"], execute=args.execute),
        route_policy_stub("other", buckets["other"], execute=args.execute),
    ]

    all_ok = all(r.ok for r in results if not r.skipped)

    payload: dict[str, Any] = {
        "phase": 56,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "base_ref": args.base_ref,
        "change_mode": args.change_mode,
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
    print("Phase 56 Language Router")
    print(f"CHANGE_MODE: {args.change_mode}")
    print(f"EXECUTE: {args.execute}")
    print(f"ALL_OK: {all_ok}")
    print(f"REPORT: {report_path}")
    print("=" * 70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
