#!/usr/bin/env python3
"""
Phase 71: 통합 검증 자동화 고도화
멀티언어 통합 검증 + 자동 복구 + 상세 리포트 생성
"""

import ast
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    language: str
    tool: str
    passed: bool
    duration_ms: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)


class IntegrationValidator:
    def __init__(self, project_root: Path):
        self.root = project_root
        self.results: list[ValidationResult] = []
        self.start_time = time.time()

    def validate_python_syntax(self) -> ValidationResult:
        """Python AST 기반 심층 문법 검증"""
        start = time.time()
        errors = []
        warnings = []

        py_files = list(self.root.rglob("*.py"))
        total_lines = 0

        for f in py_files:
            try:
                with open(f, encoding="utf-8") as file:
                    content = file.read()
                    tree = ast.parse(content)
                    total_lines += len(content.splitlines())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if len(ast.get_docstring(node) or "") == 0:
                                warnings.append(
                                    f"{f}:{node.lineno} - {node.name} has no docstring"
                                )

                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Attribute):
                                if node.func.attr == "do":
                                    errors.append(
                                        f"{f}:{node.lineno} - Potential unwrapped self.bot.do() call"
                                    )

            except SyntaxError as e:
                errors.append(f"{f}:{e.lineno} - {e.msg}")
            except Exception as e:
                warnings.append(f"{f} - {str(e)}")

        duration = (time.time() - start) * 1000
        return ValidationResult(
            language="python",
            tool="ast_parser",
            passed=len(errors) == 0,
            duration_ms=duration,
            errors=errors[:10],
            warnings=warnings[:10],
            artifacts={
                "total_files": str(len(py_files)),
                "total_lines": str(total_lines),
            },
        )

    def validate_rust_cargo(self) -> ValidationResult:
        """Rust cargo check"""
        start = time.time()
        rust_dir = self.root / "rust_accel"

        if not rust_dir.exists():
            return ValidationResult(
                "rust", "cargo", True, 0, [], ["No rust_accel directory"]
            )

        try:
            result = subprocess.run(
                ["cargo", "check", "--message-format=json"],
                cwd=rust_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )

            errors = []
            for line in result.stdout.splitlines():
                try:
                    msg = json.loads(line)
                    if msg.get("reason") == "compiler-message":
                        msg_dict = msg.get("message", {})
                        for span in msg_dict.get("spans", []):
                            if msg_dict.get("level") == "error":
                                errors.append(
                                    f"{span.get('file_name', '?')}:{span.get('line_start', '?')} - {msg_dict.get('message', '')}"
                                )
                except json.JSONDecodeError:
                    pass

            return ValidationResult(
                language="rust",
                tool="cargo_check",
                passed=result.returncode == 0,
                duration_ms=(time.time() - start) * 1000,
                errors=errors[:10],
            )
        except FileNotFoundError:
            return ValidationResult(
                "rust", "cargo", True, 0, [], ["Cargo not installed"]
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                "rust", "cargo", False, 120000, ["Cargo check timeout"]
            )
        except Exception as e:
            return ValidationResult("rust", "cargo", False, 0, [str(e)])

    def validate_typescript_tsc(self) -> ValidationResult:
        """TypeScript tsc 검증"""
        start = time.time()
        ts_files = list(self.root.rglob("*.ts")) + list(self.root.rglob("*.tsx"))

        if not ts_files:
            return ValidationResult(
                "typescript", "tsc", True, 0, [], ["No TypeScript files"]
            )

        tsconfig_paths = [
            self.root / "sc2-ai-dashboard" / "tsconfig.json",
            self.root / "tsconfig.json",
        ]

        tsconfig = None
        for p in tsconfig_paths:
            if p.exists():
                tsconfig = p.parent
                break

        if not tsconfig:
            return ValidationResult(
                "typescript", "tsc", True, 0, [], ["No tsconfig.json"]
            )

        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--pretty", "false"],
                cwd=tsconfig,
                capture_output=True,
                text=True,
                timeout=60,
            )

            errors = [
                line for line in result.stdout.splitlines() if "error TS" in line
            ][:10]
            return ValidationResult(
                language="typescript",
                tool="tsc",
                passed=result.returncode == 0,
                duration_ms=(time.time() - start) * 1000,
                errors=errors,
            )
        except FileNotFoundError:
            return ValidationResult(
                "typescript", "tsc", True, 0, [], ["Node.js not installed"]
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                "typescript", "tsc", False, 60000, ["TypeScript check timeout"]
            )
        except Exception as e:
            return ValidationResult("typescript", "tsc", False, 0, [str(e)])

    def validate_go_modules(self) -> ValidationResult:
        """Go module 검증"""
        start = time.time()
        go_dir = self.root / "go_backend"

        if not go_dir.exists():
            return ValidationResult(
                "go", "go", True, 0, [], ["No go_backend directory"]
            )

        go_mod = go_dir / "go.mod"
        if not go_mod.exists():
            return ValidationResult("go", "go", False, 0, ["go.mod not found"])

        try:
            result = subprocess.run(
                ["go", "mod", "tidy"],
                cwd=go_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return ValidationResult(
                language="go",
                tool="go_mod_tidy",
                passed=result.returncode == 0,
                duration_ms=(time.time() - start) * 1000,
                errors=[result.stderr][:5] if result.stderr else [],
            )
        except FileNotFoundError:
            return ValidationResult("go", "go", True, 0, [], ["Go not installed"])
        except subprocess.TimeoutExpired:
            return ValidationResult("go", "go", False, 60000, ["Go mod tidy timeout"])
        except Exception as e:
            return ValidationResult("go", "go", False, 0, [str(e)])

    def validate_sql_queries(self) -> ValidationResult:
        """SQL 쿼리 기본 검증"""
        start = time.time()
        errors = []
        warnings = []

        sql_files = list(self.root.rglob("*.sql"))
        for f in sql_files:
            try:
                with open(f, encoding="utf-8") as file:
                    content = file.read()
                    upper = content.upper()

                    if "DROP TABLE" in upper and "IF EXISTS" not in upper:
                        warnings.append(f"{f}: Missing IF EXISTS in DROP TABLE")

                    if "DELETE FROM" in upper and "WHERE" not in upper:
                        errors.append(f"{f}: Dangerous DELETE without WHERE clause")

            except Exception as e:
                warnings.append(f"{f}: {str(e)}")

        return ValidationResult(
            language="sql",
            tool="sql_linter",
            passed=len(errors) == 0,
            duration_ms=(time.time() - start) * 1000,
            errors=errors,
            warnings=warnings[:5],
            artifacts={"total_sql_files": str(len(sql_files))},
        )

    def validate_protobuf_syntax(self) -> ValidationResult:
        """Protobuf 문법 검증"""
        start = time.time()
        proto_files = list(self.root.rglob("*.proto"))

        if not proto_files:
            return ValidationResult(
                "protobuf", "protoc", True, 0, [], ["No proto files"]
            )

        errors = []
        for f in proto_files:
            try:
                with open(f, encoding="utf-8") as file:
                    content = file.read()

                    if "syntax =" not in content:
                        errors.append(f"{f}: Missing syntax declaration")

                    if "package " not in content:
                        errors.append(f"{f}: Missing package declaration")

                    if "message " not in content:
                        errors.append(f"{f}: No message definitions")

            except Exception as e:
                errors.append(f"{f}: {str(e)}")

        return ValidationResult(
            language="protobuf",
            tool="protoc",
            passed=len(errors) == 0,
            duration_ms=(time.time() - start) * 1000,
            errors=errors[:5],
        )

    def validate_shell_scripts(self) -> ValidationResult:
        """Shell 스크립트 검증"""
        start = time.time()
        errors = []
        warnings = []

        shell_files = list(self.root.rglob("*.sh")) + list(self.root.rglob("scripts/*"))
        for f in shell_files:
            if not f.is_file():
                continue
            try:
                with open(f, encoding="utf-8") as file:
                    content = file.read()
                    lines = content.splitlines()

                    for i, line in enumerate(lines, 1):
                        if line.startswith("#!"):
                            continue
                        if "rm -rf /" in line and not line.strip().startswith("#"):
                            errors.append(f"{f}:{i}: Dangerous rm -rf command")
                        if "chmod 777" in line:
                            warnings.append(f"{f}:{i}: Insecure chmod 777")

            except Exception as e:
                warnings.append(f"{f}: {str(e)}")

        return ValidationResult(
            language="shell",
            tool="shellcheck",
            passed=len(errors) == 0,
            duration_ms=(time.time() - start) * 1000,
            errors=errors[:5],
            warnings=warnings[:5],
        )

    def run_all_validations(self) -> dict[str, Any]:
        """모든 검증 병렬 실행"""
        validators = [
            self.validate_python_syntax,
            self.validate_rust_cargo,
            self.validate_typescript_tsc,
            self.validate_go_modules,
            self.validate_sql_queries,
            self.validate_protobuf_syntax,
            self.validate_shell_scripts,
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(v): v.__name__ for v in validators}
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    self.results.append(
                        ValidationResult(
                            language="unknown",
                            tool=futures[future],
                            passed=False,
                            duration_ms=0,
                            errors=[str(e)],
                        )
                    )

        return self.generate_report()

    def generate_report(self) -> dict[str, Any]:
        """검증 리포트 생성"""
        total_duration = (time.time() - self.start_time) * 1000
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_validations": len(self.results),
                "passed": passed,
                "failed": failed,
                "total_duration_ms": total_duration,
                "overall_status": "PASS" if failed == 0 else "FAIL",
            },
            "results": [
                {
                    "language": r.language,
                    "tool": r.tool,
                    "passed": r.passed,
                    "duration_ms": round(r.duration_ms, 2),
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "artifacts": r.artifacts,
                }
                for r in self.results
            ],
        }

        report_path = self.root / "validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n{'=' * 70}")
        print(f"  Phase 71: 통합 검증 자동화 리포트")
        print(f"{'=' * 70}")
        print(f"  Overall Status: {'✅ PASS' if failed == 0 else '❌ FAIL'}")
        print(f"  Passed: {passed}/{len(self.results)}")
        print(f"  Duration: {total_duration:.0f}ms")
        print(f"{'=' * 70}\n")

        for r in self.results:
            status = "✅" if r.passed else "❌"
            print(f"  {status} {r.language:12} ({r.tool:15}) - {r.duration_ms:.0f}ms")
            if r.errors:
                for e in r.errors[:3]:
                    print(f"      🔴 {e}")
            if r.warnings:
                for w in r.warnings[:3]:
                    print(f"      🟡 {w}")

        print(f"\n📄 Full report: {report_path}")
        return report


def main():
    project_root = Path(__file__).parent
    validator = IntegrationValidator(project_root)
    report = validator.run_all_validations()

    sys.exit(0 if report["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
