# -*- coding: utf-8 -*-
"""Lightweight memory monitoring for long-running SC2 sessions."""

from __future__ import annotations

import logging
import tracemalloc
from typing import List

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Track traced memory and flag large growth between samples."""

    def __init__(self, warn_threshold_mb: int = 200, leak_check_interval: int = 500):
        self.warn_threshold = int(warn_threshold_mb) * 1024 * 1024
        self.check_interval = max(1, int(leak_check_interval))
        self.snapshots: List[tracemalloc.Snapshot] = []
        if not tracemalloc.is_tracing():
            tracemalloc.start()

    def check(self, iteration: int) -> dict:
        if iteration % self.check_interval != 0:
            return {}

        current, peak = tracemalloc.get_traced_memory()
        result = {
            "current_bytes": current,
            "peak_bytes": peak,
            "over_threshold": current > self.warn_threshold,
            "leaks": [],
        }

        if result["over_threshold"]:
            logger.warning(
                "[MEM] High memory: %.1fMB (peak %.1fMB)",
                current / 1024 / 1024,
                peak / 1024 / 1024,
            )

        snapshot = tracemalloc.take_snapshot()
        if self.snapshots:
            top_stats = snapshot.compare_to(self.snapshots[-1], "lineno")
            leaks = [stat for stat in top_stats[:5] if stat.size_diff > 100_000]
            result["leaks"] = [str(stat) for stat in leaks]
            for stat in leaks:
                logger.warning("[MEM LEAK] %s", stat)

        self.snapshots.append(snapshot)
        if len(self.snapshots) > 10:
            self.snapshots.pop(0)
        return result

    def stop(self) -> None:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
