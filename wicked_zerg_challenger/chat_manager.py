# -*- coding: utf-8 -*-
"""Compatibility shim.

Historically this module re-exported ``ChatManager`` from
``chat_manager_utf8``; that submodule was removed before the public source
release.  To keep external imports (``from wicked_zerg_challenger.chat_manager
import ChatManager``) functional we ship a minimal no-op stand-in.
"""


class ChatManager:
    """No-op chat manager used when no canonical implementation is available."""

    def __init__(self, *_args, **_kwargs):
        pass

    async def send(self, *_args, **_kwargs):  # pragma: no cover - trivial stub
        return None

    async def on_step(self, *_args, **_kwargs):  # pragma: no cover - trivial stub
        return None


__all__ = ["ChatManager"]
