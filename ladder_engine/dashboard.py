"""
Phase 374: Real-Time Dashboard
FastAPI-based REST + WebSocket dashboard for live SC2 bot stats.
Endpoints: /stats, /current_game, /history, /ws
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    FastAPI = object
    WebSocket = object


# ------------------------------------------------------------------
# Shared state (in-memory, thread-safe via asyncio)
# ------------------------------------------------------------------

_game_state: Dict[str, Any] = {
    "in_game": False,
    "game_time": 0.0,
    "minerals": 0,
    "vespene": 0,
    "supply_used": 0,
    "supply_cap": 14,
    "worker_count": 12,
    "army_supply": 0,
    "current_strategy": "hatch_first",
    "threat_level": "NONE",
    "apm": 0.0,
    "macro_efficiency": 0.5,
    "decision_log": [],
}

_player_stats: Dict[str, Any] = {
    "mmr": 0,
    "rank": "Unranked",
    "total_games": 0,
    "win_rate": 0.0,
    "current_streak": 0,
    "win_rate_zvt": 0.0,
    "win_rate_zvp": 0.0,
    "win_rate_zvz": 0.0,
}

_match_history: List[Dict] = []

_ws_clients: Set = set()


def update_game_state(updates: Dict[str, Any]):
    """Thread-safe state update callable from the bot."""
    _game_state.update(updates)
    if len(_game_state.get("decision_log", [])) > 50:
        _game_state["decision_log"] = _game_state["decision_log"][-50:]


def update_player_stats(stats: Dict[str, Any]):
    _player_stats.update(stats)


def add_match_to_history(match: Dict):
    _match_history.append(match)
    if len(_match_history) > 200:
        _match_history.pop(0)


# ------------------------------------------------------------------
# Dashboard HTML
# ------------------------------------------------------------------

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>SC2 Zerg Bot Dashboard</title>
<style>
  body { background: #0d1117; color: #c9d1d9; font-family: monospace; padding: 20px; }
  h1 { color: #58a6ff; }
  .metric { display: inline-block; margin: 10px; padding: 10px;
            background: #161b22; border: 1px solid #30363d; min-width: 120px; }
  .metric-val { font-size: 1.6em; color: #3fb950; }
  #log { background: #010409; border: 1px solid #30363d;
         height: 200px; overflow-y: scroll; padding: 8px; font-size: 0.85em; }
</style>
</head>
<body>
<h1>SC2 Zerg Bot — Live Dashboard</h1>
<div id="metrics"></div>
<h3>Decision Log</h3>
<div id="log"></div>
<script>
const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  const m = document.getElementById("metrics");
  m.innerHTML = Object.entries(data.game || {}).map(([k, v]) =>
    `<div class="metric"><div>${k}</div><div class="metric-val">${v}</div></div>`
  ).join("");
  const log = document.getElementById("log");
  (data.game?.decision_log || []).forEach(entry => {
    const div = document.createElement("div");
    div.textContent = entry;
    log.prepend(div);
  });
  while (log.children.length > 40) log.removeChild(log.lastChild);
};
</script>
</body>
</html>
"""


# ------------------------------------------------------------------
# FastAPI application factory
# ------------------------------------------------------------------

def create_app() -> Any:
    """Create and configure the FastAPI dashboard application."""
    if not _FASTAPI_AVAILABLE:
        raise ImportError("fastapi is required: pip install fastapi uvicorn")

    app = FastAPI(
        title="SC2 Zerg Bot Dashboard",
        description="Real-time ladder performance dashboard",
        version="1.0.0",
    )

    # ---- REST endpoints ----

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return DASHBOARD_HTML

    @app.get("/stats")
    async def stats():
        """Return current player ladder stats."""
        return JSONResponse(content=_player_stats)

    @app.get("/current_game")
    async def current_game():
        """Return live in-game state."""
        return JSONResponse(content=_game_state)

    @app.get("/history")
    async def history(limit: int = 20):
        """Return recent match history."""
        recent = _match_history[-limit:]
        return JSONResponse(content={"matches": recent, "total": len(_match_history)})

    @app.get("/health")
    async def health():
        return {"status": "ok", "timestamp": time.time()}

    # ---- WebSocket ----

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        _ws_clients.add(websocket)
        try:
            while True:
                payload = json.dumps({
                    "game": _game_state,
                    "stats": _player_stats,
                    "timestamp": time.time(),
                })
                await websocket.send_text(payload)
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            _ws_clients.discard(websocket)
        except Exception:
            _ws_clients.discard(websocket)

    return app


# ------------------------------------------------------------------
# Broadcast helper (call from bot game loop)
# ------------------------------------------------------------------

async def broadcast_update(data: Dict):
    """Push a data payload to all connected WebSocket clients."""
    if not _ws_clients:
        return
    payload = json.dumps(data)
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


# ------------------------------------------------------------------
# Entry point for standalone run
# ------------------------------------------------------------------

if __name__ == "__main__":
    try:
        import uvicorn
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
    except ImportError:
        print("Install uvicorn: pip install uvicorn")
