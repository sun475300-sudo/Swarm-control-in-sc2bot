# -*- coding: utf-8 -*-
"""OpenClaw 정보/검색 스킬 Cog (9 skills)."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.info")


class OpenClawInfoCog(commands.Cog, name="OpenClaw 정보"):
    """날씨, 환율, YouTube, 뉴스, 요약, 단위변환, 장소검색, 블로그감시"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()

    # ── helpers ─────────────────────────────────────────────────────
    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.blue()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.blue()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw command error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc날씨 ────────────────────────────────────────────────────
    @app_commands.command(name="oc날씨", description="OpenClaw 날씨 조회")
    @app_commands.describe(location="지역 (예: 서울, Tokyo, New York)")
    async def oc_weather(self, interaction: discord.Interaction, location: str = "서울"):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("weather")
        await self._safe_run(interaction, f"☁ {location} 날씨",
                             self.oc.run_skill(f"Get current weather for {location}", timeout=30))

    # ── /oc환율 ────────────────────────────────────────────────────
    @app_commands.command(name="oc환율", description="실시간 환율 조회")
    @app_commands.describe(from_cur="원본 통화 (예: USD)", to_cur="대상 통화 (예: KRW)")
    async def oc_exchange(self, interaction: discord.Interaction,
                          from_cur: str = "USD", to_cur: str = "KRW"):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("exchange-rates")
        await self._safe_run(interaction, f"💱 {from_cur} → {to_cur}",
                             self.oc.run_skill(f"Get exchange rate from {from_cur} to {to_cur}", timeout=30))

    # ── /oc유튜브 ──────────────────────────────────────────────────
    @app_commands.command(name="oc유튜브", description="YouTube 검색")
    @app_commands.describe(query="검색어")
    async def oc_youtube(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("youtube")
        await self._safe_run(interaction, f"▶ YouTube: {query}",
                             self.oc.run_skill(f"Search YouTube for: {query}", timeout=30),
                             discord.Color.red())

    # ── /oc요약 ────────────────────────────────────────────────────
    @app_commands.command(name="oc요약", description="URL/파일 콘텐츠 요약")
    @app_commands.describe(url="요약할 URL 또는 파일 경로")
    async def oc_summarize(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("summarize")
        await self._safe_run(interaction, "📝 요약 결과",
                             self.oc.run_skill(f"Summarize this: {url}", timeout=60),
                             discord.Color.green())

    # ── /oc뉴스 ────────────────────────────────────────────────────
    @app_commands.command(name="oc뉴스", description="최신 뉴스 요약")
    @app_commands.describe(topic="주제 (예: technology, world, korea)")
    async def oc_news(self, interaction: discord.Interaction, topic: str = "technology"):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("news-summary")
        await self._safe_run(interaction, f"📰 뉴스: {topic}",
                             self.oc.run_skill(f"Get latest news summary about {topic}", timeout=45))

    # ── /oc단위 ────────────────────────────────────────────────────
    @app_commands.command(name="oc단위", description="단위 변환")
    @app_commands.describe(expression="변환식 (예: 100 km to miles)")
    async def oc_units(self, interaction: discord.Interaction, expression: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("units")
        await self._safe_run(interaction, "📐 단위 변환",
                             self.oc.run_skill(f"Convert units: {expression}", timeout=15),
                             discord.Color.greyple())

    # ── /oc장소 ────────────────────────────────────────────────────
    @app_commands.command(name="oc장소", description="Google Places 장소 검색")
    @app_commands.describe(query="검색어", location="위치 (예: Seoul)")
    async def oc_places(self, interaction: discord.Interaction,
                        query: str, location: str = "Seoul"):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("goplaces")
        await self._safe_run(interaction, f"📍 장소: {query}",
                             self.oc.run_skill(f"Search places for '{query}' near {location}", timeout=30),
                             discord.Color.orange())

    # ── /oc블로그감시 ──────────────────────────────────────────────
    @app_commands.command(name="oc블로그감시", description="블로그/RSS 피드 모니터링")
    @app_commands.describe(feed_url="RSS 피드 URL")
    async def oc_blogwatch(self, interaction: discord.Interaction, feed_url: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("blogwatcher")
        await self._safe_run(interaction, "📡 블로그 감시",
                             self.oc.run_skill(f"Check blog feed updates from {feed_url}", timeout=30),
                             discord.Color.purple())


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawInfoCog(bot))
