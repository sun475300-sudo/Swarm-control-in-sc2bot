#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 AI Arena Dashboard API

SC2 AI Arena�� ������ ���� ���� ���� ��ú��� API
��ŷ, ELO, ��� ��� ���� ����͸�
"""

import asyncio
import json
import requests
from datetime import datetime
import timedelta
import logging
from pathlib import Path
import os
from typing import List
import Dict
import Any
import Optional
import time

# FastAPI imports
try:
    from fastapi import FastAPI
    import HTTPException
    import Depends
    import WebSocket
    import status
    from fastapi.responses import HTMLResponse
    import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPBasic
    import HTTPBasicCredentials
    from starlette.responses import JSONResponse as StarletteJSONResponse
except ImportError:
    raise ImportError(
        "fastapi is required. Install with: pip install fastapi uvicorn")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SC2 AI Arena Dashboard API",
    description="SC2 AI Arena ���� �� ���� ��ú��� API",
    version="1.0.0"
)

# Configure default JSON encoder for UTF-8


class UTF8JSONResponse(StarletteJSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":")
        ).encode("utf-8")


app.default_response_class = UTF8JSONResponse

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Arena ��ú���� ���������� ���� �����ϵ��� ����
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Arena API Integration
# ============================================================================

# Arena API ���� (ȯ�� ���� �Ǵ� �⺻��)
ARENA_API_BASE_URL = os.environ.get(
    "ARENA_API_URL", "https://aiarena.net/api/v2")
ARENA_BOT_NAME = os.environ.get("ARENA_BOT_NAME", "WickedZerg")
ARENA_BOT_ID = os.environ.get("ARENA_BOT_ID", None)

# Arena ������ ĳ��
arena_data_cache = {
    "bot_info": None,
    "matches": [],
    "stats": {},
    "ranking": None,
    "elo_history": [],
    "last_update": None
}

# ============================================================================
# Helper Functions
# ============================================================================


def fetch_arena_bot_info() -> Optional[Dict[str, Any]]:
    """
    Arena API���� �� ���� ��������

    Returns:
        �� ���� �Ǵ� None
    """
    try:
        url = f"{ARENA_API_BASE_URL}/bots/{ARENA_BOT_NAME}/"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Arena API ȣ�� ����: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Arena �� ���� �������� ����: {e}")
        return None


def fetch_arena_matches(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Arena API���� ��� ��� ��������

    Args:
        limit: �ִ� ��� ��

    Returns:
        ��� ��� ����Ʈ
    """
    try:
        if ARENA_BOT_ID:
            url = f"{ARENA_API_BASE_URL}/matches/?bot1={ARENA_BOT_ID}&limit={limit}"
        else:
            url = f"{ARENA_API_BASE_URL}/matches/?bot1_name={ARENA_BOT_NAME}&limit={limit}"

        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            logger.warning(
                f"Arena ��� ��� �������� ����: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Arena ��� ��� �������� ����: {e}")
        return []


def fetch_arena_ranking() -> Optional[Dict[str, Any]]:
    """
    Arena ��ŷ ���� ��������

    Returns:
        ��ŷ ���� �Ǵ� None
    """
    try:
        url = f"{ARENA_API_BASE_URL}/ladders/"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            # ���� ��ŷ ã��
            for ladder in results:
                if ARENA_BOT_NAME.lower() in ladder.get("bot_name", "").lower():
                    return ladder

            return None
        else:
            logger.warning(
                f"Arena ��ŷ ���� �������� ����: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Arena ��ŷ ���� �������� ����: {e}")
        return None


