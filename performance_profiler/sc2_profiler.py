# Phase 659: Performance Profiler for SC2 Bot Optimization
# Comprehensive profiling: CPU timing, memory tracking, frame analysis, flame graphs

from __future__ import annotations

import gc
import os
import statistics
import sys
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

# ============================================================
# Timer (High-Resolution Timing)
# ============================================================


class Timer:
    """High-resolution timer for measuring code execution time.

    Supports context manager and decorator usage patterns.
    Accumulates statistics across multiple measurements.
    """

    def __init__(self, name: str = "unnamed") -> None:
        self.name = name
        self._start: Optional[float] = None
        self._elapsed: List[float] = []
        self._running = False

    def start(self) -> Timer:
        self._start = time.perf_counter()
        self._running = True
        return self

    def stop(self) -> float:
        if not self._running or self._start is None:
            return 0.0
        elapsed = time.perf_counter() - self._start
        self._elapsed.append(elapsed)
        self._running = False
        self._start = None
        return elapsed

    def reset(self) -> None:
        self._elapsed.clear()
        self._start = None
        self._running = False

    @property
    def last(self) -> float:
        return self._elapsed[-1] if self._elapsed else 0.0

    @property
    def total(self) -> float:
        return sum(self._elapsed)

    @property
    def count(self) -> int:
        return len(self._elapsed)

    @property
    def mean(self) -> float:
        return self.total / max(self.count, 1)

    @property
    def median(self) -> float:
        if not self._elapsed:
            return 0.0
        return statistics.median(self._elapsed)

    @property
    def std_dev(self) -> float:
        if len(self._elapsed) < 2:
            return 0.0
        return statistics.stdev(self._elapsed)

    @property
    def min_time(self) -> float:
        return min(self._elapsed) if self._elapsed else 0.0

    @property
    def max_time(self) -> float:
        return max(self._elapsed) if self._elapsed else 0.0

    def percentile(self, p: float) -> float:
        """Compute the p-th percentile (0-100) of recorded times."""
        if not self._elapsed:
            return 0.0
        sorted_vals = sorted(self._elapsed)
        idx = (p / 100.0) * (len(sorted_vals) - 1)
        low = int(idx)
        high = min(low + 1, len(sorted_vals) - 1)
        frac = idx - low
        return sorted_vals[low] * (1 - frac) + sorted_vals[high] * frac

    def summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "total_s": round(self.total, 6),
            "mean_ms": round(self.mean * 1000, 4),
            "median_ms": round(self.median * 1000, 4),
            "std_dev_ms": round(self.std_dev * 1000, 4),
            "min_ms": round(self.min_time * 1000, 4),
            "max_ms": round(self.max_time * 1000, 4),
            "p95_ms": round(self.percentile(95) * 1000, 4),
            "p99_ms": round(self.percentile(99) * 1000, 4),
        }

    def __enter__(self) -> Timer:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()

    def __repr__(self) -> str:
        return f"Timer({self.name!r}, count={self.count}, mean={self.mean*1000:.3f}ms)"


# ============================================================
# Memory Tracker
# ============================================================


@dataclass
class MemorySnapshot:
    """A single memory measurement point."""

    timestamp: float
    label: str
    rss_bytes: int
    gc_count: Tuple[int, int, int]
    object_count: int
    tracked_objects: int

    @property
    def rss_mb(self) -> float:
        return self.rss_bytes / (1024 * 1024)


