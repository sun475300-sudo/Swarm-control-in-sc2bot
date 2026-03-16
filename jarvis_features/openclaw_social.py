# -*- coding: utf-8 -*-
"""OpenClaw 소셜/통신 스킬 Cog (twitter, instagram, slack, email, notion, trello, remindme)."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import re
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.social")

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


class OpenClawSocialCog(commands.Cog, name="OpenClaw 소셜"):
    """트위터, 인스타, 슬랙, 이메일, 노션, 트렐로, 리마인더"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()

    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.blurple()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.blurple()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw command error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc트위터 ──────────────────────────────────────────────────
    @app_commands.command(name="oc트위터", description="Twitter/X 게시 또는 타임라인 조회")
    @app_commands.describe(action="작업 (post/timeline/search)", content="내용")
    @app_commands.choices(action=[
        app_commands.Choice(name="게시 (post)", value="post"),
        app_commands.Choice(name="타임라인 (timeline)", value="timeline"),
        app_commands.Choice(name="검색 (search)", value="search"),
    ])
    async def oc_twitter(self, interaction: discord.Interaction,
                         action: str = "timeline", content: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("twitter")
        if action == "post":
            msg = f"Post to Twitter: {content}"
        elif action == "search":
            msg = f"Search Twitter for: {content}"
        else:
            msg = "Show my Twitter timeline"
        await self._safe_run(interaction, f"🐦 Twitter ({action})",
                             self.oc.run_skill(msg, timeout=30))

    # ── /oc인스타 ──────────────────────────────────────────────────
    @app_commands.command(name="oc인스타", description="Instagram 관리")
    @app_commands.describe(action="작업 (feed/insights/post)", content="내용")
    @app_commands.choices(action=[
        app_commands.Choice(name="피드 (feed)", value="feed"),
        app_commands.Choice(name="인사이트 (insights)", value="insights"),
        app_commands.Choice(name="게시 (post)", value="post"),
    ])
    async def oc_instagram(self, interaction: discord.Interaction,
                           action: str = "feed", content: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("instagram")
        if action == "post":
            msg = f"Post to Instagram: {content}"
        elif action == "insights":
            msg = "Show my Instagram insights and analytics"
        else:
            msg = "Show my Instagram feed"
        await self._safe_run(interaction, f"📸 Instagram ({action})",
                             self.oc.run_skill(msg, timeout=30))

    # ── /oc이메일 ──────────────────────────────────────────────────
    @app_commands.command(name="oc이메일", description="이메일 전송/조회")
    @app_commands.describe(action="작업 (send/read/search)", to="수신자",
                          subject="제목", body="본문")
    @app_commands.choices(action=[
        app_commands.Choice(name="전송 (send)", value="send"),
        app_commands.Choice(name="읽기 (read)", value="read"),
        app_commands.Choice(name="검색 (search)", value="search"),
    ])
    async def oc_email(self, interaction: discord.Interaction,
                       action: str = "read", to: str = "", subject: str = "",
                       body: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("email")
        if action == "send":
            if to and not _EMAIL_RE.match(to):
                await interaction.followup.send("잘못된 이메일 주소 형식입니다.", ephemeral=True)
                return
            # Sanitize fields
            subject = re.sub(r'[\r\n]', '', subject)[:200]
            msg = f"Send email to {to} with subject '{subject}': {body[:5000]}"
        elif action == "search":
            msg = f"Search emails for: {subject or body}"
        else:
            msg = "Show recent unread emails"
        await self._safe_run(interaction, f"📧 이메일 ({action})",
                             self.oc.run_skill(msg, timeout=30))

    # ── /oc노션 ────────────────────────────────────────────────────
    @app_commands.command(name="oc노션", description="Notion 페이지 생성/조회")
    @app_commands.describe(action="작업 (create/search/list)", title="제목", content="내용")
    @app_commands.choices(action=[
        app_commands.Choice(name="생성 (create)", value="create"),
        app_commands.Choice(name="검색 (search)", value="search"),
        app_commands.Choice(name="목록 (list)", value="list"),
    ])
    async def oc_notion(self, interaction: discord.Interaction,
                        action: str = "list", title: str = "", content: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("notion")
        if action == "create":
            msg = f"Create Notion page titled '{title}' with content: {content}"
        elif action == "search":
            msg = f"Search Notion for: {title or content}"
        else:
            msg = "List my recent Notion pages"
        await self._safe_run(interaction, f"📓 Notion ({action})",
                             self.oc.run_skill(msg, timeout=30))

    # ── /oc슬랙 ────────────────────────────────────────────────────
    @app_commands.command(name="oc슬랙", description="Slack 메시지 전송")
    @app_commands.describe(channel="채널 이름", message="메시지 내용")
    async def oc_slack(self, interaction: discord.Interaction,
                       channel: str, message: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("slack")
        await self._safe_run(interaction, f"💬 Slack → #{channel}",
                             self.oc.run_skill(
                                 f"Send message to Slack channel #{channel}: {message}", timeout=15))

    # ── /oc트렐로 ──────────────────────────────────────────────────
    @app_commands.command(name="oc트렐로", description="Trello 보드/카드 관리")
    @app_commands.describe(action="작업 (list/add/move)", details="상세 내용")
    @app_commands.choices(action=[
        app_commands.Choice(name="보드 목록 (list)", value="list"),
        app_commands.Choice(name="카드 추가 (add)", value="add"),
        app_commands.Choice(name="카드 이동 (move)", value="move"),
    ])
    async def oc_trello(self, interaction: discord.Interaction,
                        action: str = "list", details: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("trello")
        if action == "add":
            msg = f"Add Trello card: {details}"
        elif action == "move":
            msg = f"Move Trello card: {details}"
        else:
            msg = "List my Trello boards and cards"
        await self._safe_run(interaction, f"📋 Trello ({action})",
                             self.oc.run_skill(msg, timeout=30))

    # ── /oc리마인더 ────────────────────────────────────────────────
    @app_commands.command(name="oc리마인더", description="리마인더 설정 (Telegram)")
    @app_commands.describe(time="시간 (예: 30m, 2h, tomorrow 9am)", message="알림 내용")
    async def oc_reminder(self, interaction: discord.Interaction,
                          time: str, message: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("remindme")
        await self._safe_run(interaction, "⏰ 리마인더 설정",
                             self.oc.run_skill(f"Set reminder in {time}: {message}", timeout=15),
                             discord.Color.green())


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawSocialCog(bot))
