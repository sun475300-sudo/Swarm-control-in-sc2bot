# Phase 650: Digital Twin for SC2 Game State Mirroring
# Real-time digital twin that mirrors live SC2 game state for analysis and prediction

from __future__ import annotations

import copy
import json
import math
import os
import random
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import numpy as np

    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

# ============================================================
# NumPy Fallback Utilities
# ============================================================


def _np_mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _np_std(values: list) -> float:
    if not values:
        return 0.0
    m = _np_mean(values)
    var = sum((v - m) ** 2 for v in values) / max(len(values), 1)
    return math.sqrt(var)


def _euclidean_dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a < 1e-12 or mag_b < 1e-12:
        return 0.0
    return dot / (mag_a * mag_b)


# ============================================================
# UnitSnapshot: Snapshot of a single SC2 unit
# ============================================================


@dataclass
class UnitSnapshot:
    """Snapshot of a single unit at a given game tick."""

    unit_id: int
    unit_type: str
    owner: int  # player id
    position: Tuple[float, float] = (0.0, 0.0)
    health: float = 100.0
    max_health: float = 100.0
    shield: float = 0.0
    energy: float = 0.0
    is_alive: bool = True
    orders: List[str] = field(default_factory=list)
    buffs: List[str] = field(default_factory=list)
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "owner": self.owner,
            "position": list(self.position),
            "health": self.health,
            "max_health": self.max_health,
            "shield": self.shield,
            "energy": self.energy,
            "is_alive": self.is_alive,
            "orders": self.orders,
            "buffs": self.buffs,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UnitSnapshot":
        d = dict(d)
        d["position"] = tuple(d.get("position", [0.0, 0.0]))
        return cls(**d)


# ============================================================
# TwinState: Full mirrored game state
# ============================================================


@dataclass
class TwinState:
    """Complete mirrored state of an SC2 game at a point in time."""

    game_loop: int = 0
    timestamp: float = 0.0
    twin_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # Resources per player (player_id -> resource dict)
    resources: Dict[int, Dict[str, float]] = field(default_factory=dict)

    # All units keyed by unit_id
    units: Dict[int, UnitSnapshot] = field(default_factory=dict)

    # Tech tree per player (player_id -> set of completed techs)
    tech_tree: Dict[int, List[str]] = field(default_factory=dict)

    # Structures per player
    structures: Dict[int, List[str]] = field(default_factory=dict)

    # Supply per player
    supply: Dict[int, Dict[str, int]] = field(default_factory=dict)

    # Visibility / fog of war mask (simplified)
    visibility_hash: str = ""

    # Metadata
    map_name: str = "Unknown"
    game_speed: str = "Faster"
    player_races: Dict[int, str] = field(default_factory=dict)

    def unit_count(self, player_id: int) -> int:
        return sum(
            1 for u in self.units.values() if u.owner == player_id and u.is_alive
        )

    def army_value(self, player_id: int) -> float:
        return sum(
            u.health + u.shield
            for u in self.units.values()
            if u.owner == player_id and u.is_alive
        )

    def deep_copy(self) -> "TwinState":
        return copy.deepcopy(self)

    def to_feature_vector(self) -> List[float]:
        """Flatten state into a numeric feature vector for ML models."""
        features: List[float] = [float(self.game_loop)]
        for pid in sorted(self.resources.keys()):
            res = self.resources[pid]
            features.extend(
                [
                    res.get("minerals", 0.0),
                    res.get("vespene", 0.0),
                ]
            )
            sup = self.supply.get(pid, {})
            features.extend(
                [
                    float(sup.get("used", 0)),
                    float(sup.get("cap", 0)),
                ]
            )
            features.append(float(self.unit_count(pid)))
            features.append(self.army_value(pid))
        return features

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_loop": self.game_loop,
            "timestamp": self.timestamp,
            "twin_id": self.twin_id,
            "resources": self.resources,
            "units": {k: v.to_dict() for k, v in self.units.items()},
            "tech_tree": self.tech_tree,
            "structures": self.structures,
            "supply": self.supply,
            "map_name": self.map_name,
            "game_speed": self.game_speed,
            "player_races": self.player_races,
        }

    def summary(self) -> str:
        lines = [f"TwinState loop={self.game_loop} map={self.map_name}"]
        for pid in sorted(self.resources.keys()):
            res = self.resources.get(pid, {})
            sup = self.supply.get(pid, {})
            lines.append(
                f"  P{pid}: {res.get('minerals', 0):.0f}M "
                f"{res.get('vespene', 0):.0f}V "
                f"supply={sup.get('used', 0)}/{sup.get('cap', 0)} "
                f"units={self.unit_count(pid)} "
                f"army={self.army_value(pid):.0f}"
            )
        return "\n".join(lines)


