# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import asyncio
import inspect
import os

import pytest

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


try:
    import pytest_asyncio  # noqa: F401

    _HAS_PYTEST_ASYNCIO = True
except ImportError:  # pragma: no cover - dev convenience path
    _HAS_PYTEST_ASYNCIO = False


# pytest-asyncio가 없는 환경에서도 async def test_* 함수가 silently
# "skipped" 처리되지 않도록 최소한의 러너를 제공한다.
# Async tests use unittest.IsolatedAsyncioTestCase or plain async def +
# asyncio.run().  pytest-asyncio가 설치된 경우 그 동작이 우선 적용된다.
if not _HAS_PYTEST_ASYNCIO:

    @pytest.hookimpl(tryfirst=True)
    def pytest_pyfunc_call(pyfuncitem):
        func = pyfuncitem.obj
        if inspect.iscoroutinefunction(func):
            sig = inspect.signature(func)
            kwargs = {
                name: pyfuncitem.funcargs[name]
                for name in sig.parameters
                if name in pyfuncitem.funcargs
            }
            asyncio.run(func(**kwargs))
            return True
        return None
