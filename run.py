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
import sys
from pathlib import Path

# Add bot package to path
bot_dir = Path(__file__).parent / "wicked_zerg_challenger"
sys.path.insert(0, str(bot_dir))

from sc2.player import Bot
from sc2.data import Race
from sc2.client import Client
from sc2.portconfig import Portconfig
from sc2.main import _play_game
from sc2.protocol import ConnectionAlreadyClosed

import aiohttp

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

logger = logging.getLogger(__name__)


def _portconfig_from_start_port(start_port: int) -> Portconfig:
    """Create Portconfig from AI Arena's --StartPort argument."""
    pc = Portconfig.__new__(Portconfig)
    pc.shared = start_port
    pc.server = [start_port + 1, start_port + 2]
    pc.players = [
        [start_port + 3, start_port + 4],
        [start_port + 5, start_port + 6],
    ]
    return pc


async def _run_ladder_game(bot_player: Bot, host: str, game_port: int, start_port: int, opponent_id: str = None):
    """
    Connect to an already-running SC2 instance (managed by AI Arena)
    and play the game.
    """
    portconfig = _portconfig_from_start_port(start_port)
    ws_url = f"ws://{host}:{game_port}/sc2api"

    logger.info(f"Connecting to ladder server: {ws_url}")

    session = aiohttp.ClientSession()
    try:
        ws = await session.ws_connect(ws_url, timeout=120)
        client = Client(ws)

        if opponent_id and hasattr(bot_player.ai, 'opponent_id'):
            bot_player.ai.opponent_id = opponent_id

        result = await _play_game(bot_player, client, realtime=False, portconfig=portconfig)
        logger.info(f"Game result: {result}")

        try:
            await client.leave()
        except (ConnectionAlreadyClosed, Exception):
            pass
        try:
            await client.quit()
        except (ConnectionAlreadyClosed, Exception):
            pass

        return result

    except ConnectionAlreadyClosed:
        logger.error("Connection was closed before the game ended")
        return None
    finally:
        await session.close()


def main():
    parser = argparse.ArgumentParser(description="WickedZergBotPro - AI Arena Entry")
    parser.add_argument("--LadderServer", action="store_true", help="Run in AI Arena ladder mode")
    parser.add_argument("--GamePort", type=int, default=None, help="Game connection port")
    parser.add_argument("--StartPort", type=int, default=None, help="Starting port for configuration")
    parser.add_argument("--OpponentId", type=str, default=None, help="Opponent identifier")
    parser.add_argument("--ComputerRace", type=str, default=None)
    parser.add_argument("--ComputerDifficulty", type=str, default=None)
    parser.add_argument("--ComputerOpponent", type=str, default=None)
    parser.add_argument("--RealTime", action="store_true", default=False)

    args, _ = parser.parse_known_args()

    bot_instance = WickedZergBotProImpl(train_mode=False)
    bot = Bot(Race.Zerg, bot_instance, name="WickedZergBotPro")

    if args.LadderServer:
        if args.GamePort is None or args.StartPort is None:
            logger.error("--GamePort and --StartPort are required for ladder mode")
            sys.exit(1)

        host = "127.0.0.1"
        # Some AI Arena setups pass host via positional or other args
        for i, arg in enumerate(sys.argv):
            if arg == "--LadderServer" and i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                host = sys.argv[i + 1]
                break

        logging.basicConfig(level=logging.INFO)
        logger.info(f"Starting ladder game: host={host}, GamePort={args.GamePort}, StartPort={args.StartPort}")

        result = asyncio.get_event_loop().run_until_complete(
            _run_ladder_game(bot, host, args.GamePort, args.StartPort, args.OpponentId)
        )
        logger.info(f"Final result: {result}")
    else:
        print("[run.py] No --LadderServer flag detected.")
        print("[run.py] For local training, use: python run_with_training.py")
        print("[run.py] For Arena mode, use:     python run.py --LadderServer --GamePort PORT --StartPort PORT")
        sys.exit(1)


if __name__ == "__main__":
    main()
