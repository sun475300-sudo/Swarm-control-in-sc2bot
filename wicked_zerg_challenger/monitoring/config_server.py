#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config Server - lightweight HTTP server for live bot configuration.

Exposes GET /config and POST /update endpoints so the Android GCS
or any client can read/write the bot's runtime settings.
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger("ConfigServer")

_DEFAULT_CONFIG: Dict[str, Any] = {
    "debug_mode": False,
    "aggression": 0.5,
    "expand_timing": 240,
    "army_size_threshold": 20,
}


class ConfigServer:
    """
    Single-instance HTTP config server running in a daemon thread.

    Args:
        host: Bind address (default 127.0.0.1).
        port: TCP port to listen on.
        initial_config: Initial configuration dict.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8081,
        initial_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.config: Dict[str, Any] = dict(_DEFAULT_CONFIG)
        if initial_config:
            self.config.update(initial_config)
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def run(self) -> None:
        """Start the HTTP server in a background daemon thread."""
        config_ref = self.config

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/config":
                    body = json.dumps(config_ref, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                parsed = urlparse(self.path)
                if parsed.path == "/update":
                    length = int(self.headers.get("Content-Length", 0))
                    try:
                        body = self.rfile.read(length)
                        updates = json.loads(body.decode("utf-8"))
                        config_ref.update(updates)
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b'{"status":"ok"}')
                    except (json.JSONDecodeError, Exception) as exc:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(exc)}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass  # suppress default request logging

        try:
            self._server = HTTPServer((self.host, self.port), _Handler)
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="ConfigServer",
            )
            self._thread.start()
            logger.info("ConfigServer listening on %s:%d", self.host, self.port)
        except OSError as exc:
            logger.warning("ConfigServer failed to start: %s", exc)

    def stop(self) -> None:
        """Shut down the HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def update(self, key: str, value: Any) -> None:
        self.config[key] = value


def main() -> None:
    server = ConfigServer(port=8081)
    server.run()
    logger.info("ConfigServer running. GET /config  POST /update")


if __name__ == "__main__":
    main()
