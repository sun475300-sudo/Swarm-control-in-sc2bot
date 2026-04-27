# airflow_dags/sc2_replay_pipeline.py
# Apache Airflow DAG for SC2 Zerg replay analysis pipeline

from datetime import datetime, timedelta
import os
import glob
import sqlite3

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator

# ---------------------------------------------------------------------------
# Default arguments
# ---------------------------------------------------------------------------
default_args = {
    "owner": "zerg_bot",
    "depends_on_past": False,
    "email": ["zergbot@example.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 1, 1),
}

REPLAY_DIR = "/data/sc2_replays"
DB_PATH = "/data/sc2_stats.db"

# ---------------------------------------------------------------------------
# Task callbacks
# ---------------------------------------------------------------------------


def parse_metadata(**context):
    """Read .SC2Replay files and extract basic metadata."""
    replay_files = glob.glob(
        os.path.join(REPLAY_DIR, "**", "*.SC2Replay"), recursive=True
    )
    records = []
    for path in replay_files:
        filename = os.path.basename(path)
        # Simulated parse: real impl would use sc2reader or mpyq
        parts = filename.replace(".SC2Replay", "").split("_")
        matchup = parts[0] if len(parts) > 0 else "ZvT"
        result = parts[1] if len(parts) > 1 else "win"
        date_str = parts[2] if len(parts) > 2 else "20260101"
        records.append(
            {
                "file": filename,
                "matchup": matchup,
                "result": result,
                "date": date_str,
            }
        )
    context["ti"].xcom_push(key="replay_records", value=records)
    print(f"Parsed {len(records)} replay files.")


def compute_stats(**context):
    """Calculate win rates per matchup from parsed metadata."""
    records = context["ti"].xcom_pull(key="replay_records", task_ids="parse_metadata")
    stats = {}
    for rec in records:
        mu = rec["matchup"]
        stats.setdefault(mu, {"wins": 0, "total": 0})
        stats[mu]["total"] += 1
        if rec["result"].lower() == "win":
            stats[mu]["wins"] += 1
    win_rates = {
        mu: round(v["wins"] / v["total"] * 100, 2) if v["total"] else 0
        for mu, v in stats.items()
    }
    context["ti"].xcom_push(key="win_rates", value=win_rates)
    print("Win rates computed:", win_rates)


def load_to_db(**context):
    """Store computed statistics into SQLite database."""
    win_rates = context["ti"].xcom_pull(key="win_rates", task_ids="compute_stats")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS matchup_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matchup TEXT NOT NULL,
            win_rate REAL NOT NULL,
            recorded_at TEXT NOT NULL
        )
    """)
    now = datetime.utcnow().isoformat()
    for matchup, rate in win_rates.items():
        cur.execute(
            "INSERT INTO matchup_stats (matchup, win_rate, recorded_at) VALUES (?, ?, ?)",
            (matchup, rate, now),
        )
    conn.commit()
    conn.close()
    print(f"Stored {len(win_rates)} matchup stats to {DB_PATH}.")


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="sc2_replay_pipeline",
    default_args=default_args,
    description="Daily SC2 Zerg replay analysis pipeline",
    schedule_interval="@daily",
    catchup=False,
    tags=["sc2", "zerg", "replay"],
) as dag:

    extract_replays = BashOperator(
        task_id="extract_replays",
        bash_command=(
            f"mkdir -p {REPLAY_DIR} && "
            f"find {REPLAY_DIR} -name '*.SC2Replay' | wc -l"
        ),
    )

    parse_metadata_task = PythonOperator(
        task_id="parse_metadata",
        python_callable=parse_metadata,
    )

    compute_stats_task = PythonOperator(
        task_id="compute_stats",
        python_callable=compute_stats,
    )

    load_to_db_task = PythonOperator(
        task_id="load_to_db",
        python_callable=load_to_db,
    )

    send_report = EmailOperator(
        task_id="send_report",
        to="zergbot@example.com",
        subject="[SC2 Bot] Daily Replay Analysis Report — {{ ds }}",
        html_content="""
            <h2>SC2 Zerg Bot — Daily Stats</h2>
            <p>Replay pipeline completed for <b>{{ ds }}</b>.</p>
            <p>Check the database at <code>"""
        + DB_PATH
        + """</code> for updated win rates.</p>
        """,
    )

    # Task dependency chain
    (
        extract_replays
        >> parse_metadata_task
        >> compute_stats_task
        >> load_to_db_task
        >> send_report
    )
