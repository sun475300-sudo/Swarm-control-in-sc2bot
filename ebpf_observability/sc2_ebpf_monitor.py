"""
Phase 652: eBPF Observability for SC2 Bot Process Monitoring

eBPF-based observability system providing low-overhead kernel and user-space
monitoring for StarCraft II bot processes. Captures syscall latency, network I/O,
file operations, memory allocation, and CPU usage with minimal performance impact.
"""

import time
import struct
import hashlib
import logging
import threading
import statistics
from enum import Enum, auto
from typing import Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------


class ProbeType(Enum):
    KPROBE = auto()
    KRETPROBE = auto()
    UPROBE = auto()
    URETPROBE = auto()
    TRACEPOINT = auto()
    RAW_TRACEPOINT = auto()
    PERF_EVENT = auto()


class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()
    SUMMARY = auto()


class BPFMapType(Enum):
    HASH = auto()
    ARRAY = auto()
    PERF_EVENT_ARRAY = auto()
    RING_BUFFER = auto()
    LRU_HASH = auto()
    PERCPU_HASH = auto()
    PERCPU_ARRAY = auto()


class MonitorTarget(Enum):
    SYSCALL_LATENCY = auto()
    NETWORK_IO = auto()
    FILE_OPS = auto()
    MEMORY_ALLOC = auto()
    CPU_SCHED = auto()
    SC2_PROCESS = auto()
    SC2_NETWORK = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BPFMapDef:
    """Definition of a BPF map used for kernel/user-space data sharing."""

    name: str
    map_type: BPFMapType
    key_size: int = 4
    value_size: int = 8
    max_entries: int = 1024


@dataclass
class ProbeEvent:
    """Single event captured by a probe."""

    timestamp_ns: int
    probe_name: str
    pid: int
    tid: int
    comm: str
    data: dict = field(default_factory=dict)
    latency_ns: int = 0


@dataclass
class HistogramBucket:
    """Bucket for histogram metric aggregation."""

    lower_bound: float
    upper_bound: float
    count: int = 0


@dataclass
class SC2ProcessInfo:
    """Information about a monitored SC2 bot process."""

    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    net_bytes_sent: int = 0
    net_bytes_recv: int = 0
    open_files: int = 0
    thread_count: int = 0
    syscall_count: int = 0
    last_update: float = 0.0


# ---------------------------------------------------------------------------
# BPFProgram
# ---------------------------------------------------------------------------


class BPFProgram:
    """
    Represents a compiled eBPF program that can be loaded into the kernel.
    Manages BPF maps for data exchange between kernel and user space.
    """

    def __init__(self, name: str, source: str = "", license_str: str = "GPL"):
        self.name = name
        self.source = source
        self.license_str = license_str
        self.program_id: Optional[int] = None
        self.maps: dict[str, BPFMapDef] = {}
        self._map_data: dict[str, dict] = defaultdict(dict)
        self._loaded = False
        self._compiled_bytecode: bytes = b""
        self._attach_points: list[str] = []
        logger.info("BPFProgram '%s' created", name)

    def add_map(self, map_def: BPFMapDef) -> None:
        """Register a BPF map definition with the program."""
        self.maps[map_def.name] = map_def
        self._map_data[map_def.name] = {}
        logger.debug(
            "Map '%s' (type=%s) added to program '%s'",
            map_def.name,
            map_def.map_type.name,
            self.name,
        )

    def compile(self) -> bytes:
        """Compile the BPF C source into bytecode (simulated)."""
        if not self.source:
            self.source = self._generate_default_source()
        raw = self.source.encode("utf-8")
        self._compiled_bytecode = hashlib.sha256(raw).digest() + raw[:256]
        logger.info(
            "Program '%s' compiled (%d bytes bytecode)",
            self.name,
            len(self._compiled_bytecode),
        )
        return self._compiled_bytecode

    def load(self) -> bool:
        """Load the compiled program into the kernel (simulated)."""
        if not self._compiled_bytecode:
            self.compile()
        self._loaded = True
        self.program_id = abs(hash(self.name)) % 100000
        logger.info("Program '%s' loaded with id=%d", self.name, self.program_id)
        return True

    def unload(self) -> bool:
        """Unload the program from the kernel."""
        if not self._loaded:
            return False
        self._loaded = False
        self.program_id = None
        logger.info("Program '%s' unloaded", self.name)
        return True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def map_update(
        self, map_name: str, key: Union[int, str], value: Union[int, float, bytes]
    ) -> None:
        """Update a value in a BPF map."""
        if map_name not in self.maps:
            raise KeyError(f"Map '{map_name}' not found in program '{self.name}'")
        self._map_data[map_name][key] = value

    def map_lookup(
        self, map_name: str, key: Union[int, str]
    ) -> Optional[Union[int, float, bytes]]:
        """Lookup a value in a BPF map."""
        if map_name not in self.maps:
            raise KeyError(f"Map '{map_name}' not found")
        return self._map_data[map_name].get(key)

    def map_delete(self, map_name: str, key: Union[int, str]) -> bool:
        """Delete a key from a BPF map."""
        if map_name not in self.maps:
            return False
        return self._map_data[map_name].pop(key, None) is not None

    def map_iterate(self, map_name: str):
        """Iterate over all entries in a BPF map."""
        if map_name not in self.maps:
            raise KeyError(f"Map '{map_name}' not found")
        yield from self._map_data[map_name].items()

    def _generate_default_source(self) -> str:
        """Generate default BPF C source for SC2 monitoring."""
        return (
            "/* Auto-generated eBPF program for SC2 bot monitoring */\n"
            "#include <linux/bpf.h>\n"
            "#include <linux/ptrace.h>\n"
            "BPF_HASH(syscall_latency, u32, u64);\n"
            "BPF_HASH(net_bytes, u32, u64);\n"
            "BPF_RINGBUF(events, 256 * 1024);\n"
            "int trace_syscall_entry(struct pt_regs *ctx) {\n"
            "    u64 ts = bpf_ktime_get_ns();\n"
            "    u32 pid = bpf_get_current_pid_tgid() >> 32;\n"
            "    syscall_latency.update(&pid, &ts);\n"
            "    return 0;\n"
            "}\n"
        )

    def get_stats(self) -> dict:
        """Return program statistics."""
        return {
            "name": self.name,
            "loaded": self._loaded,
            "program_id": self.program_id,
            "maps_count": len(self.maps),
            "bytecode_size": len(self._compiled_bytecode),
            "attach_points": len(self._attach_points),
        }


