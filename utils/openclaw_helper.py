# -*- coding: utf-8 -*-
"""
OpenClaw CLI Async Helper for JARVIS Discord Bot.

Provides a centralized async wrapper for calling OpenClaw CLI skills
via subprocess, with JSON parsing, timeout management, and usage stats.
"""

import asyncio
import subprocess
import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("jarvis.openclaw")


def _get_default_openclaw_path() -> str:
    """Get platform-appropriate default OpenClaw CLI path."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidate = str(Path(appdata) / "npm" / "openclaw.cmd")
            if Path(candidate).exists():
                return candidate
    # Fallback: assume it's on PATH
    return "openclaw"


OPENCLAW_PATH = os.environ.get("OPENCLAW_PATH", _get_default_openclaw_path())

# ANSI escape code removal pattern
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class OpenClawHelper:
    """Async wrapper for OpenClaw CLI operations."""

    def __init__(self, cli_path: str = OPENCLAW_PATH):
        self.cli_path = cli_path
        self.available = self._check_availability()
        self.stats: Dict[str, Any] = {
            "total_calls": 0,
            "success_count": 0,
            "error_count": 0,
            "skill_usage": {},
        }

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def _check_availability(self) -> bool:
        try:
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            logger.warning("OpenClaw CLI not found or not responding")
            return False

    # ------------------------------------------------------------------
    # Low-level CLI execution
    # ------------------------------------------------------------------

    async def run_cli(
        self,
        args: List[str],
        timeout: int = 30,
        strip_ansi: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an arbitrary ``openclaw <args>`` command asynchronously.

        Returns dict with keys: success (bool), output (str), error (str).
        """
        if not self.available:
            return {
                "success": False,
                "output": "",
                "error": "OpenClaw CLI is not available.",
            }

        cmd = [self.cli_path] + args
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            if strip_ansi:
                stdout = _strip_ansi(stdout)
                stderr = _strip_ansi(stderr)

            return {
                "success": result.returncode == 0,
                "output": stdout,
                "error": stderr if result.returncode != 0 else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": f"Timed out ({timeout}s)"}
        except Exception as exc:
            logger.error("OpenClaw CLI error: %s", exc)
            return {"success": False, "output": "", "error": "OpenClaw execution failed."}

    # ------------------------------------------------------------------
    # High-level skill runner (via openclaw agent)
    # ------------------------------------------------------------------

    async def run_skill(
        self,
        message: str,
        timeout: int = 45,
        session_id: str = "jarvis-discord",
    ) -> str:
        """
        Send a natural-language *message* to the OpenClaw agent and return
        the text reply.  This is the primary interface for skill invocation.
        """
        self.stats["total_calls"] += 1

        args = [
            "agent",
            "--message", message,
            "--session-id", session_id,
            "--local",
        ]
        result = await self.run_cli(args, timeout=timeout)

        if result["success"]:
            self.stats["success_count"] += 1
            return result["output"] or "(no output)"
        else:
            self.stats["error_count"] += 1
            err = result["error"] or result["output"] or "Unknown error"
            logger.warning("OpenClaw skill failed: %s", err)
            return f"OpenClaw Error: {err}"

    # ------------------------------------------------------------------
    # Direct sub-command helpers
    # ------------------------------------------------------------------

    async def browser(self, action: str, *extra_args: str, timeout: int = 30) -> str:
        args = ["browser", action] + list(extra_args)
        r = await self.run_cli(args, timeout=timeout)
        return r["output"] if r["success"] else f"Error: {r['error']}"

    async def cron(self, action: str, *extra_args: str, timeout: int = 15) -> str:
        args = ["cron", action] + list(extra_args)
        r = await self.run_cli(args, timeout=timeout)
        return r["output"] if r["success"] else f"Error: {r['error']}"

    async def skills_list(self, timeout: int = 15) -> str:
        r = await self.run_cli(["skills", "list"], timeout=timeout)
        return r["output"] if r["success"] else f"Error: {r['error']}"

    async def health(self, timeout: int = 10) -> str:
        r = await self.run_cli(["health"], timeout=timeout)
        return r["output"] if r["success"] else f"Error: {r['error']}"

    async def status(self, timeout: int = 10) -> str:
        r = await self.run_cli(["status"], timeout=timeout)
        return r["output"] if r["success"] else f"Error: {r['error']}"

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return dict(self.stats)

    def record_skill_usage(self, skill_name: str) -> None:
        self.stats["skill_usage"][skill_name] = (
            self.stats["skill_usage"].get(skill_name, 0) + 1
        )


# ------------------------------------------------------------------
# Chunking utility
# ------------------------------------------------------------------


def chunk_text(text: str, limit: int = 1900) -> List[str]:
    """Split *text* into chunks that fit within Discord's message limit."""
    if len(text) <= limit:
        return [text]
    chunks: List[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Try to break at a newline
        idx = text.rfind("\n", 0, limit)
        if idx == -1:
            idx = limit
        chunks.append(text[:idx])
        text = text[idx:].lstrip("\n")
    return chunks


# ------------------------------------------------------------------
# Global singleton (thread-safe)
# ------------------------------------------------------------------

_instance: Optional[OpenClawHelper] = None
_lock = threading.Lock()


def get_openclaw_helper() -> OpenClawHelper:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = OpenClawHelper()
    return _instance
