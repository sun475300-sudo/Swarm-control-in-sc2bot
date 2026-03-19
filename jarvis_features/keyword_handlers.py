# -*- coding: utf-8 -*-
"""
keyword_handlers — _try_local_response에서 추출된 키워드 핸들러 모음.

discord_jarvis.py의 모듈 글로벌(system_mcp_server, crypto_mcp_server 등)에
접근하기 위해 import discord_jarvis as _mod 지연 임포트 패턴을 사용합니다.

핸들러 시그니처: async def handler(prompt, message, bot, user_id, **kwargs) -> Optional[str]
  - 문자열 반환 → message.reply 전송됨 (CommandDispatcher가 처리)
  - None 반환 → 다음 핸들러 또는 AI 폴백으로 이동
  - "__SENT__" 반환 → 핸들러 내부에서 직접 reply 전송 완료 (CommandDispatcher는 빈 문자열 취급)
"""
import re
import asyncio
import logging
import io
import os
import socket
import subprocess
import base64
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("jarvis.keyword_handlers")

# ── 핸들러가 직접 message.reply를 호출한 경우의 시그널 ──
SENT = "__SENT__"


def _mod():
    """discord_jarvis 모듈 참조 (지연 임포트)."""
    import discord_jarvis as m
    return m


def _truncate(text: str, limit: int = 1900) -> str:
    if len(text) > limit:
        return text[:limit] + "\n..."
    return text


