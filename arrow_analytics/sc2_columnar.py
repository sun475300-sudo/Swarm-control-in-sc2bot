# Phase 409: Apache Arrow - SC2 Columnar Data Processing
# pyarrow columnar processing, Flight service, and Parquet storage

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.flight as flight
import pyarrow.compute as pc
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Iterator, Optional
import threading

# ============================================================
# Schema Definition
# ============================================================

GAME_STATE_SCHEMA = pa.schema(
    [
        pa.field("game_id", pa.int64()),
        pa.field("game_loop", pa.int32()),
        pa.field("minerals", pa.int32()),
        pa.field("vespene", pa.int32()),
        pa.field("supply_used", pa.int8()),
        pa.field("supply_cap", pa.int8()),
        pa.field("worker_count", pa.int8()),
        pa.field("army_supply", pa.int8()),
        pa.field("enemy_visible", pa.bool_()),
        pa.field("timestamp", pa.float64()),
    ]
)

UNIT_SCHEMA = pa.schema(
    [
        pa.field("game_id", pa.int64()),
        pa.field("unit_tag", pa.int64()),
        pa.field("unit_type", pa.dictionary(pa.int8(), pa.string())),
        pa.field("team", pa.dictionary(pa.int8(), pa.string())),
        pa.field("health", pa.float32()),
        pa.field("max_health", pa.float32()),
        pa.field("x", pa.float32()),
        pa.field("y", pa.float32()),
        pa.field("game_loop", pa.int32()),
    ]
)

# ============================================================
# Game State Snapshots as Arrow Table
# ============================================================


def create_game_state_table(n_rows: int = 1000) -> pa.Table:
    """Create a pyarrow Table of game state snapshots."""
    rng = np.random.default_rng(42)

    arrays = {
        "game_id": pa.array(rng.integers(1, 20, n_rows), type=pa.int64()),
        "game_loop": pa.array(rng.integers(0, 22000, n_rows), type=pa.int32()),
        "minerals": pa.array(rng.integers(0, 2000, n_rows), type=pa.int32()),
        "vespene": pa.array(rng.integers(0, 1000, n_rows), type=pa.int32()),
        "supply_used": pa.array(
            rng.integers(12, 200, n_rows).astype(np.int8), type=pa.int8()
        ),
        "supply_cap": pa.array(
            rng.integers(14, 200, n_rows).astype(np.int8), type=pa.int8()
        ),
        "worker_count": pa.array(
            rng.integers(12, 66, n_rows).astype(np.int8), type=pa.int8()
        ),
        "army_supply": pa.array(
            rng.integers(0, 100, n_rows).astype(np.int8), type=pa.int8()
        ),
        "enemy_visible": pa.array(rng.choice([True, False], n_rows)),
        "timestamp": pa.array(rng.uniform(0, 900, n_rows), type=pa.float64()),
    }

    return pa.table(arrays, schema=GAME_STATE_SCHEMA)


# ============================================================
# Columnar Compute with pc (pyarrow.compute)
# ============================================================


def analyze_economy(table: pa.Table) -> dict:
    """Compute economy statistics using Arrow compute functions."""
    minerals = table.column("minerals")
    vespene = table.column("vespene")
    supply_used = table.column("supply_used")
    supply_cap = table.column("supply_cap")

    # Cast for compute
    su = pc.cast(supply_used, pa.int32())
    sc = pc.cast(supply_cap, pa.int32())

    supply_blocked = pc.greater_equal(su, pc.subtract(sc, pa.scalar(2, pa.int32())))

    return {
        "avg_minerals": pc.mean(minerals).as_py(),
        "avg_vespene": pc.mean(vespene).as_py(),
        "max_minerals": pc.max(minerals).as_py(),
        "supply_blocked_pct": pc.mean(pc.cast(supply_blocked, pa.int8())).as_py() * 100,
        "avg_supply_used": pc.mean(su).as_py(),
    }


# ============================================================
# Parquet Write / Read
# ============================================================


def save_to_parquet(table: pa.Table, path: str, compression: str = "snappy"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        path,
        compression=compression,
        use_dictionary=True,
        row_group_size=50_000,
    )
    size_kb = Path(path).stat().st_size / 1024
    print(
        f"[Arrow] Saved {len(table)} rows to {path} ({size_kb:.1f} KB, {compression})"
    )


def load_from_parquet(path: str, columns: Optional[list] = None) -> pa.Table:
    table = pq.read_table(path, columns=columns)
    print(f"[Arrow] Loaded {len(table)} rows, {len(table.schema)} columns from {path}")
    return table


# ============================================================
# Arrow Flight: Streaming Game Data Service
# ============================================================


class SC2FlightServer(flight.FlightServerBase):
    def __init__(self, location: str = "grpc://0.0.0.0:8815"):
        super().__init__(location)
        self._tables: dict = {}
        print(f"[Arrow Flight] Server listening at {location}")

    def do_put(self, context, descriptor, reader, writer):
        """Receive streaming game state data from bot."""
        key = descriptor.path[0].decode()
        batches = []
        for chunk in reader:
            batches.append(chunk.data)
        self._tables[key] = pa.Table.from_batches(batches)
        print(f"[Arrow Flight] Stored table '{key}' with {len(self._tables[key])} rows")

    def do_get(self, context, ticket):
        """Stream table data to analytics clients."""
        key = ticket.ticket.decode()
        if key not in self._tables:
            raise KeyError(f"Table '{key}' not found")
        table = self._tables[key]
        return flight.RecordBatchStream(table)

    def list_flights(self, context, criteria):
        for key in self._tables:
            descriptor = flight.FlightDescriptor.for_path(key)
            info = flight.FlightInfo(
                schema=self._tables[key].schema,
                descriptor=descriptor,
                endpoints=[],
                total_records=len(self._tables[key]),
                total_bytes=-1,
            )
            yield info


def start_flight_server_background() -> SC2FlightServer:
    server = SC2FlightServer()
    t = threading.Thread(target=server.serve, daemon=True)
    t.start()
    return server


# ============================================================
# Main
# ============================================================


def main():
    print("[Arrow] SC2 columnar analytics starting...")

    # Create Arrow Table
    game_states = create_game_state_table(n_rows=2000)
    print(
        f"[Arrow] Table: {game_states.num_rows} rows, {game_states.num_columns} columns"
    )
    print(f"[Arrow] Schema:\n{game_states.schema}")

    # Columnar analytics
    stats = analyze_economy(game_states)
    print("\n=== Economy Statistics ===")
    for k, v in stats.items():
        print(f"  {k:25s}: {v:.2f}")

    # Parquet I/O
    save_to_parquet(game_states, "data/arrow/game_states.parquet")
    loaded = load_from_parquet(
        "data/arrow/game_states.parquet", columns=["game_id", "minerals", "vespene"]
    )

    # Convert subset to pandas
    df = loaded.to_pandas()
    print(f"\n[Arrow] Pandas shape: {df.shape}")
    print(df.head(3).to_string(index=False))

    print("\n[Arrow] Pipeline complete.")


if __name__ == "__main__":
    main()
