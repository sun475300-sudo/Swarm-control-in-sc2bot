# -*- coding: utf-8 -*-
"""Placeholder kept so external imports of `wicked_zerg_challenger.chat_manager`
do not fail. The previous shim claimed to re-export `ChatManager` from a
`chat_manager_utf8` module that has never existed in this repo, which made
flake8 flag `__all__` as undefined.

Nothing in the codebase imports from this module today; if a real
ChatManager is reintroduced, define it here or replace this file with the
implementation.
"""

__all__: list[str] = []
