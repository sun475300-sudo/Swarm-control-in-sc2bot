"""
ToolDispatcher — 등록형 도구 실행 디스패처
_execute_tool()의 elif 체인을 점진적으로 이관합니다.
"""
from typing import Callable, Dict, Optional
import logging

logger = logging.getLogger("jarvis.tool_dispatcher")


class ToolDispatcher:
    """도구명 → 핸들러 딕셔너리 기반 디스패처."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, tool_name: str):
        """데코레이터: 도구명으로 핸들러 등록"""
        def decorator(func: Callable):
            self._handlers[tool_name] = func
            return func
        return decorator

    def register_many(self, tool_names: list):
        """여러 도구명에 같은 핸들러 등록"""
        def decorator(func: Callable):
            for name in tool_names:
                self._handlers[name] = func
            return func
        return decorator

    async def dispatch(self, name: str, args: str, **kwargs) -> Optional[str]:
        """도구 실행. 등록 안 된 도구는 None 반환 (레거시 폴백)."""
        handler = self._handlers.get(name)
        if handler is None:
            return None  # fallback to legacy
        try:
            return await handler(name=name, args=args, **kwargs)
        except Exception as e:
            logger.error(f"ToolDispatcher '{name}' error: {e}")
            return f"도구 실행 오류: {e}"

    @property
    def registered_tools(self) -> list:
        return list(self._handlers.keys())


# Singleton instance
dispatcher = ToolDispatcher()
