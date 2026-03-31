# influxdb_metrics/performance_collector.py
# InfluxDB time-series metrics collection for SC2 Zerg bot performance

import time
import random
import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ---------------------------------------------------------------------------
# InfluxDB configuration
# ---------------------------------------------------------------------------
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "sc2-bot-super-secret-token"
INFLUX_ORG    = "zerg_bot"
INFLUX_BUCKET = "sc2_metrics"

client    = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()


# ---------------------------------------------------------------------------
# Write: game metrics at each second of a game
# ---------------------------------------------------------------------------
def collect_game_metrics(game_id: str, matchup: str, duration_sec: int = 300) -> None:
    """
    Simulate collecting per-second metrics for a single SC2 game and
    write them to InfluxDB as time-series data points.

    Fields written each second:
        army_size        – number of active army units
        minerals         – current mineral bank
        gas              – current gas bank
        win_probability  – model output probability of winning (0.0–1.0)
    """
    print(f"[InfluxDB] Writing metrics for game {game_id} ({matchup}, {duration_sec}s)…")

    base_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=duration_sec)
    points = []

    army      = 0
    minerals  = 500
    gas       = 0
    win_prob  = 0.5

    for second in range(duration_sec):
        # Simulate gradual game progression
        army      = min(200, army + random.randint(0, 2))
        minerals  = max(0, minerals + random.randint(-50, 80))
        gas       = max(0, gas + random.randint(-20, 35))
        win_prob  = max(0.0, min(1.0, win_prob + random.uniform(-0.03, 0.03)))

        ts = base_time + datetime.timedelta(seconds=second)

        point = (
            Point("game_metrics")
            .tag("game_id",  game_id)
            .tag("matchup",  matchup)
            .field("army_size",       army)
            .field("minerals",        minerals)
            .field("gas",             gas)
            .field("win_probability", round(win_prob, 4))
            .time(ts, WritePrecision.SECONDS)
        )
        points.append(point)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    print(f"[InfluxDB] Written {len(points)} data points for game {game_id}.")


# ---------------------------------------------------------------------------
# Query: recent performance over last N games using Flux
# ---------------------------------------------------------------------------
def query_recent_performance(last_n_games: int = 10) -> list[dict]:
    """
    Fetch the average win_probability trend for the most recent N game-seconds
    from InfluxDB using a Flux query.
    """
    flux = f"""
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "game_metrics")
  |> filter(fn: (r) => r._field == "win_probability")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {last_n_games})
  |> yield(name: "recent_win_prob")
"""
    tables  = query_api.query(flux, org=INFLUX_ORG)
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time":     record.get_time(),
                "game_id":  record.values.get("game_id"),
                "matchup":  record.values.get("matchup"),
                "win_prob": round(record.get_value(), 4),
            })
    return results


# ---------------------------------------------------------------------------
# Plot trend (matplotlib fallback to text if unavailable)
# ---------------------------------------------------------------------------
def plot_trend(records: list[dict]) -> None:
    """Render a simple win-probability trend chart."""
    try:
        import matplotlib.pyplot as plt

        times     = [r["time"]     for r in records]
        win_probs = [r["win_prob"] for r in records]

        plt.figure(figsize=(10, 4))
        plt.plot(times, win_probs, marker="o", linewidth=1.5, color="#00aaff")
        plt.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, label="50 % baseline")
        plt.title("SC2 Zerg Bot — Win Probability Trend (last 10 games)")
        plt.xlabel("Time")
        plt.ylabel("Win Probability")
        plt.ylim(0, 1)
        plt.legend()
        plt.tight_layout()
        plt.savefig("/data/win_prob_trend.png", dpi=120)
        print("[Plot] Saved to /data/win_prob_trend.png")
    except ImportError:
        print("[Plot] matplotlib not available — printing text summary instead.")
        for r in records:
            bar = "#" * int(r["win_prob"] * 20)
            print(f"  {r['time']}  [{bar:<20}]  {r['win_prob']:.2%}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Collect metrics for a handful of simulated games
    games = [
        ("game_001", "ZvT", 280),
        ("game_002", "ZvP", 350),
        ("game_003", "ZvZ", 200),
    ]
    for gid, mu, dur in games:
        collect_game_metrics(gid, mu, dur)

    # Query and plot recent performance
    recent = query_recent_performance(last_n_games=10)
    print(f"\n[Query] Retrieved {len(recent)} records.")
    plot_trend(recent)

    client.close()
