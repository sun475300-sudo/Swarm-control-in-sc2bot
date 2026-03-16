"""
JARVIS Crypto Trading MCP Server
- 모든 기능을 자연어로 제어 가능한 MCP 도구로 노출
- 시세 조회, 잔고, 매수/매도, 자동매매, 포트폴리오 그래프 등
"""
import json
import logging
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

# Bug fix #24: Wrap all crypto_trading imports in try/except to avoid crash if missing
try:
    from crypto_trading.upbit_client import UpbitClient
except ImportError:
    UpbitClient = None
try:
    from crypto_trading.auto_trader import AutoTrader
except ImportError:
    AutoTrader = None
try:
    from crypto_trading.portfolio_tracker import PortfolioTracker
except ImportError:
    PortfolioTracker = None
try:
    from crypto_trading import config
except ImportError:
    config = None
try:
    from crypto_trading.strategies import AVAILABLE_STRATEGIES
except ImportError:
    AVAILABLE_STRATEGIES = {}
try:
    from crypto_trading.market_analyzer import MarketAnalyzer
except ImportError:
    MarketAnalyzer = None
try:
    from crypto_trading.utils import normalize_ticker
except ImportError:
    def normalize_ticker(t):
        t = t.upper().strip()
        return t if t.startswith("KRW-") else f"KRW-{t}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("crypto_mcp")

# ── 분석 쿨다운 관리 (스레드 안전) ──
import time as _time
import threading as _threading

_analysis_cooldowns: dict = {}  # tool_name -> last_call_timestamp
_cooldown_lock = _threading.Lock()
_COOLDOWN_MAX_ENTRIES = 100  # 메모리 누수 방지


def _check_cooldown(tool_name: str, seconds: int = 30) -> str | None:
    """도구 호출 쿨다운을 확인합니다. 쿨다운 중이면 메시지를 반환, 아니면 None."""
    now = _time.time()
    with _cooldown_lock:
        last = _analysis_cooldowns.get(tool_name, 0)
        if now - last < seconds:
            remaining = int(seconds - (now - last))
            return f"쿨다운 중 ({remaining}초 남음). 잠시 후 다시 시도해주세요."
        _analysis_cooldowns[tool_name] = now
        # 만료된 항목 정리 (메모리 누수 방지)
        if len(_analysis_cooldowns) > _COOLDOWN_MAX_ENTRIES:
            expired = [k for k, v in _analysis_cooldowns.items() if now - v > 3600]
            for k in expired:
                _analysis_cooldowns.pop(k, None)
    return None

# ── 5중 보안 체계 초기화 ──
try:
    from crypto_trading.security import initialize_security
    _security_report = initialize_security()
    logger.info("보안 초기화 완료")
except ImportError:
    initialize_security = None
    _security_report = None
    logger.warning("crypto_trading.security 모듈을 찾을 수 없습니다.")

# ── 전역 인스턴스 ──
mcp = FastMCP("JARVIS-Crypto-Trader")
client = UpbitClient() if UpbitClient else None
trader = AutoTrader() if AutoTrader else None
tracker = PortfolioTracker() if PortfolioTracker else None
analyzer = MarketAnalyzer(client) if (MarketAnalyzer and client) else None

_UNAVAILABLE_MSG = "crypto_trading 모듈이 초기화되지 않았습니다. 의존성을 확인하세요."


def _require_client() -> str | None:
    """client가 None이면 에러 메시지 반환, 아니면 None."""
    return _UNAVAILABLE_MSG if client is None else None


def _require_trader() -> str | None:
    return _UNAVAILABLE_MSG if trader is None else None


def _require_tracker() -> str | None:
    return _UNAVAILABLE_MSG if tracker is None else None


def _require_analyzer() -> str | None:
    return _UNAVAILABLE_MSG if analyzer is None else None


def _require_config() -> str | None:
    return "config 모듈이 로드되지 않았습니다." if config is None else None


# ═══════════════════════════════════════════════════
#  시세 조회
# ═══════════════════════════════════════════════════

@mcp.tool()
async def coin_price(ticker: str = "KRW-BTC") -> str:
    """코인 현재가를 조회합니다. 예: 'KRW-BTC', 'KRW-ETH', 'KRW-XRP'"""
    if err := _require_client():
        return err
    price = client.get_current_price(ticker)
    if price is None:
        return f"'{ticker}' 시세 조회 실패. 티커 형식: KRW-BTC"
    return f"{ticker} 현재가: {price:,.0f}원"


