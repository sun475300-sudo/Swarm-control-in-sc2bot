"""
#179: 일일 브리핑 (Daily Briefing)

포트폴리오 요약 + SC2 전적 + 시스템 상태를 종합 리포트로 생성.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("daily_briefing")


class DailyBriefing:
    """일일 종합 브리핑 생성기

    암호화폐 포트폴리오, SC2 봇 전적, 시스템 상태를
    하나의 종합 리포트로 통합하여 제공한다.
    """

    def __init__(self):
        """초기화"""
        self._project_root = Path(__file__).parent
        self._portfolio_data = None
        self._sc2_data = None
        self._system_data = None

    def _load_portfolio_summary(self) -> dict:
        """포트폴리오 요약 데이터 로드"""
        summary = {
            "status": "unknown",
            "total_krw": 0,
            "holdings": [],
            "daily_pnl": 0.0,
            "daily_pnl_pct": 0.0,
            "trade_count_today": 0,
        }
        try:
            portfolio_file = self._project_root / "crypto_trading" / "data" / "portfolio_history.json"
            if portfolio_file.exists():
                with open(portfolio_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if history and len(history) > 0:
                    latest = history[-1] if isinstance(history, list) else history
                    summary["status"] = "active"
                    summary["total_krw"] = latest.get("total_krw", 0)
                    summary["holdings"] = latest.get("holdings", [])

                    # 전일 대비 수익률 계산
                    if isinstance(history, list) and len(history) >= 2:
                        prev = history[-2]
                        prev_total = prev.get("total_krw", 0)
                        if prev_total > 0:
                            summary["daily_pnl"] = summary["total_krw"] - prev_total
                            summary["daily_pnl_pct"] = (summary["daily_pnl"] / prev_total) * 100
            else:
                summary["status"] = "no_data"

            # 거래 로그에서 오늘 거래 수
            trade_log_file = self._project_root / "crypto_trading" / "data" / "trade_log.json"
            if trade_log_file.exists():
                with open(trade_log_file, "r", encoding="utf-8") as f:
                    trades = json.load(f)
                today = datetime.now().strftime("%Y-%m-%d")
                if isinstance(trades, list):
                    summary["trade_count_today"] = sum(
                        1 for t in trades
                        if isinstance(t, dict) and t.get("timestamp", "").startswith(today)
                    )
        except Exception as e:
            summary["status"] = f"error: {e}"
            logger.error(f"포트폴리오 데이터 로드 실패: {e}")

        self._portfolio_data = summary
        return summary

    def _load_sc2_summary(self) -> dict:
        """SC2 봇 전적 요약 데이터 로드"""
        summary = {
            "status": "unknown",
            "total_games": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "recent_games": [],
        }
        try:
            # SC2 봇 로그 파일에서 전적 추출
            bot_log = self._project_root / "wicked_zerg_challenger" / "logs" / "bot.log"
            if bot_log.exists():
                wins = 0
                losses = 0
                with open(bot_log, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        lower_line = line.lower()
                        if "victory" in lower_line or "result: win" in lower_line:
                            wins += 1
                        elif "defeat" in lower_line or "result: loss" in lower_line:
                            losses += 1
                summary["wins"] = wins
                summary["losses"] = losses
                summary["total_games"] = wins + losses
                if summary["total_games"] > 0:
                    summary["win_rate"] = (wins / summary["total_games"]) * 100
                summary["status"] = "active"
            else:
                summary["status"] = "no_log"
        except Exception as e:
            summary["status"] = f"error: {e}"
            logger.error(f"SC2 전적 로드 실패: {e}")

        self._sc2_data = summary
        return summary

    def _load_system_status(self) -> dict:
        """시스템 상태 로드"""
        import platform
        status = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "timestamp": datetime.now().isoformat(),
            "crypto_module": "unknown",
            "sc2_module": "unknown",
        }
        try:
            # 크립토 모듈 상태
            crypto_init = self._project_root / "crypto_trading" / "__init__.py"
            status["crypto_module"] = "available" if crypto_init.exists() else "missing"

            # SC2 모듈 상태
            sc2_bot = self._project_root / "wicked_zerg_challenger" / "wicked_zerg_bot_pro_impl.py"
            status["sc2_module"] = "available" if sc2_bot.exists() else "missing"
        except Exception as e:
            logger.error(f"시스템 상태 로드 실패: {e}")

        self._system_data = status
        return status

    def generate_briefing(self) -> str:
        """종합 일일 브리핑 생성

        Returns:
            str: 포맷된 브리핑 텍스트
        """
        portfolio = self._load_portfolio_summary()
        sc2 = self._load_sc2_summary()
        system = self._load_system_status()

        lines = []
        now = datetime.now()
        lines.append("=" * 60)
        lines.append(f"  JARVIS 일일 브리핑 — {now.strftime('%Y년 %m월 %d일 %H:%M')}")
        lines.append("=" * 60)
        lines.append("")

        # 포트폴리오 섹션
        lines.append("[ 암호화폐 포트폴리오 ]")
        lines.append("-" * 40)
        if portfolio["status"] == "active":
            lines.append(f"  총 자산: {portfolio['total_krw']:,.0f} KRW")
            pnl_sign = "+" if portfolio["daily_pnl"] >= 0 else ""
            lines.append(f"  일일 손익: {pnl_sign}{portfolio['daily_pnl']:,.0f} KRW ({pnl_sign}{portfolio['daily_pnl_pct']:.2f}%)")
            lines.append(f"  오늘 거래: {portfolio['trade_count_today']}건")
            if portfolio["holdings"]:
                lines.append(f"  보유 종목: {len(portfolio['holdings'])}개")
        elif portfolio["status"] == "no_data":
            lines.append("  포트폴리오 데이터 없음")
        else:
            lines.append(f"  상태: {portfolio['status']}")
        lines.append("")

        # SC2 전적 섹션
        lines.append("[ SC2 봇 전적 ]")
        lines.append("-" * 40)
        if sc2["status"] == "active":
            lines.append(f"  총 게임: {sc2['total_games']}전 {sc2['wins']}승 {sc2['losses']}패")
            lines.append(f"  승률: {sc2['win_rate']:.1f}%")
        elif sc2["status"] == "no_log":
            lines.append("  봇 로그 없음")
        else:
            lines.append(f"  상태: {sc2['status']}")
        lines.append("")

        # 시스템 상태 섹션
        lines.append("[ 시스템 상태 ]")
        lines.append("-" * 40)
        lines.append(f"  플랫폼: {system['platform']} / Python {system['python_version']}")
        lines.append(f"  호스트: {system['hostname']}")
        lines.append(f"  크립토 모듈: {system['crypto_module']}")
        lines.append(f"  SC2 모듈: {system['sc2_module']}")
        lines.append("")

        lines.append("=" * 60)
        lines.append(f"  생성 시각: {now.isoformat()}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_briefing_dict(self) -> dict:
        """브리핑 데이터를 딕셔너리로 반환"""
        return {
            "timestamp": datetime.now().isoformat(),
            "portfolio": self._load_portfolio_summary(),
            "sc2": self._load_sc2_summary(),
            "system": self._load_system_status(),
        }


if __name__ == "__main__":
    briefing = DailyBriefing()
    print(briefing.generate_briefing())
