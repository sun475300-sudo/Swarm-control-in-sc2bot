"""
Phase 459: Databricks - SC2 MLflow + Delta + Spark Integration
Databricks Connect for remote cluster, AutoML, Feature Store.
"""

import logging
import os

import mlflow
import mlflow.sklearn
import mlflow.spark
import numpy as np
import pandas as pd
from databricks.connect import DatabricksSession
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
from databricks.sdk import WorkspaceClient
from mlflow.tracking import MlflowClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col, count, stddev, when
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

DATABRICKS_HOST = "https://adb-xxxx.azuredatabricks.net"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")
MLFLOW_URI = f"{DATABRICKS_HOST}/api/2.0/mlflow"
EXPERIMENT_NAME = "/Users/sc2bot/win_rate_prediction"
FEATURE_TABLE = "sc2_features.game_features"
MODEL_NAME = "sc2_win_predictor"


def get_spark() -> SparkSession:
    """Get Databricks remote Spark session via Databricks Connect."""
    spark = DatabricksSession.builder.remote(
        host=DATABRICKS_HOST,
        token=DATABRICKS_TOKEN,
        cluster_id="0101-xxx-yyy",
    ).getOrCreate()
    return spark


def prepare_features(spark: SparkSession):
    """Load game data and engineer features using Spark."""
    df = spark.sql("SELECT * FROM sc2_warehouse.games")

    features = df.select(
        col("game_id"),
        col("player_id"),
        col("apm"),
        col("mmr"),
        col("duration_sec") / 60.0,
        when(col("player_race") == "Zerg", 1).otherwise(0).alias("is_zerg"),
        when(col("player_race") == "Terran", 1).otherwise(0).alias("is_terran"),
        when(col("player_race") == "Protoss", 1).otherwise(0).alias("is_protoss"),
        when(col("result") == "win", 1).otherwise(0).alias("label"),
    )
    return features


def write_feature_store(fe_client: FeatureEngineeringClient, spark: SparkSession):
    """Write features to Databricks Feature Store."""
    features_df = prepare_features(spark)

    fe_client.create_table(
        name=FEATURE_TABLE,
        primary_keys=["game_id"],
        df=features_df,
        description="SC2 game features for win rate prediction",
        tags={"team": "sc2bot", "version": "1.0"},
    )
    logger.info(f"Feature table {FEATURE_TABLE} written.")


def read_feature_store(
    fe_client: FeatureEngineeringClient, game_ids: list
) -> pd.DataFrame:
    """Read features from Feature Store for inference."""
    lookup = FeatureLookup(
        table_name=FEATURE_TABLE,
        lookup_key="game_id",
        feature_names=[
            "apm",
            "mmr",
            "duration_sec",
            "is_zerg",
            "is_terran",
            "is_protoss",
        ],
    )
    inference_df = pd.DataFrame({"game_id": game_ids})
    training_set = fe_client.create_training_set(
        df=inference_df,
        feature_lookups=[lookup],
        label="label",
    )
    return training_set.load_df().toPandas()


def run_automl_experiment(spark: SparkSession):
    """Run Databricks AutoML for win rate prediction."""
    from databricks import automl

    df = prepare_features(spark)
    summary = automl.classify(
        dataset=df,
        target_col="label",
        primary_metric="roc_auc",
        timeout_minutes=30,
        experiment_name=EXPERIMENT_NAME,
    )
    logger.info(f"AutoML best model: {summary.best_trial.model_path}")
    return summary


def train_and_log_model(spark: SparkSession):
    """Train model with MLflow experiment tracking."""
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    features_df = prepare_features(spark).toPandas()
    X = features_df[["apm", "mmr", "is_zerg", "is_terran", "is_protoss"]]
    y = features_df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    with mlflow.start_run(run_name="sc2_gbm_v1") as run:
        params = {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.05}
        mlflow.log_params(params)

        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)

        mlflow.log_metrics({"accuracy": acc, "roc_auc": auc})
        mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
        logger.info(
            f"Model logged: acc={acc:.4f}, auc={auc:.4f}, run_id={run.info.run_id}"
        )
        return run.info.run_id


def promote_model_to_production(run_id: str):
    """Transition best model version to Production stage."""
    client = MlflowClient(tracking_uri=MLFLOW_URI)
    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    latest = max(versions, key=lambda v: int(v.version))
    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=latest.version,
        stage="Production",
        archive_existing_versions=True,
    )
    logger.info(f"Model {MODEL_NAME} v{latest.version} promoted to Production.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("SC2 Databricks integration setup.")
    print(f"MLflow experiment: {EXPERIMENT_NAME}")
    print(f"Feature table: {FEATURE_TABLE}")
    print(f"Model name: {MODEL_NAME}")
    print("Pipeline: Feature Store -> MLflow -> AutoML -> Production promotion")
