# -*- coding: utf-8 -*-
"""OpenClaw Cron/자동화 스킬 Cog."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import re
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.cron")


class OpenClawCronCog(commands.Cog, name="OpenClaw 자동화"):
    """Cron 예약 작업 관리: 추가, 목록, 삭제, 실행, 상태"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()

    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.dark_gold()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.dark_gold()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw cron error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc크론목록 ────────────────────────────────────────────────
    @app_commands.command(name="oc크론목록", description="예약 작업 목록 조회")
    async def oc_cron_list(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "📋 Cron 작업 목록",
                             self.oc.cron("list"))

    # ── /oc크론상태 ────────────────────────────────────────────────
    @app_commands.command(name="oc크론상태", description="Cron 스케줄러 상태")
    async def oc_cron_status(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "⚙ Cron 상태",
                             self.oc.cron("status"))

    # ── /oc크론추가 ────────────────────────────────────────────────
    @app_commands.command(name="oc크론추가", description="예약 작업 추가")
    @app_commands.describe(
        name="작업 이름",
        schedule="cron 일정 (예: '0 9 * * *' = 매일 9시)",
        message="실행할 에이전트 메시지",
    )
    async def oc_cron_add(self, interaction: discord.Interaction,
                          name: str, schedule: str, message: str):
        await interaction.response.defer(thinking=True)
        # Basic cron validation: 5 space-separated fields
        parts = schedule.strip().split()
        if len(parts) != 5:
            await interaction.followup.send(
                "잘못된 cron 형식입니다. 5개 필드 필요 (예: '0 9 * * *')", ephemeral=True)
            return
        await self._safe_run(interaction, f"➕ Cron 추가: {name}",
                             self.oc.cron(
                                 "add",
                                 "--name", name,
                                 "--schedule", schedule,
                                 "--message", message,
                             ))

    # ── /oc크론삭제 ────────────────────────────────────────────────
    @app_commands.command(name="oc크론삭제", description="예약 작업 삭제")
    @app_commands.describe(job_id="삭제할 작업 ID")
    async def oc_cron_remove(self, interaction: discord.Interaction, job_id: str):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "🗑 Cron 삭제",
                             self.oc.cron("rm", job_id))

    # ── /oc크론실행 ────────────────────────────────────────────────
    @app_commands.command(name="oc크론실행", description="예약 작업 즉시 실행 (디버그)")
    @app_commands.describe(job_id="실행할 작업 ID")
    async def oc_cron_run(self, interaction: discord.Interaction, job_id: str):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "▶ Cron 즉시 실행",
                             self.oc.cron("run", job_id, timeout=60))

    # ── /oc크론활성화 ──────────────────────────────────────────────
    @app_commands.command(name="oc크론활성화", description="예약 작업 활성화/비활성화")
    @app_commands.describe(job_id="작업 ID", enable="활성화 여부")
    async def oc_cron_toggle(self, interaction: discord.Interaction,
                             job_id: str, enable: bool = True):
        await interaction.response.defer(thinking=True)
        action = "enable" if enable else "disable"
        label = "활성화" if enable else "비활성화"
        await self._safe_run(interaction, f"🔄 Cron {label}",
                             self.oc.cron(action, job_id))

    # ── /oc크론이력 ────────────────────────────────────────────────
    @app_commands.command(name="oc크론이력", description="Cron 실행 이력 조회")
    async def oc_cron_history(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "📜 Cron 실행 이력",
                             self.oc.cron("runs"))


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawCronCog(bot))
