# -*- coding: utf-8 -*-
"""
Chat Manager - sends strategic chat messages during a game.

Features:
- Greeting at game start
- Milestone messages (expansion, tech up, rally)
- Configurable message cooldown to avoid spam
- Safe no-op if bot has no chat_send method (e.g. during tests)
"""

from typing import Dict, List, Optional


class ChatManager:
    """Manages bot chat output with cooldowns and milestone tracking."""

    DEFAULT_MESSAGES: Dict[str, List[str]] = {
        "greeting": ["GL HF", "Good luck, have fun!", "GLHF!"],
        "expansion": ["Expanding!", "Taking another base."],
        "tech": ["Tech up!", "Going for new tech."],
        "attack": ["Attack!", "Push incoming!"],
        "defend": ["Defending!", "Holding position."],
        "gg": ["GG", "Good game!", "GG WP"],
    }

    def __init__(
        self,
        bot=None,
        cooldown: float = 10.0,
        messages: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self.bot = bot
        self.cooldown = cooldown
        self.messages: Dict[str, List[str]] = dict(messages) if messages else dict(self.DEFAULT_MESSAGES)
        self._last_sent: Dict[str, float] = {}
        self._send_count: int = 0
        self._greeted: bool = False

    def _now(self) -> float:
        return float(getattr(self.bot, "time", 0.0)) if self.bot else 0.0

    def _pick_message(self, category: str) -> Optional[str]:
        msgs = self.messages.get(category)
        if not msgs:
            return None
        # Simple rotation via send_count to avoid randomness in tests
        return msgs[self._send_count % len(msgs)]

    def send(self, category: str, force: bool = False) -> bool:
        """
        Send a chat message from a category.

        Args:
            category: Message category (e.g. "greeting", "attack").
            force: Bypass cooldown if True.

        Returns:
            True if a message was sent, False otherwise.
        """
        now = self._now()
        if not force:
            last = self._last_sent.get(category, -self.cooldown - 1)
            if now - last < self.cooldown:
                return False

        msg = self._pick_message(category)
        if msg is None:
            return False

        if self.bot and hasattr(self.bot, "chat_send"):
            try:
                self.bot.chat_send(msg)
            except Exception:
                return False

        self._last_sent[category] = now
        self._send_count += 1
        return True

    def greet(self) -> bool:
        """Send a greeting message once per game."""
        if self._greeted:
            return False
        sent = self.send("greeting", force=True)
        if sent:
            self._greeted = True
        return sent

    def say_gg(self) -> bool:
        """Send a GG message."""
        return self.send("gg", force=True)

    def add_message(self, category: str, message: str) -> None:
        """Add a new message to a category (creates category if missing)."""
        self.messages.setdefault(category, []).append(message)

    @property
    def stats(self) -> Dict[str, int]:
        return {"sent": self._send_count, "categories": len(self.messages)}


__all__ = ["ChatManager"]
