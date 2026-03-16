# -*- coding: utf-8 -*-
"""OpenClaw 금융 스킬 Cog (stock-analysis, crypto-wallet)."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.finance")


class OpenClawFinanceCog(commands.Cog, name="OpenClaw 금융"):
    """주식 분석, 크립토 지갑 관리"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()

    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.gold()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.gold()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw command error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc주식 ────────────────────────────────────────────────────
    @app_commands.command(name="oc주식", description="주식 종합 분석 (8차원 스코어링)")
    @app_commands.describe(ticker="종목코드 (예: AAPL, TSLA, 005930.KS)")
    async def oc_stock(self, interaction: discord.Interaction, ticker: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("stock-analysis")
        await self._safe_run(interaction, f"📊 주식 분석: {ticker.upper()}",
                             self.oc.run_skill(
                                 f"Analyze stock {ticker} with full scoring, dividend info, and trend detection",
                                 timeout=60))

    # ── /oc핫스캐너 ────────────────────────────────────────────────
    @app_commands.command(name="oc핫스캐너", description="바이럴 트렌드 주식 감지")
    async def oc_hot_scanner(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("stock-analysis")
        await self._safe_run(interaction, "🔥 핫 스캐너",
                             self.oc.run_skill(
                                 "Run hot scanner to detect viral trending stocks and early signals",
                                 timeout=60),
                             discord.Color.red())

    # ── /oc지갑 ────────────────────────────────────────────────────
    @app_commands.command(name="oc지갑", description="멀티체인 크립토 지갑 조회")
    @app_commands.describe(address="지갑 주소 (선택)", chain="체인 (ethereum, solana, bitcoin)")
    async def oc_wallet(self, interaction: discord.Interaction,
                        address: str = "", chain: str = "ethereum"):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("crypto-wallet")
        msg = f"Check crypto wallet balance on {chain}"
        if address:
            msg += f" for address {address}"
        await self._safe_run(interaction, f"💰 크립토 지갑 ({chain})",
                             self.oc.run_skill(msg, timeout=30))


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawFinanceCog(bot))
