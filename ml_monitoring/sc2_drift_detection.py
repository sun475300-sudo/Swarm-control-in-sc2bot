"""
Phase 428: Evidently - SC2 ML Monitoring & Drift Detection
Monitors SC2 model health and detects distribution shifts in production.
"""

import pandas as pd
import numpy as np
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, ClassificationPreset
from evidently.metrics import (
    DatasetDriftMetric,
    DatasetMissingValuesMetric,
    ColumnDriftMetric,
    ColumnSummaryMetric,
)
from evidently.test_suite import TestSuite
from evidently.tests import (
    TestNumberOfMissingValues,
    TestShareOfDriftedColumns,
    TestColumnDrift,
    TestValueRange,
)
from pathlib import Path


# ── Data generation ───────────────────────────────────────────────────────────


def generate_reference_data(n: int = 2000) -> pd.DataFrame:
    """Generate reference (training-time) SC2 data distribution."""
    np.random.seed(42)
    return pd.DataFrame(
        {
            "apm": np.random.normal(120, 30, n).clip(40, 300),
            "supply_used": np.random.normal(140, 25, n).clip(50, 200),
            "minerals_spent": np.random.normal(12000, 4000, n).clip(2000, 30000),
            "gas_spent": np.random.normal(5000, 2000, n).clip(500, 15000),
            "game_duration": np.random.normal(450, 150, n).clip(90, 1800),
            "army_value": np.random.normal(8000, 3000, n).clip(500, 20000),
            "workers_produced": np.random.normal(45, 12, n).clip(10, 80),
            "race_enc": np.random.randint(0, 3, n),
            "winner": np.random.randint(0, 2, n),
            "predicted_winner": np.random.randint(0, 2, n),
        }
    )


def generate_production_data(n: int = 500, shift: bool = True) -> pd.DataFrame:
    """Generate production (current) SC2 data with optional distribution shift."""
    np.random.seed(99)
    df = pd.DataFrame(
        {
            "apm": np.random.normal(140 if shift else 120, 35, n).clip(
                40, 300
            ),  # Shift: higher APM
            "supply_used": np.random.normal(155 if shift else 140, 20, n).clip(50, 200),
            "minerals_spent": np.random.normal(14000 if shift else 12000, 5000, n).clip(
                2000, 30000
            ),
            "gas_spent": np.random.normal(6000 if shift else 5000, 2500, n).clip(
                500, 15000
            ),
            "game_duration": np.random.normal(420 if shift else 450, 160, n).clip(
                90, 1800
            ),
            "army_value": np.random.normal(9500 if shift else 8000, 3500, n).clip(
                500, 20000
            ),
            "workers_produced": np.random.normal(50 if shift else 45, 13, n).clip(
                10, 80
            ),
            "race_enc": np.random.randint(0, 3, n),
            "winner": np.random.randint(0, 2, n),
            "predicted_winner": np.random.randint(0, 2, n),
        }
    )
    return df


# ── Reports ───────────────────────────────────────────────────────────────────


def build_game_state_drift_report(
    reference: pd.DataFrame, current: pd.DataFrame
) -> Report:
    """Detect drift in SC2 game state feature distributions."""
    report = Report(
        metrics=[
            DataDriftPreset(),
            DatasetDriftMetric(),
            DatasetMissingValuesMetric(),
            ColumnDriftMetric(column_name="apm"),
            ColumnDriftMetric(column_name="supply_used"),
            ColumnDriftMetric(column_name="army_value"),
            ColumnSummaryMetric(column_name="game_duration"),
        ]
    )
    report.run(reference_data=reference, current_data=current)
    return report


def build_model_performance_report(
    reference: pd.DataFrame, current: pd.DataFrame
) -> Report:
    """Monitor SC2 model classification performance."""
    report = Report(
        metrics=[
            ClassificationPreset(),
        ]
    )
    report.run(
        reference_data=reference,
        current_data=current,
        column_mapping=None,
    )
    return report


# ── Test suites ───────────────────────────────────────────────────────────────


def build_monitoring_test_suite(
    reference: pd.DataFrame, current: pd.DataFrame
) -> TestSuite:
    """Continuous monitoring test suite for SC2 production data."""
    suite = TestSuite(
        tests=[
            TestNumberOfMissingValues(lt=10),
            TestShareOfDriftedColumns(lt=0.3),
            TestColumnDrift(column_name="apm"),
            TestColumnDrift(column_name="supply_used"),
            TestColumnDrift(column_name="army_value"),
            TestValueRange(column_name="apm", left=30, right=400),
            TestValueRange(column_name="game_duration", left=30, right=3600),
        ]
    )
    suite.run(reference_data=reference, current_data=current)
    return suite


# ── Runner ────────────────────────────────────────────────────────────────────


def run_sc2_monitoring(output_dir: str = "ml_monitoring/reports") -> None:
    """Run full SC2 drift detection and monitoring pipeline."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("[Evidently] Generating reference and production data...")
    reference = generate_reference_data(2000)
    current = generate_production_data(500, shift=True)

    print("[Evidently] Running game_state_drift report...")
    drift_report = build_game_state_drift_report(reference, current)
    drift_report.save_html(f"{output_dir}/game_state_drift.html")
    drift_result = drift_report.as_dict()
    dataset_drift = drift_result["metrics"][1]["result"]
    print(f"  Drift detected: {dataset_drift.get('dataset_drift', 'N/A')}")
    print(
        f"  Drifted features: {dataset_drift.get('number_of_drifted_columns', 'N/A')}"
    )

    print("[Evidently] Running monitoring test suite...")
    suite = build_monitoring_test_suite(reference, current)
    suite.save_html(f"{output_dir}/monitoring_tests.html")
    suite_result = suite.as_dict()
    passed = sum(1 for t in suite_result["tests"] if t["status"] == "SUCCESS")
    total = len(suite_result["tests"])
    print(f"  Tests passed: {passed}/{total}")

    print(f"\n[Evidently] Reports saved to: {output_dir}")
    print("[Evidently] SC2 drift detection complete.")


if __name__ == "__main__":
    run_sc2_monitoring()

# Phase 428: Evidently registered
