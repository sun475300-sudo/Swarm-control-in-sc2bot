#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remote Client - connects to a remote monitoring server for status streaming.

Provides non-blocking connection with auto-reconnect on failure.
"""

import json
import logging
import socket
import threading
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("RemoteClient")


class RemoteClient:
    """
    TCP client that streams JSON status records to a remote server.

    Args:
        host: Server hostname or IP.
        port: Server TCP port.
        reconnect_delay: Seconds to wait between reconnect attempts.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
        reconnect_delay: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.reconnect_delay = reconnect_delay
        self._sock: Optional[socket.socket] = None
        self._connected: bool = False
        self._send_count: int = 0
        self._error_count: int = 0
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """
        Attempt a TCP connection to host:port.

        Returns:
            True if connection succeeded, False otherwise.
        """
        with self._lock:
            if self._connected:
                return True
            try:
                sock = socket.create_connection((self.host, self.port), timeout=3.0)
                self._sock = sock
                self._connected = True
                logger.info("RemoteClient connected to %s:%d", self.host, self.port)
                return True
            except (OSError, socket.timeout) as exc:
                logger.debug("RemoteClient connect failed: %s", exc)
                self._connected = False
                return False

    def disconnect(self) -> None:
        """Close the TCP connection."""
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            self._connected = False

    def send(self, data: Dict[str, Any]) -> bool:
        """
        Send a JSON record over the TCP socket.

        Args:
            data: Dict to serialize and send.

        Returns:
            True on success, False on failure (triggers disconnect).
        """
        if not self._connected:
            self.connect()
            if not self._connected:
                return False

        payload = (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock:
            try:
                if self._sock:
                    self._sock.sendall(payload)
                    self._send_count += 1
                    return True
            except OSError as exc:
                logger.debug("RemoteClient send error: %s", exc)
                self._connected = False
                self._error_count += 1
        return False

    def connect_with_retry(self, max_attempts: int = 3) -> bool:
        """Try to connect up to max_attempts times with reconnect_delay between."""
        for attempt in range(max_attempts):
            if self.connect():
                return True
            if attempt < max_attempts - 1:
                time.sleep(self.reconnect_delay)
        return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> Dict[str, int]:
        return {"sent": self._send_count, "errors": self._error_count}


def main() -> None:
    client = RemoteClient()
    if client.connect():
        client.send({"event": "test", "status": "ok"})
        client.disconnect()
    else:
        logger.info("RemoteClient: no server available (normal in standalone mode)")


if __name__ == "__main__":
    main()
