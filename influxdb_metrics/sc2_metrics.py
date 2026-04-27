# Phase 573: InfluxDB Metrics — SC2 Bot Telemetry Writer
# StarCraft II Commander Bot — writes game, economy, combat, and training
# metrics to InfluxDB using the influxdb_client v3 (write API) library.
# Falls back gracefully to a console/no-op sink when the library is absent.

from __future__ import annotations

import os
import time
import random
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Optional dependency — graceful fallback
# ──────────────────────────────────────────────
try:
    from influxdb_client import InfluxDBClient, WriteOptions, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
    from influxdb_client.domain.write_precision import WritePrecision as WP
    from influxdb_client.client.exceptions import InfluxDBError

    _INFLUX_AVAILABLE = True
except ImportError:
    _INFLUX_AVAILABLE = False
    logger.warning(
        "influxdb_client not installed — metrics will be printed to stdout. "
        "Install with: pip install influxdb-client"
    )


# ──────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────
class Race(str, Enum):
    TERRAN = "terran"
    ZERG = "zerg"
    PROTOSS = "protoss"
    RANDOM = "random"


class GameResult(str, Enum):
    WIN = "win"
    LOSS = "loss"
    TIE = "tie"
    CRASH = "crash"


class GamePhase(str, Enum):
    EARLY = "early"
    MID = "mid"
    LATE = "late"


# ──────────────────────────────────────────────
# Dataclasses (SC2 domain)
# ──────────────────────────────────────────────
@dataclass
class GameMetrics:
    """Top-level per-game summary written at game end."""

    game_id: str
    bot_race: Race
    opponent_race: Race
    map_name: str
    result: GameResult
    duration_seconds: float
    actions_per_minute: float
    avg_decision_latency_ms: float
    model_version: str
    environment: str = "production"
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class EconomySnapshot:
    """Periodic economy state — written every N game steps."""

    game_id: str
    game_time_seconds: float
    minerals_stored: int
    vespene_stored: int
    minerals_mined_total: int
    vespene_mined_total: int
    worker_count: int
    supply_used: int
    supply_cap: int
    army_supply: int
    base_count: int
    phase: GamePhase = GamePhase.EARLY
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    @property
    def mineral_income_rate(self) -> float:
        """Approximate per-worker mineral rate (heuristic)."""
        return min(self.worker_count * 42.0, 1800.0)  # ~42 minerals/worker/min


@dataclass
class CombatEvent:
    """Single combat engagement record."""

    game_id: str
    game_time_seconds: float
    event_type: str  # "attack", "defend", "retreat", "worker_rush"
    units_sent: int
    units_lost: int
    enemy_units_killed: int
    army_value_sent: int  # supply value of engaged army
    army_value_lost: int
    location_x: float = 0.0
    location_y: float = 0.0
    success: bool = False
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class TrainingStep:
    """Single RL training iteration telemetry."""

    step: int
    policy_loss: float
    value_loss: float
    entropy: float
    gradient_norm: float
    learning_rate: float
    avg_reward: float
    batch_size: int
    replay_buffer_size: int
    model_version: str
    environment: str = "training"
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# Fallback sink (no-op / stdout)
# ──────────────────────────────────────────────
class _ConsoleSink:
    """Prints line-protocol-like output when InfluxDB is unavailable."""

    def write(self, bucket: str, record: Any, **kwargs: Any) -> None:
        print(f"[InfluxDB-STUB] bucket={bucket!r} | {record!r}")

    def close(self) -> None:
        pass


