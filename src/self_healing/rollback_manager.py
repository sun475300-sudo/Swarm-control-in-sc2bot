"""Snapshot + rollback manager for self-healing state."""

from __future__ import annotations

import copy
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Snapshot:
    label: str
    state: Any
    timestamp: float


class RollbackManager:
    """Stores up to ``capacity`` deep-copied state snapshots, FIFO eviction."""

    name = "rollback_manager"

    def __init__(self, capacity: int = 16) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._snapshots: "OrderedDict[str, Snapshot]" = OrderedDict()

    def __len__(self) -> int:
        return len(self._snapshots)

    def snapshot(self, label: str, state: Any) -> Snapshot:
        if not label:
            raise ValueError("label must be non-empty")
        snap = Snapshot(label=label, state=copy.deepcopy(state), timestamp=time.time())
        if label in self._snapshots:
            self._snapshots.move_to_end(label)
        self._snapshots[label] = snap
        if len(self._snapshots) > self._capacity:
            self._snapshots.popitem(last=False)
        return snap

    def list_labels(self) -> List[str]:
        return list(self._snapshots.keys())

    def get(self, label: str) -> Optional[Snapshot]:
        return self._snapshots.get(label)

    def rollback(self, label: str) -> Any:
        if label not in self._snapshots:
            raise KeyError(f"no snapshot labelled {label!r}")
        return copy.deepcopy(self._snapshots[label].state)

    def latest(self) -> Optional[Snapshot]:
        if not self._snapshots:
            return None
        last_key = next(reversed(self._snapshots))
        return self._snapshots[last_key]

    def clear(self) -> None:
        self._snapshots.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {label: snap.state for label, snap in self._snapshots.items()}
