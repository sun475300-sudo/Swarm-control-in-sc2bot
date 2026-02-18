"""
JARVIS Discord Bot - Quick Win Features (#134-#140)
=====================================================
Discord 봇의 고급 인터랙션 기능 모음.

#134: Slash Commands (/price, /balance, /trade)
#135: Embed 포맷 (시세/잔고를 예쁜 Embed로 표시)
#136: Reaction 인터랙션 (리액션으로 추가 동작)
#137: 봇 상태 표시 (BTC 시세를 봇 상태로 표시)
#138: 멘션 모드 (@JARVIS 멘션 시 Claude에게 질문 전달)
#139: DM 지원 (다이렉트 메시지로 봇 사용 가능)
#140: 역할 기반 권한 ("Trader" 역할이 있어야 매매 가능)

사용법:
    python discord_bot_features.py

환경변수:
    DISCORD_BOT_TOKEN   - Discord 봇 토큰
    CLAUDE_API_KEY      - Claude API 키 (멘션 모드용, 선택)
    TRADER_ROLE_NAME    - 매매 권한 역할 이름 (기본: "Trader")
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto_trading.upbit_client import UpbitClient
from crypto_trading.auto_trader import AutoTrader
from crypto_trading.portfolio_tracker import PortfolioTracker
from crypto_trading import config

# ── 로깅 설정 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("jarvis.discord")

# ── 환경변수 ──
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
TRADER_ROLE_NAME = os.environ.get("TRADER_ROLE_NAME", "Trader")

# ── 전역 인스턴스 ──
upbit_client = UpbitClient()
auto_trader = AutoTrader()
portfolio_tracker = PortfolioTracker()

# ── 코인 이모지 매핑 ──
COIN_EMOJI = {
    "BTC": "\U0001FA99",   # 동전 이모지
    "ETH": "\U0001F4CE",   # 보석 대용
    "XRP": "\U0001F4B1",   # 환전
    "SOL": "\u2600\uFE0F", # 태양
    "DOGE": "\U0001F436",  # 강아지
}


# ═══════════════════════════════════════════════════════════════
#  #140: 역할 기반 권한 체크 유틸리티
# ═══════════════════════════════════════════════════════════════

def has_trader_role():
    """매매 명령 실행 전 'Trader' 역할을 확인하는 데코레이터.

    DM에서는 역할 확인 불가하므로 거부한다.
    서버 채널에서 TRADER_ROLE_NAME 역할이 없으면 권한 부족 메시지를 표시한다.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        # DM에서는 매매 명령 차단 (#140 + #139 보안)
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_error_embed("매매 명령은 서버 채널에서만 사용 가능합니다.\n"
                                   "(역할 확인이 필요합니다)"),
                ephemeral=True,
            )
            return False
        # 역할 확인
        member = interaction.user
        role_names = [r.name for r in member.roles]
        if TRADER_ROLE_NAME not in role_names:
            await interaction.response.send_message(
                embed=_error_embed(
                    f"**{TRADER_ROLE_NAME}** 역할이 필요합니다.\n"
                    f"서버 관리자에게 역할 부여를 요청하세요."
                ),
                ephemeral=True,
            )
            return False
        return True
    return app_commands.check(predicate)


# ═══════════════════════════════════════════════════════════════
#  #135: Embed 포맷 유틸리티
# ═══════════════════════════════════════════════════════════════

def _price_embed(ticker: str, price: float, change_pct: Optional[float] = None) -> discord.Embed:
    """코인 시세를 예쁜 Embed로 변환한다.

    Args:
        ticker: 코인 티커 (예: "KRW-BTC")
        price: 현재가 (KRW)
        change_pct: 24시간 변동률 (%, 선택)

    Returns:
        discord.Embed: 시세 정보 Embed
    """
    coin = ticker.replace("KRW-", "")
    emoji = COIN_EMOJI.get(coin, "\U0001F4B0")

    # 변동률에 따른 색상 결정
    if change_pct is not None:
        if change_pct > 0:
            color = discord.Color.red()       # 상승 = 빨강 (한국 주식 관례)
            arrow = "\u25B2"
        elif change_pct < 0:
            color = discord.Color.blue()      # 하락 = 파랑
            arrow = "\u25BC"
        else:
            color = discord.Color.greyple()
            arrow = "\u25AC"
        change_str = f"{arrow} {change_pct:+.2f}%"
    else:
        color = discord.Color.gold()
        change_str = ""

    embed = discord.Embed(
        title=f"{emoji} {coin} 시세",
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="현재가", value=f"**{price:,.0f}** KRW", inline=True)
    if change_str:
        embed.add_field(name="24h 변동", value=change_str, inline=True)
    embed.set_footer(text="JARVIS Crypto | Upbit")
    return embed


