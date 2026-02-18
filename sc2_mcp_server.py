import asyncio
import json
import os
import subprocess
from mcp.server.fastmcp import FastMCP

# Create an MCP server for JARVIS
mcp = FastMCP("JARVIS-SC2-Manager")

# Base directory for SC2 bot
SC2_DIR = r"d:\Swarm-contol-in-sc2bot"

@mcp.tool()
async def list_bot_logs(limit: int = 10) -> str:
    """Lists the most recent log files from the SC2 bot logs directory."""
    log_dir = os.path.join(SC2_DIR, "logs")
    if not os.path.exists(log_dir):
        return "Log directory not found."
    
    logs = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")], reverse=True)
    return "\n".join(logs[:limit])

@mcp.tool()
async def read_log_content(filename: str) -> str:
    """Reads the content of a specific log file."""
    log_path = os.path.join(SC2_DIR, "logs", filename)
    if not os.path.exists(log_path):
        return f"File {filename} not found."
    
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        # Return last 2000 characters to keep it concise
        content = f.read()
        return content[-2000:]

@mcp.tool()
async def run_sc2_test_game() -> str:
    """Runs a quick test game to verify bot stability."""
    try:
        # Run in background via CMD to avoid blocking the MCP server
        subprocess.Popen(["cmd", "/c", "start", "run_combat_tests.bat"], cwd=SC2_DIR)
        return "Started combat tests in a new window."
    except Exception as e:
        return f"Failed to start game: {str(e)}"

@mcp.tool()
async def get_game_situation() -> str:
    """Provides a summarized report of the current game situation (minerals, supply, units, etc.)"""
    # Look for the latest state JSON
    state_file = os.path.join(SC2_DIR, "logs", "game_state.json")
    if not os.path.exists(state_file):
        # Fallback to sensor_network.json if game_state.json doesn't exist
        state_file = os.path.join(SC2_DIR, "logs", "sensor_network.json")
        
    if not os.path.exists(state_file):
        return "No real-time game state data available yet. Please start a game."
    
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Summarize the data for the AI
            if isinstance(data, list) and len(data) > 0:
                # If it's the sensor network list, just count types
                counts = {}
                for entry in data:
                    t = entry.get("unit_type", "UNKNOWN")
                    counts[t] = counts.get(t, 0) + 1
                return f"Current Units: {json.dumps(counts, indent=2)}"
            return f"Current Situation: {json.dumps(data, indent=2)}"
    except Exception as e:
        return f"Error reading state: {str(e)}"

@mcp.tool()
async def set_aggression_level(level: str) -> str:
    """Sets the bot's aggression level. Options: 'passive', 'balanced', 'aggressive', 'all_in'"""
    # level = level.lower()
    valid_levels = ["passive", "balanced", "aggressive", "all_in"]
    if level not in valid_levels:
        return f"Invalid level. Choose from: {valid_levels}"
    
    cmd_file = os.path.join(SC2_DIR, "jarvis_command.json")
    try:
        with open(cmd_file, 'w', encoding='utf-8') as f:
            json.dump({"aggression_level": level}, f)
        return f"Aggression level set to: {level}. The bot will update its strategy shortly."
    except Exception as e:
        return f"Failed to set aggression: {str(e)}"

# ──────────────────────────────────────────────
# #122  SC2 Bot Stats
# ──────────────────────────────────────────────
@mcp.tool()
async def sc2_bot_stats() -> str:
    """SC2 봇 전적 및 통계를 조회합니다. 로그 파일에서 승리/패배 기록을 집계합니다."""
    try:
        log_dir = os.path.join(SC2_DIR, "logs")
        results_dir = os.path.join(SC2_DIR, "wicked_zerg_challenger", "logs")

        wins = 0
        losses = 0
        draws = 0
        games = 0
        details = []

        # Search multiple possible log locations
        search_dirs = [log_dir, results_dir]
        for sdir in search_dirs:
            if not os.path.exists(sdir):
                continue
            for fname in os.listdir(sdir):
                fpath = os.path.join(sdir, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    # Look for common result patterns in log files
                    content_lower = content.lower()
                    if 'result' in content_lower or 'victory' in content_lower or 'defeat' in content_lower:
                        w = content_lower.count('victory') + content_lower.count('result.victory') + content_lower.count('result: win')
                        l = content_lower.count('defeat') + content_lower.count('result.defeat') + content_lower.count('result: loss')
                        d = content_lower.count('result.tie') + content_lower.count('result: draw')
                        if w + l + d > 0:
                            wins += w
                            losses += l
                            draws += d
                            games += w + l + d
                            details.append(f"  {fname}: {w}W / {l}L / {d}D")
                except Exception:
                    continue

        if games == 0:
            return "전적 데이터를 찾을 수 없습니다. 게임을 실행한 후 다시 확인하세요."

        winrate = (wins / games * 100) if games > 0 else 0
        summary = (
            f"SC2 봇 전적 요약\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"총 게임: {games}판\n"
            f"승리: {wins} | 패배: {losses} | 무승부: {draws}\n"
            f"승률: {winrate:.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        if details:
            summary += "\n\n파일별 상세:\n" + "\n".join(details[:20])
        return summary
    except Exception as e:
        return f"전적 조회 실패: {e}"


if __name__ == "__main__":
    mcp.run()
