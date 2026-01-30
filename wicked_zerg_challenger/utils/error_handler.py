# -*- coding: utf-8 -*-
"""
Error Handler - 예외 처리 유틸리티

기능:
1. 구체적인 예외 처리
2. 에러 로깅 및 추적
3. 재시도 로직
"""

import functools
import traceback
from typing import Callable, Any, Optional
from utils.logger import get_logger

logger = get_logger("ErrorHandler")


class SC2BotError(Exception):
    """Base exception for SC2 bot errors"""
    pass


class UnitCommandError(SC2BotError):
    """Exception for unit command failures"""
    pass


class UpgradeError(SC2BotError):
    """Exception for upgrade-related errors"""
    pass


class BuildingError(SC2BotError):
    """Exception for building-related errors"""
    pass


class ResourceError(SC2BotError):
    """Exception for resource-related errors"""
    pass


def safe_execute(default_return=None, log_errors=True):
    """
    안전한 실행 데코레이터

    예외 발생 시 기본값 반환하고 로그 기록

    Args:
        default_return: 에러 발생 시 반환할 기본값
        log_errors: 에러를 로그에 기록할지 여부

    Example:
        @safe_execute(default_return=None)
        def my_function():
            # ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                if log_errors:
                    logger.warning(f"{func.__name__} failed: {type(e).__name__}: {e}")
                return default_return
            except SC2BotError as e:
                if log_errors:
                    logger.error(f"{func.__name__} SC2BotError: {e}")
                return default_return
            except Exception as e:
                if log_errors:
                    logger.error(f"{func.__name__} unexpected error: {e}")
                    logger.debug(traceback.format_exc())
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                if log_errors:
                    logger.warning(f"{func.__name__} failed: {type(e).__name__}: {e}")
                return default_return
            except SC2BotError as e:
                if log_errors:
                    logger.error(f"{func.__name__} SC2BotError: {e}")
                return default_return
            except Exception as e:
                if log_errors:
                    logger.error(f"{func.__name__} unexpected error: {e}")
                    logger.debug(traceback.format_exc())
                return default_return

        # 비동기 함수인지 확인
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def retry_on_failure(max_retries=3, delay=0.1):
    """
    실패 시 재시도 데코레이터

    Args:
        max_retries: 최대 재시도 횟수
        delay: 재시도 간 대기 시간 (초)

    Example:
        @retry_on_failure(max_retries=3)
        def unstable_function():
            # ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            import asyncio
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (AttributeError, KeyError, IndexError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"{func.__name__} attempt {attempt + 1} failed: {e}, retrying...")
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(f"{func.__name__} failed after {max_retries} attempts: {e}")

            return None

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (AttributeError, KeyError, IndexError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"{func.__name__} attempt {attempt + 1} failed: {e}, retrying...")
                        time.sleep(delay)
                    else:
                        logger.warning(f"{func.__name__} failed after {max_retries} attempts: {e}")

            return None

        # 비동기 함수인지 확인
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def validate_unit(unit) -> bool:
    """
    유닛 유효성 검증

    Args:
        unit: SC2 Unit object

    Returns:
        유닛이 유효하면 True
    """
    if unit is None:
        return False

    try:
        # 필수 속성 확인
        _ = unit.tag
        _ = unit.position
        _ = unit.type_id
        return True
    except (AttributeError, TypeError):
        return False


def validate_position(position) -> bool:
    """
    위치 유효성 검증

    Args:
        position: Point2 or tuple

    Returns:
        위치가 유효하면 True
    """
    if position is None:
        return False

    try:
        # x, y 좌표 확인
        _ = position.x if hasattr(position, 'x') else position[0]
        _ = position.y if hasattr(position, 'y') else position[1]
        return True
    except (AttributeError, KeyError, IndexError, TypeError):
        return False


def log_error_context(func_name: str, error: Exception, context: dict = None):
    """
    에러와 함께 컨텍스트 정보 로깅

    Args:
        func_name: 함수 이름
        error: 발생한 예외
        context: 추가 컨텍스트 정보
    """
    error_msg = f"Error in {func_name}: {type(error).__name__}: {error}"

    if context:
        error_msg += f"\nContext: {context}"

    logger.error(error_msg)
    logger.debug(traceback.format_exc())


# Import asyncio for async detection
try:
    import asyncio
except ImportError:
    # Fallback: asyncio not available
    class asyncio:
        @staticmethod
        def iscoroutinefunction(func):
            return False