def _multi_price_embed(prices: dict, title: str = "관심 코인 시세") -> discord.Embed:
    """여러 코인 시세를 하나의 Embed로 표시한다.

    Args:
        prices: {ticker: price} 딕셔너리
        title: Embed 제목

    Returns:
        discord.Embed: 복수 시세 정보 Embed
    """
    embed = discord.Embed(
        title=f"\U0001F4CA {title}",
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc),
    )
    for ticker, price in prices.items():
        coin = ticker.replace("KRW-", "")
        emoji = COIN_EMOJI.get(coin, "\U0001F4B0")
        if price is not None and price > 0:
            embed.add_field(
                name=f"{emoji} {coin}",
                value=f"**{price:,.0f}** KRW",
                inline=True,
            )
        else:
            embed.add_field(
                name=f"{emoji} {coin}",
                value="조회 실패",
                inline=True,
            )
    embed.set_footer(text="JARVIS Crypto | Upbit")
    return embed


def _balance_embed(balances: list, total_krw: float) -> discord.Embed:
    """잔고 정보를 Embed로 표시한다.

    Args:
        balances: Upbit 잔고 리스트
        total_krw: 총 자산 KRW 환산 가치

    Returns:
        discord.Embed: 잔고 정보 Embed
    """
    embed = discord.Embed(
        title="\U0001F4B0 포트폴리오 잔고",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="\U0001F3E6 총 자산 (KRW 환산)",
        value=f"**{total_krw:,.0f}** KRW",
        inline=False,
    )

    for b in balances:
        currency = b.get("currency", "")
        balance = float(b.get("balance", 0))
        locked = float(b.get("locked", 0))
        total = balance + locked
        if total <= 0:
            continue
        avg_price = float(b.get("avg_buy_price", 0))
        emoji = COIN_EMOJI.get(currency, "\U0001F4B0")

        if currency == "KRW":
            value_str = f"**{total:,.0f}** KRW"
            if locked > 0:
                value_str += f"\n(잠김: {locked:,.0f})"
        else:
            value_str = f"수량: **{total:.8g}**"
            if avg_price > 0:
                value_str += f"\n평단: {avg_price:,.0f} KRW"
            if locked > 0:
                value_str += f"\n(잠김: {locked:.8g})"

        embed.add_field(name=f"{emoji} {currency}", value=value_str, inline=True)

    if len(embed.fields) == 1:
        embed.add_field(name="보유 코인", value="없음", inline=False)

    embed.set_footer(text="JARVIS Crypto | Upbit")
    return embed


def _trade_result_embed(action: str, ticker: str, result: dict) -> discord.Embed:
    """매매 결과를 Embed로 표시한다.

    Args:
        action: "매수" 또는 "매도"
        ticker: 코인 티커
        result: Upbit API 응답 딕셔너리

    Returns:
        discord.Embed: 매매 결과 Embed
    """
    coin = ticker.replace("KRW-", "")
    is_buy = action == "매수"
    color = discord.Color.red() if is_buy else discord.Color.blue()
    emoji = "\U0001F4C8" if is_buy else "\U0001F4C9"

    embed = discord.Embed(
        title=f"{emoji} {coin} {action} {'완료' if result else '실패'}",
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if result:
        if result.get("dry_run"):
            embed.add_field(name="모드", value="\u26A0\uFE0F DRY-RUN (모의 매매)", inline=False)
        if "uuid" in result:
            embed.add_field(name="주문 ID", value=result["uuid"], inline=False)
        embed.add_field(name="상태", value="\u2705 성공", inline=True)
    else:
        embed.add_field(name="상태", value="\u274C 실패", inline=True)
        embed.add_field(name="안내", value="주문이 실패했습니다. 로그를 확인하세요.", inline=False)

    embed.set_footer(text="JARVIS Crypto | Upbit")
    return embed


def _error_embed(message: str) -> discord.Embed:
    """에러 메시지 Embed를 생성한다.

    Args:
        message: 에러 메시지 내용

    Returns:
        discord.Embed: 에러 Embed
    """
    return discord.Embed(
        title="\u274C 오류",
        description=message,
        color=discord.Color.dark_red(),
        timestamp=datetime.now(timezone.utc),
    )


def _info_embed(title: str, description: str) -> discord.Embed:
    """정보 메시지 Embed를 생성한다.

    Args:
        title: Embed 제목
        description: 설명 텍스트

    Returns:
        discord.Embed: 정보 Embed
    """
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc),
    )


