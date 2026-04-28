"""
SC2 Bot - Feature Store
Phase 396: Point-in-time correct feature retrieval for ML training

Implements a Feast-like Feature Store API for SC2 game state features.
Supports: game_state_features, unit_features, economic_features, historical_features
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class Feature:
    """A single feature definition."""

    name: str
    dtype: str  # "float32", "int32", "bool"
    description: str
    default_value: Any = 0.0

    def validate(self, value: Any) -> bool:
        if self.dtype == "float32":
            return isinstance(value, (int, float))
        if self.dtype == "int32":
            return isinstance(value, int)
        if self.dtype == "bool":
            return isinstance(value, bool)
        return True


@dataclass
class FeatureGroup:
    """
    A logical grouping of related features.
    Each group has an entity key (e.g., game_id, player_id).
    """

    name: str
    entity_key: str
    features: list[Feature]
    ttl_seconds: int = 3600
    description: str = ""

    def feature_names(self) -> list[str]:
        return [f.name for f in self.features]

    def vector_size(self) -> int:
        return len(self.features)


@dataclass
class FeatureVector:
    """A retrieved feature vector for a specific entity at a point in time."""

    entity_id: str
    feature_group: str
    timestamp: datetime
    values: dict[str, Any]
    vector: np.ndarray

    def to_tensor(self):
        """Convert to PyTorch tensor."""
        try:
            import torch

            return torch.tensor(self.vector, dtype=torch.float32)
        except ImportError:
            return self.vector


# ---------------------------------------------------------------------------
# Feature Group Definitions
# ---------------------------------------------------------------------------

GAME_STATE_FEATURES = FeatureGroup(
    name="game_state_features",
    entity_key="game_id",
    description="High-level game state features observed each step",
    features=[
        Feature("game_loop", "int32", "Current game loop (step count)"),
        Feature("map_width", "int32", "Map width in game units"),
        Feature("map_height", "int32", "Map height in game units"),
        Feature("player_minerals", "float32", "Current mineral count"),
        Feature("player_vespene", "float32", "Current vespene gas count"),
        Feature("player_supply_used", "int32", "Supply used"),
        Feature("player_supply_cap", "int32", "Supply cap"),
        Feature("player_army_value", "float32", "Total army mineral+gas value"),
        Feature("enemy_army_value", "float32", "Estimated enemy army value"),
        Feature("army_advantage", "float32", "Our army value / enemy army value"),
        Feature("base_count", "int32", "Number of active bases"),
        Feature("enemy_base_count", "int32", "Estimated enemy base count"),
        Feature("creep_coverage", "float32", "Fraction of map covered by creep"),
        Feature("vision_coverage", "float32", "Fraction of map with vision"),
        Feature("threat_level", "float32", "Normalized threat level 0-1"),
        Feature("time_minutes", "float32", "Game time in minutes"),
    ],
)

UNIT_FEATURES = FeatureGroup(
    name="unit_features",
    entity_key="game_id",
    description="Aggregate statistics about unit composition",
    features=[
        Feature("drone_count", "int32", "Number of drones"),
        Feature("zergling_count", "int32", "Number of zerglings"),
        Feature("roach_count", "int32", "Number of roaches"),
        Feature("hydralisk_count", "int32", "Number of hydralisks"),
        Feature("mutalisk_count", "int32", "Number of mutalisks"),
        Feature("corruptor_count", "int32", "Number of corruptors"),
        Feature("broodlord_count", "int32", "Number of brood lords"),
        Feature("ultra_count", "int32", "Number of ultralisks"),
        Feature("infestor_count", "int32", "Number of infestors"),
        Feature("army_count", "int32", "Total army units"),
        Feature("worker_count", "int32", "Total worker units"),
        Feature("avg_unit_health", "float32", "Average unit health percentage"),
        Feature(
            "units_in_combat", "int32", "Units currently attacking or being attacked"
        ),
        Feature("units_idle", "int32", "Army units currently idle"),
    ],
)

ECONOMIC_FEATURES = FeatureGroup(
    name="economic_features",
    entity_key="game_id",
    description="Economy and production statistics",
    features=[
        Feature("mineral_rate", "float32", "Minerals mined per minute"),
        Feature("vespene_rate", "float32", "Gas mined per minute"),
        Feature("mineral_banked", "float32", "Banked minerals (unspent)"),
        Feature("vespene_banked", "float32", "Banked gas (unspent)"),
        Feature(
            "spending_efficiency", "float32", "Resources spent / resources collected"
        ),
        Feature("hatchery_count", "int32", "Number of hatcheries/lairs/hives"),
        Feature("extractor_count", "int32", "Number of extractors"),
        Feature("queen_count", "int32", "Number of queens"),
        Feature("larvae_count", "int32", "Available larvae"),
        Feature("production_queue", "int32", "Units/buildings currently in production"),
        Feature("tech_tier", "int32", "Current tech tier (1=Hatch, 2=Lair, 3=Hive)"),
        Feature("upgrade_count", "int32", "Number of completed upgrades"),
    ],
)

HISTORICAL_FEATURES = FeatureGroup(
    name="historical_features",
    entity_key="game_id",
    description="Aggregated historical game performance metrics",
    features=[
        Feature("last_10_win_rate", "float32", "Win rate over last 10 games"),
        Feature("last_50_win_rate", "float32", "Win rate over last 50 games"),
        Feature("avg_game_length", "float32", "Average game length in minutes"),
        Feature("most_used_strategy", "int32", "Most frequently used strategy ID"),
        Feature("avg_apm", "float32", "Average actions per minute"),
        Feature("max_apm", "float32", "Peak actions per minute"),
        Feature(
            "avg_first_attack", "float32", "Average time of first attack (minutes)"
        ),
        Feature("loss_streak", "int32", "Current loss streak"),
        Feature("win_streak", "int32", "Current win streak"),
        Feature("total_games", "int32", "Total games played"),
    ],
)

ALL_FEATURE_GROUPS = [
    GAME_STATE_FEATURES,
    UNIT_FEATURES,
    ECONOMIC_FEATURES,
    HISTORICAL_FEATURES,
]


# ---------------------------------------------------------------------------
# In-Memory Feature Store Backend
# ---------------------------------------------------------------------------


class _InMemoryBackend:
    """Simple in-memory backend for feature storage."""

    def __init__(self):
        self._store: dict[str, list[tuple[float, dict]]] = {}

    def write(self, key: str, timestamp: float, values: dict) -> None:
        if key not in self._store:
            self._store[key] = []
        self._store[key].append((timestamp, values))
        self._store[key].sort(key=lambda x: x[0])

    def read_at_time(self, key: str, at_time: float) -> dict | None:
        """Point-in-time correct read: latest entry <= at_time."""
        entries = self._store.get(key, [])
        result = None
        for ts, values in entries:
            if ts <= at_time:
                result = values
            else:
                break
        return result

    def read_latest(self, key: str) -> dict | None:
        entries = self._store.get(key, [])
        if entries:
            return entries[-1][1]
        return None


# ---------------------------------------------------------------------------
# Feature Store
# ---------------------------------------------------------------------------


class FeatureStore:
    """
    SC2 Bot Feature Store - Feast-like API.

    Provides:
    - write_features(): ingest features for an entity
    - get_online_features(): low-latency online retrieval
    - get_historical_features(): point-in-time correct batch retrieval
    - get_training_dataset(): generate training feature matrix
    """

    def __init__(self):
        self._backend = _InMemoryBackend()
        self._feature_groups: dict[str, FeatureGroup] = {}

        # Register all feature groups
        for fg in ALL_FEATURE_GROUPS:
            self.register_feature_group(fg)

        logger.info(
            f"FeatureStore initialized with {len(self._feature_groups)} feature groups"
        )

    def register_feature_group(self, fg: FeatureGroup) -> None:
        self._feature_groups[fg.name] = fg
        logger.debug(
            f"Registered feature group: {fg.name} ({len(fg.features)} features)"
        )

    def write_features(
        self,
        entity_id: str,
        feature_group: str,
        values: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> None:
        """Write feature values for an entity."""
        fg = self._feature_groups.get(feature_group)
        if fg is None:
            raise KeyError(f"Unknown feature group: {feature_group}")

        ts = timestamp.timestamp() if timestamp else time.time()
        key = self._make_key(entity_id, feature_group)
        self._backend.write(key, ts, values)

    def get_online_features(
        self,
        entity_ids: list[str],
        feature_groups: list[str] | None = None,
    ) -> dict[str, FeatureVector]:
        """
        Online feature retrieval - returns latest features for each entity.
        Low-latency path for inference.
        """
        groups = feature_groups or list(self._feature_groups.keys())
        results: dict[str, FeatureVector] = {}

        for entity_id in entity_ids:
            combined_values: dict[str, Any] = {}
            for fg_name in groups:
                key = self._make_key(entity_id, fg_name)
                values = self._backend.read_latest(key) or {}
                combined_values.update(values)

            fg = self._feature_groups[groups[0]]
            vector = self._to_vector(combined_values, groups)

            results[entity_id] = FeatureVector(
                entity_id=entity_id,
                feature_group="+".join(groups),
                timestamp=datetime.utcnow(),
                values=combined_values,
                vector=vector,
            )

        return results

    def get_historical_features(
        self,
        entity_id: str,
        feature_group: str,
        at_time: datetime,
    ) -> FeatureVector | None:
        """
        Point-in-time correct feature retrieval.
        Returns the feature values that were active at the specified time.
        """
        fg = self._feature_groups.get(feature_group)
        if fg is None:
            raise KeyError(f"Unknown feature group: {feature_group}")

        key = self._make_key(entity_id, feature_group)
        values = self._backend.read_at_time(key, at_time.timestamp())

        if values is None:
            return None

        vector = self._to_vector(values, [feature_group])
        return FeatureVector(
            entity_id=entity_id,
            feature_group=feature_group,
            timestamp=at_time,
            values=values,
            vector=vector,
        )

    def get_training_dataset(
        self,
        entity_ids: list[str],
        feature_groups: list[str],
        timestamps: list[datetime],
    ) -> np.ndarray:
        """
        Generate a training feature matrix with point-in-time correct features.
        Returns: (n_samples, n_features) numpy array.
        """
        rows = []
        for entity_id, timestamp in zip(entity_ids, timestamps):
            row_values: dict[str, Any] = {}
            for fg_name in feature_groups:
                key = self._make_key(entity_id, fg_name)
                values = self._backend.read_at_time(key, timestamp.timestamp()) or {}
                row_values.update(values)
            row_vector = self._to_vector(row_values, feature_groups)
            rows.append(row_vector)

        matrix = np.array(rows, dtype=np.float32)
        logger.info(f"Training dataset shape: {matrix.shape}")
        return matrix

    def ingest_game_state(
        self, game_id: str, game_state: dict, game_info: dict | None = None
    ) -> None:
        """Convenience method: ingest a full game state into all relevant feature groups."""
        ts = datetime.utcnow()

        self.write_features(
            game_id,
            "game_state_features",
            {
                "game_loop": game_state.get("game_loop", 0),
                "map_width": game_info.get("map_width", 200) if game_info else 200,
                "map_height": game_info.get("map_height", 200) if game_info else 200,
                "player_minerals": game_state.get("minerals", 50),
                "player_vespene": game_state.get("vespene", 0),
                "player_supply_used": game_state.get("supply_used", 0),
                "player_supply_cap": game_state.get("supply_cap", 14),
                "player_army_value": game_state.get("army_value", 0),
                "enemy_army_value": game_state.get("enemy_army_value", 0),
                "army_advantage": game_state.get("army_advantage", 1.0),
                "base_count": game_state.get("base_count", 1),
                "enemy_base_count": game_state.get("enemy_base_count", 1),
                "creep_coverage": game_state.get("creep_coverage", 0.0),
                "vision_coverage": game_state.get("vision_coverage", 0.0),
                "threat_level": game_state.get("threat_level", 0.0),
                "time_minutes": game_state.get("time_minutes", 0.0),
            },
            timestamp=ts,
        )

        self.write_features(
            game_id,
            "unit_features",
            {k: game_state.get(k, 0) for k in UNIT_FEATURES.feature_names()},
            timestamp=ts,
        )

        self.write_features(
            game_id,
            "economic_features",
            {k: game_state.get(k, 0) for k in ECONOMIC_FEATURES.feature_names()},
            timestamp=ts,
        )

    def _make_key(self, entity_id: str, feature_group: str) -> str:
        return f"{feature_group}::{entity_id}"

    def _to_vector(self, values: dict[str, Any], fg_names: list[str]) -> np.ndarray:
        result = []
        for fg_name in fg_names:
            fg = self._feature_groups.get(fg_name)
            if fg is None:
                continue
            for feature in fg.features:
                val = values.get(feature.name, feature.default_value)
                try:
                    result.append(float(val))
                except (TypeError, ValueError):
                    result.append(0.0)
        return np.array(result, dtype=np.float32)

    def describe(self) -> None:
        """Print feature store summary."""
        total_features = sum(len(fg.features) for fg in self._feature_groups.values())
        print(f"\nSC2 Bot Feature Store")
        print(f"{'='*50}")
        print(f"Feature groups: {len(self._feature_groups)}")
        print(f"Total features: {total_features}")
        for name, fg in self._feature_groups.items():
            print(f"  {name}: {len(fg.features)} features (entity: {fg.entity_key})")
        print(f"{'='*50}")


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_store_instance: FeatureStore | None = None


def get_feature_store() -> FeatureStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = FeatureStore()
    return _store_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = get_feature_store()
    store.describe()

    # Demo: write and retrieve features
    mock_game_state = {
        "game_loop": 1200,
        "minerals": 350,
        "vespene": 120,
        "supply_used": 28,
        "supply_cap": 36,
        "army_value": 1200,
        "enemy_army_value": 900,
        "army_advantage": 1.33,
        "base_count": 2,
        "enemy_base_count": 2,
        "creep_coverage": 0.12,
        "vision_coverage": 0.25,
        "threat_level": 0.3,
        "time_minutes": 5.0,
        "drone_count": 16,
        "zergling_count": 12,
        "roach_count": 8,
    }
    store.ingest_game_state("game_001", mock_game_state)

    features = store.get_online_features(["game_001"], ["game_state_features"])
    fv = features["game_001"]
    print(f"\nOnline features for game_001:")
    print(f"  Feature vector shape: {fv.vector.shape}")
    print(f"  Minerals: {fv.values.get('player_minerals', 'N/A')}")
    print(f"  Army advantage: {fv.values.get('army_advantage', 'N/A')}")
