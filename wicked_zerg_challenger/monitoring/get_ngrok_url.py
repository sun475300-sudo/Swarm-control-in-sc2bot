#!/usr/bin/env python3
import logging

logger = logging.getLogger("GetNgrokUrl")
# -*- coding: utf-8 -*-
"""
Get ngrok public URL (placeholder).
"""


def get_ngrok_url() -> str:
    return ""


def main() -> None:
    url = get_ngrok_url()
    logger.info(url or "No ngrok URL available.")


if __name__ == "__main__":
    main()
