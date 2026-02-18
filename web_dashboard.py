"""
#182: 웹 대시보드 (Web Dashboard)

aiohttp 기반 간단한 웹 대시보드.
포트폴리오, SC2 전적, 시스템 상태 페이지를 제공한다.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("web_dashboard")

# ── HTML 템플릿 ──

_BASE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JARVIS Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0f0f23; color: #e0e0e0; }}
        .header {{ background: linear-gradient(135deg, #1a1a3e, #2d1b4e);
                   padding: 20px 30px; border-bottom: 2px solid #4a90d9; }}
        .header h1 {{ color: #4a90d9; font-size: 24px; }}
        .header .subtitle {{ color: #888; font-size: 14px; margin-top: 5px; }}
        .nav {{ display: flex; gap: 15px; padding: 15px 30px;
                background: #1a1a2e; border-bottom: 1px solid #333; }}
        .nav a {{ color: #4a90d9; text-decoration: none; padding: 8px 16px;
                  border-radius: 4px; transition: background 0.2s; }}
        .nav a:hover, .nav a.active {{ background: #2a2a4e; }}
        .content {{ padding: 30px; max-width: 1200px; margin: 0 auto; }}
        .card {{ background: #1a1a2e; border: 1px solid #333; border-radius: 8px;
                 padding: 20px; margin-bottom: 20px; }}
        .card h2 {{ color: #4a90d9; margin-bottom: 15px; font-size: 18px; }}
        .stat {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .stat .label {{ color: #888; font-size: 12px; text-transform: uppercase; }}
        .stat .value {{ font-size: 24px; font-weight: bold; color: #fff; }}
        .stat .value.positive {{ color: #4caf50; }}
        .stat .value.negative {{ color: #f44336; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px 15px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ color: #4a90d9; font-size: 13px; text-transform: uppercase; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px;
                  font-size: 12px; font-weight: bold; }}
        .badge.ok {{ background: #1b5e20; color: #4caf50; }}
        .badge.warning {{ background: #4e3700; color: #ff9800; }}
        .badge.error {{ background: #4a0000; color: #f44336; }}
        .footer {{ text-align: center; padding: 20px; color: #555; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>JARVIS Dashboard</h1>
        <div class="subtitle">Swarm Control + Crypto Trading Monitor</div>
    </div>
    <div class="nav">
        <a href="/" class="{nav_home}">Overview</a>
        <a href="/portfolio" class="{nav_portfolio}">Portfolio</a>
        <a href="/sc2" class="{nav_sc2}">SC2 Bot</a>
        <a href="/system" class="{nav_system}">System</a>
        <a href="/api/status" class="">API</a>
    </div>
    <div class="content">
        {content}
    </div>
    <div class="footer">JARVIS Dashboard &mdash; {timestamp}</div>
</body>
</html>"""

_OVERVIEW_CONTENT = """
<div class="card">
    <h2>Overview</h2>
    <div class="stat">
        <div class="label">Total Portfolio</div>
        <div class="value">{total_krw}</div>
    </div>
    <div class="stat">
        <div class="label">SC2 Win Rate</div>
        <div class="value">{win_rate}</div>
    </div>
    <div class="stat">
        <div class="label">System Status</div>
        <div class="value"><span class="badge ok">{system_status}</span></div>
    </div>
</div>
"""

_PORTFOLIO_CONTENT = """
<div class="card">
    <h2>Crypto Portfolio</h2>
    <div class="stat">
        <div class="label">Total Value (KRW)</div>
        <div class="value">{total_krw}</div>
    </div>
    <div class="stat">
        <div class="label">Daily P&L</div>
        <div class="value {pnl_class}">{daily_pnl}</div>
    </div>
    <div class="stat">
        <div class="label">Today Trades</div>
        <div class="value">{trade_count}</div>
    </div>
</div>
<div class="card">
    <h2>Holdings</h2>
    <table>
        <tr><th>Ticker</th><th>Amount</th><th>Value (KRW)</th></tr>
        {holdings_rows}
    </table>
</div>
"""

