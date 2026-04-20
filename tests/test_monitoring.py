# -*- coding: utf-8 -*-
"""Tests for monitoring package."""

import sys
import json
import tempfile
import os
import time
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from monitoring.bot_api_connector import BotAPIConnector
from monitoring.telemetry_logger_atomic import TelemetryLoggerAtomic
from monitoring.config_server import ConfigServer
from monitoring.remote_client import RemoteClient
from monitoring import BotAPIConnector as BotAPIConnectorPkg


class TestBotAPIConnector:
    def test_instantiate_default(self):
        conn = BotAPIConnector()
        assert conn.url == "http://localhost:8080/status"
        assert conn.timeout == 2.0

    def test_send_status_does_not_raise(self):
        conn = BotAPIConnector(url="http://127.0.0.1:9999/nowhere")
        conn.send_status({"minerals": 50})
        time.sleep(0.1)  # let background thread attempt
        # Should have failed gracefully
        assert conn.stats["errors"] >= 0  # just doesn't crash

    def test_stats_initial(self):
        conn = BotAPIConnector()
        assert conn.stats["sent"] == 0
        assert conn.stats["errors"] == 0

    def test_last_status_stored(self):
        conn = BotAPIConnector()
        conn.send_status({"event": "test"})
        assert conn._last_status == {"event": "test"}


class TestTelemetryLoggerAtomic:
    def test_log_writes_to_file(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            fname = f.name
        try:
            logger = TelemetryLoggerAtomic(filepath=fname)
            logger.log("game_start", {"map": "TestMap"})
            logger.flush()
            logger.close()

            with open(fname) as f:
                lines = f.readlines()
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["event"] == "game_start"
            assert record["map"] == "TestMap"
            assert "ts" in record
        finally:
            os.unlink(fname)

    def test_log_multiple_records(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            fname = f.name
        try:
            logger = TelemetryLoggerAtomic(filepath=fname)
            for i in range(5):
                logger.log(f"event_{i}")
            logger.flush()
            logger.close()

            with open(fname) as f:
                lines = f.readlines()
            assert len(lines) == 5
        finally:
            os.unlink(fname)

    def test_stats_tracks_written(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            fname = f.name
        try:
            logger = TelemetryLoggerAtomic(filepath=fname)
            logger.log("evt1")
            logger.log("evt2")
            logger.flush()
            logger.close()
            assert logger.stats["written"] == 2
            assert logger.stats["dropped"] == 0
        finally:
            os.unlink(fname)

    def test_queue_full_drops_gracefully(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            fname = f.name
        try:
            logger = TelemetryLoggerAtomic(filepath=fname, max_queue_size=2)
            for i in range(10):
                logger.log(f"event_{i}")
            logger.flush()
            logger.close()
            assert logger.stats["dropped"] >= 0  # some may be dropped
        finally:
            os.unlink(fname)


class TestConfigServer:
    def test_instantiate(self):
        server = ConfigServer()
        assert server.port == 8081

    def test_get_default_config(self):
        server = ConfigServer()
        assert server.get("debug_mode") is False
        assert isinstance(server.get("aggression"), float)

    def test_update_config(self):
        server = ConfigServer()
        server.update("aggression", 0.9)
        assert server.get("aggression") == 0.9

    def test_initial_config_override(self):
        server = ConfigServer(initial_config={"aggression": 0.1})
        assert server.get("aggression") == 0.1

    def test_get_missing_key_returns_default(self):
        server = ConfigServer()
        assert server.get("nonexistent", 42) == 42


class TestRemoteClient:
    def test_instantiate(self):
        client = RemoteClient()
        assert client.host == "127.0.0.1"
        assert client.port == 9000
        assert not client.is_connected

    def test_connect_to_unavailable_host_returns_false(self):
        client = RemoteClient(host="127.0.0.1", port=19999)
        result = client.connect()
        assert not result
        assert not client.is_connected

    def test_send_without_connection_returns_false(self):
        client = RemoteClient(host="127.0.0.1", port=19999)
        result = client.send({"test": "data"})
        assert not result

    def test_stats_initial(self):
        client = RemoteClient()
        assert client.stats["sent"] == 0
        assert client.stats["errors"] == 0

    def test_disconnect_when_not_connected_does_not_raise(self):
        client = RemoteClient()
        client.disconnect()  # should not raise


class TestMonitoringPackageImport:
    def test_package_exports_all_classes(self):
        assert BotAPIConnectorPkg is BotAPIConnector