# ──────────────────────────────────────────────
# Core writer class
# ──────────────────────────────────────────────
class SC2MetricsWriter:
    """
    Writes SC2 bot telemetry to InfluxDB (or a fallback console sink).

    Usage
    -----
    >>> writer = SC2MetricsWriter.from_env()
    >>> writer.write_economy_snapshot(snap)
    >>> writer.flush()
    >>> writer.close()
    """

    # InfluxDB line-protocol measurement names
    MEASUREMENT_GAME = "sc2_game"
    MEASUREMENT_ECONOMY = "sc2_economy"
    MEASUREMENT_COMBAT = "sc2_combat"
    MEASUREMENT_TRAINING = "sc2_training"

    def __init__(
        self,
        url: str = "http://localhost:8086",
        token: str = "",
        org: str = "sc2bot",
        bucket: str = "sc2bot_metrics",
        batch_size: int = 100,
        flush_interval_ms: int = 5_000,
        enable_gzip: bool = True,
        verbose: bool = False,
    ) -> None:
        self._bucket = bucket
        self._verbose = verbose
        self._closed = False
        self._lock = threading.Lock()

        if _INFLUX_AVAILABLE and token:
            write_options = WriteOptions(
                batch_size=batch_size,
                flush_interval=flush_interval_ms,
                jitter_interval=2_000,
                retry_interval=5_000,
                max_retries=3,
                max_retry_delay=30_000,
                exponential_base=2,
            )
            self._client = InfluxDBClient(
                url=url,
                token=token,
                org=org,
                enable_gzip=enable_gzip,
            )
            self._write_api = self._client.write_api(write_options=write_options)
            self._query_api = self._client.query_api()
            logger.info("SC2MetricsWriter connected to InfluxDB at %s", url)
        else:
            self._client = None
            self._write_api = _ConsoleSink()
            self._query_api = None
            if not _INFLUX_AVAILABLE:
                logger.warning("Using console sink — influxdb_client not available.")
            else:
                logger.warning("Using console sink — no InfluxDB token provided.")

    @classmethod
    def from_env(cls) -> "SC2MetricsWriter":
        """Construct writer from environment variables."""
        return cls(
            url=os.environ.get("INFLUXDB_URL", "http://localhost:8086"),
            token=os.environ.get("INFLUXDB_TOKEN", ""),
            org=os.environ.get("INFLUXDB_ORG", "sc2bot"),
            bucket=os.environ.get("INFLUXDB_BUCKET", "sc2bot_metrics"),
            batch_size=int(os.environ.get("INFLUXDB_BATCH_SIZE", "100")),
            flush_interval_ms=int(os.environ.get("INFLUXDB_FLUSH_INTERVAL_MS", "5000")),
            verbose=os.environ.get("SC2_METRICS_VERBOSE", "").lower() in ("1", "true"),
        )

    # ── Internal helpers ───────────────────────

    def _make_point_dict(
        self, measurement: str, tags: Dict, fields: Dict, ts: datetime
    ) -> str:
        """Build an InfluxDB line-protocol string (fallback path)."""
        tag_str = ",".join(f"{k}={v}" for k, v in tags.items())
        field_str = ",".join(
            f"{k}={v!r}" if isinstance(v, str) else f"{k}={v}"
            for k, v in fields.items()
        )
        ns_ts = int(ts.timestamp() * 1e9)
        return f"{measurement},{tag_str} {field_str} {ns_ts}"

    def _write(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, Any],
        ts: datetime,
    ) -> None:
        """Route to InfluxDB client or console sink."""
        if self._closed:
            raise RuntimeError("SC2MetricsWriter is closed.")

        if _INFLUX_AVAILABLE and self._client is not None:
            try:
                from influxdb_client import Point

                p = Point(measurement)
                for k, v in tags.items():
                    p = p.tag(k, v)
                for k, v in fields.items():
                    p = p.field(k, v)
                p = p.time(ts, WritePrecision.NANOSECONDS)
                self._write_api.write(bucket=self._bucket, record=p)
            except Exception as exc:
                logger.error("InfluxDB write failed: %s", exc)
        else:
            lp = self._make_point_dict(measurement, tags, fields, ts)
            self._write_api.write(bucket=self._bucket, record=lp)

        if self._verbose:
            logger.debug("Wrote %s: tags=%s fields=%s", measurement, tags, fields)

    # ── Public write methods ───────────────────

    def write_game_metrics(self, gm: GameMetrics) -> None:
        """Write end-of-game summary."""
        tags = {
            "game_id": gm.game_id,
            "bot_race": gm.bot_race.value,
            "opponent_race": gm.opponent_race.value,
            "map_name": gm.map_name.replace(" ", "_"),
            "result": gm.result.value,
            "model_version": gm.model_version,
            "environment": gm.environment,
        }
        fields = {
            "duration_seconds": float(gm.duration_seconds),
            "actions_per_minute": float(gm.actions_per_minute),
            "avg_decision_latency_ms": float(gm.avg_decision_latency_ms),
            "won": 1 if gm.result == GameResult.WIN else 0,
        }
        self._write(self.MEASUREMENT_GAME, tags, fields, gm.timestamp)

    def write_economy_snapshot(self, snap: EconomySnapshot) -> None:
        """Write periodic economy state during a game."""
        tags = {
            "game_id": snap.game_id,
            "phase": snap.phase.value,
        }
        fields = {
            "minerals_stored": int(snap.minerals_stored),
            "vespene_stored": int(snap.vespene_stored),
            "minerals_mined_total": int(snap.minerals_mined_total),
            "vespene_mined_total": int(snap.vespene_mined_total),
            "worker_count": int(snap.worker_count),
            "supply_used": int(snap.supply_used),
            "supply_cap": int(snap.supply_cap),
            "army_supply": int(snap.army_supply),
            "base_count": int(snap.base_count),
            "game_time_seconds": float(snap.game_time_seconds),
            "mineral_income_rate": snap.mineral_income_rate,
            "supply_headroom": snap.supply_cap - snap.supply_used,
        }
        self._write(self.MEASUREMENT_ECONOMY, tags, fields, snap.timestamp)

    def write_combat_event(self, event: CombatEvent) -> None:
        """Write a single combat engagement record."""
        tags = {
            "game_id": event.game_id,
            "event_type": event.event_type,
            "success": str(event.success).lower(),
        }
        fields = {
            "units_sent": int(event.units_sent),
            "units_lost": int(event.units_lost),
            "enemy_units_killed": int(event.enemy_units_killed),
            "army_value_sent": int(event.army_value_sent),
            "army_value_lost": int(event.army_value_lost),
            "location_x": float(event.location_x),
            "location_y": float(event.location_y),
            "game_time_seconds": float(event.game_time_seconds),
            "kill_loss_ratio": (event.enemy_units_killed / max(event.units_lost, 1)),
        }
        self._write(self.MEASUREMENT_COMBAT, tags, fields, event.timestamp)

    def write_training_step(self, step: TrainingStep) -> None:
        """Write a single RL training step."""
        tags = {
            "model_version": step.model_version,
            "environment": step.environment,
        }
        fields = {
            "step": int(step.step),
            "policy_loss": float(step.policy_loss),
            "value_loss": float(step.value_loss),
            "entropy": float(step.entropy),
            "gradient_norm": float(step.gradient_norm),
            "learning_rate": float(step.learning_rate),
            "avg_reward": float(step.avg_reward),
            "batch_size": int(step.batch_size),
            "replay_buffer_size": int(step.replay_buffer_size),
        }
        self._write(self.MEASUREMENT_TRAINING, tags, fields, step.timestamp)

    def flush(self) -> None:
        """Force-flush the write buffer (for batch write modes)."""
        if _INFLUX_AVAILABLE and hasattr(self._write_api, "__del__"):
            try:
                self._write_api.flush()
                logger.debug("InfluxDB write buffer flushed.")
            except Exception as exc:
                logger.warning("Flush error: %s", exc)

    def close(self) -> None:
        """Flush remaining data and close the client connection."""
        with self._lock:
            if not self._closed:
                self.flush()
                if self._client is not None:
                    self._client.close()
                self._closed = True
                logger.info("SC2MetricsWriter closed.")

    def __enter__(self) -> "SC2MetricsWriter":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# ──────────────────────────────────────────────