@mcp.tool()
async def coin_prices(tickers: str = "") -> str:
    """여러 코인의 현재가를 한번에 조회합니다. 쉼표로 구분. 비워두면 관심 목록 조회."""
    if err := _require_client():
        return err
    if tickers.strip():
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
    else:
        if err := _require_config():
            return err
        ticker_list = config.DEFAULT_WATCH_LIST

    prices = client.get_prices(ticker_list)
    if not prices:
        return "시세 조회 실패"

    lines = ["📊 코인 시세 현황:"]
    for t in ticker_list:
        p = prices.get(t, 0)
        coin = t.replace("KRW-", "")
        lines.append(f"  {coin}: {p:,.0f}원")
    return "\n".join(lines)


@mcp.tool()
async def coin_orderbook(ticker: str = "KRW-BTC") -> str:
    """코인 호가창(매수/매도 호가)을 조회합니다."""
    if err := _require_client():
        return err
    ob = client.get_orderbook(ticker)
    if not ob:
        return f"'{ticker}' 호가 조회 실패"

    # pyupbit returns a list; extract the first element
    if isinstance(ob, list):
        ob = ob[0] if ob else {}
    units = ob.get("orderbook_units", [])[:5]
    lines = [f"📋 {ticker} 호가 (상위 5개):"]
    lines.append("  [매도]                    [매수]")
    for u in reversed(units):
        ask = f"{u['ask_price']:>12,.0f} ({u['ask_size']:.4f})"
        bid = f"{u['bid_price']:>12,.0f} ({u['bid_size']:.4f})"
        lines.append(f"  {ask}  |  {bid}")
    lines.append(f"  총 매도잔량: {ob.get('total_ask_size', 0):.4f}")
    lines.append(f"  총 매수잔량: {ob.get('total_bid_size', 0):.4f}")
    return "\n".join(lines)


@mcp.tool()
async def market_list(fiat: str = "KRW") -> str:
    """거래 가능한 전체 코인 목록을 보여줍니다. fiat: KRW, BTC, USDT"""
    if err := _require_client():
        return err
    tickers = client.get_tickers(fiat=fiat.upper())
    if not tickers:
        return "마켓 목록 조회 실패"
    coins = [t.replace(f"{fiat.upper()}-", "") for t in tickers]
    return f"📋 {fiat.upper()} 마켓 ({len(coins)}개): {', '.join(coins[:50])}{'...' if len(coins) > 50 else ''}"


# ═══════════════════════════════════════════════════
#  스마트 분석 (AI 판단용)
# ═══════════════════════════════════════════════════

@mcp.tool()
async def analyze_market(tickers: str = "") -> str:
    """관심 코인의 시장을 종합 분석합니다. RSI, 이동평균, 볼린저, 거래량, 호가 등 다중 지표를 분석하고 매수/매도 추천을 제공합니다."""
    if err := _require_analyzer():
        return err
    if err := _require_trader():
        return err
    cd = _check_cooldown("analyze_market", 30)
    if cd:
        return cd
    if tickers.strip():
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
    else:
        ticker_list = trader.watch_list

    analyses = analyzer.analyze_watchlist(ticker_list)
    return analyzer.format_watchlist_report(analyses)


@mcp.tool()
async def analyze_coin_detail(ticker: str = "KRW-BTC") -> str:
    """특정 코인을 상세 분석합니다. 종합 점수(-100~+100), 지표별 판단 근거를 보여줍니다."""
    if err := _require_analyzer():
        return err
    ticker = ticker.upper()
    a = analyzer.analyze_coin(ticker)
    return analyzer.format_analysis(a)


@mcp.tool()
async def smart_trade_now(tickers: str = "") -> str:
    """시장을 분석하고 조건이 맞으면 자동으로 매수/매도를 실행합니다. 스마트 모드 1회 실행."""
    if err := _require_trader():
        return err
    if tickers.strip():
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        trader.set_watch_list(ticker_list)

    # 스마트 모드로 강제 전환 후 1회 실행
    old_mode = trader.smart_mode
    trader.smart_mode = True
    result = trader.run_cycle()
    trader.smart_mode = old_mode

    if result.get("skipped"):
        return json.dumps({"status": "skipped", "reason": result.get("reason", "Cycle already running")}, ensure_ascii=False)

    lines = [f"🧠 스마트 매매 실행 완료 ({'모의' if result['dry_run'] else '실전'})"]
    lines.append(f"  KRW 잔고: {result.get('krw_balance', 0):,.0f}원")

    for a in result.get("analyses", []):
        emoji = "🟢" if a["score"] >= 30 else "🔴" if a["score"] <= -30 else "⚪"
        coin = a["ticker"].replace("KRW-", "")
        lines.append(f"  {emoji} {coin}: {a['recommendation']} ({a['score']:+d}점) RSI={a['rsi']}")
        if a.get("reasons"):
            lines.append(f"      근거: {' / '.join(a['reasons'][:3])}")

    for action in result.get("actions", []):
        lines.append(f"  ▶ {action}")

    if not result.get("actions"):
        lines.append("  → 매매 조건 미충족, 관망")

    for err in result.get("errors", []):
        lines.append(f"  ❌ {err}")

    return "\n".join(lines)


