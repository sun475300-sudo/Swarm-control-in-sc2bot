#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atomic Telemetry Logger - thread-safe append-only JSONL log file.

Each call to log() atomically appends one JSON record to the log file.
Uses a queue + writer thread to avoid blocking the game loop.
"""

import json
import logging
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("TelemetryLoggerAtomic")

_SENTINEL = object()


class TelemetryLoggerAtomic:
    """
    Thread-safe telemetry logger that writes JSONL records asynchronously.

    Args:
        filepath: Path to the output .jsonl log file.
        max_queue_size: Maximum pending log entries before dropping.
    """

    def __init__(
        self,
        filepath: str = "telemetry.jsonl",
        max_queue_size: int = 1000,
    ) -> None:
        self.filepath = Path(filepath)
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._dropped: int = 0
        self._written: int = 0
        self._thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="TelemetryWriter",
        )
        self._thread.start()

    def log(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Enqueue a telemetry record for async write.

        Args:
            event: Event name / category string.
            data: Additional key-value data to include.
        """
        record = {
            "ts": datetime.utcnow().isoformat(),
            "event": event,
        }
        if data:
            record.update(data)

        try:
            self._queue.put_nowait(record)
        except queue.Full:
            self._dropped += 1
            logger.debug("TelemetryLoggerAtomic: queue full, dropped record '%s'", event)

    def flush(self) -> None:
        """Block until all queued records have been written."""
        self._queue.join()

    def close(self) -> None:
        """Stop the writer thread gracefully."""
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=5.0)

    def _writer_loop(self) -> None:
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "a", encoding="utf-8") as f:
                while True:
                    item = self._queue.get()
                    if item is _SENTINEL:
                        self._queue.task_done()
                        break
                    try:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                        f.flush()
                        self._written += 1
                    except Exception as exc:
                        logger.debug("TelemetryLoggerAtomic write error: %s", exc)
                    finally:
                        self._queue.task_done()
        except Exception as exc:
            logger.warning("TelemetryLoggerAtomic writer thread error: %s", exc)

    @property
    def stats(self) -> Dict[str, int]:
        return {"written": self._written, "dropped": self._dropped}


def main() -> None:
    tla = TelemetryLoggerAtomic("test_telemetry.jsonl")
    tla.log("game_start", {"map": "AcropolisLE", "opponent": "Zerg"})
    tla.flush()
    tla.close()
    logger.info("TelemetryLoggerAtomic test complete.")


if __name__ == "__main__":
    main()
