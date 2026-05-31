"""Classifies exceptions into recovery-relevant categories."""

from __future__ import annotations

from typing import Iterable, Type

CATEGORIES = ("transient", "persistent", "fatal")

_DEFAULT_TRANSIENT: tuple = (TimeoutError, ConnectionError, BlockingIOError)
_DEFAULT_PERSISTENT: tuple = (ValueError, KeyError, LookupError)
_DEFAULT_FATAL: tuple = (MemoryError, SystemError)


class ErrorClassifier:
    """Maps exceptions to one of ``transient``, ``persistent``, or ``fatal``."""

    name = "error_classifier"

    def __init__(
        self,
        transient: Iterable[Type[BaseException]] = (),
        persistent: Iterable[Type[BaseException]] = (),
        fatal: Iterable[Type[BaseException]] = (),
    ) -> None:
        self._transient = tuple(transient) or _DEFAULT_TRANSIENT
        self._persistent = tuple(persistent) or _DEFAULT_PERSISTENT
        self._fatal = tuple(fatal) or _DEFAULT_FATAL

    def classify(self, exc: BaseException) -> str:
        if isinstance(exc, self._fatal):
            return "fatal"
        if isinstance(exc, self._transient):
            return "transient"
        if isinstance(exc, self._persistent):
            return "persistent"
        return "persistent"

    def is_recoverable(self, exc: BaseException) -> bool:
        return self.classify(exc) != "fatal"

    def categories(self) -> tuple:
        return CATEGORIES