# ============================================================
# StateSync: Synchronize live game data into the twin
# ============================================================


class StateSync:
    """Handles real-time synchronization between the live SC2 game and the twin."""

    def __init__(self, sync_interval: float = 0.5, max_lag_ms: float = 200.0):
        self.sync_interval = sync_interval
        self.max_lag_ms = max_lag_ms
        self.last_sync_time: float = 0.0
        self.sync_count: int = 0
        self.lag_history: deque = deque(maxlen=500)
        self.dropped_syncs: int = 0
        self._state_buffer: deque = deque(maxlen=100)
        self._callbacks: List[Callable] = []

    def register_callback(self, cb: Callable) -> None:
        """Register callback to be notified on each sync."""
        self._callbacks.append(cb)

    def push_observation(
        self, observation: Dict[str, Any], ts: Optional[float] = None
    ) -> TwinState:
        """Convert a raw SC2 observation dict into a TwinState snapshot."""
        ts = ts or time.time()
        lag = (ts - self.last_sync_time) * 1000 if self.last_sync_time > 0 else 0.0
        self.lag_history.append(lag)

        state = TwinState(
            game_loop=observation.get("game_loop", 0),
            timestamp=ts,
            map_name=observation.get("map_name", "Unknown"),
            game_speed=observation.get("game_speed", "Faster"),
        )

        # Parse resources
        for pid, res in observation.get("resources", {}).items():
            pid_int = int(pid)
            state.resources[pid_int] = {
                "minerals": float(res.get("minerals", 0)),
                "vespene": float(res.get("vespene", 0)),
            }
            state.supply[pid_int] = {
                "used": int(res.get("supply_used", 0)),
                "cap": int(res.get("supply_cap", 0)),
            }

        # Parse units
        for uid_str, udata in observation.get("units", {}).items():
            uid = int(uid_str)
            snap = UnitSnapshot(
                unit_id=uid,
                unit_type=udata.get("type", "Unknown"),
                owner=int(udata.get("owner", 0)),
                position=tuple(udata.get("position", [0.0, 0.0])),
                health=float(udata.get("health", 100)),
                max_health=float(udata.get("max_health", 100)),
                shield=float(udata.get("shield", 0)),
                energy=float(udata.get("energy", 0)),
                is_alive=bool(udata.get("is_alive", True)),
                orders=udata.get("orders", []),
                buffs=udata.get("buffs", []),
                timestamp=ts,
            )
            state.units[uid] = snap

        # Parse tech tree
        for pid, techs in observation.get("tech_tree", {}).items():
            state.tech_tree[int(pid)] = list(techs)

        # Parse structures
        for pid, structs in observation.get("structures", {}).items():
            state.structures[int(pid)] = list(structs)

        # Parse player races
        for pid, race in observation.get("player_races", {}).items():
            state.player_races[int(pid)] = str(race)

        if lag > self.max_lag_ms and self.sync_count > 0:
            self.dropped_syncs += 1

        self.last_sync_time = ts
        self.sync_count += 1
        self._state_buffer.append(state)

        for cb in self._callbacks:
            try:
                cb(state)
            except Exception:
                pass

        return state

    def get_avg_lag(self) -> float:
        if not self.lag_history:
            return 0.0
        return _np_mean(list(self.lag_history))

    def get_buffered_states(self, n: int = 10) -> List[TwinState]:
        return list(self._state_buffer)[-n:]

    def stats(self) -> Dict[str, Any]:
        return {
            "sync_count": self.sync_count,
            "dropped_syncs": self.dropped_syncs,
            "avg_lag_ms": round(self.get_avg_lag(), 2),
            "buffer_size": len(self._state_buffer),
        }


