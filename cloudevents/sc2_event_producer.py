"""
Phase 498: CloudEvents Specification for SC2 Event Publishing
CloudEvent attributes: type, source, id, time, datacontenttype
HTTP binding and Kafka binding
SC2 event types: com.sc2bot.game.started, com.sc2bot.unit.killed
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from cloudevents.http import CloudEvent, from_dict
from cloudevents.conversion import to_json, to_structured
from cloudevents.kafka import to_binary as kafka_to_binary
import httpx
from kafka import KafkaProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SC2BOT_SOURCE = "https://sc2bot.io/game-engine"
CONTENT_TYPE = "application/json"

# Event type constants
EVENT_GAME_STARTED = "com.sc2bot.game.started"
EVENT_GAME_ENDED = "com.sc2bot.game.ended"
EVENT_UNIT_KILLED = "com.sc2bot.unit.killed"
EVENT_STRATEGY_PRED = "com.sc2bot.strategy.predicted"


def create_sc2_event(
    event_type: str, data: Dict[str, Any], subject: Optional[str] = None
) -> CloudEvent:
    """Create a CloudEvent for an SC2 game occurrence."""
    attributes = {
        "type": event_type,
        "source": SC2BOT_SOURCE,
        "id": str(uuid.uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": CONTENT_TYPE,
        "specversion": "1.0",
    }
    if subject:
        attributes["subject"] = subject
    return CloudEvent(attributes=attributes, data=data)


def publish_http(event: CloudEvent, endpoint: str) -> bool:
    """Publish CloudEvent via HTTP structured binding."""
    headers, body = to_structured(event)
    try:
        response = httpx.post(endpoint, headers=dict(headers), content=body, timeout=10)
        response.raise_for_status()
        logger.info(f"Published {event['type']} via HTTP to {endpoint}")
        return True
    except httpx.HTTPError as e:
        logger.error(f"HTTP publish failed: {e}")
        return False


def publish_kafka(event: CloudEvent, producer: KafkaProducer, topic: str) -> None:
    """Publish CloudEvent via Kafka binary binding."""
    headers, value = kafka_to_binary(event)
    kafka_headers = [(k, v.encode() if isinstance(v, str) else v) for k, v in headers]
    producer.send(
        topic,
        value=value.encode() if isinstance(value, str) else value,
        headers=kafka_headers,
        key=event["id"].encode(),
    )
    logger.info(f"Published {event['type']} to Kafka topic {topic}")


class SC2EventProducer:
    """High-level SC2 event producer supporting HTTP and Kafka bindings."""

    def __init__(self, http_endpoint: str, kafka_brokers: str):
        self.http_endpoint = http_endpoint
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=kafka_brokers,
            value_serializer=lambda v: v if isinstance(v, bytes) else v.encode(),
        )

    def game_started(self, game_id: str, players: list, map_name: str) -> CloudEvent:
        event = create_sc2_event(
            EVENT_GAME_STARTED,
            data={"gameId": game_id, "players": players, "map": map_name},
            subject=game_id,
        )
        publish_http(event, self.http_endpoint)
        publish_kafka(event, self.kafka_producer, "sc2-game-events")
        return event

    def unit_killed(
        self, game_id: str, unit_type: str, killed_by: str, position: Dict[str, float]
    ) -> CloudEvent:
        event = create_sc2_event(
            EVENT_UNIT_KILLED,
            data={
                "gameId": game_id,
                "unitType": unit_type,
                "killedBy": killed_by,
                "position": position,
            },
            subject=f"{game_id}/{unit_type}",
        )
        publish_kafka(event, self.kafka_producer, "sc2-unit-events")
        return event

    def game_ended(self, game_id: str, winner: str, duration: int) -> CloudEvent:
        event = create_sc2_event(
            EVENT_GAME_ENDED,
            data={"gameId": game_id, "winner": winner, "duration": duration},
            subject=game_id,
        )
        publish_http(event, self.http_endpoint)
        publish_kafka(event, self.kafka_producer, "sc2-game-events")
        return event
