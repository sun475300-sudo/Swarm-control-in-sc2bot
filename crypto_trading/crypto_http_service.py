"""
JARVIS Crypto HTTP Service (Port 8766)
- crypto_bridge.py가 연결하는 실제 백엔드 서비스
- 시세 조회, 잔고, 매매, 차트 생성 API 제공
- 차트 이미지를 base64로 반환하여 디스코드에서 바로 표시 가능
"""
import asyncio
import base64
import io
import json
import logging
import os
import sys
import uuid
from datetime import datetime

from aiohttp import web

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_trading.upbit_client import UpbitClient
from crypto_trading.auto_trader import AutoTrader
from crypto_trading.portfolio_tracker import PortfolioTracker
from crypto_trading.market_analyzer import MarketAnalyzer
from crypto_trading import config

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
        price = client.get_current_price(ticker)
        if price is None:
            return web.json_response({"error": f"시세 조회 실패: {ticker}"}, status=404)

        # 추가 정보
        df = client.get_ohlcv(ticker, interval="day", count=2)
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
    limit = int(request.query.get("limit", 20))
    tickers = client.get_tickers(fiat="KRW")[:limit]
    prices = client.get_prices(tickers)
    result = [{"ticker": t, "price": prices.get(t, 0)} for t in tickers]
    return web.json_response({"prices": result, "count": len(result)})


async def handle_top_movers(request):
    """GET /market/top-movers"""
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
    return web.json_response({
        "gainers": prices_data[:5],
        "losers": prices_data[-5:][::-1]
    })


# ── 잔고 ──

async def handle_balance(request):
    """GET /portfolio/balance"""
    try:
        balances = client.get_balances()
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

        prices = client.get_prices(tickers_for_price) if tickers_for_price else {}
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
        return web.json_response({"error": str(e), "traceback": traceback.format_exc()}, status=500)


async def handle_summary(request):
    """GET /portfolio/summary"""
    try:
        summary = tracker.get_summary()
        return web.json_response(summary)
    except Exception as e:
        import traceback
        logger.error(f"handle_summary error: {traceback.format_exc()}")
        return web.json_response({"error": str(e), "traceback": traceback.format_exc()}, status=500)


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
        if amount_krw < config.MIN_ORDER_AMOUNT:
            return web.json_response({"error": f"최소 주문 금액: {config.MIN_ORDER_AMOUNT}원"}, status=400)

        volume = amount_krw / current_price if current_price > 0 else 0
        result = client.buy_market_order(market, amount_krw)
        if result:
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
        coin = market.replace("KRW-", "")

        if percent > 0:
            total = client.get_balance(coin)
            volume = total * (percent / 100)

        if volume <= 0:
            return web.json_response({"error": "매도 수량 없음"}, status=400)

        result = client.sell_market_order(market, volume)
        if result:
            analysis = analyzer.analyze_coin(market)
            value_krw = volume * current_price

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
    result = trader.run_cycle()
    return web.json_response(result)


async def handle_trade_history(request):
    """GET /trade/history"""
    limit = int(request.query.get("limit", 10))
    trades = tracker.get_recent_trades(limit)
    return web.json_response({"trades": trades, "count": len(trades)})


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


# ═══════════════════════════════════════════════════
#  앱 설정 및 실행
# ═══════════════════════════════════════════════════

def create_app():
    app = web.Application()

    # Health
    app.router.add_get("/health", handle_health)

    # Market
    app.router.add_get("/market/price/{symbol}", handle_price)
    app.router.add_get("/market/prices", handle_prices)
    app.router.add_get("/market/top-movers", handle_top_movers)

    # Portfolio
    app.router.add_get("/portfolio/balance", handle_balance)
    app.router.add_get("/portfolio/summary", handle_summary)

    # Trade
    app.router.add_post("/trade/{side}", handle_trade)
    app.router.add_post("/trade/confirm/{trade_id}", handle_trade_confirm)
    app.router.add_get("/trade/history", handle_trade_history)

    # Auto Trading
    app.router.add_post("/auto/start", handle_auto_start)
    app.router.add_post("/auto/stop", handle_auto_stop)
    app.router.add_get("/auto/status", handle_auto_status)
    app.router.add_post("/auto/cycle", handle_auto_cycle)

    # Charts (JSON with base64)
    app.router.add_get("/chart/portfolio", handle_chart_portfolio)
    app.router.add_get("/chart/analysis", handle_chart_analysis)

    # Charts (Direct PNG)
    app.router.add_get("/chart/portfolio.png", handle_chart_portfolio_png)
    app.router.add_get("/chart/analysis.png", handle_chart_analysis_png)

    return app


if __name__ == "__main__":
    logger.info(f"Starting JARVIS Crypto HTTP Service on port {PORT}")
    logger.info(f"DRY_RUN: {config.DRY_RUN} | Watch: {config.DEFAULT_WATCH_LIST}")
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=PORT, print=None)