# ---------------------------------------------------------------------------
# ProbePoint
# ---------------------------------------------------------------------------


class ProbePoint:
    """
    Represents an eBPF probe attached to a kernel or user-space function.
    Collects events and timing information.
    """

    def __init__(
        self,
        name: str,
        probe_type: ProbeType,
        target: str,
        program: Optional[BPFProgram] = None,
    ):
        self.name = name
        self.probe_type = probe_type
        self.target = target
        self.program = program
        self._attached = False
        self._events: deque[ProbeEvent] = deque(maxlen=10000)
        self._hit_count = 0
        self._total_latency_ns = 0
        self._entry_timestamps: dict[int, int] = {}
        self._lock = threading.Lock()
        logger.info(
            "ProbePoint '%s' (type=%s, target='%s') created",
            name,
            probe_type.name,
            target,
        )

    def attach(self) -> bool:
        """Attach the probe to its target."""
        if self._attached:
            logger.warning("Probe '%s' already attached", self.name)
            return False
        if self.program and not self.program.is_loaded:
            logger.error("Program not loaded for probe '%s'", self.name)
            return False
        self._attached = True
        logger.info("Probe '%s' attached to '%s'", self.name, self.target)
        return True

    def detach(self) -> bool:
        """Detach the probe from its target."""
        if not self._attached:
            return False
        self._attached = False
        logger.info("Probe '%s' detached", self.name)
        return True

    @property
    def is_attached(self) -> bool:
        return self._attached

    def record_entry(self, pid: int, tid: int, comm: str) -> None:
        """Record a function entry event for latency measurement."""
        ts = time.time_ns()
        with self._lock:
            self._entry_timestamps[tid] = ts
            self._hit_count += 1

    def record_exit(
        self, pid: int, tid: int, comm: str, data: Optional[dict] = None
    ) -> Optional[ProbeEvent]:
        """Record a function exit event and compute latency."""
        ts = time.time_ns()
        with self._lock:
            entry_ts = self._entry_timestamps.pop(tid, None)
            if entry_ts is None:
                return None
            latency_ns = ts - entry_ts
            self._total_latency_ns += latency_ns

        event = ProbeEvent(
            timestamp_ns=ts,
            probe_name=self.name,
            pid=pid,
            tid=tid,
            comm=comm,
            data=data or {},
            latency_ns=latency_ns,
        )
        self._events.append(event)
        return event

    def record_event(
        self, pid: int, tid: int, comm: str, data: Optional[dict] = None
    ) -> ProbeEvent:
        """Record a single probe event without entry/exit pairing."""
        ts = time.time_ns()
        with self._lock:
            self._hit_count += 1
        event = ProbeEvent(
            timestamp_ns=ts,
            probe_name=self.name,
            pid=pid,
            tid=tid,
            comm=comm,
            data=data or {},
        )
        self._events.append(event)
        return event

    def get_events(self, limit: int = 100) -> list[ProbeEvent]:
        """Return the most recent events."""
        events = list(self._events)
        return events[-limit:]

    def get_stats(self) -> dict:
        """Return probe statistics."""
        latencies = [e.latency_ns for e in self._events if e.latency_ns > 0]
        return {
            "name": self.name,
            "type": self.probe_type.name,
            "target": self.target,
            "attached": self._attached,
            "hit_count": self._hit_count,
            "event_count": len(self._events),
            "avg_latency_us": (
                (statistics.mean(latencies) / 1000.0) if latencies else 0.0
            ),
            "p50_latency_us": (
                (statistics.median(latencies) / 1000.0) if latencies else 0.0
            ),
            "p99_latency_us": (
                statistics.quantiles(latencies, n=100)[-1] / 1000.0
                if len(latencies) >= 2
                else 0.0
            ),
            "total_latency_ms": self._total_latency_ns / 1_000_000.0,
        }

    def clear(self) -> None:
        """Clear all recorded events and counters."""
        with self._lock:
            self._events.clear()
            self._hit_count = 0
            self._total_latency_ns = 0
            self._entry_timestamps.clear()


