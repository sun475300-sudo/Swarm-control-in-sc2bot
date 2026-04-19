#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix file encoding by converting to UTF-8.

Usage: python fix_encoding.py <file>
"""

import sys
from pathlib import Path
import logging

logger = logging.getLogger("FixEncoding")


def decode_bytes(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass

    try:
        return data.decode("cp949")
    except UnicodeDecodeError:
        pass

    return data.decode("latin-1")


def main() -> int:
    if len(sys.argv) < 2:
        logger.info("Usage: fix_encoding.py <file>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        logger.info(f"File not found: {path}")
        return 2

    try:
        data = path.read_bytes()
        text = decode_bytes(data)
        path.write_text(text, encoding="utf-8")
        logger.info(f"Rewrote {path} as UTF-8")
        return 0
    except OSError as exc:
        logger.error(f"File error: {exc}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