def register_all(dispatcher):
    """모든 키워드 핸들러를 CommandDispatcher에 등록."""

    # ══════════════════════════════════════════
    # ── SC2 핸들러 ──
    # ══════════════════════════════════════════

    def _is_trade_context(p):
        return any(w in p for w in ["매매", "거래", "trade", "수익", "손익", "코인", "btc", "eth"])

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["전적", "stats", "sc2"])
        or (any(w in p for w in ["승률", "통계"]) and not _is_trade_context(p))
    ))
    async def handle_sc2_stats(prompt, message, bot, user_id, **kw):
        m = _mod()
        if m.sc2_mcp_server:
            try:
                result = await m.sc2_mcp_server.sc2_bot_stats()
                await message.reply(f"**SC2 전적**\n```\n{result}\n```")
                return SENT
            except Exception as e:
                logger.error(f"SC2 stats: {e}")
        await message.reply("SC2 모듈을 불러올 수 없습니다. (`pip install mcp` 필요)")
        return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["게임", "유닛", "situation"])
        and any(w in p for w in ["상황", "상태", "게임", "situation"])
    ))
    async def handle_sc2_situation(prompt, message, bot, user_id, **kw):
        m = _mod()
        if m.sc2_mcp_server:
            try:
                result = await m.sc2_mcp_server.get_game_situation()
                await message.reply(f"**게임 상황**\n```json\n{_truncate(result)}\n```")
                return SENT
            except Exception as e:
                logger.error(f"SC2 situation: {e}")
                await message.reply(f"게임 상황 조회 실패: {e}")
                return SENT
        return None  # no sc2_mcp_server — skip

    @dispatcher.register(["로그", "log"], max_len=20, exclude=["로그내용", "로그읽기", "logfile"])
    async def handle_sc2_log(prompt, message, bot, user_id, **kw):
        m = _mod()
        if m.sc2_mcp_server:
            try:
                result = await m.sc2_mcp_server.list_bot_logs()
                await message.reply(f"**최근 로그**\n```\n{result}\n```")
                return SENT
            except Exception as e:
                logger.error(f"SC2 logs: {e}")
                await message.reply(f"로그 조회 실패: {e}")
                return SENT
        return None

    # ══════════════════════════════════════════
    # ── 코인 시세 ──
    # ══════════════════════════════════════════

    @dispatcher.register(
        ["시세", "가격", "price", "btc", "eth", "xrp", "sol", "doge", "코인"],
        exclude=["분석", "analyze", "차트분석", "기술적"],
    )
    async def handle_coin_price(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not hasattr(m, 'upbit_client') or not m.upbit_client:
            return None
        try:
            p = prompt.lower().strip()
            symbols = {"btc": "KRW-BTC", "eth": "KRW-ETH", "xrp": "KRW-XRP",
                        "sol": "KRW-SOL", "doge": "KRW-DOGE"}
            target = None
            for sym, ticker in symbols.items():
                if sym in p:
                    target = ticker
                    break
            if target:
                price = await asyncio.to_thread(m.upbit_client.get_current_price, target)
                coin = target.replace("KRW-", "")
                if price:
                    await message.reply(f"**{coin} 현재가:** {price:,.0f} KRW")
                else:
                    await message.reply(f"{coin} 시세를 조회할 수 없습니다.")
            else:
                prices = await asyncio.to_thread(
                    m.upbit_client.get_prices, ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL"]
                )
                lines = []
                for ticker, price in prices.items():
                    coin = ticker.replace("KRW-", "")
                    if price and price > 0:
                        lines.append(f"• **{coin}**: {price:,.0f} KRW")
                await message.reply("**코인 시세**\n" + "\n".join(lines) if lines else "시세 조회 실패")
            return SENT
        except Exception as e:
            logger.error(f"Price: {e}")
            await message.reply(f"시세 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["김프", "김치프리미엄"])
        or ("김치" in p and any(w in p for w in ["프리미엄", "프미", "코인", "비트"]))
    ))
    async def handle_kimchi_premium(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            symbol = "KRW-BTC"
            for w in p.split():
                if w.upper() in ["BTC", "ETH", "XRP", "SOL"]:
                    symbol = f"KRW-{w.upper()}"
            result = await m.crypto_mcp_server.kimchi_premium(symbol)
            await message.reply(f"**김치프리미엄**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Kimchi: {e}")
            await message.reply(f"김프 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        (any(w in p for w in ["탐욕", "fear", "greed"])
         or ("공포" in p and any(w in p for w in ["지수", "index", "코인", "시장", "탐욕"])))
        and len(p) < 30
    ))
    async def handle_fear_greed(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.fear_greed_index()
            await message.reply(f"**공포/탐욕 지수**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Fear/Greed: {e}")
            await message.reply(f"공포/탐욕 지수 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["시장", "market"])
        or ("요약" in p and any(w in p for w in ["시장", "코인", "비트", "크립토", "가상화폐", "market"]))
    ))
    async def handle_market_summary(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.market_summary_tool()
            await message.reply(f"**시장 요약**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Market: {e}")
            await message.reply(f"시장 요약 조회 실패: {e}")
            return SENT

    # ══════════════════════════════════════════
    # ── 날씨 ──
    # ══════════════════════════════════════════

    @dispatcher.register(["날씨", "weather", "기온"], max_len=30)
    async def handle_weather(prompt, message, bot, user_id, **kw):
        m = _mod()
        p = prompt.lower().strip()
        city = None
        if m.web_tools and hasattr(m.web_tools, 'CITY_COORDS'):
            for known_city in m.web_tools.CITY_COORDS.keys():
                if known_city in p:
                    city = known_city
                    break
        if not city:
            words = p.replace("날씨", "").replace("weather", "").replace("기온", "").replace("알려줘", "").replace("알려", "").replace("어때", "").replace("자비스", "").replace(",", "").replace("?", "").strip().split()
            ignore_words = ["오늘", "지금", "내일", "모레", "현재", "이번주", "주말", "좀", "해줘", "보여줘"]
            for w in words:
                if w not in ignore_words:
                    city = w
                    break
        if not city:
            city = "광주"
        if m.web_tools and hasattr(m.web_tools, 'get_weather'):
            try:
                result = await asyncio.to_thread(m.web_tools.get_weather, city)
                await message.reply(result)
                return SENT
            except Exception as e:
                logger.error(f"web_tools weather: {e}")
        if m.system_mcp_server:
            try:
                result = await m.system_mcp_server.weather(city)
                await message.reply(result)
                return SENT
            except Exception as e:
                logger.error(f"MCP weather: {e}")
        await message.reply("날씨 조회 모듈을 사용할 수 없습니다.")
        return SENT

    # ══════════════════════════════════════════
    # ── 검색 ──
    # ══════════════════════════════════════════

    @dispatcher.register(["검색", "search", "찾아"], max_len=40)
    async def handle_search(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.web_tools:
            return None
        try:
            p = prompt.lower().strip()
            query = p.replace("검색", "").replace("search", "").replace("찾아", "").replace("줘", "").strip()
            if query:
                result = await asyncio.to_thread(m.web_tools.search_web, query)
                await message.reply(f"**검색 결과: {query}**\n{_truncate(result)}")
                return SENT
        except Exception as e:
            logger.error(f"Search: {e}")
            await message.reply(f"검색 실패: {e}")
            return SENT
        return None

    # ══════════════════════════════════════════
    # ── Git ──
    # ══════════════════════════════════════════

    @dispatcher.register(["git", "깃"], max_len=30)
    async def handle_git(prompt, message, bot, user_id, **kw):
        try:
            m = _mod()
            res = await asyncio.to_thread(
                subprocess.check_output, ["git", "status", "--short"],
                encoding="utf-8", stderr=subprocess.STDOUT,
                cwd=os.path.dirname(os.path.abspath(m.__file__))
            )
            if not res.strip():
                res = "작업 트리가 깨끗합니다 (nothing to commit)"
            if len(res) > 1500:
                res = res[:1500] + "..."
            await message.reply(f"**Git Status**\n```\n{res}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Git: {e}")
            await message.reply(f"Git 조회 실패: {e}")
            return SENT

    # ══════════════════════════════════════════
    # ── 운세 ──
    # ══════════════════════════════════════════

    @dispatcher.register(["운세", "fortune", "오늘의 운세"])
    async def handle_fortune(prompt, message, bot, user_id, **kw):
        m = _mod()
        if m.web_tools and hasattr(m.web_tools, 'get_daily_fortune'):
            try:
                result = await asyncio.to_thread(m.web_tools.get_daily_fortune)
                await message.reply(result)
                return SENT
            except Exception as e:
                logger.error(f"Fortune: {e}")
        await message.reply("운세 모듈을 사용할 수 없습니다.")
        return SENT

    # ══════════════════════════════════════════
    # ── 브리핑 ──
    # ══════════════════════════════════════════

    @dispatcher.register(["브리핑", "briefing", "모닝"])
    async def handle_briefing(prompt, message, bot, user_id, **kw):
        if bot._daily_briefing:
            try:
                result = await bot._daily_briefing.generate_briefing_async()
                await message.reply(_truncate(str(result)))
                return SENT
            except Exception as e:
                logger.error(f"Briefing: {e}")
                await message.reply(f"브리핑 생성 실패: {e}")
                return SENT
        await message.reply("브리핑 모듈을 사용할 수 없습니다.")
        return SENT

    # ══════════════════════════════════════════
    # ── 시스템: 스크린샷, 웹캠, 번역, 계산, 속도측정, 네트워크, 클립보드, 알림, 타이머 ──
    # ══════════════════════════════════════════

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["스크린샷", "캡처", "screenshot"])
        or ("화면" in p and "분석" not in p)
    ))
    async def handle_screenshot(prompt, message, bot, user_id, **kw):
        import discord
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            res = await m.system_mcp_server.capture_screenshot()
            if "base64," in res:
                b64_str = res.split("base64,", 1)[-1]
                img_data = base64.b64decode(b64_str)
                file = discord.File(io.BytesIO(img_data), filename="screenshot.jpg")
                await message.reply(content="**스크린샷 캡처 완료**", file=file)
            else:
                await message.reply(f"캡처 결과: {res[:500]}")
            return SENT
        except Exception as e:
            logger.error(f"Screenshot: {e}")
            await message.reply(f"스크린샷 실패: {e}")
            return SENT

    @dispatcher.register(["웹캠", "캠", "webcam"])
    async def handle_webcam(prompt, message, bot, user_id, **kw):
        import discord
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            res = await m.system_mcp_server.capture_webcam()
            if "base64," in res:
                b64_str = res.split("base64,", 1)[-1]
                img_data = base64.b64decode(b64_str)
                file = discord.File(io.BytesIO(img_data), filename="webcam.jpg")
                await message.reply(content="**웹캠 캡처 완료**", file=file)
            else:
                await message.reply(f"웹캠 결과: {res[:500]}")
            return SENT
        except Exception as e:
            logger.error(f"Webcam: {e}")
            await message.reply(f"웹캠 캡처 실패: {e}")
            return SENT

    @dispatcher.register(["번역", "translate", "영어로", "한국어로"])
    async def handle_translate(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            text = p.replace("번역", "").replace("translate", "").replace("영어로", "").replace("한국어로", "").strip()
            if not text:
                await message.reply("번역할 텍스트를 입력하세요.\n사용 예: `번역 Hello World`")
                return SENT
            if "한국어로" in p:
                target, source = "ko", "en"
            elif "영어로" in p:
                target, source = "en", "ko"
            else:
                target, source = m._detect_language_direction(text)
            result = await m.system_mcp_server.translate(text, target, source)
            await message.reply(f"**번역 결과** ({source}→{target})\n{result}")
            return SENT
        except Exception as e:
            logger.error(f"Translate: {e}")
            await message.reply(f"번역 실패: {e}")
            return SENT

    @dispatcher.register(["계산", "calc", "calculate"])
    async def handle_calculate(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            expr = p.replace("계산", "").replace("calc", "").replace("calculate", "").strip()
            if not expr:
                await message.reply("계산할 수식을 입력하세요.\n사용 예: `계산 2+3*4`")
                return SENT
            if not re.search(r'\d', expr) and not any(c in expr for c in "+-*/^()."):
                return None  # 수식이 아닌 자연어 → AI 폴백
            result = await m.system_mcp_server.calculate(expr)
            if "계산 실패" in result:
                return None  # 파싱 실패 → AI 폴백
            await message.reply(f"**계산 결과**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Calculate: {e}")
            return None  # 실패 시 AI 폴백

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["속도", "speed", "speedtest", "인터넷"])
        and any(w in p for w in ["측정", "test", "테스트", "확인"])
    ))
    async def handle_speed_test(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            await message.reply("system_mcp_server 모듈이 로드되지 않아 속도 측정을 할 수 없습니다.")
            return SENT
        try:
            await message.reply("인터넷 속도 측정 중... (30초~1분 소요)")
            result = await m.system_mcp_server.check_internet_speed()
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Speed test: {e}")
            await message.reply(f"속도 측정 실패: {e}")
            return SENT

    @dispatcher.register(["네트워크", "network", "ip", "포트"])
    async def handle_network(prompt, message, bot, user_id, **kw):
        m = _mod()
        if m.system_mcp_server:
            try:
                result = await m.system_mcp_server.network_status()
                await message.reply(f"**네트워크 상태**\n```\n{_truncate(result)}\n```")
                return SENT
            except Exception as e:
                logger.error(f"Network via MCP: {e}")
        # fallback
        try:
            import psutil as _psutil
        except ImportError:
            _psutil = None
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            net = _psutil.net_if_addrs() if _psutil else {}
            lines = [f"호스트명: {hostname}", f"로컬 IP: {local_ip}", "인터페이스:"]
            for iface, addrs in net.items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        lines.append(f"  {iface}: {addr.address}")
            await message.reply(f"**네트워크 상태**\n```\n" + "\n".join(lines) + "\n```")
            return SENT
        except Exception as e2:
            logger.error(f"Network fallback: {e2}")
            await message.reply(f"네트워크 상태 조회 실패: {e2}")
            return SENT

    @dispatcher.register(["클립보드", "clipboard", "붙여넣기"])
    async def handle_clipboard(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            result = await m.system_mcp_server.clipboard_read()
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Clipboard: {e}")
            await message.reply(f"클립보드 읽기 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["알림", "notification", "notify"])
        and len(p) < 100
        and not any(w in p for w in ["가격", "price", "이상", "이하", "도달",
                                      "btc", "eth", "xrp", "sol", "doge",
                                      "비트", "이더", "리플", "코인"])
    ))
    async def handle_notification(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            text = p.replace("알림", "").replace("notification", "").replace("notify", "").strip()
            if not text:
                text = "JARVIS 알림 테스트"
            result = await m.system_mcp_server.send_notification("JARVIS", text)
            await message.reply(f"{result}")
            return SENT
        except Exception as e:
            logger.error(f"Notification: {e}")
            await message.reply(f"알림 전송 실패: {e}")
            return SENT

    @dispatcher.register(["타이머", "timer", "알람"], max_len=50)
    async def handle_timer(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            nums = re.findall(r'(\d+)', p)
            if nums:
                minutes = float(nums[0])
                msg_text = p
                for n in nums:
                    msg_text = msg_text.replace(n, "").strip()
                msg_text = msg_text.replace("타이머", "").replace("timer", "").replace("분", "").replace("알람", "").strip() or "타이머 완료"
                result = await m.system_mcp_server.set_timer(minutes, msg_text)
                await message.reply(f"**타이머 설정**\n{result}")
            else:
                result = await m.system_mcp_server.list_timers()
                await message.reply(f"**타이머 목록**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Timer: {e}")
            await message.reply(f"타이머 설정 실패: {e}")
            return SENT

    # ══════════════════════════════════════════
    # ── 시간/날짜 ──
    # ══════════════════════════════════════════

    @dispatcher.register(match_fn=lambda p: (
        (any(w in p for w in ["시간", "몇시", "날짜"])
         or (p.strip() == "오늘")
         or ("오늘" in p and any(w in p for w in ["몇일", "무슨요일", "날짜", "며칠"])))
        and len(p) < 30
        and not any(w in p for w in ["시세", "날씨", "가격", "얼마", "상태", "분석", "공포", "지수"])
    ))
    async def handle_time(prompt, message, bot, user_id, **kw):
        from .constants import WEEKDAY_KR
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        day_name = WEEKDAY_KR[now_kst.weekday()]
        await message.reply(f"현재 시간 (KST): **{now_kst.strftime('%Y-%m-%d')} {day_name} {now_kst.strftime('%H:%M:%S')}**")
        return SENT

    # ══════════════════════════════════════════
    # ── 인사 ──
    # ══════════════════════════════════════════

    @dispatcher.register(["안녕", "hello", "hi", "반가워", "ㅎㅇ"], max_len=20)
    async def handle_greeting(prompt, message, bot, user_id, **kw):
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        name = message.author.display_name
        hour = now_kst.hour
        if hour < 12:
            greeting = "좋은 아침이에요"
        elif hour < 18:
            greeting = "좋은 오후예요"
        else:
            greeting = "좋은 저녁이에요"
        await message.reply(
            f"안녕하세요, {name}님! {greeting}.\n"
            f"저는 **JARVIS**입니다. 무엇을 도와드릴까요?\n\n"
            f"**사용 가능한 명령:**\n"
            f"• `전적` / `승률` - SC2 봇 전적\n"
            f"• `시스템` / `CPU` - PC 상태\n"
            f"• `시세` / `BTC` - 코인 시세\n"
            f"• `!scan` / `화면 분석` - 화면 AI 분석\n"
            f"• `!monitor on` - 화면 모니터링 (3분)\n"
            f"• `!cctv snap` - 웹캠 캡처\n"
            f"• `볼륨 올려` / `절전` / `잠금` - PC 제어\n"
            f"• `리플레이` / `코칭` / `래더` - SC2 고급\n"
            f"• `일정` / `메모` - 캘린더/노션\n"
            f"• `도움` - 전체 도움말"
        )
        return SENT

    # ══════════════════════════════════════════
    # ── 크립토 고급 ──
    # ══════════════════════════════════════════

    @dispatcher.register(["호가", "orderbook", "매수벽", "매도벽"])
    async def handle_orderbook(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            ticker = bot._extract_ticker(prompt.lower())
            result = await m.crypto_mcp_server.coin_orderbook(ticker)
            await message.reply(f"**호가창 ({ticker})**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Orderbook: {e}")
            await message.reply(f"호가창 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["마켓", "종목", "상장"])
        and any(w in p for w in ["목록", "리스트", "list", "전체"])
    ))
    async def handle_market_list(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.market_list()
            await message.reply(f"**거래 가능 마켓**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"마켓 목록 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["분석", "analyze", "차트분석", "기술적"])
        and any(w in p for w in ["코인", "btc", "eth", "xrp", "sol", "matic", "ada",
                                  "doge", "avax", "dot", "link", "시세", "암호화폐", "가상화폐"])
    ))
    async def handle_coin_analysis(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            ticker = bot._extract_ticker(p)
            if any(w in p for w in ["상세", "detail", "디테일"]):
                result = await m.crypto_mcp_server.analyze_coin_detail(ticker)
            else:
                result = await m.crypto_mcp_server.analyze_market(ticker)
            await message.reply(f"**코인 분석**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"코인 분석 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["포트폴리오", "portfolio", "보유", "자산"])
        and not any(w in p for w in ["시세", "가격"])
    ))
    async def handle_portfolio(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["차트", "그래프", "graph"]):
                result = await m.crypto_mcp_server.portfolio_graph()
            elif any(w in p for w in ["비율", "비중", "holdings"]):
                result = await m.crypto_mcp_server.holdings_chart()
            elif any(w in p for w in ["스냅샷", "저장", "snapshot"]):
                result = await m.crypto_mcp_server.record_portfolio_snapshot()
            else:
                result = await m.crypto_mcp_server.portfolio_summary()
            await message.reply(f"**포트폴리오**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"포트폴리오 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["거래내역", "거래기록", "최근거래", "recent", "체결"])
        and any(w in p for w in ["거래", "매매", "trade", "내역", "기록", "체결"])
    ))
    async def handle_trade_history(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.recent_trades()
            await message.reply(f"**최근 거래 내역**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"거래 내역 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["통계", "statistics", "수익률", "승률"])
        and any(w in p for w in ["매매", "거래", "trade", "수익", "손익"])
    ))
    async def handle_trade_stats(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["주간", "이번주", "week"]):
                period = "week"
            elif any(w in p for w in ["월간", "이번달", "month"]):
                period = "month"
            else:
                period = "all"
            result = await m.crypto_mcp_server.trade_statistics(period)
            await message.reply(f"**매매 통계 ({period})**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"매매 통계 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["대기", "미체결", "pending"])
        and any(w in p for w in ["주문", "order", "체결"])
    ))
    async def handle_pending_orders(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.pending_orders()
            await message.reply(f"**대기 주문**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"대기 주문 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["주문취소", "취소"])
        and any(w in p for w in ["주문", "order"])
    ))
    async def handle_cancel_order(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            uuid_match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', prompt.lower())
            if uuid_match:
                result = await m.crypto_mcp_server.cancel_my_order(uuid_match.group(0))
                await message.reply(f"```\n{result}\n```")
            else:
                await message.reply("취소할 주문 UUID를 지정해주세요.\n예: `주문 취소 abc12345-...`")
            return SENT
        except Exception as e:
            await message.reply(f"주문 취소 실패: {e}")
            return SENT

    @dispatcher.register(["자동매매", "자동거래", "auto", "봇매매"])
    async def handle_auto_trade(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["시작", "start", "켜", "on"]):
                result = await m.crypto_mcp_server.start_auto_trade("smart")
            elif any(w in p for w in ["중지", "stop", "꺼", "off", "멈춰"]):
                result = await m.crypto_mcp_server.stop_auto_trade()
            else:
                result = await m.crypto_mcp_server.auto_trade_status()
            await message.reply(f"**자동 매매**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"자동 매매 처리 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["모의", "실전", "드라이", "dry", "live"])
        and any(w in p for w in ["모드", "mode", "전환", "설정"])
    ))
    async def handle_trade_mode(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            mode = "live" if any(w in p for w in ["실전", "live"]) else "dry"
            result = await m.crypto_mcp_server.set_trade_mode(mode)
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"매매 모드 전환 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        (any(w in p for w in ["손절", "익절", "stoploss", "stop loss", "stop-loss",
                                "takeprofit", "take profit", "take-profit", "리스크"])
         or bool(re.search(r"stop.?loss|take.?profit", p)))
        and any(w in p for w in ["설정", "변경", "세팅"])
    ))
    async def handle_risk_params(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            nums = re.findall(r'[-+]?\d+(?:\.\d+)?', prompt)
            sl = float(nums[0]) if len(nums) >= 1 else -5.0
            tp = float(nums[1]) if len(nums) >= 2 else 10.0
            result = await m.crypto_mcp_server.set_risk_params(stop_loss=sl, take_profit=tp)
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"리스크 설정 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["관심", "watch", "감시"])
        and any(w in p for w in ["종목", "코인", "list", "목록", "설정"])
    ))
    async def handle_watchlist(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            tickers = re.findall(r'KRW-[A-Z]+|[A-Z]{3,}', prompt.upper())
            if tickers:
                formatted = ",".join(t if "KRW-" in t else f"KRW-{t}" for t in tickers)
                result = await m.crypto_mcp_server.set_watch_list(formatted)
            else:
                result = "관심 종목을 지정해주세요.\n예: `관심종목 BTC ETH XRP`"
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"관심종목 설정 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["알림", "alert"])
        and any(w in p for w in ["가격", "price", "이상", "이하", "도달"])
    ))
    async def handle_price_alert(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            ticker = bot._extract_ticker(p)
            nums = re.findall(r'[\d,]+(?:\.\d+)?', prompt.replace(",", ""))
            above = float(nums[0]) if len(nums) >= 1 else 0
            below = float(nums[1]) if len(nums) >= 2 else 0
            result = await m.crypto_mcp_server.set_price_alert(ticker, above=above, below=below)
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"가격 알림 설정 실패: {e}")
            return SENT

    @dispatcher.register(["트레일링", "trailing", "추적손절"])
    async def handle_trailing_stop(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            ticker = bot._extract_ticker(p)
            pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%?', prompt)
            trail_pct = float(pct_match.group(1)) if pct_match else 5.0
            result = await m.crypto_mcp_server.set_trailing_stop_tool(ticker, trail_pct)
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"트레일링 스탑 설정 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["스마트", "smart"])
        and any(w in p for w in ["매매", "trade", "매수", "설정", "모드"])
    ))
    async def handle_smart_trade(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["설정", "세팅", "모드"]):
                enabled = not any(w in p for w in ["끄", "off", "비활성"])
                result = await m.crypto_mcp_server.set_smart_mode(enabled=enabled)
            else:
                result = await m.crypto_mcp_server.smart_trade_now()
            await message.reply(f"**스마트 매매**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"스마트 매매 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["사이클", "cycle"])
        and any(w in p for w in ["실행", "run", "돌려"])
    ))
    async def handle_trade_cycle(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.run_trade_cycle()
            await message.reply(f"**매매 사이클**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"매매 사이클 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["안전", "safety", "한도"])
        and any(w in p for w in ["설정", "변경", "limit"])
    ))
    async def handle_safety_limits(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.set_safety_limits()
            await message.reply(f"```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"안전 한도 설정 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["보안", "security"])
        and any(w in p for w in ["상태", "status", "확인", "체크"])
    ))
    async def handle_security_status(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.security_status()
            await message.reply(f"**보안 상태**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"보안 상태 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["크립토", "crypto"])
        and any(w in p for w in ["도움", "help", "명령"])
    ))
    async def handle_crypto_help(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.crypto_mcp_server:
            return None
        try:
            result = await m.crypto_mcp_server.crypto_help()
            await message.reply(f"```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"크립토 도움말 실패: {e}")
            return SENT

    # ══════════════════════════════════════════
    # ── SC2 고급 ──
    # ══════════════════════════════════════════

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["로그내용", "로그읽기", "logfile"])
        or ("로그" in p and any(w in p for w in ["읽어", "내용", "보여줘", "열어"]))
    ))
    async def handle_sc2_log_content(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.sc2_mcp_server:
            return None
        try:
            tokens = prompt.strip().split()
            filename = next((t for t in tokens if "." in t and not t.startswith(".")), "")
            if filename:
                result = await m.sc2_mcp_server.read_log_content(filename)
            else:
                result = await m.sc2_mcp_server.list_bot_logs()
                result = "파일명을 지정하세요.\n예: `로그 읽어 game_2024.log`\n\n" + result
            await message.reply(f"**SC2 로그**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"로그 읽기 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["테스트게임", "연습게임"])
        or ("sc2" in p and any(w in p for w in ["테스트", "시작", "연습"]))
    ))
    async def handle_sc2_test_game(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.sc2_mcp_server:
            return None
        try:
            result = await m.sc2_mcp_server.run_sc2_test_game()
            await message.reply(f"**SC2 테스트 게임**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"SC2 테스트 게임 실행 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["공격성", "aggression", "어그로"])
        or ("sc2" in p and any(w in p for w in ["공격", "수비", "밸런스"]))
    ))
    async def handle_sc2_aggression(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.sc2_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["공격", "aggressive", "어그로"]):
                level = "aggressive"
            elif any(w in p for w in ["수비", "passive", "방어"]):
                level = "passive"
            else:
                level = "balanced"
            result = await m.sc2_mcp_server.set_aggression_level(level)
            await message.reply(f"**SC2 공격성**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"공격성 설정 실패: {e}")
            return SENT

    @dispatcher.register(["리플레이", "replay", "전적분석"])
    async def handle_sc2_replay(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.sc2_mcp_server or not hasattr(m.sc2_mcp_server, 'analyze_replay'):
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["목록", "list", "리스트"]):
                result = await m.sc2_mcp_server.list_replays()
            else:
                result = await m.sc2_mcp_server.analyze_replay()
            await message.reply(f"**SC2 리플레이**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"리플레이 분석 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["코칭", "coaching", "조언"])
        and any(w in p for w in ["sc2", "스타", "게임", "코칭"])
    ))
    async def handle_sc2_coaching(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.sc2_mcp_server or not hasattr(m.sc2_mcp_server, 'sc2_coaching_check'):
            return None
        try:
            result = await m.sc2_mcp_server.sc2_coaching_check()
            await message.reply(f"**SC2 코칭**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"코칭 분석 실패: {e}")
            return SENT

    @dispatcher.register(["래더", "ladder", "mmr", "랭킹"])
    async def handle_sc2_ladder(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.sc2_mcp_server or not hasattr(m.sc2_mcp_server, 'track_ladder'):
            return None
        try:
            p = prompt.lower().strip()
            tokens = p.replace("래더", "").replace("ladder", "").replace("mmr", "").replace("랭킹", "").strip().split()
            player = tokens[0] if tokens else ""
            server = "kr"
            for t in tokens:
                if t.lower() in ["kr", "us", "eu", "cn"]:
                    server = t.lower()
            result = await m.sc2_mcp_server.track_ladder(player, server)
            await message.reply(f"**SC2 래더**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"래더 조회 실패: {e}")
            return SENT

    # ══════════════════════════════════════════
    # ── 시스템 고급 ──
    # ══════════════════════════════════════════

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["mcp", "도구목록", "tool"])
        and any(w in p for w in ["목록", "list", "도구", "tool"])
    ))
    async def handle_mcp_tools(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            result = await m.system_mcp_server.list_mcp_tools()
            await message.reply(f"**MCP 도구 목록**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"MCP 도구 목록 조회 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["스마트홈", "smarthome", "iot"])
        or (any(w in p for w in ["조명", "에어컨", "tv", "전등"])
            and any(w in p for w in ["켜", "꺼", "on", "off", "설정"]))
    ))
    async def handle_smart_home(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            device = "light"
            action = "status"
            for kw_d, dev in [("조명", "light"), ("전등", "light"), ("에어컨", "ac"), ("tv", "tv"), ("티비", "tv")]:
                if kw_d in p:
                    device = dev
                    break
            if any(w in p for w in ["켜", "on"]):
                action = "on"
            elif any(w in p for w in ["꺼", "off"]):
                action = "off"
            result = await m.system_mcp_server.smart_home_control(device, action)
            await message.reply(f"**스마트홈**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            await message.reply(f"스마트홈 제어 실패: {e}")
            return SENT

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["파일", "file", "찾기"])
    ))
    async def handle_file_search(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            tokens = prompt.strip().split()
            filtered = [t for t in tokens if t.lower() not in
                        ("파일", "file", "찾기", "검색", "찾아", "찾아줘", "보여줘", "목록")]
            directory = "."
            pattern = "*"
            for t in filtered:
                if "/" in t or "\\" in t or ":" in t:
                    directory = t
                elif "*" in t or "?" in t or "." in t:
                    pattern = t
                elif t:
                    pattern = f"*{t}*"
            if ".." in directory or not m._is_path_allowed(directory):
                await message.reply("보안상 허용되지 않은 경로입니다. 프로젝트 폴더 또는 홈 디렉토리만 검색 가능합니다.")
                return SENT
            result = await m.system_mcp_server.search_files(directory, pattern)
            await message.reply(f"**파일 검색 결과**\n```\n{_truncate(result)}\n```")
            return SENT
        except Exception as e:
            logger.error(f"File search: {e}")
            await message.reply(f"파일 검색 실패: {e}")
            return SENT

    # ── 프로그램 실행 ──
    _prog_names_kr = {"메모장", "노트패드", "계산기", "탐색기", "그림판", "페인트",
                      "크롬", "구글", "파이어폭스", "엣지", "터미널", "코드",
                      "작업관리자", "캡처도구", "파워셸"}
    _prog_names_en = {"notepad", "calc", "explorer", "mspaint", "cmd",
                      "powershell", "code", "chrome", "firefox", "msedge",
                      "taskmgr", "snip", "winterm", "edge", "vscode"}
    _prog_map = {
        "메모장": "notepad", "노트패드": "notepad",
        "계산기": "calc", "탐색기": "explorer",
        "그림판": "mspaint", "페인트": "mspaint",
        "크롬": "chrome", "구글": "chrome",
        "파이어폭스": "firefox", "엣지": "msedge", "edge": "msedge",
        "터미널": "winterm", "코드": "code", "vscode": "code",
        "작업관리자": "taskmgr", "캡처도구": "snip",
        "cmd": "cmd", "파워셸": "powershell", "powershell": "powershell",
    }

    @dispatcher.register(match_fn=lambda p: (
        (any(w in p for w in ["열어", "run ", "open "])
         or ("실행" in p and (any(name in p for name in _prog_names_kr) or any(name in p for name in _prog_names_en))))
    ))
    async def handle_run_program(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            tokens = prompt.strip().split()
            prog_name = None
            for t in tokens:
                tl = t.lower().rstrip("을를이가해줘좀")
                if tl in _prog_map:
                    prog_name = _prog_map[tl]
                    break
                if tl in _prog_names_en:
                    prog_name = tl
                    break
            if not prog_name:
                allowed_kr = ", ".join(sorted(_prog_map.keys()))
                await message.reply(f"실행할 프로그램을 지정해주세요.\n사용 가능: {allowed_kr}")
                return SENT
            result = await m.system_mcp_server.run_program(prog_name)
            await message.reply(f"**프로그램 실행**\n```\n{result}\n```")
            return SENT
        except Exception as e:
            logger.error(f"Run program: {e}")
            await message.reply(f"프로그램 실행 실패: {e}")
            return SENT

    # ── 예약 작업 ──
    @dispatcher.register(["예약", "스케줄", "schedule"])
    async def handle_schedule(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.system_mcp_server:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["목록", "리스트", "list", "조회"]):
                result = await m.system_mcp_server.list_scheduled_tasks()
                await message.reply(f"**예약 작업 목록**\n```\n{result}\n```")
                return SENT
            elif any(w in p for w in ["취소", "삭제", "cancel", "제거"]):
                tid_match = re.search(r'[a-f0-9]{8}', p)
                if tid_match:
                    result = await m.system_mcp_server.cancel_scheduled_task(tid_match.group(0))
                    await message.reply(f"```\n{result}\n```")
                else:
                    await message.reply("취소할 작업 ID를 지정해주세요.\n예: `예약 취소 a1b2c3d4`")
                return SENT
            else:
                await message.reply(
                    "**예약 작업 명령어**\n"
                    "`예약 목록` - 현재 예약된 작업 조회\n"
                    "`예약 취소 [작업ID]` - 작업 취소\n\n"
                    "새 작업 예약은 AI에게 요청하세요:\n"
                    "예: `매 5분마다 시스템 상태 체크 예약해줘`"
                )
                return SENT
        except Exception as e:
            logger.error(f"Schedule: {e}")
            await message.reply(f"예약 작업 처리 실패: {e}")
            return SENT

    # ══════════════════════════════════════════
    # ── Google Calendar ──
    # ══════════════════════════════════════════

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["일정", "calendar"])
        and not any(w in p for w in ["예약", "schedule", "스케줄"])
    ))
    async def handle_calendar(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.calendar_integration:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["추가", "만들", "생성", "등록", "create"]):
                return None  # AI에게 위임
            elif any(w in p for w in ["이번주", "주간", "upcoming", "다음"]):
                result = await m.calendar_integration.get_upcoming_events(7)
            else:
                result = await m.calendar_integration.get_today_events()
            await message.reply(f"**일정**\n{result}")
            return SENT
        except Exception as e:
            await message.reply(f"일정 조회 실패: {e}")
            return SENT

    # ══════════════════════════════════════════
    # ── Notion ──
    # ══════════════════════════════════════════

    @dispatcher.register(match_fn=lambda p: (
        any(w in p for w in ["메모", "노트", "notion", "기록"])
        and not any(w in p for w in ["메모리", "기억"])
    ))
    async def handle_notion(prompt, message, bot, user_id, **kw):
        m = _mod()
        if not m.notion_integration:
            return None
        try:
            p = prompt.lower().strip()
            if any(w in p for w in ["저장", "기록해", "적어", "save", "write"]):
                text = p
                for k in ["메모", "노트", "저장", "기록해", "적어", "save", "write", "notion"]:
                    text = text.replace(k, "")
                text = text.strip()
                if ":" in text:
                    title, content = text.split(":", 1)
                else:
                    title = text[:30]
                    content = text
                result = await m.notion_integration.save_note(title.strip(), content.strip())
                await message.reply(result)
                return SENT
            elif any(w in p for w in ["검색", "찾아", "search"]):
                query = p
                for k in ["메모", "노트", "검색", "찾아", "search", "notion"]:
                    query = query.replace(k, "")
                result = await m.notion_integration.search_notes(query.strip())
                await message.reply(result)
                return SENT
            else:
                result = await m.notion_integration.list_recent_notes()
                await message.reply(result)
                return SENT
        except Exception as e:
            await message.reply(f"Notion 처리 실패: {e}")
            return SENT

    logger.info(f"[keyword_handlers] {dispatcher.handler_count}개 키워드 핸들러 등록 완료")
