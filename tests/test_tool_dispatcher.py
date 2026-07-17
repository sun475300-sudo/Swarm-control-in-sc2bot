# -*- coding: utf-8 -*-
"""ToolDispatcher 단위 테스트 — 등록, 다중 등록, 미등록, 예외 처리."""

import pytest

from jarvis_features.tool_dispatcher import ToolDispatcher


@pytest.fixture
def disp():
    return ToolDispatcher()


class TestRegisterTool:
    def test_register_single(self, disp):
        @disp.register("weather")
        async def handler(**kw):
            return "맑음"

        assert "weather" in disp.registered_tools

    @pytest.mark.asyncio
    async def test_dispatch_registered(self, disp):
        @disp.register("weather")
        async def handler(**kw):
            return "맑음"

        result = await disp.dispatch("weather", "서울")
        assert result == "맑음"


class TestRegisterMany:
    def test_many_registration(self, disp):
        @disp.register_many(["tool_a", "tool_b", "tool_c"])
        async def handler(**kw):
            return "ok"

        assert "tool_a" in disp.registered_tools
        assert "tool_b" in disp.registered_tools
        assert "tool_c" in disp.registered_tools

    @pytest.mark.asyncio
    async def test_all_dispatch_to_same(self, disp):
        @disp.register_many(["x", "y"])
        async def handler(**kw):
            return "shared"

        assert await disp.dispatch("x", "") == "shared"
        assert await disp.dispatch("y", "") == "shared"


class TestDispatchUnknownReturnsNone:
    @pytest.mark.asyncio
    async def test_unknown_tool(self, disp):
        result = await disp.dispatch("nonexistent", "arg")
        assert result is None


class TestDispatchErrorReturnsMessage:
    @pytest.mark.asyncio
    async def test_handler_exception(self, disp):
        @disp.register("broken")
        async def handler(**kw):
            raise RuntimeError("boom")

        result = await disp.dispatch("broken", "")
        assert "도구 실행 오류" in result
        assert "boom" in result