class MemoryTracker:
    """Track memory usage, detect leaks, and monitor GC pressure.

    Uses sys.getsizeof and gc module for portable memory tracking
    without requiring external dependencies.
    """

    def __init__(self) -> None:
        self._snapshots: List[MemorySnapshot] = []
        self._baselines: Dict[str, int] = {}
        self._allocation_log: List[Dict[str, Any]] = []

    def snapshot(self, label: str = "snapshot") -> MemorySnapshot:
        """Take a memory snapshot at the current point."""
        gc_counts = gc.get_count()
        tracked = len(gc.get_objects()) if len(self._snapshots) < 50 else 0
        rss = self._estimate_rss()
        snap = MemorySnapshot(
            timestamp=time.time(),
            label=label,
            rss_bytes=rss,
            gc_count=gc_counts,
            object_count=len(gc.get_referrers(object)) if tracked else 0,
            tracked_objects=tracked,
        )
        self._snapshots.append(snap)
        return snap

    def _estimate_rss(self) -> int:
        """Estimate RSS memory usage in bytes (cross-platform)."""
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            return usage.ru_maxrss * 1024
        except ImportError:
            pass
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            pass
        # Fallback: use sys.getsizeof on gc objects sample
        return sys.getsizeof(gc.get_objects)

    def set_baseline(self, label: str = "default") -> int:
        """Record a baseline memory measurement for later comparison."""
        rss = self._estimate_rss()
        self._baselines[label] = rss
        return rss

    def compare_to_baseline(self, label: str = "default") -> Dict[str, Any]:
        """Compare current memory to a named baseline."""
        current_rss = self._estimate_rss()
        baseline = self._baselines.get(label, current_rss)
        diff = current_rss - baseline
        return {
            "baseline_mb": round(baseline / (1024 * 1024), 2),
            "current_mb": round(current_rss / (1024 * 1024), 2),
            "diff_mb": round(diff / (1024 * 1024), 2),
            "diff_percent": round((diff / max(baseline, 1)) * 100, 2),
        }

    def detect_leak(self, threshold_mb: float = 10.0) -> Dict[str, Any]:
        """Simple leak detection by comparing first and last snapshots."""
        if len(self._snapshots) < 2:
            return {"leak_detected": False, "reason": "insufficient snapshots"}
        first = self._snapshots[0]
        last = self._snapshots[-1]
        diff_mb = (last.rss_bytes - first.rss_bytes) / (1024 * 1024)
        leak = diff_mb > threshold_mb
        return {
            "leak_detected": leak,
            "growth_mb": round(diff_mb, 2),
            "threshold_mb": threshold_mb,
            "first_label": first.label,
            "last_label": last.label,
            "snapshots_count": len(self._snapshots),
        }

    def gc_pressure(self) -> Dict[str, Any]:
        """Analyze garbage collector pressure."""
        gc_stats = gc.get_stats() if hasattr(gc, "get_stats") else []
        thresholds = gc.get_threshold()
        counts = gc.get_count()
        return {
            "gc_enabled": gc.isenabled(),
            "thresholds": thresholds,
            "current_counts": counts,
            "collections": (
                [
                    {
                        "generation": i,
                        "collected": s.get("collected", 0),
                        "uncollectable": s.get("uncollectable", 0),
                    }
                    for i, s in enumerate(gc_stats)
                ]
                if gc_stats
                else []
            ),
        }

    def track_allocation(self, label: str, size_bytes: int) -> None:
        """Manually log an allocation event."""
        self._allocation_log.append(
            {
                "timestamp": time.time(),
                "label": label,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 4),
            }
        )

    def allocation_summary(self) -> Dict[str, Any]:
        """Summarize tracked allocations by label."""
        by_label: Dict[str, List[int]] = defaultdict(list)
        for entry in self._allocation_log:
            by_label[entry["label"]].append(entry["size_bytes"])
        summary = {}
        for label, sizes in by_label.items():
            summary[label] = {
                "count": len(sizes),
                "total_mb": round(sum(sizes) / (1024 * 1024), 4),
                "mean_bytes": round(sum(sizes) / max(len(sizes), 1), 2),
            }
        return summary

    def report(self) -> Dict[str, Any]:
        return {
            "snapshots": len(self._snapshots),
            "baselines": list(self._baselines.keys()),
            "gc_pressure": self.gc_pressure(),
            "leak_check": self.detect_leak(),
            "allocations": self.allocation_summary(),
        }


# ============================================================
# CPU Profiler
# ============================================================