# ============================================================
# PredictionEngine: Simulate future game states
# ============================================================


class PredictionEngine:
    """Predict future game states using learned dynamics and simple extrapolation."""

    def __init__(self, horizon_steps: int = 50, learning_rate: float = 0.01):
        self.horizon_steps = horizon_steps
        self.learning_rate = learning_rate
        self._history: deque = deque(maxlen=2000)
        self._resource_velocity: Dict[int, Dict[str, float]] = {}
        self._unit_growth_rate: Dict[int, float] = {}
        self.prediction_count: int = 0

    def observe(self, state: TwinState) -> None:
        """Feed an observed state to update dynamics model."""
        self._history.append(state)
        if len(self._history) < 2:
            return

        prev = self._history[-2]
        dt = max(state.game_loop - prev.game_loop, 1)

        for pid in state.resources:
            prev_res = prev.resources.get(pid, {"minerals": 0, "vespene": 0})
            curr_res = state.resources[pid]
            vel = self._resource_velocity.get(pid, {"minerals": 0.0, "vespene": 0.0})
            for key in ("minerals", "vespene"):
                delta = (curr_res.get(key, 0) - prev_res.get(key, 0)) / dt
                vel[key] = (
                    vel[key] * (1 - self.learning_rate) + delta * self.learning_rate
                )
            self._resource_velocity[pid] = vel

        for pid in state.resources:
            prev_count = prev.unit_count(pid)
            curr_count = state.unit_count(pid)
            delta = (curr_count - prev_count) / dt
            old_rate = self._unit_growth_rate.get(pid, 0.0)
            self._unit_growth_rate[pid] = (
                old_rate * (1 - self.learning_rate) + delta * self.learning_rate
            )

    def predict(
        self, current: TwinState, steps_ahead: Optional[int] = None
    ) -> TwinState:
        """Predict a future state by extrapolating current dynamics."""
        steps = steps_ahead or self.horizon_steps
        predicted = current.deep_copy()
        predicted.game_loop = current.game_loop + steps
        predicted.timestamp = (
            current.timestamp + steps * 0.045
        )  # approximate seconds per loop

        for pid in predicted.resources:
            vel = self._resource_velocity.get(pid, {"minerals": 0.0, "vespene": 0.0})
            for key in ("minerals", "vespene"):
                predicted.resources[pid][key] = max(
                    0.0, predicted.resources[pid].get(key, 0) + vel[key] * steps
                )

        for pid in list(predicted.supply.keys()):
            growth = self._unit_growth_rate.get(pid, 0.0)
            estimated_new = max(0, int(growth * steps))
            predicted.supply[pid]["used"] = (
                predicted.supply[pid].get("used", 0) + estimated_new
            )

        self.prediction_count += 1
        return predicted

    def predict_trajectory(
        self, current: TwinState, num_points: int = 5
    ) -> List[TwinState]:
        """Predict multiple future states forming a trajectory."""
        step_size = self.horizon_steps // max(num_points, 1)
        trajectory: List[TwinState] = []
        for i in range(1, num_points + 1):
            pred = self.predict(current, steps_ahead=step_size * i)
            trajectory.append(pred)
        return trajectory

    def what_if(self, current: TwinState, modifications: Dict[str, Any]) -> TwinState:
        """Run a counterfactual scenario with modified parameters."""
        modified = current.deep_copy()

        if "resource_boost" in modifications:
            pid = modifications["resource_boost"].get("player", 1)
            amount = modifications["resource_boost"].get("minerals", 0)
            if pid in modified.resources:
                modified.resources[pid]["minerals"] = (
                    modified.resources[pid].get("minerals", 0) + amount
                )

        if "remove_units" in modifications:
            target_pid = modifications["remove_units"].get("player", 2)
            count = modifications["remove_units"].get("count", 5)
            removed = 0
            for uid, unit in list(modified.units.items()):
                if unit.owner == target_pid and unit.is_alive and removed < count:
                    unit.is_alive = False
                    removed += 1

        if "tech_unlock" in modifications:
            pid = modifications["tech_unlock"].get("player", 1)
            tech = modifications["tech_unlock"].get("tech", "")
            if pid not in modified.tech_tree:
                modified.tech_tree[pid] = []
            if tech and tech not in modified.tech_tree[pid]:
                modified.tech_tree[pid].append(tech)

        return self.predict(modified)

    def confidence(self) -> float:
        """Return a confidence score [0, 1] based on data history."""
        data_points = len(self._history)
        return min(1.0, data_points / 200.0)

    def stats(self) -> Dict[str, Any]:
        return {
            "history_size": len(self._history),
            "prediction_count": self.prediction_count,
            "confidence": round(self.confidence(), 4),
            "resource_velocity": {
                str(k): {rk: round(rv, 4) for rk, rv in v.items()}
                for k, v in self._resource_velocity.items()
            },
            "unit_growth_rate": {
                str(k): round(v, 6) for k, v in self._unit_growth_rate.items()
            },
        }


