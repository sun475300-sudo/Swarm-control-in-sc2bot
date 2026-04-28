#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple UTF-8 validation for main_integrated.py."""

import logging
from pathlib import Path

logger = logging.getLogger("CheckEncoding")


def main() -> None:
    filepath = Path(__file__).parent / "main_integrated.py"
    logger.info(f"Checking file: {filepath}")
    logger.info(f"File exists: {filepath.exists()}")

    if not filepath.exists():
        return

    raw_data = filepath.read_bytes()
    logger.info(f"File size: {len(raw_data)} bytes")

    try:
        text = raw_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        logger.error(f"UTF-8 decode error at byte {exc.start}: {exc}")
        logger.info(f"Problem bytes: {raw_data[exc.start:exc.start + 20]}")
        return

    logger.info("File is valid UTF-8")

    try:
        compile(text, str(filepath), "exec")
        logger.info("Syntax is valid")
    except SyntaxError as exc:
        logger.error(f"Syntax error: {exc}")
        if exc.text:
            logger.info(f"Line {exc.lineno}: {exc.text.strip()}")


if __name__ == "__main__":
    main()
