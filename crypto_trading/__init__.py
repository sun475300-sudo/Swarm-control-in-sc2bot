"""
JARVIS Crypto Trading Module
- Upbit 시세 조회 / 자동 매매 브릿지
- 5중 보안 체계 적용
"""
import logging

logger = logging.getLogger("crypto")

# 모듈 임포트 시 보안 체계 자동 초기화
def _auto_init_security():
    try:
        from .security import install_log_filter
        install_log_filter()
    except Exception:
        pass

_auto_init_security()
