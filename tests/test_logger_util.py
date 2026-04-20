# -*- coding: utf-8 -*-
"""Tests for utils/logger.py — setup_logger, get_logger, reset_all_loggers."""

import sys
import logging
import tempfile
import os
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.logger import setup_logger, get_logger, reset_all_loggers


class TestSetupLogger:
    def test_returns_logger_instance(self):
        logger = setup_logger(name="test_logger_1", log_file=None)
        assert isinstance(logger, logging.Logger)

    def test_logger_name_set(self):
        logger = setup_logger(name="test_logger_name", log_file=None)
        assert logger.name == "test_logger_name"

    def test_custom_level(self):
        logger = setup_logger(name="test_logger_level", level=logging.DEBUG, log_file=None)
        assert logger.level == logging.DEBUG

    def test_no_duplicate_handlers(self):
        logger1 = setup_logger(name="test_dup", log_file=None)
        count_before = len(logger1.handlers)
        logger2 = setup_logger(name="test_dup", log_file=None)
        count_after = len(logger2.handlers)
        assert count_after == count_before

    def test_no_console_handler_when_disabled(self):
        logger = setup_logger(name="test_no_console", log_file=None, log_to_console=False)
        # With no console and no file, handlers could still be empty
        stream_handlers = [h for h in logger.handlers
                          if isinstance(h, logging.StreamHandler)
                          and not isinstance(h, logging.FileHandler)]
        assert len(stream_handlers) == 0

    def test_file_logging(self):
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            fname = f.name
        try:
            os.unlink(fname)
            logger = setup_logger(name="test_file_log", log_file=fname, log_to_console=False)
            logger.info("hello from test")

            # Flush handlers
            for h in logger.handlers:
                h.flush()

            assert os.path.exists(fname)
            with open(fname) as f:
                content = f.read()
            assert "hello from test" in content
        finally:
            if os.path.exists(fname):
                os.unlink(fname)


class TestGetLogger:
    def test_creates_new_if_missing(self):
        logger = get_logger("test_get_new")
        assert isinstance(logger, logging.Logger)

    def test_returns_existing_if_set_up(self):
        first = setup_logger("test_get_existing", log_file=None)
        second = get_logger("test_get_existing")
        # Should be same logger instance (Python's logging.getLogger is a singleton)
        assert first is second

    def test_default_name(self):
        logger = get_logger()
        assert logger.name == "WickedZergBot"


class TestResetAllLoggers:
    def test_clears_handlers(self):
        logger = setup_logger("test_reset", log_file=None)
        assert len(logger.handlers) > 0

        reset_all_loggers()

        assert len(logger.handlers) == 0

    def test_after_reset_can_resetup(self):
        setup_logger("test_resetup", log_file=None)
        reset_all_loggers()
        logger = setup_logger("test_resetup", log_file=None)
        assert len(logger.handlers) > 0
