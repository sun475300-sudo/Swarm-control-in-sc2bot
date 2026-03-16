"""
SC2 봇 강화 기능 (3-1 ~ 3-5)

3-1. 실시간 게임 중계 (게임 진행 상황 실시간 업데이트)
3-2. 상대 전략 분석 (리플레이 빌드오더 탐지)
3-3. 전적 대시보드 (시간대별/맵별/종족별 승률)
3-4. 자동 리플레이 업로드 (게임 종료 시 자동 분석)
3-5. 훈련 스케줄러 (자동 봇 매치 실행)
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord.ext import commands, tasks

logger = logging.getLogger("jarvis.sc2")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC2_LOG_DIR = os.path.join(BASE_DIR, "wicked_zerg_challenger", "logs")
REPLAY_DIRS = [
    os.path.expanduser(r"~\Documents\StarCraft II\Accounts"),
    os.path.join(BASE_DIR, "replays"),
    os.path.join(BASE_DIR, "wicked_zerg_challenger", "replays"),
]
SC2_DATA_DIR = os.path.join(BASE_DIR, "data")
SC2_STATS_FILE = os.path.join(SC2_DATA_DIR, "sc2_match_history.json")
TRAINING_SCHEDULE_FILE = os.path.join(SC2_DATA_DIR, "training_schedule.json")


def _load_match_history() -> list[dict]:
    if os.path.exists(SC2_STATS_FILE):
        try:
            with open(SC2_STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_match_history(data: list[dict]):
    os.makedirs(SC2_DATA_DIR, exist_ok=True)
    with open(SC2_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_replays(limit: int = 20) -> list[str]:
    """모든 리플레이 디렉토리에서 .SC2Replay 파일 검색."""
    replays = []
    for d in REPLAY_DIRS:
        if os.path.exists(d):
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.endswith(".SC2Replay"):
                        replays.append(os.path.join(root, f))
    replays.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return replays[:limit]


class SC2FeaturesCog(commands.Cog, name="SC2 기능"):
    """StarCraft II 봇 강화 기능."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.live_channel: Optional[int] = None
        self.live_game_active = False
        try:
            self._last_replay_count = len(_find_replays(1000))
        except Exception:
            self._last_replay_count = 0
        self.training_schedules: list[dict] = self._load_schedules()
        self._last_triggered: dict[str, str] = {}  # schedule_key -> "YYYY-MM-DD HH:MM"
        self.check_new_replays.start()
        self.run_training_schedule.start()

    def cog_unload(self):
        self.check_new_replays.cancel()
        self.run_training_schedule.cancel()

    def _load_schedules(self) -> list[dict]:
        if os.path.exists(TRAINING_SCHEDULE_FILE):
            try:
                with open(TRAINING_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_schedules(self):
        os.makedirs(SC2_DATA_DIR, exist_ok=True)
        with open(TRAINING_SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.training_schedules, f, ensure_ascii=False, indent=2)

    # ── 3-1. 실시간 게임 중계 ──
    @commands.command(name="중계", aliases=["live", "실시간"])
    async def start_live(self, ctx: commands.Context):
        """SC2 게임 실시간 중계를 시작합니다."""
        self.live_channel = ctx.channel.id
        self.live_game_active = True
        embed = discord.Embed(
            title="🎮 SC2 실시간 중계 시작",
            description="게임 상황이 이 채널에 업데이트됩니다.\n`!중계중지`로 중단할 수 있습니다.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)
        if not self.live_broadcast.is_running():
            self.live_broadcast.start()

    @commands.command(name="중계중지", aliases=["stoplive"])
    async def stop_live(self, ctx: commands.Context):
        """실시간 중계를 중단합니다."""
        self.live_game_active = False
        self.live_broadcast.cancel()
        await ctx.send("🛑 실시간 중계가 중단되었습니다.")

    @tasks.loop(seconds=15)
    async def live_broadcast(self):
        """15초마다 게임 상황 업데이트."""
        if not self.live_game_active or not self.live_channel:
            return
        try:
            import sc2_mcp_server
        except ImportError:
            logger.warning("sc2_mcp_server 모듈이 설치되지 않았습니다. 실시간 중계 비활성화.")
            self.live_game_active = False
            channel = self.bot.get_channel(self.live_channel)
            if channel:
                await channel.send("⚠️ sc2_mcp_server 모듈을 찾을 수 없습니다. 중계를 중단합니다.")
            self.live_broadcast.cancel()
            return

        try:
            situation = sc2_mcp_server.get_game_situation()
            if not situation or "error" in str(situation).lower():
                return

            channel = self.bot.get_channel(self.live_channel)
            if not channel:
                return

            embed = discord.Embed(
                title="🎮 SC2 실시간 상황",
                color=discord.Color.dark_green(),
                timestamp=datetime.now(timezone.utc),
            )
            if isinstance(situation, dict):
                for key, value in situation.items():
                    embed.add_field(name=key, value=str(value)[:100], inline=True)
            else:
                embed.description = str(situation)[:2000]

            await channel.send(embed=embed)
        except Exception as e:
            logger.warning(f"실시간 중계 오류: {e}")

    @live_broadcast.before_loop
    async def before_live(self):
        await self.bot.wait_until_ready()

    # ── 3-2. 상대 전략 분석 ──
    @commands.command(name="전략분석", aliases=["buildorder", "빌드분석"])
    async def analyze_opponent(self, ctx: commands.Context, replay_index: int = 1):
        """리플레이에서 상대 전략을 분석합니다. 사용법: !전략분석 [리플레이번호]"""
        async with ctx.typing():
            replays = await asyncio.to_thread(_find_replays, 20)
            if not replays:
                await ctx.send("❌ 리플레이 파일이 없습니다.")
                return

            idx = min(max(replay_index, 1), len(replays)) - 1
            replay_path = replays[idx]

            try:
                import sc2reader
            except ImportError:
                await ctx.send("❌ `pip install sc2reader` 필요합니다.")
                return

            try:
                replay = sc2reader.load_replay(replay_path)
            except Exception as e:
                await ctx.send(f"❌ 리플레이 파일을 읽을 수 없습니다 (손상되었을 수 있음): {e}")
                return

            try:
                embed = discord.Embed(
                    title=f"🔍 전략 분석: {os.path.basename(replay_path)}",
                    color=discord.Color.purple(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(name="맵", value=replay.map_name, inline=True)
                embed.add_field(name="게임 시간", value=f"{replay.frames / 22.4 / 60:.1f}분", inline=True)

                for player in replay.players:
                    race = player.play_race
                    result = player.result if hasattr(player, "result") else "Unknown"
                    result_emoji = "🏆" if result == "Win" else "💀" if result == "Loss" else "🤝"

                    # 빌드오더 추출
                    build_events = []
                    for event in replay.events:
                        if hasattr(event, "player") and event.player == player:
                            if hasattr(event, "unit") and hasattr(event, "frame"):
                                time_sec = event.frame / 22.4
                                if time_sec <= 300:  # 처음 5분
                                    build_events.append(f"{time_sec:.0f}s: {event.unit.name if hasattr(event.unit, 'name') else event.unit}")

                    build_str = "\n".join(build_events[:15]) if build_events else "빌드 정보 없음"
                    embed.add_field(
                        name=f"{result_emoji} {player.name} ({race})",
                        value=f"결과: {result}\n**빌드오더 (5분):**\n```\n{build_str[:500]}\n```",
                        inline=False,
                    )

                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"❌ 리플레이 분석 오류: {e}")

    # ── 3-3. 전적 대시보드 ──
    @commands.command(name="대시보드", aliases=["dashboard", "전적통계"])
    async def stats_dashboard(self, ctx: commands.Context):
        """SC2 전적 대시보드를 표시합니다."""
        async with ctx.typing():
            history = _load_match_history()

            # 봇 로그에서 추가 통계 수집
            log_stats = {"win": 0, "loss": 0, "draw": 0}
            race_stats = defaultdict(lambda: {"win": 0, "loss": 0})
            map_stats = defaultdict(lambda: {"win": 0, "loss": 0})
            hourly_stats = defaultdict(lambda: {"win": 0, "loss": 0})

            # 로그 파일에서 파싱
            log_path = os.path.join(SC2_LOG_DIR, "bot.log")
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line_lower = line.lower()
                            if "result" in line_lower or "game ended" in line_lower:
                                if "win" in line_lower or "victory" in line_lower:
                                    log_stats["win"] += 1
                                elif "loss" in line_lower or "defeat" in line_lower:
                                    log_stats["loss"] += 1
                                elif "draw" in line_lower or "tie" in line_lower:
                                    log_stats["draw"] += 1
                except Exception:
                    pass

            # 매치 히스토리에서 통계
            for match in history:
                result = match.get("result", "").lower()
                race = match.get("opponent_race", "Unknown")
                map_name = match.get("map", "Unknown")
                hour = match.get("hour", 12)

                if result == "win":
                    race_stats[race]["win"] += 1
                    map_stats[map_name]["win"] += 1
                    hourly_stats[hour]["win"] += 1
                elif result in ["loss", "defeat"]:
                    race_stats[race]["loss"] += 1
                    map_stats[map_name]["loss"] += 1
                    hourly_stats[hour]["loss"] += 1

            total = log_stats["win"] + log_stats["loss"] + log_stats["draw"]
            win_rate = (log_stats["win"] / total * 100) if total > 0 else 0

            embed = discord.Embed(
                title="📊 SC2 전적 대시보드",
                color=discord.Color.dark_green(),
                timestamp=datetime.now(timezone.utc),
            )

            # 전체 전적
            embed.add_field(
                name="📈 전체 전적",
                value=f"**{total}**전 **{log_stats['win']}**승 **{log_stats['loss']}**패 **{log_stats['draw']}**무\n승률: **{win_rate:.1f}%**",
                inline=False,
            )

            # 종족별 전적
            if race_stats:
                race_text = ""
                for race, stats in sorted(race_stats.items()):
                    total_r = stats["win"] + stats["loss"]
                    wr = (stats["win"] / total_r * 100) if total_r > 0 else 0
                    race_text += f"vs {race}: {stats['win']}W {stats['loss']}L ({wr:.0f}%)\n"
                embed.add_field(name="🎯 종족별", value=race_text or "데이터 없음", inline=True)

            # 맵별 전적
            if map_stats:
                map_text = ""
                for m, stats in sorted(map_stats.items(), key=lambda x: x[1]["win"] + x[1]["loss"], reverse=True)[:5]:
                    total_m = stats["win"] + stats["loss"]
                    wr = (stats["win"] / total_m * 100) if total_m > 0 else 0
                    map_text += f"{m}: {wr:.0f}% ({total_m}판)\n"
                embed.add_field(name="🗺️ 맵별 (Top 5)", value=map_text or "데이터 없음", inline=True)

            # 리플레이 정보
            recent_replays = await asyncio.to_thread(_find_replays, 5)
            if recent_replays:
                replay_text = ""
                for r in recent_replays:
                    name = os.path.basename(r)
                    mtime = datetime.fromtimestamp(os.path.getmtime(r))
                    replay_text += f"• {name[:30]}... ({mtime.strftime('%m/%d %H:%M')})\n"
                embed.add_field(name="🎬 최근 리플레이", value=replay_text, inline=False)

            embed.set_footer(text="JARVIS SC2 Analytics")
            await ctx.send(embed=embed)

    # ── 리플레이 목록 조회 ──
    @commands.command(name="리플레이", aliases=["replays", "리플레이목록"])
    async def list_replays(self, ctx: commands.Context, count: int = 10):
        """최근 리플레이 파일 목록을 표시합니다. 사용법: !리플레이 [개수]"""
        count = min(max(count, 1), 30)
        async with ctx.typing():
            replays = await asyncio.to_thread(_find_replays, count)
            if not replays:
                await ctx.send("❌ 리플레이 파일이 없습니다.")
                return

            embed = discord.Embed(
                title=f"🎬 최근 리플레이 목록 ({len(replays)}개)",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc),
            )

            for i, replay_path in enumerate(replays, 1):
                name = os.path.basename(replay_path)
                try:
                    size = os.path.getsize(replay_path)
                    mtime = datetime.fromtimestamp(os.path.getmtime(replay_path))
                    size_str = f"{size / 1024:.1f} KB"
                    time_str = mtime.strftime("%m/%d %H:%M")
                except OSError:
                    size_str = "? KB"
                    time_str = "?"

                # sc2reader로 추가 정보 시도
                detail = ""
                try:
                    import sc2reader
                    replay = sc2reader.load_replay(replay_path)
                    players = " vs ".join(f"{p.name}({p.play_race})" for p in replay.players)
                    detail = f"\n{players} | {replay.map_name}"
                except Exception:
                    pass

                embed.add_field(
                    name=f"#{i} {name[:40]}",
                    value=f"📅 {time_str} | 📦 {size_str}{detail}",
                    inline=False,
                )

            embed.set_footer(text="!전략분석 <번호> 로 상세 분석")
            await ctx.send(embed=embed)

    # ── 3-4. 자동 리플레이 업로드 ──
    @tasks.loop(seconds=30)
    async def check_new_replays(self):
        """새 리플레이 파일이 생성되면 자동 분석."""
        try:
            current_count = len(await asyncio.to_thread(_find_replays, 1000))
        except (OSError, PermissionError) as e:
            logger.debug(f"리플레이 디렉토리 접근 오류: {e}")
            return
        except Exception as e:
            logger.warning(f"리플레이 검색 중 예외: {e}")
            return

        if current_count > self._last_replay_count:
            self._last_replay_count = current_count
            try:
                replays = await asyncio.to_thread(_find_replays, 1)
                if replays:
                    replay_path = replays[0]
                    # 파일이 아직 쓰기 중일 수 있으므로 잠시 대기
                    await asyncio.sleep(2)
                    if os.path.exists(replay_path):
                        await self._auto_analyze_replay(replay_path)
            except (OSError, PermissionError) as e:
                logger.debug(f"새 리플레이 파일 접근 오류: {e}")
            except Exception as e:
                logger.warning(f"자동 리플레이 처리 실패: {e}")

    @check_new_replays.before_loop
    async def before_check_replays(self):
        await self.bot.wait_until_ready()

    async def _auto_analyze_replay(self, replay_path: str):
        """새 리플레이 자동 분석 및 알림."""
        channel_id = int(os.environ.get("BRIEFING_CHANNEL_ID", "0"))
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        try:
            import sc2reader
        except ImportError:
            embed = discord.Embed(
                title="🎬 새 리플레이 감지",
                description=f"{os.path.basename(replay_path)}\n(sc2reader 미설치로 상세 분석 불가)",
                color=discord.Color.gold(),
            )
            await channel.send(embed=embed)
            return

        try:
            replay = sc2reader.load_replay(replay_path)
        except Exception as e:
            logger.warning(f"리플레이 파일 로드 실패 (손상 가능): {replay_path} - {e}")
            embed = discord.Embed(
                title="🎬 새 리플레이 감지 (분석 실패)",
                description=f"{os.path.basename(replay_path)}\n리플레이 파일을 읽을 수 없습니다 (손상 가능).",
                color=discord.Color.orange(),
            )
            await channel.send(embed=embed)
            return

        try:
            embed = discord.Embed(
                title="🎬 새 리플레이 감지!",
                description=os.path.basename(replay_path),
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="맵", value=replay.map_name, inline=True)
            embed.add_field(name="길이", value=f"{replay.frames / 22.4 / 60:.1f}분", inline=True)

            for player in replay.players:
                result = player.result if hasattr(player, "result") else "?"
                embed.add_field(
                    name=f"{player.name} ({player.play_race})",
                    value=f"결과: {result}",
                    inline=True,
                )

            # 매치 히스토리에 저장
            match_data = {
                "replay": os.path.basename(replay_path),
                "map": replay.map_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "players": [
                    {"name": p.name, "race": p.play_race, "result": getattr(p, "result", "Unknown")}
                    for p in replay.players
                ],
            }
            history = _load_match_history()
            history.append(match_data)
            _save_match_history(history[-500:])

            # 리플레이 파일 첨부 (10MB 미만)
            if os.path.getsize(replay_path) < 10 * 1024 * 1024:
                file = discord.File(replay_path, filename=os.path.basename(replay_path))
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)

        except Exception as e:
            logger.warning(f"자동 리플레이 분석 실패: {e}")

    # ── 3-5. 훈련 스케줄러 ──
    @commands.command(name="훈련", aliases=["training", "훈련설정"])
    async def set_training(self, ctx: commands.Context, time_str: str = "", *, description: str = "자동 훈련"):
        """봇 매치 훈련 스케줄을 설정합니다. 사용법: !훈련 14:00 래더 연습"""
        if not time_str:
            # 현재 스케줄 표시
            if not self.training_schedules:
                await ctx.send("📋 설정된 훈련 스케줄이 없습니다.\n사용법: `!훈련 14:00 래더 연습`")
                return
            embed = discord.Embed(title="📋 훈련 스케줄", color=discord.Color.green())
            for i, s in enumerate(self.training_schedules, 1):
                embed.add_field(
                    name=f"#{i} {s['time']}",
                    value=f"{s['description']}\n상태: {'✅ 활성' if s.get('active', True) else '❌ 비활성'}",
                    inline=True,
                )
            embed.set_footer(text="!훈련삭제 <번호>로 삭제 가능")
            await ctx.send(embed=embed)
            return

        # 시간 파싱
        try:
            hour, minute = map(int, time_str.split(":"))
            assert 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AssertionError):
            await ctx.send("❌ 시간 형식: HH:MM (예: 14:00)")
            return

        schedule = {
            "time": time_str,
            "hour": hour,
            "minute": minute,
            "description": description,
            "active": True,
            "channel_id": ctx.channel.id,
            "created_by": ctx.author.id,
        }
        self.training_schedules.append(schedule)
        self._save_schedules()

        embed = discord.Embed(
            title="✅ 훈련 스케줄 등록",
            color=discord.Color.green(),
        )
        embed.add_field(name="시간", value=time_str, inline=True)
        embed.add_field(name="설명", value=description, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="훈련삭제", aliases=["deltraining"])
    async def delete_training(self, ctx: commands.Context, index: int):
        """훈련 스케줄을 삭제합니다. 사용법: !훈련삭제 1"""
        if index < 1 or index > len(self.training_schedules):
            await ctx.send(f"❌ 유효 범위: 1~{len(self.training_schedules)}")
            return
        removed = self.training_schedules.pop(index - 1)
        self._save_schedules()
        await ctx.send(f"✅ 훈련 스케줄 삭제: {removed['time']} - {removed['description']}")

    @tasks.loop(minutes=1)
    async def run_training_schedule(self):
        """매분 훈련 스케줄 확인."""
        now = datetime.now()
        current_minute_key = now.strftime("%Y-%m-%d %H:%M")
        for i, schedule in enumerate(self.training_schedules):
            if not schedule.get("active", True):
                continue
            if now.hour == schedule["hour"] and now.minute == schedule["minute"]:
                schedule_key = f"{i}_{schedule['time']}"
                if self._last_triggered.get(schedule_key) == current_minute_key:
                    continue
                self._last_triggered[schedule_key] = current_minute_key
                channel = self.bot.get_channel(schedule.get("channel_id"))
                if channel:
                    await channel.send(f"🎮 **훈련 시작**: {schedule['description']}")
                    try:
                        import sc2_mcp_server
                        result = sc2_mcp_server.run_sc2_test_game()
                        await channel.send(f"🏁 훈련 결과: {result}")
                    except Exception as e:
                        await channel.send(f"⚠️ 훈련 실행 실패: {e}")

    @run_training_schedule.before_loop
    async def before_training(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(SC2FeaturesCog(bot))
