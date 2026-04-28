#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner for scouting and intel systems

Usage:
    python run_scouting_tests.py
"""

import logging
import os
import sys
import unittest

logger = logging.getLogger("RunScoutingTests")

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_tests():
    """Run all scouting and intel tests"""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)

    suite = unittest.TestSuite()

    # Load specific test files
    suite.addTests(loader.loadTestsFromName("test_active_scouting_system"))
    suite.addTests(loader.loadTestsFromName("test_intel_manager"))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("SCOUTING & INTEL SYSTEM TEST SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Tests run: {result.testsRun}")
    logger.error(
        f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}"
    )
    logger.error(f"Failures: {len(result.failures)}")
    logger.error(f"Errors: {len(result.errors)}")
    logger.info("=" * 70)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
