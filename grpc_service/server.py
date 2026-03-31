"""
gRPC server implementation for SC2 Bot API.
Provides GetAction, StreamGameUpdates, and ReportResult endpoints.
"""

import asyncio
import logging
import uuid
from typing import AsyncIterator

import grpc
from grpc import aio

# In a real project these would be generated from sc2bot.proto:
# import sc2bot_pb2
# import sc2bot_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SC2BotServicer:
    """Implements the SC2BotService gRPC interface."""

    def __init__(self):
        self.match_results: list[dict] = []
        self.active_sessions: dict[str, dict] = {}

    async def GetAction(self, request, context):
        """
        Compute and return the next action for the given game state.
        In production this calls the neural network inference engine.
        """
        logger.info(
            "GetAction: player=%d loop=%d units=%d",
            request.player_id,
            request.game_loop,
            len(request.units),
        )

        # Simple heuristic: attack nearest enemy if available
        if request.enemy_units and request.units:
            attacker = request.units[0]
            target = request.enemy_units[0]
            return {
                "action_type": "attack",
                "unit_tag": attacker.tag,
                "target_tag": target.tag,
                "target_x": target.pos_x,
                "target_y": target.pos_y,
                "ability_id": 23,  # Attack ability
                "confidence": 0.87,
            }

        # Default: collect minerals
        return {
            "action_type": "noop",
            "unit_tag": 0,
            "target_tag": 0,
            "target_x": 0.0,
            "target_y": 0.0,
            "ability_id": 0,
            "confidence": 1.0,
        }

    async def StreamGameUpdates(
        self, request, context
    ) -> AsyncIterator[dict]:
        """
        Stream periodic game state snapshots to subscribed clients.
        Yields an update every 22.4 game loops (~1 real second).
        """
        session_id = request.session_id
        logger.info("StreamGameUpdates: session=%s player=%d", session_id, request.player_id)
        self.active_sessions[session_id] = {"player_id": request.player_id, "loop": 0}

        try:
            for tick in range(100):  # Stream 100 updates then close
                if context.done():
                    break

                update = {
                    "game_loop": tick * 22,
                    "minerals": 50 + tick * 8,
                    "vespene": max(0, tick * 4 - 100),
                    "supply_used": min(200, tick // 5 + 12),
                    "supply_cap": min(200, 14 + (tick // 10) * 8),
                    "unit_count": tick // 5 + 12,
                    "enemy_count": tick // 6 + 10,
                    "army_value": float(tick * 35),
                    "phase": "early" if tick < 30 else ("mid" if tick < 70 else "late"),
                }
                yield update
                await asyncio.sleep(0.1)  # 100ms between updates
        finally:
            self.active_sessions.pop(session_id, None)
            logger.info("Stream ended for session=%s", session_id)

    async def ReportResult(self, request, context) -> dict:
        """Record the result of a completed game and return an ack."""
        match_id = str(uuid.uuid4())
        result_record = {
            "match_id": match_id,
            "session_id": request.session_id,
            "player_id": request.player_id,
            "result": request.result,
            "game_loops": request.game_loops,
            "score": request.score,
            "opponent_id": request.opponent_id,
            "map_name": request.map_name,
            "apm": request.apm,
        }
        self.match_results.append(result_record)
        logger.info(
            "ReportResult: match=%s result=%s score=%.1f apm=%d",
            match_id, request.result, request.score, request.apm,
        )
        return {"success": True, "message": "Result recorded", "match_id": match_id}


async def serve(host: str = "0.0.0.0", port: int = 50051) -> None:
    """Start the gRPC server and block until shutdown."""
    server = aio.server()
    # sc2bot_pb2_grpc.add_SC2BotServiceServicer_to_server(SC2BotServicer(), server)
    server.add_insecure_port(f"{host}:{port}")
    logger.info("SC2Bot gRPC server listening on %s:%d", host, port)
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
