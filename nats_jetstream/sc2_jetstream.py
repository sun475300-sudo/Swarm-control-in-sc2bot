"""
Phase 447: NATS JetStream - SC2 Persistent Messaging
Streams, durable consumers, and KV store for SC2 game pipeline.
"""

import asyncio
import json
import logging
from datetime import datetime

import nats.js.api as js_api
from nats.aio.client import Client as NATS
from nats.js.errors import NotFoundError

logger = logging.getLogger(__name__)

NATS_URL = "nats://localhost:4222"

# Stream definitions
STREAMS = {
    "SC2_GAMES": ["sc2.games.*"],
    "SC2_EVENTS": ["sc2.events.*"],
    "SC2_ALERTS": ["sc2.alerts.*"],
}

KV_BUCKET = "sc2_game_state"


async def create_streams(js):
    """Create JetStream streams for SC2 pipeline."""
    for stream_name, subjects in STREAMS.items():
        try:
            await js.find_stream(name=stream_name)
            logger.info(f"Stream {stream_name} already exists.")
        except NotFoundError:
            await js.add_stream(
                name=stream_name,
                subjects=subjects,
                retention=js_api.RetentionPolicy.LIMITS,
                max_msgs=1_000_000,
                max_age=7 * 24 * 3600,  # 7 days
                storage=js_api.StorageType.FILE,
                num_replicas=1,
            )
            logger.info(f"Stream {stream_name} created.")


async def create_durable_consumers(js):
    """Create durable consumers for replay processing pipeline."""
    consumers = [
        ("SC2_GAMES", "replay-processor", "sc2.games.>"),
        ("SC2_EVENTS", "event-analyzer", "sc2.events.>"),
        ("SC2_ALERTS", "alert-handler", "sc2.alerts.>"),
    ]
    for stream, consumer_name, filter_subj in consumers:
        try:
            await js.consumer_info(stream, consumer_name)
            logger.info(f"Consumer {consumer_name} exists.")
        except NotFoundError:
            await js.add_consumer(
                stream,
                config=js_api.ConsumerConfig(
                    durable_name=consumer_name,
                    filter_subject=filter_subj,
                    ack_policy=js_api.AckPolicy.EXPLICIT,
                    deliver_policy=js_api.DeliverPolicy.ALL,
                    max_deliver=3,
                    ack_wait=30,
                ),
            )
            logger.info(f"Durable consumer {consumer_name} created.")


async def publish_game_event(js, game_id: str, event_type: str, data: dict):
    """Publish a game event to the appropriate stream."""
    subject = f"sc2.games.{event_type}"
    payload = json.dumps(
        {
            "game_id": game_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
    ).encode()
    ack = await js.publish(subject, payload)
    logger.info(f"Published {event_type} for {game_id}: seq={ack.seq}")
    return ack


async def setup_kv_store(js):
    """Create KV store for game state caching."""
    try:
        kv = await js.key_value(KV_BUCKET)
        logger.info(f"KV bucket {KV_BUCKET} exists.")
    except NotFoundError:
        kv = await js.create_key_value(
            config=js_api.KeyValueConfig(
                bucket=KV_BUCKET,
                max_value_size=1024 * 64,
                history=5,
                ttl=3600,
            )
        )
        logger.info(f"KV bucket {KV_BUCKET} created.")
    return kv


async def cache_game_state(kv, game_id: str, state: dict):
    """Cache current game state in KV store."""
    await kv.put(f"game.{game_id}", json.dumps(state).encode())
    logger.info(f"Game state cached for {game_id}")


async def get_game_state(kv, game_id: str) -> dict:
    """Retrieve cached game state."""
    try:
        entry = await kv.get(f"game.{game_id}")
        return json.loads(entry.value)
    except Exception:
        return {}


async def process_messages(js, stream: str, consumer: str):
    """Process messages from a durable consumer."""
    sub = await js.pull_subscribe("sc2.games.>", consumer, stream=stream)
    msgs = await sub.fetch(10, timeout=2)
    for msg in msgs:
        data = json.loads(msg.data)
        logger.info(f"Processing: {data['event_type']} for game {data['game_id']}")
        await msg.ack()


async def main():
    logging.basicConfig(level=logging.INFO)
    nc = NATS()
    await nc.connect(NATS_URL)
    js = nc.jetstream()

    await create_streams(js)
    await create_durable_consumers(js)
    kv = await setup_kv_store(js)

    await publish_game_event(js, "g001", "started", {"map": "Solaris", "race": "Zerg"})
    await publish_game_event(js, "g001", "ended", {"result": "win", "duration": 420})
    await cache_game_state(kv, "g001", {"supply": 66, "minerals": 250, "gas": 100})

    state = await get_game_state(kv, "g001")
    print("Cached game state:", state)
    await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