@mcp.tool()
async def set_smart_mode(enabled: bool = True, buy_threshold: int = 20, sell_threshold: int = -20) -> str:
    """스마트 모드 설정. enabled=True면 종합 분석 기반, False면 단일 전략 기반. threshold는 자동매매 실행 기준 점수."""
    if err := _require_trader():
        return err
    trader.smart_mode = enabled
    trader.buy_threshold = buy_threshold
    trader.sell_threshold = sell_threshold
    mode = "스마트 분석 (다중 지표)" if enabled else f"단일 전략 ({trader.strategy_name})"
    return (
        f"✅ 매매 모드: {mode}\n"
        f"  매수 기준: 점수 {buy_threshold:+d} 이상\n"
        f"  매도 기준: 점수 {sell_threshold:+d} 이하"
    )


@mcp.tool()
async def set_smart_params(max_positions: int = 5, cooldown_minutes: int = 30) -> str:
    """스마트 모드 고급 파라미터 설정. max_positions: 동시 보유 최대 종목 수, cooldown_minutes: 같은 코인 재매매 대기 시간."""
    if err := _require_trader():
        return err
    trader.max_positions = max_positions
    trader.cooldown_minutes = cooldown_minutes
    return (
        f"✅ 스마트 파라미터 변경:\n"
        f"  최대 동시 포지션: {max_positions}개\n"
        f"  매매 쿨다운: {cooldown_minutes}분"
    )


# ═══════════════════════════════════════════════════
#  잔고 / 자산
# ═══════════════════════════════════════════════════

@mcp.tool()
async def my_balance() -> str:
    """내 전체 보유 자산을 조회합니다."""
    if err := _require_client():
        return err
    balances = client.get_balances()
    if not balances:
        return "잔고 조회 실패. API 키를 확인하세요."

    lines = ["💰 보유 자산:"]
    total_krw = 0.0
    tickers_for_price = []
    coin_balances = []

    for b in balances:
        currency = b.get("currency", "")
        balance = float(b.get("balance", 0))
        locked = float(b.get("locked", 0))
        total_amount = balance + locked
        if total_amount <= 0:
            continue

        if currency == "KRW":
            total_krw += total_amount
            lines.append(f"  KRW(원화): {total_amount:,.0f}원")
        else:
            coin_balances.append((currency, total_amount, float(b.get("avg_buy_price", 0))))
            tickers_for_price.append(f"KRW-{currency}")

    if tickers_for_price:
        prices = client.get_prices(tickers_for_price)
        for currency, amount, avg_price in coin_balances:
            ticker = f"KRW-{currency}"
            current_price = prices.get(ticker, 0)
            value = amount * current_price
            total_krw += value
            pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            sign = "+" if pnl_pct >= 0 else ""
            lines.append(
                f"  {currency}: {amount:.4f}개 = {value:,.0f}원 "
                f"(평단 {avg_price:,.0f} / {sign}{pnl_pct:.1f}%)"
            )

    lines.append(f"\n  📊 총 자산 평가액: {total_krw:,.0f}원")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════
#  매수 / 매도
# ═══════════════════════════════════════════════════

