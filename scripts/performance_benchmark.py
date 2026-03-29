#!/usr/bin/env python3
"""
Rust 가속 모듈 벤치마크 스크립트
Phase 58: 성능 최적화

Rust 가속 vs Python 폴백 성능 비교
"""

import json
import subprocess
import time
import statistics
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class PerformanceBenchmark:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: Dict = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def check_rust_available(self) -> bool:
        """Rust 컴파일러 사용 가능 여부"""
        try:
            result = subprocess.run(
                ["cargo", "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def check_python_version(self) -> str:
        """Python 버전 확인"""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def benchmark_rust_module(self, iterations: int = 100) -> Tuple[bool, float, str]:
        """Rust 모듈 빌드 및 기본 성능 테스트"""
        rust_dir = self.project_root / "rust_accel"
        if not rust_dir.exists():
            return False, 0.0, "Rust 프로젝트 없음"

        try:
            build_start = time.time()
            result = subprocess.run(
                ["cargo", "build", "--release"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(rust_dir),
            )
            build_time = time.time() - build_start

            if result.returncode != 0:
                return False, 0.0, f"빌드 실패: {result.stderr[:200]}"

            return True, build_time, f"빌드 성공: {build_time:.2f}초"

        except subprocess.TimeoutExpired:
            return False, 0.0, "빌드 타임아웃"
        except FileNotFoundError:
            return False, 0.0, "cargo 없음"
        except Exception as e:
            return False, 0.0, f"오류: {str(e)}"

    def benchmark_python_syntax(self, iterations: int = 10) -> Dict:
        """Python 구문 검증 성능 측정"""
        import py_compile
        import glob

        py_files = list(self.project_root.glob("wicked_zerg_challenger/**/*.py"))

        if not py_files:
            return {"error": "Python 파일 없음", "iterations": 0}

        times = []
        for _ in range(iterations):
            start = time.time()
            for f in py_files:
                try:
                    py_compile.compile(str(f), doraise=True)
                except py_compile.PyCompileError:
                    pass
            elapsed = time.time() - start
            times.append(elapsed)

        return {
            "files_checked": len(py_files),
            "iterations": iterations,
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        }

    def benchmark_import_time(self, module: str, iterations: int = 5) -> float:
        """모듈 import 시간 측정"""
        import subprocess

        times = []
        for _ in range(iterations):
            start = time.time()
            result = subprocess.run(
                [sys.executable, "-c", f"import {module}"],
                capture_output=True,
                timeout=30,
            )
            elapsed = time.time() - start
            if result.returncode == 0:
                times.append(elapsed)

        return statistics.mean(times) if times else 0.0

    def measure_ci_time(self) -> Dict:
        """CI 워크플로우 예상 시간 추정"""
        steps = [
            ("Python Lint", 30),
            ("Python Test", 120),
            ("SC2 Bot Test", 180),
            ("Node.js Test", 60),
            ("Docker Build", 300),
        ]

        total = sum(s[1] for s in steps)

        return {
            "steps": steps,
            "estimated_total_seconds": total,
            "estimated_total_minutes": total / 60,
        }

    def run_all_benchmarks(self) -> Dict:
        """모든 벤치마크 실행"""
        print("=" * 60)
        print("Phase 58: 성능 벤치마크")
        print("=" * 60)

        rust_available = self.check_rust_available()
        print(f"Rust 사용 가능: {rust_available}")

        print("\n[1/4] Python 구문 검증 벤치마크...")
        py_result = self.benchmark_python_syntax(iterations=5)
        print(f"  평균 시간: {py_result.get('avg_time', 0):.2f}초")
        print(f"  파일 수: {py_result.get('files_checked', 0)}")

        if rust_available:
            print("\n[2/4] Rust 모듈 빌드 벤치마크...")
            rust_ok, build_time, msg = self.benchmark_rust_module()
            print(f"  {msg}")
        else:
            print("\n[2/4] Rust 모듈 벤치마크 스킵 (cargo 없음)")
            build_time = 0.0

        print("\n[3/4] 모듈 Import 시간 측정...")
        import_times = {}
        for module in ["pyyaml", "aiohttp"]:
            t = self.benchmark_import_time(module)
            import_times[module] = t
            print(f"  {module}: {t:.3f}초")

        print("\n[4/4] CI 시간 추정...")
        ci_est = self.measure_ci_time()
        print(f"  예상 총 시간: {ci_est['estimated_total_minutes']:.1f}분")

        self.results = {
            "rust_available": rust_available,
            "python_version": self.check_python_version(),
            "python_syntax_benchmark": py_result,
            "rust_build_time": build_time if rust_available else None,
            "module_import_times": import_times,
            "ci_time_estimate": ci_est,
            "timestamp": self.timestamp,
        }

        return self.results

    def generate_report(self) -> Dict:
        """성능 리포트 생성"""
        report = {
            "version": "1.0.0",
            "phase": 58,
            "timestamp": self.timestamp,
            "summary": {
                "python_files": self.results.get("python_syntax_benchmark", {}).get(
                    "files_checked", 0
                ),
                "avg_syntax_check_time": self.results.get(
                    "python_syntax_benchmark", {}
                ).get("avg_time", 0),
                "rust_enabled": self.results.get("rust_available", False),
                "estimated_ci_time_minutes": self.results.get(
                    "ci_time_estimate", {}
                ).get("estimated_total_minutes", 0),
            },
            "recommendations": self._generate_recommendations(),
            "details": self.results,
        }
        return report

    def _generate_recommendations(self) -> List[str]:
        """최적화 권장사항 생성"""
        recs = []

        py_bench = self.results.get("python_syntax_benchmark", {})
        avg_time = py_bench.get("avg_time", 0)

        if avg_time > 60:
            recs.append(
                "Python 구문 검증 시간이 60초를 초과합니다. 병렬 처리를 고려하세요."
            )
        elif avg_time > 30:
            recs.append("Python 구문 검증 시간을 줄이려면 캐싱을 활성화하세요.")

        if not self.results.get("rust_available"):
            recs.append(
                "Rust 가속 모듈을 활성화하면 전투 시뮬레이션 속도를 높일 수 있습니다."
            )

        ci_minutes = self.results.get("ci_time_estimate", {}).get(
            "estimated_total_minutes", 0
        )
        if ci_minutes > 15:
            recs.append(
                f"CI 시간이 {ci_minutes:.0f}분으로 길습니다. 병렬 잡 실행을 권장합니다."
            )

        return recs

    def save_report(self, report: Dict, output_dir: Path = None):
        """리포트 저장"""
        if output_dir is None:
            output_dir = self.project_root / "data" / "scoring"

        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"performance_benchmark_{self.timestamp}.json"
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

    benchmark = PerformanceBenchmark(project_root)
    benchmark.run_all_benchmarks()
    report = benchmark.generate_report()

    print("\n" + "=" * 60)
    print("권장사항")
    print("=" * 60)
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"{i}. {rec}")

    benchmark.save_report(report)

    print(f"\nPython 파일 수: {report['summary']['python_files']}")
    print(f"평균 구문 검증 시간: {report['summary']['avg_syntax_check_time']:.2f}초")
    print(f"Rust 가속: {'활성화' if report['summary']['rust_enabled'] else '미활성화'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