@dataclass
class CallRecord:
    """Record of a single function call for profiling."""

    func_name: str
    module: str
    start_time: float
    end_time: float = 0.0
    children: List[CallRecord] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def self_time(self) -> float:
        child_time = sum(c.duration for c in self.children)
        return max(self.duration - child_time, 0.0)


class CPUProfiler:
    """Function-level CPU profiler with call graph and hot path analysis.

    Tracks function timings hierarchically to identify the most
    expensive code paths in the SC2 bot.
    """

    def __init__(self) -> None:
        self._timers: Dict[str, Timer] = {}
        self._call_stack: List[CallRecord] = []
        self._root_calls: List[CallRecord] = []
        self._hot_paths: Dict[str, float] = defaultdict(float)
        self._call_counts: Dict[str, int] = defaultdict(int)

    def get_timer(self, name: str) -> Timer:
        if name not in self._timers:
            self._timers[name] = Timer(name)
        return self._timers[name]

    @contextmanager
    def profile(self, func_name: str, module: str = "") -> Generator[None, None, None]:
        """Context manager to profile a code block."""
        record = CallRecord(
            func_name=func_name,
            module=module,
            start_time=time.perf_counter(),
        )
        if self._call_stack:
            self._call_stack[-1].children.append(record)
        else:
            self._root_calls.append(record)
        self._call_stack.append(record)

        timer = self.get_timer(func_name)
        timer.start()
        try:
            yield
        finally:
            elapsed = timer.stop()
            record.end_time = time.perf_counter()
            self._call_stack.pop()
            self._hot_paths[func_name] += elapsed
            self._call_counts[func_name] += 1

    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile a function."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self.profile(func.__qualname__, func.__module__):
                return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        return wrapper

    def hot_paths(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Return the most time-consuming functions."""
        sorted_paths = sorted(self._hot_paths.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "function": name,
                "total_time_ms": round(total * 1000, 4),
                "call_count": self._call_counts[name],
                "avg_ms": round((total / max(self._call_counts[name], 1)) * 1000, 4),
            }
            for name, total in sorted_paths[:top_n]
        ]

    def call_graph(self, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Generate a call graph from root calls."""

        def _build(record: CallRecord, depth: int) -> Optional[Dict[str, Any]]:
            if depth > max_depth:
                return None
            node = {
                "function": record.func_name,
                "module": record.module,
                "duration_ms": round(record.duration * 1000, 4),
                "self_time_ms": round(record.self_time * 1000, 4),
                "children": [],
            }
            for child in record.children:
                child_node = _build(child, depth + 1)
                if child_node:
                    node["children"].append(child_node)
            return node

        return [_build(root, 0) for root in self._root_calls[-20:] if root is not None]

    def summary(self) -> Dict[str, Any]:
        return {
            "profiled_functions": len(self._timers),
            "total_calls": sum(self._call_counts.values()),
            "hot_paths": self.hot_paths(5),
            "timers": {
                name: timer.summary()
                for name, timer in sorted(
                    self._timers.items(),
                    key=lambda x: x[1].total,
                    reverse=True,
                )[:10]
            },
        }

    def reset(self) -> None:
        self._timers.clear()
        self._call_stack.clear()
        self._root_calls.clear()
        self._hot_paths.clear()
        self._call_counts.clear()


# ============================================================
# Frame Analyzer (SC2-Specific)
# ============================================================


@dataclass
class FrameBudget:
    """Time budget breakdown for a single SC2 game frame."""

    frame_id: int
    total_ms: float
    economy_ms: float = 0.0
    combat_ms: float = 0.0
    micro_ms: float = 0.0
    macro_ms: float = 0.0
    scouting_ms: float = 0.0
    planning_ms: float = 0.0
    other_ms: float = 0.0

    @property
    def accounted_ms(self) -> float:
        return (
            self.economy_ms
            + self.combat_ms
            + self.micro_ms
            + self.macro_ms
            + self.scouting_ms
            + self.planning_ms
            + self.other_ms
        )

    @property
    def unaccounted_ms(self) -> float:
        return max(self.total_ms - self.accounted_ms, 0.0)

    def to_dict(self) -> Dict[str, float]:
        return {
            "frame_id": self.frame_id,
            "total_ms": round(self.total_ms, 4),
            "economy_ms": round(self.economy_ms, 4),
            "combat_ms": round(self.combat_ms, 4),
            "micro_ms": round(self.micro_ms, 4),
            "macro_ms": round(self.macro_ms, 4),
            "scouting_ms": round(self.scouting_ms, 4),
            "planning_ms": round(self.planning_ms, 4),
            "other_ms": round(self.other_ms, 4),
            "unaccounted_ms": round(self.unaccounted_ms, 4),
        }


class FrameAnalyzer:
    """Analyze per-frame performance budget for SC2 bot.

    Breaks down each game frame's on_step() execution into
    subsystem categories to identify bottlenecks.
    """

    # SC2 runs at ~22.4 game loops per second; real-time step budget
    TARGET_FRAME_MS: float = 44.6  # ~1000/22.4

    def __init__(self, target_ms: Optional[float] = None) -> None:
        self._frames: List[FrameBudget] = []
        self._current_frame: Optional[FrameBudget] = None
        self._subsystem_timers: Dict[str, Timer] = {}
        self.target_ms = target_ms or self.TARGET_FRAME_MS
        self._frame_counter = 0
        self._slow_frames: List[FrameBudget] = []

    def begin_frame(self) -> int:
        """Start timing a new frame. Returns frame ID."""
        self._frame_counter += 1
        self._current_frame = FrameBudget(
            frame_id=self._frame_counter,
            total_ms=0.0,
        )
        self._frame_start = time.perf_counter()
        return self._frame_counter

    def end_frame(self) -> Optional[FrameBudget]:
        """End timing the current frame and record it."""
        if self._current_frame is None:
            return None
        elapsed = (time.perf_counter() - self._frame_start) * 1000
        self._current_frame.total_ms = elapsed
        self._frames.append(self._current_frame)
        if elapsed > self.target_ms:
            self._slow_frames.append(self._current_frame)
        result = self._current_frame
        self._current_frame = None
        return result

    @contextmanager
    def subsystem(self, name: str) -> Generator[None, None, None]:
        """Time a subsystem within the current frame.

        Supported subsystem names: economy, combat, micro, macro,
        scouting, planning, other.
        """
        if name not in self._subsystem_timers:
            self._subsystem_timers[name] = Timer(name)
        timer = self._subsystem_timers[name]
        timer.start()
        try:
            yield
        finally:
            elapsed_ms = timer.stop() * 1000
            if self._current_frame:
                attr = f"{name}_ms"
                if hasattr(self._current_frame, attr):
                    current = getattr(self._current_frame, attr)
                    setattr(self._current_frame, attr, current + elapsed_ms)
                else:
                    self._current_frame.other_ms += elapsed_ms

    @contextmanager
    def frame(self) -> Generator[int, None, None]:
        """Context manager for a complete frame cycle."""
        fid = self.begin_frame()
        try:
            yield fid
        finally:
            self.end_frame()

    def frame_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all frames."""
        if not self._frames:
            return {"total_frames": 0}
        totals = [f.total_ms for f in self._frames]
        return {
            "total_frames": len(self._frames),
            "mean_ms": round(statistics.mean(totals), 4),
            "median_ms": round(statistics.median(totals), 4),
            "std_dev_ms": (
                round(statistics.stdev(totals), 4) if len(totals) >= 2 else 0.0
            ),
            "min_ms": round(min(totals), 4),
            "max_ms": round(max(totals), 4),
            "slow_frames": len(self._slow_frames),
            "slow_pct": round(len(self._slow_frames) / len(self._frames) * 100, 2),
            "target_ms": self.target_ms,
        }

    def subsystem_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Average time per subsystem across all frames."""
        if not self._frames:
            return {}
        categories = [
            "economy",
            "combat",
            "micro",
            "macro",
            "scouting",
            "planning",
            "other",
        ]
        breakdown = {}
        for cat in categories:
            attr = f"{cat}_ms"
            values = [getattr(f, attr) for f in self._frames]
            total = sum(values)
            breakdown[cat] = {
                "total_ms": round(total, 4),
                "mean_ms": round(total / max(len(values), 1), 4),
                "max_ms": round(max(values), 4) if values else 0.0,
                "pct_of_frame": round(
                    total / max(sum(f.total_ms for f in self._frames), 0.001) * 100, 2
                ),
            }
        return breakdown

    def slow_frame_report(self, top_n: int = 10) -> List[Dict[str, float]]:
        """Report the slowest frames."""
        sorted_slow = sorted(self._slow_frames, key=lambda f: f.total_ms, reverse=True)
        return [f.to_dict() for f in sorted_slow[:top_n]]

    def reset(self) -> None:
        self._frames.clear()
        self._slow_frames.clear()
        self._subsystem_timers.clear()
        self._current_frame = None
        self._frame_counter = 0


# ============================================================
# Flame Graph Generator (Text-Based)
# ============================================================


class FlameGraphGenerator:
    """Generate text-based flame graph visualizations.

    Produces a hierarchical timing tree that can be printed
    to the console, similar to a collapsed flame graph format.
    """

    @staticmethod
    def from_call_records(
        records: List[CallRecord],
        min_pct: float = 1.0,
    ) -> str:
        """Build a text flame graph from call records."""
        if not records:
            return "(no data)"
        total_time = sum(r.duration for r in records)
        if total_time <= 0:
            return "(no measurable time)"
        lines: List[str] = []
        lines.append("Flame Graph (text-based)")
        lines.append("=" * 60)

        def _render(record: CallRecord, depth: int, parent_time: float) -> None:
            pct = (record.duration / max(parent_time, 1e-9)) * 100
            if pct < min_pct:
                return
            indent = "  " * depth
            bar_len = max(int(pct / 2), 1)
            bar = "#" * bar_len
            self_pct = (record.self_time / max(record.duration, 1e-9)) * 100
            lines.append(
                f"{indent}{bar} {record.func_name} "
                f"{record.duration*1000:.2f}ms ({pct:.1f}%) "
                f"[self: {record.self_time*1000:.2f}ms ({self_pct:.1f}%)]"
            )
            for child in sorted(
                record.children, key=lambda c: c.duration, reverse=True
            ):
                _render(child, depth + 1, record.duration)

        for root in records:
            _render(root, 0, total_time)

        lines.append("=" * 60)
        lines.append(f"Total: {total_time*1000:.2f}ms")
        return "\n".join(lines)

    @staticmethod
    def from_frame_budget(budget: FrameBudget) -> str:
        """Render a single frame budget as a flame-style bar chart."""
        lines: List[str] = []
        lines.append(f"Frame #{budget.frame_id} Budget ({budget.total_ms:.2f}ms)")
        lines.append("-" * 50)
        categories = [
            ("economy", budget.economy_ms),
            ("combat", budget.combat_ms),
            ("micro", budget.micro_ms),
            ("macro", budget.macro_ms),
            ("scouting", budget.scouting_ms),
            ("planning", budget.planning_ms),
            ("other", budget.other_ms),
            ("unaccounted", budget.unaccounted_ms),
        ]
        max_bar = 40
        total = max(budget.total_ms, 0.001)
        for name, ms in categories:
            if ms <= 0:
                continue
            pct = ms / total * 100
            bar_len = max(int(ms / total * max_bar), 1)
            bar = "#" * bar_len
            lines.append(f"  {name:>12s} |{bar:<{max_bar}s}| {ms:6.2f}ms ({pct:5.1f}%)")
        lines.append("-" * 50)
        return "\n".join(lines)

    @staticmethod
    def subsystem_chart(breakdown: Dict[str, Dict[str, Any]]) -> str:
        """Render subsystem breakdown as a horizontal bar chart."""
        lines: List[str] = []
        lines.append("Subsystem Breakdown (average per frame)")
        lines.append("=" * 55)
        max_bar = 35
        total_mean = sum(v["mean_ms"] for v in breakdown.values())
        if total_mean <= 0:
            return "(no data)"
        for name, data in sorted(
            breakdown.items(), key=lambda x: x[1]["mean_ms"], reverse=True
        ):
            mean = data["mean_ms"]
            pct = data["pct_of_frame"]
            bar_len = max(int(mean / max(total_mean, 0.001) * max_bar), 0)
            bar = "#" * bar_len
            lines.append(
                f"  {name:>12s} |{bar:<{max_bar}s}| {mean:6.2f}ms ({pct:5.1f}%)"
            )
        lines.append("=" * 55)
        return "\n".join(lines)


# ============================================================
# SC2 Profiler (Main Facade)
# ============================================================


class SC2Profiler:
    """Main profiler facade for SC2 bot optimization.

    Combines CPU profiling, memory tracking, frame analysis,
    and flame graph generation into a single interface.
    Designed to wrap a bot's on_step() and subsystem calls.
    """

    def __init__(self, target_frame_ms: Optional[float] = None) -> None:
        self.cpu = CPUProfiler()
        self.memory = MemoryTracker()
        self.frames = FrameAnalyzer(target_ms=target_frame_ms)
        self.flame = FlameGraphGenerator()
        self._enabled = True
        self._session_start = time.time()
        self._step_count = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @contextmanager
    def on_step(self) -> Generator[int, None, None]:
        """Profile a full on_step() iteration.

        Usage:
            with profiler.on_step() as frame_id:
                with profiler.subsystem("economy"):
                    manage_economy()
                with profiler.subsystem("combat"):
                    manage_combat()
        """
        if not self._enabled:
            self._step_count += 1
            yield self._step_count
            return
        self._step_count += 1
        with self.cpu.profile("on_step", "sc2_bot"):
            with self.frames.frame() as fid:
                yield fid

    @contextmanager
    def subsystem(self, name: str) -> Generator[None, None, None]:
        """Profile a subsystem within on_step()."""
        if not self._enabled:
            yield
            return
        with self.cpu.profile(f"subsystem.{name}", "sc2_bot"):
            with self.frames.subsystem(name):
                yield

    def profile_func(self, func: Callable) -> Callable:
        """Decorator to profile any function."""
        return self.cpu.profile_function(func)

    def memory_checkpoint(self, label: str = "") -> MemorySnapshot:
        """Take a memory checkpoint."""
        lbl = label or f"step_{self._step_count}"
        return self.memory.snapshot(lbl)

    def identify_slow_modules(
        self, threshold_pct: float = 20.0
    ) -> List[Dict[str, Any]]:
        """Identify subsystems that exceed the threshold percentage of frame time."""
        breakdown = self.frames.subsystem_breakdown()
        slow = []
        for name, data in breakdown.items():
            if data["pct_of_frame"] >= threshold_pct:
                slow.append(
                    {
                        "subsystem": name,
                        "pct_of_frame": data["pct_of_frame"],
                        "mean_ms": data["mean_ms"],
                        "max_ms": data["max_ms"],
                        "recommendation": self._recommend(name, data),
                    }
                )
        return sorted(slow, key=lambda x: x["pct_of_frame"], reverse=True)

    def _recommend(self, name: str, data: Dict[str, Any]) -> str:
        """Generate optimization recommendations for a slow subsystem."""
        recommendations = {
            "economy": "Consider caching worker assignments and reducing re-evaluation frequency.",
            "combat": "Batch unit commands and reduce per-unit decision loops.",
            "micro": "Use spatial hashing for nearby unit queries; reduce iteration count.",
            "macro": "Cache build order lookups; reduce structure placement calculations.",
            "scouting": "Lower scouting frequency in mid/late game; reuse path data.",
            "planning": "Pre-compute strategy decisions; use incremental replanning.",
            "other": "Profile individual functions to identify the specific bottleneck.",
        }
        base = recommendations.get(name, "Profile this subsystem in more detail.")
        if data["max_ms"] > self.frames.target_ms * 0.8:
            base += " CRITICAL: Single-frame spikes near full budget."
        return base

    def generate_flame_graph(self) -> str:
        """Generate a text-based flame graph from CPU profiler data."""
        records = self.cpu._root_calls[-30:]
        return self.flame.from_call_records(records)

    def generate_frame_chart(self) -> str:
        """Generate subsystem breakdown chart."""
        breakdown = self.frames.subsystem_breakdown()
        return self.flame.subsystem_chart(breakdown)

    def full_report(self) -> Dict[str, Any]:
        """Generate a comprehensive profiling report."""
        session_time = time.time() - self._session_start
        return {
            "session": {
                "duration_s": round(session_time, 2),
                "total_steps": self._step_count,
                "steps_per_second": round(
                    self._step_count / max(session_time, 0.001), 2
                ),
                "profiling_enabled": self._enabled,
            },
            "frames": self.frames.frame_stats(),
            "subsystems": self.frames.subsystem_breakdown(),
            "cpu": self.cpu.summary(),
            "memory": self.memory.report(),
            "slow_modules": self.identify_slow_modules(),
            "slow_frames": self.frames.slow_frame_report(5),
        }

    def reset(self) -> None:
        """Reset all profiling data."""
        self.cpu.reset()
        self.frames.reset()
        self._session_start = time.time()
        self._step_count = 0


# ============================================================
# Demo
# ============================================================


def _simulate_work(duration_ms: float) -> None:
    """Simulate CPU work for a given duration in milliseconds."""
    end = time.perf_counter() + duration_ms / 1000.0
    total = 0
    while time.perf_counter() < end:
        total += 1


def demo() -> None:
    """Demonstrate the Phase 659 Performance Profiler."""
    import random

    print("=" * 70)
    print("Phase 659: Performance Profiler for SC2 Bot Optimization")
    print("=" * 70)

    profiler = SC2Profiler(target_frame_ms=20.0)

    # --- Timer Demo ---
    print("\n[1] High-resolution Timer")
    timer = Timer("test_operation")
    for _ in range(10):
        with timer:
            _simulate_work(random.uniform(1.0, 5.0))
    summary = timer.summary()
    print(f"    Name: {summary['name']}")
    print(f"    Count: {summary['count']}")
    print(f"    Mean: {summary['mean_ms']:.3f}ms")
    print(f"    P95:  {summary['p95_ms']:.3f}ms")
    print(f"    P99:  {summary['p99_ms']:.3f}ms")

    # --- Memory Tracking ---
    print("\n[2] Memory Tracker")
    profiler.memory.set_baseline("start")
    profiler.memory.snapshot("before_alloc")
    _big_list = [i * i for i in range(100000)]
    profiler.memory.snapshot("after_alloc")
    profiler.memory.track_allocation("big_list", sys.getsizeof(_big_list))
    comparison = profiler.memory.compare_to_baseline("start")
    print(f"    Baseline: {comparison['baseline_mb']:.2f}MB")
    print(f"    Current:  {comparison['current_mb']:.2f}MB")
    print(f"    Diff:     {comparison['diff_mb']:.2f}MB")
    gc_info = profiler.memory.gc_pressure()
    print(f"    GC enabled: {gc_info['gc_enabled']}")
    print(f"    GC thresholds: {gc_info['thresholds']}")
    del _big_list

    # --- CPU Profiler ---
    print("\n[3] CPU Profiler (function-level timing)")
    with profiler.cpu.profile("strategy_planner", "ai_module"):
        _simulate_work(5.0)
        with profiler.cpu.profile("threat_analysis", "ai_module"):
            _simulate_work(2.0)
        with profiler.cpu.profile("build_order_eval", "ai_module"):
            _simulate_work(3.0)

    hot = profiler.cpu.hot_paths(5)
    print("    Hot paths:")
    for entry in hot:
        print(
            f"      {entry['function']}: {entry['total_time_ms']:.3f}ms ({entry['call_count']} calls)"
        )

    # --- Frame Analysis ---
    print("\n[4] Frame Analysis (simulating 20 on_step frames)")
    for i in range(20):
        with profiler.on_step() as fid:
            with profiler.subsystem("economy"):
                _simulate_work(random.uniform(1.0, 4.0))
            with profiler.subsystem("combat"):
                _simulate_work(random.uniform(2.0, 8.0))
            with profiler.subsystem("micro"):
                _simulate_work(random.uniform(0.5, 3.0))
            with profiler.subsystem("macro"):
                _simulate_work(random.uniform(1.0, 5.0))
            with profiler.subsystem("scouting"):
                _simulate_work(random.uniform(0.2, 1.5))
            with profiler.subsystem("planning"):
                _simulate_work(random.uniform(0.5, 2.0))

    stats = profiler.frames.frame_stats()
    print(f"    Total frames: {stats['total_frames']}")
    print(f"    Mean:  {stats['mean_ms']:.3f}ms")
    print(f"    Max:   {stats['max_ms']:.3f}ms")
    print(f"    Slow frames: {stats['slow_frames']} ({stats['slow_pct']:.1f}%)")
    print(f"    Target: {stats['target_ms']:.1f}ms")

    # --- Subsystem Breakdown ---
    print("\n[5] Subsystem Breakdown")
    chart = profiler.generate_frame_chart()
    for line in chart.split("\n"):
        print(f"    {line}")

    # --- Flame Graph ---
    print("\n[6] Flame Graph (text-based)")
    flame = profiler.generate_flame_graph()
    for line in flame.split("\n")[:15]:
        print(f"    {line}")
    if flame.count("\n") > 15:
        print(f"    ... ({flame.count(chr(10)) - 15} more lines)")

    # --- Slow Module Detection ---
    print("\n[7] Slow Module Identification")
    slow_modules = profiler.identify_slow_modules(threshold_pct=10.0)
    for mod in slow_modules:
        print(
            f"    {mod['subsystem']}: {mod['pct_of_frame']:.1f}% "
            f"(mean={mod['mean_ms']:.2f}ms, max={mod['max_ms']:.2f}ms)"
        )
        print(f"      -> {mod['recommendation'][:80]}")

    # --- Slow Frames ---
    print("\n[8] Slowest Frames Report")
    slow_frames = profiler.frames.slow_frame_report(3)
    for sf in slow_frames:
        print(
            f"    Frame #{int(sf['frame_id'])}: {sf['total_ms']:.2f}ms "
            f"(combat={sf['combat_ms']:.2f}, micro={sf['micro_ms']:.2f})"
        )

    # --- Full Report ---
    print("\n[9] Full Report Summary")
    report = profiler.full_report()
    print(
        f"    Session: {report['session']['duration_s']:.2f}s, "
        f"{report['session']['total_steps']} steps"
    )
    print(
        f"    CPU: {report['cpu']['profiled_functions']} functions, "
        f"{report['cpu']['total_calls']} total calls"
    )
    print(
        f"    Memory: {report['memory']['snapshots']} snapshots, "
        f"leak={report['memory']['leak_check']['leak_detected']}"
    )

    # --- Memory Leak Detection ---
    print("\n[10] Memory Leak Detection")
    leak_info = profiler.memory.detect_leak()
    print(f"    Leak detected: {leak_info['leak_detected']}")
    print(
        f"    Growth: {leak_info['growth_mb']:.2f}MB "
        f"(threshold: {leak_info['threshold_mb']:.1f}MB)"
    )

    print("\n" + "=" * 70)
    print("Phase 659 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 659: Profiler registered