@mcp.tool()
async def buy_coin(ticker: str, amount_krw: float) -> str:
    """코인을 시장가로 매수합니다. ticker: 'KRW-BTC', amount_krw: 원화 금액"""
    if err := _require_client():
        return err
    if err := _require_config():
        return err
    if err := _require_tracker():
        return err
    try:
        from crypto_trading.security import trade_safety
    except ImportError:
        return json.dumps({"error": "security module not available"}, ensure_ascii=False)
    if not ticker or not isinstance(ticker, str):
        return "티커를 지정하세요 (예: BTC 또는 KRW-BTC)"
    ticker = ticker.upper().strip()
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    try:
        amount_krw = float(amount_krw)
        if amount_krw <= 0:
            return "주문 금액은 0보다 커야 합니다"
    except (ValueError, TypeError):
        return f"유효하지 않은 금액: {amount_krw}"
    if amount_krw < config.MIN_ORDER_AMOUNT:
        return f"최소 주문 금액: {config.MIN_ORDER_AMOUNT:,.0f}원"

    # 거래 안전 검증
    allowed, safety_msg = trade_safety.check_trade(amount_krw)
    if not allowed:
        return f"❌ {ticker} 매수 차단 — {safety_msg}"

    result = client.buy_market_order(ticker, amount_krw)
    if result:
        trade_safety.record_trade(amount_krw)
        tracker.log_trade("buy", ticker, amount_krw, 0, "수동 매수", result)
        dry = " [모의매매]" if config.DRY_RUN else ""
        return f"✅ {ticker} 매수 완료{dry}: {amount_krw:,.0f}원"
    return f"❌ {ticker} 매수 실패"


@mcp.tool()
async def sell_coin(ticker: str, volume: float = 0) -> str:
    """코인을 시장가로 매도합니다. volume=0이면 전량 매도."""
    if err := _require_client():
        return err
    if err := _require_tracker():
        return err
    if err := _require_config():
        return err
    try:
        from crypto_trading.security import trade_safety
    except ImportError:
        return json.dumps({"error": "security module not available"}, ensure_ascii=False)
    if not ticker or not isinstance(ticker, str):
        return "티커를 지정하세요 (예: BTC 또는 KRW-BTC)"
    ticker = ticker.upper().strip()
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"
    try:
        volume = float(volume)
    except (ValueError, TypeError):
        return f"유효하지 않은 수량: {volume}"
    if volume <= 0:
        volume = client.get_balance(ticker)
        if volume <= 0:
            return f"{ticker} 보유 수량이 없습니다."

    # 거래 안전 검증 (매도 금액 추정)
    est_price = client.get_current_price(ticker) or 0
    if est_price <= 0:
        return f"❌ {ticker} 매도 차단 — 현재가 조회 실패. 가격을 확인할 수 없어 매도를 진행할 수 없습니다."
    est_amount_krw = volume * est_price
    allowed, safety_msg = trade_safety.check_trade(est_amount_krw)
    if not allowed:
        return f"❌ {ticker} 매도 차단 — {safety_msg}"

    result = client.sell_market_order(ticker, volume)
    if result:
        price = client.get_current_price(ticker) or 0
        sell_amount_krw = volume * price
        trade_safety.record_trade(sell_amount_krw)
        tracker.log_trade("sell", ticker, sell_amount_krw, price, "수동 매도", result)
        dry = " [모의매매]" if config.DRY_RUN else ""
        return f"✅ {ticker} 매도 완료{dry}: {volume}개"
    return f"❌ {ticker} 매도 실패"


@mcp.tool()
async def cancel_my_order(uuid: str) -> str:
    """주문을 취소합니다. uuid: 주문 ID"""
    if err := _require_client():
        return err
    result = client.cancel_order(uuid)
    if result:
        return f"✅ 주문 취소 완료: {uuid}"
    return f"❌ 주문 취소 실패: {uuid}"


@mcp.tool()
async def pending_orders(ticker: str = "") -> str:
    """미체결 주문 목록을 조회합니다."""
    if err := _require_client():
        return err
    if not ticker:
        if err := _require_config():
            return err
        # 전체 관심 목록의 미체결 확인
        all_orders = []
        for t in config.DEFAULT_WATCH_LIST:
            orders = client.get_order(t, state="wait")
            if orders:
                all_orders.extend(orders)
        if not all_orders:
            return "미체결 주문 없음"
        lines = ["📋 미체결 주문:"]
        for o in all_orders:
            lines.append(f"  {o.get('market')} {o.get('side')} {o.get('price')} x {o.get('volume')} [{o.get('uuid', '')[:8]}]")
        return "\n".join(lines)
    else:
        orders = client.get_order(ticker.upper(), state="wait")
        if not orders:
            return f"{ticker} 미체결 주문 없음"
        lines = [f"📋 {ticker} 미체결 주문:"]
        for o in orders:
            lines.append(f"  {o.get('side')} {o.get('price')} x {o.get('volume')} [{o.get('uuid', '')[:8]}]")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════
#  자동매매
# ═══════════════════════════════════════════════════

