# -*- coding: utf-8 -*-
"""Placeholder module — the canonical ChatManager implementation lives elsewhere
or is yet to be written. The previous shim claimed to re-export ``ChatManager``
from ``chat_manager_utf8``, but that module does not exist in the tree, so the
``__all__`` was a lie that broke ``from chat_manager import *`` callers and
flagged ruff F822. Until a real ChatManager is added, expose nothing."""

__all__: list[str] = []
