"""
Discord 고급 기능 모듈 (#141-#149)

Medium + Large 기능 구현:
  #141: 버튼/셀렉트 UI (TradeView, CoinSelectView)
  #142: 스레드 대화 (자동 Thread 생성)
  #143: 스케줄 리포트 (매일/매시간 자동 전송)
  #144: 차트 첨부 (matplotlib → discord.File)
  #145: 음성 개선 (VoiceManager 스텁)
  #146: TTS 응답 (TTSManager 스텁)
  #147: Activity 표시 (게임/매매 상태)
  #148: 다국어 지원 (i18n 한국어/영어)
  #149: 음성 기록 (VoiceHistoryLogger 스텁)
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
from datetime import datetime, time, timezone, timedelta
from typing import Optional, Callable, Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# #141  버튼 / 셀렉트 UI
# ═══════════════════════════════════════════════════════════════════════════════


class TradeView(discord.ui.View):
    """매수/매도/취소 버튼이 포함된 거래 UI 뷰.

    사용자가 버튼을 클릭하면 해당 콜백이 호출되어
    거래 동작을 수행한다.
    """

    def __init__(
        self,
        ticker: str,
        amount: float,
        *,
        on_buy: Optional[Callable] = None,
        on_sell: Optional[Callable] = None,
        timeout: float = 60.0,
    ):
        """TradeView 초기화.

        Args:
            ticker: 거래 대상 티커 (예: 'KRW-BTC').
            amount: 거래 금액(원) 또는 수량.
            on_buy: 매수 버튼 클릭 시 호출할 비동기 콜백.
            on_sell: 매도 버튼 클릭 시 호출할 비동기 콜백.
            timeout: 뷰 타임아웃(초). 기본 60초.
        """
        super().__init__(timeout=timeout)
        self.ticker = ticker
        self.amount = amount
        self._on_buy = on_buy
        self._on_sell = on_sell
        self.result: Optional[str] = None

    @discord.ui.button(label="매수", style=discord.ButtonStyle.green, emoji="\U0001F4B0")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """매수 버튼 클릭 핸들러."""
        self.result = "buy"
        if self._on_buy:
            await self._on_buy(interaction, self.ticker, self.amount)
        else:
            await interaction.response.send_message(
                f"{self.ticker} {self.amount:,.0f} 매수 요청을 접수했습니다.",
                ephemeral=True,
            )
        self._disable_all()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="매도", style=discord.ButtonStyle.red, emoji="\U0001F4B8")
    async def sell_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """매도 버튼 클릭 핸들러."""
        self.result = "sell"
        if self._on_sell:
            await self._on_sell(interaction, self.ticker, self.amount)
        else:
            await interaction.response.send_message(
                f"{self.ticker} {self.amount:,.0f} 매도 요청을 접수했습니다.",
                ephemeral=True,
            )
        self._disable_all()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.grey, emoji="\u274C")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """취소 버튼 클릭 핸들러."""
        self.result = "cancel"
        await interaction.response.send_message("거래를 취소했습니다.", ephemeral=True)
        self._disable_all()
        await interaction.message.edit(view=self)

    def _disable_all(self):
        """모든 버튼을 비활성화한다."""
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True

    async def on_timeout(self):
        """타임아웃 시 모든 버튼 비활성화."""
        self._disable_all()


# ── 코인 선택 드롭다운 ──

# 기본 코인 목록
DEFAULT_COINS = [
    ("BTC", "KRW-BTC", "비트코인"),
    ("ETH", "KRW-ETH", "이더리움"),
    ("XRP", "KRW-XRP", "리플"),
    ("SOL", "KRW-SOL", "솔라나"),
    ("DOGE", "KRW-DOGE", "도지코인"),
    ("ADA", "KRW-ADA", "에이다"),
    ("AVAX", "KRW-AVAX", "아발란체"),
    ("DOT", "KRW-DOT", "폴카닷"),
    ("MATIC", "KRW-MATIC", "폴리곤"),
    ("LINK", "KRW-LINK", "체인링크"),
]


class CoinSelect(discord.ui.Select):
    """코인 선택 드롭다운 메뉴.

    사용자가 코인을 선택하면 콜백이 호출된다.
    """

    def __init__(
        self,
        coins: Optional[list[tuple[str, str, str]]] = None,
        *,
        on_select: Optional[Callable] = None,
        placeholder: str = "코인을 선택하세요",
    ):
        """CoinSelect 초기화.

        Args:
            coins: (심볼, 마켓코드, 한글명) 튜플 리스트. None이면 기본 목록 사용.
            on_select: 선택 시 호출할 비동기 콜백 ``(interaction, market_code)``.
            placeholder: 드롭다운 플레이스홀더 텍스트.
        """
        coin_list = coins or DEFAULT_COINS
        options = [
            discord.SelectOption(label=symbol, value=market, description=name_kr)
            for symbol, market, name_kr in coin_list
        ]
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
        )
        self._on_select = on_select

    async def callback(self, interaction: discord.Interaction):
        """코인 선택 콜백."""
        selected_market = self.values[0]
        if self._on_select:
            await self._on_select(interaction, selected_market)
        else:
            await interaction.response.send_message(
                f"{selected_market} 선택됨.", ephemeral=True
            )


class CoinSelectView(discord.ui.View):
    """코인 선택 드롭다운이 포함된 뷰.

    CoinSelect를 감싸서 독립적으로 메시지에 첨부할 수 있다.
    """

    def __init__(
        self,
        coins: Optional[list[tuple[str, str, str]]] = None,
        *,
        on_select: Optional[Callable] = None,
        placeholder: str = "코인을 선택하세요",
        timeout: float = 60.0,
    ):
        """CoinSelectView 초기화.

        Args:
            coins: (심볼, 마켓코드, 한글명) 튜플 리스트.
            on_select: 선택 시 호출할 비동기 콜백.
            placeholder: 드롭다운 플레이스홀더 텍스트.
            timeout: 뷰 타임아웃(초).
        """
        super().__init__(timeout=timeout)
        self.select = CoinSelect(coins, on_select=on_select, placeholder=placeholder)
        self.add_item(self.select)


# ═══════════════════════════════════════════════════════════════════════════════
# #142  스레드 대화
# ═══════════════════════════════════════════════════════════════════════════════

# 스레드 자동 생성 임계값 (메시지 수)
THREAD_MESSAGE_THRESHOLD = 5

# 채널별 메시지 카운터 (channel_id → count)
_channel_message_counters: dict[int, int] = {}


async def create_thread_for_long_conversation(
    message: discord.Message,
    *,
    threshold: int = THREAD_MESSAGE_THRESHOLD,
    thread_name: Optional[str] = None,
    auto_archive_duration: int = 60,
) -> Optional[discord.Thread]:
    """긴 대화가 감지되면 자동으로 스레드를 생성한다.

    같은 채널에서 연속 ``threshold`` 개 이상의 메시지가 발생하면
    해당 메시지에 스레드를 생성하여 대화를 분리한다.

    Args:
        message: 트리거가 된 Discord 메시지 객체.
        threshold: 스레드 생성까지 필요한 메시지 수. 기본 5.
        thread_name: 스레드 이름. None이면 자동 생성.
        auto_archive_duration: 자동 보관 시간(분). 기본 60.

    Returns:
        생성된 Thread 객체. 임계값 미만이면 None.
    """
    channel_id = message.channel.id
    _channel_message_counters[channel_id] = _channel_message_counters.get(channel_id, 0) + 1
    count = _channel_message_counters[channel_id]

    if count < threshold:
        return None

    # 임계값 도달 시 카운터 초기화 후 스레드 생성
    _channel_message_counters[channel_id] = 0

    name = thread_name or f"대화 계속 - {message.author.display_name} ({datetime.now().strftime('%H:%M')})"
    # 이름 길이 제한 (Discord 최대 100자)
    name = name[:100]

    try:
        thread = await message.create_thread(
            name=name,
            auto_archive_duration=auto_archive_duration,
        )
        await thread.send(
            f"{message.author.mention} 대화가 길어져서 스레드로 이동합니다. "
            f"이어서 대화해 주세요!"
        )
        logger.info("스레드 생성 완료: %s (channel=%d)", name, channel_id)
        return thread
    except discord.HTTPException as exc:
        logger.warning("스레드 생성 실패: %s", exc)
        return None


def reset_thread_counter(channel_id: int) -> None:
    """특정 채널의 메시지 카운터를 초기화한다.

    Args:
        channel_id: 초기화할 채널 ID.
    """
    _channel_message_counters.pop(channel_id, None)


# ═══════════════════════════════════════════════════════════════════════════════
# #143  스케줄 리포트
# ═══════════════════════════════════════════════════════════════════════════════

# 한국 표준시 (UTC+9)
KST = timezone(timedelta(hours=9))
DAILY_REPORT_TIME = time(hour=9, minute=0, tzinfo=KST)


class ScheduledReporter(commands.Cog):
    """스케줄 기반 리포트 자동 전송 Cog.

    - 매일 09:00 KST: 포트폴리오 일일 리포트
    - 매 시간 정각: 시장 요약 리포트
    """

    def __init__(
        self,
        bot: commands.Bot,
        report_channel_id: int,
        *,
        portfolio_fetcher: Optional[Callable] = None,
        market_fetcher: Optional[Callable] = None,
    ):
        """ScheduledReporter 초기화.

        Args:
            bot: Discord 봇 인스턴스.
            report_channel_id: 리포트를 전송할 채널 ID.
            portfolio_fetcher: 포트폴리오 데이터를 가져올 비동기 함수.
                               None이면 기본 더미 데이터 사용.
            market_fetcher: 시장 요약 데이터를 가져올 비동기 함수.
                            None이면 기본 더미 데이터 사용.
        """
        self.bot = bot
        self.report_channel_id = report_channel_id
        self._portfolio_fetcher = portfolio_fetcher
        self._market_fetcher = market_fetcher

    async def cog_load(self):
        """Cog 로드 시 스케줄 루프를 시작한다."""
        self.daily_portfolio_report.start()
        self.hourly_market_summary.start()

    async def cog_unload(self):
        """Cog 언로드 시 스케줄 루프를 중지한다."""
        self.daily_portfolio_report.cancel()
        self.hourly_market_summary.cancel()

    def _get_channel(self) -> Optional[discord.TextChannel]:
        """리포트 채널 객체를 반환한다."""
        return self.bot.get_channel(self.report_channel_id)

    # ── 매일 09:00 KST 포트폴리오 리포트 ──

    @tasks.loop(time=DAILY_REPORT_TIME)
    async def daily_portfolio_report(self):
        """매일 09:00 KST에 포트폴리오 일일 리포트를 전송한다."""
        channel = self._get_channel()
        if channel is None:
            logger.warning("리포트 채널을 찾을 수 없음: %d", self.report_channel_id)
            return

        try:
            if self._portfolio_fetcher:
                data = await self._portfolio_fetcher()
            else:
                data = self._default_portfolio_data()

            embed = discord.Embed(
                title="\U0001F4CA 일일 포트폴리오 리포트",
                description=f"날짜: {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}",
                color=0x2196F3,
            )
            embed.add_field(
                name="총 평가금액",
                value=f"{data.get('total_value', 0):,.0f} 원",
                inline=True,
            )
            embed.add_field(
                name="일일 손익",
                value=f"{data.get('daily_pnl', 0):+,.0f} 원",
                inline=True,
            )
            embed.add_field(
                name="수익률",
                value=f"{data.get('daily_return', 0.0):+.2f}%",
                inline=True,
            )

            # 보유 종목 목록
            holdings = data.get("holdings", [])
            if holdings:
                lines = []
                for h in holdings[:10]:  # 최대 10개
                    symbol = h.get("symbol", "???")
                    pnl = h.get("pnl", 0.0)
                    sign = "+" if pnl >= 0 else ""
                    lines.append(f"`{symbol:>8}` {sign}{pnl:.2f}%")
                embed.add_field(
                    name="보유 종목 (상위 10개)",
                    value="\n".join(lines),
                    inline=False,
                )

            embed.set_footer(text="Jarvis Crypto Trader | 자동 리포트")
            await channel.send(embed=embed)
            logger.info("일일 포트폴리오 리포트 전송 완료")

        except Exception as exc:
            logger.error("일일 리포트 전송 실패: %s", exc, exc_info=True)

    @daily_portfolio_report.before_loop
    async def _before_daily(self):
        """봇 준비 완료까지 대기."""
        await self.bot.wait_until_ready()

    # ── 매 시간 시장 요약 ──

    @tasks.loop(hours=1)
    async def hourly_market_summary(self):
        """매 시간 시장 요약 리포트를 전송한다."""
        channel = self._get_channel()
        if channel is None:
            return

        try:
            if self._market_fetcher:
                data = await self._market_fetcher()
            else:
                data = self._default_market_data()

            embed = discord.Embed(
                title="\U0001F4C8 시장 요약",
                description=datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
                color=0xFF9800,
            )
            for item in data.get("tickers", [])[:10]:
                symbol = item.get("symbol", "???")
                price = item.get("price", 0)
                change = item.get("change_pct", 0.0)
                arrow = "\U0001F7E2" if change >= 0 else "\U0001F534"
                embed.add_field(
                    name=f"{arrow} {symbol}",
                    value=f"{price:,.0f} 원 ({change:+.2f}%)",
                    inline=True,
                )

            embed.set_footer(text="Jarvis Crypto Trader | 시장 요약")
            await channel.send(embed=embed)
            logger.info("시장 요약 리포트 전송 완료")

        except Exception as exc:
            logger.error("시장 요약 전송 실패: %s", exc, exc_info=True)

    @hourly_market_summary.before_loop
    async def _before_hourly(self):
        """봇 준비 완료까지 대기."""
        await self.bot.wait_until_ready()

    # ── 기본 더미 데이터 ──

    @staticmethod
    def _default_portfolio_data() -> dict:
        """포트폴리오 더미 데이터를 반환한다."""
        return {
            "total_value": 10_000_000,
            "daily_pnl": 150_000,
            "daily_return": 1.52,
            "holdings": [
                {"symbol": "BTC", "pnl": 2.3},
                {"symbol": "ETH", "pnl": -0.5},
                {"symbol": "XRP", "pnl": 1.1},
            ],
        }

    @staticmethod
    def _default_market_data() -> dict:
        """시장 요약 더미 데이터를 반환한다."""
        return {
            "tickers": [
                {"symbol": "BTC", "price": 135_000_000, "change_pct": 2.3},
                {"symbol": "ETH", "price": 5_200_000, "change_pct": -0.5},
                {"symbol": "XRP", "price": 3_400, "change_pct": 1.1},
                {"symbol": "SOL", "price": 280_000, "change_pct": 4.2},
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# #144  차트 첨부
# ═══════════════════════════════════════════════════════════════════════════════


def generate_price_chart(
    ticker: str,
    prices: Optional[list[float]] = None,
    timestamps: Optional[list[datetime]] = None,
    *,
    title: Optional[str] = None,
    figsize: tuple[int, int] = (10, 5),
) -> io.BytesIO:
    """가격 차트를 생성하여 BytesIO 이미지로 반환한다.

    matplotlib를 사용하여 라인 차트를 그리고 PNG 이미지를
    BytesIO 버퍼에 저장한다. discord.File과 함께 사용 가능.

    Args:
        ticker: 티커 심볼 (예: 'BTC').
        prices: 가격 데이터 리스트. None이면 샘플 데이터 사용.
        timestamps: 타임스탬프 리스트. None이면 인덱스 사용.
        title: 차트 제목. None이면 자동 생성.
        figsize: 차트 크기 (가로, 세로) 인치.

    Returns:
        PNG 이미지가 담긴 BytesIO 객체.

    Examples:
        >>> buf = generate_price_chart("BTC", [100, 105, 103, 110])
        >>> file = discord.File(buf, filename="BTC_chart.png")
        >>> await channel.send(file=file)
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # 비GUI 백엔드
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import matplotlib.ticker as mticker
    except ImportError:
        logger.error("matplotlib가 설치되어 있지 않습니다: pip install matplotlib")
        raise

    # 샘플 데이터
    if prices is None:
        import random
        random.seed(42)
        base = 100_000_000 if ticker.upper() == "BTC" else 1_000_000
        prices = [base]
        for _ in range(99):
            change = random.gauss(0, base * 0.005)
            prices.append(max(prices[-1] + change, base * 0.8))

    if timestamps is None:
        now = datetime.now()
        timestamps = [now - timedelta(hours=len(prices) - 1 - i) for i in range(len(prices))]

    fig, ax = plt.subplots(figsize=figsize)

    # 가격 라인 그리기
    color = "#2196F3"
    ax.plot(timestamps, prices, color=color, linewidth=1.5, label=f"{ticker} 가격")

    # 가격 영역 채우기
    ax.fill_between(timestamps, prices, alpha=0.1, color=color)

    # 이동평균선 (데이터가 충분할 때)
    if len(prices) >= 20:
        ma20 = _moving_average(prices, 20)
        ax.plot(
            timestamps[19:], ma20,
            color="#FF9800", linewidth=1.0, linestyle="--", label="MA20",
        )

    ax.set_title(title or f"{ticker} 가격 차트", fontsize=14, fontweight="bold")
    ax.set_xlabel("시간")
    ax.set_ylabel("가격 (KRW)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)

    # Y축 통화 형식
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # X축 날짜 형식
    if len(timestamps) > 1:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate(rotation=30)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _moving_average(data: list[float], window: int) -> list[float]:
    """단순 이동 평균을 계산한다.

    Args:
        data: 숫자 리스트.
        window: 이동 평균 윈도우 크기.

    Returns:
        이동 평균 값 리스트 (길이 = len(data) - window + 1).
    """
    result = []
    for i in range(len(data) - window + 1):
        avg = sum(data[i:i + window]) / window
        result.append(avg)
    return result


async def send_chart_to_channel(
    channel: discord.TextChannel,
    ticker: str,
    prices: Optional[list[float]] = None,
    timestamps: Optional[list[datetime]] = None,
) -> discord.Message:
    """차트를 생성하여 Discord 채널에 전송한다.

    Args:
        channel: 전송할 Discord 텍스트 채널.
        ticker: 티커 심볼.
        prices: 가격 데이터 리스트.
        timestamps: 타임스탬프 리스트.

    Returns:
        전송된 Message 객체.
    """
    buf = generate_price_chart(ticker, prices, timestamps)
    file = discord.File(buf, filename=f"{ticker}_chart.png")
    embed = discord.Embed(
        title=f"\U0001F4C8 {ticker} 가격 차트",
        color=0x2196F3,
        timestamp=datetime.now(KST),
    )
    embed.set_image(url=f"attachment://{ticker}_chart.png")
    embed.set_footer(text="Jarvis Crypto Trader")
    return await channel.send(embed=embed, file=file)


# ═══════════════════════════════════════════════════════════════════════════════
# #145  음성 개선 (스텁)
# ═══════════════════════════════════════════════════════════════════════════════


class VoiceManager:
    """음성 채널 관리 매니저 (스텁 구현).

    향후 음성 채널 연결, 오디오 재생 등의 기능을
    확장할 수 있는 기본 구조를 제공한다.
    """

    def __init__(self, bot: commands.Bot):
        """VoiceManager 초기화.

        Args:
            bot: Discord 봇 인스턴스.
        """
        self.bot = bot
        self._voice_clients: dict[int, discord.VoiceClient] = {}
        logger.info("VoiceManager 초기화 완료 (스텁)")

    async def connect(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
        """음성 채널에 연결한다.

        Args:
            channel: 연결할 음성 채널.

        Returns:
            VoiceClient 객체. 실패 시 None.
        """
        guild_id = channel.guild.id
        try:
            if guild_id in self._voice_clients and self._voice_clients[guild_id].is_connected():
                await self._voice_clients[guild_id].move_to(channel)
            else:
                vc = await channel.connect()
                self._voice_clients[guild_id] = vc
            logger.info("음성 채널 연결: %s (guild=%d)", channel.name, guild_id)
            return self._voice_clients[guild_id]
        except discord.ClientException as exc:
            logger.error("음성 채널 연결 실패: %s", exc)
            return None

    async def disconnect(self, guild_id: int) -> bool:
        """음성 채널에서 연결을 해제한다.

        Args:
            guild_id: 서버(길드) ID.

        Returns:
            연결 해제 성공 여부.
        """
        vc = self._voice_clients.pop(guild_id, None)
        if vc and vc.is_connected():
            await vc.disconnect()
            logger.info("음성 채널 연결 해제 (guild=%d)", guild_id)
            return True
        return False

    async def play_audio(self, guild_id: int, source: str) -> bool:
        """음성 채널에서 오디오를 재생한다 (스텁).

        Args:
            guild_id: 서버(길드) ID.
            source: 오디오 소스 경로 또는 URL.

        Returns:
            재생 시작 성공 여부.
        """
        vc = self._voice_clients.get(guild_id)
        if vc is None or not vc.is_connected():
            logger.warning("음성 클라이언트가 연결되어 있지 않음 (guild=%d)", guild_id)
            return False

        # 스텁: 실제 오디오 재생은 FFmpegPCMAudio 등 필요
        logger.info("오디오 재생 요청 (스텁): source=%s, guild=%d", source, guild_id)
        return True

    def is_connected(self, guild_id: int) -> bool:
        """지정 서버에서 음성 연결 여부를 확인한다.

        Args:
            guild_id: 서버(길드) ID.

        Returns:
            연결 여부.
        """
        vc = self._voice_clients.get(guild_id)
        return vc is not None and vc.is_connected()


# ═══════════════════════════════════════════════════════════════════════════════
# #146  TTS 응답 (스텁)
# ═══════════════════════════════════════════════════════════════════════════════


class TTSManager:
    """텍스트-음성 변환(TTS) 매니저 (스텁 구현).

    향후 gTTS, edge-tts 등의 엔진과 연동하여
    텍스트를 음성으로 변환하는 기능을 제공한다.
    """

    def __init__(self, *, default_lang: str = "ko", cache_dir: str = "./tts_cache"):
        """TTSManager 초기화.

        Args:
            default_lang: 기본 언어 코드. 기본값 'ko' (한국어).
            cache_dir: TTS 캐시 디렉토리 경로.
        """
        self.default_lang = default_lang
        self.cache_dir = cache_dir
        self._engine: Optional[str] = None
        logger.info("TTSManager 초기화 완료 (스텁, lang=%s)", default_lang)

    async def synthesize(self, text: str, *, lang: Optional[str] = None) -> Optional[io.BytesIO]:
        """텍스트를 음성으로 변환한다 (스텁).

        Args:
            text: 변환할 텍스트.
            lang: 언어 코드. None이면 기본 언어 사용.

        Returns:
            오디오 데이터가 담긴 BytesIO. 스텁이므로 현재 None 반환.
        """
        target_lang = lang or self.default_lang
        logger.info("TTS 합성 요청 (스텁): lang=%s, text_len=%d", target_lang, len(text))
        # 스텁: 실제 구현 시 gTTS나 edge-tts 사용
        # from gtts import gTTS
        # tts = gTTS(text=text, lang=target_lang)
        # buf = io.BytesIO()
        # tts.write_to_fp(buf)
        # buf.seek(0)
        # return buf
        return None

    async def speak_in_channel(
        self,
        voice_manager: VoiceManager,
        guild_id: int,
        text: str,
        *,
        lang: Optional[str] = None,
    ) -> bool:
        """음성 채널에서 TTS 메시지를 재생한다 (스텁).

        Args:
            voice_manager: VoiceManager 인스턴스.
            guild_id: 서버(길드) ID.
            text: 읽을 텍스트.
            lang: 언어 코드.

        Returns:
            재생 시작 성공 여부.
        """
        audio = await self.synthesize(text, lang=lang)
        if audio is None:
            logger.warning("TTS 합성 결과 없음 (스텁)")
            return False

        return await voice_manager.play_audio(guild_id, "tts_buffer")

    async def send_tts_message(
        self,
        channel: discord.TextChannel,
        text: str,
    ) -> discord.Message:
        """Discord 내장 TTS로 메시지를 전송한다.

        Args:
            channel: 전송할 텍스트 채널.
            text: TTS로 읽을 텍스트.

        Returns:
            전송된 Message 객체.
        """
        return await channel.send(text, tts=True)


# ═══════════════════════════════════════════════════════════════════════════════
# #147  Activity 표시
# ═══════════════════════════════════════════════════════════════════════════════


class ActivityManager:
    """Discord 봇 Activity(상태) 관리 매니저.

    봇의 현재 상태를 다양한 Activity 타입으로 표시한다.
    - Playing: 게임 중 표시
    - Watching: 관찰 중 표시
    - Listening: 듣는 중 표시
    - Streaming: 스트리밍 중 표시
    """

    def __init__(self, bot: commands.Bot):
        """ActivityManager 초기화.

        Args:
            bot: Discord 봇 인스턴스.
        """
        self.bot = bot

    async def set_playing(self, name: str = "StarCraft II") -> None:
        """'Playing ...' 상태를 설정한다.

        Args:
            name: 게임 이름. 기본값 'StarCraft II'.
        """
        activity = discord.Game(name=name)
        await self.bot.change_presence(activity=activity)
        logger.info("Activity 설정: Playing %s", name)

    async def set_watching(self, name: str = "BTC/KRW") -> None:
        """'Watching ...' 상태를 설정한다.

        Args:
            name: 관찰 대상. 기본값 'BTC/KRW'.
        """
        activity = discord.Activity(type=discord.ActivityType.watching, name=name)
        await self.bot.change_presence(activity=activity)
        logger.info("Activity 설정: Watching %s", name)

    async def set_listening(self, name: str = "명령어") -> None:
        """'Listening to ...' 상태를 설정한다.

        Args:
            name: 듣고 있는 대상. 기본값 '명령어'.
        """
        activity = discord.Activity(type=discord.ActivityType.listening, name=name)
        await self.bot.change_presence(activity=activity)
        logger.info("Activity 설정: Listening to %s", name)

    async def set_streaming(self, name: str = "SC2 Training", url: str = "") -> None:
        """'Streaming ...' 상태를 설정한다.

        Args:
            name: 스트리밍 제목. 기본값 'SC2 Training'.
            url: 스트리밍 URL (Twitch만 보라색 표시).
        """
        activity = discord.Streaming(name=name, url=url or "https://twitch.tv/placeholder")
        await self.bot.change_presence(activity=activity)
        logger.info("Activity 설정: Streaming %s", name)

    async def set_trading_status(self, ticker: str, action: str = "watching") -> None:
        """거래 관련 상태를 설정한다.

        Args:
            ticker: 티커 심볼 (예: 'BTC/KRW').
            action: 'watching' 또는 'playing'. 기본값 'watching'.
        """
        if action == "playing":
            await self.set_playing(f"매매 중: {ticker}")
        else:
            await self.set_watching(ticker)

    async def set_idle(self) -> None:
        """봇 상태를 대기(Idle)로 설정한다."""
        await self.bot.change_presence(
            status=discord.Status.idle,
            activity=discord.Game(name="대기 중..."),
        )
        logger.info("Activity 설정: Idle")

    async def clear(self) -> None:
        """Activity를 제거한다."""
        await self.bot.change_presence(activity=None)
        logger.info("Activity 제거 완료")


# ═══════════════════════════════════════════════════════════════════════════════
# #148  다국어 지원 (i18n)
# ═══════════════════════════════════════════════════════════════════════════════

# 메시지 사전: { key: { lang: text } }
_I18N_MESSAGES: dict[str, dict[str, str]] = {
    # ── 일반 ──
    "greeting": {
        "ko": "안녕하세요! Jarvis 트레이딩 봇입니다.",
        "en": "Hello! I'm Jarvis Trading Bot.",
    },
    "help": {
        "ko": "도움말을 보려면 `/help` 명령어를 사용하세요.",
        "en": "Use the `/help` command to see available commands.",
    },
    "error_generic": {
        "ko": "오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        "en": "An error occurred. Please try again later.",
    },
    "error_permission": {
        "ko": "이 명령어를 사용할 권한이 없습니다.",
        "en": "You don't have permission to use this command.",
    },

    # ── 거래 ──
    "trade_buy_confirm": {
        "ko": "{ticker} {amount:,.0f}원 매수를 진행합니다.",
        "en": "Proceeding to buy {ticker} for {amount:,.0f} KRW.",
    },
    "trade_sell_confirm": {
        "ko": "{ticker} {amount:,.0f}원 매도를 진행합니다.",
        "en": "Proceeding to sell {ticker} for {amount:,.0f} KRW.",
    },
    "trade_cancel": {
        "ko": "거래를 취소했습니다.",
        "en": "Trade has been cancelled.",
    },
    "trade_success": {
        "ko": "거래가 성공적으로 완료되었습니다.",
        "en": "Trade completed successfully.",
    },
    "trade_fail": {
        "ko": "거래에 실패했습니다: {reason}",
        "en": "Trade failed: {reason}",
    },

    # ── 포트폴리오 ──
    "portfolio_title": {
        "ko": "포트폴리오 리포트",
        "en": "Portfolio Report",
    },
    "portfolio_total": {
        "ko": "총 평가금액: {total:,.0f}원",
        "en": "Total Value: {total:,.0f} KRW",
    },
    "portfolio_empty": {
        "ko": "보유 중인 자산이 없습니다.",
        "en": "No assets in portfolio.",
    },

    # ── 시장 ──
    "market_summary_title": {
        "ko": "시장 요약",
        "en": "Market Summary",
    },

    # ── 스레드 ──
    "thread_created": {
        "ko": "대화가 길어져서 스레드로 이동합니다.",
        "en": "Conversation is getting long. Moving to a thread.",
    },

    # ── 음성 ──
    "voice_connected": {
        "ko": "음성 채널에 연결되었습니다.",
        "en": "Connected to voice channel.",
    },
    "voice_disconnected": {
        "ko": "음성 채널에서 연결을 해제했습니다.",
        "en": "Disconnected from voice channel.",
    },

    # ── 차트 ──
    "chart_generating": {
        "ko": "{ticker} 차트를 생성 중입니다...",
        "en": "Generating {ticker} chart...",
    },
    "chart_sent": {
        "ko": "{ticker} 차트가 전송되었습니다.",
        "en": "{ticker} chart has been sent.",
    },
}

# 지원 언어 목록
SUPPORTED_LANGUAGES = ("ko", "en")

# 기본 언어
DEFAULT_LANGUAGE = "ko"

# 사용자별 언어 설정 (user_id → lang)
_user_language_prefs: dict[int, str] = {}


def get_text(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """다국어 메시지를 반환한다.

    Args:
        key: 메시지 키.
        lang: 언어 코드 ('ko' 또는 'en'). 기본값 'ko'.
        **kwargs: 메시지 포매팅에 사용할 키워드 인자.

    Returns:
        해당 언어의 메시지 문자열. 키가 없으면 키 자체를 반환.

    Examples:
        >>> get_text("greeting")
        '안녕하세요! Jarvis 트레이딩 봇입니다.'
        >>> get_text("greeting", lang="en")
        "Hello! I'm Jarvis Trading Bot."
        >>> get_text("trade_buy_confirm", ticker="BTC", amount=100000)
        'BTC 100,000원 매수를 진행합니다.'
    """
    messages = _I18N_MESSAGES.get(key)
    if messages is None:
        logger.warning("i18n 키를 찾을 수 없음: %s", key)
        return key

    text = messages.get(lang)
    if text is None:
        # 폴백: 기본 언어 → 첫 번째 사용 가능한 언어
        text = messages.get(DEFAULT_LANGUAGE) or next(iter(messages.values()), key)

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError) as exc:
            logger.warning("i18n 포매팅 실패: key=%s, error=%s", key, exc)

    return text


def set_user_language(user_id: int, lang: str) -> bool:
    """사용자의 언어 설정을 변경한다.

    Args:
        user_id: Discord 사용자 ID.
        lang: 언어 코드.

    Returns:
        설정 성공 여부.
    """
    if lang not in SUPPORTED_LANGUAGES:
        return False
    _user_language_prefs[user_id] = lang
    logger.info("사용자 언어 설정 변경: user=%d, lang=%s", user_id, lang)
    return True


def get_user_language(user_id: int) -> str:
    """사용자의 언어 설정을 반환한다.

    Args:
        user_id: Discord 사용자 ID.

    Returns:
        언어 코드. 설정되지 않았으면 기본 언어 반환.
    """
    return _user_language_prefs.get(user_id, DEFAULT_LANGUAGE)


def register_messages(messages: dict[str, dict[str, str]]) -> None:
    """커스텀 메시지를 등록한다.

    기존 메시지 사전에 새 메시지를 추가하거나 덮어쓴다.

    Args:
        messages: ``{key: {lang: text}}`` 형태의 메시지 사전.
    """
    _I18N_MESSAGES.update(messages)
    logger.info("i18n 메시지 %d개 등록 완료", len(messages))


# ═══════════════════════════════════════════════════════════════════════════════
# #149  음성 기록 (스텁)
# ═══════════════════════════════════════════════════════════════════════════════


class VoiceHistoryLogger:
    """음성 채널 활동 기록 로거 (스텁 구현).

    음성 채널 입장/퇴장/이동 등의 이벤트를 기록한다.
    향후 데이터베이스 저장 등으로 확장 가능.
    """

    def __init__(self, *, log_channel_id: Optional[int] = None, max_history: int = 1000):
        """VoiceHistoryLogger 초기화.

        Args:
            log_channel_id: 음성 활동 로그를 전송할 텍스트 채널 ID.
                            None이면 파일 로그만 기록.
            max_history: 메모리에 보관할 최대 기록 수.
        """
        self.log_channel_id = log_channel_id
        self.max_history = max_history
        self._history: list[dict[str, Any]] = []
        logger.info("VoiceHistoryLogger 초기화 완료 (스텁, max=%d)", max_history)

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
        bot: Optional[commands.Bot] = None,
    ) -> None:
        """음성 상태 변경 이벤트를 처리한다.

        Bot의 on_voice_state_update 이벤트에서 호출.

        Args:
            member: 상태가 변경된 멤버.
            before: 변경 전 VoiceState.
            after: 변경 후 VoiceState.
            bot: 봇 인스턴스 (로그 채널 전송 시 필요).
        """
        event = self._classify_event(before, after)
        if event is None:
            return

        record = {
            "timestamp": datetime.now(KST).isoformat(),
            "user_id": member.id,
            "user_name": str(member),
            "guild_id": member.guild.id,
            "event": event["type"],
            "channel_before": event.get("channel_before"),
            "channel_after": event.get("channel_after"),
        }

        self._history.append(record)

        # 최대 기록 수 초과 시 오래된 것 제거
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        logger.info(
            "음성 이벤트: %s | %s | %s → %s",
            record["event"],
            record["user_name"],
            record.get("channel_before", "-"),
            record.get("channel_after", "-"),
        )

        # 로그 채널로 전송
        if bot and self.log_channel_id:
            await self._send_log(bot, record)

    @staticmethod
    def _classify_event(
        before: discord.VoiceState, after: discord.VoiceState
    ) -> Optional[dict[str, Any]]:
        """음성 상태 변경 이벤트를 분류한다.

        Args:
            before: 변경 전 VoiceState.
            after: 변경 후 VoiceState.

        Returns:
            이벤트 정보 딕셔너리. 음성 관련 변경이 아니면 None.
        """
        if before.channel is None and after.channel is not None:
            return {
                "type": "join",
                "channel_after": after.channel.name,
            }
        elif before.channel is not None and after.channel is None:
            return {
                "type": "leave",
                "channel_before": before.channel.name,
            }
        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel.id != after.channel.id
        ):
            return {
                "type": "move",
                "channel_before": before.channel.name,
                "channel_after": after.channel.name,
            }
        return None

    async def _send_log(self, bot: commands.Bot, record: dict[str, Any]) -> None:
        """로그 채널에 음성 활동 기록을 전송한다.

        Args:
            bot: Discord 봇 인스턴스.
            record: 이벤트 기록 딕셔너리.
        """
        channel = bot.get_channel(self.log_channel_id)
        if channel is None:
            return

        event_type = record["event"]
        event_emojis = {"join": "\U0001F7E2", "leave": "\U0001F534", "move": "\U0001F7E1"}
        emoji = event_emojis.get(event_type, "\u2753")

        event_labels = {"join": "입장", "leave": "퇴장", "move": "이동"}
        label = event_labels.get(event_type, event_type)

        ch_before = record.get("channel_before") or "-"
        ch_after = record.get("channel_after") or "-"

        text = (
            f"{emoji} **{label}** | `{record['user_name']}` | "
            f"{ch_before} \u2192 {ch_after} | "
            f"`{record['timestamp']}`"
        )

        try:
            await channel.send(text)
        except discord.HTTPException as exc:
            logger.warning("음성 로그 전송 실패: %s", exc)

    def get_history(
        self,
        *,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """음성 활동 기록을 조회한다.

        Args:
            user_id: 특정 사용자로 필터링. None이면 전체.
            event_type: 이벤트 타입으로 필터링 ('join', 'leave', 'move').
            limit: 최대 반환 개수.

        Returns:
            기록 딕셔너리 리스트 (최신순).
        """
        result = self._history[::-1]  # 최신순
        if user_id is not None:
            result = [r for r in result if r["user_id"] == user_id]
        if event_type is not None:
            result = [r for r in result if r["event"] == event_type]
        return result[:limit]

    def clear_history(self) -> int:
        """전체 기록을 삭제한다.

        Returns:
            삭제된 기록 수.
        """
        count = len(self._history)
        self._history.clear()
        logger.info("음성 기록 전체 삭제: %d건", count)
        return count


# ═══════════════════════════════════════════════════════════════════════════════
# 통합 셋업 함수
# ═══════════════════════════════════════════════════════════════════════════════


async def setup_advanced_features(
    bot: commands.Bot,
    *,
    report_channel_id: Optional[int] = None,
    voice_log_channel_id: Optional[int] = None,
) -> dict[str, Any]:
    """고급 기능을 봇에 통합 설정한다.

    Args:
        bot: Discord 봇 인스턴스.
        report_channel_id: 스케줄 리포트 전송 채널 ID.
        voice_log_channel_id: 음성 로그 전송 채널 ID.

    Returns:
        초기화된 매니저 인스턴스 딕셔너리.
    """
    managers: dict[str, Any] = {}

    # #145: 음성 매니저
    voice_manager = VoiceManager(bot)
    managers["voice_manager"] = voice_manager

    # #146: TTS 매니저
    tts_manager = TTSManager()
    managers["tts_manager"] = tts_manager

    # #147: Activity 매니저
    activity_manager = ActivityManager(bot)
    managers["activity_manager"] = activity_manager
    # 기본 Activity 설정
    await activity_manager.set_playing("StarCraft II")

    # #143: 스케줄 리포트 (채널 ID가 주어진 경우)
    if report_channel_id:
        reporter = ScheduledReporter(bot, report_channel_id)
        await bot.add_cog(reporter)
        managers["scheduled_reporter"] = reporter

    # #149: 음성 기록 로거
    voice_logger = VoiceHistoryLogger(log_channel_id=voice_log_channel_id)
    managers["voice_logger"] = voice_logger

    # 음성 상태 업데이트 이벤트 등록
    @bot.event
    async def on_voice_state_update(
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        await voice_logger.on_voice_state_update(member, before, after, bot=bot)

    logger.info("Discord 고급 기능 설정 완료: %s", list(managers.keys()))
    return managers


# ═══════════════════════════════════════════════════════════════════════════════
# 슬래시 커맨드 예제 (Cog)
# ═══════════════════════════════════════════════════════════════════════════════


class AdvancedCommandsCog(commands.Cog, name="고급 기능"):
    """Discord 고급 기능 슬래시 커맨드 모음.

    #141 ~ #149 기능을 슬래시 커맨드로 노출한다.
    """

    def __init__(self, bot: commands.Bot, managers: dict[str, Any]):
        """AdvancedCommandsCog 초기화.

        Args:
            bot: Discord 봇 인스턴스.
            managers: setup_advanced_features()에서 반환된 매니저 딕셔너리.
        """
        self.bot = bot
        self.managers = managers

    @app_commands.command(name="trade", description="코인 매매 UI를 표시합니다")
    @app_commands.describe(ticker="거래 티커 (예: KRW-BTC)", amount="거래 금액 (원)")
    async def trade_command(
        self, interaction: discord.Interaction, ticker: str, amount: float
    ):
        """#141: 매매 버튼 UI를 표시하는 슬래시 커맨드."""
        lang = get_user_language(interaction.user.id)
        embed = discord.Embed(
            title=get_text("trade_buy_confirm", lang, ticker=ticker, amount=amount),
            description=f"Ticker: `{ticker}` | Amount: `{amount:,.0f}` KRW",
            color=0x2196F3,
        )
        view = TradeView(ticker, amount)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="coins", description="코인 선택 메뉴를 표시합니다")
    async def coins_command(self, interaction: discord.Interaction):
        """#141: 코인 선택 드롭다운을 표시하는 슬래시 커맨드."""
        view = CoinSelectView()
        await interaction.response.send_message("거래할 코인을 선택하세요:", view=view)

    @app_commands.command(name="chart", description="가격 차트를 생성합니다")
    @app_commands.describe(ticker="차트 티커 (예: BTC)")
    async def chart_command(self, interaction: discord.Interaction, ticker: str):
        """#144: 가격 차트를 생성하여 전송하는 슬래시 커맨드."""
        lang = get_user_language(interaction.user.id)
        await interaction.response.defer()
        try:
            buf = generate_price_chart(ticker)
            file = discord.File(buf, filename=f"{ticker}_chart.png")
            embed = discord.Embed(
                title=get_text("chart_sent", lang, ticker=ticker),
                color=0x2196F3,
            )
            embed.set_image(url=f"attachment://{ticker}_chart.png")
            await interaction.followup.send(embed=embed, file=file)
        except ImportError:
            await interaction.followup.send(
                "matplotlib가 설치되어 있지 않아 차트를 생성할 수 없습니다.",
                ephemeral=True,
            )

    @app_commands.command(name="lang", description="언어를 변경합니다")
    @app_commands.describe(language="언어 코드 (ko/en)")
    @app_commands.choices(
        language=[
            app_commands.Choice(name="한국어", value="ko"),
            app_commands.Choice(name="English", value="en"),
        ]
    )
    async def lang_command(self, interaction: discord.Interaction, language: str):
        """#148: 사용자 언어 설정을 변경하는 슬래시 커맨드."""
        success = set_user_language(interaction.user.id, language)
        if success:
            await interaction.response.send_message(
                get_text("greeting", language), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"지원하지 않는 언어입니다: {language}", ephemeral=True
            )

    @app_commands.command(name="status", description="봇 상태를 변경합니다")
    @app_commands.describe(
        activity_type="상태 타입",
        name="상태 텍스트",
    )
    @app_commands.choices(
        activity_type=[
            app_commands.Choice(name="Playing (게임 중)", value="playing"),
            app_commands.Choice(name="Watching (관찰 중)", value="watching"),
            app_commands.Choice(name="Listening (듣는 중)", value="listening"),
        ]
    )
    async def status_command(
        self,
        interaction: discord.Interaction,
        activity_type: str,
        name: str,
    ):
        """#147: 봇 Activity를 변경하는 슬래시 커맨드."""
        am: ActivityManager = self.managers.get("activity_manager")
        if am is None:
            await interaction.response.send_message("ActivityManager가 초기화되지 않았습니다.", ephemeral=True)
            return

        if activity_type == "playing":
            await am.set_playing(name)
        elif activity_type == "watching":
            await am.set_watching(name)
        elif activity_type == "listening":
            await am.set_listening(name)

        await interaction.response.send_message(
            f"봇 상태가 변경되었습니다: {activity_type} {name}", ephemeral=True
        )

    @app_commands.command(name="voice_history", description="음성 채널 활동 기록을 조회합니다")
    @app_commands.describe(limit="조회할 기록 수 (기본 10)")
    async def voice_history_command(
        self, interaction: discord.Interaction, limit: int = 10
    ):
        """#149: 음성 활동 기록을 조회하는 슬래시 커맨드."""
        vl: VoiceHistoryLogger = self.managers.get("voice_logger")
        if vl is None:
            await interaction.response.send_message("VoiceHistoryLogger가 초기화되지 않았습니다.", ephemeral=True)
            return

        records = vl.get_history(limit=limit)
        if not records:
            await interaction.response.send_message("음성 활동 기록이 없습니다.", ephemeral=True)
            return

        event_labels = {"join": "입장", "leave": "퇴장", "move": "이동"}
        lines = []
        for r in records:
            label = event_labels.get(r["event"], r["event"])
            ch = r.get("channel_after") or r.get("channel_before") or "-"
            lines.append(f"`{r['timestamp'][:19]}` | **{label}** | {r['user_name']} | {ch}")

        embed = discord.Embed(
            title="음성 채널 활동 기록",
            description="\n".join(lines),
            color=0x9C27B0,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
