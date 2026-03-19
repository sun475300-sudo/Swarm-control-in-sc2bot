# -*- coding: utf-8 -*-
"""ToolExecutor 단위 테스트 — 도구 디스패치, 권한 검증, 미지 도구 처리."""

import sys
import types
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# ── discord_jarvis 모듈 stub 생성 (실제 모듈 로드 방지) ──
_stub = types.ModuleType("discord_jarvis")
_stub.web_tools = None
_stub.sc2_mcp_server = None
_stub.system_mcp_server = None
_stub.crypto_mcp_server = None
_stub.agentic_mcp_server = None
_stub.calendar_integration = None
_stub.notion_integration = None
_stub.tool_dispatcher = None
_stub.get_tool_registry = None
_stub._price_alert_store = {}
_stub._price_alert_lock = MagicMock()  # will be replaced per-test
_stub._model_stats = {}
_stub._is_authorized = lambda msg: False
_stub._is_path_allowed = lambda d: True
_stub._detect_language_direction = lambda t: ("en", "ko")
_stub._ast_check_python_code = lambda c: (True, "")
_stub.__file__ = __file__
sys.modules["discord_jarvis"] = _stub

from jarvis_features.tool_executor import ToolExecutor, DANGEROUS_TOOLS


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.memory = None
    bot._message_count = 42
    bot._command_count = 10
    bot.get_uptime.return_value = "1h 23m"
    bot._analyze_screen = AsyncMock(return_value="screen analysis result")
    return bot


@pytest.fixture
def executor(mock_bot):
    return ToolExecutor(mock_bot)


class TestUnknownTool:
    """미지 도구 호출 시 에러 반환."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, executor):
        msg = MagicMock()
        result = await executor.execute("nonexistent_tool_xyz", "", msg, "user1")
        assert result == "Unknown Tool"


class TestDangerousToolAuth:
    """위험 도구 권한 검증."""

    @pytest.mark.asyncio
    async def test_dangerous_tool_blocked_for_non_admin(self, executor):
        """관리자가 아닌 사용자의 위험 도구 호출 차단."""
        msg = MagicMock()
        _stub._is_authorized = lambda m: False
        result = await executor.execute("kill_process", "1234", msg, "user1")
        assert "권한 부족" in result

    @pytest.mark.asyncio
    async def test_dangerous_tool_allowed_for_admin(self, executor):
        """관리자는 위험 도구 실행 가능 (모듈 없으면 모듈 에러 반환)."""
        msg = MagicMock()
        _stub._is_authorized = lambda m: True
        _stub.system_mcp_server = None
        result = await executor.execute("kill_process", "1234", msg, "admin1")
        # system_mcp_server가 None이므로 모듈 에러
        assert "시스템 모듈을 불러올 수 없습니다" in result

    def test_dangerous_tools_set_is_frozen(self):
        """DANGEROUS_TOOLS가 frozenset인지 확인."""
        assert isinstance(DANGEROUS_TOOLS, frozenset)
        assert "kill_process" in DANGEROUS_TOOLS
        assert "ssh_execute" in DANGEROUS_TOOLS


class TestListFeatures:
    """list_features 도구 테스트."""

    @pytest.mark.asyncio
    async def test_list_features_returns_feature_list(self, executor):
        msg = MagicMock()
        result = await executor.execute("list_features", "", msg, "user1")
        assert "JARVIS 사용 가능 기능" in result
        assert "날씨" in result


class TestBotStatus:
    """bot_status 도구 테스트."""

    @pytest.mark.asyncio
    async def test_bot_status_returns_status(self, executor):
        msg = MagicMock()
        _stub._model_stats = {}
        _stub.get_tool_registry = None
        result = await executor.execute("bot_status", "", msg, "user1")
        assert "JARVIS 상태" in result
        assert "1h 23m" in result
        assert "42" in result  # message count


class TestScanScreen:
    """scan_screen 도구가 봇의 _analyze_screen을 호출하는지."""

    @pytest.mark.asyncio
    async def test_scan_screen_delegates_to_bot(self, executor):
        msg = MagicMock()
        result = await executor.execute("scan_screen", "", msg, "user1")
        assert result == "screen analysis result"
        executor.bot._analyze_screen.assert_called_once()


class TestToolNameValidation:
    """도구명 안전성 검증."""

    @pytest.mark.asyncio
    async def test_sql_injection_tool_name(self, executor):
        """SQL 인젝션 스타일 도구명은 Unknown Tool 반환."""
        msg = MagicMock()
        result = await executor.execute("'; DROP TABLE users; --", "", msg, "user1")
        assert result == "Unknown Tool"

    @pytest.mark.asyncio
    async def test_empty_tool_name(self, executor):
        msg = MagicMock()
        result = await executor.execute("", "", msg, "user1")
        assert result == "Unknown Tool"
