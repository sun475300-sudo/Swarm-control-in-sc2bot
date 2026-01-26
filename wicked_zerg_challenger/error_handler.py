# -*- coding: utf-8 -*-
"""
Error Handler - 개발/프로덕션 모드 분리

개발 모드:
- 예외 즉시 발생 (디버깅 용이)
- 상세한 스택 트레이스
- 에러 발생 시 즉시 크래시

프로덕션 모드:
- 예외를 포착하여 로그
- 게임 계속 진행
- 에러 카운트 추적

참고: LOGIC_IMPROVEMENT_REPORT.md - Section 5 (Code Quality)
"""

import functools
import traceback
from typing import Callable, Any, Optional
from collections import defaultdict


class ErrorHandler:
    """
    에러 처리 핸들러

    DEBUG_MODE에 따라 다른 에러 처리 전략 사용:
    - DEBUG_MODE=True: 즉시 크래시 (개발 모드)
    - DEBUG_MODE=False: 안전한 예외 처리 (프로덕션)
    """

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.error_counts = defaultdict(int)
        self.max_error_logs = 3  # 같은 에러는 최대 3회만 로그

    def safe_execute(
        self,
        func: Callable,
        *args,
        log_key: Optional[str] = None,
        default_return: Any = None,
        **kwargs
    ) -> Any:
        """
        안전한 함수 실행

        Args:
            func: 실행할 함수
            *args: 함수 인자
            log_key: 에러 로그 키 (None이면 함수명 사용)
            default_return: 에러 시 반환값
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과 또는 default_return
        """
        if log_key is None:
            log_key = func.__name__

        try:
            return func(*args, **kwargs)
        except Exception as e:
            if self.debug_mode:
                # 개발 모드: 즉시 크래시
                print(f"\n[ERROR] {log_key} failed in DEBUG_MODE - crashing for debugging")
                print(f"[ERROR] Exception: {e}")
                print(f"[ERROR] Traceback:")
                traceback.print_exc()
                raise  # 즉시 예외 발생
            else:
                # 프로덕션 모드: 로그 후 계속
                self.error_counts[log_key] += 1

                # 처음 3회만 로그 (스팸 방지)
                if self.error_counts[log_key] <= self.max_error_logs:
                    print(f"[ERROR] {log_key} failed: {e}")
                    if self.error_counts[log_key] == self.max_error_logs:
                        print(f"[ERROR] {log_key}: Suppressing further error logs for this key")

                return default_return

    def safe_coroutine(
        self,
        log_key: Optional[str] = None,
        default_return: Any = None
    ):
        """
        안전한 코루틴 데코레이터

        사용 예:
            @error_handler.safe_coroutine(log_key="EconomyManager")
            async def on_step(self, iteration):
                # 로직...
        """
        def decorator(coro_func: Callable):
            @functools.wraps(coro_func)
            async def wrapper(*args, **kwargs):
                key = log_key if log_key else coro_func.__name__

                try:
                    return await coro_func(*args, **kwargs)
                except Exception as e:
                    if self.debug_mode:
                        # 개발 모드: 즉시 크래시
                        print(f"\n[ERROR] {key} failed in DEBUG_MODE - crashing for debugging")
                        print(f"[ERROR] Exception: {e}")
                        print(f"[ERROR] Traceback:")
                        traceback.print_exc()
                        raise
                    else:
                        # 프로덕션 모드: 로그 후 계속
                        self.error_counts[key] += 1

                        if self.error_counts[key] <= self.max_error_logs:
                            print(f"[ERROR] {key} failed: {e}")
                            if self.error_counts[key] == self.max_error_logs:
                                print(f"[ERROR] {key}: Suppressing further error logs")

                        return default_return

            return wrapper
        return decorator

    def get_error_summary(self) -> dict:
        """에러 통계 반환"""
        return dict(self.error_counts)

    def reset_error_counts(self):
        """에러 카운트 초기화"""
        self.error_counts.clear()


# ========== 전역 인스턴스 ==========

# Config에서 DEBUG_MODE 가져오기
try:
    from game_config import config
    DEBUG_MODE = config.DEBUG_MODE
except ImportError:
    import os
    DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

# 전역 에러 핸들러 인스턴스
error_handler = ErrorHandler(debug_mode=DEBUG_MODE)

print(f"[ERROR_HANDLER] Initialized with DEBUG_MODE={DEBUG_MODE}")


# ========== 편의 함수 ==========

def safe_execute(func: Callable, *args, log_key: Optional[str] = None, **kwargs) -> Any:
    """전역 에러 핸들러의 safe_execute 단축 함수"""
    return error_handler.safe_execute(func, *args, log_key=log_key, **kwargs)


def safe_coroutine(log_key: Optional[str] = None, default_return: Any = None):
    """전역 에러 핸들러의 safe_coroutine 단축 데코레이터"""
    return error_handler.safe_coroutine(log_key=log_key, default_return=default_return)