# ============================================================
# AnomalyDetector: Detect unusual opponent behaviors
# ============================================================


class AnomalyDetector:
    """Detect anomalies in the game state that indicate unusual opponent strategies."""

    def __init__(self, sensitivity: float = 2.0, min_samples: int = 20):
        self.sensitivity = sensitivity
        self.min_samples = min_samples
        self._feature_history: deque = deque(maxlen=3000)
        self._anomaly_log: List[Dict[str, Any]] = []
        self._baseline_mean: Optional[List[float]] = None
        self._baseline_std: Optional[List[float]] = None

    def observe(self, state: TwinState) -> None:
        """Record feature vectors from observed states."""
        fv = state.to_feature_vector()
        self._feature_history.append(fv)
        self._update_baseline()

    def _update_baseline(self) -> None:
        if len(self._feature_history) < self.min_samples:
            return
        history = list(self._feature_history)
        num_features = len(history[0])
        means: List[float] = []
        stds: List[float] = []
        for i in range(num_features):
            col = [row[i] for row in history if i < len(row)]
            means.append(_np_mean(col))
            stds.append(_np_std(col))
        self._baseline_mean = means
        self._baseline_std = stds

    def check(self, state: TwinState) -> List[Dict[str, Any]]:
        """Check a state for anomalies. Returns list of detected anomalies."""
        if self._baseline_mean is None or self._baseline_std is None:
            return []

        fv = state.to_feature_vector()
        anomalies: List[Dict[str, Any]] = []
        feature_names = self._get_feature_names(state)

        for i, val in enumerate(fv):
            if i >= len(self._baseline_mean):
                break
            mean = self._baseline_mean[i]
            std = self._baseline_std[i]
            if std < 1e-9:
                continue
            z_score = abs(val - mean) / std
            if z_score > self.sensitivity:
                name = feature_names[i] if i < len(feature_names) else f"feature_{i}"
                anomaly = {
                    "feature": name,
                    "value": round(val, 2),
                    "expected_mean": round(mean, 2),
                    "z_score": round(z_score, 2),
                    "game_loop": state.game_loop,
                    "severity": "high" if z_score > self.sensitivity * 2 else "medium",
                }
                anomalies.append(anomaly)

        if anomalies:
            self._anomaly_log.extend(anomalies)

        return anomalies

    def _get_feature_names(self, state: TwinState) -> List[str]:
        names = ["game_loop"]
        for pid in sorted(state.resources.keys()):
            prefix = f"P{pid}_"
            names.extend(
                [
                    prefix + "minerals",
                    prefix + "vespene",
                    prefix + "supply_used",
                    prefix + "supply_cap",
                    prefix + "unit_count",
                    prefix + "army_value",
                ]
            )
        return names

    def detect_timing_attack(
        self, states: List[TwinState], opponent_id: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Detect if opponent is massing army for a timing attack."""
        if len(states) < 10:
            return None
        recent = states[-10:]
        army_values = [s.army_value(opponent_id) for s in recent]
        resource_spend = []
        for i in range(1, len(recent)):
            prev_min = recent[i - 1].resources.get(opponent_id, {}).get("minerals", 0)
            curr_min = recent[i].resources.get(opponent_id, {}).get("minerals", 0)
            resource_spend.append(max(0, prev_min - curr_min))

        avg_spend = _np_mean(resource_spend)
        army_growth = army_values[-1] - army_values[0] if army_values else 0

        if army_growth > 500 and avg_spend > 50:
            return {
                "type": "timing_attack",
                "army_growth": round(army_growth, 1),
                "avg_resource_spend": round(avg_spend, 1),
                "confidence": min(1.0, army_growth / 1000),
                "game_loop": states[-1].game_loop,
            }
        return None

    def detect_expansion_anomaly(
        self, state: TwinState, opponent_id: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Detect if opponent is expanding unusually fast or slow."""
        opp_structs = state.structures.get(opponent_id, [])
        base_types = {
            "Nexus",
            "CommandCenter",
            "Hatchery",
            "OrbitalCommand",
            "PlanetaryFortress",
            "Lair",
            "Hive",
        }
        base_count = sum(1 for s in opp_structs if s in base_types)
        expected_bases = max(1, state.game_loop // 3000)  # rough heuristic

        if base_count > expected_bases + 1:
            return {
                "type": "fast_expansion",
                "bases": base_count,
                "expected": expected_bases,
                "game_loop": state.game_loop,
            }
        elif base_count < expected_bases - 1 and state.game_loop > 3000:
            return {
                "type": "one_base_aggression",
                "bases": base_count,
                "expected": expected_bases,
                "game_loop": state.game_loop,
            }
        return None

    def get_anomaly_log(self, last_n: int = 50) -> List[Dict[str, Any]]:
        return self._anomaly_log[-last_n:]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_observations": len(self._feature_history),
            "total_anomalies": len(self._anomaly_log),
            "baseline_ready": self._baseline_mean is not None,
            "sensitivity": self.sensitivity,
        }


# ============================================================
# DigitalTwin: Main orchestrator
# ============================================================


class DigitalTwin:
    """
    Main Digital Twin controller for SC2 game state mirroring.

    Combines state synchronization, prediction, and anomaly detection
    into a single interface that can mirror a live SC2 game.
    """

    def __init__(
        self,
        sync_interval: float = 0.5,
        max_lag_ms: float = 200.0,
        prediction_horizon: int = 50,
        anomaly_sensitivity: float = 2.0,
        snapshot_dir: Optional[str] = None,
    ):
        self.twin_id = uuid.uuid4().hex[:12]
        self.sync = StateSync(sync_interval=sync_interval, max_lag_ms=max_lag_ms)
        self.predictor = PredictionEngine(horizon_steps=prediction_horizon)
        self.detector = AnomalyDetector(sensitivity=anomaly_sensitivity)
        self.snapshot_dir = snapshot_dir

        self._current_state: Optional[TwinState] = None
        self._state_history: deque = deque(maxlen=5000)
        self._active: bool = False
        self._creation_time: float = time.time()

        # Register internal callbacks
        self.sync.register_callback(self._on_state_sync)

    def _on_state_sync(self, state: TwinState) -> None:
        """Internal callback triggered on each state sync."""
        self._current_state = state
        self._state_history.append(state)
        self.predictor.observe(state)
        self.detector.observe(state)

    def start(self) -> None:
        """Activate the digital twin."""
        self._active = True

    def stop(self) -> None:
        """Deactivate the digital twin."""
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def update(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main update loop. Feed a raw observation to sync, predict, and detect.
        Returns a summary dict with current state, predictions, and anomalies.
        """
        if not self._active:
            return {"error": "Digital twin is not active"}

        state = self.sync.push_observation(observation)

        # Run prediction
        prediction = self.predictor.predict(state)
        trajectory = self.predictor.predict_trajectory(state, num_points=3)

        # Run anomaly detection
        anomalies = self.detector.check(state)
        timing = self.detector.detect_timing_attack(list(self._state_history))
        expansion = self.detector.detect_expansion_anomaly(state)

        result: Dict[str, Any] = {
            "current_loop": state.game_loop,
            "current_summary": state.summary(),
            "predicted_loop": prediction.game_loop,
            "predicted_summary": prediction.summary(),
            "trajectory_length": len(trajectory),
            "anomalies": anomalies,
            "timing_attack": timing,
            "expansion_anomaly": expansion,
            "sync_stats": self.sync.stats(),
            "prediction_confidence": self.predictor.confidence(),
        }

        return result

    def what_if_analysis(self, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Run a what-if scenario on the current state."""
        if self._current_state is None:
            return {"error": "No state available for what-if analysis"}

        counterfactual = self.predictor.what_if(self._current_state, modifications)
        baseline = self.predictor.predict(self._current_state)

        return {
            "baseline": baseline.summary(),
            "counterfactual": counterfactual.summary(),
            "baseline_army": {
                pid: baseline.army_value(pid) for pid in baseline.resources
            },
            "counterfactual_army": {
                pid: counterfactual.army_value(pid) for pid in counterfactual.resources
            },
        }

    def get_state_at(self, game_loop: int) -> Optional[TwinState]:
        """Retrieve a historical state closest to the given game loop."""
        best: Optional[TwinState] = None
        best_dist = float("inf")
        for s in self._state_history:
            dist = abs(s.game_loop - game_loop)
            if dist < best_dist:
                best_dist = dist
                best = s
        return best

    def save_snapshot(self, filename: Optional[str] = None) -> str:
        """Save current twin state to a JSON file."""
        if self._current_state is None:
            return "No state to save"
        if self.snapshot_dir:
            os.makedirs(self.snapshot_dir, exist_ok=True)
            path = os.path.join(
                self.snapshot_dir,
                filename or f"twin_snapshot_{self._current_state.game_loop}.json",
            )
        else:
            path = filename or f"twin_snapshot_{self._current_state.game_loop}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._current_state.to_dict(), f, indent=2)
        return path

    def compare_states(self, loop_a: int, loop_b: int) -> Dict[str, Any]:
        """Compare two historical states by game loop."""
        state_a = self.get_state_at(loop_a)
        state_b = self.get_state_at(loop_b)
        if state_a is None or state_b is None:
            return {"error": "Could not find requested states"}

        diff: Dict[str, Any] = {
            "loop_a": state_a.game_loop,
            "loop_b": state_b.game_loop,
            "resource_diff": {},
            "unit_count_diff": {},
            "army_value_diff": {},
        }

        all_pids = set(state_a.resources.keys()) | set(state_b.resources.keys())
        for pid in all_pids:
            res_a = state_a.resources.get(pid, {"minerals": 0, "vespene": 0})
            res_b = state_b.resources.get(pid, {"minerals": 0, "vespene": 0})
            diff["resource_diff"][pid] = {
                "minerals": res_b.get("minerals", 0) - res_a.get("minerals", 0),
                "vespene": res_b.get("vespene", 0) - res_a.get("vespene", 0),
            }
            diff["unit_count_diff"][pid] = state_b.unit_count(pid) - state_a.unit_count(
                pid
            )
            diff["army_value_diff"][pid] = round(
                state_b.army_value(pid) - state_a.army_value(pid), 1
            )

        return diff

    def full_report(self) -> Dict[str, Any]:
        """Generate a comprehensive twin status report."""
        return {
            "twin_id": self.twin_id,
            "active": self._active,
            "uptime_seconds": round(time.time() - self._creation_time, 1),
            "history_size": len(self._state_history),
            "current_loop": (
                self._current_state.game_loop if self._current_state else None
            ),
            "sync": self.sync.stats(),
            "prediction": self.predictor.stats(),
            "anomaly": self.detector.stats(),
        }


# ============================================================
# Utility: Generate synthetic SC2 observations for testing
# ============================================================


def _generate_synthetic_observation(
    game_loop: int, rng: random.Random
) -> Dict[str, Any]:
    """Generate a synthetic SC2 observation for testing purposes."""
    mineral_base = 500 + game_loop * 2 + rng.gauss(0, 30)
    vespene_base = 200 + game_loop * 1.2 + rng.gauss(0, 20)

    units: Dict[str, Dict[str, Any]] = {}
    num_own_units = max(5, 10 + game_loop // 200 + int(rng.gauss(0, 2)))
    num_enemy_units = max(3, 8 + game_loop // 250 + int(rng.gauss(0, 3)))

    uid = 1
    unit_types_own = ["Marine", "Marauder", "SiegeTank", "Medivac", "Viking"]
    unit_types_enemy = ["Zergling", "Roach", "Hydralisk", "Mutalisk", "Queen"]

    for _ in range(num_own_units):
        units[str(uid)] = {
            "type": rng.choice(unit_types_own),
            "owner": 1,
            "position": [rng.uniform(20, 180), rng.uniform(20, 180)],
            "health": rng.uniform(30, 150),
            "max_health": 150,
            "shield": 0,
            "energy": rng.uniform(0, 200),
            "is_alive": True,
            "orders": [],
            "buffs": [],
        }
        uid += 1

    for _ in range(num_enemy_units):
        units[str(uid)] = {
            "type": rng.choice(unit_types_enemy),
            "owner": 2,
            "position": [rng.uniform(20, 180), rng.uniform(20, 180)],
            "health": rng.uniform(20, 120),
            "max_health": 120,
            "shield": 0,
            "energy": 0,
            "is_alive": True,
            "orders": [],
            "buffs": [],
        }
        uid += 1

    own_structures = ["CommandCenter", "Barracks", "Factory"]
    if game_loop > 2000:
        own_structures.append("Starport")
    if game_loop > 5000:
        own_structures.append("CommandCenter")  # expansion

    enemy_structures = ["Hatchery", "SpawningPool", "RoachWarren"]
    if game_loop > 3000:
        enemy_structures.append("Hatchery")

    return {
        "game_loop": game_loop,
        "map_name": "Equilibrium",
        "game_speed": "Faster",
        "resources": {
            "1": {
                "minerals": max(0, mineral_base),
                "vespene": max(0, vespene_base),
                "supply_used": num_own_units + 5,
                "supply_cap": max(30, num_own_units + 15),
            },
            "2": {
                "minerals": max(0, mineral_base * 0.9 + rng.gauss(0, 50)),
                "vespene": max(0, vespene_base * 0.85 + rng.gauss(0, 30)),
                "supply_used": num_enemy_units + 4,
                "supply_cap": max(30, num_enemy_units + 12),
            },
        },
        "units": units,
        "tech_tree": {
            "1": ["Stim", "CombatShield"] if game_loop > 2000 else ["Stim"],
            "2": ["MetabolicBoost"] if game_loop > 1500 else [],
        },
        "structures": {
            "1": own_structures,
            "2": enemy_structures,
        },
        "player_races": {
            "1": "Terran",
            "2": "Zerg",
        },
    }


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate the Phase 650 Digital Twin system."""
    print("=" * 70)
    print("Phase 650: Digital Twin for SC2 Game State Mirroring")
    print("=" * 70)

    rng = random.Random(650)
    twin = DigitalTwin(
        sync_interval=0.1,
        max_lag_ms=500.0,
        prediction_horizon=100,
        anomaly_sensitivity=2.5,
    )
    twin.start()

    # --- [1] Simulate game ticks and sync ---
    print("\n[1] Simulating 50 game ticks with state sync...")
    for i in range(50):
        loop = i * 100
        obs = _generate_synthetic_observation(loop, rng)
        result = twin.update(obs)

    print(f"    Sync stats: {twin.sync.stats()}")
    print(f"    Current state:\n    {result['current_summary']}")

    # --- [2] Prediction ---
    print("\n[2] Predicting future state (+200 loops)...")
    if twin._current_state:
        predicted = twin.predictor.predict(twin._current_state, steps_ahead=200)
        print(f"    Predicted:\n    {predicted.summary()}")
        print(f"    Prediction confidence: {twin.predictor.confidence():.2%}")

    # --- [3] Trajectory ---
    print("\n[3] Generating prediction trajectory (5 points)...")
    if twin._current_state:
        trajectory = twin.predictor.predict_trajectory(
            twin._current_state, num_points=5
        )
        for idx, ts in enumerate(trajectory):
            print(
                f"    T+{idx+1}: loop={ts.game_loop} "
                f"P1_army={ts.army_value(1):.0f} P2_army={ts.army_value(2):.0f}"
            )

    # --- [4] What-if analysis ---
    print("\n[4] What-if analysis: boost P1 minerals by 1000...")
    wi_result = twin.what_if_analysis(
        {
            "resource_boost": {"player": 1, "minerals": 1000},
        }
    )
    print(f"    Baseline: {wi_result.get('baseline', 'N/A')[:80]}...")
    print(f"    Counterfactual: {wi_result.get('counterfactual', 'N/A')[:80]}...")

    # --- [5] What-if: remove enemy units ---
    print("\n[5] What-if analysis: remove 5 enemy units...")
    wi2 = twin.what_if_analysis(
        {
            "remove_units": {"player": 2, "count": 5},
        }
    )
    print(f"    Baseline army P2: {wi2.get('baseline_army', {}).get(2, 'N/A')}")
    print(
        f"    Counterfactual army P2: {wi2.get('counterfactual_army', {}).get(2, 'N/A')}"
    )

    # --- [6] Anomaly detection ---
    print("\n[6] Running anomaly detection on current state...")
    if twin._current_state:
        anomalies = twin.detector.check(twin._current_state)
        print(f"    Anomalies found: {len(anomalies)}")
        for a in anomalies[:3]:
            print(f"      {a['feature']}: z={a['z_score']} severity={a['severity']}")

    # --- [7] Timing attack detection ---
    print("\n[7] Checking for timing attacks...")
    states = list(twin._state_history)
    timing = twin.detector.detect_timing_attack(states, opponent_id=2)
    if timing:
        print(
            f"    Timing attack detected! Growth={timing['army_growth']:.0f} "
            f"Confidence={timing['confidence']:.2f}"
        )
    else:
        print("    No timing attack detected.")

    # --- [8] Expansion anomaly ---
    print("\n[8] Checking expansion anomaly...")
    if twin._current_state:
        exp_anomaly = twin.detector.detect_expansion_anomaly(twin._current_state)
        if exp_anomaly:
            print(
                f"    Expansion anomaly: {exp_anomaly['type']} "
                f"bases={exp_anomaly['bases']} expected={exp_anomaly['expected']}"
            )
        else:
            print("    No expansion anomaly detected.")

    # --- [9] State comparison ---
    print("\n[9] Comparing states at loop 1000 vs 4000...")
    diff = twin.compare_states(1000, 4000)
    if "error" not in diff:
        print(f"    Loops compared: {diff['loop_a']} vs {diff['loop_b']}")
        for pid in sorted(diff.get("resource_diff", {}).keys()):
            rd = diff["resource_diff"][pid]
            print(
                f"    P{pid} mineral delta: {rd['minerals']:.0f}, "
                f"vespene delta: {rd['vespene']:.0f}, "
                f"unit delta: {diff['unit_count_diff'].get(pid, 0)}"
            )

    # --- [10] Full report ---
    print("\n[10] Full twin report:")
    report = twin.full_report()
    for key, val in report.items():
        if isinstance(val, dict):
            print(f"    {key}:")
            for k2, v2 in val.items():
                print(f"      {k2}: {v2}")
        else:
            print(f"    {key}: {val}")

    twin.stop()

    print("\n" + "=" * 70)
    print("Phase 650 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 650: Digital Twin registered
