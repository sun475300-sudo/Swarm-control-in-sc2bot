"""
Performance Profiler for WickedZergBot
SC2 봇의 성능 병목 지점을 식별하고 측정하는 프로파일링 시스템

Features:
- Function execution time tracking
- Frame time monitoring
- Bottleneck detection and reporting
- Low overhead design for production use
"""

import time
import functools
from collections import defaultdict, deque
from typing import Dict, List, Callable, Any
import logging


class PerformanceProfiler:
    """성능 프로파일러 - 함수 실행 시간 및 병목 지점 추적"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

        # Timing data: {function_name: [execution_times]}
        self.timing_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Call count: {function_name: count}
        self.call_counts: Dict[str, int] = defaultdict(int)

        # Total time spent: {function_name: total_seconds}
        self.total_time: Dict[str, float] = defaultdict(float)

        # Frame timing
        self.frame_times: deque = deque(maxlen=100)
        self.last_frame_time = None

        # Warning thresholds (seconds)
        self.slow_function_threshold = 0.010  # 10ms
        self.slow_frame_threshold = 0.045     # 45ms (SC2 runs at ~22 FPS)

        # Enable/disable profiling
        self.enabled = True

    def profile(self, func: Callable) -> Callable:
        """
        Decorator to profile a function's execution time

        Usage:
            @profiler.profile
            def my_function():
                ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                func_name = f"{func.__module__}.{func.__name__}"

                self.timing_data[func_name].append(elapsed)
                self.call_counts[func_name] += 1
                self.total_time[func_name] += elapsed

                # Warn on slow execution
                if elapsed > self.slow_function_threshold:
                    self.logger.warning(
                        f"SLOW FUNCTION: {func_name} took {elapsed*1000:.2f}ms"
                    )

        return wrapper

    def start_frame(self):
        """프레임 타이밍 시작"""
        self.last_frame_time = time.perf_counter()

    def end_frame(self):
        """프레임 타이밍 종료 및 기록"""
        if self.last_frame_time is None:
            return

        frame_time = time.perf_counter() - self.last_frame_time
        self.frame_times.append(frame_time)

        if frame_time > self.slow_frame_threshold:
            self.logger.warning(
                f"SLOW FRAME: {frame_time*1000:.2f}ms (target: {self.slow_frame_threshold*1000:.0f}ms)"
            )

    def get_stats(self) -> Dict[str, Any]:
        """프로파일링 통계 반환"""
        stats = {}

        for func_name, times in self.timing_data.items():
            if not times:
                continue

            times_list = list(times)
            avg_time = sum(times_list) / len(times_list)
            max_time = max(times_list)
            min_time = min(times_list)

            stats[func_name] = {
                "call_count": self.call_counts[func_name],
                "total_time": self.total_time[func_name],
                "avg_time": avg_time,
                "max_time": max_time,
                "min_time": min_time,
                "avg_ms": avg_time * 1000,
                "max_ms": max_time * 1000,
            }

        return stats

    def get_top_bottlenecks(self, n: int = 10) -> List[tuple]:
        """
        가장 느린 함수 N개 반환

        Returns:
            List of (func_name, total_time, avg_time, call_count)
        """
        stats = self.get_stats()

        # Sort by total time spent
        sorted_stats = sorted(
            stats.items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )

        return [
            (
                func_name,
                data["total_time"],
                data["avg_time"],
                data["call_count"]
            )
            for func_name, data in sorted_stats[:n]
        ]

    def get_frame_stats(self) -> Dict[str, float]:
        """프레임 타이밍 통계"""
        if not self.frame_times:
            return {}

        times = list(self.frame_times)
        return {
            "avg_frame_ms": (sum(times) / len(times)) * 1000,
            "max_frame_ms": max(times) * 1000,
            "min_frame_ms": min(times) * 1000,
            "avg_fps": 1.0 / (sum(times) / len(times)) if times else 0,
        }

    def print_report(self):
        """콘솔에 성능 리포트 출력"""
        self.logger.info("=" * 60)
        self.logger.info("PERFORMANCE PROFILING REPORT")
        self.logger.info("=" * 60)

        # Frame stats
        frame_stats = self.get_frame_stats()
        if frame_stats:
            self.logger.info("\n[Frame Statistics]")
            self.logger.info(f"  Average FPS: {frame_stats['avg_fps']:.1f}")
            self.logger.info(f"  Average Frame Time: {frame_stats['avg_frame_ms']:.2f}ms")
            self.logger.info(f"  Max Frame Time: {frame_stats['max_frame_ms']:.2f}ms")
            self.logger.info(f"  Min Frame Time: {frame_stats['min_frame_ms']:.2f}ms")

        # Top bottlenecks
        bottlenecks = self.get_top_bottlenecks(10)
        if bottlenecks:
            self.logger.info("\n[Top 10 Bottlenecks by Total Time]")
            for i, (func_name, total_time, avg_time, call_count) in enumerate(bottlenecks, 1):
                self.logger.info(
                    f"  {i}. {func_name}\n"
                    f"     Total: {total_time*1000:.2f}ms, "
                    f"Avg: {avg_time*1000:.3f}ms, "
                    f"Calls: {call_count}"
                )

        self.logger.info("=" * 60)

    def reset(self):
        """모든 프로파일링 데이터 초기화"""
        self.timing_data.clear()
        self.call_counts.clear()
        self.total_time.clear()
        self.frame_times.clear()
        self.last_frame_time = None
        self.logger.info("Performance profiler reset")

    def enable(self):
        """프로파일링 활성화"""
        self.enabled = True
        self.logger.info("Performance profiler enabled")

    def disable(self):
        """프로파일링 비활성화"""
        self.enabled = False
        self.logger.info("Performance profiler disabled")


# Global profiler instance
_global_profiler = None


def get_profiler(logger=None) -> PerformanceProfiler:
    """글로벌 프로파일러 인스턴스 반환"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler(logger)
    return _global_profiler


def profile(func: Callable) -> Callable:
    """
    글로벌 프로파일러를 사용하는 데코레이터

    Usage:
        from utils.performance_profiler import profile

        @profile
        def my_function():
            ...
    """
    profiler = get_profiler()
    return profiler.profile(func)


class TimingContext:
    """
    Context manager for timing code blocks

    Usage:
        with TimingContext("my_operation", profiler):
            # code to time
            ...
    """

    def __init__(self, name: str, profiler: PerformanceProfiler = None):
        self.name = name
        self.profiler = profiler or get_profiler()
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time

        self.profiler.timing_data[self.name].append(elapsed)
        self.profiler.call_counts[self.name] += 1
        self.profiler.total_time[self.name] += elapsed

        if elapsed > self.profiler.slow_function_threshold:
            self.profiler.logger.warning(
                f"SLOW OPERATION: {self.name} took {elapsed*1000:.2f}ms"
            )
