import asyncio
import json
import os
import subprocess
import urllib.parse
import urllib.request
import urllib.error
from mcp.server.fastmcp import FastMCP

# Create an MCP server for JARVIS
mcp = FastMCP("JARVIS-SC2-Manager")

# Base directory for SC2 bot (환경변수 우선, 없으면 스크립트 위치 기반)
SC2_DIR = os.environ.get("SC2_BOT_DIR", os.path.dirname(os.path.abspath(__file__)))

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
    # 경로 탐색(Path Traversal) 방지: 파일명에서 디렉토리 구분자 제거
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or ".." in filename:
        return "오류: 잘못된 파일명입니다. 파일 이름만 지정하세요."

    log_dir = os.path.join(SC2_DIR, "logs")
    log_path = os.path.join(log_dir, safe_filename)

    # 실제 경로가 로그 디렉토리 내부인지 검증
    real_path = os.path.realpath(log_path)
    real_log_dir = os.path.realpath(log_dir)
    if not real_path.startswith(real_log_dir + os.sep) and real_path != real_log_dir:
        return "오류: 허용되지 않은 경로입니다."

    if not os.path.exists(log_path):
        return f"File {safe_filename} not found."

    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        # Efficiently read only the tail to avoid loading large files into memory
        try:
            f.seek(0, 2)  # Seek to end
            size = f.tell()
            read_size = min(size, 4000)  # Read extra for multi-byte char safety
            f.seek(max(0, size - read_size))
            content = f.read()
        except OSError:
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
    # Bug fix #21: Uncomment .lower() for case-insensitive matching
    level = level.lower()
    valid_levels = ["passive", "balanced", "aggressive", "all_in"]
    if level not in valid_levels:
        return f"Invalid level. Choose from: {valid_levels}"
    
    cmd_file = os.path.join(SC2_DIR, "jarvis_command.json")
    try:
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(cmd_file), suffix='.tmp')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump({"aggression_level": level}, f)
            os.replace(temp_path, cmd_file)
        except Exception as e:
            try: os.remove(temp_path)
            except OSError as oe:
                logger.debug(f"temp file cleanup failed: {oe}")
            return f"공격성 설정 실패: {e}"
        return f"Aggression level set to: {level}. The bot will update its strategy shortly."
    except Exception as e:
        return f"Failed to set aggression: {str(e)}"

