"""
JARVIS 종합 일일 브리핑 (Daily Briefing)

날씨 + 운세 + 캘린더 + 뉴스 + 포트폴리오 + SC2 전적 + 시스템 상태
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("daily_briefing")

# 요일 한국어 매핑
_WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


class DailyBriefing:
    """종합 일일 브리핑 생성기"""

    def __init__(self):
        self._project_root = Path(__file__).parent
        self._city = os.environ.get("BRIEFING_CITY", "광주")
        self._birth_year = int(os.environ.get("OWNER_BIRTH_YEAR", "1995"))

    def _get_weather_section(self) -> str:
        """날씨 섹션"""
        try:
            from morning_briefing_helper import get_weather
            w = get_weather(self._city)
            if not w or "error" in w:
                err = w.get("error", "알 수 없음") if w else "모듈 오류"
                return f"🌤️ **날씨** ({self._city})\n  조회 실패: {err}"
            lines = [
                f"🌤️ **날씨** ({w.get('city', self._city)})",
                f"  {w['icon']} {w['condition']} | 기온: {w['temp']}°C",
                f"  💡 {w['advice']}",
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"날씨 로드 실패: {e}")
            return f"🌤️ **날씨** — 조회 실패"

    def _get_fortune_section(self) -> str:
        """운세 섹션"""
        try:
            from morning_briefing_helper import get_fortune
            f = get_fortune(self._birth_year)
            if not f:
                return "🔮 **오늘의 운세** — 조회 실패"
            lines = [
                f"🔮 **오늘의 운세**",
                f"  {f['desc']}",
                f"  📝 {f['advice']}",
                f"  🎨 행운의 색: {f['color']}",
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"운세 로드 실패: {e}")
            return "🔮 **오늘의 운세** — 조회 실패"

    def _get_calendar_section(self) -> str:
        """캘린더 섹션 (동기 - 간략 표시)"""
        return "📅 **일정** — `!briefing` 또는 비동기 호출 시 표시"

    async def _get_calendar_section_async(self) -> str:
        """캘린더 섹션 (비동기 - 실제 조회)"""
        try:
            from calendar_integration import CalendarIntegration
            cal = CalendarIntegration()
            result = await cal.get_today_events()
            return f"📅 **일정**\n{result}"
        except ImportError:
            return "📅 **일정** — 캘린더 모듈 미설치"
        except Exception as e:
            logger.error(f"캘린더 로드 실패: {e}")
            return "📅 **일정** — 조회 실패"

    def _get_news_section(self) -> str:
        """뉴스 섹션"""
        try:
            from morning_briefing_helper import get_google_news
            headlines = get_google_news(limit=3)
            if not headlines:
                return "📰 **뉴스** — 조회 실패"
            lines = ["📰 **주요 뉴스**"]
            for i, h in enumerate(headlines, 1):
                lines.append(f"  {i}. {h}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"뉴스 로드 실패: {e}")
            return "📰 **뉴스** — 조회 실패"

    def _get_portfolio_section(self) -> str:
        """암호화폐 포트폴리오 섹션"""
        try:
            portfolio_file = self._project_root / "crypto_trading" / "data" / "portfolio_history.json"
            if not portfolio_file.exists():
                return "💰 **포트폴리오** — 데이터 없음"

            with open(portfolio_file, "r", encoding="utf-8") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    return "💰 **포트폴리오** — 데이터 파싱 실패"

            if not history or not isinstance(history, list):
                return "💰 **포트폴리오** — 데이터 없음"

            latest = history[-1]
            # 실제 필드명: total_value_krw (total_krw 아님)
            total = latest.get("total_value_krw", latest.get("total_krw", 0))
            holdings = latest.get("holdings", {})

            lines = ["💰 **암호화폐 포트폴리오**"]
            lines.append(f"  총 자산: {total:,.0f} KRW")

            # 전일 대비 수익률
            if len(history) >= 2:
                prev = history[-2]
                prev_total = prev.get("total_value_krw", prev.get("total_krw", 0))
                if prev_total > 0:
                    pnl = total - prev_total
                    pnl_pct = (pnl / prev_total) * 100
                    sign = "+" if pnl >= 0 else ""
                    lines.append(f"  일일 손익: {sign}{pnl:,.0f} KRW ({sign}{pnl_pct:.2f}%)")

            # 보유 종목
            if isinstance(holdings, dict) and holdings:
                lines.append(f"  보유 종목: {len(holdings)}개")
                for coin, info in list(holdings.items())[:5]:
                    if isinstance(info, dict):
                        amt = info.get("amount", info.get("balance", "?"))
                        lines.append(f"    • {coin}: {amt}")
            elif isinstance(holdings, list) and holdings:
                lines.append(f"  보유 종목: {len(holdings)}개")

            # 오늘 거래 수
            trade_log_file = self._project_root / "crypto_trading" / "data" / "trade_log.json"
            if trade_log_file.exists():
                with open(trade_log_file, "r", encoding="utf-8") as f:
                    try:
                        trades = json.load(f)
                        today = datetime.now().strftime("%Y-%m-%d")
                        if isinstance(trades, list):
                            cnt = sum(1 for t in trades if isinstance(t, dict) and t.get("timestamp", "").startswith(today))
                            lines.append(f"  오늘 거래: {cnt}건")
                    except json.JSONDecodeError as je:
                        # P3-9: 파싱 실패 경고 — 브리핑에 표시
                        logger.warning(f"거래 로그 파싱 실패: {je}")
                        lines.append("  오늘 거래: ⚠️ 데이터 손상")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"포트폴리오 로드 실패: {e}")
            return "💰 **포트폴리오** — 조회 실패"

    def _get_sc2_section(self) -> str:
        """SC2 봇 전적 섹션"""
        try:
            bot_log = self._project_root / "wicked_zerg_challenger" / "logs" / "bot.log"
            if not bot_log.exists():
                return "🎮 **SC2 봇** — 로그 없음"

            wins = 0
            losses = 0
            with open(bot_log, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    lower_line = line.lower()
                    if "victory" in lower_line or "result: win" in lower_line:
                        wins += 1
                    elif "defeat" in lower_line or "result: loss" in lower_line:
                        losses += 1

            total = wins + losses
            if total == 0:
                return "🎮 **SC2 봇** — 게임 기록 없음"

            win_rate = (wins / total) * 100
            lines = [
                "🎮 **SC2 봇 전적**",
                f"  {total}전 {wins}승 {losses}패 (승률 {win_rate:.1f}%)",
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"SC2 전적 로드 실패: {e}")
            return "🎮 **SC2 봇** — 조회 실패"

    def _get_system_section(self) -> str:
        """시스템 상태 섹션"""
        try:
            import platform
            crypto_init = self._project_root / "crypto_trading" / "__init__.py"
            sc2_bot = self._project_root / "wicked_zerg_challenger" / "wicked_zerg_bot_pro_impl.py"
            lines = [
                "🖥️ **시스템**",
                f"  {platform.node()} | {platform.system()} | Python {platform.python_version()}",
                f"  크립토: {'✅' if crypto_init.exists() else '❌'} | SC2: {'✅' if sc2_bot.exists() else '❌'}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return "🖥️ **시스템** — 조회 실패"

    def generate_briefing(self) -> str:
        """종합 일일 브리핑 생성"""
        now = datetime.now()
        weekday = _WEEKDAY_KR[now.weekday()]

        sections = []

        # 헤더
        sections.append(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 **JARVIS 모닝 브리핑**\n"
            f"📆 {now.strftime('%Y년 %m월 %d일')} ({weekday}요일) {now.strftime('%H:%M')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        # 날씨
        sections.append(self._get_weather_section())

        # 운세
        sections.append(self._get_fortune_section())

        # 캘린더
        sections.append(self._get_calendar_section())

        # 뉴스
        sections.append(self._get_news_section())

        # 포트폴리오
        sections.append(self._get_portfolio_section())

        # SC2
        sections.append(self._get_sc2_section())

        # 시스템
        sections.append(self._get_system_section())

        # 푸터
        end_time = datetime.now()
        elapsed = (end_time - now).total_seconds()
        sections.append(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ 생성 소요: {elapsed:.2f}초 | {end_time.strftime('%H:%M:%S')} KST"
        )

        return "\n\n".join(sections)

    async def generate_briefing_async(self) -> str:
        """종합 일일 브리핑 생성 (비동기 - 오케스트레이터 병렬 실행)"""
        now = datetime.now()
        weekday = _WEEKDAY_KR[now.weekday()]

        # 헤더
        header = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 **JARVIS 모닝 브리핑**\n"
            f"📆 {now.strftime('%Y년 %m월 %d일')} ({weekday}요일) {now.strftime('%H:%M')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        # ★ WorkflowOrchestrator 기반 병렬 실행 ★
        try:
            from jarvis_features.workflow_orchestrator import (
                WorkflowOrchestrator, PipelineStep,
            )
            orchestrator = WorkflowOrchestrator()

            steps = [
                PipelineStep("weather", self._get_weather_section, timeout=10),
                PipelineStep("fortune", self._get_fortune_section, timeout=5),
                PipelineStep("calendar", self._get_calendar_section_async, timeout=15),
                PipelineStep("news", self._get_news_section, timeout=10),
                PipelineStep("portfolio", self._get_portfolio_section, timeout=10),
                PipelineStep("sc2", self._get_sc2_section, timeout=5),
                PipelineStep("system", self._get_system_section, timeout=5),
            ]

            results = await orchestrator.execute_parallel(steps)
            body = orchestrator.format_results(results)

            # 실행 보고서 로깅
            import logging
            logging.getLogger("jarvis.briefing").info(
                orchestrator.get_execution_report(results)
            )

        except ImportError:
            # Fallback: 기존 순차 실행
            body_parts = [
                self._get_weather_section(),
                self._get_fortune_section(),
                await self._get_calendar_section_async(),
                self._get_news_section(),
                self._get_portfolio_section(),
                self._get_sc2_section(),
                self._get_system_section(),
            ]
            body = "\n\n".join(body_parts)

        end_time = datetime.now()
        elapsed = (end_time - now).total_seconds()
        footer = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ 생성 소요: {elapsed:.2f}초 | {end_time.strftime('%H:%M:%S')} KST"
        )

        return f"{header}\n\n{body}\n\n{footer}"

    def generate_briefing_dict(self) -> dict:
        """브리핑 데이터를 딕셔너리로 반환"""
        return {
            "timestamp": datetime.now().isoformat(),
            "weather": self._get_weather_section(),
            "fortune": self._get_fortune_section(),
            "news": self._get_news_section(),
            "portfolio": self._get_portfolio_section(),
            "sc2": self._get_sc2_section(),
            "system": self._get_system_section(),
        }


if __name__ == "__main__":
    briefing = DailyBriefing()
    print(briefing.generate_briefing())