_SC2_CONTENT = """
<div class="card">
    <h2>SC2 Bot Statistics</h2>
    <div class="stat">
        <div class="label">Total Games</div>
        <div class="value">{total_games}</div>
    </div>
    <div class="stat">
        <div class="label">Wins</div>
        <div class="value positive">{wins}</div>
    </div>
    <div class="stat">
        <div class="label">Losses</div>
        <div class="value negative">{losses}</div>
    </div>
    <div class="stat">
        <div class="label">Win Rate</div>
        <div class="value">{win_rate}</div>
    </div>
</div>
"""

_SYSTEM_CONTENT = """
<div class="card">
    <h2>System Status</h2>
    <table>
        <tr><th>Item</th><th>Status</th></tr>
        {system_rows}
    </table>
</div>
"""


class WebDashboard:
    """aiohttp 기반 웹 대시보드

    포트폴리오, SC2 전적, 시스템 상태를 웹으로 제공.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        """초기화

        Args:
            host: 바인드 호스트 (기본: localhost)
            port: 바인드 포트 (기본: 8080)
        """
        self.host = host
        self.port = port
        self._project_root = Path(__file__).parent
        self._app = None

    def _get_portfolio_data(self) -> dict:
        """포트폴리오 데이터 로드"""
        data = {"total_krw": 0, "daily_pnl": 0, "trade_count": 0, "holdings": []}
        try:
            pf = self._project_root / "crypto_trading" / "data" / "portfolio_history.json"
            if pf.exists():
                with open(pf, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if isinstance(history, list) and history:
                    latest = history[-1]
                    data["total_krw"] = latest.get("total_krw", 0)
                    data["holdings"] = latest.get("holdings", [])
                    if len(history) >= 2:
                        prev = history[-2]
                        data["daily_pnl"] = data["total_krw"] - prev.get("total_krw", 0)

            tl = self._project_root / "crypto_trading" / "data" / "trade_log.json"
            if tl.exists():
                with open(tl, "r", encoding="utf-8") as f:
                    trades = json.load(f)
                today = datetime.now().strftime("%Y-%m-%d")
                if isinstance(trades, list):
                    data["trade_count"] = sum(
                        1 for t in trades
                        if isinstance(t, dict) and t.get("timestamp", "").startswith(today)
                    )
        except Exception as e:
            logger.error(f"포트폴리오 데이터 로드 실패: {e}")
        return data

    def _get_sc2_data(self) -> dict:
        """SC2 전적 데이터 로드"""
        data = {"total_games": 0, "wins": 0, "losses": 0, "win_rate": 0.0}
        try:
            log_path = self._project_root / "wicked_zerg_challenger" / "logs" / "bot.log"
            if log_path.exists():
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        ll = line.lower()
                        if "victory" in ll or "result: win" in ll:
                            data["wins"] += 1
                        elif "defeat" in ll or "result: loss" in ll:
                            data["losses"] += 1
                data["total_games"] = data["wins"] + data["losses"]
                if data["total_games"] > 0:
                    data["win_rate"] = (data["wins"] / data["total_games"]) * 100
        except Exception as e:
            logger.error(f"SC2 데이터 로드 실패: {e}")
        return data

    def _get_system_data(self) -> dict:
        """시스템 상태"""
        import platform
        return {
            "platform": platform.system(),
            "python": platform.python_version(),
            "hostname": platform.node(),
            "crypto_module": "OK" if (self._project_root / "crypto_trading" / "__init__.py").exists() else "Missing",
            "sc2_module": "OK" if (self._project_root / "wicked_zerg_challenger").exists() else "Missing",
        }

    def _render_page(self, page: str) -> str:
        """HTML 페이지 렌더링"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nav = {"nav_home": "", "nav_portfolio": "", "nav_sc2": "", "nav_system": ""}

        if page == "home":
            nav["nav_home"] = "active"
            pf = self._get_portfolio_data()
            sc2 = self._get_sc2_data()
            content = _OVERVIEW_CONTENT.format(
                total_krw=f"{pf['total_krw']:,.0f} KRW",
                win_rate=f"{sc2['win_rate']:.1f}%",
                system_status="OK",
            )
        elif page == "portfolio":
            nav["nav_portfolio"] = "active"
            pf = self._get_portfolio_data()
            holdings_rows = ""
            for h in pf.get("holdings", []):
                if isinstance(h, dict):
                    holdings_rows += (
                        f"<tr><td>{h.get('ticker', 'N/A')}</td>"
                        f"<td>{h.get('amount', 0)}</td>"
                        f"<td>{h.get('value_krw', 0):,.0f}</td></tr>"
                    )
            if not holdings_rows:
                holdings_rows = "<tr><td colspan='3'>No holdings data</td></tr>"
            pnl_class = "positive" if pf["daily_pnl"] >= 0 else "negative"
            sign = "+" if pf["daily_pnl"] >= 0 else ""
            content = _PORTFOLIO_CONTENT.format(
                total_krw=f"{pf['total_krw']:,.0f} KRW",
                daily_pnl=f"{sign}{pf['daily_pnl']:,.0f} KRW",
                pnl_class=pnl_class,
                trade_count=str(pf["trade_count"]),
                holdings_rows=holdings_rows,
            )
        elif page == "sc2":
            nav["nav_sc2"] = "active"
            sc2 = self._get_sc2_data()
            content = _SC2_CONTENT.format(
                total_games=sc2["total_games"],
                wins=sc2["wins"],
                losses=sc2["losses"],
                win_rate=f"{sc2['win_rate']:.1f}%",
            )
        elif page == "system":
            nav["nav_system"] = "active"
            sys_data = self._get_system_data()
            rows = ""
            for key, val in sys_data.items():
                badge_cls = "ok" if val not in ("Missing",) else "error"
                rows += f"<tr><td>{key}</td><td><span class='badge {badge_cls}'>{val}</span></td></tr>"
            content = _SYSTEM_CONTENT.format(system_rows=rows)
        else:
            content = "<div class='card'><h2>404</h2><p>Page not found</p></div>"

        return _BASE_HTML.format(content=content, timestamp=now, **nav)

    async def _handle_home(self, request):
        """홈 페이지 핸들러"""
        from aiohttp import web
        return web.Response(text=self._render_page("home"), content_type="text/html")

    async def _handle_portfolio(self, request):
        """포트폴리오 페이지 핸들러"""
        from aiohttp import web
        return web.Response(text=self._render_page("portfolio"), content_type="text/html")

    async def _handle_sc2(self, request):
        """SC2 페이지 핸들러"""
        from aiohttp import web
        return web.Response(text=self._render_page("sc2"), content_type="text/html")

    async def _handle_system(self, request):
        """시스템 페이지 핸들러"""
        from aiohttp import web
        return web.Response(text=self._render_page("system"), content_type="text/html")

    async def _handle_api_status(self, request):
        """API 상태 JSON 엔드포인트"""
        from aiohttp import web
        data = {
            "timestamp": datetime.now().isoformat(),
            "portfolio": self._get_portfolio_data(),
            "sc2": self._get_sc2_data(),
            "system": self._get_system_data(),
        }
        return web.json_response(data)

    def create_app(self):
        """aiohttp 앱 생성"""
        from aiohttp import web
        app = web.Application()
        app.router.add_get("/", self._handle_home)
        app.router.add_get("/portfolio", self._handle_portfolio)
        app.router.add_get("/sc2", self._handle_sc2)
        app.router.add_get("/system", self._handle_system)
        app.router.add_get("/api/status", self._handle_api_status)
        self._app = app
        return app

    def run(self):
        """대시보드 서버 실행"""
        from aiohttp import web
        app = self.create_app()
        logger.info(f"웹 대시보드 시작: http://{self.host}:{self.port}")
        web.run_app(app, host=self.host, port=self.port)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dashboard = WebDashboard()
    dashboard.run()
