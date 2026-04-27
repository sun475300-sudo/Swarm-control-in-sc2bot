"""
Load testing for the SC2 Bot API using Locust.
Three user classes simulate different access patterns:
  - BotPlayer: active game clients requesting actions and reporting results
  - Spectator:  read-only viewers fetching stats and leaderboards
  - Admin:      management operations, health checks, config updates

Run:
    locust -f load_tests/locustfile.py --host http://localhost:8000
    locust -f load_tests/locustfile.py --host http://localhost:8000 --headless -u 50 -r 5 --run-time 60s
"""

from __future__ import annotations

import json
import random
import uuid

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner

# ── Shared data ───────────────────────────────────────────────────────────────

RACES = ["Zerg", "Terran", "Protoss"]
MAPS = ["Catalyst LE", "Equilibrium LE", "Gresvan LE", "Goldenaura LE"]
RESULTS = ["win", "loss", "tie"]


def random_game_state() -> dict:
    return {
        "player_id": random.randint(1, 1000),
        "game_loop": random.randint(0, 10000),
        "minerals": random.randint(0, 2000),
        "vespene": random.randint(0, 1000),
        "supply_used": random.randint(0, 200),
        "supply_cap": 200,
        "unit_count": random.randint(0, 100),
        "enemy_count": random.randint(0, 100),
        "race": random.choice(RACES),
        "enemy_race": random.choice(RACES),
        "map_name": random.choice(MAPS),
    }


def random_result_payload() -> dict:
    return {
        "session_id": str(uuid.uuid4()),
        "player_id": random.randint(1, 1000),
        "result": random.choice(RESULTS),
        "game_loops": random.randint(1000, 20000),
        "score": random.uniform(0.0, 10000.0),
        "opponent_id": str(random.randint(1, 1000)),
        "map_name": random.choice(MAPS),
        "apm": random.randint(50, 400),
    }


# ── BotPlayer: active game client ─────────────────────────────────────────────


class BotPlayer(HttpUser):
    """Simulates an active SC2 bot playing games and requesting actions."""

    weight = 3
    wait_time = between(0.05, 0.2)  # Fast: one request per game tick

    @task(5)
    def get_action(self) -> None:
        """Request next action for current game state."""
        payload = random_game_state()
        with self.client.post(
            "/api/action",
            json=payload,
            name="/api/action",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if "action_type" not in data:
                    resp.failure("Missing action_type in response")
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(1)
    def report_result(self) -> None:
        """Report a completed game result."""
        payload = random_result_payload()
        self.client.post("/api/result", json=payload, name="/api/result")

    @task(2)
    def stream_live(self) -> None:
        """Fetch current live stats snapshot (polling mode)."""
        player_id = random.randint(1, 1000)
        self.client.get(f"/api/live/{player_id}", name="/api/live/[id]")


# ── Spectator: read-only viewer ───────────────────────────────────────────────


class Spectator(HttpUser):
    """Simulates spectators fetching statistics and leaderboards."""

    weight = 5
    wait_time = between(1.0, 5.0)  # Slower: human browsing pace

    @task(3)
    def fetch_leaderboard(self) -> None:
        """Fetch the global leaderboard."""
        self.client.get("/api/leaderboard?limit=20", name="/api/leaderboard")

    @task(2)
    def fetch_player_stats(self) -> None:
        """Fetch stats for a random player."""
        player_id = random.randint(1, 1000)
        self.client.get(
            f"/api/players/{player_id}/stats", name="/api/players/[id]/stats"
        )

    @task(2)
    def fetch_match_history(self) -> None:
        """Fetch recent match history for a player."""
        player_id = random.randint(1, 1000)
        self.client.get(
            f"/api/players/{player_id}/matches?limit=10",
            name="/api/players/[id]/matches",
        )

    @task(1)
    def fetch_health(self) -> None:
        """Check service health endpoint."""
        with self.client.get("/health", name="/health", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")


# ── Admin: management operations ──────────────────────────────────────────────


class Admin(HttpUser):
    """Simulates admin/management operations."""

    weight = 1
    wait_time = between(5.0, 15.0)  # Rare: infrequent admin calls

    @task(3)
    def check_metrics(self) -> None:
        """Fetch Prometheus-style metrics endpoint."""
        self.client.get("/metrics", name="/metrics")

    @task(2)
    def list_active_sessions(self) -> None:
        """List all active game sessions."""
        self.client.get(
            "/api/admin/sessions",
            name="/api/admin/sessions",
            headers={"X-Admin-Token": "test-token"},
        )

    @task(1)
    def trigger_model_reload(self) -> None:
        """Trigger a hot-reload of the bot model weights."""
        self.client.post(
            "/api/admin/reload-model",
            json={"model_version": "latest"},
            name="/api/admin/reload-model",
            headers={"X-Admin-Token": "test-token"},
        )


# ── Event hooks ───────────────────────────────────────────────────────────────


@events.test_start.add_listener
def on_test_start(environment, **kwargs) -> None:
    if isinstance(environment.runner, MasterRunner):
        print("Load test starting on master runner")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs) -> None:
    stats = environment.stats.total
    print(f"\nLoad Test Complete:")
    print(f"  Total requests : {stats.num_requests}")
    print(f"  Failures       : {stats.num_failures}")
    print(f"  Avg latency    : {stats.avg_response_time:.1f} ms")
    print(f"  p95 latency    : {stats.get_response_time_percentile(0.95):.1f} ms")
    print(f"  RPS            : {stats.current_rps:.1f}")