# ═══════════════════════════════════════════════════════════════
#  봇 클래스 정의
# ═══════════════════════════════════════════════════════════════

class JarvisCryptoBot(commands.Bot):
    """JARVIS 암호화폐 Discord 봇.

    discord.py의 commands.Bot을 확장하여 슬래시 명령, 리액션 인터랙션,
    봇 상태 표시, 멘션 모드, DM 지원, 역할 기반 권한을 통합한다.
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True   # 멘션 감지에 필요 (#138)
        intents.dm_messages = True       # DM 지원에 필요 (#139)
        intents.reactions = True         # 리액션 인터랙션에 필요 (#136)
        intents.guilds = True            # 역할 확인에 필요 (#140)
        intents.members = True           # 멤버 역할 조회에 필요 (#140)

        super().__init__(
            command_prefix="!",
            intents=intents,
            description="JARVIS Crypto Trading Bot",
        )
        # 리액션으로 보낸 메시지를 추적 (message_id -> 원본 데이터)
        self._reaction_context: dict = {}

    async def setup_hook(self):
        """봇 시작 시 슬래시 명령 등록 및 백그라운드 태스크 시작."""
        self.tree.add_command(price_command)
        self.tree.add_command(balance_command)
        self.tree.add_command(trade_command)
        # 슬래시 명령 동기화
        await self.tree.sync()
        logger.info("슬래시 명령 동기화 완료: /price, /balance, /trade")

        # #137: BTC 시세 상태 표시 태스크 시작
        if not update_bot_presence.is_running():
            update_bot_presence.start(self)
        logger.info("봇 상태 업데이트 태스크 시작됨")

    async def on_ready(self):
        """봇이 Discord에 연결되면 호출."""
        logger.info(f"JARVIS 봇 로그인 완료: {self.user} (ID: {self.user.id})")
        logger.info(f"연결된 서버: {[g.name for g in self.guilds]}")

    async def on_message(self, message: discord.Message):
        """메시지 이벤트 처리 (#138 멘션 모드 + #139 DM 지원).

        - @JARVIS 멘션 시 Claude에게 질문을 전달한다.
        - DM으로 받은 메시지도 처리한다.
        """
        # 봇 자신의 메시지 무시
        if message.author == self.user:
            return

        # #139: DM 지원 - DM으로 온 메시지 처리
        if isinstance(message.channel, discord.DMChannel):
            await self._handle_dm(message)
            return

        # #138: 멘션 모드 - @JARVIS 멘션 감지
        if self.user in message.mentions:
            await self._handle_mention(message)
            return

        # 기본 명령 처리 (prefix 명령)
        await self.process_commands(message)

    async def _handle_dm(self, message: discord.Message):
        """DM 메시지를 처리한다 (#139).

        DM에서는 시세 조회, 잔고 확인 등 읽기 전용 기능만 허용한다.
        매매 명령은 서버 채널에서만 가능하다 (#140 보안).

        Args:
            message: Discord 메시지 객체
        """
        content = message.content.strip().lower()
        logger.info(f"DM 수신 ({message.author}): {content}")

        # 간단한 키워드 기반 DM 응답
        if any(kw in content for kw in ["시세", "price", "가격"]):
            await self._dm_price_response(message)
        elif any(kw in content for kw in ["잔고", "balance", "포트폴리오", "자산"]):
            await self._dm_balance_response(message)
        elif any(kw in content for kw in ["매수", "매도", "buy", "sell", "trade"]):
            await message.channel.send(
                embed=_error_embed(
                    "매매 명령은 서버 채널에서만 실행 가능합니다.\n"
                    "서버에서 `/trade` 슬래시 명령을 사용하세요."
                )
            )
        elif any(kw in content for kw in ["도움", "help", "명령"]):
            await message.channel.send(embed=self._help_embed())
        else:
            # 기본: Claude에게 질문 전달
            await self._ask_claude(message)

    async def _dm_price_response(self, message: discord.Message):
        """DM에서 시세 조회 응답을 보낸다.

        Args:
            message: Discord 메시지 객체
        """
        try:
            prices = upbit_client.get_prices(list(config.DEFAULT_WATCH_LIST))
            embed = _multi_price_embed(prices, "관심 코인 시세")
            sent = await message.channel.send(embed=embed)
            # 리액션 컨텍스트 저장 (#136)
            self._reaction_context[sent.id] = {
                "type": "price_multi",
                "tickers": list(config.DEFAULT_WATCH_LIST),
            }
            await sent.add_reaction("\U0001F44D")  # 상세보기
            await sent.add_reaction("\U0001F4CA")  # 차트
        except Exception as e:
            logger.error(f"DM 시세 응답 실패: {e}")
            await message.channel.send(embed=_error_embed(f"시세 조회 실패: {e}"))

    async def _dm_balance_response(self, message: discord.Message):
        """DM에서 잔고 조회 응답을 보낸다.

        Args:
            message: Discord 메시지 객체
        """
        try:
            balances = upbit_client.get_balances()
            total = upbit_client.get_total_balance_krw()
            embed = _balance_embed(balances, total)
            await message.channel.send(embed=embed)
        except Exception as e:
            logger.error(f"DM 잔고 응답 실패: {e}")
            await message.channel.send(embed=_error_embed(f"잔고 조회 실패: {e}"))

    async def _handle_mention(self, message: discord.Message):
        """@JARVIS 멘션을 처리한다 (#138).

        멘션된 텍스트에서 봇 멘션 부분을 제거하고, 남은 텍스트를
        Claude API에 전달하여 응답을 받는다.

        Args:
            message: Discord 메시지 객체
        """
        # 멘션 부분 제거
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()

        if not content:
            await message.reply(
                embed=_info_embed(
                    "\U0001F916 JARVIS",
                    "무엇을 도와드릴까요? 질문을 함께 적어주세요.\n"
                    "예: `@JARVIS BTC 전망은?`"
                )
            )
            return

        logger.info(f"멘션 질문 ({message.author}): {content}")

        # Claude에게 질문 전달
        async with message.channel.typing():
            response = await self._query_claude(content)

        if response:
            embed = discord.Embed(
                title="\U0001F916 JARVIS 응답",
                description=response[:4096],  # Embed 설명 최대 길이
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"질문: {message.author.display_name}")
            await message.reply(embed=embed)
        else:
            await message.reply(
                embed=_error_embed("Claude 응답을 받지 못했습니다. API 키를 확인하세요.")
            )

    async def _ask_claude(self, message: discord.Message):
        """메시지 내용을 Claude에게 전달한다.

        Args:
            message: Discord 메시지 객체
        """
        content = message.content.strip()
        if not content:
            return

        async with message.channel.typing():
            response = await self._query_claude(content)

        if response:
            embed = discord.Embed(
                title="\U0001F916 JARVIS 응답",
                description=response[:4096],
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc),
            )
            await message.channel.send(embed=embed)
        else:
            await message.channel.send(
                embed=_info_embed(
                    "\U0001F916 JARVIS",
                    "Claude API가 설정되지 않았습니다.\n"
                    "시세 조회: `시세` 또는 `price`\n"
                    "잔고 확인: `잔고` 또는 `balance`\n"
                    "도움말: `help`"
                )
            )

    async def _query_claude(self, question: str) -> Optional[str]:
        """Claude API를 호출하여 응답을 받는다 (#138).

        CLAUDE_API_KEY 환경변수가 설정되어 있어야 한다.
        설정되지 않으면 None을 반환한다.

        Args:
            question: 사용자 질문 텍스트

        Returns:
            Claude 응답 텍스트, 또는 None (API 키 미설정 / 에러)
        """
        if not CLAUDE_API_KEY:
            logger.warning("CLAUDE_API_KEY 미설정 - 멘션 모드 비활성")
            return None

        try:
            import aiohttp

            headers = {
                "x-api-key": CLAUDE_API_KEY,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
            }
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [
                    {"role": "user", "content": question}
                ],
                "system": (
                    "너는 JARVIS, 암호화폐 트레이딩 어시스턴트야. "
                    "한국어로 간결하게 답변해. 암호화폐, 투자, 시장 분석에 특화되어 있어."
                ),
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"]
                    else:
                        error_text = await resp.text()
                        logger.error(f"Claude API 오류 ({resp.status}): {error_text}")
                        return None
        except ImportError:
            logger.error("aiohttp 미설치 - Claude API 호출 불가")
            return None
        except Exception as e:
            logger.error(f"Claude API 호출 실패: {e}")
            return None

    # ─── #136: Reaction 인터랙션 ───

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """리액션 추가 이벤트 처리 (#136).

        봇이 보낸 메시지에 사용자가 리액션을 추가하면:
        - 👍 (상세보기): 해당 코인의 상세 정보를 표시
        - 📊 (차트): 해당 코인의 간단한 가격 추이를 표시

        Args:
            payload: 리액션 이벤트 페이로드
        """
        # 봇 자신의 리액션은 무시
        if payload.user_id == self.user.id:
            return

        # 컨텍스트가 있는 메시지인지 확인
        context = self._reaction_context.get(payload.message_id)
        if not context:
            return

        emoji = str(payload.emoji)
        channel = self.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            if emoji == "\U0001F44D":  # 👍 상세보기
                await self._reaction_detail(channel, context)
            elif emoji == "\U0001F4CA":  # 📊 차트
                await self._reaction_chart(channel, context)
        except Exception as e:
            logger.error(f"리액션 처리 실패: {e}")

    async def _reaction_detail(self, channel, context: dict):
        """리액션 상세보기 응답을 보낸다 (#136).

        코인의 호가, 거래량 등 상세 정보를 Embed로 표시한다.

        Args:
            channel: Discord 채널 객체
            context: 리액션 컨텍스트 딕셔너리
        """
        tickers = context.get("tickers", [])
        if context.get("type") == "price_single":
            tickers = [context.get("ticker", "KRW-BTC")]

        embed = discord.Embed(
            title="\U0001F50D 상세 정보",
            color=discord.Color.teal(),
            timestamp=datetime.now(timezone.utc),
        )

        for ticker in tickers[:5]:  # 최대 5개
            coin = ticker.replace("KRW-", "")
            try:
                price = upbit_client.get_current_price(ticker)
                orderbook = upbit_client.get_orderbook(ticker)

                detail = f"현재가: **{price:,.0f}** KRW" if price else "조회 실패"

                if orderbook and isinstance(orderbook, list) and len(orderbook) > 0:
                    ob = orderbook[0] if isinstance(orderbook[0], dict) else orderbook
                    units = ob.get("orderbook_units", [])
                    if units:
                        best_ask = units[0].get("ask_price", 0)
                        best_bid = units[0].get("bid_price", 0)
                        detail += f"\n매도 1호가: {best_ask:,.0f}"
                        detail += f"\n매수 1호가: {best_bid:,.0f}"
                        spread = ((best_ask - best_bid) / best_bid * 100) if best_bid > 0 else 0
                        detail += f"\n스프레드: {spread:.3f}%"

                embed.add_field(name=f"{coin}", value=detail, inline=True)
            except Exception as e:
                embed.add_field(name=f"{coin}", value=f"조회 실패: {e}", inline=True)

        embed.set_footer(text="JARVIS Crypto | 상세 정보")
        await channel.send(embed=embed)

    async def _reaction_chart(self, channel, context: dict):
        """리액션 차트 응답을 보낸다 (#136).

        코인의 최근 7일 가격 추이를 텍스트 차트로 표시한다.
        (matplotlib이 없는 환경에서도 작동하도록 텍스트 기반)

        Args:
            channel: Discord 채널 객체
            context: 리액션 컨텍스트 딕셔너리
        """
        ticker = "KRW-BTC"
        if context.get("type") == "price_single":
            ticker = context.get("ticker", "KRW-BTC")
        elif context.get("tickers"):
            ticker = context["tickers"][0]

        coin = ticker.replace("KRW-", "")

        try:
            df = upbit_client.get_ohlcv(ticker, interval="day", count=7)
            if df is None or df.empty:
                await channel.send(embed=_error_embed(f"{coin} 차트 데이터 없음"))
                return

            # matplotlib 사용 가능하면 이미지로, 아니면 텍스트 차트
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                import io

                fig, ax = plt.subplots(figsize=(8, 4))
                fig.patch.set_facecolor("#2C2F33")
                ax.set_facecolor("#23272A")

                closes = df["close"].values
                dates = [d.strftime("%m/%d") for d in df.index]

                color = "#ED4245" if closes[-1] >= closes[0] else "#5865F2"
                ax.plot(dates, closes, color=color, linewidth=2, marker="o", markersize=4)
                ax.fill_between(range(len(closes)), closes, alpha=0.1, color=color)

                ax.set_title(f"{coin} 7-Day Price", color="white", fontsize=14)
                ax.tick_params(colors="white")
                ax.spines["bottom"].set_color("white")
                ax.spines["left"].set_color("white")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)

                for i, v in enumerate(closes):
                    ax.annotate(f"{v:,.0f}", (i, v), textcoords="offset points",
                                xytext=(0, 8), ha="center", fontsize=7, color="white")

                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                            facecolor=fig.get_facecolor())
                buf.seek(0)
                plt.close(fig)

                file = discord.File(buf, filename=f"{coin}_chart.png")
                embed = discord.Embed(
                    title=f"\U0001F4C8 {coin} 7일 차트",
                    color=discord.Color.dark_gold(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_image(url=f"attachment://{coin}_chart.png")
                embed.set_footer(text="JARVIS Crypto | Upbit")
                await channel.send(embed=embed, file=file)

            except ImportError:
                # matplotlib 없으면 텍스트 차트
                closes = df["close"].values
                min_p, max_p = min(closes), max(closes)
                chart_width = 20
                lines = []
                for i, row in df.iterrows():
                    close = row["close"]
                    if max_p > min_p:
                        bar_len = int((close - min_p) / (max_p - min_p) * chart_width)
                    else:
                        bar_len = chart_width // 2
                    bar = "\u2588" * bar_len + "\u2591" * (chart_width - bar_len)
                    date_str = i.strftime("%m/%d")
                    lines.append(f"`{date_str}` {bar} **{close:,.0f}**")

                embed = discord.Embed(
                    title=f"\U0001F4CA {coin} 7일 차트",
                    description="\n".join(lines),
                    color=discord.Color.dark_gold(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_footer(text="JARVIS Crypto | 텍스트 차트")
                await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"차트 생성 실패 ({ticker}): {e}")
            await channel.send(embed=_error_embed(f"차트 생성 실패: {e}"))

    def _help_embed(self) -> discord.Embed:
        """도움말 Embed를 생성한다.

        Returns:
            discord.Embed: 도움말 Embed
        """
        embed = discord.Embed(
            title="\U0001F916 JARVIS 도움말",
            description="암호화폐 트레이딩 봇 JARVIS 사용법",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="\U0001F50D 슬래시 명령",
            value=(
                "`/price [코인]` - 시세 조회\n"
                "`/balance` - 잔고 확인\n"
                "`/trade <매수|매도> <코인> <금액>` - 매매 실행"
            ),
            inline=False,
        )
        embed.add_field(
            name="\U0001F4AC 멘션 모드",
            value="`@JARVIS 질문` - Claude에게 질문 전달",
            inline=False,
        )
        embed.add_field(
            name="\u2709\uFE0F DM 지원",
            value=(
                "봇에게 DM으로 메시지를 보내면 응답합니다.\n"
                "키워드: `시세`, `잔고`, `도움`\n"
                "(매매는 서버에서만 가능)"
            ),
            inline=False,
        )
        embed.add_field(
            name="\U0001F44D 리액션 인터랙션",
            value=(
                "봇 응답 메시지에 리액션을 추가하세요:\n"
                "\U0001F44D 상세보기 | \U0001F4CA 차트"
            ),
            inline=False,
        )
        embed.add_field(
            name="\U0001F512 역할 기반 권한",
            value=f"매매 명령에는 **{TRADER_ROLE_NAME}** 역할이 필요합니다.",
            inline=False,
        )
        embed.set_footer(text="JARVIS Crypto Trading Bot")
        return embed


# ═══════════════════════════════════════════════════════════════
#  #134: Slash Commands (/price, /balance, /trade)
# ═══════════════════════════════════════════════════════════════

@app_commands.command(name="price", description="코인 시세를 조회합니다")
@app_commands.describe(
    coin="조회할 코인 심볼 (예: BTC, ETH). 비우면 관심 코인 전체 조회",
)
async def price_command(interaction: discord.Interaction, coin: Optional[str] = None):
    """코인 시세 조회 슬래시 명령 (#134).

    특정 코인을 지정하면 단일 시세를, 지정하지 않으면
    관심 코인 리스트의 전체 시세를 Embed로 표시한다 (#135).
    응답 메시지에 리액션 버튼을 추가한다 (#136).

    Args:
        interaction: Discord 인터랙션 객체
        coin: 코인 심볼 (예: "BTC", "ETH"). None이면 전체 조회.
    """
    await interaction.response.defer()

    try:
        if coin:
            # 단일 코인 조회
            ticker = coin.upper()
            if not ticker.startswith("KRW-"):
                ticker = f"KRW-{ticker}"

            price = upbit_client.get_current_price(ticker)
            if price is None:
                await interaction.followup.send(
                    embed=_error_embed(f"`{ticker}` 시세를 조회할 수 없습니다.")
                )
                return

            # 24h 변동률 계산 시도
            change_pct = None
            try:
                df = upbit_client.get_ohlcv(ticker, interval="day", count=2)
                if df is not None and len(df) >= 2:
                    prev_close = df["close"].iloc[-2]
                    if prev_close > 0:
                        change_pct = (price - prev_close) / prev_close * 100
            except Exception:
                pass

            embed = _price_embed(ticker, price, change_pct)
            sent = await interaction.followup.send(embed=embed, wait=True)

            # #136: 리액션 추가
            bot_instance = interaction.client
            if isinstance(bot_instance, JarvisCryptoBot):
                bot_instance._reaction_context[sent.id] = {
                    "type": "price_single",
                    "ticker": ticker,
                    "tickers": [ticker],
                }
            await sent.add_reaction("\U0001F44D")  # 상세보기
            await sent.add_reaction("\U0001F4CA")  # 차트
        else:
            # 관심 코인 전체 조회
            prices = upbit_client.get_prices(list(config.DEFAULT_WATCH_LIST))
            embed = _multi_price_embed(prices)
            sent = await interaction.followup.send(embed=embed, wait=True)

            # #136: 리액션 추가
            bot_instance = interaction.client
            if isinstance(bot_instance, JarvisCryptoBot):
                bot_instance._reaction_context[sent.id] = {
                    "type": "price_multi",
                    "tickers": list(config.DEFAULT_WATCH_LIST),
                }
            await sent.add_reaction("\U0001F44D")
            await sent.add_reaction("\U0001F4CA")

    except Exception as e:
        logger.error(f"/price 명령 실패: {e}")
        await interaction.followup.send(embed=_error_embed(f"시세 조회 실패: {e}"))


@app_commands.command(name="balance", description="포트폴리오 잔고를 확인합니다")
async def balance_command(interaction: discord.Interaction):
    """잔고 조회 슬래시 명령 (#134).

    Upbit 계정의 전체 잔고를 Embed 형태로 표시한다 (#135).
    총 자산 KRW 환산 가치, 각 코인 수량, 평단가를 포함한다.

    Args:
        interaction: Discord 인터랙션 객체
    """
    await interaction.response.defer(ephemeral=True)  # 잔고는 본인만 보이게

    try:
        balances = upbit_client.get_balances()
        total = upbit_client.get_total_balance_krw()
        embed = _balance_embed(balances, total)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"/balance 명령 실패: {e}")
        await interaction.followup.send(
            embed=_error_embed(f"잔고 조회 실패: {e}"),
            ephemeral=True,
        )


@app_commands.command(name="trade", description="코인을 매수 또는 매도합니다")
@app_commands.describe(
    action="매매 유형",
    coin="코인 심볼 (예: BTC, ETH)",
    amount="금액 (매수: KRW, 매도: 수량)",
)
@app_commands.choices(action=[
    app_commands.Choice(name="매수 (Buy)", value="buy"),
    app_commands.Choice(name="매도 (Sell)", value="sell"),
])
@has_trader_role()  # #140: 역할 확인
async def trade_command(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    coin: str,
    amount: float,
):
    """매매 실행 슬래시 명령 (#134).

    Trader 역할이 있는 사용자만 실행 가능하다 (#140).
    매수 시 KRW 금액을, 매도 시 코인 수량을 지정한다.
    결과를 Embed로 표시한다 (#135).

    Args:
        interaction: Discord 인터랙션 객체
        action: "buy" 또는 "sell"
        coin: 코인 심볼 (예: "BTC")
        amount: 금액(매수: KRW) 또는 수량(매도)
    """
    await interaction.response.defer()

    ticker = coin.upper()
    if not ticker.startswith("KRW-"):
        ticker = f"KRW-{ticker}"

    try:
        if action.value == "buy":
            # 매수: amount는 KRW 금액
            if amount < config.MIN_ORDER_AMOUNT:
                await interaction.followup.send(
                    embed=_error_embed(
                        f"최소 주문 금액: **{config.MIN_ORDER_AMOUNT:,.0f}** KRW\n"
                        f"입력 금액: {amount:,.0f} KRW"
                    )
                )
                return
            result = upbit_client.buy_market_order(ticker, amount)
            embed = _trade_result_embed("매수", ticker, result)
            embed.add_field(name="주문 금액", value=f"{amount:,.0f} KRW", inline=True)

        else:
            # 매도: amount는 코인 수량
            result = upbit_client.sell_market_order(ticker, amount)
            embed = _trade_result_embed("매도", ticker, result)
            embed.add_field(name="매도 수량", value=f"{amount:.8g}", inline=True)

        # 거래 기록
        side = "bid" if action.value == "buy" else "ask"
        portfolio_tracker.log_trade(
            side=side,
            ticker=ticker,
            amount=amount,
            reason=f"Discord /trade by {interaction.user}",
            order_result=result,
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"/trade 명령 실패: {e}")
        await interaction.followup.send(embed=_error_embed(f"매매 실패: {e}"))


# /trade 명령의 권한 에러 핸들러
@trade_command.error
async def trade_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """매매 명령 권한 에러를 처리한다 (#140).

    has_trader_role() 체크에서 발생하는 CheckFailure를 처리한다.
    이미 체크 함수 내에서 응답을 보내므로 여기서는 로깅만 한다.

    Args:
        interaction: Discord 인터랙션 객체
        error: 발생한 에러
    """
    if isinstance(error, app_commands.CheckFailure):
        # has_trader_role()에서 이미 응답을 보냈으므로 로깅만
        logger.warning(f"매매 권한 부족: {interaction.user} (서버: {interaction.guild})")
    else:
        logger.error(f"/trade 명령 에러: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                embed=_error_embed(f"예상치 못한 오류: {error}"),
                ephemeral=True,
            )


# ═══════════════════════════════════════════════════════════════
#  #137: 봇 상태 표시 (BTC 시세)
# ═══════════════════════════════════════════════════════════════

@tasks.loop(minutes=1)
async def update_bot_presence(bot: JarvisCryptoBot):
    """매 1분마다 봇 상태를 BTC 시세로 업데이트한다 (#137).

    Discord 프로필의 "Playing..." 상태에 BTC 현재가를 표시한다.
    API 실패 시에는 기본 상태를 표시한다.

    Args:
        bot: JarvisCryptoBot 인스턴스
    """
    try:
        price = upbit_client.get_current_price("KRW-BTC")
        if price:
            status_text = f"BTC {price:,.0f} KRW"
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=status_text,
                )
            )
        else:
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name="JARVIS Crypto",
                )
            )
    except Exception as e:
        logger.debug(f"봇 상태 업데이트 실패: {e}")
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="JARVIS Crypto",
            )
        )


@update_bot_presence.before_loop
async def before_presence_update(bot: JarvisCryptoBot):
    """봇이 준비될 때까지 대기한다.

    Args:
        bot: JarvisCryptoBot 인스턴스
    """
    await bot.wait_until_ready()


# ═══════════════════════════════════════════════════════════════
#  메인 엔트리포인트
# ═══════════════════════════════════════════════════════════════

def main():
    """Discord 봇을 시작한다.

    DISCORD_BOT_TOKEN 환경변수가 설정되어 있어야 한다.
    """
    if not DISCORD_BOT_TOKEN:
        print("[ERROR] DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        print("  .env 파일 또는 환경변수에 DISCORD_BOT_TOKEN을 설정하세요.")
        print("  예: export DISCORD_BOT_TOKEN='your-bot-token-here'")
        sys.exit(1)

    bot = JarvisCryptoBot()

    logger.info("JARVIS Discord Bot 시작 중...")
    logger.info(f"  - Trader 역할: {TRADER_ROLE_NAME}")
    logger.info(f"  - Claude API: {'설정됨' if CLAUDE_API_KEY else '미설정'}")
    logger.info(f"  - DRY_RUN: {config.DRY_RUN}")

    bot.run(DISCORD_BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
