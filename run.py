#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Arena entry point for WickedZergBotPro.

AI Arena invokes:
    python run.py --LadderServer --GamePort PORT --StartPort PORT

burnysc2 v7.1.3 does NOT provide run_ladder_game(),
so we implement ladder game joining directly via WebSocket.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add bot package to path
bot_dir = Path(__file__).parent / "wicked_zerg_challenger"
sys.path.insert(0, str(bot_dir))
# Older s2clientprotocol distributions require the Python protobuf backend.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import aiohttp
from sc2.client import Client
from sc2.data import Race
from sc2.main import _play_game
from sc2.player import Bot
from sc2.portconfig import Portconfig

try:
    from sc2.protocol import ConnectionAlreadyClosedError as ConnectionAlreadyClosed
except ImportError:  # burnysc2 releases before the exception rename
    from sc2.protocol import ConnectionAlreadyClosed
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

logger = logging.getLogger(__name__)


def _portconfig_from_start_port(start_port: int) -> Portconfig:
    """Use the 1v1 port layout in AI Arena's official example bots."""
    if not 1 <= start_port <= 65530:
        raise ValueError("StartPort must be between 1 and 65530")
    pc = Portconfig(
        server_ports=[start_port + 2, start_port + 3],
        player_ports=[[start_port + 4, start_port + 5]],
    )
    pc.shared = start_port + 1
    return pc


async def _run_ladder_game(
    bot_player: Bot,
    host: str,
    game_port: int,
    start_port: int = None,
    opponent_id: str = None,
    realtime: bool = False,
):
    """
    Connect to an already-running SC2 instance (managed by AI Arena)
    and play the game.
    """
    portconfig = (
        _portconfig_from_start_port(start_port) if start_port is not None else None
    )
    ws_url = f"ws://{host}:{game_port}/sc2api"

    logger.info(f"Connecting to ladder server: {ws_url}")

    session = aiohttp.ClientSession()
    ws = None
    try:
        ws = await session.ws_connect(ws_url, timeout=120)
        client = Client(ws)

        bot_player.ai.opponent_id = opponent_id

        result = await _play_game(
            bot_player, client, realtime=realtime, portconfig=portconfig
        )
        logger.info(f"Game result: {result}")

        return result

    except ConnectionAlreadyClosed:
        raise RuntimeError("Connection was closed before the game ended") from None
    finally:
        # The ladder runner owns the SC2 process; do not issue client.quit().
        try:
            if ws is not None:
                await ws.close()
        finally:
            await session.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="WickedZergBotPro - AI Arena Entry")
    parser.add_argument(
        "--LadderServer", nargs="?", const="127.0.0.1", help="Ladder server host"
    )
    parser.add_argument(
        "--GamePort", type=int, default=None, help="Game connection port"
    )
    parser.add_argument(
        "--StartPort", type=int, default=None, help="Starting port for configuration"
    )
    parser.add_argument(
        "--OpponentId", type=str, default=None, help="Opponent identifier"
    )
    parser.add_argument("--ComputerRace", type=str, default=None)
    parser.add_argument("--ComputerDifficulty", type=str, default=None)
    parser.add_argument("--ComputerOpponent", type=str, default=None)
    parser.add_argument("--RealTime", action="store_true", default=False)

    args, _ = parser.parse_known_args(argv)
    if args.LadderServer is not None:
        if args.GamePort is None or not 1 <= args.GamePort <= 65535:
            parser.error("--GamePort must be between 1 and 65535 in ladder mode")
        if args.StartPort is not None and not 1 <= args.StartPort <= 65530:
            parser.error("--StartPort must be between 1 and 65530")
    return args


def main(argv=None):
    args = parse_args(argv)

    bot_instance = WickedZergBotProImpl(train_mode=False)
    bot = Bot(Race.Zerg, bot_instance, name="WickedZergBotPro")

    if args.LadderServer is not None:
        host = args.LadderServer

        logging.basicConfig(level=logging.INFO)
        logger.info(
            f"Starting ladder game: host={host}, GamePort={args.GamePort}, StartPort={args.StartPort}"
        )

        result = asyncio.run(
            _run_ladder_game(
                bot, host, args.GamePort, args.StartPort, args.OpponentId, args.RealTime
            )
        )
        logger.info(f"Final result: {result}")
        return 0 if result is not None else 1
    else:
        print("[run.py] No --LadderServer flag detected.")
        print(
            "[run.py] For local training, use: python wicked_zerg_challenger/run_with_training.py"
        )
        print(
            "[run.py] For Arena mode, use:     python run.py --LadderServer --GamePort PORT --StartPort PORT"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