# ---------------------------------------------------------------------------
# MetricCollector
# ---------------------------------------------------------------------------


class MetricCollector:
    """
    Aggregates metrics from eBPF probes into counters, gauges, histograms,
    and summaries. Uses a ring buffer for efficient data collection.
    """

    DEFAULT_HISTOGRAM_BOUNDS = [
        0.001,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        25.0,
        50.0,
        100.0,
    ]

    def __init__(self, ring_buffer_size: int = 65536):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[HistogramBucket]] = {}
        self._histogram_sums: dict[str, float] = defaultdict(float)
        self._histogram_counts: dict[str, int] = defaultdict(int)
        self._summaries: dict[str, deque] = {}
        self._ring_buffer: deque = deque(maxlen=ring_buffer_size)
        self._labels: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()
        self._collection_interval_sec = 1.0
        self._running = False
        logger.info(
            "MetricCollector initialised (ring_buffer_size=%d)", ring_buffer_size
        )

    # -- Counter --------------------------------------------------------

    def counter_inc(
        self, name: str, value: float = 1.0, labels: Optional[dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        key = self._label_key(name, labels)
        with self._lock:
            self._counters[key] += value
        if labels:
            self._labels[key] = labels

    def counter_get(self, name: str, labels: Optional[dict[str, str]] = None) -> float:
        key = self._label_key(name, labels)
        return self._counters.get(key, 0.0)

    # -- Gauge ----------------------------------------------------------

    def gauge_set(
        self, name: str, value: float, labels: Optional[dict[str, str]] = None
    ) -> None:
        """Set a gauge metric to an absolute value."""
        key = self._label_key(name, labels)
        with self._lock:
            self._gauges[key] = value
        if labels:
            self._labels[key] = labels

    def gauge_inc(
        self, name: str, value: float = 1.0, labels: Optional[dict[str, str]] = None
    ) -> None:
        key = self._label_key(name, labels)
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0.0) + value

    def gauge_get(self, name: str, labels: Optional[dict[str, str]] = None) -> float:
        key = self._label_key(name, labels)
        return self._gauges.get(key, 0.0)

    # -- Histogram ------------------------------------------------------

    def histogram_create(self, name: str, bounds: Optional[list[float]] = None) -> None:
        """Create a histogram metric with specified bucket bounds."""
        bounds = bounds or self.DEFAULT_HISTOGRAM_BOUNDS
        buckets: list[HistogramBucket] = []
        prev = 0.0
        for b in sorted(bounds):
            buckets.append(HistogramBucket(lower_bound=prev, upper_bound=b))
            prev = b
        buckets.append(HistogramBucket(lower_bound=prev, upper_bound=float("inf")))
        self._histograms[name] = buckets

    def histogram_observe(self, name: str, value: float) -> None:
        """Record an observation in a histogram."""
        if name not in self._histograms:
            self.histogram_create(name)
        with self._lock:
            self._histogram_sums[name] += value
            self._histogram_counts[name] += 1
            for bucket in self._histograms[name]:
                if value <= bucket.upper_bound:
                    bucket.count += 1
                    break

    def histogram_get(self, name: str) -> dict:
        """Return histogram data including buckets, sum, and count."""
        if name not in self._histograms:
            return {}
        return {
            "buckets": [
                {"le": b.upper_bound, "count": b.count} for b in self._histograms[name]
            ],
            "sum": self._histogram_sums.get(name, 0.0),
            "count": self._histogram_counts.get(name, 0),
        }

    # -- Summary --------------------------------------------------------

    def summary_observe(self, name: str, value: float, window: int = 1000) -> None:
        """Record an observation for a summary metric."""
        if name not in self._summaries:
            self._summaries[name] = deque(maxlen=window)
        self._summaries[name].append(value)

    def summary_get(self, name: str) -> dict:
        """Return summary quantiles (p50, p90, p99)."""
        if name not in self._summaries or not self._summaries[name]:
            return {}
        values = sorted(self._summaries[name])
        n = len(values)
        return {
            "count": n,
            "sum": sum(values),
            "p50": values[n // 2],
            "p90": values[int(n * 0.9)],
            "p99": values[min(int(n * 0.99), n - 1)],
            "min": values[0],
            "max": values[-1],
        }

    # -- Ring Buffer ----------------------------------------------------

    def ring_buffer_push(self, data: dict) -> None:
        """Push a data record into the ring buffer."""
        record = {"timestamp": time.time(), **data}
        self._ring_buffer.append(record)

    def ring_buffer_drain(self, max_items: int = 256) -> list[dict]:
        """Drain up to max_items from the ring buffer."""
        items: list[dict] = []
        with self._lock:
            for _ in range(min(max_items, len(self._ring_buffer))):
                items.append(self._ring_buffer.popleft())
        return items

    def ring_buffer_size(self) -> int:
        return len(self._ring_buffer)

    # -- Export ---------------------------------------------------------

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text exposition format."""
        lines: list[str] = []
        for key, val in sorted(self._counters.items()):
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {val}")
        for key, val in sorted(self._gauges.items()):
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {val}")
        for name, buckets in sorted(self._histograms.items()):
            lines.append(f"# TYPE {name} histogram")
            for b in buckets:
                le = f"+Inf" if b.upper_bound == float("inf") else f"{b.upper_bound}"
                lines.append(f'{name}_bucket{{le="{le}"}} {b.count}')
            lines.append(f"{name}_sum {self._histogram_sums.get(name, 0.0)}")
            lines.append(f"{name}_count {self._histogram_counts.get(name, 0)}")
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._histogram_sums.clear()
            self._histogram_counts.clear()
            self._summaries.clear()
            self._ring_buffer.clear()

    # -- Helpers --------------------------------------------------------

    @staticmethod
    def _label_key(name: str, labels: Optional[dict[str, str]] = None) -> str:
        if not labels:
            return name
        suffix = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{suffix}}}"


# ---------------------------------------------------------------------------
# TraceViewer
# ---------------------------------------------------------------------------


class TraceViewer:
    """
    Visualises and analyses trace data from eBPF probes.
    Provides timeline views, flamegraph data, and anomaly detection.
    """

    def __init__(self, max_spans: int = 50000):
        self._spans: deque[dict] = deque(maxlen=max_spans)
        self._filters: dict[str, object] = {}
        self._anomaly_thresholds: dict[str, float] = {}
        self._annotations: list[dict] = []
        logger.info("TraceViewer created (max_spans=%d)", max_spans)

    def add_span(
        self,
        name: str,
        start_ns: int,
        end_ns: int,
        pid: int = 0,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Add a trace span for timeline visualisation."""
        span = {
            "name": name,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "duration_us": (end_ns - start_ns) / 1000.0,
            "pid": pid,
            "metadata": metadata or {},
        }
        self._spans.append(span)
        self._check_anomaly(span)
        return span

    def add_spans_from_events(self, events: list[ProbeEvent]) -> int:
        """Bulk-add spans from ProbeEvent objects."""
        count = 0
        for ev in events:
            if ev.latency_ns > 0:
                start = ev.timestamp_ns - ev.latency_ns
                self.add_span(
                    name=ev.probe_name,
                    start_ns=start,
                    end_ns=ev.timestamp_ns,
                    pid=ev.pid,
                    metadata=ev.data,
                )
                count += 1
        return count

    def set_anomaly_threshold(self, span_name: str, max_duration_us: float) -> None:
        """Set latency threshold for anomaly detection on a span type."""
        self._anomaly_thresholds[span_name] = max_duration_us
        logger.info("Anomaly threshold for '%s': %.1f us", span_name, max_duration_us)

    def _check_anomaly(self, span: dict) -> None:
        threshold = self._anomaly_thresholds.get(span["name"])
        if threshold and span["duration_us"] > threshold:
            annotation = {
                "type": "anomaly",
                "span_name": span["name"],
                "duration_us": span["duration_us"],
                "threshold_us": threshold,
                "pid": span["pid"],
                "timestamp_ns": span["end_ns"],
            }
            self._annotations.append(annotation)
            logger.warning(
                "Anomaly detected: %s took %.1f us (threshold %.1f us)",
                span["name"],
                span["duration_us"],
                threshold,
            )

    def get_timeline(
        self,
        pid: Optional[int] = None,
        start_ns: Optional[int] = None,
        end_ns: Optional[int] = None,
        limit: int = 500,
    ) -> list[dict]:
        """Return filtered timeline spans."""
        result: list[dict] = []
        for span in self._spans:
            if pid is not None and span["pid"] != pid:
                continue
            if start_ns is not None and span["end_ns"] < start_ns:
                continue
            if end_ns is not None and span["start_ns"] > end_ns:
                continue
            result.append(span)
            if len(result) >= limit:
                break
        return result

    def build_flamegraph(self, pid: Optional[int] = None) -> dict:
        """Build a simplified flamegraph data structure from collected spans."""
        stacks: dict[str, float] = defaultdict(float)
        for span in self._spans:
            if pid is not None and span["pid"] != pid:
                continue
            stacks[span["name"]] += span["duration_us"]
        sorted_stacks = sorted(stacks.items(), key=lambda x: -x[1])
        total_us = sum(v for _, v in sorted_stacks) or 1.0
        return {
            "total_us": total_us,
            "stacks": [
                {"name": name, "duration_us": dur, "pct": dur / total_us * 100.0}
                for name, dur in sorted_stacks
            ],
        }

    def get_anomalies(self, limit: int = 100) -> list[dict]:
        """Return detected anomalies."""
        return self._annotations[-limit:]

    def get_summary(self) -> dict:
        """Return a summary of all trace data."""
        durations = [s["duration_us"] for s in self._spans]
        return {
            "total_spans": len(self._spans),
            "total_anomalies": len(self._annotations),
            "avg_duration_us": statistics.mean(durations) if durations else 0.0,
            "max_duration_us": max(durations) if durations else 0.0,
            "unique_probes": len({s["name"] for s in self._spans}),
        }

    def clear(self) -> None:
        self._spans.clear()
        self._annotations.clear()


# ---------------------------------------------------------------------------
# eBPFMonitor  (main orchestrator)
# ---------------------------------------------------------------------------


class eBPFMonitor:
    """
    Main eBPF monitoring system for SC2 bot processes.

    Orchestrates BPF programs, probes, metric collection, and trace viewing
    to provide comprehensive, low-overhead observability of the SC2 bot.
    """

    SYSCALL_PROBES = [
        ("sys_read", "read"),
        ("sys_write", "write"),
        ("sys_recvmsg", "recvmsg"),
        ("sys_sendmsg", "sendmsg"),
        ("sys_openat", "openat"),
        ("sys_close", "close"),
        ("sys_mmap", "mmap"),
        ("sys_munmap", "munmap"),
        ("sys_nanosleep", "nanosleep"),
        ("sys_futex", "futex"),
    ]

    def __init__(self, sc2_pid: Optional[int] = None, collection_interval: float = 1.0):
        self.sc2_pid = sc2_pid
        self.collection_interval = collection_interval

        self._programs: dict[str, BPFProgram] = {}
        self._probes: dict[str, ProbePoint] = {}
        self._collector = MetricCollector()
        self._viewer = TraceViewer()
        self._sc2_info: Optional[SC2ProcessInfo] = None
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._setup_default_programs()
        logger.info("eBPFMonitor created (sc2_pid=%s)", sc2_pid)

    # -- Setup ----------------------------------------------------------

    def _setup_default_programs(self) -> None:
        """Create default BPF programs for SC2 monitoring."""
        # Syscall latency program
        syscall_prog = BPFProgram("sc2_syscall_latency")
        syscall_prog.add_map(
            BPFMapDef("latency_map", BPFMapType.HASH, max_entries=4096)
        )
        syscall_prog.add_map(
            BPFMapDef(
                "events", BPFMapType.RING_BUFFER, value_size=256, max_entries=256 * 1024
            )
        )
        self._programs["syscall_latency"] = syscall_prog

        # Network I/O program
        net_prog = BPFProgram("sc2_network_io")
        net_prog.add_map(BPFMapDef("bytes_sent", BPFMapType.PERCPU_HASH))
        net_prog.add_map(BPFMapDef("bytes_recv", BPFMapType.PERCPU_HASH))
        net_prog.add_map(BPFMapDef("conn_latency", BPFMapType.HASH))
        self._programs["network_io"] = net_prog

        # Memory allocation program
        mem_prog = BPFProgram("sc2_memory_alloc")
        mem_prog.add_map(BPFMapDef("alloc_sizes", BPFMapType.HASH, max_entries=8192))
        mem_prog.add_map(BPFMapDef("alloc_histogram", BPFMapType.ARRAY))
        self._programs["memory_alloc"] = mem_prog

        # File operations program
        file_prog = BPFProgram("sc2_file_ops")
        file_prog.add_map(BPFMapDef("file_latency", BPFMapType.HASH))
        file_prog.add_map(BPFMapDef("open_files", BPFMapType.LRU_HASH))
        self._programs["file_ops"] = file_prog

        # Histograms for metric collection
        self._collector.histogram_create(
            "syscall_latency_us", [1, 5, 10, 25, 50, 100, 500, 1000, 5000]
        )
        self._collector.histogram_create(
            "net_latency_us", [10, 50, 100, 500, 1000, 5000, 10000, 50000]
        )
        self._collector.histogram_create(
            "alloc_size_bytes", [64, 256, 1024, 4096, 16384, 65536, 262144]
        )

    def _setup_probes(self) -> None:
        """Create and attach probes for all monitored syscalls."""
        prog = self._programs["syscall_latency"]
        for func, label in self.SYSCALL_PROBES:
            kp = ProbePoint(f"kprobe_{label}", ProbeType.KPROBE, func, prog)
            krp = ProbePoint(f"kretprobe_{label}", ProbeType.KRETPROBE, func, prog)
            kp.attach()
            krp.attach()
            self._probes[f"kprobe_{label}"] = kp
            self._probes[f"kretprobe_{label}"] = krp

        # User-space probes for SC2 bot functions
        uprobe_targets = [
            ("bot_on_step", "on_step"),
            ("bot_build_order", "execute_build_order"),
            ("bot_micro", "execute_micro"),
            ("bot_macro", "execute_macro"),
        ]
        prog_mem = self._programs["memory_alloc"]
        for name, func in uprobe_targets:
            up = ProbePoint(f"uprobe_{name}", ProbeType.UPROBE, func, prog_mem)
            urp = ProbePoint(f"uretprobe_{name}", ProbeType.URETPROBE, func, prog_mem)
            up.attach()
            urp.attach()
            self._probes[f"uprobe_{name}"] = up
            self._probes[f"uretprobe_{name}"] = urp

    # -- Lifecycle ------------------------------------------------------

    def start(self) -> bool:
        """Start the eBPF monitor. Load programs and attach probes."""
        if self._running:
            logger.warning("eBPFMonitor already running")
            return False

        # Load programs
        for name, prog in self._programs.items():
            prog.compile()
            prog.load()
            logger.info("Program '%s' started", name)

        self._setup_probes()

        if self.sc2_pid:
            self._sc2_info = SC2ProcessInfo(
                pid=self.sc2_pid,
                name="SC2_Bot",
                last_update=time.time(),
            )

        # Anomaly thresholds
        self._viewer.set_anomaly_threshold("kretprobe_read", 5000.0)
        self._viewer.set_anomaly_threshold("kretprobe_write", 5000.0)
        self._viewer.set_anomaly_threshold("kretprobe_recvmsg", 10000.0)
        self._viewer.set_anomaly_threshold("uretprobe_bot_on_step", 50000.0)

        self._running = True
        self._collection_thread = threading.Thread(
            target=self._collection_loop, daemon=True
        )
        self._collection_thread.start()
        logger.info(
            "eBPFMonitor started (%d programs, %d probes)",
            len(self._programs),
            len(self._probes),
        )
        return True

    def stop(self) -> None:
        """Stop the monitor and detach all probes."""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5.0)
        for probe in self._probes.values():
            probe.detach()
        for prog in self._programs.values():
            prog.unload()
        logger.info("eBPFMonitor stopped")

    # -- Collection Loop ------------------------------------------------

    def _collection_loop(self) -> None:
        """Background thread collecting simulated metrics."""
        import random

        cycle = 0
        while self._running:
            cycle += 1
            ts = time.time()

            # Simulate syscall events
            for _, label in self.SYSCALL_PROBES:
                pid = self.sc2_pid or 12345
                tid = pid + random.randint(0, 7)
                latency_us = random.lognormvariate(3.0, 1.5)

                kp = self._probes.get(f"kprobe_{label}")
                krp = self._probes.get(f"kretprobe_{label}")
                if kp and krp:
                    kp.record_entry(pid, tid, label)
                    time.sleep(0.0001)
                    event = krp.record_exit(pid, tid, label, {"syscall": label})
                    if event:
                        self._collector.histogram_observe(
                            "syscall_latency_us", latency_us
                        )
                        self._collector.counter_inc(
                            "syscall_total", labels={"syscall": label}
                        )
                        self._viewer.add_span(
                            f"kretprobe_{label}",
                            event.timestamp_ns - event.latency_ns,
                            event.timestamp_ns,
                            pid=pid,
                        )

            # Simulate network metrics
            net_sent = random.randint(64, 4096)
            net_recv = random.randint(128, 8192)
            net_lat = random.lognormvariate(5.0, 1.0)
            self._collector.counter_inc("net_bytes_sent", net_sent)
            self._collector.counter_inc("net_bytes_recv", net_recv)
            self._collector.histogram_observe("net_latency_us", net_lat)
            self._collector.gauge_set("net_connections_active", random.randint(1, 5))

            # Simulate memory metrics
            alloc_size = random.choice([64, 128, 256, 512, 1024, 4096, 16384])
            self._collector.histogram_observe("alloc_size_bytes", alloc_size)
            self._collector.gauge_set("memory_rss_mb", random.uniform(150.0, 350.0))

            # SC2 process info
            if self._sc2_info:
                self._sc2_info.cpu_percent = random.uniform(10.0, 85.0)
                self._sc2_info.memory_mb = random.uniform(200.0, 400.0)
                self._sc2_info.net_bytes_sent += net_sent
                self._sc2_info.net_bytes_recv += net_recv
                self._sc2_info.syscall_count += len(self.SYSCALL_PROBES)
                self._sc2_info.thread_count = random.randint(4, 16)
                self._sc2_info.open_files = random.randint(10, 60)
                self._sc2_info.last_update = ts

                self._collector.gauge_set("sc2_cpu_percent", self._sc2_info.cpu_percent)
                self._collector.gauge_set("sc2_memory_mb", self._sc2_info.memory_mb)

            # Push to ring buffer
            self._collector.ring_buffer_push(
                {
                    "cycle": cycle,
                    "syscall_events": len(self.SYSCALL_PROBES),
                    "net_sent": net_sent,
                    "net_recv": net_recv,
                }
            )

            time.sleep(self.collection_interval)

    # -- Queries --------------------------------------------------------

    def get_sc2_process_info(self) -> Optional[dict]:
        """Return current SC2 process information."""
        if not self._sc2_info:
            return None
        info = self._sc2_info
        return {
            "pid": info.pid,
            "name": info.name,
            "cpu_percent": round(info.cpu_percent, 2),
            "memory_mb": round(info.memory_mb, 2),
            "net_bytes_sent": info.net_bytes_sent,
            "net_bytes_recv": info.net_bytes_recv,
            "open_files": info.open_files,
            "thread_count": info.thread_count,
            "syscall_count": info.syscall_count,
            "uptime_sec": round(time.time() - info.last_update, 1),
        }

    def get_probe_stats(self) -> dict[str, dict]:
        """Return statistics for all attached probes."""
        return {name: probe.get_stats() for name, probe in self._probes.items()}

    def get_program_stats(self) -> dict[str, dict]:
        """Return statistics for all loaded BPF programs."""
        return {name: prog.get_stats() for name, prog in self._programs.items()}

    def get_syscall_latency_summary(self) -> dict:
        """Return syscall latency histogram data."""
        return self._collector.histogram_get("syscall_latency_us")

    def get_network_latency_summary(self) -> dict:
        """Return network latency histogram data."""
        return self._collector.histogram_get("net_latency_us")

    def get_trace_timeline(self, limit: int = 200) -> list[dict]:
        """Return recent trace spans."""
        return self._viewer.get_timeline(pid=self.sc2_pid, limit=limit)

    def get_flamegraph(self) -> dict:
        """Return flamegraph data for the SC2 process."""
        return self._viewer.build_flamegraph(pid=self.sc2_pid)

    def get_anomalies(self) -> list[dict]:
        """Return detected anomalies."""
        return self._viewer.get_anomalies()

    def export_metrics(self) -> str:
        """Export all metrics in Prometheus format."""
        return self._collector.export_prometheus()

    def get_full_report(self) -> dict:
        """Generate a comprehensive monitoring report."""
        return {
            "monitor": {
                "sc2_pid": self.sc2_pid,
                "running": self._running,
                "programs": len(self._programs),
                "probes": len(self._probes),
                "collection_interval": self.collection_interval,
            },
            "sc2_process": self.get_sc2_process_info(),
            "syscall_latency": self.get_syscall_latency_summary(),
            "network_latency": self.get_network_latency_summary(),
            "trace_summary": self._viewer.get_summary(),
            "anomalies": self.get_anomalies()[:10],
            "ring_buffer_size": self._collector.ring_buffer_size(),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate eBPF-based SC2 bot process monitoring."""
    import json

    print("=" * 70)
    print("Phase 652: eBPF Observability for SC2 Bot Process Monitoring")
    print("=" * 70)

    # 1. BPFProgram
    print("\n[1] BPF Program Management")
    prog = BPFProgram("demo_prog", license_str="GPL")
    prog.add_map(BPFMapDef("test_map", BPFMapType.HASH, max_entries=256))
    prog.compile()
    prog.load()
    prog.map_update("test_map", 1, 42)
    print(f"  Program stats: {prog.get_stats()}")
    print(f"  Map lookup key=1: {prog.map_lookup('test_map', 1)}")

    # 2. ProbePoint
    print("\n[2] Probe Point Tracing")
    probe = ProbePoint("demo_kprobe", ProbeType.KPROBE, "sys_read", prog)
    probe.attach()
    for i in range(5):
        pid, tid = 1000, 1000 + i
        probe.record_entry(pid, tid, "reader")
        time.sleep(0.001)
        probe.record_exit(pid, tid, "reader", {"fd": i})
    stats = probe.get_stats()
    print(
        f"  Probe stats: hit_count={stats['hit_count']}, "
        f"avg_latency={stats['avg_latency_us']:.1f} us"
    )

    # 3. MetricCollector
    print("\n[3] Metric Collection")
    collector = MetricCollector()
    collector.counter_inc("requests_total", 10)
    collector.gauge_set("cpu_usage", 45.7)
    collector.histogram_create("response_time_ms", [1, 5, 10, 50, 100])
    for v in [2.1, 3.5, 7.8, 12.0, 55.0, 1.2, 0.9]:
        collector.histogram_observe("response_time_ms", v)
    collector.ring_buffer_push({"event": "test", "value": 123})
    print(f"  Counter requests_total: {collector.counter_get('requests_total')}")
    print(f"  Gauge cpu_usage: {collector.gauge_get('cpu_usage')}")
    print(f"  Histogram: {collector.histogram_get('response_time_ms')}")
    print(f"  Ring buffer size: {collector.ring_buffer_size()}")

    # 4. TraceViewer
    print("\n[4] Trace Viewer")
    viewer = TraceViewer()
    viewer.set_anomaly_threshold("slow_call", 100.0)
    base_ns = time.time_ns()
    for i in range(10):
        dur = (i + 1) * 20 * 1000  # 20-200 us
        viewer.add_span(
            "slow_call" if dur > 100000 else "fast_call",
            base_ns + i * 1_000_000,
            base_ns + i * 1_000_000 + dur,
            pid=9999,
        )
    flamegraph = viewer.build_flamegraph()
    print(f"  Trace summary: {viewer.get_summary()}")
    print(f"  Flamegraph stacks: {len(flamegraph['stacks'])}")
    print(f"  Anomalies: {len(viewer.get_anomalies())}")

    # 5. Full eBPFMonitor
    print("\n[5] SC2 eBPF Monitor (3 second run)")
    monitor = eBPFMonitor(sc2_pid=31337, collection_interval=0.5)
    monitor.start()
    time.sleep(3)
    monitor.stop()

    report = monitor.get_full_report()
    print(f"  Programs: {report['monitor']['programs']}")
    print(f"  Probes: {report['monitor']['probes']}")
    if report["sc2_process"]:
        p = report["sc2_process"]
        print(
            f"  SC2 PID {p['pid']}: CPU={p['cpu_percent']}%, "
            f"MEM={p['memory_mb']} MB, Syscalls={p['syscall_count']}"
        )
    print(f"  Trace spans: {report['trace_summary']['total_spans']}")
    print(f"  Anomalies: {report['trace_summary']['total_anomalies']}")
    print(f"  Ring buffer records: {report['ring_buffer_size']}")

    # Prometheus export (first 10 lines)
    prom = monitor.export_metrics()
    prom_lines = prom.strip().split("\n")[:10]
    print(f"\n  Prometheus export ({len(prom.split(chr(10)))} lines, first 10):")
    for line in prom_lines:
        print(f"    {line}")

    print("\n" + "=" * 70)
    print("Phase 652: eBPF Observability demo complete")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    demo()

# Phase 652: eBPF registered
