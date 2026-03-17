"""
Crypto Trading Configuration
- 환경변수에서 API 키 로드
- 거래 관련 기본 설정
"""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *a, **k: None

# .env 파일 로드 (프로젝트 내 여러 위치 탐색)
_env_paths = [
    Path(__file__).parent.parent / ".env.jarvis",
    Path(__file__).parent.parent / "wicked_zerg_challenger" / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent / ".env",
]
for p in _env_paths:
    if p.exists():
        load_dotenv(p)
        break

# ── Upbit API Keys ──
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "")

# ── 거래 설정 ──
DEFAULT_FIAT = "KRW"                    # 기본 마켓 (원화)
MIN_ORDER_AMOUNT = 5000                 # 최소 주문 금액 (KRW)
MAX_SINGLE_ORDER_RATIO = 0.1            # 1회 최대 주문 비율 (총 자산 대비 10%)
MAX_TOTAL_INVESTMENT_RATIO = 0.5        # 최대 투자 비율 (총 자산 대비 50%)
DEFAULT_STOP_LOSS_PCT = -5.0            # 기본 손절 (%)
DEFAULT_TAKE_PROFIT_PCT = 10.0          # 기본 익절 (%)

# ── 자동매매 설정 ──
AUTO_TRADE_INTERVAL = 60                # 자동매매 체크 간격 (초)
UPBIT_MIN_API_INTERVAL = 0.12           # Upbit API rate-limit 보호 간격 (초) (P3-4)
DRY_RUN = True                          # True = 모의매매 (안전 기본값)

# ── 포트폴리오 추적 ──
DATA_DIR = Path(__file__).parent / "data"
PORTFOLIO_HISTORY_FILE = DATA_DIR / "portfolio_history.json"
TRADE_LOG_FILE = DATA_DIR / "trade_log.json"
GRAPH_OUTPUT_DIR = DATA_DIR / "graphs"

REPORTS_DIR = DATA_DIR / "reports"

# 디렉토리 생성
DATA_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── 관심 코인 기본 목록 ──
DEFAULT_WATCH_LIST = [
    "KRW-BTC",     # 비트코인
    "KRW-ETH",     # 이더리움
    "KRW-XRP",     # 리플
    "KRW-SOL",     # 솔라나
    "KRW-DOGE",    # 도지코인
]

# ── 관심 코인 프리셋 (#34) ──
WATCHLIST_PRESETS = {
    "major": ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL"],
    "alt": ["KRW-ADA", "KRW-DOT", "KRW-AVAX", "KRW-MATIC", "KRW-LINK"],
    "defi": ["KRW-AAVE", "KRW-UNI", "KRW-COMP", "KRW-MKR"],
    "meme": ["KRW-DOGE", "KRW-SHIB"],
    "default": list(DEFAULT_WATCH_LIST),
}


# ── P2-19: 런타임 설정 검증 ──
def validate_config():
    """설정값 범위 검증 — import 시 자동 호출"""
    import logging as _log
    _logger = _log.getLogger("crypto.config")
    errors = []
    if MIN_ORDER_AMOUNT < 5000:
        errors.append(f"MIN_ORDER_AMOUNT({MIN_ORDER_AMOUNT}) < 5000")
    if not (0 < MAX_SINGLE_ORDER_RATIO <= 1):
        errors.append(f"MAX_SINGLE_ORDER_RATIO({MAX_SINGLE_ORDER_RATIO}) 범위 초과 (0~1)")
    if not (0 < MAX_TOTAL_INVESTMENT_RATIO <= 1):
        errors.append(f"MAX_TOTAL_INVESTMENT_RATIO({MAX_TOTAL_INVESTMENT_RATIO}) 범위 초과 (0~1)")
    if DEFAULT_STOP_LOSS_PCT >= 0:
        errors.append(f"DEFAULT_STOP_LOSS_PCT({DEFAULT_STOP_LOSS_PCT})는 음수여야 합니다")
    if DEFAULT_TAKE_PROFIT_PCT <= 0:
        errors.append(f"DEFAULT_TAKE_PROFIT_PCT({DEFAULT_TAKE_PROFIT_PCT})는 양수여야 합니다")
    if AUTO_TRADE_INTERVAL < 10:
        errors.append(f"AUTO_TRADE_INTERVAL({AUTO_TRADE_INTERVAL}) < 10초")
    if errors:
        for e in errors:
            _logger.warning(f"설정 검증 실패: {e}")
    return errors


validate_config()