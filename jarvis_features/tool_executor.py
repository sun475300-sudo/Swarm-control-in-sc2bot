# -*- coding: utf-8 -*-
"""
ToolExecutor — discord_jarvis.py에서 추출된 도구 디스패치 엔진

기존 _execute_tool() 메서드를 독립 모듈로 분리하여:
- 단위 테스트 가능
- 도구 추가/수정 시 봇 코드 수정 불필요
- 관심사 분리 (봇 이벤트 핸들링 vs 도구 실행)
"""

import asyncio
import logging
import os
import subprocess
import time

logger = logging.getLogger("JarvisBot.ToolExecutor")

# 위험한 도구 — 관리자만 실행 가능
DANGEROUS_TOOLS = frozenset({
    "ssh_execute", "kill_process", "pc_control", "run_program",
    "restart_bot", "execute_terminal_command", "execute_python_code",
    "pc_mouse_click", "write_file", "edit_file",
    "openclaw_coding", "openclaw_browser", "openclaw_cron", "openclaw_email",
})


class ToolExecutor:
    """도구 실행기 — 도구명+인자를 받아 적절한 핸들러를 디스패치한다."""

    def __init__(self, bot):
        """
        Args:
            bot: JarvisBot 인스턴스 (memory, get_uptime 등 접근)
        """
        self.bot = bot

    async def execute(self, name: str, args: str, message, user_id: str) -> str:
        """
        도구명과 인자를 받아 해당 도구 실행. 결과 문자열 반환.

        Args:
            name: 도구 이름
            args: 도구 인자 (문자열)
            message: Discord 메시지 객체
            user_id: 사용자 ID

        Returns:
            실행 결과 문자열
        """
        # Lazy import — 순환 참조 방지, 항상 최신 모듈 상태 참조
        import discord_jarvis as _mod

        logger.info(f"Tool Exec: {name}(***)")

        # Authorization check for dangerous tools
        if name in DANGEROUS_TOOLS:
            if not _mod._is_authorized(message):
                return f"권한 부족: '{name}' 도구는 관리자만 사용할 수 있습니다."

        _tool_start = time.time()
        _tool_success = True
        _tool_error = ""
        try:
            # ── ToolDispatcher (점진적 이관 — 등록된 도구 우선 실행) ──
            if _mod.tool_dispatcher:
                result = await _mod.tool_dispatcher.dispatch(
                    name=name, args=args, message=message, user_id=user_id, bot=self.bot,
                )
                if result is not None:
                    return result

            if name == "search_web":
                if _mod.web_tools:
                    return await asyncio.to_thread(_mod.web_tools.search_web, args)
                return "web_tools 모듈을 불러올 수 없습니다."
            elif name == "get_weather":
                city = args.strip() if args.strip() else "서울"
                if _mod.web_tools and hasattr(_mod.web_tools, 'get_weather'):
                    return await asyncio.to_thread(_mod.web_tools.get_weather, city)
                if _mod.system_mcp_server:
                    return await _mod.system_mcp_server.weather(city)
                return f"{city} 날씨 조회 모듈을 사용할 수 없습니다."
            elif name == "get_sc2_stats":
                if _mod.sc2_mcp_server:
                    return await _mod.sc2_mcp_server.sc2_bot_stats()
                return "SC2 모듈을 불러올 수 없습니다."
            elif name == "get_system_status":
                if _mod.system_mcp_server:
                    return await _mod.system_mcp_server.system_resources()
                return "시스템 모듈을 불러올 수 없습니다."
            elif name == "get_crypto_price":
                if _mod.crypto_mcp_server:
                    return await _mod.crypto_mcp_server.coin_price(args)
                return "크립토 모듈을 불러올 수 없습니다."
            elif name == "scan_screen":
                return await self.bot._analyze_screen()
            elif name == "remember":
                if not self.bot.memory:
                    return "메모리 모듈을 불러올 수 없습니다."
                if "|" in args:
                    k, v = args.split("|", 1)
                else:
                    k, v = "info", args
                self.bot.memory.update_user_memory(user_id, k, v)
                return "Saved."
            elif name == "check_git":
                cmd = ["git", "status"]
                allowed_args = args.split()
                if allowed_args:
                    subcmd = allowed_args[0]
                    if subcmd in ["status", "log", "diff", "show", "branch"]:
                        cmd = ["git"] + allowed_args
                    else:
                        return "Blocked Git command."
                try:
                    res = await asyncio.to_thread(
                        subprocess.check_output, cmd,
                        encoding="utf-8", stderr=subprocess.STDOUT,
                        cwd=os.path.dirname(os.path.abspath(_mod.__file__))
                    )
                    if len(res) > 1500:
                        res = res[:1500] + "\n...(truncated)"
                    return f"Git Output:\n{res}"
                except subprocess.CalledProcessError as e:
                    return f"Git Error: {e.output}"
            elif name == "get_fortune":
                if _mod.web_tools and hasattr(_mod.web_tools, 'get_daily_fortune'):
                    return await asyncio.to_thread(_mod.web_tools.get_daily_fortune)
                return "운세 모듈을 불러올 수 없습니다."
            elif name == "translate":
                if _mod.system_mcp_server:
                    parts = args.split("|", 2) if "|" in args else [args]
                    text = parts[0].strip()
                    if len(parts) > 1:
                        target = parts[1].strip()
                        source = parts[2].strip() if len(parts) > 2 else ("ko" if target == "en" else "en")
                    else:
                        target, source = _mod._detect_language_direction(text)
                    return await _mod.system_mcp_server.translate(text, target, source)
                return "번역 모듈을 불러올 수 없습니다."
            elif name == "calculate":
                if _mod.system_mcp_server:
                    return await _mod.system_mcp_server.calculate(args)
                return "계산기 모듈을 불러올 수 없습니다."
            elif name == "list_features":
                return (
                    "**JARVIS 사용 가능 기능:**\n"
                    "• 날씨, 검색, 시세, 김프, 공포/탐욕, 시장, 호가창\n"
                    "• 전적, 게임상황, 로그, 테스트게임, 공격성\n"
                    "• 시스템, 프로세스, 캡처, 웹캠, 파일검색\n"
                    "• 운세, 번역, 계산, 속도측정, 프로그램실행\n"
                    "• 네트워크, Git, 브리핑, SSH, MCP도구\n"
                    "• 포트폴리오, 거래내역, 매매통계, 자동매매\n"
                    "• 스마트매매, 손절/익절, 관심종목, 가격알림\n"
                    "• 스마트홈, 예약작업, 메모리(기억)\n"
                    "• **!scan** - 화면 AI 분석 (Gemini Vision)\n"
                    "• **!monitor on/off** - 화면 모니터링 (3분 주기)\n"
                    "• **!cctv start/stop/snap** - 웹캠 CCTV\n"
                    "• 볼륨/밝기/절전/잠금/종료 - PC 원격제어\n"
                    "• 리플레이/코칭/래더 - SC2 고급 분석\n"
                    "• 일정(Google Calendar)/메모(Notion) - 비서"
                )
            # ── 새 AI 도구들 ──
            elif name == "portfolio":
                if _mod.crypto_mcp_server:
                    return await _mod.crypto_mcp_server.portfolio_summary()
                return "크립토 모듈을 불러올 수 없습니다."
            elif name == "recent_trades":
                if _mod.crypto_mcp_server:
                    return await _mod.crypto_mcp_server.recent_trades()
                return "크립토 모듈을 불러올 수 없습니다."
            elif name == "trade_stats":
                if _mod.crypto_mcp_server:
                    period = args.strip() if args.strip() else "all"
                    return await _mod.crypto_mcp_server.trade_statistics(period)
                return "크립토 모듈을 불러올 수 없습니다."
            elif name == "analyze_coin":
                if _mod.crypto_mcp_server:
                    ticker = args.strip() if args.strip() else "KRW-BTC"
                    return await _mod.crypto_mcp_server.analyze_coin_detail(ticker)
                return "크립토 모듈을 불러올 수 없습니다."
            elif name == "auto_trade":
                if _mod.crypto_mcp_server:
                    cmd = args.strip().lower()
                    if cmd == "start":
                        return await _mod.crypto_mcp_server.start_auto_trade()
                    elif cmd == "stop":
                        return await _mod.crypto_mcp_server.stop_auto_trade()
                    else:
                        return await _mod.crypto_mcp_server.auto_trade_status()
                return "크립토 모듈을 불러올 수 없습니다."
            elif name == "pending_orders":
                if _mod.crypto_mcp_server:
                    return await _mod.crypto_mcp_server.pending_orders()
                return "크립토 모듈을 불러올 수 없습니다."
            elif name == "price_alert":
                parts = args.split("|", 1) if "|" in args else [args.strip(), ""]
                coin_arg = parts[0].strip().upper()
                value_arg = parts[1].strip() if len(parts) > 1 else ""
                async with _mod._price_alert_lock:
                    if coin_arg == "LIST":
                        user_alerts = _mod._price_alert_store.get(user_id, {})
                        if not user_alerts:
                            return "등록된 가격 알림이 없습니다."
                        lines = [f"{t.replace('KRW-','')}: {p:,.0f} KRW" for t, p in user_alerts.items()]
                        return "현재 가격 알림:\n" + "\n".join(lines)
                    ticker = f"KRW-{coin_arg}" if not coin_arg.startswith("KRW-") else coin_arg
                    if value_arg.lower() == "clear":
                        if user_id in _mod._price_alert_store and ticker in _mod._price_alert_store[user_id]:
                            del _mod._price_alert_store[user_id][ticker]
                            if not _mod._price_alert_store[user_id]:
                                del _mod._price_alert_store[user_id]
                            return f"{coin_arg} 가격 알림이 해제되었습니다."
                        return f"{coin_arg} 가격 알림이 없습니다."
                    try:
                        target_price = float(value_arg.replace(",", ""))
                    except ValueError:
                        return "형식: TOOL:price_alert:BTC|60000000 (설정) / list (목록) / BTC|clear (해제)"
                    MAX_ALERTS_PER_USER = 50
                    MAX_TOTAL_ALERTS = 500
                    user_alerts = _mod._price_alert_store.get(user_id, {})
                    if len(user_alerts) >= MAX_ALERTS_PER_USER:
                        return f"가격 알림 한도 초과: 유저당 최대 {MAX_ALERTS_PER_USER}개"
                    total_alerts = sum(len(v) for v in _mod._price_alert_store.values())
                    if total_alerts >= MAX_TOTAL_ALERTS:
                        return f"전체 가격 알림 한도 초과: 최대 {MAX_TOTAL_ALERTS}개"
                    _mod._price_alert_store.setdefault(user_id, {})[ticker] = target_price
                    return f"{coin_arg} 가격 알림 설정: {target_price:,.0f} KRW 도달 시 DM 알림"
            elif name == "run_program":
                if _mod.system_mcp_server:
                    return await _mod.system_mcp_server.run_program(args.strip())
                return "시스템 모듈을 불러올 수 없습니다."
            elif name == "kill_process":
                if _mod.system_mcp_server:
                    try:
                        pid = int(args.strip())
                        return await _mod.system_mcp_server.kill_process(pid)
                    except ValueError:
                        return "PID는 숫자여야 합니다."
                return "시스템 모듈을 불러올 수 없습니다."
            elif name == "search_files":
                if _mod.system_mcp_server:
                    parts = args.split("|", 1) if "|" in args else [".", args.strip()]
                    directory = parts[0].strip()
                    pattern = parts[1].strip() if len(parts) > 1 else "*"
                    if not _mod._is_path_allowed(directory):
                        return "보안 차단: 허용되지 않은 경로입니다. 프로젝트 폴더 또는 홈 디렉토리만 검색 가능합니다."
                    return await _mod.system_mcp_server.search_files(directory, pattern)
                return "시스템 모듈을 불러올 수 없습니다."
            elif name == "ssh_execute":
                if _mod.system_mcp_server:
                    parts = args.split("|", 1) if "|" in args else [args.strip(), "echo connected"]
                    host_part = parts[0].strip()
                    command = parts[1].strip() if len(parts) > 1 else "echo connected"
                    user, host = ("", host_part)
                    if "@" in host_part:
                        user, host = host_part.split("@", 1)
                    return await _mod.system_mcp_server.ssh_execute(host, command, user=user)
                return "시스템 모듈을 불러올 수 없습니다."
            # ── OpenClaw Agentic Tools ──
            elif name == "execute_terminal_command":
                if _mod.agentic_mcp_server:
                    return await _mod.agentic_mcp_server.execute_terminal_command(args)
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "execute_python_code":
                is_safe, reason = _mod._ast_check_python_code(args)
                if not is_safe:
                    return f"보안 차단: {reason}. 이 코드 패턴은 허용되지 않습니다."
                if _mod.agentic_mcp_server:
                    return await _mod.agentic_mcp_server.execute_python_code(args)
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "pc_mouse_move":
                if _mod.agentic_mcp_server:
                    parts = args.split("|")
                    try:
                        x = int(parts[0].strip())
                        y = int(parts[1].strip())
                        duration = float(parts[2].strip()) if len(parts) > 2 else 0.5
                        return await _mod.agentic_mcp_server.computer_use_mouse_move(x, y, duration)
                    except (ValueError, IndexError):
                        return "좌표값이 올바르지 않습니다. (x|y)"
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "pc_mouse_click":
                if _mod.agentic_mcp_server:
                    parts = args.split("|")
                    btn = parts[0].strip() if len(parts) > 0 and parts[0].strip() else "left"
                    clicks = int(parts[1].strip()) if len(parts) > 1 else 1
                    return await _mod.agentic_mcp_server.computer_use_mouse_click(button=btn, clicks=clicks)
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "pc_keyboard_type":
                if _mod.agentic_mcp_server:
                    return await _mod.agentic_mcp_server.computer_use_keyboard_type(args)
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "pc_keyboard_press":
                if _mod.agentic_mcp_server:
                    return await _mod.agentic_mcp_server.computer_use_keyboard_press(args)
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "read_file":
                if _mod.agentic_mcp_server:
                    return await _mod.agentic_mcp_server.read_file(args.strip())
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "write_file":
                if _mod.agentic_mcp_server:
                    parts = args.split("|", 1) if "|" in args else [args.strip(), ""]
                    path = parts[0].strip()
                    content = parts[1].strip() if len(parts) > 1 else ""
                    return await _mod.agentic_mcp_server.write_file(path, content)
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "edit_file":
                if _mod.agentic_mcp_server:
                    parts = args.split("|", 2)
                    path = parts[0].strip() if len(parts) > 0 else ""
                    old_t = parts[1].strip() if len(parts) > 1 else ""
                    new_t = parts[2].strip() if len(parts) > 2 else ""
                    return await _mod.agentic_mcp_server.edit_file(path, old_t, new_t)
                return "Agentic 모듈을 불러올 수 없습니다."
            elif name == "list_dir":
                if _mod.agentic_mcp_server:
                    path = args.strip() if args.strip() else "."
                    return await _mod.agentic_mcp_server.list_directory(path)
                return "Agentic 모듈을 불러올 수 없습니다."
            # ── Phase 3: PC 제어 ──
            elif name == "pc_control":
                if _mod.system_mcp_server and hasattr(_mod.system_mcp_server, 'pc_control'):
                    parts = args.split("|", 1) if "|" in args else [args.strip(), ""]
                    action = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""
                    return await _mod.system_mcp_server.pc_control(action, value)
                return "PC 제어 모듈을 불러올 수 없습니다."
            # ── Phase 4: SC2 고급 ──
            elif name == "analyze_replay":
                if _mod.sc2_mcp_server and hasattr(_mod.sc2_mcp_server, 'analyze_replay'):
                    return await _mod.sc2_mcp_server.analyze_replay(args.strip() if args.strip() else None)
                return "SC2 리플레이 모듈을 불러올 수 없습니다."
            elif name == "list_replays":
                if _mod.sc2_mcp_server and hasattr(_mod.sc2_mcp_server, 'list_replays'):
                    return await _mod.sc2_mcp_server.list_replays()
                return "SC2 리플레이 모듈을 불러올 수 없습니다."
            elif name == "sc2_coaching":
                if _mod.sc2_mcp_server and hasattr(_mod.sc2_mcp_server, 'sc2_coaching_check'):
                    return await _mod.sc2_mcp_server.sc2_coaching_check()
                return "SC2 코칭 모듈을 불러올 수 없습니다."
            elif name == "track_ladder":
                if _mod.sc2_mcp_server and hasattr(_mod.sc2_mcp_server, 'track_ladder'):
                    parts = args.split("|", 1) if "|" in args else [args.strip(), "kr"]
                    player = parts[0].strip()
                    server = parts[1].strip() if len(parts) > 1 else "kr"
                    return await _mod.sc2_mcp_server.track_ladder(player, server)
                return "SC2 래더 모듈을 불러올 수 없습니다."
            # ── Phase 5: Calendar ──
            elif name == "get_today_events":
                if _mod.calendar_integration:
                    return await _mod.calendar_integration.get_today_events()
                return "캘린더 모듈을 불러올 수 없습니다."
            elif name == "get_upcoming_events":
                if _mod.calendar_integration:
                    days = int(args.strip()) if args.strip().isdigit() else 7
                    return await _mod.calendar_integration.get_upcoming_events(days)
                return "캘린더 모듈을 불러올 수 없습니다."
            elif name == "create_event":
                if _mod.calendar_integration:
                    parts = args.split("|")
                    title = parts[0].strip() if len(parts) > 0 else "새 일정"
                    start = parts[1].strip() if len(parts) > 1 else ""
                    end = parts[2].strip() if len(parts) > 2 else ""
                    return await _mod.calendar_integration.create_event(title, start, end)
                return "캘린더 모듈을 불러올 수 없습니다."
            # ── Phase 5: Notion ──
            elif name == "save_note":
                if _mod.notion_integration:
                    parts = args.split("|", 1) if "|" in args else [args.strip()[:30], args.strip()]
                    title = parts[0].strip()
                    content = parts[1].strip() if len(parts) > 1 else title
                    return await _mod.notion_integration.save_note(title, content)
                return "Notion 모듈을 불러올 수 없습니다."
            elif name == "search_notes":
                if _mod.notion_integration:
                    return await _mod.notion_integration.search_notes(args.strip())
                return "Notion 모듈을 불러올 수 없습니다."
            elif name == "list_notes":
                if _mod.notion_integration:
                    return await _mod.notion_integration.list_recent_notes()
                return "Notion 모듈을 불러올 수 없습니다."
            # ── 신규 도구: 봇 상태 ──
            elif name == "bot_status":
                uptime = self.bot.get_uptime()
                model_info = []
                for m, s in _mod._model_stats.items():
                    rate = (s["success"] / s["calls"] * 100) if s["calls"] > 0 else 0
                    avg_ms = (s["total_ms"] / s["success"]) if s["success"] > 0 else 0
                    model_info.append(f"  {m}: {rate:.0f}% 성공 ({s['calls']}회, 평균 {avg_ms:.0f}ms)")

                tool_summary = ""
                if _mod.get_tool_registry:
                    tool_summary = f"\n**도구 사용 통계:**\n{_mod.get_tool_registry().get_summary()}"

                return (
                    f"**JARVIS 상태**\n"
                    f"• 가동시간: {uptime}\n"
                    f"• 처리 메시지: {self.bot._message_count:,}개\n"
                    f"• 실행 명령어: {self.bot._command_count:,}개\n"
                    f"• 메모리 사용자: {len(self.bot.memory.get_all_users()) if self.bot.memory and hasattr(self.bot.memory, 'get_all_users') else '?'}명\n"
                    f"**AI 모델 통계:**\n" + ("\n".join(model_info) if model_info else "  통계 없음")
                    + tool_summary
                )
            # ── 신규 도구: 메모리 검색 ──
            elif name == "search_memory":
                if not self.bot.memory:
                    return "메모리 모듈을 불러올 수 없습니다."
                if self.bot.memory and hasattr(self.bot.memory, 'search_memory'):
                    results = self.bot.memory.search_memory(args)
                    if results:
                        lines = [f"• [{r['user_id']}] {r['key']}: {r['value']}" for r in results[:10]]
                        return "메모리 검색 결과:\n" + "\n".join(lines)
                    return "검색 결과가 없습니다."
                return "메모리 모듈을 불러올 수 없습니다."
            # ── 신규 도구: 메모리 백업 ──
            elif name == "backup_memory":
                if self.bot.memory and hasattr(self.bot.memory, 'backup'):
                    return self.bot.memory.backup()
                return "메모리 모듈을 불러올 수 없습니다."

            # ══════════════════════════════════════════════════════
            # OpenClaw Tools (AI → Discord 자동 호출)
            # ══════════════════════════════════════════════════════
            elif name.startswith("openclaw_"):
                try:
                    from utils.openclaw_helper import get_openclaw_helper
                    oc = get_openclaw_helper()
                except ImportError:
                    return "OpenClaw 헬퍼를 불러올 수 없습니다."
                if not oc.available:
                    return "OpenClaw CLI가 설치되어 있지 않습니다."

                skill_map = {
                    "openclaw_weather": lambda a: f"Get weather for {a.strip() or '서울'}",
                    "openclaw_youtube": lambda a: f"Search YouTube: {a.strip()}",
                    "openclaw_summarize": lambda a: f"Summarize: {a.strip()}",
                    "openclaw_news": lambda a: f"Get latest news about {a.strip() or 'technology'}",
                    "openclaw_exchange": lambda a: f"Get exchange rate {a.replace('|', ' to ')}" if a.strip() else "Get USD to KRW exchange rate",
                    "openclaw_stock": lambda a: f"Analyze stock {a.strip() or 'AAPL'} with full scoring",
                    "openclaw_image_gen": lambda a: f"Generate image: {a.strip()}",
                    "openclaw_email": lambda a: f"Send email to {a}" if "|" in a else f"Check emails: {a}",
                    "openclaw_notion": lambda a: f"Notion: {a.replace('|', ' - ')}",
                    "openclaw_github": lambda a: f"GitHub {a.replace('|', ' for repo ')}",
                    "openclaw_coding": lambda a: f"Write code: {a.strip()}",
                    "openclaw_browser": lambda a: f"Browser: open {a.split('|')[0].strip()}" if a.strip() else "Browser status",
                    "openclaw_cron": lambda a: f"Cron: {a.replace('|', ' ')}",
                    "openclaw_transcribe": lambda a: f"Transcribe audio: {a.strip()}",
                    "openclaw_calendar": lambda a: f"Calendar: {'show today events' if a.strip() in ('today', 'none', '') else a.strip()}",
                }
                msg_fn = skill_map.get(name)
                if msg_fn is None:
                    return f"Unknown OpenClaw tool: {name}"
                skill_msg = msg_fn(args)
                oc.record_skill_usage(name)
                timeout = 90 if name in ("openclaw_coding", "openclaw_image_gen", "openclaw_transcribe") else 45
                return await oc.run_skill(skill_msg, timeout=timeout)

            return "Unknown Tool"
        except Exception as e:
            _tool_success = False
            _tool_error = str(e)[:200]
            return f"Tool Error: {e}"
        finally:
            if _mod.get_tool_registry:
                _elapsed = (time.time() - _tool_start) * 1000
                _mod.get_tool_registry().record_call(name, user_id, _tool_success, _elapsed, _tool_error)
