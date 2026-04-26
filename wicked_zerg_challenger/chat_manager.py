# -*- coding: utf-8 -*-
"""Compatibility shim placeholder.

Historically this module re-exported ``ChatManager`` from ``chat_manager_utf8``,
but that canonical module was removed and no current code-path imports the
symbol. Keeping the file as an empty placeholder preserves any wildcard imports
(``from wicked_zerg_challenger.chat_manager import *``) without exporting an
undefined name.
"""

__all__: list[str] = []
