"""
Async test infrastructure sanity check.

If pytest-asyncio is not installed (or asyncio_mode is misconfigured),
every async test in the suite silently fails with the unhelpful message
"async def functions are not natively supported".

This file isolates that failure mode into a single canary test so that
a missing dev-dependency surfaces as one obvious failure rather than 80+
mystery failures scattered across the suite.

If this test fails, install:

    pip install -r requirements-dev.txt
"""

import asyncio


async def test_async_runtime_runs():
    """A trivial async test that proves the asyncio plugin is active."""
    await asyncio.sleep(0)
    assert True


async def test_async_event_loop_is_real():
    """Confirm we have a real running loop (not a stub)."""
    loop = asyncio.get_running_loop()
    assert loop is not None
    assert loop.is_running()
