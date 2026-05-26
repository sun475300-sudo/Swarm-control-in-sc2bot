# -*- coding: utf-8 -*-
"""
utils/logger.py 단위 테스트.
"""

import logging
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.logger import get_logger, reset_all_loggers, setup_logger


class TestSetupLogger(unittest.TestCase):
    def tearDown(self):
        reset_all_loggers()

    def test_returns_logger(self):
        logger = setup_logger(name="TestLogger_1", log_file=None)
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "TestLogger_1")

    def test_no_duplicate_handlers(self):
        name = "TestLogger_NoDup"
        logger1 = setup_logger(name=name, log_file=None)
        logger2 = setup_logger(name=name, log_file=None)
        # 같은 이름이면 같은 logger 반환, handler 중복 없음
        self.assertIs(logger1, logger2)
        self.assertLessEqual(len(logger1.handlers), 2)

    def test_log_file_created(self):
        with TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "subdir" / "test.log"
            logger = setup_logger(name="TestLogger_File", log_file=str(log_file))
            logger.info("test message")
            # subdir 가 자동 생성되었어야 함
            self.assertTrue(log_file.parent.exists())

    def test_console_only(self):
        logger = setup_logger(
            name="TestLogger_ConsoleOnly", log_file=None, log_to_console=True
        )
        # 최소 1개 핸들러 (콘솔)
        self.assertGreaterEqual(len(logger.handlers), 1)

    def test_level_set(self):
        logger = setup_logger(
            name="TestLogger_Level", log_file=None, level=logging.DEBUG
        )
        self.assertEqual(logger.level, logging.DEBUG)


class TestGetLogger(unittest.TestCase):
    def tearDown(self):
        reset_all_loggers()

    def test_first_call_creates_logger(self):
        logger = get_logger("BrandNewLogger")
        self.assertIsInstance(logger, logging.Logger)

    def test_second_call_returns_same(self):
        a = get_logger("SameLogger")
        b = get_logger("SameLogger")
        self.assertIs(a, b)


class TestResetAllLoggers(unittest.TestCase):
    def test_clears_handlers(self):
        logger = setup_logger(name="WillBeReset", log_file=None)
        self.assertGreaterEqual(len(logger.handlers), 1)
        reset_all_loggers()
        # 핸들러가 비워짐
        self.assertEqual(len(logger.handlers), 0)


if __name__ == "__main__":
    unittest.main()
