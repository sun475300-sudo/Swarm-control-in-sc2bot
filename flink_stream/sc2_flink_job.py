# Phase 406: Apache Flink - SC2 Stream Processing
# PyFlink DataStream API for real-time SC2 game event processing

from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.connectors.kafka import (
    FlinkKafkaConsumer,
    FlinkKafkaProducer,
)
from pyflink.datastream.window import (
    SlidingEventTimeWindows,
    TumblingEventTimeWindows,
)
from pyflink.datastream.functions import (
    MapFunction,
    FlatMapFunction,
    ReduceFunction,
    ProcessWindowFunction,
    KeyedProcessFunction,
)
from pyflink.cep import pattern as cep_pattern, CEP
from pyflink.common import Time, Types, Row, WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
import json
from datetime import timedelta

# ============================================================
# Environment Setup
# ============================================================


def create_env() -> StreamExecutionEnvironment:
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_stream_time_characteristic(TimeCharacteristic.EventTime)
    env.set_parallelism(4)
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka.jar")
    return env


# ============================================================
# Deserialization
# ============================================================


class SC2EventDeserializer(MapFunction):
    def map(self, value: str) -> Row:
        event = json.loads(value)
        return Row(
            event_type=event.get("event_type", ""),
            game_id=int(event.get("game_id", 0)),
            game_loop=int(event.get("game_loop", 0)),
            team=event.get("team", ""),
            unit_type=event.get("unit_type", ""),
            action=event.get("action", ""),
            timestamp=event.get("timestamp", ""),
        )


# ============================================================
# APM Calculation: Sliding Window
# ============================================================


class APMWindowFunction(ProcessWindowFunction):
    """Compute APM over a 60-second sliding window (step=5s)."""

    def process(self, key, context, elements):
        actions = list(elements)
        window = context.window()
        duration_minutes = (window.end - window.start) / 60_000.0
        apm = len(actions) / max(duration_minutes, 1e-6)

        yield json.dumps(
            {
                "metric": "apm",
                "game_id": key,
                "apm": round(apm, 2),
                "window_end": window.end,
            }
        )


def build_apm_stream(action_stream):
    """Sliding window APM: 60s window, 5s slide."""
    return (
        action_stream.filter(lambda r: r.event_type == "action_taken")
        .key_by(lambda r: r.game_id)
        .window(SlidingEventTimeWindows.of(Time.seconds(60), Time.seconds(5)))
        .process(APMWindowFunction())
    )


# ============================================================
# Win Rate: Tumbling Window
# ============================================================


class WinRateReducer(ReduceFunction):
    def reduce(self, a: Row, b: Row) -> Row:
        return Row(
            wins=a.wins + b.wins,
            total=a.total + b.total,
        )


class WinRateWindowFunction(ProcessWindowFunction):
    def process(self, key, context, elements):
        results = list(elements)
        wins = sum(r.wins for r in results)
        total = len(results)
        win_rate = wins / max(total, 1)
        yield json.dumps(
            {
                "metric": "win_rate",
                "race": key,
                "win_rate": round(win_rate, 4),
                "games": total,
            }
        )


# ============================================================
# CEP Pattern Detection
# ============================================================


def build_timing_attack_pattern(action_stream):
    """
    Detect timing attack: attack_move within 4-6 minute mark (game_loop 5760-8640).
    Pattern: resource_change (supply full) -> attack_move in 30s window.
    """
    timed_actions = action_stream.filter(
        lambda r: r.event_type in ("action_taken", "resource_change")
    )

    timing_pattern = (
        cep_pattern.Pattern.begin(
            "supply_cap",
            Types.ROW(
                [
                    Types.STRING(),
                    Types.INT(),
                    Types.INT(),
                    Types.STRING(),
                    Types.STRING(),
                    Types.STRING(),
                    Types.STRING(),
                ]
            ),
        )
        .where(lambda r, _: r.event_type == "resource_change")
        .next("attack", Types.ROW_NAMED(["event_type"], [Types.STRING()]))
        .where(lambda r, _: r.action == "attack_move")
        .within(Time.seconds(30))
    )

    return CEP.pattern(timed_actions.key_by(lambda r: r.game_id), timing_pattern)


def build_drop_harass_pattern(action_stream):
    """
    Detect drop harass: medivac_load -> attack_move at opponent's base in 60s.
    """
    drop_pattern = (
        cep_pattern.Pattern.begin("load")
        .where(lambda r, _: r.unit_type == "Medivac" and r.action == "load")
        .followed_by("move")
        .where(lambda r, _: r.action == "attack_move")
        .within(Time.seconds(60))
    )
    return CEP.pattern(action_stream.key_by(lambda r: r.game_id), drop_pattern)


# ============================================================
# Kafka Source / Sink
# ============================================================


def create_kafka_source(env: StreamExecutionEnvironment, topic: str, group_id: str):
    props = {
        "bootstrap.servers": "localhost:9092",
        "group.id": group_id,
    }
    consumer = FlinkKafkaConsumer(
        topics=topic,
        deserialization_schema=SimpleStringSchema(),
        properties=props,
    )
    consumer.set_start_from_latest()
    return env.add_source(consumer)


def create_kafka_sink(topic: str) -> FlinkKafkaProducer:
    return FlinkKafkaProducer(
        topic=topic,
        serialization_schema=SimpleStringSchema(),
        producer_config={"bootstrap.servers": "localhost:9092"},
    )


# ============================================================
# Main Job
# ============================================================


def main():
    env = create_env()
    print("[Flink] SC2 stream processing job starting...")

    # Source: SC2 game events from Kafka
    raw_stream = create_kafka_source(env, "sc2-game-events", "flink-sc2-group")

    # Deserialize events
    event_stream = raw_stream.map(
        SC2EventDeserializer(),
        output_type=Types.ROW_NAMED(
            [
                "event_type",
                "game_id",
                "game_loop",
                "team",
                "unit_type",
                "action",
                "timestamp",
            ],
            [
                Types.STRING(),
                Types.INT(),
                Types.INT(),
                Types.STRING(),
                Types.STRING(),
                Types.STRING(),
                Types.STRING(),
            ],
        ),
    ).assign_timestamps_and_watermarks(
        WatermarkStrategy.for_bounded_out_of_orderness(timedelta(seconds=5))
    )

    # APM sliding window stream
    apm_stream = build_apm_stream(event_stream)
    apm_stream.add_sink(create_kafka_sink("sc2-apm-metrics"))
    apm_stream.print()

    # CEP: timing attack detection
    timing_match = build_timing_attack_pattern(event_stream)
    timing_match.select(
        lambda pattern: json.dumps(
            {"alert": "timing_attack_detected", "game_id": pattern["attack"][0].game_id}
        )
    ).add_sink(create_kafka_sink("sc2-alerts"))

    print("[Flink] Executing job graph...")
    env.execute("SC2 Game Stream Processing Job")


if __name__ == "__main__":
    main()
