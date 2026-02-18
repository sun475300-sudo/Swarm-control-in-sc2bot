"""
JARVIS Crypto HTTP Service (Port 8766)
- crypto_bridge.py가 연결하는 실제 백엔드 서비스
- 시세 조회, 잔고, 매매, 차트 생성 API 제공
- 차트 이미지를 base64로 반환하여 디스코드에서 바로 표시 가능
"""
import asyncio
import base64
import gzip
import io
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta

import aiohttp
from aiohttp import web

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_trading.upbit_client import UpbitClient
from crypto_trading.auto_trader import AutoTrader
from crypto_trading.portfolio_tracker import PortfolioTracker
from crypto_trading.market_analyzer import MarketAnalyzer
from crypto_trading import config
from crypto_trading.security import trade_safety

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("crypto_http")

PORT = int(os.environ.get("CRYPTO_SERVICE_PORT", 8766))

# ── 전역 인스턴스 ──
client = UpbitClient()
trader = AutoTrader()
tracker = PortfolioTracker()
analyzer = MarketAnalyzer(client)

# 매매 대기열 (confirm 패턴용)
_pending_trades = {}

# ── Discord Webhook (#176-178) ──
DISCORD_WEBHOOK_URL = os.environ.get("CRYPTO_WEBHOOK_URL", "")


async def send_discord_notification(title: str, message: str, color: int = 0x2196F3):
    """Discord Webhook으로 알림 전송"""
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }]
        }
        async with aiohttp.ClientSession() as session:
            await session.post(DISCORD_WEBHOOK_URL, json=payload, timeout=aiohttp.ClientTimeout(total=5))
    except Exception as e:
        logger.warning(f"Discord 알림 실패: {e}")


# ═══════════════════════════════════════════════════
#  미들웨어 (#67-#69, #73-#74)
# ═══════════════════════════════════════════════════

# ── #67: CORS 미들웨어 ──

@web.middleware
async def cors_middleware(request, handler):
    """수동 CORS 미들웨어 - aiohttp_cors 없이 CORS 헤더를 직접 추가한다."""
    # Preflight (OPTIONS) 요청 처리
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response


# ── #68: 요청 로깅 미들웨어 ──

@web.middleware
async def request_logging_middleware(request, handler):
    """모든 요청의 method, path, status, 소요시간을 로깅한다."""
    start = time.monotonic()
    try:
        response = await handler(request)
        elapsed = (time.monotonic() - start) * 1000  # ms
        logger.info(
            f"{request.method} {request.path} -> {response.status} ({elapsed:.1f}ms)"
        )
        return response
    except web.HTTPException as exc:
        elapsed = (time.monotonic() - start) * 1000
        logger.warning(
            f"{request.method} {request.path} -> {exc.status} ({elapsed:.1f}ms)"
        )
        raise
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        logger.error(
            f"{request.method} {request.path} -> 500 ({elapsed:.1f}ms) {exc!r}"
        )
        raise


# ── #69: 통합 에러 핸들러 미들웨어 ──

@web.middleware
async def error_handler_middleware(request, handler):
    """모든 예외를 JSON 응답으로 변환하는 통합 에러 핸들러."""
    try:
        return await handler(request)
    except web.HTTPException as exc:
        return web.json_response(
            {"error": exc.reason, "status": exc.status},
            status=exc.status,
        )
    except Exception as exc:
        logger.exception(f"Unhandled error on {request.method} {request.path}")
        return web.json_response(
            {"error": str(exc), "status": 500},
            status=500,
        )


# ── #73: Gzip 압축 미들웨어 ──

@web.middleware
async def gzip_middleware(request, handler):
    """응답 크기가 1KB 이상이고 클라이언트가 gzip을 지원하면 압축한다."""
    response = await handler(request)

    # StreamResponse(SSE 등)는 압축하지 않는다
    if not isinstance(response, web.Response):
        return response

    accept_encoding = request.headers.get("Accept-Encoding", "")
    if "gzip" not in accept_encoding:
        return response

    body = response.body
    if body is None:
        return response

    if isinstance(body, bytes):
        raw = body
    else:
        raw = body.encode("utf-8") if isinstance(body, str) else bytes(body)

    if len(raw) < 1024:
        return response

    compressed = gzip.compress(raw)
    response.body = compressed
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = str(len(compressed))
    return response


# ── #74: 캐시 헤더 미들웨어 ──

# 캐시 가능 경로 패턴 -> max-age 초
_CACHE_RULES = {
    "/api-docs": 3600,           # API 문서: 1시간
    "/market/fear-greed": 300,   # 공포/탐욕: 5분
    "/market/summary": 120,      # 시장 요약: 2분
    "/chart/analysis": 60,       # 분석 차트: 1분
    "/settings/chart-theme": 86400,  # 테마 설정: 하루
}


@web.middleware
async def cache_header_middleware(request, handler):
    """자주 변하지 않는 응답에 Cache-Control 헤더를 추가한다."""
    response = await handler(request)

    for path_prefix, max_age in _CACHE_RULES.items():
        if request.path.startswith(path_prefix):
            response.headers["Cache-Control"] = f"public, max-age={max_age}"
            return response

    # 기본: 캐시하지 않음
    response.headers.setdefault("Cache-Control", "no-cache")
    return response


# ═══════════════════════════════════════════════════
#  거래 큐 (#76) 및 테마 설정 (#77) 전역 상태
# ═══════════════════════════════════════════════════

_trade_queue: asyncio.Queue = asyncio.Queue()
_trade_queue_results: dict = {}  # order_id -> result
_trade_queue_running: bool = False

_chart_theme: dict = {
    "mode": "dark",
    "bg_color": "#1a1a2e",
    "card_color": "#16213e",
    "text_color": "#e8e8e8",
    "accent_color": "#00d2ff",
}


# ═══════════════════════════════════════════════════
#  차트 생성 유틸리티
# ═══════════════════════════════════════════════════

def _fig_to_base64(fig) -> str:
    """matplotlib Figure → base64 PNG 문자열"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    return b64


def _fig_to_bytes(fig) -> bytes:
    """matplotlib Figure → PNG bytes"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    data = buf.read()
    buf.close()
    return data


