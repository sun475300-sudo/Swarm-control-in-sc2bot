# -*- coding: utf-8 -*-
"""Compatibility shim. Use chat_manager_utf8.ChatManager as the canonical implementation."""


try:
    from chat_manager_utf8 import ChatManager  # canonical implementation
except ImportError:  # pragma: no cover
    # Canonical module not available; provide a no-op stub so imports succeed.
    class ChatManager:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass


__all__ = ["ChatManager"]
