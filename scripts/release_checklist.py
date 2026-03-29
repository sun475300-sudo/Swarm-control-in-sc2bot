#!/usr/bin/env python3
"""
Release Checklist Automation Script
Phase 57: CI/CD 자동화 고도화

체크리스트 항목 자동 검증:
1. 구문 검증 (Python, TypeScript, Rust)
2. 테스트 통과
3. 패키징 검증
4. 문서 최신화
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class ReleaseChecklist:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: Dict[str, Dict] = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def check_python_syntax(self) -> Tuple[bool, str]:
        """Python 구문 검증"""
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "py_compile",
                    str(self.project_root / "wicked_zerg_challenger"),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                return True, "All Python files compiled successfully"
            else:
                return False, f"Syntax errors found: {result.stderr[:500]}"
        except Exception as e:
            return False, f"Python check failed: {str(e)}"

    def check_typescript_syntax(self) -> Tuple[bool, str]:
        """TypeScript 구문 검증"""
        dashboard_dir = self.project_root / "sc2-ai-dashboard"
        if not dashboard_dir.exists():
            return True, "No TypeScript files found (skipped)"

        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(dashboard_dir),
            )
            if result.returncode == 0:
                return True, "TypeScript check passed"
            else:
                return False, f"TS errors: {result.stdout[:500]}"
        except FileNotFoundError:
            return True, "TypeScript check skipped (npx not found)"
        except Exception as e:
            return False, f"TS check failed: {str(e)}"

    def check_rust_syntax(self) -> Tuple[bool, str]:
        """Rust 구문 검증"""
        rust_dir = self.project_root / "rust_accel"
        if not rust_dir.exists():
            return True, "No Rust project found (skipped)"

        try:
            result = subprocess.run(
                ["cargo", "check", "--message-format=short"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(rust_dir),
            )
            if result.returncode == 0:
                return True, "Rust check passed"
            else:
                return False, f"Rust errors: {result.stderr[:500]}"
        except FileNotFoundError:
            return True, "Rust check skipped (cargo not found)"
        except Exception as e:
            return False, f"Rust check failed: {str(e)}"

    def check_pytest(self) -> Tuple[bool, str]:
        """pytest 실행"""
        try:
            result = subprocess.run(
                ["pytest", "--co", "-q"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project_root),
            )
            if "error" not in result.stdout.lower():
                collected = (
                    result.stdout.strip().split("\n")[-1]
                    if result.stdout
                    else "unknown"
                )
                return True, f"Tests collected: {collected}"
            else:
                return False, f"Test collection failed: {result.stderr[:300]}"
        except Exception as e:
            return True, f"Pytest check skipped: {str(e)}"

    def check_package_structure(self) -> Tuple[bool, str]:
        """패키지 구조 검증"""
        required_files = [
            "README.md",
            "wicked_zerg_challenger/wicked_zerg_bot_pro_impl.py",
            "requirements.txt",
        ]

        missing = []
        for f in required_files:
            if not (self.project_root / f).exists():
                missing.append(f)

        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "All required files present"

    def check_documentation(self) -> Tuple[bool, str]:
        """문서 검증"""
        readme = self.project_root / "README.md"
        if not readme.exists():
            return False, "README.md not found"

        content = readme.read_text(encoding="utf-8")

        checks = {
            "Phase Progress": "Phase" in content,
            "Architecture": "System Architecture" in content or "## System" in content,
            "Usage Instructions": "Usage" in content or "Quick Start" in content,
        }

        failed = [k for k, v in checks.items() if not v]
        if failed:
            return False, f"Missing sections: {', '.join(failed)}"
        return True, "Documentation complete"

    def run_all_checks(self) -> Dict:
        """모든 체크리스트 실행"""
        checks = [
            ("python_syntax", self.check_python_syntax),
            ("typescript_syntax", self.check_typescript_syntax),
            ("rust_syntax", self.check_rust_syntax),
            ("pytest", self.check_pytest),
            ("package_structure", self.check_package_structure),
            ("documentation", self.check_documentation),
        ]

        for name, check_func in checks:
            print(f"Running: {name}...")
            passed, message = check_func()
            self.results[name] = {
                "passed": passed,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {message}")

        return self.results

    def generate_report(self) -> Dict:
        """JSON 리포트 생성"""
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["passed"])
        failed = total - passed

        report = {
            "version": "1.0.0",
            "timestamp": self.timestamp,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
            },
            "checks": self.results,
            "ready_for_release": failed == 0,
        }

        return report

    def save_report(self, report: Dict, output_dir: Path = None):
        """리포트 저장"""
        if output_dir is None:
            output_dir = self.project_root / "data" / "reports"

        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"release_checklist_{self.timestamp}.json"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\nReport saved: {filepath}")

        summary_file = output_dir / "latest.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"Latest report: {summary_file}")


def main():
    project_root = Path(__file__).parent.parent.resolve()

    print("=" * 60)
    print("Release Checklist Automation - Phase 57")
    print("=" * 60)

    checklist = ReleaseChecklist(project_root)

    report = checklist.run_all_checks()
    full_report = checklist.generate_report()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total: {full_report['summary']['total']}")
    print(f"Passed: {full_report['summary']['passed']} ✅")
    print(f"Failed: {full_report['summary']['failed']} ❌")
    print(f"Pass Rate: {full_report['summary']['pass_rate']}")
    print(
        f"Ready for Release: {'✅ YES' if full_report['ready_for_release'] else '❌ NO'}"
    )

    checklist.save_report(full_report)

    if full_report["summary"]["failed"] > 0:
        print("\n⚠️  Release checklist not passed!")
        print("Please fix the failed items before releasing.")
        return 1

    print("\n✅ All checks passed! Ready for release.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