# ──────────────────────────────────────────────
# #122  SC2 Bot Stats
# ──────────────────────────────────────────────
@mcp.tool()
async def sc2_bot_stats() -> str:
    """SC2 봇 전적 및 통계를 조회합니다. 구조화 데이터 우선, 로그 파일 보조."""
    import json as _json
    import re as _re
    from collections import defaultdict

    try:
        wins = 0
        losses = 0
        draws = 0
        race_stats = defaultdict(lambda: {"w": 0, "l": 0})
        recent_games = []  # (timestamp, opponent, map, result)

        # ── 1차: 구조화된 JSON 게임 데이터 (data/games/*.json) ──
        games_dir = os.path.join(SC2_DIR, "wicked_zerg_challenger", "data", "games")
        if os.path.isdir(games_dir):
            for fname in sorted(os.listdir(games_dir)):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(games_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = _json.load(f)
                    meta = data.get("meta", {})
                    gr = data.get("game_result", {})
                    result_str = gr.get("result", "").upper()
                    opp_race = meta.get("opponent_race", "Unknown")
                    map_name = meta.get("map_name", "Unknown")
                    timestamp = meta.get("timestamp", "")[:16]

                    if "VICTORY" in result_str or "WIN" in result_str:
                        wins += 1
                        race_stats[opp_race]["w"] += 1
                        recent_games.append((timestamp, opp_race, map_name, "W"))
                    elif "DEFEAT" in result_str or "LOSS" in result_str:
                        losses += 1
                        race_stats[opp_race]["l"] += 1
                        recent_games.append((timestamp, opp_race, map_name, "L"))
                    elif "TIE" in result_str or "DRAW" in result_str:
                        draws += 1
                        recent_games.append((timestamp, opp_race, map_name, "D"))
                except Exception:
                    continue

        # ── 2차: game_analytics.json (GameAnalytics 시스템) ──
        analytics_path = os.path.join(
            SC2_DIR, "wicked_zerg_challenger", "local_training", "game_analytics.json"
        )
        if os.path.isfile(analytics_path) and wins + losses + draws == 0:
            try:
                with open(analytics_path, 'r', encoding='utf-8') as f:
                    analytics = _json.load(f)
                for race, stats in analytics.get("race_stats", {}).items():
                    rw = stats.get("wins", 0)
                    rl = stats.get("losses", 0)
                    wins += rw
                    losses += rl
                    race_stats[race]["w"] += rw
                    race_stats[race]["l"] += rl
            except Exception:
                pass

        # ── 3차: 로그 파일 (엄격한 패턴만 — "Match result:" 라인) ──
        if wins + losses + draws == 0:
            log_dirs = [
                os.path.join(SC2_DIR, "logs"),
                os.path.join(SC2_DIR, "wicked_zerg_challenger", "logs"),
            ]
            result_pattern = _re.compile(
                r"match result:\s*(victory|defeat|win|loss|draw|tie)",
                _re.IGNORECASE,
            )
            for sdir in log_dirs:
                if not os.path.isdir(sdir):
                    continue
                for fname in sorted(os.listdir(sdir)):
                    fpath = os.path.join(sdir, fname)
                    if not os.path.isfile(fpath):
                        continue
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        # 파일당 최초 "Match result:" 라인만 카운트 (중복 방지)
                        match = result_pattern.search(content)
                        if match:
                            r = match.group(1).upper()
                            if r in ("VICTORY", "WIN"):
                                wins += 1
                            elif r in ("DEFEAT", "LOSS"):
                                losses += 1
                            else:
                                draws += 1
                    except Exception:
                        continue

        games = wins + losses + draws
        if games == 0:
            return "전적 데이터를 찾을 수 없습니다. 게임을 실행한 후 다시 확인하세요."

        winrate = (wins / games * 100) if games > 0 else 0

        # ── 요약 출력 ──
        summary = (
            f"SC2 봇 전적 요약\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"총 게임: {games}판\n"
            f"승리: {wins} | 패배: {losses} | 무승부: {draws}\n"
            f"승률: {winrate:.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

        # 종족별 승률
        if race_stats:
            summary += "\n\n종족별 전적:"
            for race, rs in sorted(race_stats.items()):
                rw, rl = rs["w"], rs["l"]
                rtotal = rw + rl
                rwr = (rw / rtotal * 100) if rtotal > 0 else 0
                summary += f"\n  vs {race}: {rw}W/{rl}L ({rwr:.0f}%)"

        # 최근 게임 (최대 5개)
        if recent_games:
            summary += "\n\n최근 게임:"
            for ts, opp, mp, res in recent_games[-5:]:
                icon = "✅" if res == "W" else "❌" if res == "L" else "➖"
                summary += f"\n  {icon} vs {opp} @ {mp} ({ts})"

        return summary
    except Exception as e:
        return f"전적 조회 실패: {e}"


# ──────────────────────────────────────────────
# SC2 리플레이 분석
# ──────────────────────────────────────────────
_SC2_REPLAY_DIRS = [
    os.path.expanduser(r"~\Documents\StarCraft II\Accounts"),
    os.path.join(SC2_DIR, "replays"),
    os.path.join(SC2_DIR, "wicked_zerg_challenger", "replays"),
]


def _find_latest_replay(limit: int = 1) -> list:
    """최근 SC2Replay 파일을 탐색합니다."""
    replays = []
    _MAX_FILES = 5000  # Bug fix #22: Limit max files scanned to prevent unbounded os.walk
    _MAX_DEPTH = 5     # Limit directory traversal depth
    file_count = 0
    for base_dir in _SC2_REPLAY_DIRS:
        if not os.path.exists(base_dir):
            continue
        base_depth = base_dir.rstrip(os.sep).count(os.sep)
        for root, dirs, files in os.walk(base_dir):
            current_depth = root.count(os.sep) - base_depth
            if current_depth >= _MAX_DEPTH:
                dirs.clear()
                continue
            for f in files:
                if f.endswith(".SC2Replay"):
                    fpath = os.path.join(root, f)
                    replays.append((fpath, os.path.getmtime(fpath)))
                    file_count += 1
                    if file_count >= _MAX_FILES:
                        break
            if file_count >= _MAX_FILES:
                break
        if file_count >= _MAX_FILES:
            break
    replays.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in replays[:limit]]


@mcp.tool()
async def analyze_replay(replay_path: str = "") -> str:
    """SC2 리플레이 파일을 분석합니다.
    replay_path: 분석할 리플레이 경로 (비우면 가장 최근 리플레이)"""
    try:
        if not replay_path:
            found = _find_latest_replay(1)
            if not found:
                return "리플레이 파일을 찾을 수 없습니다.\n탐색 경로: " + ", ".join(_SC2_REPLAY_DIRS)
            replay_path = found[0]

        if not os.path.exists(replay_path):
            return f"파일이 존재하지 않습니다: {replay_path}"

        fname = os.path.basename(replay_path)
        fsize = os.path.getsize(replay_path)
        mtime = os.path.getmtime(replay_path)
        from datetime import datetime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

        # 파일 크기 유효성 검사
        if fsize > 100_000_000:  # 100MB
            return "리플레이 파일이 너무 큽니다 (100MB 초과)"
        if fsize == 0:
            return "리플레이 파일이 비어있습니다"

        # sc2reader가 설치되어 있으면 상세 분석
        try:
            import sc2reader
            replay = sc2reader.load_replay(replay_path)
            players = []
            for p in replay.players:
                players.append(f"  {p.name} ({p.play_race}) - {p.result}")

            result = (
                f"SC2 리플레이 분석\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"파일: {fname}\n"
                f"날짜: {date_str}\n"
                f"맵: {replay.map_name}\n"
                f"게임 길이: {replay.game_length}\n"
                f"카테고리: {replay.category}\n"
                f"플레이어:\n" + "\n".join(players) + "\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            # 유닛 생산 통계 (가능한 경우)
            if hasattr(replay, 'tracker_events'):
                unit_counts = {}
                for event in replay.tracker_events:
                    if hasattr(event, 'unit') and hasattr(event, 'name') and 'Born' in type(event).__name__:
                        uname = getattr(event.unit, 'name', 'Unknown')
                        unit_counts[uname] = unit_counts.get(uname, 0) + 1
                if unit_counts:
                    top_units = sorted(unit_counts.items(), key=lambda x: x[1], reverse=True)[:15]
                    result += "\n\n유닛 생산 TOP 15:\n"
                    for uname, cnt in top_units:
                        result += f"  {uname}: {cnt}\n"
            return result

        except ImportError:
            # sc2reader 없으면 기본 파일 정보만
            return (
                f"SC2 리플레이 (기본 정보)\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"파일: {fname}\n"
                f"날짜: {date_str}\n"
                f"크기: {fsize / 1024:.1f} KB\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"상세 분석을 위해 sc2reader를 설치하세요:\n"
                f"  pip install sc2reader"
            )
    except Exception as e:
        return f"리플레이 분석 실패: {e}"


@mcp.tool()
async def list_replays(limit: int = 10) -> str:
    """최근 SC2 리플레이 파일 목록을 조회합니다.
    limit: 조회할 최대 개수 (기본 10)"""
    found = _find_latest_replay(limit)
    if not found:
        return "리플레이 파일을 찾을 수 없습니다."
    from datetime import datetime
    lines = []
    for i, fpath in enumerate(found, 1):
        fname = os.path.basename(fpath)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%m/%d %H:%M")
        size_kb = os.path.getsize(fpath) / 1024
        lines.append(f"  {i}. [{mtime}] {fname} ({size_kb:.0f}KB)")
    return f"최근 리플레이 ({len(found)}개)\n" + "\n".join(lines)


# ──────────────────────────────────────────────
# SC2 실시간 코칭
# ──────────────────────────────────────────────
@mcp.tool()
async def sc2_coaching_check() -> str:
    """현재 게임 상태를 분석하여 코칭 메시지를 반환합니다.
    game_state.json 또는 sensor_network.json 기반."""
    state_file = os.path.join(SC2_DIR, "logs", "game_state.json")
    if not os.path.exists(state_file):
        state_file = os.path.join(SC2_DIR, "logs", "sensor_network.json")
    if not os.path.exists(state_file):
        state_file = os.path.join(SC2_DIR, "wicked_zerg_challenger", "logs", "sensor_network.json")
    if not os.path.exists(state_file):
        return "게임 상태 데이터가 없습니다. 게임 실행 중인지 확인하세요."

    # 파일 읽기 가능 여부 확인
    if not os.access(state_file, os.R_OK):
        return f"게임 상태 파일을 읽을 수 없습니다 (권한 부족): {state_file}"
    if os.path.getsize(state_file) == 0:
        return "게임 상태 파일이 비어있습니다. 게임이 데이터를 기록할 때까지 기다려주세요."

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        warnings = []
        tips = []

        if isinstance(data, dict):
            minerals = data.get("minerals", data.get("mineral", 0))
            vespene = data.get("vespene", data.get("gas", 0))
            supply_used = data.get("supply_used", data.get("food_used", 0))
            supply_cap = data.get("supply_cap", data.get("food_cap", 200))
            idle_workers = data.get("idle_workers", 0)
            army_count = data.get("army_count", data.get("army_supply", 0))
            worker_count = data.get("worker_count", data.get("workers", 0))

            # 자원 축적 경고
            if minerals > 1000:
                warnings.append(f"미네랄 과다 축적: {minerals} (소비 필요!)")
            if minerals > 500 and vespene > 300:
                tips.append("자원이 충분합니다. 생산 시설을 추가하거나 유닛을 생산하세요.")

            # 인구수 경고
            if supply_cap > 0 and supply_used / supply_cap > 0.95:
                warnings.append(f"인구수 막힘! {supply_used}/{supply_cap} - 오버로드/서플라이 디포 필요")
            elif supply_cap > 0 and supply_used / supply_cap > 0.85:
                tips.append(f"인구수 {supply_used}/{supply_cap} - 곧 막힐 수 있으니 미리 대비하세요.")

            # 놀고 있는 일꾼
            if idle_workers > 0:
                warnings.append(f"놀고 있는 일꾼: {idle_workers}마리! 자원에 배치하세요.")

            # 일꾼 수 체크
            if worker_count < 16 and supply_used > 20:
                warnings.append(f"일꾼 부족: {worker_count}마리 (최소 16마리 이상 권장)")
            elif worker_count > 80:
                tips.append(f"일꾼 과다: {worker_count}마리. 일부를 군대로 전환하세요.")

            status = (
                f"SC2 코칭 리포트\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"미네랄: {minerals} | 가스: {vespene}\n"
                f"인구: {supply_used}/{supply_cap}\n"
                f"군대: {army_count} | 일꾼: {worker_count}\n"
            )
            if warnings:
                status += f"\n⚠️ 경고:\n" + "\n".join(f"  - {w}" for w in warnings) + "\n"
            if tips:
                status += f"\n💡 팁:\n" + "\n".join(f"  - {t}" for t in tips) + "\n"
            if not warnings and not tips:
                status += "\n✅ 현재 상태 양호!\n"

            return status

        # 리스트 형태 (sensor_network)
        if isinstance(data, list):
            counts = {}
            for entry in data:
                t = entry.get("unit_type", "UNKNOWN")
                counts[t] = counts.get(t, 0) + 1
            total = sum(counts.values())
            top_units = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
            status = f"현재 유닛 구성 (총 {total})\n"
            for uname, cnt in top_units:
                status += f"  {uname}: {cnt}\n"
            return status

        return f"알 수 없는 데이터 형식: {type(data)}"
    except Exception as e:
        return f"코칭 분석 실패: {e}"


# ──────────────────────────────────────────────
# SC2 래더 추적
# ──────────────────────────────────────────────
_LADDER_CACHE_FILE = os.path.join(SC2_DIR, "data", "ladder_tracking.json")


@mcp.tool()
async def track_ladder(player_name: str, server: str = "kr") -> str:
    """SC2 래더 점수를 조회하고 변화를 추적합니다.
    player_name: 배틀넷 닉네임
    server: 서버 (kr, us, eu)"""
    from datetime import datetime

    try:
        # SC2Pulse API 시도
        encoded_name = urllib.parse.quote(player_name)
        url = f"https://sc2pulse.nephest.com/sc2/api/character/search?term={encoded_name}"

        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-SC2/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError):
            data = []

        if data:
            # 서버 필터
            server_map = {"kr": "KR", "us": "US", "eu": "EU"}
            target_region = server_map.get(server.lower(), "KR")
            matches = [p for p in data if p.get("members", [{}])[0].get("region", {}).get("name", "") == target_region]
            if not matches:
                matches = data[:3]

            lines = [f"SC2 래더 조회: {player_name} ({server.upper()})\n━━━━━━━━━━━━━━━━━━━━"]
            for p in matches[:3]:
                members = p.get("members", [{}])
                if members:
                    m = members[0]
                    char = m.get("character", {})
                    name = char.get("name", "?")
                    realm = char.get("realm", "?")
                    region = m.get("region", {}).get("name", "?")
                    rating = p.get("ratingMax", p.get("rating", "?"))
                    league = p.get("leagueMax", {})
                    league_type = league.get("type", "?") if isinstance(league, dict) else "?"
                    race = p.get("race", {}).get("name", "?") if isinstance(p.get("race"), dict) else str(p.get("race", "?"))

                    lines.append(f"  {name}#{realm} ({region})")
                    lines.append(f"    MMR: {rating} | 리그: {league_type} | 종족: {race}")

            result = "\n".join(lines)
        else:
            result = f"'{player_name}'을(를) SC2Pulse에서 찾을 수 없습니다.\n직접 확인: https://sc2pulse.nephest.com/sc2/?type=search&name={encoded_name}"

        # 추적 기록 저장
        os.makedirs(os.path.dirname(_LADDER_CACHE_FILE), exist_ok=True)
        history = {}
        if os.path.exists(_LADDER_CACHE_FILE):
            with open(_LADDER_CACHE_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)

        key = f"{player_name}_{server}"
        if key not in history:
            history[key] = []
        history[key].append({
            "timestamp": datetime.now().isoformat(),
            "result_preview": result[:200],
        })
        # 최근 30개만 유지
        history[key] = history[key][-30:]

        # Bug fix #23: Use atomic write (tempfile + os.replace) for ladder file
        import tempfile
        ladder_dir = os.path.dirname(_LADDER_CACHE_FILE)
        temp_fd, temp_path = tempfile.mkstemp(dir=ladder_dir, suffix='.tmp')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, _LADDER_CACHE_FILE)
        except Exception:
            try:
                os.remove(temp_path)
            except OSError as oe:
                logger.debug(f"temp file cleanup failed: {oe}")
            raise

        return result
    except Exception as e:
        return f"래더 조회 실패: {e}"


if __name__ == "__main__":
    mcp.run()
