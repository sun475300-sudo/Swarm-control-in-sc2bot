"""
CommandDispatcher — 등록형 명령 핸들러 디스패처
_try_local_response()의 if-elif 체인을 점진적으로 이관합니다.
"""
from typing import Callable, Dict, List, Optional, Tuple
import re
import logging

logger = logging.getLogger("jarvis.command_dispatcher")


class CommandDispatcher:
    """키워드 기반 명령 디스패처. 키워드 → 핸들러 매핑."""

    def __init__(self):
        self._handlers: List[Tuple[List[str], Callable]] = []  # [(keywords, handler), ...]

    def register(self, keywords: List[str]):
        """데코레이터: 키워드 리스트로 핸들러 등록"""
        def decorator(func: Callable):
            self._handlers.append((keywords, func))
            return func
        return decorator

    async def dispatch(self, prompt: str, **kwargs) -> Optional[str]:
        """프롬프트에서 키워드 매칭 후 핸들러 실행. 매칭 없으면 None 반환."""
        p = prompt.lower().strip()
        for keywords, handler in self._handlers:
            if any(kw in p for kw in keywords):
                try:
                    result = await handler(prompt=prompt, **kwargs)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.error(f"CommandDispatcher handler error: {e}")
        return None  # fallback to legacy


# Singleton instance
dispatcher = CommandDispatcher()
