"""
생산성/일정 기능 (5-1 ~ 5-5)

5-1. 투두 리스트 (할 일 관리)
5-2. 리마인더 강화 (반복 알림)
5-3. 뽀모도로 타이머
5-4. 회의록 자동 생성 (보이스 요약)
5-5. 습관 트래커 (매일 체크인)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger("jarvis.productivity")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TODO_FILE = os.path.join(DATA_DIR, "todos.json")
REMINDER_FILE = os.path.join(DATA_DIR, "reminders.json")
HABIT_FILE = os.path.join(DATA_DIR, "habits.json")
POMO_STATS_FILE = os.path.join(DATA_DIR, "pomodoro_stats.json")


def _load_json(path: str):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ProductivityCog(commands.Cog, name="생산성"):
    """생산성/일정 관리 기능."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        data = _load_json(TODO_FILE)
        self.todos: dict[str, list] = data if data else {}
        data = _load_json(REMINDER_FILE)
        self.reminders: list[dict] = data if isinstance(data, list) else []
        data = _load_json(HABIT_FILE)
        self.habits: dict[str, dict] = data if data else {}
        self.active_pomodoros: dict[int, dict] = {}  # user_id -> pomodoro state
        data = _load_json(POMO_STATS_FILE)
        self.pomo_stats: dict[str, dict] = data if data else {}
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    # ═══════════════════════════════════════════════════════════════════════════
    # 5-1. 투두 리스트
    # ═══════════════════════════════════════════════════════════════════════════

    def _parse_due_date(self, text: str) -> Optional[datetime]:
        """한국어 마감일 표현을 파싱합니다. (내일까지, 금요일까지, N일후까지 등)"""
        import re
        now = datetime.now(timezone.utc)

        # "내일까지"
        if "내일까지" in text or "내일" in text:
            return now + timedelta(days=1)

        # "모레까지"
        if "모레까지" in text or "모레" in text:
            return now + timedelta(days=2)

        # "오늘까지"
        if "오늘까지" in text:
            return now

        # "N일후까지" / "N일뒤까지" / "N일후" / "N일뒤"
        m = re.search(r"(\d+)\s*일\s*(후|뒤)(?:까지)?", text)
        if m:
            return now + timedelta(days=int(m.group(1)))

        # "N주후까지"
        m = re.search(r"(\d+)\s*주\s*(후|뒤)(?:까지)?", text)
        if m:
            return now + timedelta(weeks=int(m.group(1)))

        # 요일까지 (월~일)
        weekday_map = {
            "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3,
            "금요일": 4, "토요일": 5, "일요일": 6,
        }
        for day_name, day_num in weekday_map.items():
            if day_name + "까지" in text or day_name in text:
                current_weekday = now.weekday()
                days_ahead = day_num - current_weekday
                if days_ahead <= 0:
                    days_ahead += 7
                return now + timedelta(days=days_ahead)

        # "YYYY-MM-DD" or "MM/DD" 형식
        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass

        m = re.search(r"(\d{1,2})/(\d{1,2})(?:까지)?", text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                try:
                    return datetime(now.year, month, day, tzinfo=timezone.utc)
                except ValueError:
                    pass

        return None

    def _remove_due_date_text(self, text: str) -> str:
        """마감일 관련 텍스트를 제거하고 깔끔한 할일 내용을 반환합니다."""
        import re
        patterns = [
            r"\d{4}-\d{1,2}-\d{1,2}까지\s*",
            r"\d{1,2}/\d{1,2}까지\s*",
            r"\d+\s*주\s*(?:후|뒤)(?:까지)?\s*",
            r"\d+\s*일\s*(?:후|뒤)(?:까지)?\s*",
            r"(?:월|화|수|목|금|토|일)요일까지\s*",
            r"(?:내일|모레|오늘)까지\s*",
        ]
        result = text
        for pat in patterns:
            result = re.sub(pat, "", result)
        return result.strip() or text.strip()

    def _get_user_todos(self, user_id: int) -> list:
        uid = str(user_id)
        if uid not in self.todos:
            self.todos[uid] = []
        return self.todos[uid]

    @commands.group(name="할일", aliases=["todo"], invoke_without_command=True)
    async def todo_group(self, ctx: commands.Context):
        """할 일 목록을 확인합니다."""
        todos = self._get_user_todos(ctx.author.id)
        if not todos:
            await ctx.send("📋 할 일이 없습니다. `!할일 추가 <내용>`으로 추가하세요.")
            return

        embed = discord.Embed(
            title=f"📋 {ctx.author.display_name}의 할 일 목록",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )

        pending = [t for t in todos if not t.get("done")]
        done = [t for t in todos if t.get("done")]

        if pending:
            lines = []
            for i, t in enumerate(pending):
                line = f"**{i+1}.** ⬜ {t['content']}"
                if t.get('priority'):
                    line += f" (우선: {'🔴' if t['priority'] == 'high' else '🟡' if t['priority'] == 'mid' else '🟢'})"
                if t.get('due_date'):
                    line += f" 📅 {t['due_date']}"
                lines.append(line)
            text = "\n".join(lines)
            embed.add_field(name=f"미완료 ({len(pending)})", value=text[:1024], inline=False)

        if done:
            text = "\n".join(f"~~{t['content']}~~" for t in done[-5:])
            embed.add_field(name=f"완료 ({len(done)})", value=text[:1024], inline=False)

        embed.set_footer(text="!할일 추가/완료/삭제/초기화")
        await ctx.send(embed=embed)

    @todo_group.command(name="추가", aliases=["add", "a"])
    async def todo_add(self, ctx: commands.Context, *, content: str):
        """할 일을 추가합니다. 사용법: !할일 추가 장보기 내일까지 / !할일 추가 보고서 금요일까지"""
        todos = self._get_user_todos(ctx.author.id)

        # 우선순위 파싱
        priority = None
        for tag in ["!높음", "!high", "!중간", "!mid", "!낮음", "!low"]:
            if tag in content:
                content = content.replace(tag, "").strip()
                priority = {"!높음": "high", "!high": "high", "!중간": "mid", "!mid": "mid", "!낮음": "low", "!low": "low"}[tag]

        # 마감일 파싱
        due_date = self._parse_due_date(content)
        clean_content = self._remove_due_date_text(content) if due_date else content

        todo = {
            "content": clean_content,
            "done": False,
            "priority": priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if due_date:
            todo["due_date"] = due_date.strftime("%Y-%m-%d")

        todos.append(todo)
        _save_json(TODO_FILE, self.todos)
        msg = f"✅ 할 일 추가: **{clean_content}**"
        if priority:
            msg += f" (우선순위: {priority})"
        if due_date:
            msg += f" (마감: {due_date.strftime('%Y-%m-%d')})"
        await ctx.send(msg)

    @todo_group.command(name="완료", aliases=["done", "d", "check"])
    async def todo_done(self, ctx: commands.Context, index: int):
        """할 일을 완료 표시합니다. 사용법: !할일 완료 1"""
        todos = self._get_user_todos(ctx.author.id)
        pending = [t for t in todos if not t.get("done")]
        if index < 1 or index > len(pending):
            await ctx.send(f"❌ 번호 범위: 1~{len(pending)}")
            return
        pending[index - 1]["done"] = True
        pending[index - 1]["done_at"] = datetime.now(timezone.utc).isoformat()
        _save_json(TODO_FILE, self.todos)
        await ctx.send(f"✅ 완료: ~~{pending[index - 1]['content']}~~")

    @todo_group.command(name="삭제", aliases=["delete", "del", "remove"])
    async def todo_delete(self, ctx: commands.Context, index: int):
        """할 일을 삭제합니다. 사용법: !할일 삭제 1"""
        todos = self._get_user_todos(ctx.author.id)
        pending = [t for t in todos if not t.get("done")]
        if index < 1 or index > len(pending):
            await ctx.send(f"❌ 번호 범위: 1~{len(pending)}")
            return
        removed = pending[index - 1]
        todos.remove(removed)
        _save_json(TODO_FILE, self.todos)
        await ctx.send(f"🗑️ 삭제: {removed['content']}")

    @todo_group.command(name="초기화", aliases=["clear", "reset"])
    async def todo_clear(self, ctx: commands.Context):
        """완료된 할 일을 모두 삭제합니다."""
        todos = self._get_user_todos(ctx.author.id)
        before = len(todos)
        self.todos[str(ctx.author.id)] = [t for t in todos if not t.get("done")]
        after = len(self.todos[str(ctx.author.id)])
        _save_json(TODO_FILE, self.todos)
        await ctx.send(f"🧹 완료 항목 {before - after}개 삭제됨")

    @app_commands.command(name="todo", description="할 일 목록을 확인하거나 추가합니다")
    @app_commands.describe(action="동작 (목록/추가/완료)", content="할 일 내용 또는 완료할 번호")
    @app_commands.choices(action=[
        app_commands.Choice(name="목록", value="list"),
        app_commands.Choice(name="추가", value="add"),
        app_commands.Choice(name="완료", value="done"),
    ])
    async def todo_slash(self, interaction: discord.Interaction, action: str = "list", content: str = ""):
        uid = str(interaction.user.id)
        if uid not in self.todos:
            self.todos[uid] = []
        todos = self.todos[uid]

        if action == "list":
            if not todos:
                await interaction.response.send_message("📋 할 일이 없습니다. `/todo add <내용>`으로 추가하세요.", ephemeral=True)
                return
            pending = [t for t in todos if not t.get("done")]
            done = [t for t in todos if t.get("done")]
            embed = discord.Embed(title=f"📋 {interaction.user.display_name}의 할 일 목록", color=discord.Color.blue())
            if pending:
                text = "\n".join(
                    f"**{i+1}.** ⬜ {t['content']}" + (f" 📅 {t['due_date']}" if t.get('due_date') else "")
                    for i, t in enumerate(pending)
                )
                embed.add_field(name=f"미완료 ({len(pending)})", value=text[:1024], inline=False)
            if done:
                text = "\n".join(f"~~{t['content']}~~" for t in done[-5:])
                embed.add_field(name=f"완료 ({len(done)})", value=text[:1024], inline=False)
            await interaction.response.send_message(embed=embed)

        elif action == "add":
            if not content:
                await interaction.response.send_message("❌ 내용을 입력해주세요.", ephemeral=True)
                return
            due_date = self._parse_due_date(content)
            clean_content = self._remove_due_date_text(content)
            todo = {
                "content": clean_content,
                "done": False,
                "priority": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if due_date:
                todo["due_date"] = due_date.strftime("%Y-%m-%d")
            todos.append(todo)
            _save_json(TODO_FILE, self.todos)
            msg = f"✅ 할 일 추가: **{clean_content}**"
            if due_date:
                msg += f" (마감: {due_date.strftime('%Y-%m-%d')})"
            await interaction.response.send_message(msg)

        elif action == "done":
            try:
                index = int(content)
            except ValueError:
                await interaction.response.send_message("❌ 완료할 번호를 입력해주세요.", ephemeral=True)
                return
            pending = [t for t in todos if not t.get("done")]
            if index < 1 or index > len(pending):
                await interaction.response.send_message(f"❌ 번호 범위: 1~{len(pending)}", ephemeral=True)
                return
            pending[index - 1]["done"] = True
            pending[index - 1]["done_at"] = datetime.now(timezone.utc).isoformat()
            _save_json(TODO_FILE, self.todos)
            await interaction.response.send_message(f"✅ 완료: ~~{pending[index - 1]['content']}~~")

    # ═══════════════════════════════════════════════════════════════════════════
    # 5-2. 리마인더
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="알려줘", aliases=["remind", "리마인더"])
    async def set_reminder(self, ctx: commands.Context, *, text: str):
        """리마인더를 설정합니다. 사용법: !알려줘 30분후 회의 / !알려줘 매일 9시 물마시기"""
        import re

        # 시간 파싱
        minutes = 0
        repeat = None
        message = text

        # "매일 HH시" 패턴 (check first since it's the most specific)
        m = re.search(r"매일\s*(\d{1,2})\s*시", text)
        if m:
            repeat = "daily"
            hour = int(m.group(1))
            now = datetime.now()
            target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            minutes = int((target - now).total_seconds() / 60)
            message = text.replace(m.group(0), "").strip()

        # "N일후"
        elif re.search(r"(\d+)\s*일\s*후?", text):
            m = re.search(r"(\d+)\s*일\s*후?", text)
            minutes = int(m.group(1)) * 24 * 60
            message = text.replace(m.group(0), "").strip()

        # "N시간후"
        elif re.search(r"(\d+)\s*시간\s*후?", text):
            m = re.search(r"(\d+)\s*시간\s*후?", text)
            minutes = int(m.group(1)) * 60
            message = text.replace(m.group(0), "").strip()

        # "N분후"
        elif re.search(r"(\d+)\s*분\s*후?", text):
            m = re.search(r"(\d+)\s*분\s*후?", text)
            minutes = int(m.group(1))
            message = text.replace(m.group(0), "").strip()

        if minutes <= 0:
            await ctx.send("❌ 시간을 지정해주세요. 예: `!알려줘 30분후 회의` 또는 `!알려줘 매일 9시 운동`")
            return

        trigger_at = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()

        reminder = {
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "message": message or "리마인더",
            "trigger_at": trigger_at,
            "repeat": repeat,
            "triggered": False,
        }
        self.reminders.append(reminder)
        _save_json(REMINDER_FILE, self.reminders)

        time_str = f"{minutes}분" if minutes < 60 else f"{minutes // 60}시간 {minutes % 60}분"
        repeat_str = " (매일 반복)" if repeat == "daily" else ""
        await ctx.send(f"⏰ 리마인더 설정: **{message}** - {time_str} 후{repeat_str}")

    @commands.command(name="리마인더목록", aliases=["reminders", "내리마인더"])
    async def list_reminders(self, ctx: commands.Context):
        """리마인더 목록을 확인합니다."""
        user_reminders = [r for r in self.reminders if r["user_id"] == ctx.author.id and not r["triggered"]]
        if not user_reminders:
            await ctx.send("📭 설정된 리마인더가 없습니다.")
            return
        embed = discord.Embed(title="⏰ 내 리마인더 목록", color=discord.Color.gold())
        for i, r in enumerate(user_reminders, 1):
            try:
                trigger = datetime.fromisoformat(r["trigger_at"]).strftime("%m/%d %H:%M")
            except (ValueError, TypeError):
                trigger = r.get("trigger_at", "???")
            repeat_str = " 🔁" if r.get("repeat") else ""
            embed.add_field(name=f"#{i}{repeat_str}", value=f"{r['message']}\n⏰ {trigger}", inline=True)
        await ctx.send(embed=embed)

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        """30초마다 리마인더 확인."""
        now = datetime.now(timezone.utc)
        triggered = []
        for reminder in self.reminders:
            if reminder["triggered"]:
                continue
            try:
                trigger_at = datetime.fromisoformat(reminder["trigger_at"])
            except (ValueError, TypeError):
                reminder["triggered"] = True
                continue
            if now >= trigger_at:
                triggered.append(reminder)

        for reminder in triggered:
            try:
                channel = self.bot.get_channel(reminder["channel_id"])
                user = await self.bot.fetch_user(reminder["user_id"])

                embed = discord.Embed(
                    title="⏰ 리마인더!",
                    description=f"**{reminder['message']}**",
                    color=discord.Color.orange(),
                    timestamp=now,
                )

                if channel:
                    await channel.send(f"{user.mention}", embed=embed)
                else:
                    await user.send(embed=embed)

                if reminder.get("repeat") == "daily":
                    reminder["trigger_at"] = (now + timedelta(days=1)).isoformat()
                else:
                    reminder["triggered"] = True

            except Exception as e:
                logger.warning(f"리마인더 전송 실패: {e}")
                reminder["triggered"] = True

        if triggered:
            _save_json(REMINDER_FILE, self.reminders)

    @check_reminders.before_loop
    async def before_reminders(self):
        await self.bot.wait_until_ready()

    # ═══════════════════════════════════════════════════════════════════════════
    # 5-3. 뽀모도로 타이머
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="뽀모", aliases=["pomodoro", "pomo"])
    async def pomodoro(self, ctx: commands.Context, minutes: int = 25):
        """뽀모도로 타이머를 시작합니다. 사용법: !뽀모 25"""
        user_id = ctx.author.id
        minutes = min(max(minutes, 1), 120)

        if user_id in self.active_pomodoros:
            pomo = self.active_pomodoros[user_id]
            if not pomo.get("done"):
                remaining = pomo["end_time"] - datetime.now(timezone.utc)
                if remaining.total_seconds() > 0:
                    await ctx.send(f"⏳ 진행 중인 뽀모도로가 있습니다. 남은 시간: {int(remaining.total_seconds() / 60)}분")
                    return

        end_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.active_pomodoros[user_id] = {
            "start_time": datetime.now(timezone.utc),
            "end_time": end_time,
            "minutes": minutes,
            "channel_id": ctx.channel.id,
            "is_break": False,
            "done": False,
            "sessions": self.active_pomodoros.get(user_id, {}).get("sessions", 0),
        }

        embed = discord.Embed(
            title="🍅 뽀모도로 시작!",
            description=f"**{minutes}분** 집중 시간입니다. 화이팅!",
            color=discord.Color.red(),
        )
        embed.add_field(name="종료 시각", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        embed.add_field(name="완료 세션", value=f"{self.active_pomodoros[user_id]['sessions']}회", inline=True)
        embed.set_footer(text="!뽀모중지 로 중단")
        await ctx.send(embed=embed)

        # 타이머 비동기 실행 -- store the task for cancellation
        async def _pomo_wait():
            await asyncio.sleep(minutes * 60)
        task = asyncio.create_task(_pomo_wait())
        self.active_pomodoros[user_id]["_task"] = task
        try:
            await task
        except asyncio.CancelledError:
            return

        if user_id in self.active_pomodoros and not self.active_pomodoros[user_id]["done"]:
            self.active_pomodoros[user_id]["done"] = True
            self.active_pomodoros[user_id]["sessions"] += 1
            sessions = self.active_pomodoros[user_id]["sessions"]

            # 통계 업데이트
            uid = str(user_id)
            if uid not in self.pomo_stats:
                self.pomo_stats[uid] = {"total_sessions": 0, "total_focus_minutes": 0, "history": []}
            self.pomo_stats[uid]["total_sessions"] += 1
            self.pomo_stats[uid]["total_focus_minutes"] += minutes
            self.pomo_stats[uid]["history"].append({
                "date": datetime.now(timezone.utc).isoformat(),
                "minutes": minutes,
            })
            # 히스토리는 최근 200개만 유지
            self.pomo_stats[uid]["history"] = self.pomo_stats[uid]["history"][-200:]
            _save_json(POMO_STATS_FILE, self.pomo_stats)

            channel = self.bot.get_channel(ctx.channel.id)
            if channel:
                is_long_break = sessions % 4 == 0
                break_time = 15 if is_long_break else 5
                break_type = "긴 휴식" if is_long_break else "짧은 휴식"

                total_focus = self.pomo_stats[uid]["total_focus_minutes"]
                total_hours = total_focus // 60
                total_mins = total_focus % 60

                embed = discord.Embed(
                    title="🍅 뽀모도로 완료!",
                    description=f"잘했어요! {break_type} **{break_time}분**을 가지세요.",
                    color=discord.Color.green(),
                )
                embed.add_field(name="오늘 세션", value=f"{sessions}회", inline=True)
                embed.add_field(name="누적 세션", value=f"{self.pomo_stats[uid]['total_sessions']}회", inline=True)
                embed.add_field(name="누적 집중", value=f"{total_hours}시간 {total_mins}분", inline=True)
                embed.add_field(name="다음", value=f"`!뽀모 {minutes}` 로 재시작", inline=True)
                await channel.send(f"{ctx.author.mention}", embed=embed)

    @commands.command(name="뽀모중지", aliases=["pomostop"])
    async def pomo_stop(self, ctx: commands.Context):
        """뽀모도로를 중단합니다."""
        user_id = ctx.author.id
        if user_id in self.active_pomodoros:
            pomo = self.active_pomodoros[user_id]
            pomo["done"] = True
            task = pomo.get("_task")
            if task and not task.done():
                task.cancel()
            await ctx.send("🛑 뽀모도로가 중단되었습니다.")
        else:
            await ctx.send("진행 중인 뽀모도로가 없습니다.")

    @commands.command(name="뽀모통계", aliases=["pomostats", "pomostat"])
    async def pomo_stats_cmd(self, ctx: commands.Context):
        """뽀모도로 통계를 확인합니다."""
        uid = str(ctx.author.id)
        stats = self.pomo_stats.get(uid)
        if not stats or stats.get("total_sessions", 0) == 0:
            await ctx.send("📊 뽀모도로 기록이 없습니다. `!뽀모`로 시작해보세요!")
            return

        total_sessions = stats["total_sessions"]
        total_minutes = stats["total_focus_minutes"]
        total_hours = total_minutes // 60
        total_mins = total_minutes % 60

        # 최근 7일 통계
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        def _safe_parse(d):
            try:
                return datetime.fromisoformat(d)
            except (ValueError, TypeError):
                return None
        recent = [h for h in stats.get("history", [])
                  if (_dt := _safe_parse(h.get("date"))) and _dt >= week_ago]
        week_sessions = len(recent)
        week_minutes = sum(h["minutes"] for h in recent)

        # 오늘 통계
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today = [h for h in stats.get("history", [])
                 if (_dt := _safe_parse(h.get("date"))) and _dt >= today_start]
        today_sessions = len(today)
        today_minutes = sum(h["minutes"] for h in today)

        embed = discord.Embed(
            title=f"🍅 {ctx.author.display_name}의 뽀모도로 통계",
            color=discord.Color.red(),
            timestamp=now,
        )
        embed.add_field(name="📊 전체 세션", value=f"**{total_sessions}**회", inline=True)
        embed.add_field(name="⏱️ 전체 집중 시간", value=f"**{total_hours}**시간 **{total_mins}**분", inline=True)
        embed.add_field(name="📐 평균 세션 길이", value=f"**{total_minutes // total_sessions}**분", inline=True)
        embed.add_field(name="📅 오늘", value=f"{today_sessions}회 / {today_minutes}분", inline=True)
        embed.add_field(name="📅 최근 7일", value=f"{week_sessions}회 / {week_minutes}분", inline=True)

        # 최근 7일 시각화
        day_counts = {}
        for h in recent:
            _parsed = _safe_parse(h.get("date"))
            if not _parsed:
                continue
            day = _parsed.strftime("%m/%d")
            day_counts[day] = day_counts.get(day, 0) + 1
        if day_counts:
            chart = " | ".join(f"{d}: {'🍅' * min(c, 8)}" for d, c in sorted(day_counts.items()))
            embed.add_field(name="최근 활동", value=chart[:1024], inline=False)

        embed.set_footer(text="꾸준한 집중이 성공의 비결!")
        await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 5-4. 회의록 자동 생성
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="회의록", aliases=["meeting", "minutes"])
    async def meeting_notes(self, ctx: commands.Context, count: int = 100):
        """채널 대화를 기반으로 회의록을 생성합니다. 사용법: !회의록 [메시지수]"""
        count = min(max(count, 20), 500)

        async with ctx.typing():
            messages = []
            async for msg in ctx.channel.history(limit=count):
                if not msg.author.bot:
                    messages.append({
                        "author": msg.author.display_name,
                        "content": msg.content,
                        "time": msg.created_at.strftime("%H:%M"),
                    })
            messages.reverse()

            if len(messages) < 3:
                await ctx.send("회의록을 작성할 메시지가 부족합니다.")
                return

            conversation = "\n".join(f"[{m['time']}] {m['author']}: {m['content']}" for m in messages)

            # AI로 회의록 생성
            claude_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            meeting_notes = None
            if claude_key:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": claude_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": "claude-sonnet-4-5-20250929",
                            "max_tokens": 2048,
                            "system": "당신은 전문 회의록 작성자입니다. 대화 내용을 분석하여 구조화된 회의록을 한국어로 작성해주세요.",
                            "messages": [{"role": "user", "content": f"다음 대화를 바탕으로 회의록을 작성해주세요. "
                                f"안건, 논의사항, 결정사항, 액션아이템(담당자 포함)을 포함해주세요:\n\n{conversation[:6000]}"}],
                        },
                    ) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                            except Exception:
                                data = {}
                            content = data.get("content") or []
                            if content and isinstance(content, list):
                                meeting_notes = content[0].get("text")

            if not meeting_notes:
                # 폴백: 수동 정리
                participants = set(m["author"] for m in messages)
                meeting_notes = (
                    f"**참여자:** {', '.join(participants)}\n"
                    f"**메시지 수:** {len(messages)}개\n"
                    f"**시간:** {messages[0]['time']} ~ {messages[-1]['time']}\n\n"
                    f"_AI 회의록을 위해 CLAUDE_API_KEY를 설정해주세요._"
                )

            embed = discord.Embed(
                title="📝 회의록",
                description=meeting_notes[:4000],
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"메시지 {len(messages)}개 기반 | {ctx.author.display_name}")
            await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 5-5. 습관 트래커
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.group(name="습관", aliases=["habit"], invoke_without_command=True)
    async def habit_group(self, ctx: commands.Context):
        """습관 트래커를 확인합니다."""
        uid = str(ctx.author.id)
        user_habits = self.habits.get(uid, {})

        if not user_habits:
            await ctx.send("📊 등록된 습관이 없습니다. `!습관 추가 <습관이름>`으로 시작하세요.")
            return

        embed = discord.Embed(
            title=f"📊 {ctx.author.display_name}의 습관 트래커",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        today = datetime.now().strftime("%Y-%m-%d")
        for name, data in user_habits.items():
            checkins = data.get("checkins", [])
            streak = data.get("streak", 0)
            today_done = today in checkins

            # 최근 7일 시각화
            week_display = ""
            for i in range(6, -1, -1):
                day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                week_display += "🟢" if day in checkins else "⚪"

            status = "✅ 완료" if today_done else "⬜ 미완료"
            embed.add_field(
                name=f"{name} {status}",
                value=f"🔥 연속: **{streak}일** | 총: {len(checkins)}일\n최근 7일: {week_display}",
                inline=False,
            )

        embed.set_footer(text="!습관 체크 <이름> | !습관 추가 <이름>")
        await ctx.send(embed=embed)

    @habit_group.command(name="추가", aliases=["add", "new"])
    async def habit_add(self, ctx: commands.Context, *, name: str):
        """습관을 추가합니다. 사용법: !습관 추가 운동"""
        uid = str(ctx.author.id)
        if uid not in self.habits:
            self.habits[uid] = {}

        if name in self.habits[uid]:
            await ctx.send(f"이미 등록된 습관: **{name}**")
            return

        self.habits[uid][name] = {
            "checkins": [],
            "streak": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_json(HABIT_FILE, self.habits)
        await ctx.send(f"✅ 습관 추가: **{name}**\n매일 `!습관 체크 {name}`으로 체크하세요!")

    @habit_group.command(name="체크", aliases=["check", "done"])
    async def habit_check(self, ctx: commands.Context, *, name: str):
        """습관을 체크합니다. 사용법: !습관 체크 운동"""
        uid = str(ctx.author.id)
        if uid not in self.habits or name not in self.habits[uid]:
            await ctx.send(f"❌ 등록되지 않은 습관: **{name}**")
            return

        habit = self.habits[uid][name]
        today = datetime.now().strftime("%Y-%m-%d")

        if today in habit["checkins"]:
            await ctx.send(f"이미 오늘 체크했어요! ✅ **{name}**")
            return

        habit["checkins"].append(today)

        # 연속일 계산
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if yesterday in habit["checkins"]:
            habit["streak"] = habit.get("streak", 0) + 1
        else:
            habit["streak"] = 1

        _save_json(HABIT_FILE, self.habits)

        streak = habit["streak"]
        milestone = ""
        if streak in [7, 14, 21, 30, 50, 100]:
            milestone = f"\n🎉 **{streak}일 연속 달성!** 대단해요!"

        await ctx.send(f"✅ **{name}** 체크 완료! 🔥 {streak}일 연속{milestone}")

    @habit_group.command(name="삭제", aliases=["delete", "remove"])
    async def habit_delete(self, ctx: commands.Context, *, name: str):
        """습관을 삭제합니다."""
        uid = str(ctx.author.id)
        if uid not in self.habits or name not in self.habits[uid]:
            await ctx.send(f"❌ 등록되지 않은 습관: **{name}**")
            return
        del self.habits[uid][name]
        _save_json(HABIT_FILE, self.habits)
        await ctx.send(f"🗑️ 습관 삭제: **{name}**")


async def setup(bot: commands.Bot):
    await bot.add_cog(ProductivityCog(bot))
