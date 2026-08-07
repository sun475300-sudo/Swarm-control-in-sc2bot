"""String helpers used by logging, replay parsing, and config."""

from __future__ import annotations

import re

_CAMEL_BOUNDARY = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_INNER = re.compile(r"([a-z0-9])([A-Z])")
_FILENAME_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def to_snake_case(text: str) -> str:
    """Convert ``CamelCase`` or ``camelCase`` to ``snake_case``."""
    s = _CAMEL_BOUNDARY.sub(r"\1_\2", text)
    s = _CAMEL_INNER.sub(r"\1_\2", s)
    return s.lower()


def to_camel_case(text: str, capitalize_first: bool = False) -> str:
    """Convert ``snake_case`` or ``kebab-case`` to ``camelCase``.

    When ``capitalize_first`` is true, returns ``UpperCamelCase`` instead.
    """
    parts = re.split(r"[_\-\s]+", text)
    parts = [p for p in parts if p]
    if not parts:
        return ""
    head = parts[0].capitalize() if capitalize_first else parts[0].lower()
    return head + "".join(p.capitalize() for p in parts[1:])


def truncate(text: str, max_length: int, ellipsis: str = "…") -> str:
    """Truncate ``text`` to ``max_length`` characters (including ellipsis)."""
    if max_length < 0:
        raise ValueError("max_length must be non-negative")
    if len(text) <= max_length:
        return text
    if max_length <= len(ellipsis):
        return ellipsis[:max_length]
    return text[: max_length - len(ellipsis)] + ellipsis


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Replace path-unsafe characters in ``name`` with ``replacement``."""
    cleaned = _FILENAME_INVALID.sub(replacement, name)
    return cleaned.strip(" .") or replacement


def slugify(text: str) -> str:
    """Lowercase, hyphenated, ASCII-only slug suitable for URLs."""
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return text.strip("-").lower()
