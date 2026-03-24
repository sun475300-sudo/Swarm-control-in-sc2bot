"""
코인/금융 확장 기능 (2-1 ~ 2-6)

2-1. 가격 알림 (목표가 DM 알림)
2-2. 백테스트 (과거 데이터 전략 시뮬레이션)
2-3. 뉴스 감정분석 (크롤링 + AI)
2-4. 환율 조회
2-5. 수익 리포트 (주간/월간)
2-6. 온체인 분석 (고래 추적)
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger("jarvis.finance")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ALERTS_FILE = os.path.join(DATA_DIR, "price_alerts.json")

UpbitClient = None
try:
    from crypto_trading.upbit_client import UpbitClient as _UC
    UpbitClient = _UC
except ImportError:
    pass


def _load_alerts() -> list[dict]:
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_alerts(alerts: list[dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)


class FinanceFeaturesCog(commands.Cog, name="금융 기능"):
    """코인/금융 확장 기능."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.price_alerts: list[dict] = _load_alerts()
        self.upbit = None
        if UpbitClient:
            try:
                self.upbit = UpbitClient()
            except Exception as e:
                logger.warning(f"UpbitClient 초기화 실패: {e}")
        self.check_price_alerts.start()
        self.cleanup_old_alerts.start()

    def cog_unload(self):
        self.check_price_alerts.cancel()
        self.cleanup_old_alerts.cancel()

    # ── 2-1. 가격 알림 ──
    @commands.command(name="알림", aliases=["alert", "가격알림"])
    async def set_price_alert(self, ctx: commands.Context, coin: str, target_price: str):
        """가격 알림을 설정합니다. 사용법: !알림 BTC 1억 / !알림 ETH 500만"""
        coin = coin.upper().replace("KRW-", "")
        ticker = f"KRW-{coin}"

        # 한국어 숫자 파싱
        price_str = target_price.replace(",", "").replace(" ", "")
        multiplier = 1
        if "억" in price_str:
            price_str = price_str.replace("억", "")
            multiplier = 100_000_000
        elif "만" in price_str:
            price_str = price_str.replace("만", "")
            multiplier = 10_000
        elif "천" in price_str:
            price_str = price_str.replace("천", "")
            multiplier = 1_000

        try:
            target = float(price_str) * multiplier
        except ValueError:
            await ctx.send("❌ 가격 형식이 올바르지 않습니다. 예: `!알림 BTC 1억` 또는 `!알림 ETH 5000000`")
            return

        # 현재가 확인
        current_price = 0
        if self.upbit:
            try:
                current_price = self.upbit.get_current_price(ticker) or 0
            except Exception:
                pass

        if current_price <= 0:
            await ctx.send("❌ 현재가를 조회할 수 없습니다. 잠시 후 다시 시도해주세요.")
            return

        direction = "above" if target > current_price else "below"

        alert = {
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "ticker": ticker,
            "target_price": target,
            "direction": direction,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "triggered": False,
        }
        self.price_alerts.append(alert)
        _save_alerts(self.price_alerts)

        arrow = "📈 이상" if direction == "above" else "📉 이하"
        embed = discord.Embed(
            title="🔔 가격 알림 설정 완료",
            color=discord.Color.green(),
        )
        embed.add_field(name="코인", value=coin, inline=True)
        embed.add_field(name="목표가", value=f"{target:,.0f} KRW {arrow}", inline=True)
        if current_price:
            embed.add_field(name="현재가", value=f"{current_price:,.0f} KRW", inline=True)
        embed.set_footer(text="목표가 도달 시 DM으로 알려드립니다")
        await ctx.send(embed=embed)

    @commands.command(name="알림목록", aliases=["alerts", "내알림"])
    async def list_alerts(self, ctx: commands.Context):
        """설정된 가격 알림 목록을 확인합니다."""
        user_alerts = [a for a in self.price_alerts if a["user_id"] == ctx.author.id and not a["triggered"]]
        if not user_alerts:
            await ctx.send("📭 설정된 가격 알림이 없습니다.")
            return
        embed = discord.Embed(title="🔔 내 가격 알림 목록", color=discord.Color.gold())
        for i, alert in enumerate(user_alerts, 1):
            coin = alert["ticker"].replace("KRW-", "")
            direction = "📈 이상" if alert["direction"] == "above" else "📉 이하"
            embed.add_field(
                name=f"#{i} {coin}",
                value=f"목표: {alert['target_price']:,.0f} KRW {direction}",
                inline=True,
            )
        await ctx.send(embed=embed)

    @app_commands.command(name="alerts", description="설정된 가격 알림 목록을 확인합니다")
    async def alerts_slash(self, interaction: discord.Interaction):
        user_alerts = [a for a in self.price_alerts if a["user_id"] == interaction.user.id and not a["triggered"]]
        if not user_alerts:
            await interaction.response.send_message("📭 설정된 가격 알림이 없습니다.", ephemeral=True)
            return
        embed = discord.Embed(title="🔔 내 가격 알림 목록", color=discord.Color.gold())
        for i, alert in enumerate(user_alerts, 1):
            coin = alert["ticker"].replace("KRW-", "")
            direction = "📈 이상" if alert["direction"] == "above" else "📉 이하"
            embed.add_field(
                name=f"#{i} {coin}",
                value=f"목표: {alert['target_price']:,.0f} KRW {direction}",
                inline=True,
            )
        await interaction.response.send_message(embed=embed)

    @commands.command(name="알림삭제", aliases=["delalert"])
    async def delete_alert(self, ctx: commands.Context, index: int):
        """가격 알림을 삭제합니다. 사용법: !알림삭제 1"""
        user_alerts = [(i, a) for i, a in enumerate(self.price_alerts) if a["user_id"] == ctx.author.id and not a["triggered"]]
        if index < 1 or index > len(user_alerts):
            await ctx.send(f"❌ 유효한 번호를 입력해주세요. (1~{len(user_alerts)})")
            return
        real_idx = user_alerts[index - 1][0]
        removed = self.price_alerts.pop(real_idx)
        _save_alerts(self.price_alerts)
        coin = removed["ticker"].replace("KRW-", "")
        await ctx.send(f"✅ {coin} {removed['target_price']:,.0f} KRW 알림이 삭제되었습니다.")

    @tasks.loop(seconds=30)
    async def check_price_alerts(self):
        """30초마다 가격 알림 조건 확인."""
        if not self.upbit:
            return
        triggered = []
        for alert in self.price_alerts:
            if alert["triggered"]:
                continue
            try:
                price = self.upbit.get_current_price(alert["ticker"])
                if not price:
                    continue
                hit = False
                if alert["direction"] == "above" and price >= alert["target_price"]:
                    hit = True
                elif alert["direction"] == "below" and price <= alert["target_price"]:
                    hit = True

                if hit:
                    alert["triggered"] = True
                    triggered.append((alert, price))
            except Exception:
                continue

        if triggered:
            _save_alerts(self.price_alerts)

        for alert, price in triggered:
            try:
                user = await self.bot.fetch_user(alert["user_id"])
                coin = alert["ticker"].replace("KRW-", "")
                direction = "돌파 📈" if alert["direction"] == "above" else "하락 📉"
                embed = discord.Embed(
                    title=f"🚨 가격 알림: {coin} 목표가 {direction}!",
                    color=discord.Color.red() if alert["direction"] == "above" else discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(name="현재가", value=f"**{price:,.0f}** KRW", inline=True)
                embed.add_field(name="목표가", value=f"{alert['target_price']:,.0f} KRW", inline=True)
                await user.send(embed=embed)
            except Exception as e:
                logger.warning(f"알림 DM 전송 실패: {e}")

    @check_price_alerts.before_loop
    async def before_check_alerts(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def cleanup_old_alerts(self):
        """1시간마다 오래된 트리거 완료 알림 정리 (최근 100개만 유지)."""
        triggered = [a for a in self.price_alerts if a.get("triggered")]
        active = [a for a in self.price_alerts if not a.get("triggered")]
        if len(triggered) > 100:
            triggered = triggered[-100:]
            self.price_alerts = active + triggered
            _save_alerts(self.price_alerts)
            logger.info(f"오래된 트리거 알림 정리 완료. 남은 알림: {len(self.price_alerts)}")

    @cleanup_old_alerts.before_loop
    async def before_cleanup_alerts(self):
        await self.bot.wait_until_ready()

    # ── 2-2. 백테스트 ──
    @commands.command(name="백테스트", aliases=["backtest"])
    async def backtest(self, ctx: commands.Context, coin: str = "BTC", strategy: str = "RSI", days: int = 30):
        """과거 데이터로 전략을 시뮬레이션합니다. 사용법: !백테스트 BTC RSI 30"""
        coin = coin.upper()
        ticker = f"KRW-{coin}"
        days = min(max(days, 7), 200)

        if not self.upbit:
            await ctx.send("❌ Upbit 클라이언트가 초기화되지 않았습니다.")
            return

        async with ctx.typing():
            try:
                df = self.upbit.get_ohlcv(ticker, interval="day", count=days)
                if df is None or df.empty:
                    await ctx.send(f"❌ {coin} OHLCV 데이터를 가져올 수 없습니다.")
                    return

                closes = df["close"].values.tolist()
                initial_krw = 1_000_000  # 100만원 시작
                krw = initial_krw
                holdings = 0
                trades = []

                if strategy.upper() == "RSI":
                    # RSI 전략: RSI < 30 매수, RSI > 70 매도
                    rsi_period = 14
                    if len(closes) < rsi_period + 1:
                        await ctx.send(f"❌ 데이터가 부족합니다. 최소 {rsi_period + 1}일 필요")
                        return

                    for i in range(rsi_period, len(closes)):
                        gains = []
                        losses = []
                        for j in range(i - rsi_period, i):
                            change = closes[j + 1] - closes[j] if j + 1 < len(closes) else 0
                            if change > 0:
                                gains.append(change)
                            else:
                                losses.append(abs(change))
                        avg_gain = sum(gains) / rsi_period if gains else 0
                        avg_loss = sum(losses) / rsi_period if losses else 0.001
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))

                        if rsi < 30 and krw > 0:
                            holdings = krw / closes[i]
                            krw = 0
                            trades.append(("매수", closes[i], rsi))
                        elif rsi > 70 and holdings > 0:
                            krw = holdings * closes[i]
                            holdings = 0
                            trades.append(("매도", closes[i], rsi))

                elif strategy.upper() in ["MA", "이평선", "이동평균"]:
                    # 이동평균 교차 전략
                    short_period, long_period = 5, 20
                    for i in range(long_period, len(closes)):
                        short_ma = sum(closes[i - short_period:i]) / short_period
                        long_ma = sum(closes[i - long_period:i]) / long_period

                        if short_ma > long_ma and krw > 0:
                            holdings = krw / closes[i]
                            krw = 0
                            trades.append(("매수", closes[i], 0))
                        elif short_ma < long_ma and holdings > 0:
                            krw = holdings * closes[i]
                            holdings = 0
                            trades.append(("매도", closes[i], 0))
                else:
                    await ctx.send(f"❌ 지원 전략: `RSI`, `MA`(이동평균)")
                    return

                # 최종 평가
                final_value = krw + (holdings * closes[-1])
                pnl = final_value - initial_krw
                pnl_pct = (pnl / initial_krw) * 100
                buy_hold_pnl = ((closes[-1] - closes[0]) / closes[0]) * 100

                embed = discord.Embed(
                    title=f"📊 백테스트 결과: {coin} {strategy.upper()} ({days}일)",
                    color=discord.Color.green() if pnl >= 0 else discord.Color.red(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(name="시작 금액", value=f"{initial_krw:,.0f} KRW", inline=True)
                embed.add_field(name="최종 금액", value=f"{final_value:,.0f} KRW", inline=True)
                embed.add_field(name="수익률", value=f"{'📈' if pnl >= 0 else '📉'} {pnl_pct:+.2f}%", inline=True)
                embed.add_field(name="거래 횟수", value=f"{len(trades)}회", inline=True)
                embed.add_field(name="단순 보유 수익률", value=f"{buy_hold_pnl:+.2f}%", inline=True)
                embed.add_field(name="초과 수익", value=f"{pnl_pct - buy_hold_pnl:+.2f}%", inline=True)

                if trades:
                    trade_log = "\n".join(
                        f"{'🟢' if t[0] == '매수' else '🔴'} {t[0]} @ {t[1]:,.0f}"
                        for t in trades[-10:]
                    )
                    embed.add_field(name="최근 거래 (최대 10건)", value=trade_log, inline=False)

                embed.set_footer(text="⚠️ 백테스트 결과는 과거 데이터 기반이며 미래 수익을 보장하지 않습니다")

                # 차트 생성 (matplotlib 사용 가능 시)
                chart_file = None
                try:
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as plt
                    import matplotlib.dates as mdates

                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={"height_ratios": [3, 1]})
                    fig.suptitle(f"{coin} {strategy.upper()} Backtest ({days}d)", fontsize=14)

                    # 가격 차트 + 매수/매도 표시
                    ax1.plot(closes, color="steelblue", linewidth=1, label="Price")
                    # Build index-based trade position map to avoid duplicate price collisions
                    trade_positions = []
                    _trade_iter = iter(trades)
                    _next_trade = next(_trade_iter, None)
                    for idx, price in enumerate(closes):
                        if _next_trade and price == _next_trade[1]:
                            trade_positions.append((idx, _next_trade))
                            _next_trade = next(_trade_iter, None)
                    for idx_pos, t in trade_positions:
                        marker = "^" if t[0] == "매수" else "v"
                        color = "green" if t[0] == "매수" else "red"
                        ax1.scatter(idx_pos, t[1], marker=marker, color=color, s=80, zorder=5)
                    ax1.set_ylabel("Price (KRW)")
                    ax1.legend(loc="upper left")
                    ax1.grid(True, alpha=0.3)

                    # 누적 수익률 차트
                    cumulative = []
                    sim_krw = initial_krw
                    sim_holdings = 0
                    trade_idx = 0
                    for i, price in enumerate(closes):
                        if trade_idx < len(trades):
                            t = trades[trade_idx]
                            if price == t[1]:
                                if t[0] == "매수" and sim_krw > 0:
                                    sim_holdings = sim_krw / price
                                    sim_krw = 0
                                elif t[0] == "매도" and sim_holdings > 0:
                                    sim_krw = sim_holdings * price
                                    sim_holdings = 0
                                trade_idx += 1
                        val = sim_krw + sim_holdings * price
                        cumulative.append((val - initial_krw) / initial_krw * 100)
                    ax2.fill_between(range(len(cumulative)), cumulative, alpha=0.3,
                                     color="green" if cumulative[-1] >= 0 else "red")
                    ax2.plot(cumulative, color="green" if cumulative[-1] >= 0 else "red", linewidth=1)
                    ax2.axhline(y=0, color="black", linewidth=0.5)
                    ax2.set_ylabel("PnL %")
                    ax2.set_xlabel("Days")
                    ax2.grid(True, alpha=0.3)

                    plt.tight_layout()
                    buf = io.BytesIO()
                    plt.savefig(buf, format="png", dpi=100)
                    buf.seek(0)
                    plt.close(fig)
                    chart_file = discord.File(buf, filename="backtest_chart.png")
                    embed.set_image(url="attachment://backtest_chart.png")
                except ImportError:
                    pass  # matplotlib 미설치 시 차트 없이 진행
                except Exception as chart_err:
                    logger.debug(f"백테스트 차트 생성 실패: {chart_err}")

                if chart_file:
                    await ctx.send(embed=embed, file=chart_file)
                else:
                    await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"❌ 백테스트 오류: {e}")

    # ── 2-3. 뉴스 감정 분석 ──
    @commands.command(name="뉴스감정", aliases=["sentiment", "코인뉴스"])
    async def news_sentiment(self, ctx: commands.Context, coin: str = "BTC"):
        """코인 관련 뉴스의 감정을 분석합니다. 사용법: !뉴스감정 BTC"""
        coin = coin.upper()
        async with ctx.typing():
            # DuckDuckGo로 뉴스 검색
            articles = []
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.news(f"{coin} cryptocurrency", max_results=5))
                    for r in results:
                        articles.append({"title": r.get("title", ""), "body": r.get("body", "")[:200]})
            except ImportError:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://news.google.com/rss/search?q={coin}+crypto&hl=ko&gl=KR",
                        ) as resp:
                            if resp.status == 200:
                                import xml.etree.ElementTree as ET
                                text = await resp.text()
                                root = ET.fromstring(text)
                                for item in root.findall(".//item")[:5]:
                                    title = item.findtext("title", "")
                                    articles.append({"title": title, "body": ""})
                except Exception as rss_err:
                    logger.warning(f"RSS XML 파싱 실패: {rss_err}")

            if not articles:
                await ctx.send(f"❌ {coin} 관련 뉴스를 찾을 수 없습니다.")
                return

            news_text = "\n".join(f"- {a['title']}: {a['body']}" for a in articles)

            # AI 감정 분석
            claude_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            sentiment_result = None
            if claude_key:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": claude_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": "claude-sonnet-4-5-20250929",
                            "max_tokens": 1024,
                            "messages": [{"role": "user", "content": f"다음 {coin} 관련 뉴스들의 시장 감정을 분석해주세요. "
                                f"긍정/부정/중립 비율, 전체 감정 점수(-100~+100), 핵심 키워드를 한국어로 알려주세요:\n{news_text}"}],
                        },
                    ) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                            except Exception:
                                data = {}
                            content = data.get("content") or []
                            if content and isinstance(content, list):
                                sentiment_result = content[0].get("text")

            embed = discord.Embed(
                title=f"📰 {coin} 뉴스 감정 분석",
                color=discord.Color.dark_gold(),
                timestamp=datetime.now(timezone.utc),
            )

            if sentiment_result:
                embed.description = sentiment_result[:4000]
            else:
                embed.description = "AI 분석 불가 (API 키 확인 필요)\n\n**최근 뉴스:**"
                for a in articles[:5]:
                    embed.add_field(name=a["title"][:100], value=a["body"][:100] or "...", inline=False)

            embed.set_footer(text="JARVIS News Sentiment")
            await ctx.send(embed=embed)

    # ── 2-4. 환율 조회 ──
    @commands.command(name="환율", aliases=["forex", "exchange"])
    async def forex_rate(self, ctx: commands.Context, currency: str = "USD"):
        """실시간 환율을 조회합니다. 사용법: !환율 USD"""
        currency = currency.upper()
        currency_map = {
            "달러": "USD", "엔": "JPY", "유로": "EUR", "위안": "CNY",
            "파운드": "GBP", "원": "KRW",
        }
        currency = currency_map.get(currency, currency)

        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.exchangerate-api.com/v4/latest/{currency}",
                ) as resp:
                    if resp.status != 200:
                        await ctx.send(f"❌ 환율 조회 실패: {currency}")
                        return
                    data = await resp.json()

            rates = data.get("rates", {})
            krw_rate = rates.get("KRW", 0)

            embed = discord.Embed(
                title=f"💱 환율 정보 (기준: 1 {currency})",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )
            if krw_rate:
                embed.add_field(name="🇰🇷 KRW", value=f"**{krw_rate:,.2f}** 원", inline=True)
            for code in ["USD", "EUR", "JPY", "CNY", "GBP"]:
                if code != currency and code in rates:
                    flag = {"USD": "🇺🇸", "EUR": "🇪🇺", "JPY": "🇯🇵", "CNY": "🇨🇳", "GBP": "🇬🇧"}.get(code, "🏳️")
                    embed.add_field(name=f"{flag} {code}", value=f"{rates[code]:,.4f}", inline=True)

            embed.set_footer(text=f"Source: ExchangeRate API | {data.get('date', '')}")
            await ctx.send(embed=embed)

    # ── 2-5. 수익 리포트 ──
    @commands.command(name="수익리포트", aliases=["pnlreport", "리포트"])
    async def profit_report(self, ctx: commands.Context, period: str = "주간"):
        """수익 리포트를 생성합니다. 사용법: !수익리포트 [주간|월간]"""
        if not self.upbit:
            await ctx.send("❌ Upbit 클라이언트 미초기화")
            return

        async with ctx.typing():
            days = 7 if period in ["주간", "weekly", "7일"] else 30
            trade_log_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "crypto_trading", "data", "trade_log.json",
            )

            trades = []
            if os.path.exists(trade_log_path):
                try:
                    with open(trade_log_path, "r", encoding="utf-8") as f:
                        all_trades = json.load(f)
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                    trades = [t for t in all_trades if t.get("timestamp", "") >= cutoff]
                except Exception:
                    pass

            total_buy = sum(t.get("amount_krw", 0) for t in trades if t.get("side") == "buy")
            total_sell = sum(t.get("amount_krw", 0) for t in trades if t.get("side") == "sell")
            realized_pnl = total_sell - total_buy

            # 현재 포트폴리오
            portfolio_value = 0
            try:
                accounts = self.upbit.get_accounts()
                for acc in accounts:
                    curr = acc.get("currency", "")
                    balance = float(acc.get("balance", 0))
                    if curr == "KRW":
                        portfolio_value += balance
                    elif balance > 0:
                        price = self.upbit.get_current_price(f"KRW-{curr}") or 0
                        portfolio_value += balance * price
            except Exception:
                pass

            period_name = "주간" if days == 7 else "월간"
            embed = discord.Embed(
                title=f"📊 {period_name} 수익 리포트",
                color=discord.Color.green() if realized_pnl >= 0 else discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="기간", value=f"최근 {days}일", inline=True)
            embed.add_field(name="총 거래", value=f"{len(trades)}건", inline=True)
            embed.add_field(name="매수 총액", value=f"{total_buy:,.0f} KRW", inline=True)
            embed.add_field(name="매도 총액", value=f"{total_sell:,.0f} KRW", inline=True)
            embed.add_field(
                name="실현 손익",
                value=f"{'📈' if realized_pnl >= 0 else '📉'} {realized_pnl:+,.0f} KRW",
                inline=True,
            )
            if portfolio_value:
                embed.add_field(name="현재 포트폴리오", value=f"💰 {portfolio_value:,.0f} KRW", inline=True)

            embed.set_footer(text="JARVIS Finance Report")
            await ctx.send(embed=embed)

    # ── 2-6. 온체인 분석 ──
    @commands.command(name="온체인", aliases=["onchain", "고래"])
    async def onchain_analysis(self, ctx: commands.Context, coin: str = "BTC"):
        """온체인 데이터를 분석합니다. 사용법: !온체인 BTC"""
        coin = coin.upper()
        async with ctx.typing():
            embed = discord.Embed(
                title=f"🐋 {coin} 온체인 분석",
                color=discord.Color.dark_blue(),
                timestamp=datetime.now(timezone.utc),
            )

            # Blockchain.com API (BTC)
            if coin == "BTC":
                try:
                    async with aiohttp.ClientSession() as session:
                        stats_url = "https://api.blockchain.info/stats"
                        async with session.get(stats_url) as resp:
                            if resp.status == 200:
                                stats = await resp.json()
                                embed.add_field(name="해시레이트", value=f"{stats.get('hash_rate', 0) / 1e9:.2f} EH/s", inline=True)
                                embed.add_field(name="난이도", value=f"{stats.get('difficulty', 0) / 1e12:.2f}T", inline=True)
                                embed.add_field(name="일일 거래량", value=f"{stats.get('n_tx', 0):,}", inline=True)
                                embed.add_field(name="블록 수", value=f"{stats.get('n_blocks_total', 0):,}", inline=True)
                                market_cap = stats.get('market_price_usd', 0) * 21_000_000
                                embed.add_field(name="시가총액 (추정)", value=f"${market_cap / 1e9:,.1f}B", inline=True)
                                embed.add_field(
                                    name="채굴 보상",
                                    value=f"{stats.get('miners_revenue_btc', 0):.2f} BTC/day",
                                    inline=True,
                                )
                except Exception as e:
                    embed.add_field(name="⚠️", value=f"BTC 온체인 데이터 조회 실패: {e}", inline=False)
            else:
                embed.description = f"{coin} 온체인 데이터는 BTC만 지원됩니다. (추후 ETH 확장 예정)"

            embed.set_footer(text="JARVIS On-Chain Analytics")
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(FinanceFeaturesCog(bot))