# Query helpers
# ──────────────────────────────────────────────
class SC2MetricsQuery:
    """
    Helper for common Flux aggregation queries against InfluxDB.
    Falls back gracefully if the query API is unavailable.
    """

    def __init__(self, writer: SC2MetricsWriter) -> None:
        self._api = writer._query_api
        self._org = (
            getattr(writer._client, "_org", "sc2bot") if writer._client else "sc2bot"
        )
        self._bucket = writer._bucket

    def _run(self, flux: str) -> List[Any]:
        if self._api is None:
            logger.warning("Query API unavailable — returning empty result.")
            return []
        try:
            return self._api.query(flux, org=self._org)
        except Exception as exc:
            logger.error("Query failed: %s", exc)
            return []

    def win_rate_last_n_games(self, n: int = 100) -> float:
        """Return win rate over last N games."""
        flux = f"""
from(bucket: "{self._bucket}")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "sc2_game")
  |> filter(fn: (r) => r._field == "won")
  |> tail(n: {n})
  |> mean()
"""
        tables = self._run(flux)
        for table in tables:
            for record in table.records:
                return float(record.get_value() or 0.0)
        return 0.0

    def avg_decision_latency_last_hour(self) -> float:
        """Return mean decision latency (ms) over the last hour."""
        flux = f"""
from(bucket: "{self._bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sc2_game")
  |> filter(fn: (r) => r._field == "avg_decision_latency_ms")
  |> mean()
"""
        tables = self._run(flux)
        for table in tables:
            for record in table.records:
                return float(record.get_value() or 0.0)
        return 0.0

    def economy_trend(self, game_id: str) -> List[Dict]:
        """Return economy snapshots for a specific game_id."""
        flux = f"""
from(bucket: "{self._bucket}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "sc2_economy")
  |> filter(fn: (r) => r.game_id == "{game_id}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["game_time_seconds"])
"""
        rows = []
        for table in self._run(flux):
            for record in table.records:
                rows.append(dict(record.values))
        return rows

    def training_loss_summary(self, last_n_steps: int = 1000) -> Dict[str, float]:
        """Return mean policy/value loss and entropy for last N training steps."""
        flux = f"""
from(bucket: "{self._bucket}")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "sc2_training")
  |> filter(fn: (r) =>
       r._field == "policy_loss" or
       r._field == "value_loss" or
       r._field == "entropy"
     )
  |> tail(n: {last_n_steps})
  |> mean()
"""
        result: Dict[str, float] = {}
        for table in self._run(flux):
            for record in table.records:
                result[record.get_field()] = float(record.get_value() or 0.0)
        return result