@mcp.tool()
async def start_auto_trade(strategy: str = "smart", tickers: str = "") -> str:
    """자동매매를 시작합니다. strategy: 'smart'(AI 종합분석), 'volatility_breakout', 'ma_crossover', 'rsi'"""
    if err := _require_trader():
        return err
    if strategy == "smart":
        trader.smart_mode = True
    else:
        if strategy not in AVAILABLE_STRATEGIES:
            return f"사용 가능한 전략: smart, {list(AVAILABLE_STRATEGIES.keys())}"
        trader.smart_mode = False
        trader.set_strategy(strategy)

    if tickers.strip():
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        trader.set_watch_list(ticker_list)

    msg = trader.start()
    mode = "스마트 분석" if trader.smart_mode else trader.strategy_name
    return f"🤖 {msg}\n모드: {mode}\n관심 코인: {', '.join(trader.watch_list)}"


@mcp.tool()
async def stop_auto_trade() -> str:
    """자동매매를 중지합니다."""
    if err := _require_trader():
        return err
    msg = trader.stop()
    return f"🛑 {msg}"


@mcp.tool()
async def auto_trade_status() -> str:
    """자동매매 현재 상태를 확인합니다."""
    if err := _require_trader():
        return err
    status = trader.get_status()
    running = "🟢 실행 중" if status["is_running"] else "🔴 중지됨"
    dry = "모의매매" if status["dry_run"] else "실전매매"
    mode = "🧠 스마트 분석" if status.get("smart_mode") else f"📐 {status['strategy']}"

    lines = [
        f"🤖 자동매매 상태: {running} ({dry})",
        f"  모드: {mode}",
        f"  관심 코인: {', '.join(status['watch_list'])}",
        f"  체크 간격: {status['interval_seconds']}초",
        f"  매수 기준: {status.get('buy_threshold', 30):+d}점 | 매도 기준: {status.get('sell_threshold', -30):+d}점",
        f"  최대 포지션: {status.get('max_positions', 5)}개 | 쿨다운: {status.get('cooldown_minutes', 30)}분",
        f"  손절: {status['stop_loss_pct']}% / 익절: {status['take_profit_pct']}%",
        f"  누적 사이클: {status.get('cycle_count', 0)}회 | 마지막: {status['last_cycle']}",
    ]
    if status["last_actions"]:
        lines.append(f"  최근 액션: {', '.join(status['last_actions'])}")
    return "\n".join(lines)


@mcp.tool()
async def set_trade_mode(mode: str = "dry") -> str:
    """매매 모드를 설정합니다. mode: 'dry'(모의매매), 'live'(실전매매)"""
    if err := _require_config():
        return err
    prev_mode = "실전" if not config.DRY_RUN else "모의"
    if mode.lower() == "live":
        config.DRY_RUN = False
        logger.warning(f"[감사] 매매 모드 변경: {prev_mode} → 실전매매")
        return "⚠️ 실전매매 모드로 전환되었습니다. 실제 주문이 실행됩니다!"
    else:
        config.DRY_RUN = True
        logger.info(f"[감사] 매매 모드 변경: {prev_mode} → 모의매매")
        return "✅ 모의매매 모드로 전환되었습니다. 실제 주문은 실행되지 않습니다."


@mcp.tool()
async def set_risk_params(stop_loss: float = -5.0, take_profit: float = 10.0) -> str:
    """손절/익절 비율을 설정합니다. stop_loss는 음수여야 합니다. (예: stop_loss=-5, take_profit=10)"""
    if err := _require_trader():
        return err
    if stop_loss > 0:
        stop_loss = -abs(stop_loss)  # 양수 입력 시 자동 음수 변환
    trader.set_risk_params(stop_loss=stop_loss, take_profit=take_profit)
    return f"✅ 리스크 설정 변경: 손절 {stop_loss}% / 익절 {take_profit}%"


@mcp.tool()
async def set_watch_list(tickers: str) -> str:
    """자동매매 관심 코인 목록을 변경합니다. 쉼표로 구분."""
    if err := _require_trader():
        return err
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    trader.set_watch_list(ticker_list)
    return f"✅ 관심 목록 변경: {', '.join(ticker_list)}"


