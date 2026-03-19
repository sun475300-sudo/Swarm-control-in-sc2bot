"""
CommandDispatcher — 등록형 명령 핸들러 디스패처
_try_local_response()의 if-elif 체인을 점진적으로 이관합니다.
"""
from typing import Callable, List, Optional, Tuple, Union
import logging

logger = logging.getLogger("jarvis.command_dispatcher")


class CommandDispatcher:
    """키워드 기반 명령 디스패처. 키워드 → 핸들러 매핑.

    지원하는 등록 방식:
    1) keywords 리스트 (단순 키워드 매칭)
    2) match_fn 커스텀 함수 (복잡 조건)
    """

    def __init__(self):
        # (match_fn, handler) — match_fn(p: str) -> bool
        self._handlers: List[Tuple[Callable, Callable]] = []

    def register(
        self,
        keywords: Optional[List[str]] = None,
        *,
        match_fn: Optional[Callable] = None,
        max_len: Optional[int] = None,
        exclude: Optional[List[str]] = None,
    ):
        """데코레이터: 키워드 리스트 또는 커스텀 매치 함수로 핸들러 등록.

        Args:
            keywords: 단순 키워드 리스트 (any match)
            match_fn: 커스텀 매칭 함수 (p: str) -> bool
            max_len: 프롬프트 최대 길이 제한
            exclude: 이 키워드가 있으면 스킵
        """
        def decorator(func: Callable):
            if match_fn is not None:
                self._handlers.append((match_fn, func))
            elif keywords is not None:
                def _keyword_match(p: str) -> bool:
                    if max_len and len(p) > max_len:
                        return False
                    if exclude and any(kw in p for kw in exclude):
                        return False
                    return any(kw in p for kw in keywords)
                self._handlers.append((_keyword_match, func))
            else:
                raise ValueError("register() requires 'keywords' or 'match_fn'")
            return func
        return decorator

    @property
    def handler_count(self) -> int:
        return len(self._handlers)

    async def dispatch(self, prompt: str, **kwargs) -> Optional[str]:
        """프롬프트에서 키워드 매칭 후 핸들러 실행. 매칭 없으면 None 반환."""
        p = prompt.lower().strip()
        for match_fn, handler in self._handlers:
            if match_fn(p):
                try:
                    result = await handler(prompt=prompt, **kwargs)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.error(f"CommandDispatcher handler error [{handler.__name__}]: {e}")
        return None  # fallback to legacy


# Singleton instance
dispatcher = CommandDispatcher()
