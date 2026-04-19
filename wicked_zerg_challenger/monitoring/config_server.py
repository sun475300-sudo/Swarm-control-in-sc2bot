#!/usr/bin/env python3
import logging

logger = logging.getLogger("ConfigServer")
# -*- coding: utf-8 -*-
"""
Configuration server (placeholder).
"""


class ConfigServer:
    def __init__(self, *args, **kwargs):
        pass

    def run(self) -> None:
        logger.info("ConfigServer placeholder running.")


def main() -> None:
    server = ConfigServer()
    server.run()


if __name__ == "__main__":
    main()