@mcp.tool()
async def run_trade_cycle() -> str:
    """자동매매 사이클을 1회 수동으로 실행합니다."""
    if err := _require_trader():
        return err
    result = trader.run_cycle()

    if result.get("skipped"):
        return json.dumps({"status": "skipped", "reason": result.get("reason", "Cycle already running")}, ensure_ascii=False)

    lines = [f"🔄 매매 사이클 실행 완료 ({result['strategy']}, {'모의' if result['dry_run'] else '실전'})"]
    lines.append(f"  KRW 잔고: {result.get('krw_balance', 0):,.0f}원")

    for sig in result.get("signals", []):
        emoji = "🟢" if sig["signal"] == "buy" else "🔴" if sig["signal"] == "sell" else "⚪"
        lines.append(f"  {emoji} {sig['ticker']}: {sig['signal']} ({sig['reason']})")

    for action in result.get("actions", []):
        lines.append(f"  ▶ {action}")

    for err in result.get("errors", []):
        lines.append(f"  ❌ {err}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════
#  포트폴리오 / 그래프
# ═══════════════════════════════════════════════════

@mcp.tool()
async def portfolio_summary() -> str:
    """포트폴리오 요약 (총 자산, 수익률, 거래 횟수)을 보여줍니다."""
    if err := _require_tracker():
        return err
    summary = tracker.get_summary()
    if summary.get("status") == "no_data":
        return summary["message"]

    pnl_sign = "+" if summary["pnl_krw"] >= 0 else ""
    lines = [
        "📈 포트폴리오 요약:",
        f"  현재 총 자산: {summary['total_value_krw']:,.0f}원",
        f"  초기 자산: {summary['initial_value_krw']:,.0f}원",
        f"  수익/손실: {pnl_sign}{summary['pnl_krw']:,.0f}원 ({pnl_sign}{summary['pnl_pct']}%)",
        f"  보유 종목 수: {summary['holdings_count']}개",
        f"  기록된 스냅샷: {summary['snapshots_count']}회",
        f"  총 거래 횟수: {summary['trades_count']}회",
    ]
    return "\n".join(lines)


@mcp.tool()
async def portfolio_graph(days: int = 30) -> str:
    """보유 자산 추이 그래프를 생성합니다. days: 최근 N일"""
    if err := _require_client():
        return err
    if err := _require_tracker():
        return err
    # 먼저 현재 상태 스냅샷 기록
    balances = client.get_balances()
    tickers_for_price = [normalize_ticker(b['currency']) for b in balances
                         if b.get("currency") != "KRW" and float(b.get("balance", 0)) > 0]
    prices = client.get_prices(tickers_for_price) if tickers_for_price else {}
    tracker.record_snapshot(balances, prices)

    # 그래프 생성
    path = tracker.generate_portfolio_graph(days=days)
    if path:
        return f"📊 포트폴리오 그래프 생성 완료: {path}"
    return "그래프 생성 실패. 최소 2개의 스냅샷이 필요합니다."


@mcp.tool()
async def holdings_chart() -> str:
    """보유 자산 비중 파이차트를 생성합니다."""
    if err := _require_tracker():
        return err
    path = tracker.generate_holdings_pie_chart()
    if path:
        return f"🥧 보유 비중 차트 생성 완료: {path}"
    return "차트 생성 실패. 스냅샷 데이터가 필요합니다."


@mcp.tool()
async def recent_trades(count: int = 10) -> str:
    """최근 거래 내역을 보여줍니다."""
    if err := _require_tracker():
        return err
    trades = tracker.get_recent_trades(count)
    if not trades:
        return "거래 내역이 없습니다."

    lines = [f"📜 최근 거래 내역 ({len(trades)}건):"]
    for t in trades:
        dry = "[모의]" if t.get("dry_run") else "[실전]"
        emoji = "🟢" if t["side"] == "buy" else "🔴"
        lines.append(
            f"  {emoji} {dry} {t['timestamp'][:16]} {t['side'].upper()} "
            f"{t['ticker']} {t['amount']:,.0f}원 - {t['reason']}"
        )
    return "\n".join(lines)


@mcp.tool()
async def record_portfolio_snapshot() -> str:
    """현재 포트폴리오 스냅샷을 수동으로 기록합니다."""
    if err := _require_client():
        return err
    if err := _require_tracker():
        return err
    balances = client.get_balances()
    if not balances:
        return "잔고 조회 실패"

    tickers_for_price = [normalize_ticker(b['currency']) for b in balances
                         if b.get("currency") != "KRW" and float(b.get("balance", 0)) > 0]
    prices = client.get_prices(tickers_for_price) if tickers_for_price else {}
    snapshot = tracker.record_snapshot(balances, prices)
    return f"✅ 스냅샷 기록 완료: 총 {snapshot['total_value_krw']:,.0f}원 ({len(snapshot['holdings'])}개 자산)"


# ═══════════════════════════════════════════════════
#  도움말
# ═══════════════════════════════════════════════════

# ═══════════════════════════════════════════════════
#  새 도구 (#29-#42)
# ═══════════════════════════════════════════════════

@mcp.tool()
async def kimchi_premium(symbol: str = "KRW-BTC") -> str:
    """김치 프리미엄(업비트 vs 글로벌 가격 차이)을 조회합니다."""
    if err := _require_analyzer():
        return err
    result = analyzer.get_kimchi_premium(symbol)
    if "error" in result:
        return f"김치 프리미엄 조회 실패: {result['error']}"
    return (
        f"김치 프리미엄 ({result['ticker']}):\n"
        f"  업비트 KRW: {result['krw_price']:,.0f}원\n"
        f"  글로벌 USD: ${result['global_usd_price']:,.2f}\n"
        f"  환율 적용: {result['estimated_global_krw']:,.0f}원 (1USD={result['usd_krw_rate']}원)\n"
        f"  프리미엄: {result['premium_pct']:+.2f}%"
    )


@mcp.tool()
async def fear_greed_index() -> str:
    """암호화폐 공포/탐욕 지수를 조회합니다."""
    if err := _require_analyzer():
        return err
    result = analyzer.get_fear_greed_index()
    if result.get("error"):
        return f"공포/탐욕 지수 조회 실패: {result.get('error')}"
    return (
        f"공포/탐욕 지수:\n"
        f"  값: {result['value']}/100\n"
        f"  분류: {result['classification']}\n"
        f"  시점: {result['timestamp']}"
    )


@mcp.tool()
async def market_summary_tool() -> str:
    """전체 암호화폐 시장 요약 정보를 조회합니다."""
    if err := _require_analyzer():
        return err
    result = analyzer.get_market_summary()
    if "error" in result:
        return f"시장 요약 조회 실패: {result['error']}"
    lines = [
        f"시장 요약:",
        f"  총 코인 수: {result['total_coins']}",
        f"  상승: {result['rising_count']}  하락: {result['falling_count']}  보합: {result['flat_count']}",
        f"  평균 변동률: {result['avg_change_pct']:+.2f}%",
        f"  총 거래대금: {result['total_volume_krw']:,.0f}원",
        "",
        "  상승 상위 5:",
    ]
    for g in result.get("top_gainers", []):
        lines.append(f"    {g['ticker']}: {g['price']:,.0f}원 ({g['change_pct']:+.2f}%)")
    lines.append("  하락 상위 5:")
    for l in result.get("top_losers", []):
        lines.append(f"    {l['ticker']}: {l['price']:,.0f}원 ({l['change_pct']:+.2f}%)")
    return "\n".join(lines)


@mcp.tool()
async def trade_statistics(period: str = "all") -> str:
    """거래 통계를 조회합니다. period: 'day', 'week', 'month', 'all'"""
    if err := _require_tracker():
        return err
    stats = tracker.get_trade_statistics(period)
    if stats.get("total_trades", 0) == 0:
        return f"해당 기간({period}) 거래 내역이 없습니다."
    return (
        f"거래 통계 ({stats['period']}):\n"
        f"  총 거래: {stats['total_trades']}회 (매수:{stats['buy_count']} / 매도:{stats['sell_count']})\n"
        f"  승률: {stats['win_rate']}%\n"
        f"  평균 수익률: {stats['avg_profit_pct']:+.2f}%\n"
        f"  최대 연속 수익: {stats['max_consecutive_wins']}회\n"
        f"  최대 연속 손실: {stats['max_consecutive_losses']}회\n"
        f"  총 매수: {stats['total_buy_krw']:,.0f}원\n"
        f"  총 매도: {stats['total_sell_krw']:,.0f}원\n"
        f"  손익: {stats['pnl_krw']:+,.0f}원"
    )


@mcp.tool()
async def set_price_alert(symbol: str, above: float = 0, below: float = 0) -> str:
    """가격 알림을 설정합니다. above: 상한 가격, below: 하한 가격 (0이면 미설정)"""
    if err := _require_trader():
        return err
    above_val = above if above > 0 else None
    below_val = below if below > 0 else None
    result = trader.set_price_alert(symbol, above=above_val, below=below_val)
    if "error" in result:
        return f"알림 설정 실패: {result['error']}"
    alert = result['alert']
    parts = [f"가격 알림 설정 완료: {result['ticker']}"]
    if 'above' in alert:
        parts.append(f"  상한: {alert['above']:,.0f}원 이상 시 알림")
    if 'below' in alert:
        parts.append(f"  하한: {alert['below']:,.0f}원 이하 시 알림")
    return "\n".join(parts)


@mcp.tool()
async def set_trailing_stop_tool(symbol: str, trail_pct: float = 5.0) -> str:
    """트레일링 스탑을 설정합니다. 최고가 대비 trail_pct% 하락 시 자동 매도."""
    if err := _require_trader():
        return err
    result = trader.set_trailing_stop(symbol, trail_pct)
    if "error" in result:
        return f"트레일링 스탑 설정 실패: {result['error']}"
    return (
        f"트레일링 스탑 설정 완료:\n"
        f"  코인: {result['ticker']}\n"
        f"  하락률: {result['trail_pct']}%\n"
        f"  기준 최고가: {result['highest_price']:,.0f}원"
    )


@mcp.tool()
async def crypto_help() -> str:
    """사용 가능한 코인 거래 명령어 목록을 보여줍니다."""
    return """🪙 JARVIS 코인 거래 도움말:

📊 시세 조회:
  - 비트코인 시세 / 이더리움 가격 → coin_price
  - 관심 코인 전체 시세 → coin_prices
  - 호가창 보기 → coin_orderbook
  - 거래 가능 코인 목록 → market_list

🧠 스마트 분석 (AI 판단):
  - 시장 종합 분석 → analyze_market
  - 개별 코인 상세 분석 → analyze_coin_detail
  - 분석 후 자동 매매 실행 → smart_trade_now
  - 스마트 모드 설정 → set_smart_mode
  - 고급 파라미터 (포지션/쿨다운) → set_smart_params

💰 잔고:
  - 내 잔고 / 보유 자산 → my_balance

🛒 매매:
  - 비트코인 10만원어치 매수 → buy_coin
  - 이더리움 전량 매도 → sell_coin
  - 미체결 주문 확인 → pending_orders
  - 주문 취소 → cancel_my_order

🤖 자동매매:
  - 자동매매 시작 (기본=스마트) → start_auto_trade
  - 자동매매 중지 → stop_auto_trade
  - 자동매매 상태 → auto_trade_status
  - 1회 수동 실행 → run_trade_cycle
  - 실전/모의 전환 → set_trade_mode
  - 손절/익절 설정 → set_risk_params
  - 관심 코인 변경 → set_watch_list

📈 포트폴리오:
  - 자산 요약 → portfolio_summary
  - 자산 추이 그래프 → portfolio_graph
  - 보유 비중 차트 → holdings_chart
  - 거래 내역 → recent_trades
  - 스냅샷 기록 → record_portfolio_snapshot

🔒 보안:
  - 5중 보안 점검 → security_status
  - 거래 안전 한도 설정 → set_safety_limits

⚙️ 전략: smart(AI종합분석), volatility_breakout(변동성돌파), ma_crossover(이동평균), rsi
"""


@mcp.tool()
async def security_status() -> str:
    """보안 상태를 점검하고 보고합니다."""
    try:
        from crypto_trading.security import initialize_security, trade_safety
    except ImportError:
        return json.dumps({"error": "security module not available"}, ensure_ascii=False)
    report = initialize_security()
    daily = trade_safety.get_daily_summary()
    lines = [
        f"🔒 5중 보안 체계 점검 결과:",
        report,
        "",
        f"📊 일일 거래 안전 현황:",
        f"  오늘 거래: {daily['trade_count']}회 / 잔여: {daily['remaining_trades']}회",
        f"  오늘 거래액: {daily['total_volume_krw']:,.0f}원 / 잔여: {daily['remaining_volume_krw']:,.0f}원",
    ]
    if daily['recent_alerts']:
        lines.append("  최근 경고:")
        for ts, msg in daily['recent_alerts']:
            lines.append(f"    {ts[:16]} {msg}")
    return "\n".join(lines)


@mcp.tool()
async def set_safety_limits(max_daily_trades: int = 50, max_single_order_krw: float = 1000000,
                             max_daily_volume_krw: float = 5000000) -> str:
    """거래 안전 한도를 설정합니다. 일일 최대 거래 횟수, 1회 최대 금액, 일일 최대 총액."""
    try:
        from crypto_trading.security import trade_safety
    except ImportError:
        return json.dumps({"error": "security module not available"}, ensure_ascii=False)
    trade_safety.set_limits(
        max_daily_trades=max_daily_trades,
        max_single_order_krw=max_single_order_krw,
        max_daily_volume_krw=max_daily_volume_krw,
    )
    return (
        f"🛡️ 거래 안전 한도 설정 완료:\n"
        f"  일일 최대 거래: {max_daily_trades}회\n"
        f"  1회 최대 금액: {max_single_order_krw:,.0f}원\n"
        f"  일일 최대 총액: {max_daily_volume_krw:,.0f}원"
    )


if __name__ == "__main__":
    mcp.run()