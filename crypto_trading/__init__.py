"""
JARVIS Crypto Trading Module
- Upbit 시세 조회 / 자동 매매 브릿지
- 5중 보안 체계 적용
"""

import logging

logger = logging.getLogger("crypto")


# 모듈 임포트 시 보안 체계 자동 초기화
def _auto_init_security():
    # NOTE: catch BaseException, not Exception. cryptography's Rust
    # binding can raise pyo3_runtime.PanicException (a BaseException
    # subclass) when its native libs are broken in the host environment.
    # Without catching BaseException the whole crypto_trading package
    # fails to import, breaking unrelated tests.
    try:
        from .security import install_log_filter

        install_log_filter()
    except BaseException:
        pass


_auto_init_security()
