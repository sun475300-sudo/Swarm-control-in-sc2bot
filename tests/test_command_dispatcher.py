# -*- coding: utf-8 -*-
"""CommandDispatcher 단위 테스트 — 등록, 디스패치, 매칭 실패, kwargs 전달."""

import pytest

from jarvis_features.command_dispatcher import CommandDispatcher


@pytest.fixture
def disp():
    return CommandDispatcher()


class TestRegisterAddsHandler:
    def test_register_keyword(self, disp):
        @disp.register(["날씨", "weather"])
        async def handler(**kw):
            return "맑음"

        assert disp.handler_count == 1

    def test_register_match_fn(self, disp):
        @disp.register(match_fn=lambda p: "안녕" in p and len(p) < 10)
        async def handler(**kw):
            return "인사"

        assert disp.handler_count == 1


class TestDispatchKeywordMatch:
    @pytest.mark.asyncio
    async def test_keyword_match(self, disp):
        @disp.register(["날씨", "weather"])
        async def handler(**kw):
            return "서울 맑음"

        result = await disp.dispatch("서울 날씨 알려줘")
        assert result == "서울 맑음"

    @pytest.mark.asyncio
    async def test_match_fn_match(self, disp):
        @disp.register(match_fn=lambda p: "시간" in p)
        async def handler(**kw):
            return "12:00"

        result = await disp.dispatch("지금 시간")
        assert result == "12:00"


class TestDispatchNoMatchReturnsNone:
    @pytest.mark.asyncio
    async def test_no_match(self, disp):
        @disp.register(["날씨"])
        async def handler(**kw):
            return "맑음"

        result = await disp.dispatch("시세 BTC")
        assert result is None


class TestDispatchPassesKwargs:
    @pytest.mark.asyncio
    async def test_kwargs_passed(self, disp):
        received = {}

        @disp.register(["테스트"])
        async def handler(**kw):
            received.update(kw)
            return "ok"

        await disp.dispatch("테스트", message="msg_obj", bot="bot_obj", user_id="u1")
        assert received["message"] == "msg_obj"
        assert received["bot"] == "bot_obj"
        assert received["user_id"] == "u1"


class TestMaxLenAndExclude:
    @pytest.mark.asyncio
    async def test_max_len_blocks(self, disp):
        @disp.register(["안녕"], max_len=5)
        async def handler(**kw):
            return "인사"

        result = await disp.dispatch("안녕하세요 반갑습니다 오늘 날씨가 좋네요")
        assert result is None

    @pytest.mark.asyncio
    async def test_exclude_blocks(self, disp):
        @disp.register(["시세"], exclude=["분석"])
        async def handler(**kw):
            return "가격"

        assert await disp.dispatch("BTC 시세") == "가격"
        assert await disp.dispatch("BTC 시세 분석") is None