# ──────────────────────────────────────────────
# Demo / standalone entry point
# ──────────────────────────────────────────────
def _simulate_game(writer: SC2MetricsWriter, game_id: str) -> None:
    """Simulate a complete SC2 game writing economy snapshots and combat events."""
    rng = random.Random(hash(game_id))
    bot_race = rng.choice(list(Race))
    opp_race = rng.choice(list(Race))
    map_name = rng.choice(
        ["Equilibrium", "Gresvan", "Tropical Sacrifice", "Inside and Out"]
    )
    duration = rng.uniform(300, 1200)
    result = rng.choice(list(GameResult))
    model_version = "v2.4.1"

    print(f"\n[GAME {game_id}] {bot_race.value} vs {opp_race.value} on {map_name}")

    minerals_mined = 0
    vespene_mined = 0

    for step_idx, game_time in enumerate(range(0, int(duration), 30)):
        phase = (
            GamePhase.EARLY
            if game_time < 240
            else GamePhase.MID if game_time < 600 else GamePhase.LATE
        )
        workers = min(16 + step_idx * 2, 66)
        supply = min(workers + step_idx * 3, 190)
        minerals_income = int(workers * 42 * 30 / 60)
        vespene_income = int(min(step_idx * 1.5, 6) * 38 * 30 / 60)
        minerals_mined += minerals_income
        vespene_mined += vespene_income

        snap = EconomySnapshot(
            game_id=game_id,
            game_time_seconds=float(game_time),
            minerals_stored=rng.randint(100, 800),
            vespene_stored=rng.randint(0, 400),
            minerals_mined_total=minerals_mined,
            vespene_mined_total=vespene_mined,
            worker_count=workers,
            supply_used=supply,
            supply_cap=min(supply + rng.randint(4, 16), 200),
            army_supply=max(supply - workers, 0),
            base_count=max(1, step_idx // 5),
            phase=phase,
        )
        writer.write_economy_snapshot(snap)

        # Occasional combat event
        if rng.random() < 0.2:
            units = rng.randint(4, 24)
            lost = rng.randint(0, units)
            evt = CombatEvent(
                game_id=game_id,
                game_time_seconds=float(game_time),
                event_type=rng.choice(["attack", "defend", "skirmish"]),
                units_sent=units,
                units_lost=lost,
                enemy_units_killed=rng.randint(0, units + 4),
                army_value_sent=units * 2,
                army_value_lost=lost * 2,
                location_x=rng.uniform(0, 200),
                location_y=rng.uniform(0, 200),
                success=rng.random() > 0.4,
            )
            writer.write_combat_event(evt)

    # End of game
    gm = GameMetrics(
        game_id=game_id,
        bot_race=bot_race,
        opponent_race=opp_race,
        map_name=map_name,
        result=result,
        duration_seconds=duration,
        actions_per_minute=rng.uniform(60, 180),
        avg_decision_latency_ms=rng.uniform(20, 120),
        model_version=model_version,
    )
    writer.write_game_metrics(gm)
    print(
        f"  Result: {result.value} | Duration: {duration:.0f}s | APM: {gm.actions_per_minute:.1f}"
    )


def _simulate_training(writer: SC2MetricsWriter, num_steps: int = 20) -> None:
    """Simulate training steps with typical loss curves."""
    print("\n[TRAINING] Simulating training telemetry ...")
    rng = random.Random(42)
    policy_loss = 3.0
    value_loss = 4.0
    entropy = 1.5
    lr = 3e-4

    for step in range(num_steps):
        policy_loss = max(0.1, policy_loss * 0.92 + rng.gauss(0, 0.05))
        value_loss = max(0.05, value_loss * 0.95 + rng.gauss(0, 0.08))
        entropy = max(0.01, entropy * 0.98 + rng.gauss(0, 0.02))
        grad_norm = abs(rng.gauss(1.5, 0.8))
        reward = rng.gauss(-0.2 + step * 0.02, 0.5)

        ts_step = TrainingStep(
            step=step,
            policy_loss=policy_loss,
            value_loss=value_loss,
            entropy=entropy,
            gradient_norm=grad_norm,
            learning_rate=lr,
            avg_reward=reward,
            batch_size=256,
            replay_buffer_size=10_000 + step * 256,
            model_version="v2.4.1",
        )
        writer.write_training_step(ts_step)

    print(f"  Wrote {num_steps} training steps. Final policy_loss={policy_loss:.4f}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SC2 InfluxDB Metrics Demo")
    parser.add_argument("--url", default="http://localhost:8086")
    parser.add_argument("--token", default=os.environ.get("INFLUXDB_TOKEN", ""))
    parser.add_argument("--org", default="sc2bot")
    parser.add_argument("--bucket", default="sc2bot_metrics")
    parser.add_argument("--games", type=int, default=3)
    parser.add_argument("--training-steps", type=int, default=20)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=== SC2 Bot InfluxDB Metrics Writer Demo ===")
    print(f"Target: {args.url} | Org: {args.org} | Bucket: {args.bucket}")
    if not args.token:
        print("NOTE: No token — using console (stub) sink.\n")

    with SC2MetricsWriter(
        url=args.url,
        token=args.token,
        org=args.org,
        bucket=args.bucket,
        verbose=args.verbose,
    ) as writer:
        for i in range(args.games):
            _simulate_game(writer, game_id=f"game-{i+1:04d}")

        _simulate_training(writer, num_steps=args.training_steps)

        # Demonstrate query helper (no-op if no real InfluxDB)
        q = SC2MetricsQuery(writer)
        wr = q.win_rate_last_n_games(n=50)
        print(f"\n[QUERY] Win rate last 50 games: {wr:.1%}")

    print("\nDone. All metrics flushed and writer closed.")