def calculate_arena_stats(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    ��� ��Ͽ��� ��� ���

    Args:
        matches: ��� ��� ����Ʈ

    Returns:
        ��� ��ųʸ�
    """
    if not matches:
        return {
            "total_matches": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "win_rate": 0.0,
            "current_elo": 0,
            "peak_elo": 0,
            "elo_change": 0
        }

    wins = 0
    losses = 0
    ties = 0
    elo_values = []

    for match in matches:
        result = match.get("result", "").lower()
        if "win" in result or result == "1":
            wins += 1
        elif "loss" in result or result == "0":
            losses += 1
        else:
            ties += 1

        elo = match.get("bot1_elo_after", match.get("elo_after", None))
        if elo:
            elo_values.append(elo)

    total_matches = wins + losses + ties
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0.0

    current_elo = elo_values[0] if elo_values else 0
    peak_elo = max(elo_values) if elo_values else 0
    elo_change = elo_values[0] - elo_values[-1] if len(elo_values) > 1 else 0

    return {
        "total_matches": total_matches,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": round(win_rate, 2),
        "current_elo": current_elo,
        "peak_elo": peak_elo,
        "elo_change": elo_change
    }


async def update_arena_cache():
    """Arena ������ ĳ�� ������Ʈ"""
    try:
        logger.info("Arena ������ ĳ�� ������Ʈ ��...")

        # �� ���� ��������
        bot_info = fetch_arena_bot_info()
        if bot_info:
            arena_data_cache["bot_info"] = bot_info
            if not ARENA_BOT_ID and bot_info.get("id"):
                global ARENA_BOT_ID
                ARENA_BOT_ID = bot_info.get("id")

        # ��� ��� ��������
        matches = fetch_arena_matches(limit=100)
        arena_data_cache["matches"] = matches

        # ��� ���
        arena_data_cache["stats"] = calculate_arena_stats(matches)

        # ��ŷ ���� ��������
        ranking = fetch_arena_ranking()
        arena_data_cache["ranking"] = ranking

        # ELO �����丮 ���� (�ֱ� 50���)
        recent_matches = matches[:50] if len(matches) > 50 else matches
        elo_history = []
        for match in reversed(recent_matches):  # ������ �������
            elo_after = match.get(
                "bot1_elo_after", match.get(
                    "elo_after", None))
            if elo_after:
                elo_history.append({
                    "elo": elo_after,
                    "date": match.get("created", match.get("date", datetime.now().isoformat())),
                    "result": match.get("result", "Unknown"),
                    "opponent": match.get("bot2_name", "Unknown")
                })
        arena_data_cache["elo_history"] = elo_history

        arena_data_cache["last_update"] = datetime.now().isoformat()
        logger.info("Arena ������ ĳ�� ������Ʈ �Ϸ�")

    except Exception as e:
        logger.error(f"Arena ĳ�� ������Ʈ ����: {e}")

# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "SC2 AI Arena Dashboard API",
        "version": "1.0.0",
        "bot_name": ARENA_BOT_NAME,
        "bot_id": ARENA_BOT_ID,
        "arena_api_url": ARENA_API_BASE_URL,
        "endpoints": {
            "bot_info": "/api/arena/bot-info",
            "stats": "/api/arena/stats",
            "matches": "/api/arena/matches",
            "ranking": "/api/arena/ranking",
            "elo_history": "/api/arena/elo-history",
            "refresh": "/api/arena/refresh"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_updated": arena_data_cache.get("last_update")
    }


@app.get("/api/arena/bot-info")
async def get_arena_bot_info():
    """Arena �� ���� ��ȸ"""
    bot_info = arena_data_cache.get("bot_info")

    if not bot_info:
        # ĳ�ð� ������ ���� ��������
        bot_info = fetch_arena_bot_info()
        if bot_info:
            arena_data_cache["bot_info"] = bot_info

    if not bot_info:
        return {
            "success": False,
            "message": "�� ������ ������ �� �����ϴ�. Arena API URL�� �� �̸��� Ȯ���ϼ���.",
            "config": {
                "arena_api_url": ARENA_API_BASE_URL,
                "bot_name": ARENA_BOT_NAME,
                "bot_id": ARENA_BOT_ID}}

    return {
        "success": True,
        "data": bot_info,
        "cached": arena_data_cache.get("bot_info") is not None
    }


@app.get("/api/arena/stats")
async def get_arena_stats():
    """Arena ��� ��ȸ"""
    stats = arena_data_cache.get("stats")

    if not stats or not arena_data_cache.get("last_update"):
        # ĳ�ð� ������ ������Ʈ
        matches = fetch_arena_matches(limit=100)
        stats = calculate_arena_stats(matches)
        arena_data_cache["stats"] = stats

    return {
        "success": True,
        "data": stats,
        "last_update": arena_data_cache.get("last_update")
    }


@app.get("/api/arena/matches")
async def get_arena_matches(limit: int = 50, offset: int = 0):
    """Arena ��� ��� ��ȸ"""
    matches = arena_data_cache.get("matches", [])

    # ���������̼�
    total = len(matches)
    paginated_matches = matches[offset:offset + limit]

    return {
        "success": True,
        "data": paginated_matches,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        },
        "last_update": arena_data_cache.get("last_update")
    }


@app.get("/api/arena/ranking")
async def get_arena_ranking():
    """Arena ��ŷ ���� ��ȸ"""
    ranking = arena_data_cache.get("ranking")

    if not ranking:
        # ĳ�ð� ������ ���� ��������
        ranking = fetch_arena_ranking()
        if ranking:
            arena_data_cache["ranking"] = ranking

    if not ranking:
        return {
            "success": False,
            "message": "��ŷ ������ ������ �� �����ϴ�.",
            "data": None
        }

    return {
        "success": True,
        "data": ranking
    }


@app.get("/api/arena/elo-history")
async def get_arena_elo_history(limit: int = 50):
    """ELO ������ �����丮 ��ȸ"""
    elo_history = arena_data_cache.get("elo_history", [])

    if not elo_history:
        # ĳ�ð� ������ ����
        matches = fetch_arena_matches(limit=limit)
        elo_history = []
        for match in reversed(matches):
            elo_after = match.get(
                "bot1_elo_after", match.get(
                    "elo_after", None))
            if elo_after:
                elo_history.append({
                    "elo": elo_after,
                    "date": match.get("created", match.get("date", datetime.now().isoformat())),
                    "result": match.get("result", "Unknown"),
                    "opponent": match.get("bot2_name", "Unknown")
                })
        arena_data_cache["elo_history"] = elo_history

    return {
        "success": True,
        "data": elo_history[:limit],
        "last_update": arena_data_cache.get("last_update")
    }


@app.post("/api/arena/refresh")
async def refresh_arena_data():
    """Arena ������ ĳ�� ���� ���ΰ�ħ"""
    await update_arena_cache()
    return {
        "success": True,
        "message": "Arena �����Ͱ� ���ΰ�ħ�Ǿ����ϴ�.",
        "last_update": arena_data_cache.get("last_update")
    }


@app.get("/api/arena/opponents")
async def get_arena_opponents():
    """��� ���� ���� ��ȸ"""
    matches = arena_data_cache.get("matches", [])

    opponent_stats = {}

    for match in matches:
        opponent = match.get("bot2_name", "Unknown")
        result = match.get("result", "").lower()

        if opponent not in opponent_stats:
            opponent_stats[opponent] = {
                "opponent_name": opponent,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "total": 0,
                "win_rate": 0.0
            }

        if "win" in result or result == "1":
            opponent_stats[opponent]["wins"] += 1
        elif "loss" in result or result == "0":
            opponent_stats[opponent]["losses"] += 1
        else:
            opponent_stats[opponent]["ties"] += 1

        opponent_stats[opponent]["total"] += 1

    # �·� ���
    for opponent, stats in opponent_stats.items():
        if stats["total"] > 0:
            stats["win_rate"] = round(
                (stats["wins"] / stats["total"]) * 100, 2)

    # �·� ������ ����
    sorted_opponents = sorted(
        opponent_stats.values(),
        key=lambda x: x["win_rate"],
        reverse=True
    )

    return {
        "success": True,
        "data": sorted_opponents,
        "total_opponents": len(sorted_opponents)
    }


@app.get("/api/arena/recent-performance")
async def get_recent_performance(days: int = 7):
    """�ֱ� ���� ��ȸ (�Ⱓ��)"""
    matches = arena_data_cache.get("matches", [])

    cutoff_date = datetime.now() - timedelta(days=days)

    recent_matches = []
    for match in matches:
        match_date_str = match.get("created", match.get("date", ""))
        if match_date_str:
            try:
                match_date = datetime.fromisoformat(
                    match_date_str.replace('Z', '+00:00'))
                if match_date.replace(tzinfo=None) >= cutoff_date:
                    recent_matches.append(match)
            except Exception:
                continue

    stats = calculate_arena_stats(recent_matches)

    return {
        "success": True,
        "data": {
            "period_days": days,
            "stats": stats,
            "matches_count": len(recent_matches)
        },
        "last_update": arena_data_cache.get("last_update")
    }

# ============================================================================
# WebSocket for real-time updates
# ============================================================================

connected_arena_clients: List[WebSocket] = []


@app.websocket("/ws/arena-updates")
async def websocket_arena_updates(websocket: WebSocket):
    """�ǽð� Arena ������Ʈ WebSocket"""
    await websocket.accept()
    connected_arena_clients.append(websocket)

    try:
        while True:
            # ĳ�õ� ������ ����
            data = {
                "type": "arena_update",
                "stats": arena_data_cache.get("stats", {}),
                "ranking": arena_data_cache.get("ranking"),
                "last_update": arena_data_cache.get("last_update"),
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(data)
            await asyncio.sleep(30)  # 30�ʸ��� ������Ʈ
    except Exception as e:
        logger.error(f"WebSocket ����: {e}")
    finally:
        connected_arena_clients.remove(websocket)

# ============================================================================
# Background Tasks
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """���� ���� �� ����"""
    logger.info("SC2 AI Arena Dashboard API ����")
    logger.info(f"�� �̸�: {ARENA_BOT_NAME}")
    logger.info(f"Arena API URL: {ARENA_API_BASE_URL}")

    # �ʱ� ĳ�� ������Ʈ
    await update_arena_cache()

    # �ֱ������� ĳ�� ������Ʈ (5�и���)
    async def periodic_update():
        while True:
            await asyncio.sleep(300)  # 5��
            await update_arena_cache()

    # ��׶��� �½�ũ ����
    asyncio.create_task(periodic_update())

# ============================================================================
# Server startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,  # Arena ��ú���� �ٸ� ��Ʈ ���
        log_level="info"
    )
