"""Exercise the actual ladder entry point without launching SC2."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

spec = importlib.util.spec_from_file_location(
    "arena_entrypoint", Path(__file__).resolve().parents[2] / "run.py"
)
entrypoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entrypoint)


def test_ports_match_aiarena_official_1v1_protocol():
    ports = entrypoint._portconfig_from_start_port(5000)
    assert ports.server == [5002, 5003]
    assert ports.players == [[5004, 5005]]
    assert ports.shared == 5001
    ports.clean()  # Real Portconfig initialization must not be bypassed.


@pytest.mark.parametrize("host", ["127.0.0.1", "ladder-host"])
def test_standard_ladder_host_argument(host):
    args = entrypoint.parse_args(
        [f"--LadderServer={host}", "--GamePort", "5000", "--StartPort", "6000"]
    )
    assert args.LadderServer == host


def test_bare_ladder_flag_defaults_to_localhost_and_startport_is_optional():
    args = entrypoint.parse_args(["--LadderServer", "--GamePort", "5000"])
    assert args.LadderServer == "127.0.0.1"
    assert args.StartPort is None


@pytest.mark.parametrize("port", ["0", "65536"])
def test_invalid_game_ports_fail_before_bot_creation(port):
    with pytest.raises(SystemExit):
        entrypoint.parse_args(["--LadderServer", "--GamePort", port])


@pytest.mark.parametrize("port", [0, 65531])
def test_invalid_start_ports_cannot_overflow_udp_ports(port):
    with pytest.raises(ValueError):
        entrypoint._portconfig_from_start_port(port)


@pytest.mark.asyncio
async def test_match_forwards_runner_settings_and_does_not_quit_sc2():
    websocket = SimpleNamespace(close=AsyncMock())
    session = SimpleNamespace(
        ws_connect=AsyncMock(return_value=websocket), close=AsyncMock()
    )
    bot = SimpleNamespace(ai=SimpleNamespace())
    client = MagicMock()
    play = AsyncMock(return_value="Victory")
    with (
        patch.object(entrypoint.aiohttp, "ClientSession", return_value=session),
        patch.object(entrypoint, "Client", return_value=client),
        patch.object(entrypoint, "_play_game", play),
    ):
        result = await entrypoint._run_ladder_game(
            bot, "ladder", 5000, 6000, "enemy", True
        )

    assert result == "Victory"
    assert bot.ai.opponent_id == "enemy"
    assert play.await_args.kwargs["realtime"] is True
    assert play.await_args.kwargs["portconfig"].players == [[6004, 6005]]
    websocket.close.assert_awaited_once()
    session.close.assert_awaited_once()
    client.quit.assert_not_called()


@pytest.mark.asyncio
async def test_connection_failure_is_not_a_successful_game():
    session = SimpleNamespace(
        ws_connect=AsyncMock(side_effect=entrypoint.ConnectionAlreadyClosed()),
        close=AsyncMock(),
    )
    with patch.object(entrypoint.aiohttp, "ClientSession", return_value=session):
        with pytest.raises(RuntimeError, match="before the game ended"):
            await entrypoint._run_ladder_game(
                SimpleNamespace(ai=SimpleNamespace()), "ladder", 5000
            )
    session.close.assert_awaited_once()
