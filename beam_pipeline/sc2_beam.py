"""
Phase 451: Apache Beam - SC2 Batch + Streaming Pipeline
PCollection transforms for replay analysis with ParDo and GroupByKey.
"""

import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.transforms.window import SlidingWindows, FixedWindows
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime
from apache_beam.io import ReadFromText, WriteToText
from typing import Iterator

logger = logging.getLogger(__name__)


# ---- DoFn Transforms ----


class ParseReplayFn(beam.DoFn):
    """Parse raw replay JSON into structured event records."""

    def process(self, element: str) -> Iterator[dict]:
        import json

        try:
            record = json.loads(element)
            yield {
                "game_id": record.get("game_id", ""),
                "player_race": record.get("race", "Zerg"),
                "result": record.get("result", "unknown"),
                "apm": int(record.get("apm", 0)),
                "duration": int(record.get("duration", 0)),
                "map_name": record.get("map", ""),
                "units_made": record.get("units", []),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Parse error: {e}")


class ExtractFeaturesFn(beam.DoFn):
    """Extract ML features from a parsed replay record."""

    def process(self, record: dict) -> Iterator[tuple]:
        race = record["player_race"]
        features = {
            "apm_bucket": record["apm"] // 50 * 50,
            "duration_minutes": record["duration"] // 60,
            "unit_diversity": len(set(record.get("units_made", []))),
            "result": 1 if record["result"] == "win" else 0,
        }
        yield (race, features)


class ComputeWinRateFn(beam.DoFn):
    """Compute win rate from grouped race records."""

    def process(self, element: tuple) -> Iterator[dict]:
        race, records = element
        records = list(records)
        total = len(records)
        wins = sum(r["result"] for r in records)
        win_rate = wins / total if total > 0 else 0.0
        avg_apm = sum(r["apm_bucket"] for r in records) / total if total > 0 else 0
        yield {
            "race": race,
            "total_games": total,
            "win_rate": round(win_rate, 4),
            "avg_apm_bucket": avg_apm,
        }


class FormatOutputFn(beam.DoFn):
    """Format results as CSV strings for output."""

    def process(self, record: dict) -> Iterator[str]:
        yield f"{record['race']},{record['total_games']},{record['win_rate']},{record['avg_apm_bucket']}"


# ---- Pipeline Definitions ----


def build_batch_pipeline(
    input_path: str, output_path: str, runner: str = "DirectRunner"
):
    """Batch pipeline for replay archive analysis."""
    options = PipelineOptions(runner=runner)

    with beam.Pipeline(options=options) as p:
        results = (
            p
            | "ReadReplays" >> ReadFromText(input_path)
            | "ParseReplays" >> beam.ParDo(ParseReplayFn())
            | "ExtractFeatures" >> beam.ParDo(ExtractFeaturesFn())
            | "GroupByRace" >> beam.GroupByKey()
            | "ComputeWinRate" >> beam.ParDo(ComputeWinRateFn())
            | "FormatOutput" >> beam.ParDo(FormatOutputFn())
            | "WriteResults"
            >> WriteToText(output_path, header="race,games,win_rate,avg_apm")
        )
    logger.info(f"Batch pipeline complete. Results at {output_path}")


def build_streaming_pipeline(input_topic: str, output_topic: str):
    """Streaming pipeline for live game event processing."""
    options = PipelineOptions(
        runner="DataflowRunner",
        streaming=True,
        project="sc2-bot-project",
        region="us-central1",
        temp_location="gs://sc2-bot-temp/beam",
    )
    options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=options) as p:
        events = (
            p
            | "ReadPubSub" >> beam.io.ReadFromPubSub(topic=input_topic)
            | "ParseEvents" >> beam.ParDo(ParseReplayFn())
            | "Window" >> beam.WindowInto(SlidingWindows(size=300, period=60))
            | "ExtractFeatures" >> beam.ParDo(ExtractFeaturesFn())
            | "GroupByRace" >> beam.GroupByKey()
            | "ComputeWinRate" >> beam.ParDo(ComputeWinRateFn())
            | "FormatOutput" >> beam.ParDo(FormatOutputFn())
            | "WriteOutput" >> beam.io.WriteToPubSub(topic=output_topic)
        )


def run_sample_batch():
    """Run a minimal sample batch pipeline with in-memory data."""
    import json

    sample_data = [
        json.dumps(
            {
                "game_id": "g1",
                "race": "Zerg",
                "result": "win",
                "apm": 185,
                "duration": 420,
                "map": "Solaris",
                "units": ["Zergling", "Roach"],
            }
        ),
        json.dumps(
            {
                "game_id": "g2",
                "race": "Zerg",
                "result": "loss",
                "apm": 140,
                "duration": 360,
                "map": "Solaris",
                "units": ["Zergling"],
            }
        ),
        json.dumps(
            {
                "game_id": "g3",
                "race": "Terran",
                "result": "win",
                "apm": 220,
                "duration": 500,
                "map": "Altitude",
                "units": ["Marine", "Marauder"],
            }
        ),
    ]

    with beam.Pipeline() as p:
        results = (
            p
            | "CreateData" >> beam.Create(sample_data)
            | "ParseReplays" >> beam.ParDo(ParseReplayFn())
            | "ExtractFeatures" >> beam.ParDo(ExtractFeaturesFn())
            | "GroupByRace" >> beam.GroupByKey()
            | "ComputeWinRate" >> beam.ParDo(ComputeWinRateFn())
            | "Print" >> beam.Map(print)
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_sample_batch()
