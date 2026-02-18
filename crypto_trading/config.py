"""
Crypto Trading Configuration
- 환경변수에서 API 키 로드
- 거래 관련 기본 설정
"""
import os
from pathlib import Path
from dotenv import load_dotenv

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
DRY_RUN = False                         # False = 실제 매매 (Upbit API로 실주문)

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