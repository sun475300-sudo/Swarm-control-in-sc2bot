# Phase 405: Apache Kafka - SC2 Event Streaming
# Kafka producer/consumer for real-time SC2 game events

import json
import time
import threading
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass, asdict

from confluent_kafka import Producer, Consumer, KafkaException, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic

# ============================================================
# Topics
# ============================================================

TOPIC_GAME_EVENTS = "sc2-game-events"
TOPIC_ALERTS = "sc2-alerts"
TOPIC_REPLAY = "sc2-replay"

KAFKA_CONFIG = {
    "bootstrap.servers": "localhost:9092",
}

# ============================================================
# Event Data Classes
# ============================================================


@dataclass
class UnitCreatedEvent:
    event_type: str = "unit_created"
    game_id: int = 0
    game_loop: int = 0
    unit_type: str = ""
    team: str = "player"
    x: float = 0.0
    y: float = 0.0
    timestamp: str = ""


@dataclass
class UnitDiedEvent:
    event_type: str = "unit_died"
    game_id: int = 0
    game_loop: int = 0
    unit_type: str = ""
    team: str = "player"
    killer: str = ""
    timestamp: str = ""


@dataclass
class ResourceChangeEvent:
    event_type: str = "resource_change"
    game_id: int = 0
    game_loop: int = 0
    minerals: int = 0
    vespene: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    timestamp: str = ""


@dataclass
class ActionTakenEvent:
    event_type: str = "action_taken"
    game_id: int = 0
    game_loop: int = 0
    action: str = ""
    target_x: float = 0.0
    target_y: float = 0.0
    timestamp: str = ""


# ============================================================
# Producer
# ============================================================


class SC2EventProducer:
    def __init__(self, config: dict = None):
        cfg = config or KAFKA_CONFIG
        self.producer = Producer(cfg)
        self._setup_topics()

    def _setup_topics(self):
        admin = AdminClient(KAFKA_CONFIG)
        topics = [
            NewTopic(TOPIC_GAME_EVENTS, num_partitions=4, replication_factor=1),
            NewTopic(TOPIC_ALERTS, num_partitions=2, replication_factor=1),
            NewTopic(TOPIC_REPLAY, num_partitions=2, replication_factor=1),
        ]
        fs = admin.create_topics(topics)
        for topic, f in fs.items():
            try:
                f.result()
                print(f"[Kafka] Topic created: {topic}")
            except Exception as e:
                print(f"[Kafka] Topic {topic}: {e}")

    def _delivery_report(self, err, msg):
        if err:
            print(f"[Kafka] Delivery failed: {err}")
        else:
            print(
                f"[Kafka] Delivered to {msg.topic()}[{msg.partition()}] offset={msg.offset()}"
            )

    def send_event(self, topic: str, event: dict, key: Optional[str] = None):
        value = json.dumps(event).encode("utf-8")
        k = key.encode("utf-8") if key else None
        self.producer.produce(topic, value=value, key=k, callback=self._delivery_report)
        self.producer.poll(0)

    def send_unit_created(
        self,
        game_id: int,
        game_loop: int,
        unit_type: str,
        team: str,
        x: float,
        y: float,
    ):
        event = UnitCreatedEvent(
            game_id=game_id,
            game_loop=game_loop,
            unit_type=unit_type,
            team=team,
            x=x,
            y=y,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.send_event(TOPIC_GAME_EVENTS, asdict(event), key=str(game_id))

    def send_unit_died(
        self, game_id: int, game_loop: int, unit_type: str, team: str, killer: str
    ):
        event = UnitDiedEvent(
            game_id=game_id,
            game_loop=game_loop,
            unit_type=unit_type,
            team=team,
            killer=killer,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.send_event(TOPIC_GAME_EVENTS, asdict(event), key=str(game_id))

    def send_resource_change(
        self,
        game_id: int,
        game_loop: int,
        minerals: int,
        vespene: int,
        supply_used: int,
        supply_cap: int,
    ):
        event = ResourceChangeEvent(
            game_id=game_id,
            game_loop=game_loop,
            minerals=minerals,
            vespene=vespene,
            supply_used=supply_used,
            supply_cap=supply_cap,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.send_event(TOPIC_GAME_EVENTS, asdict(event), key=str(game_id))

    def send_action(
        self, game_id: int, game_loop: int, action: str, x: float, y: float
    ):
        event = ActionTakenEvent(
            game_id=game_id,
            game_loop=game_loop,
            action=action,
            target_x=x,
            target_y=y,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.send_event(TOPIC_GAME_EVENTS, asdict(event), key=str(game_id))

    def flush(self):
        self.producer.flush()


# ============================================================
# Consumer: Real-time Analytics
# ============================================================


class SC2AnalyticsConsumer:
    def __init__(self, group_id: str = "sc2-analytics", config: dict = None):
        cfg = {
            **(config or KAFKA_CONFIG),
            "group.id": group_id,
            "auto.offset.reset": "earliest",
        }
        self.consumer = Consumer(cfg)
        self.running = False
        self.stats = {
            "unit_created": 0,
            "unit_died": 0,
            "resource_change": 0,
            "action_taken": 0,
        }

    def start(self, topics: list = None):
        topics = topics or [TOPIC_GAME_EVENTS]
        self.consumer.subscribe(topics)
        self.running = True
        print(f"[Kafka Consumer] Subscribed to: {topics}")

        while self.running:
            msg = self.consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            event = json.loads(msg.value().decode("utf-8"))
            self._process_event(event)

    def _process_event(self, event: dict):
        etype = event.get("event_type", "unknown")
        self.stats[etype] = self.stats.get(etype, 0) + 1

        if etype == "unit_died" and event.get("team") == "player":
            self._trigger_alert(f"Player unit lost: {event.get('unit_type')}")

        if etype == "resource_change":
            supply_used = event.get("supply_used", 0)
            supply_cap = event.get("supply_cap", 200)
            if supply_used >= supply_cap - 2:
                self._trigger_alert("Supply blocked!")

    def _trigger_alert(self, message: str):
        print(f"[Kafka Alert] {message}")

    def stop(self):
        self.running = False
        self.consumer.close()
        print(f"[Kafka Consumer] Stopped. Stats: {self.stats}")


# ============================================================
# Main
# ============================================================


def simulate_game_events(producer: SC2EventProducer, game_id: int = 1):
    """Simulate a SC2 game event stream."""
    print(f"[Kafka] Simulating game {game_id}...")

    for loop in range(0, 500, 50):
        producer.send_resource_change(
            game_id,
            loop,
            minerals=400 + loop * 2,
            vespene=200 + loop,
            supply_used=12 + loop // 50,
            supply_cap=22,
        )
        time.sleep(0.05)

    for i in range(5):
        producer.send_unit_created(
            game_id, 100 + i * 10, "Zergling", "player", 20.0 + i, 30.0
        )

    producer.send_unit_died(game_id, 200, "Zergling", "player", "Marine")
    producer.send_action(game_id, 250, "attack_move", 150.0, 160.0)

    producer.flush()
    print(f"[Kafka] Game {game_id} events sent")


if __name__ == "__main__":
    producer = SC2EventProducer()
    simulate_game_events(producer, game_id=42)
    print("[Kafka] Producer done. Start consumer with SC2AnalyticsConsumer().start()")
