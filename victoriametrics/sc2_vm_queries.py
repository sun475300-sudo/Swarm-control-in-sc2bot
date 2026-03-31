# SC2 Bot - VictoriaMetrics Queries
# High-performance Prometheus-compatible time series DB with MetricsQL

import requests
import json
from datetime import datetime, timedelta
from typing import Optional

VMSELECT_URL = "http://vmselect:8481/select/0/prometheus"
VMINSERT_URL = "http://vminsert:8480/insert/0/prometheus"

# --- MetricsQL Queries (superset of PromQL) ---

METRICSQL_QUERIES = {
    # Basic SC2 bot metrics
    "win_rate_5m": 'rate(sc2_bot_wins_total[5m]) / rate(sc2_bot_games_total[5m])',

    # MetricsQL extensions: WITH templates
    "supply_efficiency": """
        WITH (
            supply_used = sc2_supply_used,
            supply_cap  = sc2_supply_cap
        )
        supply_used / supply_cap * 100
    """,

    # ANOMALY_DETECTION: MetricsQL unique function
    "anomaly_apm": 'ANOMALY_DETECTION(sc2_actions_per_minute[1h], "mad")',
    "anomaly_win_rate": 'ANOMALY_DETECTION(rate(sc2_bot_wins_total[10m])[2h:10m], "iqr")',

    # Rollup functions
    "peak_minerals_1h": 'rollup_increase(sc2_minerals_collected_total[1h])',
    "avg_game_duration": 'avg_over_time(sc2_game_duration_seconds[24h])',

    # MetricsQL: keep_last_value fills gaps
    "active_workers": 'keep_last_value(sc2_worker_count)',

    # aggr_over_time: custom aggregation
    "p99_reaction_time": 'aggr_over_time("p99", sc2_reaction_time_ms[1h])',
}

# --- vminsert: Push metrics ---
def push_metric(metric_name: str, value: float, labels: dict, timestamp: Optional[int] = None):
    """Push a metric to VictoriaMetrics via vminsert."""
    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
    ts = timestamp or int(datetime.utcnow().timestamp() * 1000)
    line = f"{metric_name}{{{label_str}}} {value} {ts}"
    resp = requests.post(f"{VMINSERT_URL}/api/v1/import/prometheus", data=line,
                         headers={"Content-Type": "text/plain"})
    resp.raise_for_status()
    return resp.status_code

# --- vmselect: Query metrics ---
def query_instant(metricsql: str) -> dict:
    """Instant query against vmselect."""
    resp = requests.get(f"{VMSELECT_URL}/api/v1/query",
                        params={"query": metricsql})
    resp.raise_for_status()
    return resp.json()

def query_range(metricsql: str, start: datetime, end: datetime, step: str = "1m") -> dict:
    """Range query against vmselect."""
    resp = requests.get(f"{VMSELECT_URL}/api/v1/query_range", params={
        "query": metricsql,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "step": step,
    })
    resp.raise_for_status()
    return resp.json()

# --- Cluster Configuration ---
VM_CLUSTER_CONFIG = {
    "vminsert": {
        "replication_factor": 2,
        "storage_nodes": ["vmstorage-0:8400", "vmstorage-1:8400", "vmstorage-2:8400"],
    },
    "vmselect": {
        "storage_nodes": ["vmstorage-0:8401", "vmstorage-1:8401", "vmstorage-2:8401"],
        "dedup_min_scrape_interval": "1m",
    },
    "vmstorage": {
        "retention_period": "12",  # months
        "storage_data_path": "/var/lib/victoria-metrics-data",
    },
}

def anomaly_detection_example():
    """Run anomaly detection on SC2 APM metric."""
    result = query_instant(METRICSQL_QUERIES["anomaly_apm"])
    for series in result.get("data", {}).get("result", []):
        metric = series["metric"]
        value  = series["value"][1]
        print(f"[VM Anomaly] {metric}: score={value}")

if __name__ == "__main__":
    push_metric("sc2_bot_wins_total", 42.0, {"race": "Zerg", "opponent": "Terran"})
    anomaly_detection_example()
    end = datetime.utcnow()
    start = end - timedelta(hours=1)
    data = query_range(METRICSQL_QUERIES["win_rate_5m"], start, end)
    print(json.dumps(data, indent=2))
