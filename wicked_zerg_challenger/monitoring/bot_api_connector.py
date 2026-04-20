#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot API Connector - sends bot status to a remote HTTP endpoint.

Supports fire-and-forget JSON POST with configurable timeout and retry.
"""

import json
import logging
import threading
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

logger = logging.getLogger("BotApiConnector")


class BotAPIConnector:
    """
    Sends bot status updates to a remote HTTP endpoint via non-blocking POST.

    Args:
        url: Base URL of the API endpoint (e.g. "http://localhost:8080/status")
        timeout: HTTP request timeout in seconds.
        max_retries: Number of retry attempts on failure.
    """

    def __init__(
        self,
        url: str = "http://localhost:8080/status",
        timeout: float = 2.0,
        max_retries: int = 1,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_status: Optional[Dict[str, Any]] = None
        self._send_count: int = 0
        self._error_count: int = 0

    def send_status(self, status: Dict[str, Any]) -> None:
        """
        Send status dict to the API endpoint in a background thread.

        Args:
            status: Arbitrary key-value status data to POST as JSON.
        """
        self._last_status = status
        thread = threading.Thread(
            target=self._post_json,
            args=(status,),
            daemon=True,
        )
        thread.start()

    def _post_json(self, data: Dict[str, Any]) -> None:
        """Perform the HTTP POST (called from background thread)."""
        payload = json.dumps(data).encode("utf-8")
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout):
                    pass
                self._send_count += 1
                return
            except urllib.error.URLError as exc:
                if attempt < self.max_retries:
                    continue
                self._error_count += 1
                logger.debug("BotAPIConnector POST failed (attempt %d): %s", attempt + 1, exc)
            except Exception as exc:
                self._error_count += 1
                logger.debug("BotAPIConnector unexpected error: %s", exc)
                return

    @property
    def stats(self) -> Dict[str, int]:
        return {"sent": self._send_count, "errors": self._error_count}


def main() -> None:
    connector = BotAPIConnector()
    connector.send_status({"state": "idle", "minerals": 0, "gas": 0})
    logger.info("BotAPIConnector test status sent.")


if __name__ == "__main__":
    main()
