"""
Tests for sc2_mcp_server module.

Stubs the mcp package when not installed, so the module can be imported
in test environments without the full MCP dependency.
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

# Stub the mcp.server.fastmcp module if not installed so the module imports.
if "mcp" not in sys.modules:
    fake_mcp = MagicMock()
    # FastMCP("name").tool() should return a no-op decorator
    fake_instance = MagicMock()
    fake_instance.tool = lambda *a, **k: (lambda f: f)
    fake_mcp.server.fastmcp.FastMCP = lambda *a, **k: fake_instance
    sys.modules["mcp"] = fake_mcp
    sys.modules["mcp.server"] = fake_mcp.server
    sys.modules["mcp.server.fastmcp"] = fake_mcp.server.fastmcp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sc2_mcp_server  # noqa: E402


class TestFindLatestReplay:
    def test_no_replays_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "_SC2_REPLAY_DIRS", [str(tmp_path)])
        result = sc2_mcp_server._find_latest_replay(5)
        assert result == []

    def test_finds_replay(self, tmp_path, monkeypatch):
        replay = tmp_path / "test.SC2Replay"
        replay.write_bytes(b"fake")
        monkeypatch.setattr(sc2_mcp_server, "_SC2_REPLAY_DIRS", [str(tmp_path)])
        result = sc2_mcp_server._find_latest_replay(5)
        assert len(result) == 1
        assert result[0].endswith("test.SC2Replay")

    def test_returns_most_recent_first(self, tmp_path, monkeypatch):
        old = tmp_path / "old.SC2Replay"
        new = tmp_path / "new.SC2Replay"
        old.write_bytes(b"a")
        new.write_bytes(b"b")
        # Make `old` actually older
        os.utime(str(old), (1000, 1000))
        os.utime(str(new), (2000, 2000))
        monkeypatch.setattr(sc2_mcp_server, "_SC2_REPLAY_DIRS", [str(tmp_path)])
        result = sc2_mcp_server._find_latest_replay(2)
        assert result[0].endswith("new.SC2Replay")
        assert result[1].endswith("old.SC2Replay")

    def test_skips_non_replay_files(self, tmp_path, monkeypatch):
        (tmp_path / "valid.SC2Replay").write_bytes(b"a")
        (tmp_path / "ignore.txt").write_bytes(b"a")
        monkeypatch.setattr(sc2_mcp_server, "_SC2_REPLAY_DIRS", [str(tmp_path)])
        result = sc2_mcp_server._find_latest_replay(10)
        assert len(result) == 1

    def test_respects_limit(self, tmp_path, monkeypatch):
        for i in range(5):
            (tmp_path / f"r{i}.SC2Replay").write_bytes(b"a")
        monkeypatch.setattr(sc2_mcp_server, "_SC2_REPLAY_DIRS", [str(tmp_path)])
        result = sc2_mcp_server._find_latest_replay(2)
        assert len(result) == 2

    def test_respects_max_depth(self, tmp_path, monkeypatch):
        # Create deeply nested .SC2Replay - should be ignored beyond _MAX_DEPTH
        deep = tmp_path
        for d in range(7):
            deep = deep / f"lvl{d}"
            deep.mkdir()
        (deep / "deep.SC2Replay").write_bytes(b"a")
        (tmp_path / "shallow.SC2Replay").write_bytes(b"a")
        monkeypatch.setattr(sc2_mcp_server, "_SC2_REPLAY_DIRS", [str(tmp_path)])
        result = sc2_mcp_server._find_latest_replay(10)
        names = [os.path.basename(p) for p in result]
        assert "shallow.SC2Replay" in names
        # Deep file beyond depth 5 should not be found
        assert "deep.SC2Replay" not in names


class TestListBotLogs:
    @pytest.mark.asyncio
    async def test_missing_dir_returns_message(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.list_bot_logs()
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_lists_log_files(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "a.log").write_text("a")
        (log_dir / "b.log").write_text("b")
        (log_dir / "ignore.txt").write_text("c")
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.list_bot_logs(limit=10)
        assert "a.log" in result
        assert "b.log" in result
        assert "ignore.txt" not in result

    @pytest.mark.asyncio
    async def test_respects_limit(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        for i in range(5):
            (log_dir / f"x{i}.log").write_text("a")
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.list_bot_logs(limit=2)
        assert len(result.splitlines()) == 2


class TestReadLogContent:
    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.read_log_content("../etc/passwd")
        assert "잘못된 파일명" in result or "허용되지 않은" in result

    @pytest.mark.asyncio
    async def test_disallowed_extension_rejected(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "secret.json").write_text("{}")
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.read_log_content("secret.json")
        assert "허용되지 않은 파일 형식" in result

    @pytest.mark.asyncio
    async def test_nonexistent_file_message(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.read_log_content("missing.log")
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_reads_log_content(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        content = "log line 1\nlog line 2\nlog line 3"
        (log_dir / "ok.log").write_text(content)
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.read_log_content("ok.log")
        assert "log line" in result


class TestSetAggressionLevel:
    @pytest.mark.asyncio
    async def test_invalid_level_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.set_aggression_level("nuclear")
        assert "Invalid level" in result

    @pytest.mark.asyncio
    async def test_case_insensitive(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.set_aggression_level("AGGRESSIVE")
        assert "aggressive" in result.lower()

    @pytest.mark.asyncio
    async def test_writes_command_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        await sc2_mcp_server.set_aggression_level("balanced")
        cmd_file = tmp_path / "jarvis_command.json"
        assert cmd_file.exists()
        data = json.loads(cmd_file.read_text())
        assert data["aggression_level"] == "balanced"


class TestSc2BotStats:
    @pytest.mark.asyncio
    async def test_no_data_returns_message(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.sc2_bot_stats()
        assert "찾을 수 없" in result

    @pytest.mark.asyncio
    async def test_parses_game_results(self, tmp_path, monkeypatch):
        games = tmp_path / "wicked_zerg_challenger" / "data" / "games"
        games.mkdir(parents=True)
        (games / "g1.json").write_text(
            json.dumps(
                {
                    "meta": {
                        "opponent_race": "Protoss",
                        "map_name": "TestMap",
                        "timestamp": "2026-05-02T10:00:00",
                    },
                    "game_result": {"result": "VICTORY"},
                }
            )
        )
        (games / "g2.json").write_text(
            json.dumps(
                {
                    "meta": {
                        "opponent_race": "Terran",
                        "map_name": "TestMap",
                        "timestamp": "2026-05-02T11:00:00",
                    },
                    "game_result": {"result": "DEFEAT"},
                }
            )
        )
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.sc2_bot_stats()
        assert "총 게임: 2" in result
        assert "승리: 1" in result
        assert "패배: 1" in result
        assert "Protoss" in result
        assert "Terran" in result


class TestRunSc2TestGame:
    @pytest.mark.asyncio
    async def test_missing_script_returns_helpful_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sc2_mcp_server, "SC2_DIR", str(tmp_path))
        result = await sc2_mcp_server.run_sc2_test_game()
        assert "not found" in result.lower()
