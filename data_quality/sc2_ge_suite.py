"""
Phase 423: Great Expectations - SC2 Training Data Quality
Validates SC2 replay datasets before feeding them to the ML pipeline.
"""

import great_expectations as gx
from great_expectations.core import ExpectationSuite, ExpectationConfiguration
from great_expectations.dataset import PandasDataset
import pandas as pd
import numpy as np
from pathlib import Path


# ── Sample SC2 dataset ────────────────────────────────────────────────────────


def generate_sc2_dataset(n: int = 500) -> pd.DataFrame:
    np.random.seed(42)
    return pd.DataFrame(
        {
            "game_id": [f"g{i:05d}" for i in range(n)],
            "player_id": np.random.randint(1, 200, n),
            "race": np.random.choice(["Zerg", "Terran", "Protoss"], n),
            "opponent_race": np.random.choice(["Zerg", "Terran", "Protoss"], n),
            "map_name": np.random.choice(
                ["Berlingrad", "Ancient Cistern", "Equilibrium"], n
            ),
            "apm": np.random.uniform(40, 300, n).round(1),
            "game_duration": np.random.uniform(90, 1800, n).round(0),
            "supply_peak": np.random.randint(50, 200, n),
            "minerals_spent": np.random.randint(2000, 30000, n),
            "gas_spent": np.random.randint(500, 15000, n),
            "workers_produced": np.random.randint(10, 80, n),
            "winner": np.random.choice([True, False], n),
            "league": np.random.choice(
                [
                    "Bronze",
                    "Silver",
                    "Gold",
                    "Platinum",
                    "Diamond",
                    "Master",
                    "Grandmaster",
                ],
                n,
            ),
        }
    )


# ── Expectation Suite ─────────────────────────────────────────────────────────


def build_sc2_expectation_suite() -> ExpectationSuite:
    """Define all data quality expectations for SC2 replay data."""
    suite = ExpectationSuite(expectation_suite_name="sc2_replay_quality_suite")

    # Not-null expectations
    for col in ["game_id", "player_id", "race", "apm", "game_duration", "winner"]:
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_not_be_null",
                kwargs={"column": col},
            )
        )

    # Unique game_id
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_unique",
            kwargs={"column": "game_id"},
        )
    )

    # Race values must be valid
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_in_set",
            kwargs={"column": "race", "value_set": ["Zerg", "Terran", "Protoss"]},
        )
    )

    # APM range
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={"column": "apm", "min_value": 10, "max_value": 800},
        )
    )

    # Game duration range (seconds)
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={"column": "game_duration", "min_value": 30, "max_value": 7200},
        )
    )

    # Supply peak range
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={"column": "supply_peak", "min_value": 12, "max_value": 200},
        )
    )

    # Workers produced
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={"column": "workers_produced", "min_value": 1, "max_value": 100},
        )
    )

    # Winner is boolean
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_in_set",
            kwargs={"column": "winner", "value_set": [True, False, 0, 1]},
        )
    )

    # Dataset size
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_table_row_count_to_be_between",
            kwargs={"min_value": 100, "max_value": 10_000_000},
        )
    )

    # Expected columns
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_table_columns_to_match_ordered_list",
            kwargs={
                "column_list": [
                    "game_id",
                    "player_id",
                    "race",
                    "opponent_race",
                    "map_name",
                    "apm",
                    "game_duration",
                    "supply_peak",
                    "minerals_spent",
                    "gas_spent",
                    "workers_produced",
                    "winner",
                    "league",
                ]
            },
        )
    )

    return suite


# ── Validation runner ─────────────────────────────────────────────────────────


def validate_sc2_dataset(df: pd.DataFrame, suite: ExpectationSuite) -> dict:
    """Validate SC2 DataFrame against the expectation suite."""
    ge_df = gx.from_pandas(df, expectation_suite=suite)
    results = ge_df.validate()

    summary = {
        "success": results["success"],
        "evaluated": results["statistics"]["evaluated_expectations"],
        "successful": results["statistics"]["successful_expectations"],
        "failed": results["statistics"]["unsuccessful_expectations"],
        "success_pct": results["statistics"]["success_percent"],
    }
    return summary, results


# ── Data docs generation ──────────────────────────────────────────────────────


def generate_data_docs(context, output_dir: str = "data_quality/docs") -> None:
    """Build HTML data docs for validation results."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    context.build_data_docs()
    print(f"[GE] Data docs written to: {output_dir}")


# ── Main runner ───────────────────────────────────────────────────────────────


def run_sc2_data_quality() -> None:
    print("[Great Expectations] Building SC2 data quality suite...")
    df = generate_sc2_dataset(500)
    suite = build_sc2_expectation_suite()

    print(f"[GE] Suite has {len(suite.expectations)} expectations.")
    print(f"[GE] Dataset shape: {df.shape}")

    summary, results = validate_sc2_dataset(df, suite)

    print("\n[Validation Summary]")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    failed = [r for r in results["results"] if not r["success"]]
    if failed:
        print(f"\n[Failed Expectations ({len(failed)})]")
        for r in failed:
            print(
                f"  - {r['expectation_config']['expectation_type']} "
                f"on column '{r['expectation_config']['kwargs'].get('column', 'table')}'"
            )
    else:
        print("\n[All expectations passed!]")

    print("\n[Great Expectations SC2 suite complete.]")


if __name__ == "__main__":
    run_sc2_data_quality()

# Phase 423: Great Expectations registered