def generate_trade_result_chart(trade_info: dict) -> str:
    """매매 결과를 시각적 차트로 생성"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    side = trade_info.get("side", "buy")
    ticker = trade_info.get("ticker", "KRW-BTC")
    coin = ticker.replace("KRW-", "")
    amount_krw = trade_info.get("amount_krw", 0)
    price = trade_info.get("price", 0)
    volume = trade_info.get("volume", 0)
    dry_run = trade_info.get("dry_run", True)
    timestamp = trade_info.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))
    score = trade_info.get("score", 0)
    reasons = trade_info.get("reasons", [])

    # 색상 테마
    bg_color = "#1a1a2e"
    card_color = "#16213e"
    buy_color = "#00d2ff"
    sell_color = "#ff6b6b"
    text_color = "#e8e8e8"
    accent = buy_color if side == "buy" else sell_color

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.2, 1]})
    fig.set_facecolor(bg_color)

    # ── 왼쪽: 매매 정보 카드 ──
    ax1 = axes[0]
    ax1.set_facecolor(card_color)
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis("off")

    # 헤더
    mode_tag = "[모의매매]" if dry_run else "[실전매매]"
    side_kr = "매수" if side == "buy" else "매도"
    ax1.text(5, 9.3, f"JARVIS {side_kr} 리포트", fontsize=20, fontweight="bold",
             color=accent, ha="center", va="center")
    ax1.text(5, 8.6, f"{mode_tag}  |  {timestamp}", fontsize=11,
             color="#888", ha="center", va="center")

    # 구분선
    ax1.plot([1, 9], [8.1, 8.1], color=accent, linewidth=2, alpha=0.5)

    # 매매 상세
    info_items = [
        ("코인", f"{coin} ({ticker})"),
        ("유형", f"시장가 {side_kr}"),
        ("금액", f"{amount_krw:,.0f} 원"),
    ]
    if price > 0:
        info_items.append(("단가", f"{price:,.0f} 원"))
    if volume > 0:
        info_items.append(("수량", f"{volume:.6f} {coin}"))

    y = 7.3
    for label, value in info_items:
        ax1.text(1.5, y, label, fontsize=13, color="#999", va="center")
        ax1.text(8.5, y, value, fontsize=13, color=text_color, ha="right", va="center",
                 fontweight="bold")
        y -= 0.9

    # 스코어 표시 (있으면)
    if score != 0:
        y -= 0.3
        score_color = "#4caf50" if score > 0 else "#f44336" if score < 0 else "#999"
        ax1.text(1.5, y, "AI 스코어", fontsize=13, color="#999", va="center")
        ax1.text(8.5, y, f"{score:+d} / 100", fontsize=15, color=score_color,
                 ha="right", va="center", fontweight="bold")

    # ── 오른쪽: 스코어 게이지 + 판단 근거 ──
    ax2 = axes[1]
    ax2.set_facecolor(card_color)
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis("off")

    ax2.text(5, 9.3, "AI 분석 근거", fontsize=16, fontweight="bold",
             color=text_color, ha="center", va="center")
    ax2.plot([1, 9], [8.7, 8.7], color="#444", linewidth=1)

    if reasons:
        y = 8.2
        for i, reason in enumerate(reasons[:8]):
            if "+" in reason:
                dot_color = "#4caf50"
            elif "-" in reason:
                dot_color = "#f44336"
            else:
                dot_color = "#888"
            ax2.text(1.2, y, "●", fontsize=8, color=dot_color, va="center")
            ax2.text(1.8, y, reason, fontsize=10, color=text_color, va="center")
            y -= 0.7
    else:
        ax2.text(5, 5, "분석 근거 없음", fontsize=12, color="#666",
                 ha="center", va="center")

    # 스코어 바 (하단)
    bar_y = 1.0
    ax2.plot([1, 9], [bar_y, bar_y], color="#333", linewidth=8, solid_capstyle="round")
    # 스코어에 따른 바 위치 (0~8 범위에 매핑, -100~+100)
    bar_pos = 5 + (score / 100) * 4  # 1~9 범위
    bar_color = "#4caf50" if score >= 30 else "#f44336" if score <= -30 else "#ff9800"
    ax2.plot([5, bar_pos], [bar_y, bar_y], color=bar_color, linewidth=8, solid_capstyle="round")
    ax2.text(bar_pos, bar_y + 0.5, f"{score:+d}", fontsize=12, fontweight="bold",
             color=bar_color, ha="center")
    ax2.text(1, bar_y - 0.5, "-100", fontsize=8, color="#666", ha="center")
    ax2.text(9, bar_y - 0.5, "+100", fontsize=8, color="#666", ha="center")
    ax2.text(5, bar_y - 0.5, "0", fontsize=8, color="#666", ha="center")

    plt.tight_layout(pad=1.5)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_portfolio_chart_image(balances: list, prices: dict) -> str:
    """포트폴리오 현황을 시각적 차트로 생성 (파이 + 바)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    bg_color = "#1a1a2e"
    card_color = "#16213e"
    text_color = "#e8e8e8"

    labels = []
    values = []
    pnl_list = []
    total_krw = 0

    for b in balances:
        currency = b.get("currency", "")
        balance = float(b.get("balance", 0)) + float(b.get("locked", 0))
        if balance <= 0:
            continue

        if currency == "KRW":
            labels.append("KRW")
            values.append(balance)
            pnl_list.append(0)
            total_krw += balance
        else:
            ticker = f"KRW-{currency}"
            price = prices.get(ticker, 0)
            value = balance * price
            avg_price = float(b.get("avg_buy_price", 0))
            pnl_pct = ((price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            labels.append(currency)
            values.append(value)
            pnl_list.append(pnl_pct)
            total_krw += value

    if not labels:
        return ""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.set_facecolor(bg_color)

    # ── 왼쪽: 파이차트 ──
    ax1.set_facecolor(card_color)
    colors = ["#00d2ff", "#4caf50", "#ff9800", "#f44336", "#9c27b0",
              "#00bcd4", "#ffeb3b", "#795548", "#607d8b", "#e91e63"]
    wedges, texts, autotexts = ax1.pie(
        values, labels=labels, autopct="%1.1f%%",
        colors=colors[:len(values)], startangle=90,
        textprops={"fontsize": 11, "color": text_color}
    )
    for at in autotexts:
        at.set_color(text_color)
    ax1.set_title(f"보유 비중  |  총 {total_krw:,.0f}원",
                  fontsize=14, fontweight="bold", color=text_color, pad=15)

    # ── 오른쪽: 수익률 바 차트 ──
    ax2.set_facecolor(card_color)
    non_krw = [(l, p) for l, p in zip(labels, pnl_list) if l != "KRW"]
    if non_krw:
        bar_labels, bar_pnl = zip(*non_krw)
        bar_colors = ["#4caf50" if p >= 0 else "#f44336" for p in bar_pnl]
        bars = ax2.barh(bar_labels, bar_pnl, color=bar_colors, height=0.5)
        ax2.axvline(x=0, color="#666", linewidth=0.8)
        ax2.set_xlabel("수익률 (%)", color=text_color, fontsize=11)
        ax2.tick_params(colors=text_color)
        for bar, pnl in zip(bars, bar_pnl):
            sign = "+" if pnl >= 0 else ""
            ax2.text(bar.get_width() + (0.5 if pnl >= 0 else -0.5), bar.get_y() + bar.get_height() / 2,
                     f"{sign}{pnl:.1f}%", va="center",
                     ha="left" if pnl >= 0 else "right",
                     color=text_color, fontsize=11, fontweight="bold")
    else:
        ax2.text(0.5, 0.5, "코인 보유 없음", transform=ax2.transAxes,
                 ha="center", va="center", color="#666", fontsize=14)
    ax2.set_title("종목별 수익률", fontsize=14, fontweight="bold", color=text_color, pad=15)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["bottom"].set_color("#444")
    ax2.spines["left"].set_color("#444")

    plt.tight_layout(pad=2)
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_analysis_chart(analyses: list) -> str:
    """시장 분석 결과를 차트로 생성"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    bg_color = "#1a1a2e"
    card_color = "#16213e"
    text_color = "#e8e8e8"

    if not analyses:
        return ""

    coins = [a.ticker.replace("KRW-", "") for a in analyses]
    scores = [a.score for a in analyses]
    rsi_vals = [a.rsi_14 for a in analyses]
    changes = [a.price_change_24h_pct for a in analyses]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
    fig.set_facecolor(bg_color)
    fig.suptitle("JARVIS 시장 종합 분석", fontsize=18, fontweight="bold",
                 color=text_color, y=0.98)

    # ── 종합 스코어 ──
    ax1.set_facecolor(card_color)
    colors = ["#4caf50" if s >= 30 else "#f44336" if s <= -30 else "#ff9800" for s in scores]
    bars = ax1.barh(coins, scores, color=colors, height=0.6)
    ax1.axvline(x=0, color="#666", linewidth=0.8)
    ax1.axvline(x=30, color="#4caf50", linewidth=0.5, linestyle="--", alpha=0.5)
    ax1.axvline(x=-30, color="#f44336", linewidth=0.5, linestyle="--", alpha=0.5)
    ax1.set_xlim(-100, 100)
    ax1.set_title("종합 스코어", fontsize=13, fontweight="bold", color=text_color)
    ax1.tick_params(colors=text_color)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["bottom"].set_color("#444")
    ax1.spines["left"].set_color("#444")
    for bar, s in zip(bars, scores):
        ax1.text(bar.get_width() + (2 if s >= 0 else -2), bar.get_y() + bar.get_height() / 2,
                 f"{s:+d}", va="center", ha="left" if s >= 0 else "right",
                 color=text_color, fontsize=10, fontweight="bold")

    # ── RSI ──
    ax2.set_facecolor(card_color)
    rsi_colors = ["#f44336" if r > 70 else "#4caf50" if r < 30 else "#ff9800" for r in rsi_vals]
    ax2.barh(coins, rsi_vals, color=rsi_colors, height=0.6)
    ax2.axvline(x=30, color="#4caf50", linewidth=1, linestyle="--", alpha=0.7)
    ax2.axvline(x=70, color="#f44336", linewidth=1, linestyle="--", alpha=0.7)
    ax2.axvline(x=50, color="#666", linewidth=0.5)
    ax2.set_xlim(0, 100)
    ax2.set_title("RSI (14)", fontsize=13, fontweight="bold", color=text_color)
    ax2.tick_params(colors=text_color)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["bottom"].set_color("#444")
    ax2.spines["left"].set_color("#444")

    # ── 24h 변동률 ──
    ax3.set_facecolor(card_color)
    change_colors = ["#4caf50" if c >= 0 else "#f44336" for c in changes]
    ax3.barh(coins, changes, color=change_colors, height=0.6)
    ax3.axvline(x=0, color="#666", linewidth=0.8)
    ax3.set_title("24h 변동률 (%)", fontsize=13, fontweight="bold", color=text_color)
    ax3.tick_params(colors=text_color)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    ax3.spines["bottom"].set_color("#444")
    ax3.spines["left"].set_color("#444")
    for i, c in enumerate(changes):
        sign = "+" if c >= 0 else ""
        ax3.text(c + (0.2 if c >= 0 else -0.2), i,
                 f"{sign}{c:.1f}%", va="center",
                 ha="left" if c >= 0 else "right",
                 color=text_color, fontsize=10)

    plt.tight_layout(pad=2, rect=[0, 0, 1, 0.95])
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


# ═══════════════════════════════════════════════════
#  HTTP 핸들러
# ═══════════════════════════════════════════════════

async def handle_health(request):
    return web.json_response({"status": "ok", "service": "jarvis-crypto", "port": PORT})


# ── 시세 ──

async def handle_price(request):
    """GET /market/price/<symbol>"""
    symbol = request.match_info.get("symbol", "BTC").upper()
    ticker = f"KRW-{symbol}" if not symbol.startswith("KRW-") else symbol
    try:
        price = await asyncio.to_thread(client.get_current_price, ticker)
        if price is None:
            return web.json_response({"error": f"시세 조회 실패: {ticker}"}, status=404)

        # 추가 정보
        df = await asyncio.to_thread(client.get_ohlcv, ticker, "day", 2)
        data = {"ticker": ticker, "trade_price": price}
        if df is not None and len(df) >= 2:
            prev = float(df["close"].iloc[-2])
            data["high_price"] = float(df["high"].iloc[-1])
            data["low_price"] = float(df["low"].iloc[-1])
            data["signed_change_rate"] = (price - prev) / prev if prev > 0 else 0
            data["acc_trade_volume_24h"] = float(df["volume"].iloc[-1])
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_prices(request):
    """GET /market/prices"""
    limit = min(int(request.query.get("limit", 20)), 100)
    tickers = await asyncio.to_thread(client.get_tickers, "KRW")
    tickers = tickers[:limit]
    prices = await asyncio.to_thread(client.get_prices, tickers)
    result = [{"ticker": t, "price": prices.get(t, 0)} for t in tickers]
    return web.json_response({"prices": result, "count": len(result)})


async def handle_top_movers(request):
    """GET /market/top-movers"""
    def _fetch_top_movers():
        tickers = client.get_tickers(fiat="KRW")
        prices_data = []
        for t in tickers[:30]:
            df = client.get_ohlcv(t, interval="day", count=2)
            if df is not None and len(df) >= 2:
                prev = float(df["close"].iloc[-2])
                cur = float(df["close"].iloc[-1])
                chg = ((cur - prev) / prev * 100) if prev > 0 else 0
                prices_data.append({"ticker": t, "price": cur, "change_pct": round(chg, 2)})
        prices_data.sort(key=lambda x: x["change_pct"], reverse=True)
        return prices_data

    prices_data = await asyncio.to_thread(_fetch_top_movers)
    return web.json_response({
        "gainers": prices_data[:5],
        "losers": prices_data[-5:][::-1]
    })


# ── 잔고 ──

async def handle_balance(request):
    """GET /portfolio/balance"""
    try:
        balances = await asyncio.to_thread(client.get_balances)
        if not balances:
            has_keys = bool(config.UPBIT_ACCESS_KEY and config.UPBIT_SECRET_KEY)
            if not has_keys:
                return web.json_response({"error": "API 키 미설정. .env 파일을 확인하세요."}, status=500)
            return web.json_response({"error": "잔고 조회 실패. API 키가 유효한지 확인하세요."}, status=500)

        assets = []
        total_krw = 0
        tickers_for_price = []
        coin_data = []

        for b in balances:
            currency = b.get("currency", "")
            # string 혹은 float 어떤 형태든 대응 가능하도록 변경
            try:
                balance = float(b.get("balance", 0)) + float(b.get("locked", 0))
            except (ValueError, TypeError):
                balance = 0

            if balance <= 0:
                continue
            if currency == "KRW":
                total_krw += balance
                assets.append({"currency": "KRW", "balance": balance, "value_krw": balance})
            else:
                tickers_for_price.append(f"KRW-{currency}")
                try:
                    avg_pay_price = float(b.get("avg_buy_price") or b.get("avg_buy_price_unit") or 0)
                except (ValueError, TypeError):
                    avg_pay_price = 0
                coin_data.append((currency, balance, avg_pay_price))

        prices = (await asyncio.to_thread(client.get_prices, tickers_for_price)) if tickers_for_price else {}
        for currency, balance, avg_price in coin_data:
            ticker = f"KRW-{currency}"
            price = prices.get(ticker, 0)
            value = balance * price
            total_krw += value
            pnl_pct = ((price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            assets.append({
                "currency": currency,
                "balance": balance,
                "price": price,
                "avg_price": avg_price,
                "value_krw": value,
                "pnl_pct": round(pnl_pct, 2),
            })

        return web.json_response({"total_krw": total_krw, "assets": assets})
    except Exception as e:
        import traceback
        logger.error(f"handle_balance error: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_summary(request):
    """GET /portfolio/summary"""
    try:
        summary = tracker.get_summary()
        return web.json_response(summary)
    except Exception as e:
        import traceback
        logger.error(f"handle_summary error: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)


# ── 매매 ──

async def handle_trade(request):
    """POST /trade/buy or /trade/sell"""
    side = request.match_info.get("side", "")
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    market = data.get("market", "").upper()
    if not market.startswith("KRW-"):
        market = f"KRW-{market}"

    trade_id = str(uuid.uuid4())[:8]
    current_price = client.get_current_price(market) or 0

    if side == "buy":
        amount_krw = float(data.get("amount_krw", 0))
        if amount_krw <= 0:
            return web.json_response({"error": "주문 금액은 0보다 커야 합니다."}, status=400)
        if amount_krw < config.MIN_ORDER_AMOUNT:
            return web.json_response({"error": f"최소 주문 금액: {config.MIN_ORDER_AMOUNT}원"}, status=400)

        safe, safe_msg = trade_safety.check_trade(amount_krw)
        if not safe:
            return web.json_response({"error": f"안전 가드 차단: {safe_msg}"}, status=403)

        volume = amount_krw / current_price if current_price > 0 else 0
        result = client.buy_market_order(market, amount_krw)
        if result:
            trade_safety.record_trade(amount_krw)
            # 분석 결과 가져오기
            analysis = analyzer.analyze_coin(market)

            trade_info = {
                "side": "buy", "ticker": market,
                "amount_krw": amount_krw, "price": current_price,
                "volume": volume, "dry_run": config.DRY_RUN,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "score": analysis.score,
                "reasons": analysis.reasons,
            }
            tracker.log_trade("buy", market, amount_krw, current_price, "디스코드 매수", result)

            # Discord 알림 (#176)
            await send_discord_notification("매수 완료", f"{market} {amount_krw:,.0f}원", 0x4CAF50)

            # 차트 생성
            chart_b64 = generate_trade_result_chart(trade_info)

            return web.json_response({
                "trade_id": trade_id, "market": market, "side": "buy",
                "amount_krw": amount_krw, "price": current_price,
                "volume": volume, "dry_run": config.DRY_RUN,
                "score": analysis.score,
                "recommendation": analysis.recommendation,
                "reasons": analysis.reasons[:5],
                "chart_base64": chart_b64,
            })
        return web.json_response({"error": "매수 실패"}, status=500)

    elif side == "sell":
        volume = float(data.get("volume", 0))
        percent = float(data.get("percent", 0))
        percent = max(0, min(100, percent))
        coin = market.replace("KRW-", "")

        if percent > 0:
            total = client.get_balance(coin)
            volume = total * (percent / 100)

        if volume <= 0:
            return web.json_response({"error": "매도 수량 없음"}, status=400)

        value_krw = volume * current_price
        safe, safe_msg = trade_safety.check_trade(value_krw)
        if not safe:
            return web.json_response({"error": f"안전 가드 차단: {safe_msg}"}, status=403)

        result = client.sell_market_order(market, volume)
        if result:
            trade_safety.record_trade(value_krw)
            analysis = analyzer.analyze_coin(market)

            trade_info = {
                "side": "sell", "ticker": market,
                "amount_krw": value_krw, "price": current_price,
                "volume": volume, "dry_run": config.DRY_RUN,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "score": analysis.score,
                "reasons": analysis.reasons,
            }
            tracker.log_trade("sell", market, value_krw, current_price, "디스코드 매도", result)

            chart_b64 = generate_trade_result_chart(trade_info)

            return web.json_response({
                "trade_id": trade_id, "market": market, "side": "sell",
                "volume": volume, "price": current_price,
                "value_krw": value_krw, "dry_run": config.DRY_RUN,
                "score": analysis.score,
                "reasons": analysis.reasons[:5],
                "chart_base64": chart_b64,
            })
        return web.json_response({"error": "매도 실패"}, status=500)

    return web.json_response({"error": f"Unknown side: {side}"}, status=400)


async def handle_trade_confirm(request):
    """POST /trade/confirm/<trade_id>"""
    trade_id = request.match_info.get("trade_id", "")
    return web.json_response({"confirmed": True, "trade_id": trade_id})


# ── 자동매매 ──

async def handle_auto_start(request):
    """POST /auto/start - 자동매매 시작"""
    try:
        data = await request.json() if request.content_length else {}
    except Exception:
        data = {}

    # 옵션 설정
    if "smart_mode" in data:
        trader.smart_mode = bool(data["smart_mode"])
    if "buy_threshold" in data:
        trader.buy_threshold = int(data["buy_threshold"])
    if "sell_threshold" in data:
        trader.sell_threshold = int(data["sell_threshold"])
    if "interval" in data:
        trader.interval = int(data["interval"])
    if "watch_list" in data:
        trader.set_watch_list(data["watch_list"])

    msg = trader.start()
    st = trader.get_status()
    return web.json_response({
        "message": msg,
        "status": "started" if trader.is_running else "error",
        "dry_run": st["dry_run"],
        "config": st,
    })


async def handle_auto_stop(request):
    """POST /auto/stop - 자동매매 중지"""
    msg = trader.stop()
    st = trader.get_status()
    return web.json_response({
        "message": msg,
        "status": "stopped",
        "dry_run": st["dry_run"],
        "config": st,
    })


async def handle_auto_status(request):
    """GET /auto/status - 자동매매 상태 조회"""
    st = trader.get_status()
    return web.json_response({
        "is_running": st["is_running"],
        "dry_run": st["dry_run"],
        "cycle_count": st["cycle_count"],
        "last_cycle": st["last_cycle"],
        "last_actions": st["last_actions"],
        "last_analysis": st["last_analysis"],
        "recent_trades": st["recent_trades"],
        "config": st
    })


async def handle_auto_cycle(request):
    """POST /auto/cycle - 수동으로 1회 사이클 실행"""
    result = await asyncio.to_thread(trader.run_cycle)
    return web.json_response(result)


async def handle_trade_history(request):
    """GET /trade/history"""
    limit = int(request.query.get("limit", 10))
    trades = tracker.get_recent_trades(limit)
    return web.json_response({"trades": trades, "count": len(trades)})


# ── 새 엔드포인트 (#29-#42) ──

async def handle_kimchi_premium(request):
    """GET /market/premium/<symbol> - 김치 프리미엄"""
    symbol = request.match_info.get("symbol", "BTC").upper()
    ticker = f"KRW-{symbol}" if not symbol.startswith("KRW-") else symbol
    try:
        result = await asyncio.to_thread(analyzer.get_kimchi_premium, ticker)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_fear_greed(request):
    """GET /market/fear-greed - 공포/탐욕 지수"""
    try:
        result = analyzer.get_fear_greed_index()
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_market_summary(request):
    """GET /market/summary - 시장 전체 요약"""
    try:
        result = await asyncio.to_thread(analyzer.get_market_summary)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_spread_analysis(request):
    """GET /market/spread/<symbol> - 스프레드 분석"""
    symbol = request.match_info.get("symbol", "BTC").upper()
    ticker = f"KRW-{symbol}" if not symbol.startswith("KRW-") else symbol
    try:
        result = await asyncio.to_thread(analyzer.analyze_spread, ticker)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_trade_statistics(request):
    """GET /portfolio/statistics?period=all - 거래 통계"""
    period = request.query.get("period", "all")
    try:
        result = tracker.get_trade_statistics(period)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_export_csv(request):
    """GET /portfolio/export-csv - 거래 내역 CSV 다운로드"""
    try:
        filepath = tracker.export_trades_csv()
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()
        return web.Response(
            body=content.encode("utf-8-sig"),
            content_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=trades.csv"}
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_set_alert(request):
    """POST /alert/set - 가격 알림 설정"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ticker = data.get("ticker", "").upper()
    above = data.get("above")
    below = data.get("below")
    if above is not None:
        above = float(above)
    if below is not None:
        below = float(below)
    result = trader.set_price_alert(ticker, above=above, below=below)
    return web.json_response(result)


async def handle_list_alerts(request):
    """GET /alert/list - 활성 알림 목록"""
    alerts = trader.get_price_alerts()
    return web.json_response({"alerts": alerts, "count": len(alerts)})


async def handle_dca(request):
    """POST /auto/dca - DCA 시작"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ticker = data.get("ticker", "")
    total_amount = float(data.get("total_amount", 0))
    num_splits = int(data.get("num_splits", 1))
    interval_minutes = int(data.get("interval_minutes", 60))
    result = trader.start_dca(ticker, total_amount, num_splits, interval_minutes)
    return web.json_response(result)


async def handle_trailing_stop(request):
    """POST /auto/trailing-stop - 트레일링 스탑 설정"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ticker = data.get("ticker", "")
    trail_pct = float(data.get("trail_pct", 5.0))
    result = await asyncio.to_thread(trader.set_trailing_stop, ticker, trail_pct)
    return web.json_response(result)


# ── 차트 전용 엔드포인트 ──

async def handle_chart_portfolio(request):
    """GET /chart/portfolio - 포트폴리오 차트 이미지 생성"""
    balances = client.get_balances()
    if not balances:
        return web.json_response({"error": "잔고 조회 실패"}, status=500)

    tickers = [f"KRW-{b['currency']}" for b in balances
               if b.get("currency") != "KRW" and float(b.get("balance", 0)) > 0]
    prices = client.get_prices(tickers) if tickers else {}

    chart_b64 = generate_portfolio_chart_image(balances, prices)
    if not chart_b64:
        return web.json_response({"error": "차트 생성 실패"}, status=500)

    # base64로 반환 (Discord bot에서 Buffer로 변환하여 전송)
    return web.json_response({"chart_base64": chart_b64, "type": "portfolio"})


async def handle_chart_portfolio_png(request):
    """GET /chart/portfolio.png - 포트폴리오 차트 PNG 이미지 직접 반환"""
    balances = client.get_balances()
    if not balances:
        return web.Response(text="잔고 조회 실패", status=500)

    tickers = [f"KRW-{b['currency']}" for b in balances
               if b.get("currency") != "KRW" and float(b.get("balance", 0)) > 0]
    prices = client.get_prices(tickers) if tickers else {}

    chart_b64 = generate_portfolio_chart_image(balances, prices)
    if not chart_b64:
        return web.Response(text="차트 생성 실패", status=500)

    img_bytes = base64.b64decode(chart_b64)
    return web.Response(body=img_bytes, content_type="image/png")


async def handle_chart_analysis(request):
    """GET /chart/analysis - 시장 분석 차트 생성"""
    tickers_param = request.query.get("tickers", "")
    if tickers_param:
        ticker_list = [t.strip().upper() for t in tickers_param.split(",")]
    else:
        ticker_list = config.DEFAULT_WATCH_LIST

    analyses = analyzer.analyze_watchlist(ticker_list)
    chart_b64 = generate_analysis_chart(analyses)

    # 텍스트 요약도 함께
    summary = []
    for a in analyses:
        coin = a.ticker.replace("KRW-", "")
        rec_kr = {"STRONG_BUY": "강력매수", "BUY": "매수", "HOLD": "관망",
                  "SELL": "매도", "STRONG_SELL": "강력매도"}.get(a.recommendation, "관망")
        summary.append({
            "coin": coin, "ticker": a.ticker,
            "score": a.score, "recommendation": rec_kr,
            "rsi": a.rsi_14, "change_24h": a.price_change_24h_pct,
            "price": a.current_price,
        })

    return web.json_response({
        "chart_base64": chart_b64,
        "type": "analysis",
        "summary": summary,
    })


async def handle_chart_analysis_png(request):
    """GET /chart/analysis.png - 분석 차트 PNG 직접 반환"""
    tickers_param = request.query.get("tickers", "")
    if tickers_param:
        ticker_list = [t.strip().upper() for t in tickers_param.split(",")]
    else:
        ticker_list = config.DEFAULT_WATCH_LIST

    analyses = analyzer.analyze_watchlist(ticker_list)
    chart_b64 = generate_analysis_chart(analyses)
    if not chart_b64:
        return web.Response(text="차트 생성 실패", status=500)

    img_bytes = base64.b64decode(chart_b64)
    return web.Response(body=img_bytes, content_type="image/png")


# ── 동적 로그 레벨 변경 (#163) ──

# 유효한 로그 레벨 목록
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


async def handle_get_log_level(request):
    """GET /admin/log-level - 현재 로그 레벨 반환"""
    current_level = logging.getLogger().getEffectiveLevel()
    level_name = logging.getLevelName(current_level)
    return web.json_response({
        "level": level_name,
        "available_levels": sorted(VALID_LOG_LEVELS),
    })


async def handle_set_log_level(request):
    """PUT /admin/log-level - 런타임에 로그 레벨 변경

    요청 본문: {"level": "DEBUG"}
    지원 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "유효하지 않은 JSON"}, status=400)

    level = data.get("level", "").upper()
    if level not in VALID_LOG_LEVELS:
        return web.json_response({
            "error": f"유효하지 않은 로그 레벨: {level}",
            "available_levels": sorted(VALID_LOG_LEVELS),
        }, status=400)

    previous_level = logging.getLevelName(logging.getLogger().getEffectiveLevel())
    logging.getLogger().setLevel(getattr(logging, level))
    # 하위 로거들도 동기화
    for name in logging.Logger.manager.loggerDict:
        child_logger = logging.getLogger(name)
        child_logger.setLevel(getattr(logging, level))

    logger.info(f"로그 레벨 변경: {previous_level} -> {level}")
    return web.json_response({
        "message": f"로그 레벨이 {level}(으)로 변경되었습니다.",
        "previous_level": previous_level,
        "current_level": level,
    })


# ═══════════════════════════════════════════════════
#  새 엔드포인트 (#67-#78)
# ═══════════════════════════════════════════════════

# ── #70: 캔들 차트 엔드포인트 ──

async def handle_candle_chart(request):
    """GET /chart/candle/{symbol}?count=100 - pyupbit OHLCV 캔들 데이터를 반환한다."""
    symbol = request.match_info.get("symbol", "BTC").upper()
    ticker = f"KRW-{symbol}" if not symbol.startswith("KRW-") else symbol
    count = min(int(request.query.get("count", 100)), 500)
    interval = request.query.get("interval", "day")  # day, minute1, minute5 등

    try:
        df = await asyncio.to_thread(client.get_ohlcv, ticker, interval, count)
        if df is None or len(df) == 0:
            return web.json_response(
                {"error": f"OHLCV 데이터 없음: {ticker}"}, status=404
            )

        candles = []
        for idx, row in df.iterrows():
            candles.append({
                "timestamp": str(idx),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })

        return web.json_response({
            "ticker": ticker,
            "interval": interval,
            "count": len(candles),
            "candles": candles,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ── #71: RSI 차트 데이터 ──

async def handle_rsi_chart(request):
    """GET /chart/rsi/{symbol}?period=14 - RSI 값 시계열을 반환한다."""
    symbol = request.match_info.get("symbol", "BTC").upper()
    ticker = f"KRW-{symbol}" if not symbol.startswith("KRW-") else symbol
    period = int(request.query.get("period", 14))
    count = min(int(request.query.get("count", 200)), 500)

    try:
        df = await asyncio.to_thread(client.get_ohlcv, ticker, "day", count)
        if df is None or len(df) < period + 1:
            return web.json_response(
                {"error": f"RSI 계산에 충분한 데이터 없음 (최소 {period + 1}개 필요)"},
                status=404,
            )

        # RSI 계산
        close = df["close"]
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        rsi = 100 - (100 / (1 + rs))

        rsi_data = []
        for idx, val in rsi.dropna().items():
            rsi_data.append({
                "timestamp": str(idx),
                "rsi": round(float(val), 2),
                "close": float(close.loc[idx]),
            })

        current_rsi = rsi_data[-1]["rsi"] if rsi_data else None
        signal = "과매수" if current_rsi and current_rsi > 70 else \
                 "과매도" if current_rsi and current_rsi < 30 else "중립"

        return web.json_response({
            "ticker": ticker,
            "period": period,
            "current_rsi": current_rsi,
            "signal": signal,
            "count": len(rsi_data),
            "rsi_series": rsi_data,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ── #72: API 문서 엔드포인트 ──

async def handle_api_docs(request):
    """GET /api-docs - 모든 엔드포인트 목록과 설명을 JSON으로 반환한다."""
    docs = [
        {"method": "GET",  "path": "/health",                    "description": "서비스 헬스체크"},
        {"method": "GET",  "path": "/market/price/{symbol}",     "description": "개별 코인 현재가 조회"},
        {"method": "GET",  "path": "/market/prices",             "description": "전체 코인 시세 목록 (?limit=20)"},
        {"method": "GET",  "path": "/market/top-movers",         "description": "상승/하락 상위 5종목"},
        {"method": "GET",  "path": "/market/premium/{symbol}",   "description": "김치 프리미엄 조회"},
        {"method": "GET",  "path": "/market/fear-greed",         "description": "공포/탐욕 지수"},
        {"method": "GET",  "path": "/market/summary",            "description": "시장 전체 요약"},
        {"method": "GET",  "path": "/market/spread/{symbol}",    "description": "스프레드 분석"},
        {"method": "GET",  "path": "/portfolio/balance",         "description": "보유 자산 잔고 조회"},
        {"method": "GET",  "path": "/portfolio/summary",         "description": "포트폴리오 요약"},
        {"method": "GET",  "path": "/portfolio/statistics",      "description": "거래 통계 (?period=all)"},
        {"method": "GET",  "path": "/portfolio/export-csv",      "description": "거래 내역 CSV 다운로드"},
        {"method": "GET",  "path": "/portfolio/returns",         "description": "기간별 수익률 (?period=7d)"},
        {"method": "POST", "path": "/trade/{side}",              "description": "매수/매도 주문 (side=buy|sell)"},
        {"method": "POST", "path": "/trade/confirm/{trade_id}",  "description": "매매 확인"},
        {"method": "GET",  "path": "/trade/history",             "description": "거래 내역 (?limit=10)"},
        {"method": "POST", "path": "/trade/queue",               "description": "거래 큐에 주문 추가"},
        {"method": "POST", "path": "/auto/start",                "description": "자동매매 시작"},
        {"method": "POST", "path": "/auto/stop",                 "description": "자동매매 중지"},
        {"method": "GET",  "path": "/auto/status",               "description": "자동매매 상태 조회"},
        {"method": "POST", "path": "/auto/cycle",                "description": "자동매매 1회 수동 사이클"},
        {"method": "POST", "path": "/auto/dca",                  "description": "DCA(분할매수) 시작"},
        {"method": "POST", "path": "/auto/trailing-stop",        "description": "트레일링 스탑 설정"},
        {"method": "POST", "path": "/alert/set",                 "description": "가격 알림 설정"},
        {"method": "GET",  "path": "/alert/list",                "description": "활성 알림 목록"},
        {"method": "GET",  "path": "/chart/portfolio",           "description": "포트폴리오 차트 (base64 JSON)"},
        {"method": "GET",  "path": "/chart/portfolio.png",       "description": "포트폴리오 차트 PNG 이미지"},
        {"method": "GET",  "path": "/chart/analysis",            "description": "시장 분석 차트 (base64 JSON)"},
        {"method": "GET",  "path": "/chart/analysis.png",        "description": "시장 분석 차트 PNG 이미지"},
        {"method": "GET",  "path": "/chart/candle/{symbol}",     "description": "캔들 OHLCV 데이터 (?count=100&interval=day)"},
        {"method": "GET",  "path": "/chart/rsi/{symbol}",        "description": "RSI 시계열 데이터 (?period=14&count=200)"},
        {"method": "GET",  "path": "/stream/prices",             "description": "SSE 실시간 시세 스트림"},
        {"method": "GET",  "path": "/settings/chart-theme",      "description": "차트 테마 설정 조회"},
        {"method": "PUT",  "path": "/settings/chart-theme",      "description": "차트 테마 설정 변경"},
        {"method": "GET",  "path": "/api-docs",                  "description": "API 문서 (이 엔드포인트)"},
        {"method": "GET",  "path": "/admin/log-level",           "description": "로그 레벨 변경 (?level=INFO)"},
    ]
    return web.json_response({
        "service": "jarvis-crypto",
        "version": "2.0",
        "total_endpoints": len(docs),
        "endpoints": docs,
    })


# ── #75: SSE 실시간 가격 스트림 ──

async def handle_sse_prices(request):
    """GET /stream/prices - Server-Sent Events로 실시간 시세를 스트리밍한다.

    쿼리 파라미터:
        tickers: 쉼표 구분 종목 (기본값: DEFAULT_WATCH_LIST)
        interval: 전송 간격 초 (기본값: 3)
    """
    tickers_param = request.query.get("tickers", "")
    if tickers_param:
        ticker_list = [t.strip().upper() for t in tickers_param.split(",")]
        ticker_list = [
            f"KRW-{t}" if not t.startswith("KRW-") else t for t in ticker_list
        ]
    else:
        ticker_list = list(config.DEFAULT_WATCH_LIST)

    interval = max(1, min(int(request.query.get("interval", 3)), 30))

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
    await response.prepare(request)

    try:
        while True:
            prices = await asyncio.to_thread(client.get_prices, ticker_list)
            data = {
                "timestamp": datetime.now().isoformat(),
                "prices": {t: prices.get(t, 0) for t in ticker_list},
            }
            payload = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            await response.write(payload.encode("utf-8"))
            await asyncio.sleep(interval)
    except (asyncio.CancelledError, ConnectionResetError):
        pass

    return response


# ── #76: 거래 큐 ──

async def _trade_queue_worker():
    """거래 큐 워커 - 큐에서 주문을 꺼내 순차적으로 실행한다."""
    global _trade_queue_running
    _trade_queue_running = True
    logger.info("거래 큐 워커 시작")

    while True:
        try:
            order = await _trade_queue.get()
            order_id = order.get("order_id", "unknown")
            logger.info(f"거래 큐 처리 중: {order_id}")

            side = order.get("side", "buy")
            market = order.get("market", "")
            if not market.startswith("KRW-"):
                market = f"KRW-{market}"

            try:
                current_price = await asyncio.to_thread(
                    client.get_current_price, market
                )
                if current_price is None:
                    _trade_queue_results[order_id] = {
                        "order_id": order_id,
                        "status": "failed",
                        "error": f"시세 조회 실패: {market}",
                    }
                    continue

                if side == "buy":
                    amount_krw = float(order.get("amount_krw", 0))
                    result = await asyncio.to_thread(
                        client.buy_market_order, market, amount_krw
                    )
                else:
                    volume = float(order.get("volume", 0))
                    result = await asyncio.to_thread(
                        client.sell_market_order, market, volume
                    )

                _trade_queue_results[order_id] = {
                    "order_id": order_id,
                    "status": "completed" if result else "failed",
                    "market": market,
                    "side": side,
                    "price": current_price,
                    "result": result,
                    "completed_at": datetime.now().isoformat(),
                }
            except Exception as e:
                _trade_queue_results[order_id] = {
                    "order_id": order_id,
                    "status": "failed",
                    "error": str(e),
                }
            finally:
                _trade_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"거래 큐 워커 오류: {e}")


async def handle_trade_queue(request):
    """POST /trade/queue - 주문을 큐에 넣고 순차 실행한다.

    요청 본문:
        {"side": "buy", "market": "BTC", "amount_krw": 10000}
        {"side": "sell", "market": "BTC", "volume": 0.001}
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    side = data.get("side", "").lower()
    if side not in ("buy", "sell"):
        return web.json_response({"error": "side는 buy 또는 sell이어야 합니다."}, status=400)

    market = data.get("market", "").upper()
    if not market:
        return web.json_response({"error": "market 필수"}, status=400)

    order_id = str(uuid.uuid4())[:8]
    order = {
        "order_id": order_id,
        "side": side,
        "market": market,
        "amount_krw": data.get("amount_krw", 0),
        "volume": data.get("volume", 0),
        "queued_at": datetime.now().isoformat(),
    }

    await _trade_queue.put(order)
    queue_size = _trade_queue.qsize()

    return web.json_response({
        "order_id": order_id,
        "status": "queued",
        "position": queue_size,
        "message": f"주문이 큐에 등록되었습니다. (대기: {queue_size}건)",
    })


# ── #77: 차트 테마 설정 ──

async def handle_get_chart_theme(request):
    """GET /settings/chart-theme - 현재 차트 테마 설정을 반환한다."""
    return web.json_response({"theme": _chart_theme})


async def handle_put_chart_theme(request):
    """PUT /settings/chart-theme - 차트 테마 설정을 변경한다.

    요청 본문 예시:
        {"mode": "light", "bg_color": "#ffffff", "text_color": "#000000"}
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    valid_modes = {"dark", "light", "system"}
    if "mode" in data:
        mode = data["mode"].lower()
        if mode not in valid_modes:
            return web.json_response(
                {"error": f"mode는 {', '.join(valid_modes)} 중 하나여야 합니다."},
                status=400,
            )
        _chart_theme["mode"] = mode

    for key in ("bg_color", "card_color", "text_color", "accent_color"):
        if key in data:
            _chart_theme[key] = str(data[key])

    return web.json_response({
        "message": "테마 설정이 업데이트되었습니다.",
        "theme": _chart_theme,
    })


# ── #78: 기간별 수익률 ──

async def handle_portfolio_returns(request):
    """GET /portfolio/returns?period=7d - 일간/주간/월간/연간 수익률을 반환한다.

    지원 기간: 1d, 7d, 30d, 90d, 365d, all
    """
    period = request.query.get("period", "7d").lower()

    period_map = {
        "1d": 1,
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "365d": 365,
        "all": None,
    }

    days = period_map.get(period)
    if period not in period_map:
        return web.json_response(
            {"error": f"지원 기간: {', '.join(period_map.keys())}"}, status=400
        )

    try:
        # 현재 포트폴리오 평가액 계산
        balances = await asyncio.to_thread(client.get_balances)
        if not balances:
            return web.json_response({"error": "잔고 조회 실패"}, status=500)

        total_current = 0.0
        total_invested = 0.0
        coin_returns = []

        tickers_for_price = []
        coin_data_list = []

        for b in balances:
            currency = b.get("currency", "")
            try:
                balance = float(b.get("balance", 0)) + float(b.get("locked", 0))
            except (ValueError, TypeError):
                balance = 0
            if balance <= 0:
                continue

            if currency == "KRW":
                total_current += balance
                total_invested += balance
            else:
                tickers_for_price.append(f"KRW-{currency}")
                try:
                    avg_price = float(b.get("avg_buy_price", 0))
                except (ValueError, TypeError):
                    avg_price = 0
                coin_data_list.append((currency, balance, avg_price))

        prices = (
            await asyncio.to_thread(client.get_prices, tickers_for_price)
        ) if tickers_for_price else {}

        for currency, balance, avg_price in coin_data_list:
            ticker = f"KRW-{currency}"
            cur_price = prices.get(ticker, 0)
            cur_value = balance * cur_price
            invested_value = balance * avg_price
            total_current += cur_value
            total_invested += invested_value

            pnl_pct = (
                ((cur_price - avg_price) / avg_price * 100)
                if avg_price > 0
                else 0
            )

            # 기간 내 가격 변동 (OHLCV 기반)
            period_return = None
            if days is not None and cur_price > 0:
                try:
                    df = await asyncio.to_thread(
                        client.get_ohlcv, ticker, "day", days + 1
                    )
                    if df is not None and len(df) >= 2:
                        past_price = float(df["close"].iloc[0])
                        period_return = round(
                            (cur_price - past_price) / past_price * 100, 2
                        )
                except Exception:
                    period_return = None

            coin_returns.append({
                "currency": currency,
                "current_price": cur_price,
                "avg_buy_price": avg_price,
                "total_return_pct": round(pnl_pct, 2),
                "period_return_pct": period_return,
                "value_krw": round(cur_value, 0),
            })

        overall_return = (
            ((total_current - total_invested) / total_invested * 100)
            if total_invested > 0
            else 0
        )

        return web.json_response({
            "period": period,
            "days": days,
            "total_current_krw": round(total_current, 0),
            "total_invested_krw": round(total_invested, 0),
            "overall_return_pct": round(overall_return, 2),
            "coin_returns": coin_returns,
            "calculated_at": datetime.now().isoformat(),
        })
    except Exception as e:
        import traceback
        logger.error(f"handle_portfolio_returns error: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)


# ═══════════════════════════════════════════════════
#  앱 설정 및 실행
# ═══════════════════════════════════════════════════

def create_app():
    """aiohttp 앱을 생성하고 미들웨어와 라우트를 등록한다."""
    app = web.Application(
        middlewares=[
            cors_middleware,              # #67: CORS
            request_logging_middleware,   # #68: 요청 로깅
            error_handler_middleware,     # #69: 통합 에러 핸들러
            gzip_middleware,              # #73: Gzip 압축
            cache_header_middleware,      # #74: 캐시 헤더
        ]
    )

    # Health
    app.router.add_get("/health", handle_health)

    # Market
    app.router.add_get("/market/price/{symbol}", handle_price)
    app.router.add_get("/market/prices", handle_prices)
    app.router.add_get("/market/top-movers", handle_top_movers)

    # Portfolio
    app.router.add_get("/portfolio/balance", handle_balance)
    app.router.add_get("/portfolio/summary", handle_summary)
    app.router.add_get("/portfolio/returns", handle_portfolio_returns)   # #78

    # Trade
    app.router.add_post("/trade/{side}", handle_trade)
    app.router.add_post("/trade/confirm/{trade_id}", handle_trade_confirm)
    app.router.add_get("/trade/history", handle_trade_history)
    app.router.add_post("/trade/queue", handle_trade_queue)             # #76

    # Auto Trading
    app.router.add_post("/auto/start", handle_auto_start)
    app.router.add_post("/auto/stop", handle_auto_stop)
    app.router.add_get("/auto/status", handle_auto_status)
    app.router.add_post("/auto/cycle", handle_auto_cycle)

    # Charts (JSON with base64)
    app.router.add_get("/chart/portfolio", handle_chart_portfolio)
    app.router.add_get("/chart/analysis", handle_chart_analysis)
    app.router.add_get("/chart/candle/{symbol}", handle_candle_chart)    # #70
    app.router.add_get("/chart/rsi/{symbol}", handle_rsi_chart)          # #71

    # Charts (Direct PNG)
    app.router.add_get("/chart/portfolio.png", handle_chart_portfolio_png)
    app.router.add_get("/chart/analysis.png", handle_chart_analysis_png)

    # SSE 실시간 스트림 (#75)
    app.router.add_get("/stream/prices", handle_sse_prices)

    # Settings (#77)
    app.router.add_get("/settings/chart-theme", handle_get_chart_theme)
    app.router.add_put("/settings/chart-theme", handle_put_chart_theme)

    # API Docs (#72)
    app.router.add_get("/api-docs", handle_api_docs)

    # New endpoints (#29-#42)
    app.router.add_get("/market/premium/{symbol}", handle_kimchi_premium)
    app.router.add_get("/market/fear-greed", handle_fear_greed)
    app.router.add_get("/market/summary", handle_market_summary)
    app.router.add_get("/market/spread/{symbol}", handle_spread_analysis)
    app.router.add_get("/portfolio/statistics", handle_trade_statistics)
    app.router.add_get("/portfolio/export-csv", handle_export_csv)
    app.router.add_post("/alert/set", handle_set_alert)
    app.router.add_get("/alert/list", handle_list_alerts)
    app.router.add_post("/auto/dca", handle_dca)
    app.router.add_post("/auto/trailing-stop", handle_trailing_stop)

    # Admin (#163: 동적 로그 레벨 변경)
    app.router.add_get("/admin/log-level", handle_get_log_level)
    app.router.add_put("/admin/log-level", handle_set_log_level)

    # 거래 큐 워커 시작 (#76)
    async def start_trade_queue_worker(app):
        """앱 시작 시 거래 큐 워커를 백그라운드로 실행한다."""
        app["trade_queue_task"] = asyncio.create_task(_trade_queue_worker())

    async def stop_trade_queue_worker(app):
        """앱 종료 시 거래 큐 워커를 정리한다."""
        task = app.get("trade_queue_task")
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app.on_startup.append(start_trade_queue_worker)
    app.on_cleanup.append(stop_trade_queue_worker)

    return app


if __name__ == "__main__":
    logger.info(f"Starting JARVIS Crypto HTTP Service on port {PORT}")
    logger.info(f"DRY_RUN: {config.DRY_RUN} | Watch: {config.DEFAULT_WATCH_LIST}")
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=PORT, print=None)
